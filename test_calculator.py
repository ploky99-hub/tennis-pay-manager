from calculator import Absence, calculate_settlement


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
