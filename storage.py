from __future__ import annotations

import json
from pathlib import Path

from calculator import Absence, Prepayment

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DEFAULT_CONFIG_PATH = ROOT / "config.json"
CONFIG_PATH = DATA_DIR / "config.json"


def load_config() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    if DEFAULT_CONFIG_PATH.exists():
        with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as f:
            config = json.load(f)
        save_config(config)
        return config
    raise FileNotFoundError("config.json not found")


def save_config(config: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def month_file(year: int, month: int) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / f"{month_key(year, month)}.json"


def _load_month_raw(year: int, month: int) -> dict:
    path = month_file(year, month)
    if not path.exists():
        return {"year": year, "month": month, "absences": [], "prepayments": []}

    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    raw.setdefault("absences", [])
    raw.setdefault("prepayments", [])
    return raw


def load_absences(year: int, month: int) -> list[Absence]:
    raw = _load_month_raw(year, month)
    return [
        Absence(
            name=item["name"],
            week=int(item["week"]),
            absence_type=item["absence_type"],
        )
        for item in raw["absences"]
    ]


def load_prepayments(year: int, month: int) -> list[Prepayment]:
    raw = _load_month_raw(year, month)
    return [
        Prepayment(name=item["name"], amount=int(item["amount"]))
        for item in raw["prepayments"]
        if int(item.get("amount", 0)) > 0
    ]


def save_absences(year: int, month: int, absences: list[Absence]) -> None:
    raw = _load_month_raw(year, month)
    raw["absences"] = [
        {
            "name": a.name,
            "week": a.week,
            "absence_type": a.absence_type,
        }
        for a in absences
    ]
    _save_month_raw(year, month, raw)


def save_prepayments(year: int, month: int, prepayments: list[Prepayment]) -> None:
    raw = _load_month_raw(year, month)
    raw["prepayments"] = [
        {"name": p.name, "amount": p.amount}
        for p in prepayments
        if p.amount > 0
    ]
    _save_month_raw(year, month, raw)


def _save_month_raw(year: int, month: int, raw: dict) -> None:
    path = month_file(year, month)
    payload = {
        "year": year,
        "month": month,
        "absences": raw.get("absences", []),
        "prepayments": raw.get("prepayments", []),
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
