from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Absence:
    name: str
    week: int
    absence_type: str  # "day_before" | "same_day"


@dataclass
class Prepayment:
    name: str
    amount: int


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


@dataclass
class TransferRow:
    name: str
    role: str
    refund: int
    settlement_fee: int
    to_payer1: int
    to_payer2: int
    action: str


@dataclass
class TreasurerSummary:
    name: str
    prepaid: int
    receive_from_others: int


def split_by_ratio(total: int, ratio1: float) -> tuple[int, int]:
    if total <= 0:
        return 0, 0
    amount1 = int(total * ratio1)
    amount2 = total - amount1
    return amount1, amount2


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


def calculate_transfers(
    member_rows: list[MemberSettlement],
    prepayments: list[Prepayment],
) -> tuple[list[TransferRow], list[TreasurerSummary]]:
    if not prepayments:
        return [], []

    payer1 = prepayments[0]
    payer2 = prepayments[1] if len(prepayments) > 1 else None
    amount1 = payer1.amount
    amount2 = payer2.amount if payer2 else 0
    total_paid = amount1 + amount2

    if total_paid <= 0:
        ratio1 = 1.0
    else:
        ratio1 = amount1 / total_paid

    payer_names = {payer1.name}
    if payer2 and amount2 > 0:
        payer_names.add(payer2.name)

    transfer_rows: list[TransferRow] = []
    receive_totals = {payer1.name: 0}
    if payer2 and amount2 > 0:
        receive_totals[payer2.name] = 0

    for member in member_rows:
        settlement_fee = member.next_month_fee
        to_payer1 = 0
        to_payer2 = 0

        if member.name in payer_names:
            if member.name == payer1.name:
                role = "👑 총무 1"
            else:
                role = "👑 총무 2"
            action = "송금 불필요 (선결제자)"
        else:
            role = "일반 멤버"
            to_payer1, to_payer2 = split_by_ratio(settlement_fee, ratio1)
            if payer2 is None or amount2 <= 0:
                to_payer1 = settlement_fee
                to_payer2 = 0

            parts = []
            if to_payer1 > 0:
                parts.append(f"{payer1.name}에게 {to_payer1:,}원")
            if to_payer2 > 0 and payer2:
                parts.append(f"{payer2.name}에게 {to_payer2:,}원")
            action = " · ".join(parts) if parts else "송금 없음"

            receive_totals[payer1.name] = receive_totals.get(payer1.name, 0) + to_payer1
            if payer2 and amount2 > 0:
                receive_totals[payer2.name] = receive_totals.get(payer2.name, 0) + to_payer2

        transfer_rows.append(
            TransferRow(
                name=member.name,
                role=role,
                refund=member.refund,
                settlement_fee=settlement_fee,
                to_payer1=to_payer1,
                to_payer2=to_payer2,
                action=action,
            )
        )

    treasurer_summaries = [
        TreasurerSummary(
            name=payer1.name,
            prepaid=amount1,
            receive_from_others=receive_totals.get(payer1.name, 0),
        )
    ]
    if payer2 and amount2 > 0:
        treasurer_summaries.append(
            TreasurerSummary(
                name=payer2.name,
                prepaid=amount2,
                receive_from_others=receive_totals.get(payer2.name, 0),
            )
        )

    return transfer_rows, treasurer_summaries
