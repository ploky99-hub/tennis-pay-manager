from __future__ import annotations

import re
from typing import Any


DEFAULT_MEMBERS: list[dict[str, Any]] = [
    {"name": "김혁진", "nickname": "ploky", "twins_benefit": False},
    {"name": "전도영", "nickname": "왕다람이", "twins_benefit": False},
    {"name": "전상권", "nickname": "nabi", "twins_benefit": False},
    {"name": "이민우", "nickname": "오늘발리만빵꾸", "twins_benefit": True},
    {"name": "서정욱", "nickname": "guttr0503", "twins_benefit": True},
    {"name": "김영진", "nickname": "세레나영리엄스", "twins_benefit": False},
]


def normalize_members(raw_members: list[Any]) -> list[dict[str, Any]]:
    if not raw_members:
        return []
    if isinstance(raw_members[0], str):
        return [
            {"name": name, "nickname": name, "twins_benefit": False}
            for name in raw_members
        ]
    return raw_members


def format_member(member: dict[str, Any]) -> str:
    label = f"{member['name']}({member['nickname']})"
    if member.get("twins_benefit"):
        label += " - 다둥이"
    return label


def members_to_text(members: list[dict[str, Any]]) -> str:
    return "\n".join(format_member(member) for member in members)


def parse_member_line(line: str) -> dict[str, Any]:
    stripped = line.strip()
    if not stripped:
        raise ValueError("empty line")

    twins_benefit = False
    if stripped.endswith("- 다둥이"):
        twins_benefit = True
        stripped = stripped[: -len("- 다둥이")].strip()

    match = re.match(r"^(.+?)\((.+)\)$", stripped)
    if not match:
        raise ValueError(f"invalid member format: {line}")

    return {
        "name": match.group(1).strip(),
        "nickname": match.group(2).strip(),
        "twins_benefit": twins_benefit,
    }


def parse_members_text(text: str) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        members.append(parse_member_line(line))
    return members


def member_names(members: list[dict[str, Any]]) -> list[str]:
    return [member["name"] for member in members]


def member_label(members: list[dict[str, Any]], name: str) -> str:
    for member in members:
        if member["name"] == name:
            return format_member(member)
    return name


def default_payer_amount(member: dict[str, Any], default_court_fee: int) -> int:
    if member.get("twins_benefit"):
        return default_court_fee // 2
    return default_court_fee


def is_legacy_members(members: list[dict[str, Any]]) -> bool:
    if not members:
        return True

    if all(member.get("nickname") == member["name"] for member in members):
        return True

    legacy_names = {"김혁진", "전도영", "전상권", "이민우", "서정욱"}
    current_names = {member["name"] for member in members}
    if current_names == legacy_names:
        return True

    return False


def migrate_config(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    changed = False
    members = normalize_members(config.get("members", []))

    if is_legacy_members(members):
        config["members"] = [member.copy() for member in DEFAULT_MEMBERS]
        changed = True
    else:
        config["members"] = members

    if "default_court_fee" not in config:
        config["default_court_fee"] = int(config.pop("court_fee", 11000))
        changed = True

    for old_key in ("base_monthly_fee", "court_fee", "absence_deadline_note"):
        if old_key in config:
            config.pop(old_key)
            changed = True

    if "weeks_per_month" not in config:
        config["weeks_per_month"] = 4
        changed = True

    return config, changed