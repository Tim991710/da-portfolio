"""Загрузка результатов API-выгрузки в SQLite: витрины и проверки.

Запуск:  python sql/build_db.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
MARTS = BASE / "data" / "marts"
SQL = BASE / "sql"
DB = BASE / "data" / "api_pipeline.db"

MARTS.mkdir(parents=True, exist_ok=True)


def run_sql(con: sqlite3.Connection, name: str) -> None:
    con.executescript((SQL / name).read_text(encoding="utf-8"))
    con.commit()


def main() -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 60)

    if DB.exists():
        DB.unlink()

    issues = pd.read_csv(RAW / "issues.csv", encoding="utf-8-sig")
    fetch_log = pd.read_csv(RAW / "fetch_log.csv", encoding="utf-8-sig")
    completeness = pd.read_csv(RAW / "completeness.csv", encoding="utf-8-sig")
    # "check" — зарезервированное слово в SQLite
    completeness = completeness.rename(columns={"check": "check_name"})

    con = sqlite3.connect(DB)
    issues.to_sql("raw_issue", con, if_exists="replace", index=False)
    fetch_log.to_sql("raw_fetch_log", con, if_exists="replace", index=False)
    completeness.to_sql("raw_completeness", con, if_exists="replace", index=False)
    print(f"Загружено: обращений {len(issues)}, страниц в логе {len(fetch_log)}")

    run_sql(con, "01_schema.sql")
    run_sql(con, "02_marts.sql")
    run_sql(con, "03_checks.sql")

    for table in ["fact_issue", "mart_month", "mart_label", "mart_author", "log_data_quality"]:
        table_df = pd.read_sql(f"SELECT * FROM {table}", con)
        table_df.to_csv(MARTS / f"{table}.csv", index=False, encoding="utf-8-sig")
        print(f"  экспорт {table}: {len(table_df)} строк")

    checks = pd.read_sql(
        "SELECT check_name, actual, status FROM log_data_quality", con
    )
    print("\nПроверки:")
    for _, r in checks.iterrows():
        print(f"  [{r['status']}] {r['check_name']}: {r['actual']}")

    print("\nТоп-10 меток:")
    print(
        pd.read_sql(
            "SELECT label, issues_cnt FROM mart_label ORDER BY issues_cnt DESC LIMIT 10", con
        ).to_string(index=False)
    )

    print("\nПо месяцам (последние 8):")
    print(
        pd.read_sql(
            "SELECT * FROM mart_month ORDER BY month DESC LIMIT 8", con
        ).to_string(index=False)
    )

    print("\nДоля ботов среди авторов:")
    print(
        pd.read_sql(
            """
            SELECT SUM(CASE WHEN is_bot = 1 THEN issues_cnt ELSE 0 END) AS bot_issues,
                   SUM(issues_cnt) AS total,
                   ROUND(SUM(CASE WHEN is_bot = 1 THEN issues_cnt ELSE 0 END) * 100.0
                         / SUM(issues_cnt), 1) AS bot_pct
            FROM mart_author
            """,
            con,
        ).to_string(index=False)
    )

    failures = (checks["status"] == "FAIL").sum()
    con.close()
    print(f"\nПроваленных проверок: {failures}")
    if failures:
        raise SystemExit("Есть FAIL — данные неполные, отчёт публиковать нельзя.")


if __name__ == "__main__":
    main()
