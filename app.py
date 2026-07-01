from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from calculator import Payer, Session, calculate_member_totals, calculate_monthly_settlements
from members import (
    default_payer_amount,
    format_member,
    member_label,
    member_names,
    members_to_text,
    parse_members_text,
)
from storage import load_config, load_sessions, save_config, save_sessions


def init_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = load_config()


def session_label(session: Session, members: list[dict]) -> str:
    payer_text = ", ".join(
        f"{member_label(members, payer.name)} {payer.amount:,}원"
        for payer in session.payers
    )
    participant_text = ", ".join(member_label(members, name) for name in session.participants)
    return (
        f"{session.week}주차 · {payer_text} · "
        f"참여 {len(session.participants)}명 ({participant_text})"
    )


def build_payment_table(
    settlement,
    members: list[dict],
    payer_names_in_session: list[str],
) -> pd.DataFrame:
    rows = []
    for payment in settlement.payments:
        row = {
            "이름": member_label(members, payment.name),
            "1인 부담": f"{settlement.share_per_person:,}원",
        }
        for payer_name in payer_names_in_session:
            amount = payment.amounts_to_payers.get(payer_name, 0)
            row[f"{member_label(members, payer_name)}에게"] = (
                f"{amount:,}원" if amount > 0 else "-"
            )
        row["안내"] = payment.note
        rows.append(row)
    return pd.DataFrame(rows)


def payer_inputs(
    members: list[dict],
    names: list[str],
    payer_count: int,
    saved_payers: list[Payer],
    default_court_fee: int,
    key_prefix: str,
) -> list[Payer]:
    payers: list[Payer] = []
    selected_names: list[str] = []

    for index in range(payer_count):
        available = [name for name in names if name not in selected_names]
        if not available:
            break

        saved = saved_payers[index] if index < len(saved_payers) else None
        default_name = (
            saved.name
            if saved and saved.name in available
            else available[0]
        )
        member = next(item for item in members if item["name"] == default_name)
        default_amount = (
            saved.amount
            if saved
            else default_payer_amount(member, default_court_fee)
        )

        col1, col2 = st.columns(2)
        with col1:
            payer_name = st.selectbox(
                f"비용 지불자 {index + 1}",
                available,
                index=available.index(default_name),
                format_func=lambda value, members=members: member_label(members, value),
                key=f"{key_prefix}_payer_{index}",
            )
        with col2:
            amount = st.number_input(
                "결제 금액 (원)",
                min_value=0,
                step=500,
                value=default_amount,
                key=f"{key_prefix}_amount_{index}",
            )

        selected_names.append(payer_name)
        if amount > 0:
            payers.append(Payer(name=payer_name, amount=int(amount)))

    return payers


init_state()
config = st.session_state.config
members = config["members"]
names = member_names(members)
default_fee = config.get("default_court_fee", 11000)
weeks_per_month = config.get("weeks_per_month", 4)

st.set_page_config(
    page_title="강동 테린이 꿈나무방 정산",
    page_icon="🎾",
    layout="wide",
)

st.title("🎾 강동 테린이 꿈나무방 정산")
st.caption(
    "매주 코트비를 선결제한 사람들에게, 참여자 중 미납자가 1/N으로 나눠 송금합니다."
)

tab_dashboard, tab_register, tab_settings = st.tabs(
    ["📊 정산 현황", "💳 코트비 등록", "⚙️ 설정"]
)

today = date.today()

