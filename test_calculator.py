from calculator import (
    Absence,
    Prepayment,
    calculate_settlement,
    calculate_transfers,
)


def test_day_before_refund_matches_example():
    members = ["A", "B", "C", "D", "E"]
    absences = [
        Absence(name="D", week=3, absence_type="day_before"),
        Absence(name="E", week=4, absence_type="same_day"),
    ]
    _, member_rows = calculate_settlement(
        members=members,
        absences=absences,
        court_fee=11000,
        base_monthly_fee=10000,
        weeks_per_month=4,
    )
    by_name = {row.name: row for row in member_rows}

    assert by_name["D"].refund == 2750
    assert by_name["D"].next_month_fee == 7250
    assert by_name["E"].refund == 0
    assert by_name["E"].next_month_fee == 10000
    assert by_name["A"].refund == 0


def test_multiple_day_before_same_week():
    members = ["A", "B", "C", "D", "E"]
    absences = [
        Absence(name="D", week=2, absence_type="day_before"),
        Absence(name="E", week=2, absence_type="day_before"),
    ]
    week_rows, member_rows = calculate_settlement(
        members=members,
        absences=absences,
        court_fee=11000,
        base_monthly_fee=10000,
        weeks_per_month=4,
    )
    week2 = next(row for row in week_rows if row.week == 2)
    assert week2.participants == 3
    assert week2.share_per_person == 3666

    by_name = {row.name: row for row in member_rows}
    assert by_name["D"].refund == 3666
    assert by_name["E"].refund == 3666


def test_single_treasurer_transfer():
    members = ["A", "B", "C", "D", "E"]
    _, member_rows = calculate_settlement(
        members=members,
        absences=[],
        court_fee=11000,
        base_monthly_fee=10000,
        weeks_per_month=4,
    )
    transfer_rows, summaries = calculate_transfers(
        member_rows, [Prepayment(name="A", amount=44000)]
    )
    by_name = {row.name: row for row in transfer_rows}

    assert by_name["A"].to_payer1 == 0
    assert by_name["B"].to_payer1 == 10000
    assert summaries[0].name == "A"
    assert summaries[0].receive_from_others == 40000


def test_dual_treasurer_split_by_ratio():
    members = ["A", "B", "C", "D", "E"]
    _, member_rows = calculate_settlement(
        members=members,
        absences=[],
        court_fee=11000,
        base_monthly_fee=10000,
        weeks_per_month=4,
    )
    transfer_rows, summaries = calculate_transfers(
        member_rows,
        [
            Prepayment(name="A", amount=33000),
            Prepayment(name="B", amount=11000),
        ],
    )
    by_name = {row.name: row for row in transfer_rows}

    assert by_name["C"].to_payer1 == 7500
    assert by_name["C"].to_payer2 == 2500
    assert by_name["A"].to_payer1 == 0
    assert by_name["B"].to_payer2 == 0

    summary_by_name = {s.name: s for s in summaries}
    assert summary_by_name["A"].receive_from_others == 22500
    assert summary_by_name["B"].receive_from_others == 7500


def test_dual_treasurer_with_day_before_absence():
    members = ["A", "B", "C", "D", "E"]
    absences = [Absence(name="C", week=3, absence_type="day_before")]
    _, member_rows = calculate_settlement(
        members=members,
        absences=absences,
        court_fee=11000,
        base_monthly_fee=10000,
        weeks_per_month=4,
    )
    transfer_rows, _ = calculate_transfers(
        member_rows,
        [
            Prepayment(name="A", amount=33000),
            Prepayment(name="B", amount=11000),
        ],
    )
    by_name = {row.name: row for row in transfer_rows}

    assert by_name["C"].settlement_fee == 7250
    assert by_name["C"].to_payer1 + by_name["C"].to_payer2 == 7250
