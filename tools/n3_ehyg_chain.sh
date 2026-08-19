#!/bin/bash
# N3 causal block + E-HYG rider, gap-gated (approved 2026-08-21: "立刻启动 E-HYG 与 N3 关键因果块",
# reconciled with the GPU rule by running only in >=14GB headroom windows, nice priority).
set -u
R=/data/robotixx/climb
LOG=$R/logs/campaign
mkdir -p $LOG $R/reports/N3 $R/reports/E_HYG
CK_S2=$(ls -d $R/logs/rsl_rl/g1_tracking/*uniform-mixed100-s2)/model_3999.pt
CK_S3=$(ls -d $R/logs/rsl_rl/g1_tracking/*uniform-mixed100-s3)/model_3999.pt

waitgpu() { local ok=0; while [ $ok -lt 3 ]; do
  u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
  [ $((32607-u)) -ge ${1:-14000} ] && ok=$((ok+1)) || ok=0; sleep 60; done; }

# ---- resume-safety verification (abort on any mismatch) ----------------------
verify() {
  local fail=0
  check() { local got=$(sha256sum "$1" | cut -c1-8); [ "$got" = "$2" ] || { echo "HASH MISMATCH $1: $got != $2"; fail=1; }; }
  check $R/bank/tiers/aug_ground16.txt      e489f1b8
  check $R/bank/tiers/aug_random16.txt      17aa3f5a
  check $R/tools/analyze_n3.py              b118b2d3
  check $R/bank/tiers/tier_800_pruned.txt   4cfb5aea
  check $R/tools/analyze_ehyg.py            5f8eb56e
  # composed tier files must equal mixed100 + augmentation, in order
  cat $R/bank/tiers/tier_mixed100.txt $R/bank/tiers/aug_ground16.txt | diff -q - $R/bank/tiers/tier_mixed100_plus_ground16.txt || fail=1
  cat $R/bank/tiers/tier_mixed100.txt $R/bank/tiers/aug_random16.txt | diff -q - $R/bank/tiers/tier_mixed100_plus_random16.txt || fail=1
  [ -f "$CK_S2" ] && [ -f "$CK_S3" ] || { echo "missing s2/s3 checkpoints"; fail=1; }
  echo "config: ITERS=4000 ENVS=4096 seeds: A1={1,2} A2={1} A3={1} EHYG={1}"
  return $fail
}
verify > $LOG/n3_verify.log 2>&1 || { echo "VERIFY FAILED" >> $LOG/n3_verify.log; exit 1; }

STRAT="$R/bridge/.venv/bin/python $R/tools/eval_stratified.py --offsets 0,1,2,3,4,6,8 --window 3 --episodes 8"
export ITERS=4000 ENVS=4096 EPISODES=8

# ---- 0) pre-unblinding baselines (cheap, first): stratified s2/s3 on probe clips
waitgpu 8000
MUJOCO_GL=egl $R/tools/with_sentinel.sh $R/reports/N3/baseline_s2 -- $STRAT --checkpoint "$CK_S2" \
  --clips $R/plan/N3_probe_clips.txt --out $R/reports/N3_baseline_uniform-s2_strat.csv > $LOG/n3_base_s2.log 2>&1
MUJOCO_GL=egl $R/tools/with_sentinel.sh $R/reports/N3/baseline_s3 -- $STRAT --checkpoint "$CK_S3" \
  --clips $R/plan/N3_probe_clips.txt --out $R/reports/N3_baseline_uniform-s3_strat.csv > $LOG/n3_base_s3.log 2>&1

# ---- 1) N3 training arms (keystone first) ----
waitgpu 14000
BANKTAG=mixed100g16 TRAIN_CLIPS=$R/bank/tiers/tier_mixed100_plus_ground16.txt ARMS=uniform  SEEDS="1 2" bash $R/tools/run_campaign_n3.sh > $LOG/n3_A1.log 2>&1
waitgpu 14000
BANKTAG=mixed100g16 TRAIN_CLIPS=$R/bank/tiers/tier_mixed100_plus_ground16.txt ARMS=adaptive SEEDS="1"   bash $R/tools/run_campaign_n3.sh > $LOG/n3_A2.log 2>&1
waitgpu 14000
BANKTAG=mixed100r16 TRAIN_CLIPS=$R/bank/tiers/tier_mixed100_plus_random16.txt ARMS=uniform  SEEDS="1"   bash $R/tools/run_campaign_n3.sh > $LOG/n3_A3.log 2>&1

# ---- 2) N3 stratified evals for the new arms ----
for tag in uniform-mixed100g16-s1 uniform-mixed100g16-s2 adaptive-mixed100g16-s1 uniform-mixed100r16-s1; do
  CK=$(ls -d $R/logs/rsl_rl/g1_tracking/*$tag 2>/dev/null | tail -1)/model_3999.pt
  [ -f "$CK" ] || { echo "missing $tag" >> $LOG/n3_evals.log; continue; }
  waitgpu 8000
  MUJOCO_GL=egl $R/tools/with_sentinel.sh $R/reports/N3/strat_$tag -- $STRAT --checkpoint "$CK" \
    --clips $R/plan/N3_probe_clips.txt --out $R/reports/N3_${tag}_strat.csv >> $LOG/n3_evals.log 2>&1
done
touch $R/reports/N3/TRAINING_BLOCK_DONE

# ---- 3) E-HYG (sealed a5494b7c): comparator (E3 arm run early) + pruned ----
waitgpu 14000
BANKTAG=amass800  TRAIN_CLIPS=$R/bank/tiers/tier_800.txt        ARMS=uniform SEEDS="1" bash $R/tools/run_campaign_n3.sh > $LOG/ehyg_comparator.log 2>&1
waitgpu 14000
BANKTAG=amass800p TRAIN_CLIPS=$R/bank/tiers/tier_800_pruned.txt ARMS=uniform SEEDS="1" bash $R/tools/run_campaign_n3.sh > $LOG/ehyg_pruned.log 2>&1
for tag in uniform-amass800-s1 uniform-amass800p-s1; do
  CK=$(ls -d $R/logs/rsl_rl/g1_tracking/*$tag 2>/dev/null | tail -1)/model_3999.pt
  [ -f "$CK" ] || { echo "missing $tag" >> $LOG/ehyg_evals.log; continue; }
  for pair in "heldout100:$R/bank/tiers/heldout100.txt" "zsg:$R/bank/tiers/zs_ground_feasible.txt" "zsd:$R/bank/tiers/zs_dynamic_feasible.txt"; do
    nm=${pair%%:*}; f=${pair#*:}
    waitgpu 8000
    MUJOCO_GL=egl $R/tools/with_sentinel.sh $R/reports/E_HYG/${tag}_${nm} -- $STRAT --checkpoint "$CK" \
      --clips "$f" --out $R/reports/E_HYG_${tag}_${nm}_strat.csv >> $LOG/ehyg_evals.log 2>&1
  done
done
touch $R/reports/E_HYG/EVALS_DONE
echo "chain done $(date -u)" >> $LOG/n3_ehyg_chain.log
