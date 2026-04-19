import streamlit as st
import pandas as pd
from datetime import date
from database import (
    create_all_tables,
    create_project,
    get_user_projects,
    add_project_entry,
    get_project_entries,
    delete_project_entry,
    get_all_transactions,
    project_source_exists,
    save_known_entity,
    get_known_entities
)

st.set_page_config(page_title="Projects", layout="wide")
create_all_tables()

if "user" not in st.session_state:
    st.session_state.user = None

if "project_message" not in st.session_state:
    st.session_state.project_message = ""

if st.session_state.user is None:
    st.title("Projects")
    st.warning("Please log in first from the main BookkeepAI page.")
    st.stop()


def logout():
    st.session_state.user = None
    st.rerun()


def normalize_text(text):
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in str(text))
    return " ".join(cleaned.split())


def suggest_project_entry_details(description_text, notes_text, known_entities_df):
    description = str(description_text).strip()
    notes = str(notes_text).strip()
    combined = normalize_text(f"{description} {notes}")

    # 1. Known entity memory first
    if not known_entities_df.empty:
        for _, row in known_entities_df.iterrows():
            entity_name = normalize_text(row["Entity Name"])
            if entity_name and entity_name in combined:
                return (
                    row["Learned Category"],
                    row["Learned Entry Type"],
                    f"Matched known entity memory: {row['Entity Name']}",
                    row["Confidence"]
                )

    # 2. Accounting-aware logic
    if any(word in combined for word in ["resell", "resale", "ukay", "thrift", "inventory", "stock", "supplier"]):
        return "Inventory Purchase", "Business", "Contains resale or inventory language", "High"

    if any(phrase in combined for phrase in [
        "owner invested", "capital contribution", "added capital",
        "owner cash in", "business capital", "capital infusion"
    ]):
        return "Owner Capital", "Business", "Looks like owner money going into the business", "High"

    if any(phrase in combined for phrase in [
        "owner draw", "owner withdrew", "personal withdrawal",
        "money taken out", "cash taken by owner"
    ]):
        return "Owner Draw", "Personal", "Looks like money taken out by the owner", "High"

    if any(word in combined for word in ["equipment", "laptop", "computer", "printer", "machine", "asset"]):
        return "Asset Purchase", "Business", "Looks like a longer-term asset purchase", "Medium"

    if any(word in combined for word in ["sale", "revenue", "invoice", "income", "deposit", "client payment"]):
        return "Income", "Business", "Looks like incoming business money", "High"

    if any(word in combined for word in ["electric", "electricity", "water", "internet", "wifi", "phone", "power", "gas"]):
        return "Utilities", "Business", "Looks like a utility-related expense", "High"

    if "rent" in combined:
        return "Rent", "Business", "Looks like a rent-related expense", "High"

    if any(word in combined for word in ["loan", "mortgage", "credit", "interest"]):
        return "Loan", "Business", "Looks like a loan or financing-related expense", "High"

    if any(word in combined for word in ["netflix", "spotify", "chatgpt", "canva", "subscription"]):
        return "Subscription", "Business", "Looks like a recurring subscription-type expense", "Medium"

    if any(word in combined for word in ["family", "wife", "kids", "birthday", "personal", "dinner"]):
        return "Other", "Personal", "Looks more personal than business", "Medium"

    if any(word in combined for word in ["shop", "shopping", "grocery", "market"]):
        return "Shopping", "Review", "Looks like a shopping-type expense but may need review", "Low"

    return "Other", "Review", "No strong accounting signal found yet", "Low"


def build_cleanup_ai_table(project_entries_df):
    if project_entries_df.empty:
        return pd.DataFrame(columns=["Issue", "Entry ID", "Description", "Suggested Action"])

    results = []

    for _, row in project_entries_df.iterrows():
        description = str(row["Description"]).lower()
        category = str(row["Category"]).strip()

        if category == "" or category == "Other":
            results.append({
                "Issue": "Weak or missing category",
                "Entry ID": row["ID"],
                "Description": row["Description"],
                "Suggested Action": "Review and reclassify this entry"
            })

        if any(word in description for word in ["family", "wife", "kids", "birthday", "dinner"]):
            results.append({
                "Issue": "Possible personal expense",
                "Entry ID": row["ID"],
                "Description": row["Description"],
                "Suggested Action": "Confirm whether this is business or personal"
            })

        if str(row["Description"]).strip() == "":
            results.append({
                "Issue": "Missing description",
                "Entry ID": row["ID"],
                "Description": row["Description"],
                "Suggested Action": "Ask for better description"
            })

    return pd.DataFrame(results)


