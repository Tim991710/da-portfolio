-- postgres_port.sql
-- Порт ключевых запросов под PostgreSQL 15+.
-- Не прогонялся на сервере: в проекте используется SQLite, чтобы запускаться
-- без установки СУБД. Отличия от SQLite-версии — типы, date_trunc, DISTINCT ON.

CREATE TABLE dim_date (
    date_key    date PRIMARY KEY,
    year        int  NOT NULL,
    quarter     int  NOT NULL,
    month       int  NOT NULL,
    month_start date NOT NULL,
    month_name  text NOT NULL,
    year_month  text NOT NULL,
    weekday     int  NOT NULL,
    is_weekend  int  NOT NULL
);

CREATE TABLE dim_outlet (
    outlet_code text PRIMARY KEY,
    outlet_name text NOT NULL,
    city        text NOT NULL,
    open_date   date NOT NULL,
    format      text
);

CREATE TABLE dim_dish (
    dish_code text PRIMARY KEY,
    dish_name text NOT NULL,
    category  text NOT NULL
);

CREATE TABLE fact_sales (
    order_id      text NOT NULL,
    order_line_id int  NOT NULL,
    date_key      date NOT NULL,
    outlet_code   text NOT NULL,
    dish_code     text NOT NULL,
    qty           int  NOT NULL,
    price         numeric(12,2) NOT NULL,
    discount_sum  numeric(12,2) NOT NULL,
    amount_gross  numeric(12,2) NOT NULL,
    amount_paid   numeric(12,2) NOT NULL,
    cost_sum      numeric(12,2) NOT NULL,
    PRIMARY KEY (order_id, order_line_id)
);

CREATE TABLE fact_payroll (
    month_start    date NOT NULL,
    outlet_code    text NOT NULL,
    position_group text NOT NULL,
    hours          numeric(10,2) NOT NULL,
    accrual        numeric(14,2) NOT NULL,
    PRIMARY KEY (month_start, outlet_code, position_group)
);

CREATE TABLE fact_plan (
    month_start  date NOT NULL,
    outlet_code text NOT NULL,
    revenue_plan numeric(14,2) NOT NULL,
    payroll_plan numeric(14,2) NOT NULL,
    PRIMARY KEY (month_start, outlet_code)
);

-- fact_sales: дедупликация и правила качества.
-- DISTINCT ON удобнее для «оставить одну строку на ключ» и для отладки дублей:
--   SELECT order_id, order_line_id, count(*) FROM raw_sales
--   GROUP BY 1, 2 HAVING count(*) > 1;
INSERT INTO fact_sales
SELECT DISTINCT ON (order_id, order_line_id)
       order_id,
       order_line_id,
       order_datetime::date AS date_key,
       outlet_code,
       CASE WHEN dish_code = 'D15N' THEN 'D15' ELSE dish_code END AS dish_code,
       qty, price, discount_sum, amount_gross, amount_paid, cost_sum
FROM raw_sales
WHERE order_status = 'Closed'
  AND NOT (qty > 0 AND amount_paid < 0)
ORDER BY order_id, order_line_id;

-- Витрина «месяц x точка»: date_trunc вместо substr.
INSERT INTO mart_monthly_outlet
SELECT
    date_trunc('month', s.date_key)::date AS month_start,
    s.outlet_code,
    round(s.revenue, 2),
    round(s.foodcost, 2),
    round(s.revenue - s.foodcost, 2),
    round(p.payroll, 2),
    round((s.revenue - s.foodcost) / s.revenue * 100, 2)          AS gross_margin_pct,
    round(p.payroll / s.revenue * 100, 2)                          AS payroll_pct,
    round((s.revenue - s.foodcost - p.payroll) / s.revenue * 100, 2) AS operating_profit_pct,
    s.checks_cnt,
    round(s.revenue / s.checks_cnt, 0)                             AS avg_check,
    CASE WHEN p.payroll IS NULL THEN 1 ELSE 0 END                  AS payroll_missing
FROM (
    SELECT date_trunc('month', date_key)::date AS m,
           outlet_code,
           sum(amount_paid) AS revenue,
           sum(cost_sum)    AS foodcost,
           count(DISTINCT order_id) AS checks_cnt
    FROM fact_sales
    GROUP BY 1, 2
) AS s
JOIN (
    SELECT date_trunc('month', date_key)::date AS m,
           outlet_code, sum(amount_paid) AS revenue
    FROM fact_sales GROUP BY 1, 2
) AS x ON x.m = s.m AND x.outlet_code = s.outlet_code
LEFT JOIN (
    SELECT month_start, outlet_code, sum(accrual) AS payroll
    FROM fact_payroll
    GROUP BY 1, 2
) AS p ON p.month_start = s.m AND p.outlet_code = s.outlet_code
WHERE s.revenue > 0;

-- Сверка выручки: сырьё против витрины (в PostgreSQL выполняется в одной
-- транзакции после загрузки landing-таблицы).
WITH raw AS (
    SELECT sum(amount_paid) AS amount
    FROM (SELECT DISTINCT order_id, order_line_id, amount_paid FROM raw_sales) AS d
), mart AS (
    SELECT sum(amount_paid) AS amount FROM fact_sales
)
SELECT raw.amount AS raw_amount,
       mart.amount AS mart_amount,
       round(raw.amount - mart.amount, 2) AS diff
FROM raw, mart;

-- Оконные функции: доля точки в выручке месяца и накопленный итог.
SELECT month_start, outlet_code, revenue,
       round(revenue / sum(revenue) OVER (PARTITION BY month_start) * 100, 2) AS share_in_month_pct,
       sum(revenue) OVER (PARTITION BY outlet_code ORDER BY month_start) AS revenue_running_total,
       revenue - lag(revenue) OVER (PARTITION BY outlet_code ORDER BY month_start) AS mom_delta
FROM mart_monthly_outlet
ORDER BY outlet_code, month_start;
