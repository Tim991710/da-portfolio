"""Генератор синтетических данных, имитирующих выгрузки из iiko.

Задача: получить сырьё, максимально похожее по структуре и «грязи» на реальные
выгрузки сети общепита, чтобы дальше показать полный путь
CSV -> landing -> витрины -> модель Power BI.

Запуск:  python data_gen/generate_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SEED = 42
rng = np.random.default_rng(SEED)

START = pd.Timestamp("2024-11-01")
END = pd.Timestamp("2026-10-31")
DAYS = pd.date_range(START, END, freq="D")

WEEKDAY_F = np.array([1.18, 1.00, 1.00, 1.03, 1.09, 1.26, 1.21])  # Пн..Вс
MONTH_F = np.array([0.95, 0.97, 1.00, 1.00, 1.05, 1.08, 1.05, 1.00, 1.02, 1.05, 0.98, 1.12])


OUTLETS = [
    # code, name, city, open_date, base_orders_per_day, annual_trend
    ("T01", "Точка Еды Томск Ленина", "Томск", "2021-03-01", 22, 0.10),
    ("T02", "Точка Еды Томск Фрунзе", "Томск", "2022-06-01", 17, 0.07),
    ("T03", "Точка Еды Томск Академгородок", "Томск", "2023-02-01", 15, 0.04),
    ("T04", "Точка Еды Новосибирск Красный", "Новосибирск", "2021-09-01", 24, 0.11),
    ("T05", "Точка Еды Новосибирск Площадь", "Новосибирск", "2023-05-01", 16, 0.06),
    ("T06", "Точка Еды Кемерово Центр", "Кемерово", "2022-11-01", 12, 0.03),
    ("T07", "Точка Еды Красноярск Мира", "Красноярск", "2026-02-01", 14, 0.05),
    ("T08", "Точка Еды Красноярск Взлётка", "Красноярск", "2024-04-01", 13, 0.08),
    ("T09", "Точка Еды Иркутск Декабристов", "Иркутск", "2023-09-01", 11, 0.05),
    ("T10", "Точка Еды Омск Мира", "Омск", "2024-08-01", 10, 0.06),
]

CATEGORIES = {
    "Шаурма": 0.34,
    "Бургеры": 0.16,
    "Снэки": 0.20,
    "Напитки": 0.20,
    "Десерты": 0.06,
    "Соусы": 0.04,
}

DISHES = [
    # code, name, category, price, cost
    ("D01", "Шаурма классическая", "Шаурма", 240, 96),
    ("D02", "Шаурма с курицей", "Шаурма", 260, 104),
    ("D03", "Шаурма с говядиной", "Шаурма", 320, 148),
    ("D04", "Шаурма острая", "Шаурма", 275, 112),
    ("D05", "Шаурма-боул", "Шаурма", 290, 118),
    ("D06", "Бургер классический", "Бургеры", 310, 132),
    ("D07", "Бургер с беконом", "Бургеры", 370, 168),
    ("D08", "Чизбургер", "Бургеры", 330, 142),
    ("D09", "Картофель фри", "Снэки", 130, 44),
    ("D10", "Картофель по-деревенски", "Снэки", 145, 49),
    ("D11", "Наггетсы", "Снэки", 170, 68),
    ("D12", "Стрипсы", "Снэки", 195, 82),
    ("D13", "Кола 0.5", "Напитки", 120, 34),
    ("D14", "Вода 0.5", "Напитки", 80, 22),
    ("D15", "Морс клюквенный", "Напитки", 110, 30),
    ("D16", "Чай черный", "Напитки", 70, 12),
    ("D17", "Кофе американо", "Напитки", 110, 28),
    ("D18", "Сырный соус", "Соусы", 45, 14),
    ("D19", "Чесночный соус", "Соусы", 45, 12),
    ("D20", "Кетчуп", "Соусы", 35, 8),
    ("D21", "Чизкейк", "Десерты", 190, 78),
    ("D22", "Брауни", "Десерты", 165, 66),
    ("D23", "Мороженое", "Десерты", 120, 45),
]

# Переименование блюда: с 01.05.2026 в выгрузке появляется новый код D15N
RENAME_CODE_FROM = pd.Timestamp("2026-05-01")
RENAME_SRC, RENAME_DST = "D15", "D15N"

PRICE_STEPS = [(pd.Timestamp("2025-09-01"), 1.07), (pd.Timestamp("2026-06-01"), 1.05)]
COST_STEPS = [
    (pd.Timestamp("2025-10-01"), 1.18, {"Шаурма", "Снэки", "Соусы"}),
    (pd.Timestamp("2026-04-01"), 1.05, None),
]


# Атрибуты заказа, как в iiko OLAP: час, канал продажи, тип оплаты, гости
HOURS = np.array([8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22])
HOUR_W = np.array([2, 3, 4, 6, 12, 14, 12, 8, 6, 6, 8, 9, 7, 4, 2], dtype=float)
HOUR_W = HOUR_W / HOUR_W.sum()

ORDER_TYPES = np.array(["Зал", "На вынос", "Доставка"])
ORDER_W = np.array([0.55, 0.30, 0.15])

PAY_TYPES = np.array(["Наличные", "Карта", "Онлайн"])
PAY_W = np.array([0.25, 0.60, 0.15])

DISCOUNT_TYPES = np.array(["Скидка на блюдо", "Промокод", "Скидка сотрудника"])
DISCOUNT_W = np.array([0.55, 0.35, 0.10])

WRITEOFF_REASONS = np.array(["Брак", "Порча", "Истечение срока", "Дегустация", "Ошибка кассира"])
WRITEOFF_W = np.array([0.30, 0.25, 0.25, 0.12, 0.08])


def price_mult(day: pd.Timestamp) -> float:
    m = 1.0
    for dt, k in PRICE_STEPS:
        if day >= dt:
            m *= k
    return m


def cost_mult(day: pd.Timestamp, category: str) -> float:
    m = 1.0
    for dt, k, cats in COST_STEPS:
        if day >= dt and (cats is None or category in cats):
            m *= k
    return m


def outlet_event(code: str, day: pd.Timestamp) -> float:
    # T03 теряет трафик с марта 2026, T07 выходит на плановый объём за 3 месяца
    if code == "T03" and day >= pd.Timestamp("2026-03-01"):
        return 0.78
    if code == "T07":
        months = (day - pd.Timestamp("2026-02-01")).days // 30
        return min(1.0, 0.55 + 0.15 * months)
    return 1.0


def build_sales() -> pd.DataFrame:
    dishes = pd.DataFrame(DISHES, columns=["dish_code", "dish_name", "category", "price", "cost"])
    cat_w = pd.Series(CATEGORIES) / sum(CATEGORIES.values())
    by_cat = {c: g.to_dict("records") for c, g in dishes.groupby("category")}

    rows: list[tuple] = []
    order_seq = 1
    for outlet_code, _, _, open_date, base_orders, trend in OUTLETS:
        open_dt = pd.Timestamp(open_date)
        for day in DAYS:
            if day < open_dt:
                continue
            years = (day - START).days / 365.0
            lam = (
                base_orders
                * WEEKDAY_F[day.weekday()]
                * MONTH_F[day.month - 1]
                * (1 + trend) ** years
                * outlet_event(outlet_code, day)
                * rng.normal(1.0, 0.10)
            )
            n_orders = max(0, int(rng.poisson(max(lam, 0.1))))
            pm = price_mult(day)
            for _ in range(n_orders):
                basket = int(rng.choice([1, 2, 3, 4, 5], p=[0.45, 0.32, 0.15, 0.06, 0.02]))
                cats = rng.choice(cat_w.index.to_numpy(), size=basket, p=cat_w.to_numpy())
                # Атрибуты заказа: в iiko OLAP они доступны в каждой строке чека
                hour = int(rng.choice(HOURS, p=HOUR_W))
                ts = day + pd.Timedelta(hours=hour, minutes=int(rng.integers(0, 60)))
                order_type = str(rng.choice(ORDER_TYPES, p=ORDER_W))
                payment = str(rng.choice(PAY_TYPES, p=PAY_W))
                guests = int(rng.choice([1, 1, 2, 2, 3, 4]))
                for line_no, cat in enumerate(cats, start=1):
                    dish = by_cat[cat][rng.integers(0, len(by_cat[cat]))]
                    qty = 1 if cat != "Соусы" else int(rng.choice([1, 1, 2]))
                    price = float(np.floor(dish["price"] * pm / 5) * 5)
                    amount = round(price * qty, 2)
                    if rng.random() < 0.18:
                        discount = round(amount * rng.choice([0.05, 0.10, 0.15, 0.20, 0.30]), 2)
                        discount_type = str(rng.choice(DISCOUNT_TYPES, p=DISCOUNT_W))
                    else:
                        discount = 0.0
                        discount_type = "Без скидки"
                    cost = round(dish["cost"] * cost_mult(day, cat) * qty, 2)
                    code = dish["dish_code"]
                    name = dish["dish_name"]
                    if code == RENAME_SRC and day >= RENAME_CODE_FROM:
                        code, name = RENAME_DST, "Морс клюквенный (новый)"
                    rows.append(
                        (
                            f"{outlet_code}-{day:%Y%m%d}-{order_seq:07d}",
                            line_no,
                            ts.strftime("%Y-%m-%d %H:%M:%S"),
                            hour,
                            order_type,
                            payment,
                            guests,
                            outlet_code,
                            code,
                            name,
                            cat,
                            qty,
                            price,
                            discount_type,
                            discount,
                            round(amount - discount, 2),
                            amount,
                            cost,
                            "Closed",
                        )
                    )
                order_seq += 1

    df = pd.DataFrame(
        rows,
        columns=[
            "order_id",
            "order_line_id",
            "order_datetime",
            "order_hour",
            "order_type",
            "payment_type",
            "guest_count",
            "outlet_code",
            "dish_code",
            "dish_name",
            "category",
            "qty",
            "price",
            "discount_type",
            "discount_sum",
            "amount_paid",
            "amount_gross",
            "cost_sum",
            "order_status",
        ],
    )
    return df


def degrade(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Намеренно добавляем типовые дефекты выгрузки."""
    marks = {}

    # 1. Удалённые заказы: 1% заказов помечаем Deleted (в выручку не идут)
    order_ids = df["order_id"].drop_duplicates().to_numpy()
    deleted = rng.choice(order_ids, size=int(len(order_ids) * 0.01), replace=False)
    df.loc[df["order_id"].isin(deleted), "order_status"] = "Deleted"
    marks["deleted_lines"] = int(df["order_status"].eq("Deleted").sum())

    # 2. Возвраты: отрицательное количество
    ret_idx = rng.choice(df.index.to_numpy(), size=40, replace=False)
    df.loc[ret_idx, ["qty", "amount_gross", "amount_paid", "cost_sum"]] *= -1
    marks["return_lines"] = len(ret_idx)

    # 3. Дубли строк (сбой повторной выгрузки)
    dup_src = df.sample(60, random_state=SEED)
    df = pd.concat([df, dup_src], ignore_index=True)
    marks["duplicate_lines"] = len(dup_src)

    # 4. Скидка больше суммы (ошибка ручного ввода)
    bad_idx = rng.choice(df.index.to_numpy(), size=12, replace=False)
    df.loc[bad_idx, "discount_sum"] = df.loc[bad_idx, "amount_gross"] + 50
    df.loc[bad_idx, "amount_paid"] = df.loc[bad_idx, "amount_gross"] - df.loc[bad_idx, "discount_sum"]
    marks["bad_discount_lines"] = len(bad_idx)

    return df, marks


