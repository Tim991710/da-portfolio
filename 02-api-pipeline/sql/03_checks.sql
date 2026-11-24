-- 03_checks.sql
-- Проверки полноты и осмысленности выгрузки. Сравниваем витрину с
-- логом загрузчика (raw_completeness, raw_fetch_log): если BI и скрипт
-- считают по-разному, ошибка в одном из двух путей, а не в источнике.

INSERT INTO log_data_quality (check_name, expected, actual, status, note)
SELECT 'C1 Строк против счётчика источника',
       CAST((SELECT expected FROM raw_completeness WHERE check_name LIKE 'Строк%') AS TEXT),
       CAST(COUNT(*) AS TEXT),
       CASE WHEN COUNT(*) = (SELECT expected FROM raw_completeness WHERE check_name LIKE 'Строк%')
            THEN 'OK' ELSE 'FAIL' END,
       'open_issues_count GitHub включает pull request'
FROM fact_issue
UNION ALL
SELECT 'C2 Дубли по номеру',
       '0',
       CAST(COUNT(*) - COUNT(DISTINCT number) AS TEXT),
       CASE WHEN COUNT(*) = COUNT(DISTINCT number) THEN 'OK' ELSE 'FAIL' END,
       ''
FROM fact_issue
UNION ALL
SELECT 'C3 Доля pull request',
       'справочно',
       CAST(ROUND(AVG(is_pull_request) * 100, 1) AS TEXT) || '%',
       'INFO',
       'метрики по обращениям считать без PR'
FROM fact_issue
UNION ALL
SELECT 'C4 Закрытые даты у открытых обращений',
       '0',
       CAST(COUNT(*) AS TEXT),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'FAIL' END,
       'state = open, но closed_at заполнен'
FROM fact_issue
WHERE state = 'open' AND closed_at IS NOT NULL AND closed_at <> ''
UNION ALL
SELECT 'C5 Пустая дата создания',
       '0',
       CAST(COUNT(*) AS TEXT),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'FAIL' END,
       'без даты создания нельзя считать возраст обращения'
FROM fact_issue
WHERE created_at IS NULL OR created_at = ''
UNION ALL
SELECT 'C6 Даты в будущем',
       '0',
       CAST(COUNT(*) AS TEXT),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'WARN' END,
       'часовые пояса источника могут давать сдвиг на сутки'
FROM fact_issue
WHERE date(created_at) > date('now')
UNION ALL
SELECT 'C7 Покрытие периодами',
       '24+ месяца',
       CAST(COUNT(DISTINCT substr(created_at, 1, 7)) AS TEXT) || ' мес., '
       || MIN(substr(created_at, 1, 10)) || ' .. ' || MAX(substr(created_at, 1, 10)),
       'INFO',
       ''
FROM fact_issue
UNION ALL
SELECT 'C8 Обращения без меток',
       'справочно',
       CAST(COUNT(*) AS TEXT) || ' (' || CAST(ROUND(AVG(CASE WHEN labels_count = 0 THEN 1.0 ELSE 0 END) * 100, 1) AS TEXT) || '%)',
       'INFO',
       'разметка неполная — фильтры по меткам теряют часть обращений'
FROM fact_issue
UNION ALL
SELECT 'C9 Страниц в логе загрузки',
       CAST((SELECT expected FROM raw_completeness WHERE check_name LIKE 'Запросов%') AS TEXT),
       CAST(COUNT(*) AS TEXT),
       CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'FAIL' END,
       'оценка стоимости обновления по квоте API'
FROM raw_fetch_log
UNION ALL
SELECT 'C10 Пустые страницы в логе',
       '0',
       CAST(SUM(CASE WHEN items = 0 THEN 1 ELSE 0 END) AS TEXT),
       CASE WHEN SUM(CASE WHEN items = 0 THEN 1 ELSE 0 END) = 0 THEN 'OK' ELSE 'WARN' END,
       'пустая страница означает обрыв пагинации'
FROM raw_fetch_log
UNION ALL
SELECT 'C11 Топ-метка',
       'справочно',
       (SELECT label || ' — ' || issues_cnt FROM mart_label ORDER BY issues_cnt DESC LIMIT 1),
       'INFO',
       '';