def build_reconciliation_ai_table(project_entries_df):
    if project_entries_df.empty:
        return pd.DataFrame(columns=["Issue", "Entry ID", "Description", "Suggested Action"])

    results = []
    temp = project_entries_df.copy()

    duplicate_groups = temp.groupby(["Entry Date", "Amount", "Description"]).size().reset_index(name="Count")
    duplicate_groups = duplicate_groups[duplicate_groups["Count"] > 1]

    for _, dup in duplicate_groups.iterrows():
        matching = temp[
            (temp["Entry Date"] == dup["Entry Date"]) &
            (temp["Amount"] == dup["Amount"]) &
            (temp["Description"] == dup["Description"])
        ]

        for _, row in matching.iterrows():
            results.append({
                "Issue": "Possible duplicate entry",
                "Entry ID": row["ID"],
                "Description": row["Description"],
                "Suggested Action": "Check whether this transaction was entered twice"
            })

    return pd.DataFrame(results)


def build_payables_ai_table(project_entries_df):
    if project_entries_df.empty:
        return pd.DataFrame(columns=["Rank", "Entry ID", "Description", "Category", "Amount", "Suggested Action"])

    temp = project_entries_df.copy()

    priority_map = {
        "Rent": 1,
        "Utilities": 2,
        "Loan": 3,
        "Inventory Purchase": 4,
        "Subscription": 5,
        "Asset Purchase": 6,
        "Owner Capital": 7,
        "Owner Draw": 8,
        "Other": 9
    }

    temp["Priority Rank"] = temp["Category"].map(priority_map).fillna(10)
    temp = temp.sort_values(by=["Priority Rank", "Amount"], ascending=[True, False]).copy()

    results = []
    for i, (_, row) in enumerate(temp.iterrows(), start=1):
        results.append({
            "Rank": i,
            "Entry ID": row["ID"],
            "Description": row["Description"],
            "Category": row["Category"],
            "Amount": row["Amount"],
            "Suggested Action": "Review this as a higher-priority item"
        })

    return pd.DataFrame(results)


def build_client_questions_ai_table(project_entries_df):
    if project_entries_df.empty:
        return pd.DataFrame(columns=["Question", "Entry ID", "Description", "Reason"])

    results = []

    for _, row in project_entries_df.iterrows():
        description = str(row["Description"]).lower()
        category = str(row["Category"]).strip()

        if category == "" or category == "Other":
            results.append({
                "Question": "Can you confirm the proper category for this transaction?",
                "Entry ID": row["ID"],
                "Description": row["Description"],
                "Reason": "Category is weak or unclear"
            })

        if any(word in description for word in ["sent", "transfer", "cash"]):
            results.append({
                "Question": "What was the purpose of this transfer or cash movement?",
                "Entry ID": row["ID"],
                "Description": row["Description"],
                "Reason": "Description may need clarification"
            })

        if str(row["Notes"]).strip() == "":
            results.append({
                "Question": "Do you have more details or supporting documents for this entry?",
                "Entry ID": row["ID"],
                "Description": row["Description"],
                "Reason": "No supporting note was provided"
            })

    return pd.DataFrame(results)


with st.sidebar:
    st.subheader("Account")
    st.write(f"**Name:** {st.session_state.user['full_name']}")
    st.write(f"**Email:** {st.session_state.user['email']}")

    if st.button("Logout", key="projects_logout"):
        logout()


st.title("Projects")
st.write("This page is the CPA work area. Project data stays separate from My Books.")

if st.session_state.project_message:
    st.success(st.session_state.project_message)
    st.session_state.project_message = ""

user_id = st.session_state.user["id"]
project_rows = get_user_projects(user_id)
known_entity_rows = get_known_entities()

