from calculator import Session, calculate_member_totals, calculate_monthly_settlements


def test_equal_split_with_payer_participating():
    session = Session(
        week=1,
        payer="A",
        amount_paid=11000,
        participants=["A", "B", "C", "D", "E"],
    )
    settlement = calculate_monthly_settlements([session])[0]

    assert settlement.share_per_person == 2200
    by_name = {item.name: item for item in settlement.payments}
    assert by_name["A"].amount == 0
    assert by_name["B"].amount == 2200


def test_discounted_court_fee():
    session = Session(
        week=2,
        payer="B",
        amount_paid=5500,
        participants=["A", "B", "C", "D", "E"],
    )
    settlement = calculate_monthly_settlements([session])[0]

    assert settlement.share_per_person == 1100
    assert next(item for item in settlement.payments if item.name == "C").amount == 1100


def test_payer_not_participating():
    session = Session(
        week=3,
        payer="A",
        amount_paid=11000,
        participants=["B", "C", "D", "E"],
    )
    settlement = calculate_monthly_settlements([session])[0]

    assert settlement.share_per_person == 2750
    assert len(settlement.payments) == 4


def test_member_monthly_totals():
    sessions = [
        Session(1, "A", 11000, ["A", "B", "C"]),
        Session(2, "B", 5500, ["A", "B", "C"]),
    ]
    settlements = calculate_monthly_settlements(sessions)
    totals = calculate_member_totals(settlements)
    by_name = {item.name: item for item in totals}

    assert by_name["C"].total_to_payer["A"] == 3666
    assert by_name["C"].total_to_payer["B"] == 1833