def build_payroll() -> tuple[pd.DataFrame, dict]:
    rates = {"Повар": 320, "Кассир": 290, "Управляющий": 520}
    share = {"Повар": 0.45, "Кассир": 0.40, "Управляющий": 0.15}
    rows = []
    for outlet_code, _, _, open_date, base_orders, trend in OUTLETS:
        open_dt = pd.Timestamp(open_date)
        for m in pd.period_range(START, END, freq="M"):
            m_start = m.to_timestamp()
            if m_start < pd.Timestamp(open_dt.year, open_dt.month, 1):
                continue
            idx = list(pd.period_range(START, END, freq="M")).index(m)
            # Штат планируется заранее и не пересматривается вслед за трафиком:
            # 0.30 чел-часа на заказ * 30 дней. Именно поэтому падение трафика
            # поднимает долю ФОТ в выручке.
            hours_base = base_orders * 30 * 0.30 * (1 + 0.005 * idx)
            season = MONTH_F[m_start.month - 1]
            for pos, r in rates.items():
                hours = round(hours_base * share[pos] * season * rng.normal(1.0, 0.04), 1)
                rate = r * (1 + 0.006) ** idx
                accrual = round(hours * rate, 2)
                rows.append((m_start.strftime("%Y-%m-%d"), outlet_code, pos, hours, accrual))

    df = pd.DataFrame(rows, columns=["month_start", "outlet_code", "position_group", "hours", "accrual"])

    # Пропуск одного месяца по точке T05: обновление отчёта по ФОТ сломалось
    mask = (df["outlet_code"] == "T05") & (df["month_start"] == "2026-03-01")
    marks = {"missing_payroll_rows": int(mask.sum())}
    df = df[~mask].reset_index(drop=True)
    return df, marks