if known_entity_rows:
    known_entities_df = pd.DataFrame(
        known_entity_rows,
        columns=["Entity Name", "Learned Category", "Learned Entry Type", "Learned Reason", "Confidence"]
    )
else:
    known_entities_df = pd.DataFrame(columns=[
        "Entity Name", "Learned Category", "Learned Entry Type", "Learned Reason", "Confidence"
    ])

st.markdown("## Create Project")

with st.form("create_project_form"):
    project_name = st.text_input("Project Name")
    client_name = st.text_input("Client Name")
    project_type = st.selectbox("Project Type", [
        "Monthly Bookkeeping",
        "Cleanup",
        "Reconciliation",
        "Tax Prep Support",
        "Review",
        "Other"
    ])
    project_status = st.selectbox("Status", ["Open", "In Progress", "In Review", "Completed"])
    project_notes = st.text_area("Project Notes")

    create_project_submitted = st.form_submit_button("Create Project")

    if create_project_submitted:
        if project_name.strip() == "":
            st.warning("Please enter a project name.")
        else:
            create_project(
                user_id=user_id,
                project_name=project_name.strip(),
                client_name=client_name.strip(),
                project_type=project_type,
                status=project_status,
                notes=project_notes.strip()
            )
            st.session_state.project_message = "Project created successfully."
            st.rerun()

project_rows = get_user_projects(user_id)

if not project_rows:
    st.info("No projects yet. Create your first project above.")
    st.stop()

project_df = pd.DataFrame(
    project_rows,
    columns=["ID", "Project Name", "Client Name", "Project Type", "Status", "Notes", "Created At"]
)

st.markdown("## Select Project")

project_options = project_df["Project Name"].tolist()
selected_project_name = st.selectbox("Choose a Project", project_options)

selected_project_row = project_df[project_df["Project Name"] == selected_project_name].iloc[0]
selected_project_id = int(selected_project_row["ID"])

st.markdown("### Project Summary")
summary_col1, summary_col2, summary_col3 = st.columns(3)
summary_col1.metric("Project ID", str(selected_project_id))
summary_col2.metric("Project Type", selected_project_row["Project Type"])
summary_col3.metric("Status", selected_project_row["Status"])

st.write(f"**Client:** {selected_project_row['Client Name']}")
st.write(f"**Notes:** {selected_project_row['Notes']}")

project_entry_rows = get_project_entries(selected_project_id)

if project_entry_rows:
    project_entries_df = pd.DataFrame(
        project_entry_rows,
        columns=["ID", "Entry Date", "Description", "Amount", "Category", "Entry Type", "Notes", "Source Type", "Source Transaction ID"]
    )
    project_entries_df["Entry Date"] = pd.to_datetime(project_entries_df["Entry Date"], errors="coerce")
else:
    project_entries_df = pd.DataFrame(columns=[
        "ID", "Entry Date", "Description", "Amount", "Category", "Entry Type", "Notes", "Source Type", "Source Transaction ID"
    ])

tab1, tab2, tab3, tab4 = st.tabs([
    "Project Sheet",
    "Import Into Project",
    "Pull From My Books",
    "AI Tables"
])

