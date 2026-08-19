#!/usr/bin/env python3
"""S1 — Newton <-> mjlab conformance on one clip, one frozen policy.

The gate for the entire evaluation-side fragility program: nothing measured
under a Newton solver is believable until Newton reproduces mjlab's own result
under the *same* physics.

Architecture: mjlab keeps everything it is good at -- observations, the frozen
policy, action scaling, terminations, the motion command -- and Newton replaces
only the physics step. Per control step:

    mjlab obs -> policy -> mjlab writes ctrl (PD targets)
        -> targets copied into Newton control.joint_target_q
        -> Newton solver steps `decimation` substeps
        -> Newton joint_q / joint_qd copied back into mjlab's qpos / qvel
        -> mjlab mj_forward so sensors and terminations see the new state

Newton is built from *mjlab's own compiled MjModel* (saved to XML), with mjlab's
runtime solver options, actuator gains, effort limits and armature transplanted,
so the only thing that differs from a stock mjlab rollout is which code
integrates the equations of motion. With SolverMuJoCo that is the same
mujoco_warp 3.11.0 both sides -- so the S1 prediction is agreement to within
seed noise, and disagreement means the plumbing is wrong.

Runs three arms in one process on the same clip and policy:
    mjlab      stock mjlab stepping                (the reference)
    newton_mjw Newton SolverMuJoCo, MJWarp backend (S1 proper)
    newton_cpu Newton SolverMuJoCo, MuJoCo-C CPU   (first ladder rung)

Usage:
    s1_newton_conformance.py --checkpoint model_3999.pt --clip walk1_subject1 \
        --episodes 16 --out reports/S1_conformance.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import re
import tempfile
import time
from dataclasses import asdict

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# --------------------------------------------------------------------------- #
# mjlab side
# --------------------------------------------------------------------------- #

def build_mjlab(clip_path: str, num_envs: int, device: str):
    import climb  # noqa: F401  (registers Climb-* tasks)
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.tasks.registry import load_rl_cfg, load_runner_cls
    from climb import climb_g1_tracking_env_cfg

    task = "Climb-Tracking-Flat-Unitree-G1"
    env_cfg = climb_g1_tracking_env_cfg(motion_files=[clip_path], sampling_mode="uniform")
    env_cfg.scene.num_envs = num_envs
    env_cfg.commands["motion"].resampling_time_range = (1.0e9, 1.0e9)
    # Keep mjlab's events exactly as trained. An earlier version stripped them
    # for "determinism" and the reference arm died in 0.2 s: the startup DR
    # (base_com, encoder_bias, foot_friction) is part of the distribution the
    # policy was trained under, and encoder_bias in particular is folded into
    # how it reads joint_pos. Only the interval push is removed, so a fall is
    # attributable to physics rather than to a random shove. Obs noise stays
    # off for the same reason -- both arms then see identical inputs.
    if "push_robot" in env_cfg.events:
        del env_cfg.events["push_robot"]
    for grp in env_cfg.observations.values():
        grp.enable_corruption = False
    agent_cfg = load_rl_cfg(task)
    env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    return env, wrapped, agent_cfg, load_runner_cls(task)


def load_policy(runner_cls, wrapped, agent_cfg, checkpoint: str, device: str):
    runner = runner_cls(wrapped, asdict(agent_cfg), device=device)
    runner.load(checkpoint, load_cfg={"actor": True}, strict=True, map_location=device)
    return runner.get_inference_policy(device=device)


# --------------------------------------------------------------------------- #
# Newton side
# --------------------------------------------------------------------------- #

class NewtonPhysics:
    """A Newton solver driven from mjlab's ctrl, syncing state back each step."""

    def __init__(self, env, backend: str, device: str):
        import mujoco
        import newton
        import warp as wp
        from newton import JointTargetMode

        # Targets indexed like joint_q (36 = 7 free + 29 hinges) rather than
        # like joint_qd (35). We address targets by MuJoCo qposadr, so this
        # must be the coordinate layout.
        newton.use_coord_layout_targets = True

        self.env = env
        self.mj_model = env.sim.mj_model
        m = self.mj_model
        self.n_env = env.num_envs
        self.wp_device = device

        # Newton reads the robot from MJCF. Serialise mjlab's own MjSpec -- the
        # exact spec it compiled -- so collision geoms, inertias and joint order
        # are identical. (mj_saveLastXML only works after from_xml_*, and mjlab
        # compiles from a spec, so go through the spec.)
        # Written into a scratch dir that symlinks the G1 mesh folder, so the
        # spec's relative mesh paths resolve. Collision geoms are primitives;
        # meshes are visual, but Newton's importer still resolves them.
        scratch = tempfile.mkdtemp(prefix="s1_")
        mesh_src = os.path.join(os.path.dirname(__import__("mjlab").__file__),
                                "asset_zoo", "robots", "unitree_g1", "xmls", "assets")
        os.symlink(mesh_src, os.path.join(scratch, "assets"))
        xml = os.path.join(scratch, "g1_compiled.xml")
        spec_xml = env.scene.spec.to_xml()
        with open(xml, "w") as fh:
            fh.write(spec_xml)
        # to_xml() flattens meshdir into per-file relative names; make sure the
        # resolver looks in ./assets for any bare "*.STL".
        if 'meshdir=' not in spec_xml:
            spec_xml = spec_xml.replace("<compiler", '<compiler meshdir="assets"', 1)
            with open(xml, "w") as fh:
                fh.write(spec_xml)

        # Two Newton builder defaults differ from mjlab and must be pinned:
        #  - rigid_gap defaults to 0.1 m and is applied to every shape whose
        #    config leaves gap unset -- including the ground plane. MuJoCo's
        #    gap gates when a contact enters the solver, so a 10 cm gap makes
        #    the feet "touch" early and the robot bounces (z oscillating
        #    0.76-0.81 while mjlab held 0.772). mjlab uses gap = 0.
        #    Newton's own robot_policy example sets rigid_gap = 0.0 for the
        #    same reason.
        #  - the XML's opt.timestep is what parse_mujoco_options bakes into the
        #    MjModel; mjlab overrides it at runtime to 0.005. Rewrite the XML so
        #    Newton compiles the runtime value rather than the file default.
        scfg = env.cfg.sim.mujoco
        spec_xml = re.sub(r'timestep="[^"]*"', f'timestep="{scfg.timestep}"', spec_xml, count=1)
        if 'timestep=' not in spec_xml:
            spec_xml = spec_xml.replace("<option", f'<option timestep="{scfg.timestep}"', 1)
        with open(xml, "w") as fh:
            fh.write(spec_xml)

        builder = newton.ModelBuilder()
        builder.rigid_gap = 0.0
        builder.default_shape_cfg.gap = 0.0
        builder.add_mjcf(xml, ignore_names=["terrain"], parse_meshes=True,
                         parse_visuals=False, enable_self_collisions=True)
        # Ground plane with mjlab's terrain contact params (friction 1.0,
        # default solref/solimp, gap 0).
        gcfg = newton.ModelBuilder.ShapeConfig(mu=1.0, gap=0.0)
        builder.add_ground_plane(cfg=gcfg)
        base = builder                                    # one world, then replicate
        full = newton.ModelBuilder()
        full.replicate(base, world_count=self.n_env)

        # Joint layout: free (7q/6qd) then hinges. Map mjlab actuator -> Newton dof.
        # actuator i drives joint trnid; gains from the compiled model.
        kp = m.actuator_gainprm[:, 0].copy()
        kd = -m.actuator_biasprm[:, 2].copy()
        fmax = m.actuator_forcerange[:, 1].copy()
        act_joint = [m.actuator_trnid[i, 0] for i in range(m.nu)]
        act_dof = [m.jnt_dofadr[j] for j in act_joint]          # dof index in mjlab (0..34)
        self.act_dof = np.asarray(act_dof)
        self.act_qadr = np.asarray([m.jnt_qposadr[j] for j in act_joint])

        # Newton dof indexing: per world, [6 free] + hinges in dfs order = same
        # as MuJoCo's qvel layout for this single-tree model (verified: masses,
        # armature, joint ranges and the 34 collision geoms all match).
        dof_per_world = m.nv
        q_per_world = m.nq

        # Do NOT set joint_target_ke/kd/mode here. mjlab's spec already carries
        # its 29 <position> actuators with kp, kd and forcerange, and Newton's
        # importer maps those to JOINT_TARGET/POSITION driven by
        # control.joint_target_q. Setting target gains on top synthesises a
        # *second* actuator per joint that receives no ctrl and pulls every
        # joint toward zero with kp up to 99 -- the first S1 run built nu=58
        # and the robot "fell" under a pure hold. Nothing to transplant: the
        # imported actuators are byte-identical to mjlab's.
        self._imported_actuator_gains = (kp, kd, fmax)

        self.model = full.finalize(device=device)
        self.model.set_gravity(tuple(float(g) for g in m.opt.gravity))
        assert self.model.joint_dof_count == self.n_env * dof_per_world, \
            (self.model.joint_dof_count, self.n_env, dof_per_world)
        assert self.model.joint_coord_count == self.n_env * q_per_world

        # Every solver option comes from mjlab's *runtime* MujocoCfg, not from
        # the compiled XML (which still carries the file defaults: 0.002 s,
        # 100 iters, Euler). This is what mjlab actually integrates with.
        scfg = env.cfg.sim.mujoco
        self.dt = float(scfg.timestep)
        self.decimation = int(env.cfg.decimation)
        kw = dict(solver=scfg.solver, integrator=scfg.integrator, cone=scfg.cone,
                  jacobian=None if scfg.jacobian == "auto" else scfg.jacobian,
                  iterations=int(scfg.iterations), ls_iterations=int(scfg.ls_iterations),
                  tolerance=float(scfg.tolerance), ls_tolerance=float(scfg.ls_tolerance),
                  impratio=float(scfg.impratio))
        # update_data_interval=0: do NOT re-derive mjw_data.qpos/qvel from
        # Newton's joint_q/joint_qd each step. We sync mjlab's MuJoCo state
        # straight into Newton's MuJoCo state -- identical layout and identical
        # conventions (wxyz quaternion, body-frame angular velocity, joint-
        # origin linear velocity) -- and let Newton's own kernels lift it back
        # to joint_q/qd after stepping. Round-tripping through Newton's
        # free-joint convention (world-frame omega, COM-referenced v) was the
        # last divergence: 0.64 rad/s on base angular x at substep 0, before
        # any dynamics could differ.
        # Contact / constraint capacity MUST match. Newton defaulted njmax to 64
        # rows per world; mjlab uses 250. At a hard multi-contact impact the
        # G1 needs 84-112 constraint rows and MJWarp silently drops rows past
        # njmax -- so Newton discarded up to half its contact constraints
        # exactly at the step-298 impact, forking survival (0.44-0.72 vs 1.00)
        # while the mean tracking error stayed identical. mjlab itself is not
        # sensitive at that instant (100% survival under 0.01 rad/s
        # perturbation), so this was integration error, as G0 assumes.
        wpm = env.sim.wp_data
        self.solver = newton.solvers.SolverMuJoCo(self.model, use_mujoco_cpu=(backend == "cpu"),
                                                  update_data_interval=0,
                                                  njmax=int(getattr(wpm, "njmax", 0) or 0) or None,
                                                  nconmax=int(getattr(wpm, "naconmax", 0) or 0) // max(self.n_env, 1) or None,
                                                  ccd_iterations=int(env.sim.mj_model.opt.ccd_iterations),
                                                  enable_multiccd=not bool(env.sim.mj_model.opt.disableflags
                                                                           & mujoco.mjtDisableBit.mjDSBL_MULTICCD),
                                                  **kw)
        if backend != "cpu":
            d = self.solver.mjw_data
            print(f"[S1] capacity: njmax newton={getattr(d,'njmax',None)} mjlab={getattr(wpm,'njmax',None)}  "
                  f"naconmax newton={getattr(d,'naconmax',None)} mjlab={getattr(wpm,'naconmax',None)}")
        # G0 discipline: after this the two MJWarp models differ in NOTHING but
        # the 35 visual (contype=0) meshes mjlab keeps and Newton drops. A
        # field-by-field diff (opt.*, sizes, per-geom/body/dof/actuator arrays)
        # found exactly three live differences -- timestep (set per step by
        # Newton, so fine at runtime), ccd_iterations, and MULTICCD -- and the
        # latter two are now pinned to mjlab's values.
        if backend != "cpu":
            for name, want in (("ccd_iterations", int(env.sim.mj_model.opt.ccd_iterations)),):
                got = getattr(self.solver.mjw_model.opt, name, None)
                got = int(wp.to_torch(got)[0]) if hasattr(got, "shape") else got
                if got is not None and got != want:
                    print(f"[S1] WARN mjw opt.{name}={got} != mjlab {want}")
        print(f"[S1] newton solver: backend={backend} dt={self.dt} decimation={self.decimation} "
              f"solver={scfg.solver} integrator={scfg.integrator} iters={scfg.iterations}/{scfg.ls_iterations}")
        self.state_a = self.model.state()
        self.state_b = self.model.state()
        self.control = self.model.control()
        # get_max_contact_count() is not implemented on the MuJoCo-C backend;
        # the contact buffer is unused here (Newton runs MuJoCo's own collision).
        self.contacts = None
        self.wp = wp
        self.newton = newton
        self.dof_per_world = dof_per_world
        self.q_per_world = q_per_world

        # torch views onto Newton's *MuJoCo* state. Same (n_env, nq)/(n_env, nv)
        # layout as mjlab's sim.data.qpos/qvel. The CPU backend holds a single
        # world in an MjData, so it is only valid for n_env == 1.
        self.cpu = backend == "cpu"
        if self.cpu:
            assert self.n_env == 1, "MuJoCo-C backend: one env per process"
            self.mq = None
        else:
            self.mq = wp.to_torch(self.solver.mjw_data.qpos)
            self.mqd = wp.to_torch(self.solver.mjw_data.qvel)
        if not self.cpu:
            assert tuple(self.mq.shape) == (self.n_env, q_per_world), self.mq.shape
            assert tuple(self.mqd.shape) == (self.n_env, dof_per_world), self.mqd.shape
        self._derived = None
        self._q_seen = None
        self._qd_seen = None
        self.absorbed_writes = 0
        # The imported <position> actuators are CTRL_DIRECT: they read
        # control.mujoco.ctrl in MJCF actuator order, NOT joint_target_q.
        # Writing targets into joint_target_q left mjw_data.ctrl at all-zeros,
        # so every joint was driven toward angle 0 -- the constant step-1 death
        # after the double-actuator fix. mjlab's ctrl is in the same actuator
        # order (verified actuator-by-actuator), so this is a straight copy.
        assert hasattr(self.control, "mujoco") and self.control.mujoco.ctrl is not None, \
            "imported actuators expected control.mujoco.ctrl"
        self.tctrl = wp.to_torch(self.control.mujoco.ctrl).view(self.n_env, m.nu)
        if backend == "cpu" and self.tctrl.device.type != "cuda":
            self.tctrl = None   # written via mj_data.ctrl instead

        # ---- G0 close-out: mirror mjlab's *live* model, not its spec. ----
        # mjlab's startup domain randomisation (base_com: torso_link body_ipos
        # +-2.5/5/5 cm; foot_friction: 0.3-1.2 shared over the 14 foot geoms;
        # encoder_bias: observation-side only) is applied to env.sim.wp_model
        # after compile, per env, and never touches the spec / mj_model that
        # this class serialised. So Newton was integrating the *nominal* G1
        # while mjlab integrated the randomised one. Measured with identical
        # (q, qd) and qvel = 0: mjlab's gravity torque about the base was
        # [-2.79, -8.24, 0] N.m, Newton's [0.03, -6.65, 0] -- a ~1 cm whole-
        # body CoM shift, exactly the 3.3 N.m free-joint qfrc_bias residual
        # that forked survival at the step-298 impact. (The exported XML loaded
        # straight into MuJoCo reproduces Newton's numbers, which is what
        # located it.) Mirror every per-env-expanded field into Newton's
        # MJWarp model through name-based index maps and recompute the derived
        # constants the same way mjlab does.
        self.mirrored_fields = []
        if not self.cpu:
            self.mirrored_fields = self._mirror_mjlab_model_fields()
            # Second G0 residual, found after the DR mirror: Newton's import
            # path (MJCF -> float32 wp.transform -> MjSpec -> MJWarp) rounds
            # geometry differently from mjlab's float64 spec -> MJWarp:
            # geom_quat 4e-7, body_pos 3e-7, geom_size 4e-8, armature 2e-8.
            # Physically nothing -- but MuJoCo's contact inclusion test is
            # dist < margin with margin = 0, and a lightly loaded foot capsule
            # rests at dist ~ 0, so a 1e-8 offset decides whether a FRICTIONAL
            # contact exists. In a Newton-driven rollout the extra contact
            # sticks the foot (|dqvel| up to 3 rad/s vs mjlab and MuJoCo-C,
            # which agree with each other to 1e-3 at those substeps) and the
            # forks accumulate into the step-298 survival split. Copy mjlab's
            # exact float32 geometry so the two MJWarp models are bitwise
            # identical where it matters.
            self._mirror_exact_geometry()

    def _mirror_exact_geometry(self):
        import mujoco_warp as mjw
        import warp as wp
        A = self.env.sim.wp_model; B = self.solver.mjw_model
        maps = self._entity_maps()
        idx = {"nbody": (maps["nbody"], self.env.sim.mj_model.nbody, self.solver.mj_model.nbody),
               "ngeom": (maps["ngeom"], self.env.sim.mj_model.ngeom, self.solver.mj_model.ngeom),
               "njnt": (maps["njnt"], self.env.sim.mj_model.njnt, self.solver.mj_model.njnt),
               "nv": (maps["nv"], self.env.sim.mj_model.nv, self.solver.mj_model.nv)}
        fields = {"nbody": ("body_pos", "body_quat", "body_ipos", "body_iquat", "body_inertia", "body_mass"),
                  "ngeom": ("geom_pos", "geom_quat", "geom_size", "geom_rbound", "geom_aabb"),
                  "njnt": ("jnt_pos", "jnt_axis"),
                  "nv": ("dof_armature",)}
        done = []
        for ax, names in fields.items():
            mp, na, nb = idx[ax]
            ia = torch.tensor(sorted(mp), device=self.wp_device); ib = torch.tensor([mp[int(i)] for i in ia.tolist()], device=self.wp_device)
            for f in names:
                a = wp.to_torch(getattr(A, f)); b = wp.to_torch(getattr(B, f))
                # strip/broadcast the world axis: mjlab (1|N, n, ...) / (n, ...); newton (1|N, n', ...) / (n', ...)
                aw = a.dim() >= 2 and a.shape[0] in (1, self.n_env) and a.shape[1] == na
                bw = b.dim() >= 2 and b.shape[0] in (1, self.n_env) and b.shape[1] == nb
                if aw and bw and a.shape[0] == self.n_env and b.shape[0] == self.n_env:
                    b[:, ib] = a[:, ia].to(b.dtype)          # per-world (DR-expanded) field
                else:
                    src = a[0] if aw else a
                    if bw:
                        b[:, ib] = src[ia].to(b.dtype)
                    else:
                        b[ib] = src[ia].to(b.dtype)
                done.append(f)
        # derived constants that depend on inertia / geometry
        with wp.ScopedDevice(self.wp_device):
            mjw.set_const(B, self.solver.mjw_data)
        print("[S1] exact-geometry mirror: " + ", ".join(done))

    # ------------------------------------------------------------------ #
    def _entity_maps(self):
        """mjlab index -> Newton index for bodies, geoms, joints, dofs, actuators.

        Newton's compiled MjModel names entities by their full path
        ('mjlab scene_worldbody_robot_pelvis', '.../robot/left_foot1_collision_6')
        while mjlab uses 'robot/pelvis' / 'robot/left_foot1_collision'; match on
        the trailing short name. Actuators are unnamed in Newton, so map them
        through the joint they drive.
        """
        import mujoco
        A = self.env.sim.mj_model
        B = self.solver.mj_model
        def nm(mdl, obj, i):
            return mujoco.mj_id2name(mdl, obj, i) or ""
        def short(n):
            return n.split("/")[-1]
        def match(obj, na, nb, tail_re):
            out = {}
            names_b = [nm(B, obj, j) for j in range(nb)]
            for i in range(na):
                s = short(nm(A, obj, i))
                if not s:
                    continue
                pat = re.compile(tail_re.format(s=re.escape(s)))
                c = [j for j, n in enumerate(names_b) if pat.search(n)]
                if len(c) == 1:
                    out[i] = c[0]
                elif len(c) > 1:
                    raise RuntimeError(f"ambiguous match for {s}: {[names_b[j] for j in c]}")
            return out
        body = match(mujoco.mjtObj.mjOBJ_BODY, A.nbody, B.nbody, r"(^|[_/]){s}$")
        geom = match(mujoco.mjtObj.mjOBJ_GEOM, A.ngeom, B.ngeom, r"(^|[_/]){s}(_\d+)?$")
        jnt = match(mujoco.mjtObj.mjOBJ_JOINT, A.njnt, B.njnt, r"(^|[_/]){s}$")
        dof = {}
        ndof = {int(mujoco.mjtJoint.mjJNT_FREE): 6, int(mujoco.mjtJoint.mjJNT_BALL): 3}
        for ja, jb in jnt.items():
            for k in range(ndof.get(int(A.jnt_type[ja]), 1)):
                dof[int(A.jnt_dofadr[ja]) + k] = int(B.jnt_dofadr[jb]) + k
        act = {}
        jb_to_actb = {int(B.actuator_trnid[j, 0]): j for j in range(B.nu)}
        for i in range(A.nu):
            ja = int(A.actuator_trnid[i, 0])
            if ja in jnt and jnt[ja] in jb_to_actb:
                act[i] = jb_to_actb[jnt[ja]]
        return {"nbody": body, "ngeom": geom, "njnt": jnt, "nv": dof, "nu": act}

    def _mirror_mjlab_model_fields(self):
        """Copy mjlab's per-env-randomised wp_model fields into Newton's mjw_model."""
        import mujoco_warp as mjw
        import warp as wp
        from mjlab.sim.randomization import expand_model_fields
        sim = self.env.sim
        fields = sorted(getattr(sim, "_expanded_fields", set()))
        if not fields:
            print("[S1] mirror: mjlab expanded no model fields")
            return []
        maps = self._entity_maps()
        A = sim.mj_model
        # which entity axis a field is indexed by, from its mj_model length
        axis_of = {A.nbody: "nbody", A.ngeom: "ngeom", A.njnt: "njnt", A.nv: "nv", A.nu: "nu"}
        # expand Newton's copies to per-world first (mjlab's helper, same layout)
        with wp.ScopedDevice(self.wp_device):
            expand_model_fields(self.solver.mjw_model, self.n_env, list(fields))
        done = []
        for f in fields:
            src = wp.to_torch(getattr(sim.wp_model, f))          # (n_env, N, ...)
            dst = wp.to_torch(getattr(self.solver.mjw_model, f))  # (n_env, N', ...)
            n = int(getattr(A, f).shape[0])
            ax = axis_of.get(n)
            if ax is None or src.shape[0] != self.n_env or dst.shape[0] != self.n_env:
                print(f"[S1] mirror: skip {f} (src {tuple(src.shape)} dst {tuple(dst.shape)} n={n})")
                continue
            mp = maps[ax]
            ia = torch.tensor(sorted(mp.keys()), device=src.device)
            ib = torch.tensor([mp[int(i)] for i in ia.tolist()], device=src.device)
            dst[:, ib] = src[:, ia].to(dst.dtype)
            done.append((f, ax, int(ia.numel()), int(n)))
        # derived constants: mjlab recomputes after each DR event; do the full set once
        with wp.ScopedDevice(self.wp_device):
            mjw.set_const(self.solver.mjw_model, self.solver.mjw_data)
        print("[S1] mirror: " + ", ".join(f"{f}[{ax}:{k}/{n}]" for f, ax, k, n in done))
        return done

    def sync_from_mjlab(self):
        """mjlab qpos/qvel -> Newton's MuJoCo state (call after any mjlab reset)."""
        if self.cpu:
            self.solver.mj_data.qpos[:] = self.env.sim.data.qpos[0].cpu().numpy()
            self.solver.mj_data.qvel[:] = self.env.sim.data.qvel[0].cpu().numpy()
        else:
            self.mq.copy_(self.env.sim.data.qpos)
            self.mqd.copy_(self.env.sim.data.qvel)
        # Newton's step reads mjw_data directly (update_data_interval=0), and
        # writes joint_q/qd back afterwards, so no FK is needed here.
        self._q_seen = self.env.sim.data.qpos.clone()
        self._qd_seen = self.env.sim.data.qvel.clone()
        self.absorbed_writes = 0

    def _absorb_external_state_writes(self):
        """Pull any qpos/qvel that mjlab wrote since Newton's last writeback.

        The coupling was one-directional (Newton -> mjlab each substep) and that
        was the last G0 residual: mjlab writes robot state *itself* during an
        episode -- the motion command's clip wrap teleports the robot to a fresh
        reference frame (`_resample_command`), auto-reset re-poses terminated
        envs, and interval events like push_robot set qvel. KIT_1226 is a 6.0 s
        clip; "the step-298 contact-event fork" was the 6.0 s wrap: mjlab's arm
        got teleported onto the new reference, Newton's arm had the teleport
        overwritten by its own physics one substep later and had to chase a
        reference that had jumped -- 40-60% of envs then exceeded the
        `ee_body_pos` threshold. Per-substep physics was identical throughout
        (mjlab shadow-stepping Newton's states: 1 of 1280 substeps differed by
        > 1e-3 rad/s). So: any env whose mjlab state differs from what Newton
        last wrote is treated as externally re-posed and copied into Newton,
        with its warm start cleared.
        """
        if getattr(self, "_q_seen", None) is None:
            return
        q = self.env.sim.data.qpos
        qd = self.env.sim.data.qvel
        changed = (q != self._q_seen).any(dim=1) | (qd != self._qd_seen).any(dim=1)
        if not bool(changed.any()):
            return
        self.absorbed_writes += int(changed.sum())
        if self.cpu:
            self.solver.mj_data.qpos[:] = q[0].cpu().numpy()
            self.solver.mj_data.qvel[:] = qd[0].cpu().numpy()
            self.solver.mj_data.qacc_warmstart[:] = 0.0
        else:
            self.mq[changed] = q[changed]
            self.mqd[changed] = qd[changed]
            ws = self.wp.to_torch(self.solver.mjw_data.qacc_warmstart)
            ws[changed] = 0.0

    def ctrl_for_substep(self):
        """The ctrl Newton applies this substep. Hook for interventions (G1 delay FIFO)."""
        return self.env.sim.data.ctrl

    def substep_from_ctrl(self):
        """ONE physics substep: mjlab ctrl -> Newton -> mjlab qpos/qvel + forward.

        Called in place of each mjlab ``sim.step()``. mjlab's env loop runs
        apply_action -> write_data_to_sim -> sim.step -> scene.update once per
        substep and relies on the step's own forward pass for xpos/xquat/
        sensors -- it never calls forward() separately. So Newton must be
        stepped once per call and the derived quantities refreshed each time;
        doing all substeps on the first call and no-op'ing the rest left
        scene.update reading stale poses and fired anchor_ori/ee_body_pos on
        step 0 with a near-perfect tracking error.
        """
        self._absorb_external_state_writes()
        ctrl = self.ctrl_for_substep()
        if self.tctrl is not None:
            self.tctrl.copy_(ctrl)   # (n_env, nu), mjlab wrote it this substep
        else:
            self.solver.mj_data.ctrl[:] = ctrl[0].cpu().numpy()
        self.state_a.clear_forces()
        self.solver.step(self.state_a, self.state_b, self.control, None, self.dt)
        self.state_a, self.state_b = self.state_b, self.state_a
        if self.cpu:
            d = self.solver.mj_data
            self.env.sim.data.qpos[0] = torch.as_tensor(d.qpos, dtype=torch.float32, device=self.env.device)
            self.env.sim.data.qvel[0] = torch.as_tensor(d.qvel, dtype=torch.float32, device=self.env.device)
            self._q_seen = self.env.sim.data.qpos.clone()
            self._qd_seen = self.env.sim.data.qvel.clone()
            self.env.sim.forward()
            return
        # MuJoCo state -> MuJoCo state: no quaternion reorder, no frame change.
        # But enforce quaternion sign continuity. At a hard impact MJWarp's
        # integrator can land on -q rather than +q (same rotation); mjlab's
        # anchor-orientation observation and its termination difference
        # quaternions directly, so a sign flip reads as a 360 deg error, the
        # policy reacts violently, and ee_body_pos fires. Traced exactly: at
        # step 298 |dq| jumped 0.135 -> 1.99 on the free-joint quaternion in
        # one step, ee error 0.155 -> 0.381, 3/16 envs killed. Keep the sign
        # continuous with what mjlab held before this substep.
        prev = self.env.sim.data.qpos[:, 3:7]
        newq = self.mq[:, 3:7]
        flip = (newq * prev).sum(dim=1, keepdim=True) < 0
        if bool(flip.any()):
            self.mq[:, 3:7] = torch.where(flip, -newq, newq)   # in place: mjw_data too
        self.env.sim.data.qpos[:] = self.mq
        self.env.sim.data.qvel[:] = self.mqd
        self._q_seen = self.mq.clone()
        self._qd_seen = self.mqd.clone()
        # Then let mjlab recompute its own derived quantities. Two earlier
        # variants were both wrong: (a) forward() alone -- fine, but I then
        # (b) removed it in favour of mirroring Newton's derived arrays, and
        # the mirroring silently mirrored NOTHING (the name list resolved
        # empty), leaving xpos AND sensordata stale. Newton also imports no
        # sensors at all (nsensor 7 -> 0), so mjlab's IMU obs terms
        # (imu_lin_vel / imu_ang_vel) can only come from mjlab's forward. A
        # policy fed stale IMU velocities tracks fine on the mean and then
        # overshoots at a hard impact -- the step-298 fork. mjlab itself is
        # NOT sensitive there (100% survival under 0.01 rad/s perturbation),
        # so that fork was integration error, exactly as G0 says to assume.
        # Positions from a fresh forward equal Newton's xpos to 1e-5, so this
        # costs nothing in staleness parity.
        self.env.sim.forward()


