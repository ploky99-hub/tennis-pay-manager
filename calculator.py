from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Absence:
    name: str
    week: int
    absence_type: str  # "day_before" | "same_day"


@dataclass
class MemberSettlement:
    name: str
    refund: int
    next_month_fee: int
    day_before_count: int
    same_day_count: int


@dataclass
class WeekSettlement:
    week: int
    participants: int
    day_before_absent: list[str]
    same_day_absent: list[str]
    share_per_person: int


def calculate_settlement(
    members: list[str],
    absences: list[Absence],
    court_fee: int,
    base_monthly_fee: int,
    weeks_per_month: int,
) -> tuple[list[WeekSettlement], list[MemberSettlement]]:
    week_rows: list[WeekSettlement] = []
    refunds = {name: 0 for name in members}
    day_before_counts = {name: 0 for name in members}
    same_day_counts = {name: 0 for name in members}

    for week in range(1, weeks_per_month + 1):
        week_absences = [a for a in absences if a.week == week]
        day_before = [a.name for a in week_absences if a.absence_type == "day_before"]
        same_day = [a.name for a in week_absences if a.absence_type == "same_day"]

        participants = len(members) - len(day_before)
        if participants <= 0:
            share = 0
        else:
            share = court_fee // participants

        for name in day_before:
            refunds[name] += share
            day_before_counts[name] += 1

        for name in same_day:
            same_day_counts[name] += 1

        week_rows.append(
            WeekSettlement(
                week=week,
                participants=participants,
                day_before_absent=day_before,
                same_day_absent=same_day,
                share_per_person=share,
            )
        )

    member_rows = [
        MemberSettlement(
            name=name,
            refund=refunds[name],
            next_month_fee=max(0, base_monthly_fee - refunds[name]),
            day_before_count=day_before_counts[name],
            same_day_count=same_day_counts[name],
        )
        for name in members
    ]

    return week_rows, member_rows
