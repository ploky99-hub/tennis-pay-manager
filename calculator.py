from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Payer:
    name: str
    amount: int


@dataclass
class Session:
    week: int
    payers: list[Payer]
    participants: list[str]

    @property
    def total_paid(self) -> int:
        return sum(payer.amount for payer in self.payers)


@dataclass
class ParticipantPayment:
    name: str
    amounts_to_payers: dict[str, int]
    is_payer: bool
    note: str


@dataclass
class SessionSettlement:
    week: int
    payers: list[Payer]
    total_paid: int
    participants: list[str]
    share_per_person: int
    payments: list[ParticipantPayment]


@dataclass
class MemberWeeklyTotal:
    name: str
    total_to_payer: dict[str, int]


def split_by_payer_ratio(total: int, payers: list[Payer]) -> dict[str, int]:
    if total <= 0 or not payers:
        return {}

    total_paid = sum(payer.amount for payer in payers)
    if total_paid <= 0:
        equal = total // len(payers)
        result = {payer.name: equal for payer in payers}
        result[payers[-1].name] = total - equal * (len(payers) - 1)
        return result

    amounts: dict[str, int] = {}
    allocated = 0
    for index, payer in enumerate(payers):
        if index == len(payers) - 1:
            amounts[payer.name] = total - allocated
        else:
            share = int(total * payer.amount / total_paid)
            amounts[payer.name] = share
            allocated += share
    return amounts


def calculate_session(session: Session) -> SessionSettlement:
    participants = list(dict.fromkeys(session.participants))
    total_paid = session.total_paid
    share = total_paid // len(participants) if participants else 0
    payer_names = {payer.name for payer in session.payers}

    payments: list[ParticipantPayment] = []
    for name in participants:
        if name in payer_names:
            payments.append(
                ParticipantPayment(
                    name=name,
                    amounts_to_payers={payer.name: 0 for payer in session.payers},
                    is_payer=True,
                    note="송금 불필요 (비용 지불자)",
                )
            )
            continue

        amounts = split_by_payer_ratio(share, session.payers)
        parts = [
            f"{payer_name}에게 {amount:,}원"
            for payer_name, amount in amounts.items()
            if amount > 0
        ]
        payments.append(
            ParticipantPayment(
                name=name,
                amounts_to_payers=amounts,
                is_payer=False,
                note=" · ".join(parts) if parts else "송금 없음",
            )
        )

    return SessionSettlement(
        week=session.week,
        payers=session.payers,
        total_paid=total_paid,
        participants=participants,
        share_per_person=share,
        payments=payments,
    )


def calculate_monthly_settlements(
    sessions: list[Session],
) -> list[SessionSettlement]:
    return [
        calculate_session(session)
        for session in sorted(sessions, key=lambda item: item.week)
    ]


def calculate_member_totals(
    settlements: list[SessionSettlement],
) -> list[MemberWeeklyTotal]:
    totals: dict[str, dict[str, int]] = {}

    for settlement in settlements:
        for payment in settlement.payments:
            if payment.is_payer:
                continue
            member_totals = totals.setdefault(payment.name, {})
            for payer_name, amount in payment.amounts_to_payers.items():
                if amount > 0:
                    member_totals[payer_name] = (
                        member_totals.get(payer_name, 0) + amount
                    )

    return [
        MemberWeeklyTotal(name=name, total_to_payer=totals[name])
        for name in sorted(totals)
    ]