def build_plan(sales: pd.DataFrame) -> pd.DataFrame:
    """План ставится заранее: +5..8% к прошлому факту, ФОТ 21-23% от выручки."""
    fact = (
        sales[sales["order_status"] == "Closed"]
        .assign(month_start=lambda d: pd.to_datetime(d["order_datetime"]).dt.to_period("M").dt.to_timestamp())
        .groupby(["month_start", "outlet_code"], as_index=False)["amount_paid"]
        .sum()
        .rename(columns={"amount_paid": "prev_fact"})
    )
    fact["revenue_plan"] = (
        fact["prev_fact"] * rng.uniform(1.03, 1.09, len(fact))
    ).round(-3)
    fact["payroll_plan_pct"] = rng.uniform(0.21, 0.23, len(fact))
    fact["payroll_plan"] = (fact["revenue_plan"] * fact["payroll_plan_pct"]).round(0)
    return fact[["month_start", "outlet_code", "revenue_plan", "payroll_plan"]]


def build_refs() -> tuple[pd.DataFrame, pd.DataFrame]:
    outlets = pd.DataFrame(
        [(c, n, city, od, "Street-food") for c, n, city, od, _, _ in OUTLETS],
        columns=["outlet_code", "outlet_name", "city", "open_date", "format"],
    )
    cost_rows = []
    for code, name, cat, _, base_cost in DISHES:
        points = [(START, base_cost)]
        for dt, k, cats in COST_STEPS:
            if cats is None or cat in cats:
                points.append((dt, points[-1][1] * k))
        for dt, c in points:
            cost_rows.append((code, dt.strftime("%Y-%m-%d"), round(c, 2)))
    costs = pd.DataFrame(cost_rows, columns=["dish_code", "valid_from", "cost_per_unit"])
    return outlets, costs


