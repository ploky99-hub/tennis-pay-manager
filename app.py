from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from calculator import Session, calculate_member_totals, calculate_monthly_settlements
from storage import load_config, load_sessions, save_config, save_sessions


def init_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = load_config()


def session_label(session: Session) -> str:
    names = ", ".join(session.participants)
    return (
        f"{session.week}주차 · {session.payer} · "
        f"{session.amount_paid:,}원 · 참여 {len(session.participants)}명 ({names})"
    )


init_state()
config = st.session_state.config
members = config["members"]
default_fee = config.get("default_court_fee", 11000)
weeks_per_month = config.get("weeks_per_month", 4)

st.set_page_config(
    page_title="강동 테린이 꿈나무방 정산",
    page_icon="🎾",
    layout="wide",
)

st.title("🎾 강동 테린이 꿈나무방 정산")
st.caption("매주 코트비를 선결제한 총무에게, 참여자들이 1/N으로 송금합니다.")

tab_dashboard, tab_register, tab_settings = st.tabs(
    ["📊 정산 현황", "📝 주차 등록", "⚙️ 설정"]
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
        f"{sum(session.amount_paid for session in sessions):,}원",
    )

    if not settlements:
        st.info("**주차 등록** 탭에서 주차별 총무, 결제 금액, 참여자를 등록해 주세요.")
    else:
        for settlement in settlements:
            st.subheader(f"{settlement.week}주차 송금 안내")
            st.caption(
                f"**{settlement.payer}**님이 **{settlement.amount_paid:,}원** 선결제 · "
                f"참여 {len(settlement.participants)}명 · "
                f"1인당 **{settlement.share_per_person:,}원**"
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "이름": payment.name,
                            f"{settlement.payer}에게": (
                                f"{payment.amount:,}원"
                                if payment.amount > 0
                                else "-"
                            ),
                            "안내": payment.note,
                        }
                        for payment in settlement.payments
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

        member_totals = calculate_member_totals(settlements)
        if member_totals:
            st.subheader("이번 달 누적 송금 요약")
            payer_names = sorted(
                {payer for item in member_totals for payer in item.total_to_payer}
            )
            summary_rows = []
            for item in member_totals:
                row = {"이름": item.name}
                for payer in payer_names:
                    amount = item.total_to_payer.get(payer, 0)
                    row[f"{payer}에게"] = f"{amount:,}원" if amount > 0 else "-"
                summary_rows.append(row)
            st.dataframe(
                pd.DataFrame(summary_rows),
                use_container_width=True,
                hide_index=True,
            )

with tab_register:
    st.subheader("주차별 코트비 등록")
    st.caption(
        "해당 주에 코트비를 낸 사람, 실제 결제 금액, 참여자를 입력하세요. "
        "다둥이 할인 등으로 5,500원이어도 그대로 입력하면 됩니다."
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
        payer = st.selectbox("비용 지불자 (총무)", members)
        amount_paid = st.number_input(
            "실제 결제 금액 (원)",
            min_value=0,
            step=500,
            value=default_fee,
        )
        participants = st.multiselect(
            "참여자",
            members,
            default=members,
            help="그날 코트에 나온 사람만 선택하세요.",
        )
        submitted = st.form_submit_button("등록하기", use_container_width=True)

    if submitted:
        if amount_paid <= 0:
            st.error("결제 금액을 입력해 주세요.")
        elif not participants:
            st.error("참여자를 1명 이상 선택해 주세요.")
        else:
            new_session = Session(
                week=week,
                payer=payer,
                amount_paid=int(amount_paid),
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
                        "비용 지불자": session.payer,
                        "결제 금액": f"{session.amount_paid:,}원",
                        "참여자": ", ".join(session.participants),
                    }
                    for session in current_sessions
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 주차 수정 / 삭제")
        labels = [session_label(session) for session in current_sessions]

        with st.form("edit_session_form"):
            selected_label = st.selectbox("수정할 주차", labels)
            selected_index = labels.index(selected_label)
            selected = current_sessions[selected_index]

            edit_payer = st.selectbox(
                "비용 지불자 (총무)",
                members,
                index=members.index(selected.payer),
            )
            edit_amount = st.number_input(
                "실제 결제 금액 (원)",
                min_value=0,
                step=500,
                value=selected.amount_paid,
            )
            edit_participants = st.multiselect(
                "참여자",
                members,
                default=selected.participants,
            )

            c1, c2 = st.columns(2)
            with c1:
                save_edit = st.form_submit_button("수정 저장", use_container_width=True)
            with c2:
                delete_session = st.form_submit_button(
                    "주차 삭제", use_container_width=True
                )

        if save_edit:
            if edit_amount <= 0:
                st.error("결제 금액을 입력해 주세요.")
            elif not edit_participants:
                st.error("참여자를 1명 이상 선택해 주세요.")
            else:
                current_sessions[selected_index] = Session(
                    week=selected.week,
                    payer=edit_payer,
                    amount_paid=int(edit_amount),
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

    with st.form("settings_form"):
        members_text = st.text_area(
            "멤버 목록 (한 줄에 한 명)",
            value="\n".join(members),
            height=150,
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
        new_members = [
            line.strip() for line in members_text.splitlines() if line.strip()
        ]
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

st.divider()
st.markdown(
    "**정산 규칙** · 해당 주 결제 금액 ÷ 참여 인원 = 1인당 송금액 · "
    "비용 지불자 본인은 송금하지 않음"
)
