import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import (
    create_all_tables,
    add_bill,
    get_user_bills,
    save_ai_profile,
    get_ai_profile
)

st.set_page_config(page_title="Financial Assistant", layout="wide")
create_all_tables()

if "user" not in st.session_state:
    st.session_state.user = None

if "bill_message" not in st.session_state:
    st.session_state.bill_message = ""

if "ai_profile_message" not in st.session_state:
    st.session_state.ai_profile_message = ""

if "ai_response" not in st.session_state:
    st.session_state.ai_response = ""


def suggest_bill_details(bill_name_text):
    text = bill_name_text.strip().lower()

    if any(word in text for word in ["electric", "electricity", "water", "internet", "wifi", "phone", "power", "gas"]):
        return "Utilities", "High", "Monthly"

    if "rent" in text:
        return "Rent", "Critical", "Monthly"

    if any(word in text for word in ["loan", "mortgage", "credit", "credit card"]):
        return "Loan", "Critical", "Monthly"

    if any(word in text for word in ["netflix", "spotify", "chatgpt", "canva", "subscription"]):
        return "Subscription", "Medium", "Monthly"

    if any(word in text for word in ["shop", "shopping", "grocery", "market"]):
        return "Shopping", "Low", "One-Time"

    return "Other", "Medium", "Monthly"


def split_saved_list(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def safe_date_value(value):
    if value:
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return date.today()
    return date.today()


def format_money(amount, currency_code):
    return f"{currency_code} {amount:,.2f}"


def logout():
    st.session_state.user = None
    st.rerun()


def build_priority_sorted_bills(df, must_pay_categories):
    if df.empty:
        return df.copy()

    temp = df.copy()
    priority_map = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}

    temp["Priority Rank"] = temp["Priority"].map(priority_map).fillna(5)
    temp["Must Pay Rank"] = temp["Category"].apply(lambda x: 0 if x in must_pay_categories else 1)

    temp = temp.sort_values(
        by=["Must Pay Rank", "Due Date", "Priority Rank", "Amount"],
        ascending=[True, True, True, False]
    )
    return temp


