import sqlite3


def initialize_database():
    # Connect to SQLite database
    # The database file will be 'resident_data.db'
    conn = sqlite3.connect('resident_data.db')
    c = conn.cursor()

    # Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        initials TEXT,
        is_temp_password BOOLEAN DEFAULT 1)''')

    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        description TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # Create table for user settings
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_name TEXT UNIQUE,
        setting_value TEXT)''')

    # Create Resident table
    c.execute('''CREATE TABLE IF NOT EXISTS residents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date_of_birth TEXT,
        level_of_care TEXT)''')

    # Create Time Slots table
    c.execute('''CREATE TABLE IF NOT EXISTS time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_name TEXT UNIQUE)''')

    # Populate Time Slots table with standard slots
    time_slots = ['Morning', 'Noon', 'Evening', 'Night']
    for slot in time_slots:
        c.execute('INSERT INTO time_slots (slot_name) VALUES (?) ON CONFLICT(slot_name) DO NOTHING', (slot,))

    # Create medications table
    c.execute('''CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resident_id INTEGER,
        medication_name TEXT,
        dosage TEXT,
        instructions TEXT,
        medication_type TEXT DEFAULT 'Scheduled',
        medication_form TEXT DEFAULT 'Pill',
        count INTEGER DEFAULT NULL,
        discontinued_date DATE DEFAULT NULL,
        FOREIGN KEY(resident_id) REFERENCES residents(id))''')

    # Create medication_time_slots
    c.execute('''CREATE TABLE IF NOT EXISTS medication_time_slots (
        medication_id INTEGER,
        time_slot_id INTEGER,
        FOREIGN KEY(medication_id) REFERENCES medications(id),
        FOREIGN KEY(time_slot_id) REFERENCES time_slots(id),
        PRIMARY KEY (medication_id, time_slot_id))''')

    # Create table for eMARS charts
    c.execute('''CREATE TABLE IF NOT EXISTS emar_chart (
        chart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        resident_id INTEGER,
        medication_id INTEGER,
        date TEXT,
        time_slot TEXT,
        administered TEXT,
        current_count INTEGER DEFAULT NULL,
        notes TEXT DEFAULT '',
        FOREIGN KEY(resident_id) REFERENCES residents(id),
        FOREIGN KEY(medication_id) REFERENCES medications(id),
        UNIQUE(resident_id, medication_id, date, time_slot))''')

    # Create table for ADL charts
    c.execute('''CREATE TABLE IF NOT EXISTS adl_chart (
                chart_id INTEGER PRIMARY KEY,
                resident_name TEXT,
                date TEXT,
                first_shift_sp TEXT,
                second_shift_sp TEXT,
                first_shift_activity1 TEXT,
                first_shift_activity2 TEXT,
                first_shift_activity3 TEXT,
                second_shift_activity4 TEXT,
                first_shift_bm TEXT,
                second_shift_bm TEXT,
                shower TEXT,
                shampoo TEXT,
                sponge_bath TEXT,
                peri_care_am TEXT,
                peri_care_pm TEXT,
                oral_care_am TEXT,
                oral_care_pm TEXT,
                nail_care TEXT,
                skin_care TEXT,
                shave TEXT,
                breakfast TEXT,
                lunch TEXT,
                dinner TEXT,
                snack_am TEXT,
                snack_pm TEXT,
                water_intake TEXT,
                FOREIGN KEY(resident_name) REFERENCES residents(name),
                UNIQUE(resident_name, date))''')
        
    conn.commit()
    conn.close()