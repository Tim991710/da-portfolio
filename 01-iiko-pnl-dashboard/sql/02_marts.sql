-- 02_marts.sql
-- Слой витрин: landing (raw_*) -> dim/fact -> марты для BI.
-- Правила расчёта зафиксированы здесь и дублируются в README.

-- ---------- Справочники ----------

-- Блюда: коды берём из фактов продаж, названия — актуальные.
-- D15N — переименование блюда с 01.05.2026, сводим к исходному D15.
INSERT INTO dim_dish (dish_code, dish_name, category)
SELECT dish_code, MAX(dish_name), MAX(category)
FROM raw_sales
WHERE dish_code NOT IN ('D15', 'D15N')
GROUP BY dish_code;

INSERT INTO dim_dish (dish_code, dish_name, category)
SELECT 'D15', 'Морс клюквенный', 'Напитки'
WHERE EXISTS (SELECT 1 FROM raw_sales WHERE dish_code = 'D15N');

INSERT INTO dim_outlet (outlet_code, outlet_name, city, open_date, format)
SELECT DISTINCT outlet_code, outlet_name, city, open_date, format
FROM raw_outlets;

-- ---------- Карантин ----------

-- Правило: строка с положительным количеством и отрицательной суммой после
-- скидки — техническая ошибка ввода (скидка больше суммы). В выручку не идёт.
INSERT INTO quarantine_sales (order_id, order_line_id, outlet_code, amount_paid, reason)
SELECT DISTINCT order_id, order_line_id, outlet_code, amount_paid,
       'скидка больше суммы заказа'
FROM raw_sales
WHERE order_status = 'Closed' AND qty > 0 AND amount_paid < 0;

-- ---------- Факты ----------

-- DISTINCT убирает повторы повторной выгрузки; Deleted-заказы исключены.
INSERT INTO fact_sales (
    order_id, order_line_id, date_key, order_hour, order_type, payment_type,
    guest_count, outlet_code, dish_code, qty, price, discount_type,
    discount_sum, amount_gross, amount_paid, cost_sum
)
SELECT DISTINCT
    order_id,
    order_line_id,
    substr(order_datetime, 1, 10) AS date_key,
    order_hour, order_type, payment_type, guest_count,
    outlet_code,
    CASE WHEN dish_code = 'D15N' THEN 'D15' ELSE dish_code END AS dish_code,
    qty, price, discount_type, discount_sum, amount_gross, amount_paid, cost_sum
FROM raw_sales
WHERE order_status = 'Closed'
  AND NOT (qty > 0 AND amount_paid < 0);

INSERT INTO fact_payroll (month_start, outlet_code, position_group, hours, accrual)
SELECT DISTINCT month_start, outlet_code, position_group, hours, accrual
FROM raw_payroll;

INSERT INTO fact_plan (month_start, outlet_code, revenue_plan, payroll_plan)
SELECT DISTINCT month_start, outlet_code, revenue_plan, payroll_plan
FROM raw_plan;

-- Списания: отрицательные количества — ошибка ввода, в витрину не идут
INSERT INTO fact_writeoff (
    doc_number, writeoff_date, outlet_code, dish_code, category, qty, reason, cost_sum
)
SELECT DISTINCT
    doc_number,
    writeoff_date,
    outlet_code,
    CASE WHEN dish_code = 'D15N' THEN 'D15' ELSE dish_code END AS dish_code,
    category, qty, reason, cost_sum
FROM raw_writeoffs
WHERE qty > 0;

-- ---------- Марты ----------

-- Месяц x точка: выручка, food cost, ФОТ, маржинальность, рентабельность.
-- payroll_missing = 1, если по точке нет строк ФОТ за месяц: показатель
-- остаётся NULL, а не 0, чтобы не занижать долю ФОТ.
INSERT INTO mart_monthly_outlet (
    month_start, outlet_code, revenue, foodcost, gross_profit, payroll,
    gross_margin_pct, payroll_pct, operating_profit_pct,
    writeoff_sum, writeoff_pct, op_margin_wr_pct,
    checks_cnt, avg_check, payroll_missing
)
SELECT
    s.month_start,
    s.outlet_code,
    ROUND(s.revenue, 2),
    ROUND(s.foodcost, 2),
    ROUND(s.revenue - s.foodcost, 2),
    ROUND(p.payroll, 2),
    ROUND((s.revenue - s.foodcost) / s.revenue * 100, 2),
    ROUND(p.payroll / s.revenue * 100, 2),
    ROUND((s.revenue - s.foodcost - p.payroll) / s.revenue * 100, 2),
    ROUND(COALESCE(w.wr, 0), 2),
    ROUND(COALESCE(w.wr, 0) / s.revenue * 100, 2),
    ROUND((s.revenue - s.foodcost - p.payroll - COALESCE(w.wr, 0)) / s.revenue * 100, 2),
    s.checks_cnt,
    ROUND(s.revenue / s.checks_cnt, 0),
    CASE WHEN p.payroll IS NULL THEN 1 ELSE 0 END
FROM (
    SELECT
        substr(date_key, 1, 7) || '-01' AS month_start,
        outlet_code,
        SUM(amount_paid) AS revenue,
        SUM(cost_sum)   AS foodcost,
        COUNT(DISTINCT order_id) AS checks_cnt
    FROM fact_sales
    GROUP BY 1, 2
) AS s
LEFT JOIN (
    SELECT month_start, outlet_code, SUM(accrual) AS payroll
    FROM fact_payroll
    GROUP BY 1, 2
) AS p
    ON p.month_start = s.month_start
   AND p.outlet_code = s.outlet_code
LEFT JOIN (
    SELECT
        substr(writeoff_date, 1, 7) || '-01' AS month_start,
        outlet_code,
        SUM(cost_sum) AS wr
    FROM fact_writeoff
    GROUP BY 1, 2
) AS w
    ON w.month_start = s.month_start
   AND w.outlet_code = s.outlet_code
WHERE s.revenue > 0;

-- План-факт: отклонения в рублях, процентах и п.п. по доле ФОТ.
INSERT INTO mart_plan_fact (
    month_start, outlet_code, revenue_plan, revenue_fact, revenue_dev,
    revenue_dev_pct, payroll_plan, payroll_fact, payroll_pct_plan,
    payroll_pct_fact, payroll_pp_dev
)
SELECT
    m.month_start,
    m.outlet_code,
    pl.revenue_plan,
    m.revenue,
    ROUND(m.revenue - pl.revenue_plan, 2),
    ROUND((m.revenue - pl.revenue_plan) / pl.revenue_plan * 100, 2),
    pl.payroll_plan,
    m.payroll,
    ROUND(pl.payroll_plan / pl.revenue_plan * 100, 2),
    ROUND(m.payroll / m.revenue * 100, 2),
    ROUND(m.payroll / m.revenue * 100 - pl.payroll_plan / pl.revenue_plan * 100, 2)
FROM mart_monthly_outlet AS m
JOIN fact_plan AS pl
    ON pl.month_start = m.month_start
   AND pl.outlet_code = m.outlet_code;