def generate_ai_response(question, ai_profile, active_bills_df, due_today_df, due_this_week_df, overdue_df, expected_cash_out):
    q = question.strip().lower()

    if q == "":
        return "Please type a question first."

    currency = ai_profile["currency"]
    main_income = ai_profile["main_income"]
    minimum_safe_balance = ai_profile["minimum_safe_balance"]
    must_pay_categories = ai_profile["must_pay_categories"]
    goals = ai_profile["financial_goals"]

    sorted_bills = build_priority_sorted_bills(active_bills_df, must_pay_categories)

    snapshot = (
        f"Current snapshot: {len(overdue_df)} overdue, "
        f"{len(due_today_df)} due today, "
        f"{len(due_this_week_df)} due this week, "
        f"and expected cash out of {format_money(expected_cash_out, currency)}."
    )

    # PAY FIRST
    if any(phrase in q for phrase in ["pay first", "what should i pay", "priority", "which bill first"]):
        if sorted_bills.empty:
            return "You currently have no active bills saved, so there is nothing to prioritize yet."

        top_bills = sorted_bills.head(3)

        response = snapshot + "\n\n"
        response += "Top payment priorities right now:\n"

        for i, (_, row) in enumerate(top_bills.iterrows(), start=1):
            response += (
                f"{i}. {row['Bill Name']} | "
                f"{format_money(row['Amount'], currency)} | "
                f"Due {row['Due Date'].strftime('%Y-%m-%d')} | "
                f"{row['Priority']} priority | "
                f"{row['Category']}\n"
            )

        response += "\nReasoning: I ranked bills using must-pay categories first, then due date, then priority level."
        return response

    # RISK / PRESSURE
    if any(phrase in q for phrase in ["am i at risk", "risk", "pressure", "danger", "safe", "survive this week"]):
        response = snapshot + "\n\n"

        if len(overdue_df) > 0:
            response += "Risk level looks elevated because you already have overdue bills.\n"
        elif len(due_today_df) > 0:
            response += "There is immediate pressure because you have bills due today.\n"
        else:
            response += "You do not have immediate overdue pressure right now.\n"

        if main_income > 0:
            if expected_cash_out > main_income:
                response += f"Your expected cash out is higher than your saved main income of {format_money(main_income, currency)}.\n"
            else:
                response += f"Your saved main income of {format_money(main_income, currency)} currently covers expected cash out on paper.\n"
        else:
            response += "You have not saved a main income amount yet, so the risk check is partial.\n"

        if minimum_safe_balance > 0:
            response += f"Your minimum safe balance target is {format_money(minimum_safe_balance, currency)}.\n"

        response += "For deeper accuracy later, add current balance tracking into the assistant."
        return response

    # OVERDUE
    if "overdue" in q:
        response = snapshot + "\n\n"

        if overdue_df.empty:
            response += "You currently have no overdue bills."
        else:
            response += "These bills are overdue:\n"
            for _, row in overdue_df.iterrows():
                response += f"- {row['Bill Name']} | {format_money(row['Amount'], currency)} | Due {row['Due Date'].strftime('%Y-%m-%d')}\n"

        return response

    # CASH FLOW
    if any(phrase in q for phrase in ["cash flow", "money out", "outflow", "money in", "income"]):
        response = snapshot + "\n\n"

        if main_income > 0:
            response += f"Saved main income: {format_money(main_income, currency)}.\n"
            response += f"Expected cash out from active bills: {format_money(expected_cash_out, currency)}.\n"

            if expected_cash_out > main_income:
                response += "Your bill outflow currently looks heavier than your saved income amount.\n"
            else:
                response += "Your saved income currently looks stronger than your active bill total.\n"
        else:
            response += "You have not saved your income setup yet, so cash flow analysis is limited.\n"

        return response

    # APP SUPPORT
    if any(phrase in q for phrase in ["what does due this week mean", "how do i use", "what is this page", "customer support", "help me use"]):
        return (
            "This page has 6 main areas:\n"
            "1. Bills Manager: save and track bills\n"
            "2. Cash Flow: compare expected income and expected cash out\n"
            "3. Overspending: future budget warning area\n"
            "4. Pay First: ranking of what to pay first\n"
            "5. AI Setup: stores your financial profile for smarter answers\n"
            "6. AI Assistant: answers your questions using your saved setup and bills"
        )

    # GOALS / GENERAL GUIDANCE
    response = snapshot + "\n\n"

    if goals:
        response += f"Your saved goals are: {', '.join(goals)}.\n"

    if len(overdue_df) > 0:
        response += "First recommendation: clear overdue bills before taking on optional spending.\n"
    elif len(due_today_df) > 0:
        response += "First recommendation: handle bills due today before anything non-essential.\n"
    else:
        response += "You do not have urgent bill pressure right now based on saved bill data.\n"

    if must_pay_categories:
        response += f"Your must-pay categories are: {', '.join(must_pay_categories)}.\n"

    response += "Ask me something specific like 'What should I pay first?' or 'Am I at risk this week?' for a stronger answer."
    return response


if st.session_state.user is None:
    st.title("Financial Assistant")
    st.warning("Please log in first from the main BookkeepAI page.")
    st.stop()


# =========================
# LOAD USER DATA
# =========================
user_id = st.session_state.user["id"]

bill_rows = get_user_bills(user_id)
ai_profile_row = get_ai_profile(user_id)

if bill_rows:
    bills_df = pd.DataFrame(
        bill_rows,
        columns=["ID", "Bill Name", "Amount", "Due Date", "Frequency", "Category", "Priority", "Notes", "Status"]
    )
    bills_df["Due Date"] = pd.to_datetime(bills_df["Due Date"], errors="coerce")
    bills_df = bills_df.dropna(subset=["Due Date"]).copy()
else:
    bills_df = pd.DataFrame(columns=[
        "ID", "Bill Name", "Amount", "Due Date", "Frequency", "Category", "Priority", "Notes", "Status"
    ])