# --------------------------------------------------------------------------- #
# rollout
# --------------------------------------------------------------------------- #

def rollout(env, wrapped, policy, physics, horizon_steps: int, arm: str):
    """One frozen-policy rollout of `env.num_envs` episodes from frame 0."""
    cmd = env.command_manager.get_term("motion")
    n = env.num_envs
    obs, _ = wrapped.reset()
    cmd.assign_clips(torch.zeros(n, dtype=torch.long, device=env.device), at_start=True)
    # assign_clips teleports the robot onto frame 0 AFTER reset() computed its
    # observation, so `obs` still describes mjlab's random pre-teleport pose
    # (a random clip time +- noise): joint_pos differed by up to 1.15 rad and
    # the reference term by 1.2 between two resets. The first action was
    # therefore a random kick that differed between arms and between runs.
    # Recompute the observation from the actual start state so every arm and
    # every env starts from the same (obs, state) pair.
    env.sim.forward()
    obs = wrapped.get_observations()
    if physics is not None:
        physics.sync_from_mjlab()

    alive = torch.ones(n, dtype=torch.bool, device=env.device)
    steps = torch.zeros(n, device=env.device)
    err_sum = torch.zeros(n, device=env.device)
    root_z = []
    t0 = time.time()
    with torch.no_grad():
        for k in range(horizon_steps):
            act = policy(obs)
            if physics is None:
                obs, _, _, _ = wrapped.step(act)
            else:
                # Let mjlab do everything *except* the physics: write actions
                # (-> ctrl), then we step Newton, then mjlab computes obs/dones.
                obs, _, _, _ = _step_with_external_physics(env, wrapped, act, physics)
            failed = env.termination_manager.terminated.bool()
            e = cmd.metrics["error_body_pos"]
            err_sum += torch.where(alive, e, torch.zeros_like(e))
            steps += alive.float()
            alive &= ~failed
            root_z.append(float(env.sim.data.qpos[:, 2].mean()))
            if not alive.any():
                break
    dt_wall = time.time() - t0
    surv = (steps >= horizon_steps).float()
    return {
        "arm": arm,
        "absorbed_state_writes": (physics.absorbed_writes if physics is not None else None),
        "survival_rate": float(surv.mean()),
        "mean_steps": float(steps.mean()),
        "mean_body_pos_err": float((err_sum / steps.clamp(min=1)).mean()),
        "root_z_trace": root_z[::10],
        "wall_s": round(dt_wall, 1),
    }


