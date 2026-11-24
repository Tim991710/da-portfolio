"""Единая витрина для дашборда: одна таблица вместо шести.

Данные уже посчитаны в mart_monthly_outlet и mart_plan_fact; здесь они
соединяются со справочниками и выгружаются в CSV, который грузится в Power BI
одним источником. Так модель не зависит от ручной сборки связей, а цифры
совпадают с витринами SQL.

Запуск:  python power_bi/make_dashboard_mart.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DB = BASE / "data" / "analytics.db"
OUT = BASE / "data" / "marts" / "dashboard_facts.csv"

SQL = """
SELECT
    m.month_start,
    d.year,
    d.month_name,
    d.year_month,
    m.outlet_code,
    o.outlet_name,
    o.city,
    m.revenue,
    m.foodcost,
    m.gross_profit,
    m.payroll,
    m.checks_cnt,
    m.avg_check,
    m.gross_margin_pct,
    m.payroll_pct,
    m.operating_profit_pct,
    f.revenue_plan,
    f.payroll_plan,
    f.revenue_dev,
    f.revenue_dev_pct,
    f.payroll_pp_dev,
    m.payroll_missing
FROM mart_monthly_outlet AS m
JOIN mart_plan_fact AS f
    ON f.month_start = m.month_start
   AND f.outlet_code = m.outlet_code
JOIN dim_outlet AS o ON o.outlet_code = m.outlet_code
JOIN dim_date AS d ON d.date_key = m.month_start
ORDER BY m.month_start, m.outlet_code
"""


def main() -> None:
    if not DB.exists():
        raise SystemExit("Нет data/analytics.db — сначала запусти python sql/build_db.py")

    con = sqlite3.connect(DB)
    frame = pd.read_sql(SQL, con)
    con.close()

    frame.to_csv(OUT, index=False, encoding="utf-8-sig")

    print(f"Строк: {len(frame)}")
    print(f"Точек: {frame['outlet_code'].nunique()}")
    print(f"Месяцев: {frame['month_start'].nunique()}")
    print(f"Колонок: {len(frame.columns)}")
    print(f"Пустой ФОТ в {int(frame['payroll_missing'].sum())} строке (T05, март 2026)")
    print(f"Выручка: {frame['revenue'].sum() / 1e6:.2f} млн ₽")
    print(f"Файл: {OUT}")


if __name__ == "__main__":
    main()