# =========================
# TAB 1 - PROJECT SHEET
# =========================
with tab1:
    st.subheader("Project Sheet")
    st.write("This is the project bookkeeping workspace. For the demo, both entry styles are available.")

    mode_tab1, mode_tab2 = st.tabs(["Quick Grid Entry", "AI Rapid Entry"])

    # -------------------------
    # QUICK GRID ENTRY
    # -------------------------
    with mode_tab1:
        st.markdown("### Quick Grid Entry")
        st.caption("Spreadsheet-style entry with more manual control.")

        blank_rows = pd.DataFrame({
            "Entry Date": [date.today() for _ in range(10)],
            "Description": ["" for _ in range(10)],
            "Amount": [0.0 for _ in range(10)],
            "Category": ["Other" for _ in range(10)],
            "Entry Type": ["Review" for _ in range(10)],
            "Notes": ["" for _ in range(10)]
        })

        quick_entry_df = st.data_editor(
            blank_rows,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=f"quick_entry_grid_{selected_project_id}",
            column_config={
                "Entry Date": st.column_config.DateColumn("Entry Date"),
                "Description": st.column_config.TextColumn("Description"),
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=[
                        "Income", "Utilities", "Rent", "Loan", "Subscription",
                        "Inventory Purchase", "Asset Purchase",
                        "Owner Capital", "Owner Draw",
                        "Shopping", "Other"
                    ]
                ),
                "Entry Type": st.column_config.SelectboxColumn(
                    "Entry Type",
                    options=["Business", "Personal", "Review"]
                ),
                "Notes": st.column_config.TextColumn("Notes")
            }
        )

        if st.button("Save Quick Grid Rows To Project"):
            added_count = 0

            for _, row in quick_entry_df.iterrows():
                description = str(row["Description"]).strip()
                amount = row["Amount"]

                if description == "":
                    continue

                try:
                    amount_value = float(amount)
                except Exception:
                    amount_value = 0.0

                add_project_entry(
                    project_id=selected_project_id,
                    entry_date=str(row["Entry Date"]),
                    description=description,
                    amount=amount_value,
                    category=str(row["Category"]),
                    entry_type=str(row["Entry Type"]),
                    notes=str(row["Notes"]).strip(),
                    source_type="manual",
                    source_transaction_id=None
                )
                added_count += 1

            if added_count == 0:
                st.warning("No valid rows were found. Please type at least one description.")
            else:
                st.session_state.project_message = f"{added_count} quick-grid row(s) added to the project."
                st.rerun()

    # -------------------------
    # AI RAPID ENTRY
    # -------------------------
    with mode_tab2:
        st.markdown("### AI Rapid Entry")
        st.caption("Type only the expense, amount, date, and notes. AI fills the category and entry type for you.")

        ai_blank_rows = pd.DataFrame({
            "Entry Date": [date.today() for _ in range(10)],
            "Description": ["" for _ in range(10)],
            "Amount": [0.0 for _ in range(10)],
            "Notes": ["" for _ in range(10)]
        })

        ai_entry_df = st.data_editor(
            ai_blank_rows,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=f"ai_rapid_grid_{selected_project_id}",
            column_config={
                "Entry Date": st.column_config.DateColumn("Entry Date"),
                "Description": st.column_config.TextColumn("Description"),
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                "Notes": st.column_config.TextColumn("Notes")
            }
        )

        preview_rows = []
        for _, row in ai_entry_df.iterrows():
            description = str(row["Description"]).strip()
            notes = str(row["Notes"]).strip()

            if description == "":
                continue

            auto_category, auto_entry_type, auto_reason, auto_confidence = suggest_project_entry_details(
                description,
                notes,
                known_entities_df
            )

            preview_rows.append({
                "Entry Date": row["Entry Date"],
                "Description": description,
                "Amount": row["Amount"],
                "Notes": notes,
                "AI Category": auto_category,
                "AI Entry Type": auto_entry_type,
                "AI Reason": auto_reason,
                "AI Confidence": auto_confidence
            })

        st.markdown("#### AI Preview")
        if preview_rows:
            preview_df = pd.DataFrame(preview_rows)
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
        else:
            st.info("Type at least one row above to preview how the AI will classify it.")

        if st.button("Save AI Rapid Rows To Project"):
            added_count = 0

            for _, row in ai_entry_df.iterrows():
                description = str(row["Description"]).strip()
                notes = str(row["Notes"]).strip()
                amount = row["Amount"]

                if description == "":
                    continue

                try:
                    amount_value = float(amount)
                except Exception:
                    amount_value = 0.0

                auto_category, auto_entry_type, auto_reason, auto_confidence = suggest_project_entry_details(
                    description,
                    notes,
                    known_entities_df
                )

                add_project_entry(
                    project_id=selected_project_id,
                    entry_date=str(row["Entry Date"]),
                    description=description,
                    amount=amount_value,
                    category=auto_category,
                    entry_type=auto_entry_type,
                    notes=f"{notes} | AI Reason: {auto_reason} | AI Confidence: {auto_confidence}".strip(" |"),
                    source_type="manual",
                    source_transaction_id=None
                )
                added_count += 1

            if added_count == 0:
                st.warning("No valid rows were found. Please type at least one description.")
            else:
                st.session_state.project_message = f"{added_count} AI rapid-entry row(s) added to the project."
                st.rerun()

        st.markdown("#### Teach AI Memory")
        st.caption("Use this when the AI should permanently remember a company or vendor.")

        with st.form("teach_ai_memory_form"):
            entity_name = st.text_input("Company / Vendor Name")
            learned_category = st.selectbox(
                "Learned Category",
                [
                    "Income", "Utilities", "Rent", "Loan", "Subscription",
                    "Inventory Purchase", "Asset Purchase",
                    "Owner Capital", "Owner Draw",
                    "Shopping", "Other"
                ]
            )
            learned_entry_type = st.selectbox("Learned Entry Type", ["Business", "Personal", "Review"])
            learned_reason = st.text_input("Why does it belong there?")
            confidence = st.selectbox("Confidence", ["High", "Medium", "Low"])

            save_memory = st.form_submit_button("Save To AI Memory")

            if save_memory:
                if entity_name.strip() == "":
                    st.warning("Please enter a company or vendor name.")
                else:
                    save_known_entity(
                        entity_name=entity_name.strip(),
                        learned_category=learned_category,
                        learned_entry_type=learned_entry_type,
                        learned_reason=learned_reason.strip() if learned_reason.strip() else "Manually taught by user",
                        confidence=confidence
                    )
                    st.session_state.project_message = f"{entity_name.strip()} saved into AI memory."
                    st.rerun()

        st.markdown("#### Known Companies / Vendors")
        if not known_entities_df.empty:
            st.dataframe(known_entities_df, use_container_width=True, hide_index=True)
        else:
            st.info("No known entities saved yet.")

    st.markdown("### Current Project Table")

    if not project_entries_df.empty:
        display_df = project_entries_df.copy()
        display_df["Entry Date"] = project_entries_df["Entry Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        export_csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Project CSV",
            data=export_csv,
            file_name=f"project_{selected_project_id}_entries.csv",
            mime="text/csv"
        )

        delete_labels_df = project_entries_df.copy()
        delete_labels_df["Entry Date Label"] = delete_labels_df["Entry Date"].dt.strftime("%Y-%m-%d")
        delete_labels_df["Delete Label"] = (
            delete_labels_df["ID"].astype(str)
            + " | "
            + delete_labels_df["Entry Date Label"]
            + " | "
            + delete_labels_df["Description"].astype(str)
            + " | "
            + delete_labels_df["Amount"].astype(str)
        )

        selected_delete_label = st.selectbox(
            "Select a project row to delete",
            delete_labels_df["Delete Label"].tolist()
        )

        if st.button("Delete Selected Project Row"):
            selected_delete_id = int(selected_delete_label.split(" | ")[0])
            delete_project_entry(selected_delete_id, selected_project_id)
            st.session_state.project_message = "Project row deleted successfully."
            st.rerun()
    else:
        blank_display_df = pd.DataFrame(columns=[
            "Entry Date", "Description", "Amount", "Category", "Entry Type", "Notes", "Source Type"
        ])
        st.dataframe(blank_display_df, use_container_width=True, hide_index=True)
        st.info("This project is still blank. Use Quick Grid Entry, AI Rapid Entry, import, or pull from My Books.")

