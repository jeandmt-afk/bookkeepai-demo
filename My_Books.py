import streamlit as st
import pandas as pd
from datetime import date
from database import create_all_tables, add_transaction, get_all_transactions, delete_transaction
from classifier import classify_transaction
from auth import register_user, login_user

st.set_page_config(page_title="BookkeepAI", layout="wide")
create_all_tables()

if "user" not in st.session_state:
    st.session_state.user = None


def inject_premium_css():
    st.markdown("""
    <style>
    .stApp {
        background:
            radial-gradient(circle at 10% 10%, rgba(0, 173, 181, 0.12), transparent 24%),
            radial-gradient(circle at 90% 10%, rgba(111, 66, 193, 0.16), transparent 24%),
            radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 0.05), transparent 30%),
            linear-gradient(180deg, #050814 0%, #070b16 45%, #04070d 100%);
        color: #f5f7fb;
    }

    .main .block-container {
        max-width: 1450px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .glass-hero {
        background: rgba(15, 20, 34, 0.66);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 18px 40px rgba(0,0,0,0.35);
        backdrop-filter: blur(22px);
        -webkit-backdrop-filter: blur(22px);
        border-radius: 28px;
        padding: 1.5rem 1.6rem;
        margin-bottom: 1rem;
        animation: fadeUp 0.55s ease;
    }

    .glass-card {
        background: rgba(13, 18, 30, 0.64);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 10px 28px rgba(0,0,0,0.28);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border-radius: 24px;
        padding: 1rem 1rem 0.85rem 1rem;
        margin-bottom: 1rem;
        animation: fadeUp 0.55s ease;
    }

    .hero-title {
        font-size: 2.35rem;
        font-weight: 800;
        line-height: 1.05;
        color: #ffffff;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }

    .hero-sub {
        color: rgba(255,255,255,0.72);
        font-size: 0.96rem;
        margin-bottom: 0;
    }

    .section-title {
        color: #ffffff;
        font-size: 1.02rem;
        font-weight: 700;
        margin-bottom: 0.15rem;
    }

    .section-sub {
        color: rgba(255,255,255,0.68);
        font-size: 0.82rem;
        margin-bottom: 0.8rem;
    }

    div.stButton > button,
    div[data-testid="stDownloadButton"] button {
        background: rgba(255,255,255,0.06) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 14px !important;
        transition: all 0.2s ease !important;
        font-weight: 600 !important;
    }

    div.stButton > button:hover,
    div[data-testid="stDownloadButton"] button:hover {
        background: rgba(255,255,255,0.11) !important;
        border-color: rgba(255,255,255,0.20) !important;
        transform: translateY(-1px);
    }

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea {
        background: rgba(255,255,255,0.04) !important;
        color: #ffffff !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }

    div[data-baseweb="select"] > div {
        background: rgba(255,255,255,0.04) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }

    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 0.85rem 0.95rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.45rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.04);
        border-radius: 14px 14px 0 0;
        padding-left: 0.9rem;
        padding-right: 0.9rem;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(255,255,255,0.11) !important;
    }

    div[data-testid="stExpander"] {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
    }

    @keyframes fadeUp {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0px);
        }
    }
    </style>
    """, unsafe_allow_html=True)


def open_glass_card(title, subtitle=""):
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)


def close_glass_card():
    st.markdown('</div>', unsafe_allow_html=True)


def logout():
    st.session_state.user = None
    st.rerun()