today = pd.Timestamp(date.today())
week_end = pd.Timestamp(date.today() + timedelta(days=7))

if not bills_df.empty:
    active_bills_df = bills_df[bills_df["Status"] == "Active"].copy()

    due_today_df = active_bills_df[active_bills_df["Due Date"].dt.date == date.today()].copy()
    due_this_week_df = active_bills_df[
        (active_bills_df["Due Date"] >= today) &
        (active_bills_df["Due Date"] <= week_end)
    ].copy()
    overdue_df = active_bills_df[active_bills_df["Due Date"] < today].copy()

    expected_cash_out = active_bills_df["Amount"].sum()
else:
    active_bills_df = bills_df.copy()
    due_today_df = bills_df.copy()
    due_this_week_df = bills_df.copy()
    overdue_df = bills_df.copy()
    expected_cash_out = 0.0

if ai_profile_row:
    ai_profile = {
        "user_type": ai_profile_row[0] or "Personal",
        "currency": ai_profile_row[1] or "PHP",
        "response_style": ai_profile_row[2] or "Clear and Practical",
        "pay_frequency": ai_profile_row[3] or "Monthly",
        "main_income": ai_profile_row[4] or 0.0,
        "next_pay_date": safe_date_value(ai_profile_row[5]),
        "other_income_notes": ai_profile_row[6] or "",
        "minimum_safe_balance": ai_profile_row[7] or 0.0,
        "emergency_reserve_target": ai_profile_row[8] or 0.0,
        "never_touch_amount": ai_profile_row[9] or 0.0,
        "must_pay_categories": split_saved_list(ai_profile_row[10]),
        "can_delay_categories": split_saved_list(ai_profile_row[11]),
        "priority_style": ai_profile_row[12] or "Essential first",
        "financial_goals": split_saved_list(ai_profile_row[13]),
        "support_mode": ai_profile_row[14] or "Action Steps"
    }
else:
    ai_profile = {
        "user_type": "Personal",
        "currency": "PHP",
        "response_style": "Clear and Practical",
        "pay_frequency": "Monthly",
        "main_income": 0.0,
        "next_pay_date": date.today(),
        "other_income_notes": "",
        "minimum_safe_balance": 0.0,
        "emergency_reserve_target": 0.0,
        "never_touch_amount": 0.0,
        "must_pay_categories": [],
        "can_delay_categories": [],
        "priority_style": "Essential first",
        "financial_goals": [],
        "support_mode": "Action Steps"
    }


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.subheader("Account")
    st.write(f"**Name:** {st.session_state.user['full_name']}")
    st.write(f"**Email:** {st.session_state.user['email']}")

    if st.button("Logout", key="financial_assistant_logout"):
        logout()


# =========================
# PAGE HEADER
# =========================
st.title("Financial Assistant")
st.write("A separate planning and control page for bills, cash flow, spending alerts, payment priorities, AI setup, and a live in-app assistant.")

if st.session_state.bill_message:
    st.success(st.session_state.bill_message)
    st.session_state.bill_message = ""

if st.session_state.ai_profile_message:
    st.success(st.session_state.ai_profile_message)
    st.session_state.ai_profile_message = ""

st.info(
    "Bills Manager is connected. AI Setup stores the profile. AI Assistant is now live inside this page."
)


# =========================
# TOP SUMMARY ROW
# =========================
m1, m2, m3, m4 = st.columns(4)
m1.metric("Bills Due Soon", str(len(due_this_week_df)))
m2.metric("Expected Cash In", f"{ai_profile['main_income']:,.2f}")
m3.metric("Expected Cash Out", f"{expected_cash_out:,.2f}")
m4.metric("Budget Alerts", "0")


# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Bills Manager",
    "Cash Flow",
    "Overspending",
    "Pay First",
    "AI Setup",
    "AI Assistant"
])


