"""Эталонный загрузчик REST API: пагинация, лимиты, ретраи, лог полноты.

Источник: GitHub REST API, открытые обращения репозитория. Проект специально
построен на «незнакомой» системе: JSON с вложенными объектами, пагинация через
заголовок Link, лимит 60 запросов в час без токена, 403 вместо 429 при
исчерпании квоты.

Зачем: доказать, что выгрузку можно воспроизвести, а не собрать руками.
Power Query повторяет ту же логику (см. power_query), а этот скрипт нужен как
эталон для сверки: если BI насчитал другое число строк, виноват запрос, а не
источник.

Запуск:  python api_fetch.py
"""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent
RAW = BASE / "data" / "raw"
PAGES = RAW / "pages"
PAGES.mkdir(parents=True, exist_ok=True)

OWNER, REPO = "duckdb", "duckdb"
STATE = "open"
PER_PAGE = 100
MAX_PAGES = 30
API = "https://api.github.com"
HEADERS = {
    "User-Agent": "DataPortfolioBot/1.0 (portfolio project)",
    "Accept": "application/vnd.github+json",
}


def get(url: str, params: dict | None = None, attempts: int = 3) -> requests.Response:
    """GET с ретраями. 403 у GitHub означает исчерпанную квоту, а не запрет."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2 ** attempt)
            continue

        if resp.status_code == 200:
            return resp

        remaining = resp.headers.get("X-RateLimit-Remaining")
        if resp.status_code in (403, 429):
            if remaining == "0":
                reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                wait = max(reset - int(time.time()), 0)
                raise RuntimeError(
                    f"Квота исчерпана: осталось {remaining}, сброс через {wait} с. "
                    "Нужен токен или пауза — молча продолжать нельзя, получим дыры в данных."
                )
            last_error = f"403: {resp.text[:200]}"
        elif resp.status_code >= 500:
            last_error = f"{resp.status_code}: {resp.text[:200]}"
        else:
            raise RuntimeError(f"{resp.status_code} на {resp.url}: {resp.text[:300]}")

        time.sleep(2 ** attempt)

    raise RuntimeError(f"Не удалось получить {url}: {last_error}")


def next_link(header: str | None) -> str | None:
    """Разбирает Link: <...>; rel="next", <...>; rel="last"."""
    if not header:
        return None
    for part in header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def flatten(item: dict) -> dict:
    labels = [lb["name"] for lb in item.get("labels", [])]
    return {
        "number": item["number"],
        "title": item["title"],
        "state": item["state"],
        "created_at": item["created_at"],
        "closed_at": item.get("closed_at"),
        "updated_at": item["updated_at"],
        "author_login": (item.get("user") or {}).get("login"),
        "author_type": (item.get("user") or {}).get("type"),
        "labels": ";".join(labels),
        "labels_count": len(labels),
        "comments": item.get("comments", 0),
        "is_pull_request": 1 if item.get("pull_request") else 0,
        "milestone": (item.get("milestone") or {}).get("title"),
    }


def main() -> None:
    started = datetime.now(timezone.utc)

    repo_info = get(f"{API}/repos/{OWNER}/{REPO}").json()
    expected = repo_info["open_issues_count"]  # включает pull request'ы
    print(f"Источник: {OWNER}/{REPO}, открытых обращений по счётчику: {expected}")

    url: str | None = f"{API}/repos/{OWNER}/{REPO}/issues"
    params: dict | None = {
        "state": STATE,
        "per_page": PER_PAGE,
        "sort": "created",
        "direction": "desc",
        "page": 1,
    }

    rows: list[dict] = []
    log: list[dict] = []
    page_no = 0

    while url and page_no < MAX_PAGES:
        page_no += 1
        resp = get(url, params)
        items = resp.json()
        if not isinstance(items, list):
            raise RuntimeError(f"Ожидался список, пришёл {type(items).__name__}")

        (PAGES / f"page_{page_no:03d}.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        rows.extend(flatten(i) for i in items)
        log.append(
            {
                "page": page_no,
                "http_status": resp.status_code,
                "items": len(items),
                "cumulative": len(rows),
                "rate_remaining": resp.headers.get("X-RateLimit-Remaining"),
                "url": resp.url,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        print(f"  страница {page_no}: {len(items)} записей, всего {len(rows)}")

        if not items:
            break
        url = next_link(resp.headers.get("Link"))
        params = None  # дальше идём по готовой ссылке, параметры уже в ней

    df = pd.DataFrame(rows).drop_duplicates(subset=["number"])
    df.to_csv(RAW / "issues.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(log).to_csv(RAW / "fetch_log.csv", index=False, encoding="utf-8-sig")

    # ---------- Контроль полноты ----------
    checks = []

    def check(name: str, expected_v, actual_v, ok: bool, note: str = "") -> None:
        checks.append(
            {"check": name, "expected": expected_v, "actual": actual_v,
             "status": "OK" if ok else "FAIL", "note": note}
        )

    check("Строк собрано против счётчика источника", expected, len(df), expected == len(df),
          "счётчик GitHub включает PR")
    dupes = len(rows) - df["number"].nunique()
    check("Дубли по number", 0, dupes, dupes == 0)
    short_pages = [l["page"] for l in log[:-1] if 0 < l["items"] < PER_PAGE]
    check("Неполные страницы кроме последней", 0, len(short_pages), not short_pages,
          f"страницы: {short_pages}" if short_pages else "")
    empties = sum(1 for l in log if l["items"] == 0)
    check("Пустых страниц", 0, empties, empties == 0)
    check("Запросов к API", f"<={MAX_PAGES}", len(log), len(log) <= MAX_PAGES)

    result = pd.DataFrame(checks)
    result.to_csv(RAW / "completeness.csv", index=False, encoding="utf-8-sig")

    print("\nКонтроль полноты:")
    for _, r in result.iterrows():
        print(f"  [{r['status']}] {r['check']}: ожидали {r['expected']}, получили {r['actual']}")

    print("\nСтруктура выгрузки:")
    print(f"  всего записей: {len(df)}")
    print(f"  из них pull request'ов: {int(df['is_pull_request'].sum())} "
          f"({df['is_pull_request'].mean() * 100:.1f}%)")
    print(f"  без меток: {int((df['labels_count'] == 0).sum())}")
    print(f"  период создания: {df['created_at'].min()[:10]} .. {df['created_at'].max()[:10]}")
    print(f"  длительность сбора: {(datetime.now(timezone.utc) - started).seconds} с")

    if (result["status"] == "FAIL").any():
        raise SystemExit("Есть непройденные проверки — данные неполные.")


if __name__ == "__main__":
    main()