with tab_dashboard:
    col_y, col_m = st.columns(2)
    with col_y:
        year = st.number_input("연도", min_value=2024, max_value=2035, value=today.year)
    with col_m:
        month = st.selectbox("월", list(range(1, 13)), index=today.month - 1)

    sessions = load_sessions(year, month)
    settlements = calculate_monthly_settlements(sessions)

    m1, m2 = st.columns(2)
    m1.metric("등록된 주차", f"{len(settlements)}회")
    m2.metric(
        "이번 달 선결제 합계",
        f"{sum(session.total_paid for session in sessions):,}원",
    )

    if not settlements:
        st.info("**코트비 등록** 탭에서 주차별 비용 지불자, 결제 금액, 참여자를 등록해 주세요.")
    else:
        for settlement in settlements:
            payer_labels = [
                f"{member_label(members, payer.name)} {payer.amount:,}원"
                for payer in settlement.payers
            ]
            st.subheader(f"{settlement.week}주차 송금 안내")
            st.caption(
                f"선결제 **{settlement.total_paid:,}원** ({' + '.join(payer_labels)}) · "
                f"참여 {len(settlement.participants)}명 · "
                f"1인당 **{settlement.share_per_person:,}원**"
            )
            payer_names_in_session = [payer.name for payer in settlement.payers]
            st.dataframe(
                build_payment_table(settlement, members, payer_names_in_session),
                use_container_width=True,
                hide_index=True,
            )

        member_totals = calculate_member_totals(settlements)
        if member_totals:
            st.subheader("이번 달 누적 송금 요약")
            all_payers = sorted(
                {payer for item in member_totals for payer in item.total_to_payer}
            )
            summary_rows = []
            for item in member_totals:
                row = {"이름": member_label(members, item.name)}
                for payer_name in all_payers:
                    amount = item.total_to_payer.get(payer_name, 0)
                    row[f"{member_label(members, payer_name)}에게"] = (
                        f"{amount:,}원" if amount > 0 else "-"
                    )
                summary_rows.append(row)
            st.dataframe(
                pd.DataFrame(summary_rows),
                use_container_width=True,
                hide_index=True,
            )

with tab_register:
    st.subheader("주차별 코트비 등록")
    st.caption(
        "비용 지불자는 여러 명일 수 있습니다. 다둥이 회원은 5,500원처럼 "
        "실제 결제 금액을 각각 입력하세요."
    )

    reg_y = st.number_input(
        "등록 연도", min_value=2024, max_value=2035, value=today.year, key="reg_year"
    )
    reg_m = st.selectbox(
        "등록 월", list(range(1, 13)), index=today.month - 1, key="reg_month"
    )
    current_sessions = load_sessions(reg_y, reg_m)

    with st.form("session_form", clear_on_submit=True):
        week = st.selectbox(
            "주차",
            list(range(1, weeks_per_month + 1)),
            format_func=lambda value: f"{value}주차",
        )
        payer_count = st.number_input(
            "비용 지불자 수",
            min_value=1,
            max_value=len(names),
            value=1,
            step=1,
        )
        payers = payer_inputs(
            members=members,
            names=names,
            payer_count=int(payer_count),
            saved_payers=[],
            default_court_fee=default_fee,
            key_prefix="new",
        )
        participants = st.multiselect(
            "참여자",
            names,
            default=names,
            format_func=lambda value: member_label(members, value),
            help="그날 코트에 나온 사람만 선택하세요.",
        )
        submitted = st.form_submit_button("등록하기", use_container_width=True)

    if submitted:
        if not payers:
            st.error("비용 지불자와 결제 금액을 입력해 주세요.")
        elif not participants:
            st.error("참여자를 1명 이상 선택해 주세요.")
        elif len({payer.name for payer in payers}) != len(payers):
            st.error("같은 사람을 비용 지불자로 중복 선택할 수 없습니다.")
        else:
            new_session = Session(
                week=week,
                payers=payers,
                participants=participants,
            )
            updated = False
            for index, session in enumerate(current_sessions):
                if session.week == week:
                    current_sessions[index] = new_session
                    updated = True
                    break
            if not updated:
                current_sessions.append(new_session)
            save_sessions(reg_y, reg_m, current_sessions)
            message = "수정했습니다." if updated else "등록했습니다."
            st.success(f"{reg_y}년 {reg_m}월 {week}주차를 {message}")
            st.rerun()

    if current_sessions:
        st.markdown("#### 등록된 주차")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "주차": f"{session.week}주차",
                        "비용 지불자": ", ".join(
                            f"{member_label(members, payer.name)} {payer.amount:,}원"
                            for payer in session.payers
                        ),
                        "총 결제": f"{session.total_paid:,}원",
                        "참여자": ", ".join(
                            member_label(members, name) for name in session.participants
                        ),
                    }
                    for session in current_sessions
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 주차 수정 / 삭제")
        labels = [session_label(session, members) for session in current_sessions]

        with st.form("edit_session_form"):
            selected_label = st.selectbox("수정할 주차", labels)
            selected_index = labels.index(selected_label)
            selected = current_sessions[selected_index]

            edit_payer_count = st.number_input(
                "비용 지불자 수",
                min_value=1,
                max_value=len(names),
                value=len(selected.payers),
                step=1,
                key="edit_payer_count",
            )
            edit_payers = payer_inputs(
                members=members,
                names=names,
                payer_count=int(edit_payer_count),
                saved_payers=selected.payers,
                default_court_fee=default_fee,
                key_prefix="edit",
            )
            edit_participants = st.multiselect(
                "참여자",
                names,
                default=selected.participants,
                format_func=lambda value: member_label(members, value),
            )

            c1, c2 = st.columns(2)
            with c1:
                save_edit = st.form_submit_button("수정 저장", use_container_width=True)
            with c2:
                delete_session = st.form_submit_button(
                    "주차 삭제", use_container_width=True
                )

        if save_edit:
            if not edit_payers:
                st.error("비용 지불자와 결제 금액을 입력해 주세요.")
            elif not edit_participants:
                st.error("참여자를 1명 이상 선택해 주세요.")
            elif len({payer.name for payer in edit_payers}) != len(edit_payers):
                st.error("같은 사람을 비용 지불자로 중복 선택할 수 없습니다.")
            else:
                current_sessions[selected_index] = Session(
                    week=selected.week,
                    payers=edit_payers,
                    participants=edit_participants,
                )
                save_sessions(reg_y, reg_m, current_sessions)
                st.success(f"{selected.week}주차를 수정했습니다.")
                st.rerun()

        if delete_session:
            current_sessions.pop(selected_index)
            save_sessions(reg_y, reg_m, current_sessions)
            st.success(f"{selected.week}주차 기록을 삭제했습니다.")
            st.rerun()