# =========================
# TAB 2 - IMPORT INTO PROJECT
# =========================
with tab2:
    st.subheader("Import Into Project")
    st.write("Import rows into this project only. They will not mix into My Books.")

    uploaded_file = st.file_uploader("Upload CSV for this project", type=["csv"], key="project_import_csv")

    if uploaded_file is not None:
        df_upload = pd.read_csv(uploaded_file)
        st.dataframe(df_upload, use_container_width=True, hide_index=True)

        if st.button("Import CSV Into Project"):
            required_columns = ["Description", "Amount"]

            if all(col in df_upload.columns for col in required_columns):
                if "Date" not in df_upload.columns:
                    df_upload["Date"] = str(date.today())

                if "Category" not in df_upload.columns:
                    df_upload["Category"] = "Other"

                if "Type" not in df_upload.columns:
                    df_upload["Type"] = "Review"

                if "Notes" not in df_upload.columns:
                    df_upload["Notes"] = ""

                for _, row in df_upload.iterrows():
                    add_project_entry(
                        project_id=selected_project_id,
                        entry_date=str(row["Date"]),
                        description=str(row["Description"]),
                        amount=float(row["Amount"]),
                        category=str(row["Category"]),
                        entry_type=str(row["Type"]),
                        notes=str(row["Notes"]),
                        source_type="import",
                        source_transaction_id=None
                    )

                st.session_state.project_message = "CSV imported into project successfully."
                st.rerun()
            else:
                st.error("CSV must contain at least: Description, Amount")

