import sqlite3
from pathlib import Path

DB_PATH = Path("data/bookkeeping.db")


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


# =========================
# TRANSACTIONS TABLE
# =========================
def create_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            amount REAL,
            category TEXT,
            review_status TEXT,
            transaction_type TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()


# =========================
# USERS TABLE
# =========================
def create_users_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# =========================
# BILLS TABLE
# =========================
def create_bills_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bill_name TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            frequency TEXT,
            category TEXT,
            priority TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# =========================
# AI PROFILES TABLE
# =========================
def create_ai_profiles_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            user_type TEXT,
            currency TEXT,
            response_style TEXT,
            pay_frequency TEXT,
            main_income REAL,
            next_pay_date TEXT,
            other_income_notes TEXT,
            minimum_safe_balance REAL,
            emergency_reserve_target REAL,
            never_touch_amount REAL,
            must_pay_categories TEXT,
            can_delay_categories TEXT,
            priority_style TEXT,
            financial_goals TEXT,
            support_mode TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# =========================
# PROJECTS TABLE
# =========================
def create_projects_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            client_name TEXT,
            project_type TEXT,
            status TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# =========================
# PROJECT ENTRIES TABLE
# =========================
def create_project_entries_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            entry_date TEXT,
            description TEXT,
            amount REAL,
            category TEXT,
            entry_type TEXT,
            notes TEXT,
            source_type TEXT,
            source_transaction_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def create_all_tables():
    create_table()
    create_users_table()
    create_bills_table()
    create_ai_profiles_table()
    create_projects_table()
    create_project_entries_table()
    create_known_entities_table()


# =========================
# TRANSACTION FUNCTIONS
# =========================
def add_transaction(description, amount, category, review_status, transaction_type, date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (description, amount, category, review_status, transaction_type, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (description, amount, category, review_status, transaction_type, date))
    conn.commit()
    conn.close()


def get_all_transactions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, description, amount, category, review_status, transaction_type, date
        FROM transactions
        ORDER BY date DESC, id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_transaction(transaction_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()


# =========================
# BILL FUNCTIONS
# =========================
def add_bill(user_id, bill_name, amount, due_date, frequency, category, priority, notes, status="Active"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bills (user_id, bill_name, amount, due_date, frequency, category, priority, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, bill_name, amount, due_date, frequency, category, priority, notes, status))
    conn.commit()
    conn.close()


def get_user_bills(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, bill_name, amount, due_date, frequency, category, priority, notes, status
        FROM bills
        WHERE user_id = ?
        ORDER BY due_date ASC, id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# =========================
# AI PROFILE FUNCTIONS
# =========================
def save_ai_profile(
    user_id,
    user_type,
    currency,
    response_style,
    pay_frequency,
    main_income,
    next_pay_date,
    other_income_notes,
    minimum_safe_balance,
    emergency_reserve_target,
    never_touch_amount,
    must_pay_categories,
    can_delay_categories,
    priority_style,
    financial_goals,
    support_mode
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ai_profiles (
            user_id,
            user_type,
            currency,
            response_style,
            pay_frequency,
            main_income,
            next_pay_date,
            other_income_notes,
            minimum_safe_balance,
            emergency_reserve_target,
            never_touch_amount,
            must_pay_categories,
            can_delay_categories,
            priority_style,
            financial_goals,
            support_mode,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            user_type = excluded.user_type,
            currency = excluded.currency,
            response_style = excluded.response_style,
            pay_frequency = excluded.pay_frequency,
            main_income = excluded.main_income,
            next_pay_date = excluded.next_pay_date,
            other_income_notes = excluded.other_income_notes,
            minimum_safe_balance = excluded.minimum_safe_balance,
            emergency_reserve_target = excluded.emergency_reserve_target,
            never_touch_amount = excluded.never_touch_amount,
            must_pay_categories = excluded.must_pay_categories,
            can_delay_categories = excluded.can_delay_categories,
            priority_style = excluded.priority_style,
            financial_goals = excluded.financial_goals,
            support_mode = excluded.support_mode,
            updated_at = CURRENT_TIMESTAMP
    """, (
        user_id,
        user_type,
        currency,
        response_style,
        pay_frequency,
        main_income,
        next_pay_date,
        other_income_notes,
        minimum_safe_balance,
        emergency_reserve_target,
        never_touch_amount,
        must_pay_categories,
        can_delay_categories,
        priority_style,
        financial_goals,
        support_mode
    ))

    conn.commit()
    conn.close()


def get_ai_profile(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            user_type,
            currency,
            response_style,
            pay_frequency,
            main_income,
            next_pay_date,
            other_income_notes,
            minimum_safe_balance,
            emergency_reserve_target,
            never_touch_amount,
            must_pay_categories,
            can_delay_categories,
            priority_style,
            financial_goals,
            support_mode
        FROM ai_profiles
        WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# =========================
# KNOWN ENTITIES TABLE
# =========================
def create_known_entities_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS known_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_name TEXT NOT NULL UNIQUE,
            learned_category TEXT,
            learned_entry_type TEXT,
            learned_reason TEXT,
            confidence TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_known_entity(entity_name, learned_category, learned_entry_type, learned_reason, confidence):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO known_entities (
            entity_name,
            learned_category,
            learned_entry_type,
            learned_reason,
            confidence
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(entity_name) DO UPDATE SET
            learned_category = excluded.learned_category,
            learned_entry_type = excluded.learned_entry_type,
            learned_reason = excluded.learned_reason,
            confidence = excluded.confidence
    """, (
        entity_name,
        learned_category,
        learned_entry_type,
        learned_reason,
        confidence
    ))
    conn.commit()
    conn.close()


def get_known_entities():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT entity_name, learned_category, learned_entry_type, learned_reason, confidence
        FROM known_entities
        ORDER BY entity_name ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

# =========================
# PROJECT FUNCTIONS
# =========================
def create_project(user_id, project_name, client_name, project_type, status, notes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects (user_id, project_name, client_name, project_type, status, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, project_name, client_name, project_type, status, notes))
    conn.commit()
    conn.close()


def get_user_projects(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, project_name, client_name, project_type, status, notes, created_at
        FROM projects
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_project_entry(
    project_id,
    entry_date,
    description,
    amount,
    category,
    entry_type,
    notes,
    source_type="manual",
    source_transaction_id=None
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_entries (
            project_id,
            entry_date,
            description,
            amount,
            category,
            entry_type,
            notes,
            source_type,
            source_transaction_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id,
        entry_date,
        description,
        amount,
        category,
        entry_type,
        notes,
        source_type,
        source_transaction_id
    ))
    conn.commit()
    conn.close()


def get_project_entries(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, entry_date, description, amount, category, entry_type, notes, source_type, source_transaction_id
        FROM project_entries
        WHERE project_id = ?
        ORDER BY entry_date DESC, id DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_project_entry(entry_id, project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM project_entries
        WHERE id = ? AND project_id = ?
    """, (entry_id, project_id))
    conn.commit()
    conn.close()


def project_source_exists(project_id, source_type, source_transaction_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id
        FROM project_entries
        WHERE project_id = ? AND source_type = ? AND source_transaction_id = ?
    """, (project_id, source_type, source_transaction_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None