def render_auth_page():
    inject_premium_css()

    st.markdown("""
    <div class="glass-hero">
        <div class="hero-title">BookkeepAI</div>
        <div class="hero-sub">Secure access to your books, assistant tools, and premium workspace.</div>
    </div>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.2, 1])

    with center:
        open_glass_card("Access", "Login only for demo access")

        login_tab = st.tabs(["Login"])[0]

        with login_tab:
            with st.form("login_form"):
                login_email = st.text_input("Email")
                login_password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Login")

                if login_submitted:
                    success, result = login_user(login_email, login_password)
                    if success:
                        st.session_state.user = result
                        st.success(f"Welcome back, {result['full_name']}!")
                        st.rerun()
                    else:
                        st.error(result)

        close_glass_card()


def render_dashboard():
    inject_premium_css()

    rows = get_all_transactions()

    if rows:
        df = pd.DataFrame(
            rows,
            columns=["ID", "Description", "Amount", "Category", "Review Status", "Type", "Date"]
        )
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).copy()
    else:
        df = pd.DataFrame(columns=["ID", "Description", "Amount", "Category", "Review Status", "Type", "Date"])

    with st.sidebar:
        open_glass_card("Account")
        st.write(f"**Name:** {st.session_state.user['full_name']}")
        st.write(f"**Email:** {st.session_state.user['email']}")
        st.button("Logout", on_click=logout)
        close_glass_card()

    st.markdown(f"""
    <div class="glass-hero">
        <div class="hero-title">My Books</div>
        <div class="hero-sub">Welcome back, {st.session_state.user['full_name']}. This is your free ledger dashboard.</div>
    </div>
    """, unsafe_allow_html=True)

    action_col1, action_col2, action_col3 = st.columns([1.35, 1.25, 0.75])

    with action_col1:
        open_glass_card("Entry Center", "Add transactions or import CSV files")
        entry_tabs = st.tabs(["Add Transaction", "Import CSV"])

        with entry_tabs[0]:
            with st.form("add_transaction_form"):
                description = st.text_input("Description")
                amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
                transaction_date = st.date_input("Date", value=date.today())
                submitted = st.form_submit_button("Add Transaction")

                if submitted:
                    if description.strip() == "":
                        st.warning("Please enter a description.")
                    else:
                        category, review_status, transaction_type = classify_transaction(description)
                        add_transaction(
                            description,
                            amount,
                            category,
                            review_status,
                            transaction_type,
                            str(transaction_date)
                        )
                        st.success(f"Saved: {category} | {transaction_type}")
                        st.rerun()

        with entry_tabs[1]:
            uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
            if uploaded_file is not None:
                df_upload = pd.read_csv(uploaded_file)
                required_columns = ["Description", "Amount"]

                if all(col in df_upload.columns for col in required_columns):
                    if "Date" not in df_upload.columns:
                        df_upload["Date"] = str(date.today())

                    st.dataframe(df_upload, use_container_width=True, hide_index=True)

                    if st.button("Import CSV Transactions"):
                        for _, row in df_upload.iterrows():
                            description = str(row["Description"])
                            amount = float(row["Amount"])
                            transaction_date = str(row["Date"])

                            category, review_status, transaction_type = classify_transaction(description)

                            add_transaction(
                                description,
                                amount,
                                category,
                                review_status,
                                transaction_type,
                                transaction_date
                            )

                        st.success("CSV imported successfully.")
                        st.rerun()
                else:
                    st.error("CSV must contain at least these columns: Description, Amount")
        close_glass_card()

    with action_col2:
        open_glass_card("Control Panel", "Delete transactions and manage quick actions")
        if df.empty:
            st.info("No transactions yet.")
        else:
            delete_df = df[["ID", "Date", "Description", "Amount"]].copy().sort_values(
                by=["Date", "ID"], ascending=[False, False]
            )
            delete_df["Label"] = (
                delete_df["ID"].astype(str)
                + " | "
                + delete_df["Date"].dt.strftime("%Y-%m-%d")
                + " | "
                + delete_df["Description"]
                + " | "
                + delete_df["Amount"].map(lambda x: f"{x:,.2f}")
            )

            selected_label = st.selectbox("Delete Transaction", delete_df["Label"].tolist())

            if st.button("Delete Selected Transaction"):
                selected_id = int(selected_label.split(" | ")[0])
                delete_transaction(selected_id)
                st.success("Transaction deleted.")
                st.rerun()
        close_glass_card()

    with action_col3:
        open_glass_card("Export", "Download your books")
        if df.empty:
            st.info("No data to export.")
        else:
            full_csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Full CSV",
                data=full_csv,
                file_name="bookkeepai_all_transactions.csv",
                mime="text/csv"
            )
        close_glass_card()

    if df.empty:
        open_glass_card("Empty Dashboard", "Your books will appear once you add data")
        st.info("No transactions yet.")
        close_glass_card()
        return

    open_glass_card("Filters", "Refine your dashboard view")
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.strftime("%B")

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    f1, f2, f3 = st.columns(3)
    with f1:
        start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

    with f2:
        year_options = ["All"] + sorted(df["Year"].dropna().unique().tolist(), reverse=True)
        selected_year = st.selectbox("Year", year_options)

        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_options = ["All"] + [m for m in month_order if m in df["Month"].unique().tolist()]
        selected_month = st.selectbox("Month", month_options)

    with f3:
        type_options = sorted(df["Type"].dropna().unique().tolist())
        selected_types = st.multiselect("Type", type_options, default=type_options)

        category_options = sorted(df["Category"].dropna().unique().tolist())
        selected_categories = st.multiselect("Category", category_options, default=category_options)

    f4, f5 = st.columns(2)
    with f4:
        search_text = st.text_input("Search Description")

    with f5:
        amount_min = float(df["Amount"].min()) if not df.empty else 0.0
        amount_max = float(df["Amount"].max()) if not df.empty else 0.0
        selected_amount_range = st.slider(
            "Amount Range",
            min_value=float(amount_min),
            max_value=float(amount_max),
            value=(float(amount_min), float(amount_max))
        )
    close_glass_card()

    filtered = df.copy()
    filtered = filtered[
        (filtered["Date"].dt.date >= start_date) &
        (filtered["Date"].dt.date <= end_date)
    ]

    if selected_year != "All":
        filtered = filtered[filtered["Year"] == selected_year]

    if selected_month != "All":
        filtered = filtered[filtered["Month"] == selected_month]

    if selected_types:
        filtered = filtered[filtered["Type"].isin(selected_types)]

    if selected_categories:
        filtered = filtered[filtered["Category"].isin(selected_categories)]

    filtered = filtered[
        (filtered["Amount"] >= selected_amount_range[0]) &
        (filtered["Amount"] <= selected_amount_range[1])
    ]

    if search_text.strip():
        filtered = filtered[
            filtered["Description"].str.contains(search_text, case=False, na=False)
        ]

    if filtered.empty:
        open_glass_card("No Results", "Your current filters returned no matching transactions")
        st.warning("No transactions match your filters.")
        close_glass_card()
        return

    income = filtered[filtered["Category"] == "Income"]["Amount"].sum()
    business_expenses = filtered[
        (filtered["Type"] == "Business") &
        (filtered["Category"] != "Income")
    ]["Amount"].sum()
    personal_total = filtered[filtered["Type"] == "Personal"]["Amount"].sum()
    review_total = filtered[filtered["Type"] == "Review"]["Amount"].sum()
    net = income - business_expenses

    open_glass_card("Overview", "Filtered performance snapshot")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Income", f"{income:,.2f}")
    m2.metric("Business Expenses", f"{business_expenses:,.2f}")
    m3.metric("Net", f"{net:,.2f}")
    m4.metric("Personal", f"{personal_total:,.2f}")
    m5.metric("Review", f"{review_total:,.2f}")
    close_glass_card()

    personal_df = filtered[filtered["Type"] == "Personal"]
    business_df = filtered[filtered["Type"] == "Business"]
    utilities_df = filtered[filtered["Category"] == "Utilities"]

    g1, g2 = st.columns(2)
    with g1:
        open_glass_card("Personal Bar Graph")
        if not personal_df.empty:
            personal_chart = (
                personal_df.groupby("Description", as_index=False)["Amount"]
                .sum()
                .sort_values(by="Amount", ascending=False)
                .set_index("Description")
            )
            st.bar_chart(personal_chart, use_container_width=True)
        else:
            st.info("No personal entries for current filters.")
        close_glass_card()

    with g2:
        open_glass_card("Business Bar Graph")
        if not business_df.empty:
            business_chart = (
                business_df.groupby("Category", as_index=False)["Amount"]
                .sum()
                .sort_values(by="Amount", ascending=False)
                .set_index("Category")
            )
            st.bar_chart(business_chart, use_container_width=True)
        else:
            st.info("No business entries for current filters.")
        close_glass_card()

    g3, g4 = st.columns(2)
    with g3:
        open_glass_card("Utility Bar Graph")
        if not utilities_df.empty:
            utility_chart = (
                utilities_df.groupby("Description", as_index=False)["Amount"]
                .sum()
                .sort_values(by="Amount", ascending=False)
                .set_index("Description")
            )
            st.bar_chart(utility_chart, use_container_width=True)
        else:
            st.info("No utility entries for current filters.")
        close_glass_card()

    with g4:
        open_glass_card("Overall Bar Graph")
        overall_chart = (
            filtered.groupby("Category", as_index=False)["Amount"]
            .sum()
            .sort_values(by="Amount", ascending=False)
            .set_index("Category")
        )
        st.bar_chart(overall_chart, use_container_width=True)
        close_glass_card()

    open_glass_card("Ledger Views", "Browse the filtered transaction tables")
    display_cols = ["ID", "Description", "Amount", "Category", "Review Status", "Type", "Date"]

    table_tabs = st.tabs(["Transactions", "Business", "Personal", "Utilities", "Review"])

    with table_tabs[0]:
        st.dataframe(
            filtered[display_cols].sort_values(by=["Date", "ID"], ascending=[False, False]),
            use_container_width=True,
            hide_index=True,
            height=430
        )

    with table_tabs[1]:
        business_table = filtered[filtered["Type"] == "Business"][display_cols].sort_values(
            by=["Date", "ID"], ascending=[False, False]
        )
        st.dataframe(business_table, use_container_width=True, hide_index=True, height=430)

    with table_tabs[2]:
        personal_table = filtered[filtered["Type"] == "Personal"][display_cols].sort_values(
            by=["Date", "ID"], ascending=[False, False]
        )
        st.dataframe(personal_table, use_container_width=True, hide_index=True, height=430)

    with table_tabs[3]:
        utilities_table = filtered[filtered["Category"] == "Utilities"][display_cols].sort_values(
            by=["Date", "ID"], ascending=[False, False]
        )
        st.dataframe(utilities_table, use_container_width=True, hide_index=True, height=430)

    with table_tabs[4]:
        review_table = filtered[filtered["Type"] == "Review"][display_cols].sort_values(
            by=["Date", "ID"], ascending=[False, False]
        )
        st.dataframe(review_table, use_container_width=True, hide_index=True, height=430)

    filtered_csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Filtered CSV",
        data=filtered_csv,
        file_name="bookkeepai_filtered_transactions.csv",
        mime="text/csv"
    )
    close_glass_card()


if st.session_state.user is None:
    render_auth_page()
else:
    render_dashboard()
