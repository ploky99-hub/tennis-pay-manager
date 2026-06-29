from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from calculator import Absence, calculate_settlement
from storage import load_absences, load_config, save_absences, save_config

st.set_page_config(
    page_title="강동 테린이 꿈나무방 정산",
    page_icon="🎾",
    layout="wide",
)

ABSENCE_LABELS = {
    "day_before": "하루 전 불참 (익월 회비 차감)",
    "same_day": "당일 불참 (차감 없음, 코트비 부담)",
}


def absence_label(absence_type: str) -> str:
    return ABSENCE_LABELS.get(absence_type, absence_type)


def init_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = load_config()


init_state()
config = st.session_state.config

st.title("🎾 강동 테린이 꿈나무방 정산")
st.caption(
    f"기본 월 회비 **{config['base_monthly_fee']:,}원** · "
    f"코트비 **{config['court_fee']:,}원**/회 · "
    f"{config['absence_deadline_note']}"
)

tab_dashboard, tab_register, tab_settings = st.tabs(
    ["📊 정산 현황", "📝 불참 등록", "⚙️ 설정"]
)

today = date.today()
with tab_dashboard:
    col_y, col_m = st.columns(2)
    with col_y:
        year = st.number_input("연도", min_value=2024, max_value=2035, value=today.year)
    with col_m:
        month = st.selectbox("월", list(range(1, 13)), index=today.month - 1)

    absences = load_absences(year, month)
    week_rows, member_rows = calculate_settlement(
        members=config["members"],
        absences=absences,
        court_fee=config["court_fee"],
        base_monthly_fee=config["base_monthly_fee"],
        weeks_per_month=config["weeks_per_month"],
    )

    total_court_cost = config["court_fee"] * config["weeks_per_month"]

    m1, m2, m3 = st.columns(3)
    m1.metric("이번 달 예상 코트비", f"{total_court_cost:,}원")
    m2.metric("멤버 수", f"{len(config['members'])}명")
    m3.metric("등록된 불참", f"{len(absences)}건")

    st.subheader("다음 달 납부 회비")
    member_df = pd.DataFrame(
        [
            {
                "이름": row.name,
                "하루 전 불참": f"{row.day_before_count}회",
                "당일 불참": f"{row.same_day_count}회",
                "이번 달 차감액": f"{row.refund:,}원",
                "다음 달 납부 회비": f"{row.next_month_fee:,}원",
            }
            for row in member_rows
        ]
    )
    st.dataframe(member_df, use_container_width=True, hide_index=True)

    st.subheader("주차별 정산 내역")
    week_df = pd.DataFrame(
        [
            {
                "주차": f"{row.week}주차",
                "정산 인원": f"{row.participants}명",
                "1인당 부담": f"{row.share_per_person:,}원",
                "하루 전 불참": ", ".join(row.day_before_absent) or "-",
                "당일 불참": ", ".join(row.same_day_absent) or "-",
            }
            for row in week_rows
        ]
    )
    st.dataframe(week_df, use_container_width=True, hide_index=True)

    with st.expander("이번 달 불참 기록"):
        if absences:
            record_df = pd.DataFrame(
                [
                    {
                        "이름": a.name,
                        "주차": f"{a.week}주차",
                        "유형": absence_label(a.absence_type),
                    }
                    for a in absences
                ]
            )
            st.dataframe(record_df, use_container_width=True, hide_index=True)
            st.caption("개별 수정·삭제는 **불참 등록** 탭에서 할 수 있습니다.")

            if st.button("이번 달 기록 전체 삭제", type="primary"):
                save_absences(year, month, [])
                st.success("기록을 초기화했습니다.")
                st.rerun()
        else:
            st.info("등록된 불참 기록이 없습니다.")