def build_writeoffs() -> pd.DataFrame:
    """Акты списания — вторая выгрузка iiko: брак, порча, истечение срока."""
    rows: list[tuple] = []
    seq = 1
    for outlet_code, _, _, open_date, _, _ in OUTLETS:
        open_dt = pd.Timestamp(open_date)
        for m in pd.period_range(START, END, freq="M"):
            m_start = m.to_timestamp()
            if m_start < pd.Timestamp(open_dt.year, open_dt.month, 1):
                continue
            for _ in range(int(rng.integers(8, 19))):
                code, name, cat, _, base_cost = DISHES[int(rng.integers(0, len(DISHES)))]
                day = m_start + pd.Timedelta(days=int(rng.integers(0, 27)))
                qty = int(rng.integers(1, 5))
                cost = round(base_cost * cost_mult(day, cat) * qty, 2)
                rows.append(
                    (
                        f"WO-{m.strftime('%Y%m')}-{seq:05d}",
                        day.strftime("%Y-%m-%d"),
                        outlet_code,
                        code,
                        name,
                        cat,
                        qty,
                        str(rng.choice(WRITEOFF_REASONS, p=WRITEOFF_W)),
                        cost,
                        "Сотрудник точки",
                    )
                )
                seq += 1

    df = pd.DataFrame(
        rows,
        columns=[
            "doc_number",
            "writeoff_date",
            "outlet_code",
            "dish_code",
            "dish_name",
            "category",
            "qty",
            "reason",
            "cost_sum",
            "employee",
        ],
    )
    # дефект выгрузки: три строки с отрицательным количеством
    bad = rng.choice(df.index.to_numpy(), size=3, replace=False)
    df.loc[bad, ["qty", "cost_sum"]] *= -1
    return df


def main() -> None:
    sales = build_sales()
    sales, sales_marks = degrade(sales)

    # iiko выгружает в windows-1251 с точкой с запятой — оставляем как есть,
    # чтобы при загрузке в Power Query пришлось явно указать кодировку.
    sales = sales.sort_values(["order_datetime", "order_id", "order_line_id"])
    sales_to_csv = sales.copy()
    sales_to_csv["order_datetime"] = sales_to_csv["order_datetime"].astype(str)
    sales_to_csv.to_csv(
        RAW / "iiko_olap_sales.csv", index=False, sep=";", encoding="cp1251", decimal=","
    )

    outlets, costs = build_refs()
    outlets.to_csv(RAW / "outlets.csv", index=False, encoding="utf-8")

    costs.to_csv(RAW / "dish_cost_techcards.csv", index=False, encoding="utf-8")

    payroll, payroll_marks = build_payroll()
    payroll.to_csv(RAW / "iiko_payroll.csv", index=False, encoding="utf-8")

    plan = build_plan(sales)
    plan.to_csv(RAW / "plan_revenue_payroll.csv", index=False, encoding="utf-8")

    # Вторая выгрузка iiko: акты списания (брак, порча, истечение срока)
    writeoffs = build_writeoffs()
    writeoffs.to_csv(RAW / "iiko_writeoffs.csv", index=False, encoding="utf-8")

    marks = {
        **sales_marks,
        **payroll_marks,
        "sales_rows": len(sales),
        "orders": sales["order_id"].nunique(),
        "writeoff_rows": len(writeoffs),
        "writeoff_sum": round(float(writeoffs.loc[writeoffs["qty"] > 0, "cost_sum"].sum()), 2),
    }
    print("Готово. Файлы в", RAW)
    for k, v in marks.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