def _step_with_external_physics(env, wrapped, actions, physics):
    """mjlab's step with each sim.step() substep replaced by one Newton substep."""
    real_step = env.sim.step
    env.sim.step = physics.substep_from_ctrl
    try:
        out = wrapped.step(actions)
    finally:
        env.sim.step = real_step
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--clip", default="walk1_subject1")
    ap.add_argument("--bank", default="/data/robotixx/climb/bank/lafan1")
    ap.add_argument("--episodes", type=int, default=16)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--arms", nargs="+", default=["mjlab", "newton_mjw", "newton_cpu"])
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out")
    args = ap.parse_args()

    clip_path = os.path.join(args.bank, args.clip + ".npz")
    assert os.path.exists(clip_path), clip_path

    env, wrapped, agent_cfg, runner_cls = build_mjlab(clip_path, args.episodes, args.device)
    policy = load_policy(runner_cls, wrapped, agent_cfg, args.checkpoint, args.device)
    horizon = int(args.seconds / env.step_dt)
    print(f"[S1] clip={args.clip} episodes={args.episodes} horizon={horizon} steps "
          f"(control dt {env.step_dt:.3f}s, sim dt {env.cfg.sim.mujoco.timestep}, "
          f"decimation {env.cfg.decimation})")

    results = []
    for arm in args.arms:
        if arm == "mjlab":
            r = rollout(env, wrapped, policy, None, horizon, arm)
        elif arm == "mjlab_fwdsub":
            # Protocol probe: stock mjlab physics, but forward() after every
            # substep -- exactly what the Newton arm does -- so terminations
            # and scene.update see fresh (not one-substep-stale) kinematics
            # and the constraint warm start is refreshed 4x per control step.
            real_step = env.sim.step
            def _step_fwd():
                real_step()
                env.sim.forward()
            env.sim.step = _step_fwd
            try:
                r = rollout(env, wrapped, policy, None, horizon, arm)
            finally:
                env.sim.step = real_step
        else:
            backend = "cpu" if arm.endswith("cpu") else "mjw"
            phys = NewtonPhysics(env, backend, args.device)
            r = rollout(env, wrapped, policy, phys, horizon, arm)
        results.append(r)
        print(f"  {arm:>11s}: survival={r['survival_rate']:.3f}  mean_steps={r['mean_steps']:.1f}"
              f"  err={r['mean_body_pos_err']:.4f}  ({r['wall_s']}s)")

    ref = next((r for r in results if r["arm"] == "mjlab"), None)
    verdict = {}
    if ref:
        for r in results:
            if r["arm"] == "mjlab":
                continue
            d_surv = r["survival_rate"] - ref["survival_rate"]
            d_err = r["mean_body_pos_err"] - ref["mean_body_pos_err"]
            # Seed noise on survival at 16 episodes is ~1/16 = 0.0625 per step;
            # accept agreement within one episode and 10% on error.
            ok = abs(d_surv) <= 1.0 / args.episodes + 1e-6 and abs(d_err) <= 0.10 * max(ref["mean_body_pos_err"], 1e-6)
            verdict[r["arm"]] = {"d_survival": round(d_surv, 4), "d_err": round(d_err, 5), "conforms": ok}
            print(f"  {r['arm']:>11s} vs mjlab: Δsurv={d_surv:+.3f}  Δerr={d_err:+.4f}  "
                  f"-> {'CONFORMS' if ok else 'DIVERGES'}")

    if args.out:
        json.dump({"clip": args.clip, "episodes": args.episodes, "horizon_steps": horizon,
                   "results": results, "verdict": verdict}, open(args.out, "w"), indent=2)
        print(f"[S1] wrote {args.out}")
    env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
