-- 01_schema.sql
-- Слой витрин для выгрузки обращений из API.

DROP VIEW IF EXISTS v_labels_split;
DROP TABLE IF EXISTS fact_issue;
DROP TABLE IF EXISTS mart_month;
DROP TABLE IF EXISTS mart_label;
DROP TABLE IF EXISTS mart_author;
DROP TABLE IF EXISTS log_data_quality;

CREATE TABLE fact_issue (
    number          INTEGER PRIMARY KEY,
    title           TEXT NOT NULL,
    state           TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    closed_at       TEXT,
    updated_at      TEXT NOT NULL,
    author_login    TEXT,
    author_type     TEXT,
    labels          TEXT,
    labels_count    INTEGER NOT NULL,
    comments        INTEGER NOT NULL,
    is_pull_request INTEGER NOT NULL,
    milestone       TEXT
);

CREATE TABLE mart_month (
    month            TEXT PRIMARY KEY,   -- YYYY-MM
    issues_total     INTEGER NOT NULL,
    issues_only      INTEGER NOT NULL,
    pull_requests    INTEGER NOT NULL,
    without_labels   INTEGER NOT NULL,
    avg_comments     REAL
);

CREATE TABLE mart_label (
    label       TEXT PRIMARY KEY,
    issues_cnt  INTEGER NOT NULL
);

CREATE TABLE mart_author (
    author_login TEXT PRIMARY KEY,
    issues_cnt   INTEGER NOT NULL,
    pr_cnt       INTEGER NOT NULL,
    is_bot       INTEGER NOT NULL
);

CREATE TABLE log_data_quality (
    check_name TEXT NOT NULL,
    expected   TEXT,
    actual     TEXT,
    status     TEXT NOT NULL,
    note       TEXT
);