with tab_settings:
    st.subheader("모임 설정")
    st.caption(
        "형식: `이름(닉네임)` 또는 `이름(닉네임) - 다둥이` · "
        "닉네임은 코트 대관 예약 시 사용합니다."
    )

    with st.form("settings_form"):
        members_text = st.text_area(
            "멤버 목록 (한 줄에 한 명)",
            value=members_to_text(members),
            height=180,
        )
        default_court_fee = st.number_input(
            "기본 코트비 (원, 등록 시 기본값)",
            min_value=0,
            step=500,
            value=default_fee,
        )
        weeks = st.number_input(
            "월별 모임 횟수",
            min_value=1,
            max_value=5,
            value=weeks_per_month,
        )
        save_clicked = st.form_submit_button("설정 저장", use_container_width=True)

    if save_clicked:
        try:
            new_members = parse_members_text(members_text)
        except ValueError as error:
            st.error(f"멤버 형식 오류: {error}")
        else:
            if len(new_members) < 2:
                st.error("멤버는 최소 2명 이상이어야 합니다.")
            else:
                new_config = {
                    "members": new_members,
                    "default_court_fee": int(default_court_fee),
                    "weeks_per_month": int(weeks),
                }
                save_config(new_config)
                st.session_state.config = new_config
                st.success("설정을 저장했습니다.")
                st.rerun()

    st.markdown("#### 멤버 안내")
    for member in members:
        badge = " · **다둥이 혜택 가능 (5,500원)**" if member.get("twins_benefit") else ""
        st.write(f"- {format_member(member)}{badge}")

st.divider()
st.markdown(
    "**정산 규칙** · 총 결제액 ÷ 참여 인원 = 1인 부담 · "
    "비용 지불자는 송금하지 않음 · 미납자는 지불자별 결제 비율로 분배"
)
