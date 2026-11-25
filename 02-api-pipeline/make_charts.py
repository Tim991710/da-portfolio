"""Графики по выгрузке обращений — визуальная часть портфолио проекта 2.

Строит две картинки из тех же данных, которые грузятся в Power BI:
топ меток и динамику обращений с разделением на issues / pull request.

Запуск:  python make_charts.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parent
RAW = BASE / "data" / "raw" / "issues.csv"
OUT = BASE / "screenshots"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3})


def top_labels(df: pd.DataFrame, n: int = 10) -> pd.Series:
    series = df["labels"].fillna("").str.split(";").explode()
    series = series[series.astype(str).str.strip() != ""]
    return series.str.strip().value_counts().head(n)


def main() -> None:
    df = pd.read_csv(RAW, encoding="utf-8-sig")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["month"] = df["created_at"].dt.strftime("%Y-%m")

    # 1. Топ меток
    labels = top_labels(df)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(labels.index[::-1], labels.values[::-1], color="#2b6cb0")
    ax.set_title(f"Топ-{len(labels)} меток в открытых обращениях, {len(df)} записей")
    ax.set_xlabel("Обращений")
    for i, v in enumerate(labels.values[::-1]):
        ax.text(v + 3, i, str(v), va="center", fontsize=9)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "01-labels.png", dpi=150)
    plt.close(fig)

    # 2. Динамика: обращения и pull request'ы по месяцам
    by_month = (
        df.groupby(["month", "is_pull_request"]).size().unstack(fill_value=0).sort_index()
    )
    by_month = by_month.rename(columns={0: "Обращения", 1: "Pull request"})
    fig, ax = plt.subplots(figsize=(10, 5))
    for col, color in zip(by_month.columns, ["#2b6cb0", "#dd6b20"]):
        ax.plot(by_month.index, by_month[col], marker="o", markersize=3, label=col, color=color)
    ax.set_title("Открытые обращения по месяцам создания")
    ax.set_ylabel("Записей")
    ax.tick_params(axis="x", rotation=90, labelsize=8)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "02-monthly.png", dpi=150)
    plt.close(fig)

    print("Сохранено:")
    for f in sorted(OUT.glob("*.png")):
        print(f"  {f.name} — {f.stat().st_size // 1024} КБ")
    print(f"Топ-1 метка: {labels.index[0]} ({labels.iloc[0]})")


if __name__ == "__main__":
    main()
