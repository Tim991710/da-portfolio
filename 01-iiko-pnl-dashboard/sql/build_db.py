"""Загрузка CSV -> SQLite -> витрины -> проверки -> экспорт для Power BI.

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
DB = BASE / "data" / "analytics.db"
MARTS.mkdir(parents=True, exist_ok=True)

MONTHS_RU = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]


def load_raw(con: sqlite3.Connection) -> None:
    # Продажи: iiko отдаёт windows-1251, разделитель ";" и десятичную запятую
    sales = pd.read_csv(
        RAW / "iiko_olap_sales.csv",
        sep=";",
        encoding="cp1251",
        decimal=",",
        dtype={
            "order_id": str,
            "order_datetime": str,
            "outlet_code": str,
            "dish_code": str,
            "dish_name": str,
            "category": str,
            "order_status": str,
        },
    )
    sales.to_sql("raw_sales", con, if_exists="replace", index=False)

    pd.read_csv(RAW / "outlets.csv", dtype={"outlet_code": str}).to_sql(
        "raw_outlets", con, if_exists="replace", index=False
    )
    pd.read_csv(RAW / "dish_cost_techcards.csv", dtype={"dish_code": str}).to_sql(
        "raw_dish_cost", con, if_exists="replace", index=False
    )
    pd.read_csv(RAW / "iiko_payroll.csv", dtype={"outlet_code": str}).to_sql(
        "raw_payroll", con, if_exists="replace", index=False
    )
    pd.read_csv(
        RAW / "plan_revenue_payroll.csv", dtype={"outlet_code": str}
    ).to_sql("raw_plan", con, if_exists="replace", index=False)


def build_dim_date(con: sqlite3.Connection) -> None:
    days = pd.date_range("2024-11-01", "2026-10-31", freq="D")
    frame = pd.DataFrame(
        {
            "date_key": days.strftime("%Y-%m-%d"),
            "year": days.year,
            "quarter": days.quarter,
            "month": days.month,
            "month_start": days.to_period("M").to_timestamp().strftime("%Y-%m-%d"),
            "month_name": [MONTHS_RU[m - 1] for m in days.month],
            "year_month": days.strftime("%Y-%m"),
            "weekday": days.weekday + 1,
            "is_weekend": (days.weekday >= 5).astype(int),
        }
    )
    frame.to_sql("dim_date", con, if_exists="append", index=False)


def run_sql(con: sqlite3.Connection, name: str) -> None:
    con.executescript((SQL / name).read_text(encoding="utf-8"))
    con.commit()


def export_marts(con: sqlite3.Connection) -> None:
    for table in [
        "dim_date", "dim_outlet", "dim_dish", "fact_sales",
        "fact_payroll", "fact_plan", "mart_monthly_outlet", "mart_plan_fact",
        "log_data_quality", "quarantine_sales",
    ]:
        df = pd.read_sql(f"SELECT * FROM {table}", con)
        df.to_csv(MARTS / f"{table}.csv", index=False, encoding="utf-8-sig")
        print(f"  экспорт {table}: {len(df):,} строк".replace(",", " "))


def main() -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 90)

    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)

    print("1. Загрузка сырья в landing-таблицы")
    load_raw(con)
    print("2. Создание схемы витрин")
    run_sql(con, "01_schema.sql")
    build_dim_date(con)
    print("3. Построение витрин")
    run_sql(con, "02_marts.sql")
    print("4. Проверки качества")
    run_sql(con, "03_checks.sql")
    print("5. Экспорт мартов для Power BI")
    export_marts(con)

    checks = pd.read_sql(
        "SELECT check_name, metric, status FROM log_data_quality", con
    )
    for _, r in checks.iterrows():
        print(f"  [{r['status']}] {r['check_name']}: {r['metric']}")

    print("\n--- Сводка по сети ---")
    summary = pd.read_sql(
        """
        SELECT ROUND(SUM(revenue)/1e6, 2) AS revenue_mln,
               ROUND(SUM(foodcost)/SUM(revenue)*100, 2) AS foodcost_pct,
               ROUND(SUM(payroll)/SUM(revenue)*100, 2) AS payroll_pct,
               ROUND((SUM(revenue)-SUM(foodcost)-SUM(payroll))/SUM(revenue)*100, 2) AS op_margin_pct
        FROM mart_monthly_outlet
        """,
        con,
    )
    print(summary.to_string(index=False))

    print("\n--- Точки: итог за 24 месяца ---")
    print(
        pd.read_sql(
            """
            SELECT outlet_code,
                   ROUND(SUM(revenue)/1e6, 2) AS revenue_mln,
                   ROUND(SUM(revenue)/SUM(checks_cnt), 0) AS avg_check,
                   ROUND(SUM(foodcost)/SUM(revenue)*100, 1) AS foodcost_pct,
                   ROUND(SUM(payroll)/SUM(revenue)*100, 1) AS payroll_pct,
                   ROUND((SUM(revenue)-SUM(foodcost)-SUM(payroll))/SUM(revenue)*100, 1) AS op_margin_pct,
                   SUM(payroll_missing) AS months_without_payroll
            FROM mart_monthly_outlet
            GROUP BY outlet_code
            ORDER BY revenue_mln DESC
            """,
            con,
        ).to_string(index=False)
    )

    print("\n--- Топ-5 отклонений план-факт по выручке ---")
    print(
        pd.read_sql(
            """
            SELECT month_start, outlet_code, revenue_plan, revenue_fact, revenue_dev_pct
            FROM mart_plan_fact
            ORDER BY revenue_dev_pct ASC
            LIMIT 5
            """,
            con,
        ).to_string(index=False)
    )

    print("\n--- Топ-5 отклонений доли ФОТ (п.п.) ---")
    print(
        pd.read_sql(
            """
            SELECT month_start, outlet_code, payroll_pct_plan, payroll_pct_fact, payroll_pp_dev
            FROM mart_plan_fact
            WHERE payroll_pct_fact IS NOT NULL
            ORDER BY payroll_pp_dev DESC
            LIMIT 5
            """,
            con,
        ).to_string(index=False)
    )

    print("\n--- T03: сравнение периодов ---")
    print(
        pd.read_sql(
            """
            SELECT substr(month_start,1,4) AS year,
                   ROUND(SUM(revenue)/1e6, 2) AS revenue_mln,
                   ROUND(SUM(revenue)/SUM(checks_cnt), 0) AS avg_check
            FROM mart_monthly_outlet
            WHERE outlet_code = 'T03'
            GROUP BY 1
            """,
            con,
        ).to_string(index=False)
    )

    con.close()
    print(f"\nГотово: {DB}")


if __name__ == "__main__":
    main()
