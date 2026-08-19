#!/usr/bin/env python3
"""Render the two paper drafts (markdown, source of truth in paper/) as typeset article pages
for the GitHub Pages site (docs/companion.html, docs/flagship.html). Figures inserted at content
anchors; print stylesheet included so the browser's Print → PDF produces a clean document.
Re-run after any draft edit; the HTML is generated, never hand-edited."""
import re

import markdown

R = "/data/robotixx/climb/"

TPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--bg:#F7F8F8;--paper:#FFFFFF;--ink:#1A2530;--muted:#5C6B75;--rule:#DCE2E6;--accent:#0B7285;--code:#EFF2F3}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#10161A;--paper:#171F25;--ink:#E5EAED;--muted:#94A3AC;--rule:#2A363E;--accent:#4CC3D5;--code:#202A31}}}}
:root[data-theme="dark"]{{--bg:#10161A;--paper:#171F25;--ink:#E5EAED;--muted:#94A3AC;--rule:#2A363E;--accent:#4CC3D5;--code:#202A31}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Source Serif 4",Georgia,serif;font-size:17px;line-height:1.62}}
.sheet{{max-width:47rem;margin:2.2rem auto 5rem;background:var(--paper);border:1px solid var(--rule);border-radius:6px;padding:3.2rem 3.4rem}}
nav{{font-family:"IBM Plex Sans",sans-serif;font-size:.85rem;max-width:47rem;margin:1.2rem auto 0;padding:0 .4rem;display:flex;gap:1.4rem}}
nav a{{color:var(--accent)}}
.banner{{font-family:"IBM Plex Sans",sans-serif;font-size:.82rem;color:var(--muted);border:1px solid var(--rule);border-left:3px solid var(--accent);border-radius:0 5px 5px 0;padding:.6rem .9rem;margin:0 0 2rem;background:var(--bg)}}
h1{{font-size:1.9rem;font-weight:700;line-height:1.18;letter-spacing:-.01em;text-wrap:balance;margin:.2rem 0 1rem}}
.sheet h1:not(:first-of-type){{font-size:1.32rem;font-weight:600;margin:2.8rem 0 .8rem;border-top:1px solid var(--rule);padding-top:2.2rem}}
h2{{font-size:1.28rem;font-weight:600;margin:2.4rem 0 .7rem;text-wrap:balance}}
h3{{font-size:1.05rem;font-weight:600;margin:1.8rem 0 .5rem}}
p{{margin:.85rem 0}}
em{{font-style:italic}} strong{{font-weight:600}}
a{{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:2px}}
code{{font-family:"IBM Plex Mono",monospace;font-size:.8em;background:var(--code);padding:.06em .32em;border-radius:3px}}
hr{{border:0;border-top:1px solid var(--rule);margin:2.6rem 0}}
.tablewrap{{overflow-x:auto;margin:1.1rem 0}}
table{{border-collapse:collapse;font-family:"IBM Plex Sans",sans-serif;font-size:.82rem;font-variant-numeric:tabular-nums;width:100%}}
th,td{{border:1px solid var(--rule);padding:.4rem .55rem;text-align:left;vertical-align:top}}
th{{background:var(--bg);font-weight:600;color:var(--muted)}}
figure{{margin:1.6rem -1.2rem;padding:.7rem;border:1px solid var(--rule);border-radius:6px;background:var(--paper)}}
figure.wide{{margin:1.6rem -2.2rem}}
figure img{{width:100%;height:auto;display:block;border-radius:3px;background:#fff}}
figcaption{{font-family:"IBM Plex Sans",sans-serif;font-size:.82rem;color:var(--muted);margin-top:.55rem;line-height:1.45}}
blockquote{{margin:1rem 0;padding:.2rem 1rem;border-left:3px solid var(--rule);color:var(--muted)}}
@media (max-width:720px){{.sheet{{padding:1.6rem 1.1rem;margin-top:.8rem}} figure,figure.wide{{margin:1.4rem 0}}}}
@media print{{body{{background:#fff;font-size:11pt}} .sheet{{border:0;margin:0;max-width:100%;padding:0}} nav{{display:none}} figure,figure.wide{{margin:1rem 0;break-inside:avoid}} a{{color:inherit;text-decoration:none}}}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important;transition:none!important}}}}
</style></head><body>
<nav><a href="index.html">← CLIMB project page</a><a href="{other_href}">{other_label}</a><a href="https://github.com/linjiw/climb-feasibility-first">repository</a><span style="color:var(--muted)">print this page for a PDF</span></nav>
<div class="sheet">
<div class="banner">{banner}</div>
{body}
</div></body></html>"""

FIGS = {
    # anchor substring (in the markdown source) -> (asset, caption, wide?)
    "companion": [
        ("`reports/upstream_drafts/clip44_airborne_repro.png`",
         "assets/clip44_airborne_repro.png",
         "Figure 1 [measured] — the impossible descent: reference stick-frames (red panels: no contact available) and the torque-limited unsupported force pinned at ≈ body weight. tools/n1_knee_id.py → reports/N1_clip44_knee_id.json.", True),
        ("(script\n`f4_prevalence.py`",
         "assets/f4_prevalence.png",
         "Figure 2 [measured] — prevalence by category and source, AMASS→Unitree-G1 under one retargeter. reports/feasibility_all/feasibility.csv.", True),
        ("`reports/repair_census/summary.md`, sentinel present]: **65.8",
         "assets/f_census_repair.png",
         "Figure 3 [measured] — the repair census: two-thirds of flagged clips are a 3-second fix. reports/repair_census/summary.json.", False),
    ],
    "flagship": [
        ("**difficulty = feasibility × support × intrinsic.**",
         "assets/decomposition.svg",
         "Figure F1 — the decomposition spine: each factor has its own measurement and its own fix.", True),
        ("`reports/A7_attractor.json`) — grounding does not change *what* the sampler wants",
         "assets/f2_collapse.png",
         "Figure F2 [sealed ✓] — collapse and its cost: held-out survival (3 seeds, min–max band) and exposure concentration. reports/campaign/*.csv, reports/A5_coverage_dose.json.", True),
        ("lifting the legs instead of lowering the root.",
         "assets/f3_anatomy.png",
         "Figure F3 — anatomy of the attractor: (a) airborne reference frames [measured]; (b) unsupported wrench [measured]; (c) stratified-start deaths [measured]; (d) the sealed-negative physics gate at the same-solver floor [sealed ✗, kept].", True),
        ("pipeline × source property, not a difficulty gradient.",
         "assets/f4_prevalence.png",
         "Figure F4 [measured] — prevalence by category × source: 0.1 % → 100 % under one pipeline. reports/feasibility_all/.", True),
        ("**feasibility is the first feature family that transfers across policies**",
         "assets/f5_transfer.png",
         "Figure F5 — transfer lift: intrinsic vs +support [sealed null, kept] vs +feasibility [sealed ✓], against random-feature permutation baselines. reports/N_atlas_v21.json.", True),
    ],
}


def insert_figures(src, key):
    for anchor, asset, caption, wide in FIGS[key]:
        i = src.find(anchor)
        if i < 0:
            print(f"  WARN anchor not found ({key}): {anchor[:50]!r}")
            continue
        j = src.find("\n\n", i)
        j = len(src) if j < 0 else j
        cls = ' class="wide"' if wide else ""
        fig = f'\n\n<figure{cls}><img src="{asset}" alt="{caption.split("—")[0].strip()}"><figcaption>{caption}</figcaption></figure>\n\n'
        src = src[:j] + fig + src[j:]
    return src


def render(md_path, out_path, key, title, banner, other):
    src = open(R + md_path).read()
    src = insert_figures(src, key)
    body = markdown.markdown(src, extensions=["tables", "fenced_code", "sane_lists"])
    body = body.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    html = TPL.format(title=title, banner=banner, body=body, other_href=other[0], other_label=other[1])
    open(R + out_path, "w").write(html)
    print(f"rendered {out_path} ({len(html)//1024} KB)")


if __name__ == "__main__":
    render("paper/companion/companion_note_draft.md", "docs/companion.html", "companion",
           "Auditing Dynamic Feasibility of Retargeted Humanoid Motion Data",
           "Working draft v0.3 (companion note; arXiv target). Claim labels: sealed ✓ / sealed ✗ (kept) / "
           "measured / exploratory / pending 🕐. Artifact paths refer to the "
           "<a href='https://github.com/linjiw/climb-feasibility-first'>repository</a>; ground truth is "
           "<code>paper/RESULTS_LOG.md</code>. Author list pending.",
           ("flagship.html", "flagship draft →"))
    render("paper/flagship/DRAFT_full.md", "docs/flagship.html", "flagship",
           "CLIMB — Flagship Working Draft",
           "Working draft with slots (title not final; five candidates under review). Sections §8 (N3/N7/E3) and the "
           "P-SIGN slot in §9 are sealed-and-scheduled — they state predictions and fill dates and do no load-bearing "
           "work. The sealed record (pre-registration table) is included in full, including the failed gate, the "
           "withdrawn verdict, and the kept nulls.",
           ("companion.html", "companion note →"))
