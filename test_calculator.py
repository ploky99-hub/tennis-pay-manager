from calculator import Payer, Session, calculate_member_totals, calculate_monthly_settlements


def test_single_payer():
    session = Session(
        week=1,
        payers=[Payer(name="A", amount=11000)],
        participants=["A", "B", "C", "D", "E"],
    )
    settlement = calculate_monthly_settlements([session])[0]
    by_name = {item.name: item for item in settlement.payments}

    assert settlement.share_per_person == 2200
    assert by_name["A"].is_payer
    assert by_name["B"].amounts_to_payers["A"] == 2200


def test_multiple_payers_equal_split():
    session = Session(
        week=1,
        payers=[
            Payer(name="A", amount=5500),
            Payer(name="B", amount=5500),
        ],
        participants=["A", "B", "C", "D", "E"],
    )
    settlement = calculate_monthly_settlements([session])[0]
    by_name = {item.name: item for item in settlement.payments}

    assert by_name["C"].amounts_to_payers["A"] == 1100
    assert by_name["C"].amounts_to_payers["B"] == 1100


def test_multiple_payers_weighted_split():
    session = Session(
        week=2,
        payers=[
            Payer(name="A", amount=8250),
            Payer(name="B", amount=2750),
        ],
        participants=["A", "B", "C", "D", "E"],
    )
    settlement = calculate_monthly_settlements([session])[0]
    by_name = {item.name: item for item in settlement.payments}

    assert by_name["C"].amounts_to_payers["A"] == 1650
    assert by_name["C"].amounts_to_payers["B"] == 550


def test_non_payer_participants_only():
    session = Session(
        week=3,
        payers=[Payer(name="A", amount=11000)],
        participants=["B", "C", "D", "E"],
    )
    settlement = calculate_monthly_settlements([session])[0]

    assert settlement.share_per_person == 2750
    assert len(settlement.payments) == 4


def test_member_totals_with_multiple_payers():
    sessions = [
        Session(
            1,
            [Payer("A", 5500), Payer("B", 5500)],
            ["A", "B", "C"],
        )
    ]
    totals = calculate_member_totals(calculate_monthly_settlements(sessions))
    by_name = {item.name: item for item in totals}

    assert by_name["C"].total_to_payer["A"] == 1833
    assert by_name["C"].total_to_payer["B"] == 1833
