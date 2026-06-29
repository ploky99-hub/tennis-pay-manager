from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Session:
    week: int
    payer: str
    amount_paid: int
    participants: list[str]


@dataclass
class ParticipantPayment:
    name: str
    amount: int
    is_payer: bool
    note: str


@dataclass
class SessionSettlement:
    week: int
    payer: str
    amount_paid: int
    participants: list[str]
    share_per_person: int
    payments: list[ParticipantPayment]


@dataclass
class MemberWeeklyTotal:
    name: str
    total_to_payer: dict[str, int]


def calculate_session(session: Session) -> SessionSettlement:
    participants = list(dict.fromkeys(session.participants))
    if not participants:
        share = 0
    else:
        share = session.amount_paid // len(participants)

    payments: list[ParticipantPayment] = []
    for name in participants:
        if name == session.payer:
            payments.append(
                ParticipantPayment(
                    name=name,
                    amount=0,
                    is_payer=True,
                    note="송금 불필요 (비용 지불자)",
                )
            )
        else:
            payments.append(
                ParticipantPayment(
                    name=name,
                    amount=share,
                    is_payer=False,
                    note=f"{session.payer}에게 {share:,}원",
                )
            )

    return SessionSettlement(
        week=session.week,
        payer=session.payer,
        amount_paid=session.amount_paid,
        participants=participants,
        share_per_person=share,
        payments=payments,
    )


def calculate_monthly_settlements(
    sessions: list[Session],
) -> list[SessionSettlement]:
    return [calculate_session(session) for session in sorted(sessions, key=lambda s: s.week)]


def calculate_member_totals(
    settlements: list[SessionSettlement],
) -> list[MemberWeeklyTotal]:
    totals: dict[str, dict[str, int]] = {}

    for settlement in settlements:
        for payment in settlement.payments:
            if payment.is_payer or payment.amount <= 0:
                continue
            member_totals = totals.setdefault(payment.name, {})
            member_totals[settlement.payer] = (
                member_totals.get(settlement.payer, 0) + payment.amount
            )

    member_names = sorted(totals.keys())
    return [
        MemberWeeklyTotal(name=name, total_to_payer=totals[name])
        for name in member_names
    ]
