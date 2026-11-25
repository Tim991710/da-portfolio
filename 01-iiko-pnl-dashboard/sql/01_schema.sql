-- 01_schema.sql
-- Слой витрин (analytics.db). Landing-таблицы raw_* создаются загрузчиком.
-- Целевая СУБД для продакшена — PostgreSQL; здесь SQLite, чтобы проект
-- запускался одной командой без установки сервера.

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS fact_payroll;
DROP TABLE IF EXISTS fact_plan;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_outlet;
DROP TABLE IF EXISTS dim_dish;
DROP TABLE IF EXISTS mart_monthly_outlet;
DROP TABLE IF EXISTS mart_plan_fact;
DROP TABLE IF EXISTS quarantine_sales;
DROP TABLE IF EXISTS log_data_quality;

CREATE TABLE dim_outlet (
    outlet_code TEXT PRIMARY KEY,
    outlet_name TEXT NOT NULL,
    city        TEXT NOT NULL,
    open_date   TEXT NOT NULL,
    format      TEXT
);

CREATE TABLE dim_dish (
    dish_code TEXT PRIMARY KEY,
    dish_name TEXT NOT NULL,
    category  TEXT NOT NULL
);

CREATE TABLE dim_date (
    date_key    TEXT PRIMARY KEY,   -- YYYY-MM-DD
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_start TEXT NOT NULL,
    month_name  TEXT NOT NULL,
    year_month  TEXT NOT NULL,      -- 2026-03
    weekday     INTEGER NOT NULL,
    is_weekend  INTEGER NOT NULL
);

CREATE TABLE fact_sales (
    order_id      TEXT NOT NULL,
    order_line_id INTEGER NOT NULL,
    date_key      TEXT NOT NULL,
    order_hour    INTEGER NOT NULL,
    order_type    TEXT NOT NULL,
    payment_type  TEXT NOT NULL,
    guest_count   INTEGER NOT NULL,
    outlet_code   TEXT NOT NULL,
    dish_code     TEXT NOT NULL,
    qty           INTEGER NOT NULL,
    price         REAL NOT NULL,
    discount_type TEXT NOT NULL,
    discount_sum  REAL NOT NULL,
    amount_gross  REAL NOT NULL,
    amount_paid   REAL NOT NULL,     -- выручка: сумма после скидки
    cost_sum      REAL NOT NULL,
    PRIMARY KEY (order_id, order_line_id)
);

-- Акты списания: брак, порча, истечение срока, дегустация
CREATE TABLE fact_writeoff (
    doc_number    TEXT PRIMARY KEY,
    writeoff_date TEXT NOT NULL,
    outlet_code   TEXT NOT NULL,
    dish_code     TEXT NOT NULL,
    category      TEXT NOT NULL,
    qty           INTEGER NOT NULL,
    reason        TEXT NOT NULL,
    cost_sum      REAL NOT NULL
);

CREATE TABLE fact_payroll (
    month_start    TEXT NOT NULL,
    outlet_code    TEXT NOT NULL,
    position_group TEXT NOT NULL,
    hours          REAL NOT NULL,
    accrual        REAL NOT NULL,    -- начисленный ФОТ, ₽
    PRIMARY KEY (month_start, outlet_code, position_group)
);

CREATE TABLE fact_plan (
    month_start  TEXT NOT NULL,
    outlet_code TEXT NOT NULL,
    revenue_plan REAL NOT NULL,
    payroll_plan REAL NOT NULL,
    PRIMARY KEY (month_start, outlet_code)
);

-- Строки, не прошедшие правила качества
CREATE TABLE quarantine_sales (
    order_id      TEXT NOT NULL,
    order_line_id INTEGER NOT NULL,
    outlet_code   TEXT NOT NULL,
    amount_paid   REAL NOT NULL,
    reason        TEXT NOT NULL
);

CREATE TABLE mart_monthly_outlet (
    month_start         TEXT NOT NULL,
    outlet_code         TEXT NOT NULL,
    revenue             REAL NOT NULL,
    foodcost            REAL NOT NULL,
    gross_profit        REAL NOT NULL,
    payroll             REAL,
    gross_margin_pct    REAL,
    payroll_pct         REAL,
    operating_profit_pct REAL,
    writeoff_sum        REAL NOT NULL DEFAULT 0,
    writeoff_pct        REAL,
    op_margin_wr_pct    REAL,
    checks_cnt          INTEGER NOT NULL,
    avg_check           REAL,
    payroll_missing     INTEGER NOT NULL,
    PRIMARY KEY (month_start, outlet_code)
);

CREATE TABLE mart_plan_fact (
    month_start      TEXT NOT NULL,
    outlet_code      TEXT NOT NULL,
    revenue_plan     REAL NOT NULL,
    revenue_fact     REAL NOT NULL,
    revenue_dev      REAL,
    revenue_dev_pct  REAL,
    payroll_plan     REAL NOT NULL,
    payroll_fact     REAL,
    payroll_pct_plan REAL,
    payroll_pct_fact REAL,
    payroll_pp_dev   REAL,
    PRIMARY KEY (month_start, outlet_code)
);

CREATE TABLE log_data_quality (
    check_name TEXT NOT NULL,
    metric     TEXT NOT NULL,
    expected   TEXT,
    actual     TEXT,
    status     TEXT NOT NULL
);
