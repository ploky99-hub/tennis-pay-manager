from __future__ import annotations

import json
from pathlib import Path

from calculator import Payer, Session
from members import normalize_members

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DEFAULT_CONFIG_PATH = ROOT / "config.json"
CONFIG_PATH = DATA_DIR / "config.json"


def load_config() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as f:
            config = json.load(f)
    elif DEFAULT_CONFIG_PATH.exists():
        with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as f:
            config = json.load(f)
        save_config(config)
    else:
        raise FileNotFoundError("config.json not found")

    config["members"] = normalize_members(config.get("members", []))
    return config


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
        return {"year": year, "month": month, "sessions": []}

    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    raw.setdefault("sessions", [])
    return raw


def _parse_payers(item: dict) -> list[Payer]:
    if item.get("payers"):
        return [
            Payer(name=payer["name"], amount=int(payer["amount"]))
            for payer in item["payers"]
            if int(payer.get("amount", 0)) > 0
        ]
    if item.get("payer"):
        return [Payer(name=item["payer"], amount=int(item["amount_paid"]))]
    return []


def load_sessions(year: int, month: int) -> list[Session]:
    raw = _load_month_raw(year, month)
    sessions: list[Session] = []
    for item in raw["sessions"]:
        participants = list(dict.fromkeys(item.get("participants", [])))
        payers = _parse_payers(item)
        if not payers:
            continue
        sessions.append(
            Session(
                week=int(item["week"]),
                payers=payers,
                participants=participants,
            )
        )
    return sorted(sessions, key=lambda session: session.week)


def save_sessions(year: int, month: int, sessions: list[Session]) -> None:
    payload = {
        "year": year,
        "month": month,
        "sessions": [
            {
                "week": session.week,
                "payers": [
                    {"name": payer.name, "amount": payer.amount}
                    for payer in session.payers
                ],
                "participants": session.participants,
            }
            for session in sorted(sessions, key=lambda session: session.week)
        ],
    }
    path = month_file(year, month)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
