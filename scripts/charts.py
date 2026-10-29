"""The article's chart from aggregate.json: cost per 1,000 successful pages ($19 plans), by page type.
Bars carry their values, so there is no y-axis text or grid. Rendered at 2x for high-density screens,
on a narrow canvas so the labels stay readable at phone width (about 11 px at 343 px wide)."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for path in ("/System/Library/Fonts/HelveticaNeue.ttc",):
    try:
        font_manager.fontManager.addfont(path)
        plt.rcParams["font.family"] = "Helvetica Neue"
    except Exception:
        pass

A = json.load(open("results/aggregate.json"))
SB, FC, INK, MUTED, BASE, SURF = "#eda100", "#2a78d6", "#1f2328", "#57606a", "#d6d5cf", "#fcfcfb"
APIS = (("sb", SB, "ScrapingBee"), ("fc", FC, "Firecrawl"))


def bars(types, key, fmt, title, fname):
    fig, ax = plt.subplots(figsize=(5, 3.4), dpi=320, facecolor=SURF)
    ax.set_facecolor(SURF)
    x = range(len(types))
    w = 0.36
    top = max(A[f"{t}|{api}"][key] for t, _ in types for api, _, _ in APIS)
    for i, (api, col, name) in enumerate(APIS):
        vals = [A[f"{t}|{api}"][key] for t, _ in types]
        rects = ax.bar([j + (i - 0.5) * (w + 0.02) for j in x], vals, w, color=col, label=name, zorder=3)
        for r, v in zip(rects, vals):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + top * 0.015, fmt(v),
                    ha="center", va="bottom", fontsize=11, color=INK)
    ax.set_xticks(list(x), [n for _, n in types], color=INK, fontsize=12)
    ax.set_title(title, color=INK, fontsize=13, loc="left", pad=14)
    ax.set_ylim(0, top * 1.12)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=12)
    fig.tight_layout()
    fig.savefig(fname, facecolor=SURF)
    print("wrote", fname)


bars([("static", "Static"), ("js", "JavaScript"), ("protected", "Protected"), ("pdf", "PDF")], "usd_per_1k_ok",
     lambda v: f"${v:.2f}", "Cost per 1,000 successful pages, $19 plans",
     "results/scrapingbee-vs-firecrawl-cost-per-1000-successful-pages.png")