with tab_register:
    st.subheader("불참 / 사정 등록")
    reg_y = st.number_input(
        "등록 연도", min_value=2024, max_value=2035, value=today.year, key="reg_year"
    )
    reg_m = st.selectbox(
        "등록 월", list(range(1, 13)), index=today.month - 1, key="reg_month"
    )
    current_absences = load_absences(reg_y, reg_m)

    with st.form("absence_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.selectbox("이름", config["members"])
        with c2:
            week = st.selectbox(
                "주차",
                list(range(1, config["weeks_per_month"] + 1)),
                format_func=lambda w: f"{w}주차",
            )
        with c3:
            absence_type = st.selectbox(
                "불참 유형",
                ["day_before", "same_day"],
                format_func=lambda t: ABSENCE_LABELS[t],
            )

        submitted = st.form_submit_button("등록하기", use_container_width=True)

    if submitted:
        updated = False
        for absence in current_absences:
            if absence.name == name and absence.week == week:
                absence.absence_type = absence_type
                updated = True
                break
        if updated:
            save_absences(reg_y, reg_m, current_absences)
            st.success(
                f"[{reg_y}년 {reg_m}월 {week}주차] {name}님 — "
                f"{absence_label(absence_type)}(으)로 수정했습니다."
            )
        else:
            current_absences.append(
                Absence(name=name, week=week, absence_type=absence_type)
            )
            save_absences(reg_y, reg_m, current_absences)
            st.success(
                f"[{reg_y}년 {reg_m}월 {week}주차] {name}님 — "
                f"{absence_label(absence_type)} 등록 완료!"
            )
        st.rerun()

    if current_absences:
        st.markdown("#### 현재 등록된 기록")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "이름": a.name,
                        "주차": f"{a.week}주차",
                        "유형": absence_label(a.absence_type),
                    }
                    for a in current_absences
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### 기록 수정 / 삭제")
        st.caption(
            "사정이 바뀌어 다시 참석하면 **참석으로 변경**을 누르세요. "
            "불참 유형만 바꿀 수도 있습니다."
        )

        record_labels = [
            f"{a.name} · {a.week}주차 · {absence_label(a.absence_type)}"
            for a in current_absences
        ]

        with st.form("edit_absence_form"):
            selected_label = st.selectbox("수정할 기록", record_labels)
            selected_idx = record_labels.index(selected_label)
            selected = current_absences[selected_idx]

            new_type = st.selectbox(
                "변경할 불참 유형",
                ["day_before", "same_day"],
                index=0 if selected.absence_type == "day_before" else 1,
                format_func=lambda t: ABSENCE_LABELS[t],
                key="edit_absence_type",
            )

            c1, c2 = st.columns(2)
            with c1:
                save_edit = st.form_submit_button(
                    "유형 변경 저장", use_container_width=True
                )
            with c2:
                mark_attending = st.form_submit_button(
                    "참석으로 변경 (삭제)", use_container_width=True
                )

        if save_edit:
            current_absences[selected_idx].absence_type = new_type
            save_absences(reg_y, reg_m, current_absences)
            st.success(f"{selected.name}님 {selected.week}주차 기록을 수정했습니다.")
            st.rerun()

        if mark_attending:
            current_absences.pop(selected_idx)
            save_absences(reg_y, reg_m, current_absences)
            st.success(
                f"{selected.name}님 {selected.week}주차 불참 기록을 삭제했습니다. "
                "참석으로 반영됩니다."
            )
            st.rerun()

with tab_settings:
    st.subheader("모임 설정")
    st.info(
        "멤버 이름, 코트비, 월 회비를 수정할 수 있습니다. "
        "변경 사항은 서버에 저장됩니다."
    )

    with st.form("settings_form"):
        members_text = st.text_area(
            "멤버 목록 (한 줄에 한 명)",
            value="\n".join(config["members"]),
            height=150,
        )
        court_fee = st.number_input(
            "코트비 (원/회)",
            min_value=1000,
            step=500,
            value=config["court_fee"],
        )
        base_fee = st.number_input(
            "기본 월 회비 (원)",
            min_value=1000,
            step=1000,
            value=config["base_monthly_fee"],
        )
        weeks = st.number_input(
            "월별 모임 횟수",
            min_value=1,
            max_value=5,
            value=config["weeks_per_month"],
        )
        deadline_note = st.text_input(
            "하루 전 불참 기준 안내 문구",
            value=config["absence_deadline_note"],
        )
        save_clicked = st.form_submit_button("설정 저장", use_container_width=True)

    if save_clicked:
        members = [line.strip() for line in members_text.splitlines() if line.strip()]
        if len(members) < 2:
            st.error("멤버는 최소 2명 이상이어야 합니다.")
        else:
            new_config = {
                "members": members,
                "court_fee": int(court_fee),
                "base_monthly_fee": int(base_fee),
                "weeks_per_month": int(weeks),
                "absence_deadline_note": deadline_note.strip(),
            }
            save_config(new_config)
            st.session_state.config = new_config
            st.success("설정을 저장했습니다.")
            st.rerun()

st.divider()
st.markdown(
    "**정산 규칙** · 하루 전 불참: 해당 주 코트비 n분의 1만큼 익월 회비에서 차감 · "
    "당일 불참: 차감 없음 (출석한 것과 동일하게 코트비 부담)"
)
