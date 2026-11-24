-- 02_marts.sql
-- Из плоской выгрузки в витрины для дашборда.

-- DISTINCT по номеру: защита от повторной загрузки страницы.
INSERT INTO fact_issue (
    number, title, state, created_at, closed_at, updated_at,
    author_login, author_type, labels, labels_count, comments,
    is_pull_request, milestone
)
SELECT DISTINCT
    number, title, state, created_at, closed_at, updated_at,
    author_login, author_type, labels, labels_count, comments,
    is_pull_request, milestone
FROM raw_issue;

-- Разбор меток: «a; b; c» -> одна строка на метку.
CREATE VIEW v_labels_split AS
WITH RECURSIVE base AS (
    SELECT number, labels || ';' AS rest
    FROM fact_issue
    WHERE labels IS NOT NULL AND labels <> ''
),
split(number, label, rest) AS (
    SELECT number, '', rest FROM base
    UNION ALL
    SELECT number,
           trim(substr(rest, 1, instr(rest, ';') - 1)),
           substr(rest, instr(rest, ';') + 1)
    FROM split
    WHERE rest <> ''
)
SELECT number, label FROM split WHERE label <> '';

INSERT INTO mart_month (
    month, issues_total, issues_only, pull_requests, without_labels, avg_comments
)
SELECT
    substr(created_at, 1, 7) AS month,
    COUNT(*),
    SUM(CASE WHEN is_pull_request = 0 THEN 1 ELSE 0 END),
    SUM(is_pull_request),
    SUM(CASE WHEN labels_count = 0 THEN 1 ELSE 0 END),
    ROUND(AVG(comments), 2)
FROM fact_issue
GROUP BY 1;

INSERT INTO mart_label (label, issues_cnt)
SELECT label, COUNT(*) FROM v_labels_split GROUP BY label;

INSERT INTO mart_author (author_login, issues_cnt, pr_cnt, is_bot)
SELECT
    COALESCE(author_login, 'не указан'),
    COUNT(*),
    SUM(is_pull_request),
    MAX(CASE WHEN author_type = 'Bot' OR author_login LIKE '%[bot]%' THEN 1 ELSE 0 END)
FROM fact_issue
GROUP BY COALESCE(author_login, 'не указан');