# =========================
# TAB 1 - BILLS MANAGER
# =========================
with tab1:
    st.subheader("Bills Manager")
    st.write("This section stores recurring bills, due dates, priority levels, and reminders.")

    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.markdown("### Add Bill")

        with st.form("add_bill_form"):
            bill_name_input = st.text_input("Bill Name")
            bill_amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
            due_date = st.date_input("Due Date", value=date.today())

            auto_category, auto_priority, auto_frequency = suggest_bill_details(bill_name_input)

            frequency_options = ["One-Time", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Yearly"]
            frequency_index = frequency_options.index(auto_frequency) if auto_frequency in frequency_options else 3
            frequency = st.selectbox("Frequency", frequency_options, index=frequency_index)

            days_until_due = (due_date - date.today()).days
            if days_until_due < 0:
                st.caption(f"Status Preview: Overdue by {abs(days_until_due)} day(s)")
            elif days_until_due == 0:
                st.caption("Status Preview: Due today")
            else:
                st.caption(f"Status Preview: Due in {days_until_due} day(s)")

            st.markdown(f"**Auto Category:** {auto_category}")
            st.markdown(f"**Auto Priority:** {auto_priority}")

            notes = st.text_area("Notes (optional)")

            save_bill_submitted = st.form_submit_button("Save Bill")

            if save_bill_submitted:
                if bill_name_input.strip() == "":
                    st.warning("Please enter a bill name.")
                elif bill_amount <= 0:
                    st.warning("Amount must be greater than zero.")
                else:
                    add_bill(
                        user_id=user_id,
                        bill_name=bill_name_input.strip().title(),
                        amount=float(bill_amount),
                        due_date=str(due_date),
                        frequency=frequency,
                        category=auto_category,
                        priority=auto_priority,
                        notes=notes.strip()
                    )
                    st.session_state.bill_message = "Bill saved successfully."
                    st.rerun()

    with col2:
        st.markdown("### Bill Overview")

        overview1, overview2, overview3 = st.columns(3)
        overview1.metric("Due Today", str(len(due_today_df)))
        overview2.metric("Due This Week", str(len(due_this_week_df)))
        overview3.metric("Overdue", str(len(overdue_df)))

        st.markdown("#### Upcoming Bills")
        if not active_bills_df.empty:
            upcoming_display = active_bills_df[[
                "Bill Name", "Amount", "Due Date", "Frequency", "Priority", "Status"
            ]].copy()
            upcoming_display["Due Date"] = upcoming_display["Due Date"].dt.strftime("%Y-%m-%d")
            st.dataframe(upcoming_display, use_container_width=True, hide_index=True)
        else:
            st.info("No saved bills yet.")

        st.markdown("#### Reminder Panel")
        if not overdue_df.empty:
            for _, row in overdue_df.iterrows():
                st.error(
                    f"Overdue: {row['Bill Name']} | {format_money(row['Amount'], ai_profile['currency'])} | Due {row['Due Date'].strftime('%Y-%m-%d')}"
                )

        if not due_today_df.empty:
            for _, row in due_today_df.iterrows():
                st.warning(
                    f"Due Today: {row['Bill Name']} | {format_money(row['Amount'], ai_profile['currency'])}"
                )

        if overdue_df.empty and due_today_df.empty and active_bills_df.empty:
            st.info("No bill reminders yet.")

    st.markdown("### Saved Bills")
    if not bills_df.empty:
        saved_bills_display = bills_df[[
            "ID", "Bill Name", "Amount", "Due Date", "Frequency", "Category", "Priority", "Notes", "Status"
        ]].copy()
        saved_bills_display["Due Date"] = saved_bills_display["Due Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(saved_bills_display, use_container_width=True, hide_index=True)
    else:
        st.info("No saved bills yet.")


# =========================
# TAB 2 - CASH FLOW
# =========================
with tab2:
    st.subheader("Cash Flow Forecast")
    st.write("This section will estimate what your money situation may look like over the next few days or weeks.")

    c1, c2 = st.columns([1, 1.3])

    with c1:
        st.markdown("### Forecast Inputs")
        current_balance = st.number_input("Current Balance", min_value=0.0, step=0.01, format="%.2f")
        expected_income = st.number_input("Expected Income", min_value=0.0, value=float(ai_profile["main_income"]), step=0.01, format="%.2f")
        extra_expected_expenses = st.number_input("Extra Expected Expenses", min_value=0.0, step=0.01, format="%.2f")
        forecast_days = st.selectbox("Forecast Window", [7, 14, 30, 60, 90])

    with c2:
        st.markdown("### Forecast Summary")

        projected_end_balance = current_balance + expected_income - extra_expected_expenses - expected_cash_out

        f1, f2, f3 = st.columns(3)
        f1.metric("Current Balance", f"{current_balance:,.2f}")
        f2.metric("Projected End Balance", f"{projected_end_balance:,.2f}")
        f3.metric("Forecast Days", str(forecast_days))

        st.markdown("#### Forecast Timeline")
        forecast_df = pd.DataFrame({
            "Date": pd.date_range(start=date.today(), periods=forecast_days, freq="D"),
            "Projected Balance": [projected_end_balance for _ in range(forecast_days)]
        })
        st.line_chart(forecast_df.set_index("Date"))

        st.caption("Next step later: use real timing of income and due dates in the forecast.")


# =========================
# TAB 3 - OVERSPENDING
# =========================
with tab3:
    st.subheader("Overspending Warnings")
    st.write("This section will compare budget limits against actual spending and warn the user when spending gets too high.")

    o1, o2 = st.columns([1, 1.3])

    with o1:
        st.markdown("### Budget Setup")
        budget_month = st.selectbox("Budget Month", [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])
        budget_category = st.selectbox("Budget Category", [
            "Utilities", "Transportation", "Marketing", "Office Supplies",
            "Software & Subscriptions", "Meals & Entertainment", "Travel",
            "Equipment", "Salary", "Bank Fees", "Tax", "Personal", "Other"
        ])
        budget_limit = st.number_input("Budget Limit", min_value=0.0, step=0.01, format="%.2f")
        warning_threshold = st.slider("Warning Threshold (%)", min_value=50, max_value=100, value=80)

    with o2:
        st.markdown("### Budget Alert Overview")

        alert1, alert2, alert3 = st.columns(3)
        alert1.metric("Safe", "0")
        alert2.metric("Near Limit", "0")
        alert3.metric("Over Budget", "0")

        overspending_df = pd.DataFrame(columns=[
            "Category", "Budget Limit", "Actual Spend", "Usage %", "Status"
        ])
        st.dataframe(overspending_df, use_container_width=True, hide_index=True)

        st.warning("Budget saving and overspending logic will be connected next in a future step.")


# =========================
# TAB 4 - PAY FIRST
# =========================
with tab4:
    st.subheader("What to Pay First")
    st.write("This section will help rank bills by urgency, priority, due date, and payment risk.")

    p1, p2 = st.columns([1, 1.3])

    with p1:
        st.markdown("### Priority Rules Preview")
        st.markdown("""
        The future ranking logic can consider:
        - overdue bills first
        - critical bills first
        - bills with near due dates
        - bills with penalty risk
        - essential bills before non-essential bills
        """)

        available_cash = st.number_input("Available Cash", min_value=0.0, step=0.01, format="%.2f")

    with p2:
        st.markdown("### Suggested Payment Order")

        if not active_bills_df.empty:
            pay_first_df = build_priority_sorted_bills(active_bills_df, ai_profile["must_pay_categories"])

            pay_first_display = pay_first_df[[
                "Bill Name", "Amount", "Due Date", "Priority", "Category"
            ]].copy()
            pay_first_display["Due Date"] = pay_first_display["Due Date"].dt.strftime("%Y-%m-%d")
            st.dataframe(pay_first_display, use_container_width=True, hide_index=True)
        else:
            st.info("No bills available yet for payment ranking.")


# =========================
# TAB 5 - AI SETUP
# =========================
with tab5:
    st.subheader("AI Setup")
    st.write("This is where you feed the expert assistant the information it needs about the user.")

    setup_col1, setup_col2 = st.columns([1, 1])

    with setup_col1:
        st.markdown("### AI Profile Form")

        with st.form("ai_profile_form"):
            user_type = st.selectbox("User Type", ["Personal", "Business"], index=["Personal", "Business"].index(ai_profile["user_type"]))
            currency = st.selectbox("Currency", ["PHP", "AUD", "USD"], index=["PHP", "AUD", "USD"].index(ai_profile["currency"]) if ai_profile["currency"] in ["PHP", "AUD", "USD"] else 0)
            response_style = st.selectbox(
                "Response Style",
                ["Clear and Practical", "Detailed Coach", "Strict and Direct", "Supportive"],
                index=["Clear and Practical", "Detailed Coach", "Strict and Direct", "Supportive"].index(ai_profile["response_style"]) if ai_profile["response_style"] in ["Clear and Practical", "Detailed Coach", "Strict and Direct", "Supportive"] else 0
            )

            pay_frequency = st.selectbox(
                "Main Income Frequency",
                ["Weekly", "Bi-Weekly", "Monthly", "Variable"],
                index=["Weekly", "Bi-Weekly", "Monthly", "Variable"].index(ai_profile["pay_frequency"]) if ai_profile["pay_frequency"] in ["Weekly", "Bi-Weekly", "Monthly", "Variable"] else 2
            )

            main_income = st.number_input("Main Income", min_value=0.0, value=float(ai_profile["main_income"]), step=0.01, format="%.2f")
            next_pay_date = st.date_input("Next Pay Date", value=ai_profile["next_pay_date"])
            other_income_notes = st.text_area("Other Income Notes", value=ai_profile["other_income_notes"])

            minimum_safe_balance = st.number_input("Minimum Safe Balance", min_value=0.0, value=float(ai_profile["minimum_safe_balance"]), step=0.01, format="%.2f")
            emergency_reserve_target = st.number_input("Emergency Reserve Target", min_value=0.0, value=float(ai_profile["emergency_reserve_target"]), step=0.01, format="%.2f")
            never_touch_amount = st.number_input("Never-Touch Amount", min_value=0.0, value=float(ai_profile["never_touch_amount"]), step=0.01, format="%.2f")

            all_categories = ["Utilities", "Rent", "Loan", "Subscription", "Shopping", "Other"]
            must_pay_categories = st.multiselect("Must-Pay Categories", all_categories, default=ai_profile["must_pay_categories"])
            can_delay_categories = st.multiselect("Can-Delay Categories", all_categories, default=ai_profile["can_delay_categories"])

            priority_style = st.selectbox(
                "Priority Style",
                ["Essential first", "Urgent first", "Lowest amount first", "Highest amount first"],
                index=["Essential first", "Urgent first", "Lowest amount first", "Highest amount first"].index(ai_profile["priority_style"]) if ai_profile["priority_style"] in ["Essential first", "Urgent first", "Lowest amount first", "Highest amount first"] else 0
            )

            goal_options = [
                "Avoid overdue bills",
                "Improve monthly cash flow",
                "Build savings",
                "Reduce debt",
                "Stay above safe balance"
            ]
            financial_goals = st.multiselect("Financial Goals", goal_options, default=ai_profile["financial_goals"])

            support_mode = st.selectbox(
                "Support Mode",
                ["Action Steps", "Quick Answers", "Deep Explanation", "App Support"],
                index=["Action Steps", "Quick Answers", "Deep Explanation", "App Support"].index(ai_profile["support_mode"]) if ai_profile["support_mode"] in ["Action Steps", "Quick Answers", "Deep Explanation", "App Support"] else 0
            )

            save_ai_setup = st.form_submit_button("Save AI Setup")

            if save_ai_setup:
                save_ai_profile(
                    user_id=user_id,
                    user_type=user_type,
                    currency=currency,
                    response_style=response_style,
                    pay_frequency=pay_frequency,
                    main_income=float(main_income),
                    next_pay_date=str(next_pay_date),
                    other_income_notes=other_income_notes.strip(),
                    minimum_safe_balance=float(minimum_safe_balance),
                    emergency_reserve_target=float(emergency_reserve_target),
                    never_touch_amount=float(never_touch_amount),
                    must_pay_categories=",".join(must_pay_categories),
                    can_delay_categories=",".join(can_delay_categories),
                    priority_style=priority_style,
                    financial_goals=",".join(financial_goals),
                    support_mode=support_mode
                )
                st.session_state.ai_profile_message = "AI Setup saved successfully."
                st.rerun()

    with setup_col2:
        st.markdown("### What the AI Will Learn")
        profile_summary = pd.DataFrame({
            "Field": [
                "User Type",
                "Currency",
                "Response Style",
                "Main Income Frequency",
                "Main Income",
                "Next Pay Date",
                "Minimum Safe Balance",
                "Emergency Reserve Target",
                "Never-Touch Amount",
                "Must-Pay Categories",
                "Can-Delay Categories",
                "Priority Style",
                "Financial Goals",
                "Support Mode"
            ],
            "Value": [
                ai_profile["user_type"],
                ai_profile["currency"],
                ai_profile["response_style"],
                ai_profile["pay_frequency"],
                f"{ai_profile['main_income']:,.2f}",
                str(ai_profile["next_pay_date"]),
                f"{ai_profile['minimum_safe_balance']:,.2f}",
                f"{ai_profile['emergency_reserve_target']:,.2f}",
                f"{ai_profile['never_touch_amount']:,.2f}",
                ", ".join(ai_profile["must_pay_categories"]) if ai_profile["must_pay_categories"] else "-",
                ", ".join(ai_profile["can_delay_categories"]) if ai_profile["can_delay_categories"] else "-",
                ai_profile["priority_style"],
                ", ".join(ai_profile["financial_goals"]) if ai_profile["financial_goals"] else "-",
                ai_profile["support_mode"]
            ]
        })
        st.dataframe(profile_summary, use_container_width=True, hide_index=True)

        st.info(
            "This saved profile becomes the background context of the assistant."
        )


# =========================
# TAB 6 - AI ASSISTANT
# =========================
with tab6:
    st.subheader("AI Assistant")
    st.write("Ask for financial guidance, bill prioritization, risk checks, or help using the page.")

    a1, a2 = st.columns([1.2, 1])

    with a1:
        st.markdown("### Ask the Assistant")
        user_question = st.text_area(
            "Type your question here",
            placeholder="Example: What should I pay first this week?"
        )

        ask_ai = st.button("Ask Assistant")

        if ask_ai:
            st.session_state.ai_response = generate_ai_response(
                question=user_question,
                ai_profile=ai_profile,
                active_bills_df=active_bills_df,
                due_today_df=due_today_df,
                due_this_week_df=due_this_week_df,
                overdue_df=overdue_df,
                expected_cash_out=expected_cash_out
            )

        st.markdown("### Assistant Response")
        if st.session_state.ai_response:
            st.text(st.session_state.ai_response)
        else:
            st.info("No response yet. Ask a question to make the assistant work.")

    with a2:
        st.markdown("### What the Assistant Sees")

        assistant_context_df = pd.DataFrame({
            "Context": [
                "Currency",
                "Main Income",
                "Must-Pay Categories",
                "Goals",
                "Bills Due Today",
                "Bills Due This Week",
                "Overdue Bills",
                "Expected Cash Out"
            ],
            "Value": [
                ai_profile["currency"],
                f"{ai_profile['main_income']:,.2f}",
                ", ".join(ai_profile["must_pay_categories"]) if ai_profile["must_pay_categories"] else "-",
                ", ".join(ai_profile["financial_goals"]) if ai_profile["financial_goals"] else "-",
                str(len(due_today_df)),
                str(len(due_this_week_df)),
                str(len(overdue_df)),
                f"{expected_cash_out:,.2f}"
            ]
        })
        st.dataframe(assistant_context_df, use_container_width=True, hide_index=True)

        st.markdown("### Good Questions to Try")
        st.info(
            "Try questions like:\n"
            "- What should I pay first?\n"
            "- Am I at risk this week?\n"
            "- Which bills are overdue?\n"
            "- Explain this page to me."
        )