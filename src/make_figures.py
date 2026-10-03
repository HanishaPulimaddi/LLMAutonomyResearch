"""Draw all report figures in one shared style, from existing results only.

    figures/exp_architectures.png          the three experimental architectures
    figures/accuracy_by_architecture.png   correct eligibility decisions and effective dates (from evaluation_summary.csv)
    figures/error_pattern_matrix.png       per-case, per-stage check results (from error_pattern_matrix.csv)

Usage:
    python src/make_figures.py
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, Patch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

# Shared style: serif type, black lines, greyscale fills.
GREY = "#d9d9d9"   # LLM step / first series
DARK = "#404040"   # failed check
THIN, HEAVY = 0.6, 1.6
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8.5,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "savefig.dpi": 300,
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
    "hatch.linewidth": 0.6,
})


def legend(ax, handles, anchor):
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=anchor, ncol=len(handles), frameon=False)


# ---------------------------------------------------------------- architectures
BOX_H = 0.62
COLS = {"input": (1.0, 1.6), "llm": (3.45, 1.9), "code": (6.3, 2.4), "output": (9.05, 1.7)}
ARCH_ROWS = [
    ("A", "LLM only", "Profile + rule", "LLM:\ndecide", None, "Decision"),
    ("B", "LLM + validation", "Profile + rule", "LLM:\ndecide (JSON)", "Schema\nvalidation", "Decision"),
    ("C", "LLM extraction + rules", "Profile only", "LLM:\nextract facts", "Schema validation +\ndeterministic rules",
     "Decision +\nrule trace"),
]


def _box(ax, col, y, text, fill, lw):
    cx, w = COLS[col]
    ax.add_patch(Rectangle((cx - w / 2, y - BOX_H / 2), w, BOX_H, facecolor=fill, edgecolor="black", linewidth=lw))
    ax.text(cx, y, text, ha="center", va="center")


def _arrow(ax, x0, x1, y, label=None):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=10, color="black", linewidth=0.9))
    if label:
        ax.text((x0 + x1) / 2, y + 0.1, label, ha="center", va="bottom", fontsize=7.5, style="italic")


def _edge(col, side):
    cx, w = COLS[col]
    return cx + w / 2 if side == "right" else cx - w / 2


def architectures():
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    for i, (key, name, inp, llm, code, out) in enumerate(ARCH_ROWS):
        y = 2.6 - i * 1.15
        ax.text(-0.05, y + 0.1, f"({key})", ha="right", va="center", fontsize=10, fontweight="bold")
        ax.text(-0.05, y - 0.14, name, ha="right", va="center", fontsize=7.5)
        _box(ax, "input", y, inp, "white", THIN)
        _box(ax, "llm", y, llm, GREY, 0.8)
        _box(ax, "output", y, out, "white", THIN)
        _arrow(ax, _edge("input", "right"), _edge("llm", "left"), y)
        if code:
            _box(ax, "code", y, code, "white", HEAVY)
            _arrow(ax, _edge("llm", "right"), _edge("code", "left"), y, "JSON" if key == "B" else "facts")
            _arrow(ax, _edge("code", "right"), _edge("output", "left"), y)
        else:
            _arrow(ax, _edge("llm", "right"), _edge("output", "left"), y, "free text + DECISION / DATE lines")
    legend(ax, [Patch(facecolor=GREY, edgecolor="black", linewidth=0.8, label="LLM step"),
                Patch(facecolor="white", edgecolor="black", linewidth=HEAVY, label="Deterministic software step"),
                Patch(facecolor="white", edgecolor="black", linewidth=THIN, label="Input / output")], (0.5, 0.0))
    ax.set_xlim(-1.9, 10.0)
    ax.set_ylim(-0.1, 3.05)
    ax.axis("off")
    return fig


# ---------------------------------------------------------------- accuracy
def accuracy():
    summary = {s["architecture"]: s for s in csv.DictReader((RESULTS / "evaluation_summary.csv").open(encoding="utf-8"))}
    archs = ["A", "B", "C"]
    labels = ["(A) LLM only", "(B) LLM + validation", "(C) LLM extraction\n+ rules"]
    n = int(summary["A"]["n"])
    series = [("Eligibility decision correct", "eligibility_correct", dict(facecolor=GREY)),
              ("Effective date correct", "effective_date_correct", dict(facecolor="white", hatch="////"))]

    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    width = 0.34
    x = np.arange(len(archs))
    for offset, (label, key, style) in zip((-width / 2, width / 2), series):
        values = [int(summary[a][key]) for a in archs]
        bars = ax.bar(x + offset, values, width, edgecolor="black", linewidth=0.8, label=label, **style)
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3, f"{v}/{n}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x, labels)
    ax.set_ylim(0, n + 2)
    ax.set_yticks(range(0, n + 1, 5))
    ax.set_ylabel(f"Cases correct (of {n})")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", length=0)
    legend(ax, ax.get_legend_handles_labels()[0], (0.5, -0.2))
    return fig


# ---------------------------------------------------------------- error matrix
MATRIX_GROUPS = [
    ("(A) LLM only", [("A_eligibility", "Eligibility"), ("A_date", "Effective date")]),
    ("(B) LLM + validation", [("B_schema_valid", "Schema valid"), ("B_claimable_months", "Claimable months"),
                              ("B_eligibility", "Eligibility"), ("B_date", "Effective date")]),
    ("(C) LLM extraction + rules", [("C_schema_valid", "Schema valid"), ("C_facts_extracted", "Facts extracted"),
                                    ("C_rule_application", "Rule step"), ("C_eligibility", "Eligibility"),
                                    ("C_date", "Effective date")]),
]


def error_matrix():
    rows = list(csv.DictReader((RESULTS / "error_pattern_matrix.csv").open(encoding="utf-8")))
    columns = [key for _, cols in MATRIX_GROUPS for key, _ in cols]
    labels = [label for _, cols in MATRIX_GROUPS for _, label in cols]
    matrix = np.array([[0 if row[key] == "True" else 1 for key in columns] for row in rows])  # 1 = check failed

    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    ax.imshow(matrix, cmap=ListedColormap(["white", DARK]), vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(-0.5, len(columns)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(rows)), minor=True)
    ax.grid(which="minor", color="#bdbdbd", linewidth=0.5)
    ax.tick_params(which="both", length=0)
    ax.set_xticks(range(len(columns)), labels, rotation=90)
    ax.set_yticks(range(len(rows)), [f"{r['applicant_id']}  {r['case_category']}" for r in rows])

    start = 0
    for name, cols in MATRIX_GROUPS:
        end = start + len(cols)
        if start:
            ax.axvline(start - 0.5, color="black", linewidth=HEAVY)
        ax.text((start + end - 1) / 2, -1.0, name, ha="center", va="bottom", fontweight="bold")
        start = end
    for spine in ax.spines.values():
        spine.set_linewidth(HEAVY)

    legend(ax, [Patch(facecolor="white", edgecolor="black", linewidth=THIN, label="Check passed"),
                Patch(facecolor=DARK, edgecolor="black", linewidth=THIN, label="Check failed")], (0.5, -0.27))
    return fig


def main():
    for name, draw in (("exp_architectures.png", architectures),
                       ("accuracy_by_architecture.png", accuracy),
                       ("error_pattern_matrix.png", error_matrix)):
        fig = draw()
        fig.savefig(FIGURES / name)
        plt.close(fig)
        print(f"Saved figures/{name}")


if __name__ == "__main__":
    main()