# =========================
# TAB 3 - PULL FROM MY BOOKS
# =========================
with tab3:
    st.subheader("Pull From My Books")
    st.write("Select transactions from My Books and copy them into this project workspace.")

    main_rows = get_all_transactions()

    if not main_rows:
        st.info("No transactions found in My Books.")
    else:
        main_df = pd.DataFrame(
            main_rows,
            columns=["ID", "Description", "Amount", "Category", "Review Status", "Type", "Date"]
        )
        main_df["Date"] = pd.to_datetime(main_df["Date"], errors="coerce")
        main_df = main_df.dropna(subset=["Date"]).copy()
        main_df["Select"] = False

        editable_df = main_df[["Select", "ID", "Date", "Description", "Amount", "Category", "Type"]].copy()
        editable_df["Date"] = editable_df["Date"].dt.strftime("%Y-%m-%d")

        edited_df = st.data_editor(
            editable_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        if st.button("Add Selected Transactions To Project"):
            selected_rows = edited_df[edited_df["Select"] == True]

            if selected_rows.empty:
                st.warning("Please select at least one transaction.")
            else:
                added_count = 0

                for _, row in selected_rows.iterrows():
                    transaction_id = int(row["ID"])

                    if not project_source_exists(selected_project_id, "main_record", transaction_id):
                        add_project_entry(
                            project_id=selected_project_id,
                            entry_date=str(row["Date"]),
                            description=str(row["Description"]),
                            amount=float(row["Amount"]),
                            category=str(row["Category"]),
                            entry_type=str(row["Type"]),
                            notes="Copied from My Books",
                            source_type="main_record",
                            source_transaction_id=transaction_id
                        )
                        added_count += 1

                st.session_state.project_message = f"{added_count} transaction(s) copied into the project."
                st.rerun()

# =========================
# TAB 4 - AI TABLES
# =========================
with tab4:
    st.subheader("AI Tables")
    st.write("Choose one CPA problem table to analyze the current project sheet.")

    ai_table_choice = st.selectbox(
        "Choose AI Table",
        [
            "Cleanup AI",
            "Reconciliation AI",
            "Payables Priority AI",
            "Client Questions AI"
        ]
    )

    if project_entries_df.empty:
        st.info("No project data yet. Add rows first so the AI tables have something to analyze.")
    else:
        if ai_table_choice == "Cleanup AI":
            st.markdown("### Cleanup AI Table")
            cleanup_df = build_cleanup_ai_table(project_entries_df)
            if cleanup_df.empty:
                st.success("No cleanup issues found in the current project data.")
            else:
                st.dataframe(cleanup_df, use_container_width=True, hide_index=True)

        elif ai_table_choice == "Reconciliation AI":
            st.markdown("### Reconciliation AI Table")
            recon_df = build_reconciliation_ai_table(project_entries_df)
            if recon_df.empty:
                st.success("No duplicate-style reconciliation issues found.")
            else:
                st.dataframe(recon_df, use_container_width=True, hide_index=True)

        elif ai_table_choice == "Payables Priority AI":
            st.markdown("### Payables Priority AI Table")
            payables_df = build_payables_ai_table(project_entries_df)
            if payables_df.empty:
                st.success("No payable ranking data found.")
            else:
                st.dataframe(payables_df, use_container_width=True, hide_index=True)

        elif ai_table_choice == "Client Questions AI":
            st.markdown("### Client Questions AI Table")
            questions_df = build_client_questions_ai_table(project_entries_df)
            if questions_df.empty:
                st.success("No client clarification questions generated.")
            else:
                st.dataframe(questions_df, use_container_width=True, hide_index=True)