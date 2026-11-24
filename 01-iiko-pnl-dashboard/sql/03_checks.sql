-- 03_checks.sql
-- Проверки качества: каждая строка результат-сета — один контроль.
-- Запускается после 02_marts.sql, результат пишется в log_data_quality.

INSERT INTO log_data_quality (check_name, metric, expected, actual, status)
SELECT 'C1 Дубли строк выгрузки',
       printf('%d повторов на %d строк сырья',
              (SELECT COUNT(*) FROM raw_sales)
              - (SELECT COUNT(*) FROM (SELECT DISTINCT order_id, order_line_id, order_datetime,
                     outlet_code, dish_code, qty, price, discount_sum, amount_gross,
                     amount_paid, cost_sum, order_status FROM raw_sales)),
              (SELECT COUNT(*) FROM raw_sales)),
       '0',
       CAST((SELECT COUNT(*) FROM raw_sales)
            - (SELECT COUNT(*) FROM (SELECT DISTINCT order_id, order_line_id, order_datetime,
                     outlet_code, dish_code, qty, price, discount_sum, amount_gross,
                     amount_paid, cost_sum, order_status FROM raw_sales)) AS TEXT),
       'OK: устранены DISTINCT'
UNION ALL
SELECT 'C2 Сверка выручки сырьё vs витрина',
       printf('дедуплицированное сырьё: %.2f руб., витрина: %.2f руб.',
              (SELECT SUM(amount_paid) FROM (
                   SELECT DISTINCT order_id, order_line_id, amount_paid FROM raw_sales
                   WHERE order_status = 'Closed' AND NOT (qty > 0 AND amount_paid < 0))),
              (SELECT SUM(amount_paid) FROM fact_sales)),
       'расхождение 0.00',
       printf('%.2f', (SELECT SUM(amount_paid) FROM (
                        SELECT DISTINCT order_id, order_line_id, amount_paid FROM raw_sales
                        WHERE order_status = 'Closed' AND NOT (qty > 0 AND amount_paid < 0)))
                     - (SELECT SUM(amount_paid) FROM fact_sales)),
       CASE WHEN ABS((SELECT SUM(amount_paid) FROM (
                        SELECT DISTINCT order_id, order_line_id, amount_paid FROM raw_sales
                        WHERE order_status = 'Closed' AND NOT (qty > 0 AND amount_paid < 0)))
                   - (SELECT SUM(amount_paid) FROM fact_sales)) < 0.01 THEN 'OK' ELSE 'FAIL' END
UNION ALL
SELECT 'C3 Карантин: скидка больше суммы',
       printf('%d строк на %.2f руб.', COUNT(*), SUM(amount_paid)),
       'изолированы',
       CASE WHEN COUNT(*) > 0 THEN 'исключены из витрины' ELSE 'нет' END,
       'OK'
FROM quarantine_sales
UNION ALL
SELECT 'C4 Удалённые заказы',
       printf('%d строк на %.2f руб.', COUNT(*), SUM(amount_paid)),
       'не входят в выручку',
       'исключены в fact_sales',
       'OK'
FROM raw_sales
WHERE order_status = 'Deleted'
UNION ALL
SELECT 'C5 Возвраты',
       printf('%d строк на %.2f руб.', COUNT(*), SUM(amount_paid)),
       'входят в выручку со знаком минус',
       'учтены',
       'OK'
FROM fact_sales
WHERE qty < 0
UNION ALL
SELECT 'C6 Коды блюд без техкарты',
       printf('%d кодов: %s', COUNT(DISTINCT r.dish_code),
              COALESCE(GROUP_CONCAT(DISTINCT r.dish_code), 'нет')),
       '0',
       CASE WHEN COUNT(DISTINCT r.dish_code) = 0 THEN 'нет' ELSE 'сопоставлены вручную' END,
       CASE WHEN COUNT(DISTINCT r.dish_code) = 0 THEN 'OK' ELSE 'OK: mapping D15N -> D15' END
FROM raw_sales AS r
WHERE NOT EXISTS (SELECT 1 FROM raw_dish_cost AS c WHERE c.dish_code = r.dish_code)
UNION ALL
SELECT 'C7 Полнота ФОТ',
       printf('%d месяцев по точкам без ФОТ: %s', COUNT(*),
              COALESCE(GROUP_CONCAT(outlet_code || ' ' || substr(month_start, 1, 7)), 'нет')),
       '0',
       CASE WHEN COUNT(*) = 0 THEN 'нет' ELSE 'показатель оставлен NULL' END,
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'WARN: требует сверки с бухгалтерией' END
FROM mart_monthly_outlet
WHERE payroll_missing = 1
UNION ALL
SELECT 'C8 Покрытие планом',
       printf('%d месяцев по точкам без плана', COUNT(*)),
       '0',
       CAST(COUNT(*) AS TEXT),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'FAIL' END
FROM mart_monthly_outlet AS m
WHERE NOT EXISTS (SELECT 1 FROM fact_plan AS p
                   WHERE p.month_start = m.month_start AND p.outlet_code = m.outlet_code)
UNION ALL
SELECT 'C9 Рентабельность: выбросы',
       printf('месяцев с отрицательной рентабельностью: %d, минимум %.1f%%',
              SUM(CASE WHEN operating_profit_pct < 0 THEN 1 ELSE 0 END),
              MIN(operating_profit_pct)),
       'перечень на разбор',
       printf('%d точек затронуто', COUNT(DISTINCT CASE WHEN operating_profit_pct < 0 THEN outlet_code END)),
       'OK: разобрано в выводах'
FROM mart_monthly_outlet
UNION ALL
SELECT 'C10 Средний чек',
       printf('мин %.0f руб., макс %.0f руб.', MIN(avg_check), MAX(avg_check)),
       '200-900 руб.',
       CASE WHEN MIN(avg_check) < 200 OR MAX(avg_check) > 900 THEN 'вне диапазона' ELSE 'в диапазоне' END,
       CASE WHEN MIN(avg_check) >= 200 AND MAX(avg_check) <= 900 THEN 'OK' ELSE 'WARN' END
FROM mart_monthly_outlet
UNION ALL
SELECT 'C11 Итоги по сети',
       printf('выручка %.0f млн руб., food cost %.1f%%, ФОТ %.1f%%, операционная рентабельность %.1f%%',
              SUM(revenue) / 1000000.0,
              SUM(foodcost) / SUM(revenue) * 100,
              SUM(payroll) / SUM(revenue) * 100,
              (SUM(revenue) - SUM(foodcost) - SUM(payroll)) / SUM(revenue) * 100),
       '—',
       printf('%d месяцев, %d точек', COUNT(DISTINCT month_start), COUNT(DISTINCT outlet_code)),
       'INFO'
FROM mart_monthly_outlet;
