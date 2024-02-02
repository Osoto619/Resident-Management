import sqlite3
from datetime import datetime
import calendar
import bcrypt


def log_action(username, action, description):
    # Get current time in local timezone
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (username, action, description, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (username, action, description, current_time))
        conn.commit()


def validate_login(username, password):
    """
    Validate user login credentials using bcrypt for password hashing.

    Args:
    username (str): The username of the user.
    password (str): The password of the user.

    Returns:
    bool: True if credentials are valid, otherwise False.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user is None:
            return False

        # No need to encode the hashed password as it's already a byte string
        hashed_password = user[0]
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def needs_password_reset(username):
    """
    Check if the user's current password is a temporary one.

    Args:
    username (str): The username of the user.

    Returns:
    bool: True if the user's password is temporary, otherwise False.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_temp_password FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()

        if result is None:
            return False  # User not found

        return bool(result[0])  # Convert to Boolean: 1 (True) if temp, 0 (False) otherwise


def update_user_password(username, new_password):
    """
    Update the user's password in the database.

    Args:
    username (str): The username of the user.
    new_password (str): The new password to be set for the user.
    """
    # Hash the new password
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    # Connect to the SQLite database
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Update the user's password and reset the is_temp_password flag
        cursor.execute('''
            UPDATE users
            SET password_hash = ?, is_temp_password = 0
            WHERE username = ?
        ''', (hashed_password, username))

        conn.commit()


def update_user_password_and_initials(username, new_password, initials):
    """
    Update the password and initials for a user, and set the is_temp_password flag to False.

    Args:
    username (str): The username of the user.
    new_password (str): The new password for the user.
    initials (str): The initials of the user.
    """
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET password_hash = ?, initials = ?, is_temp_password = 0
            WHERE username = ?
        ''', (hashed_password, initials, username))
        conn.commit()


def is_first_time_setup():
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM users")
        user_count = cursor.fetchone()[0]
        return user_count == 0


# Function used for initial admin setup
def create_admin_account(username, password, initials):
    # Hash the password for secure storage
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Connect to the SQLite database
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Insert the new admin account into the users table with is_temp_password set to False
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, initials, is_temp_password)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hashed_password, 'admin', initials, False))

        conn.commit()


def is_username_exists(username):
    """
    Check if a given username already exists in the database.

    Args:
    username (str): The username to check.

    Returns:
    bool: True if the username exists, False otherwise.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
        count = cursor.fetchone()[0]
        return count > 0


def create_user(username, password, role='User', is_temp_password=True, initials=''):
    """
    Create a new user with a hashed password using bcrypt.

    Args:
    username (str): The username of the user.
    password (str): The plain password of the user.
    role (str): The role of the user ('Admin' or 'User').
    is_temp_password (bool): Flag indicating if the password is temporary.
    initials (str): The initials of the user.
    """
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password_hash, role, is_temp_password, initials) VALUES (?, ?, ?, ?, ?)',
                       (username, hashed_password, role, is_temp_password, initials))
        conn.commit()


def is_admin(username):
    """
    Check if the given user is an admin.

    Args:
    username (str): The username of the user.

    Returns:
    bool: True if the user is an admin, False otherwise.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Fetch the role of the user
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()

        if result is None:
            return False  # User not found
        else:
            return result[0].lower() == 'admin'  # Check if the role is 'admin'


def get_user_initials(username):
    """
    Fetches the initials for a given username from the users table.

    Args:
    username (str): The username of the user.

    Returns:
    str: The initials of the user or None if not found.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT initials FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return None


def get_user_theme():
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM user_settings WHERE setting_name = 'theme'")
        result = cursor.fetchone()
        return result[0] if result else 'Reddit'  # Replace 'DarkBlue' with your default theme


# Function to save theme choice
def save_user_theme_choice(theme):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Check if the theme setting already exists
        cursor.execute('SELECT COUNT(*) FROM user_settings WHERE setting_name = "theme"')
        exists = cursor.fetchone()[0] > 0

        if exists:
            # Update the existing theme setting
            cursor.execute('UPDATE user_settings SET setting_value = ? WHERE setting_name = "theme"', (theme,))
        else:
            # Insert a new theme setting
            cursor.execute('INSERT INTO user_settings (setting_name, setting_value) VALUES ("theme", ?)', (theme,))

        conn.commit()


def get_user_font():
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Query to select the font setting from the database
        cursor.execute("SELECT setting_value FROM user_settings WHERE setting_name = 'font'")
        result = cursor.fetchone()
        # Return the result if found, otherwise return 'Helvetica' as the default font
        return result[0] if result else 'Helvetica'


def save_user_font_choice(font):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Check if the font setting already exists
        cursor.execute('SELECT COUNT(*) FROM user_settings WHERE setting_name = "font"')
        exists = cursor.fetchone()[0] > 0

        if exists:
            # Update the existing font setting
            cursor.execute('UPDATE user_settings SET setting_value = ? WHERE setting_name = "font"', (font,))
        else:
            # Insert a new font setting
            cursor.execute('INSERT INTO user_settings (setting_name, setting_value) VALUES ("font", ?)', (font,))

        conn.commit()


def get_resident_count():
    """ Return the number of residents in the database. """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM residents')
        return cursor.fetchone()[0]


def get_resident_names():
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM residents')
        residents = cursor.fetchall()
        # Fetchall returns a list of tuples, so we'll use a list comprehension
        # to extract the names and return them as a list of strings.
        return [name[0] for name in residents]


def insert_resident(name, date_of_birth, level_of_care):
    """ Insert a new resident into the database. """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Adjusted SQL query to match the new table structure
        cursor.execute('INSERT INTO residents (name, date_of_birth, level_of_care) VALUES (?, ?, ?)', 
                       (name, date_of_birth, level_of_care))
        conn.commit()


def fetch_resident_information(resident_name):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, date_of_birth FROM residents WHERE name = ?", (resident_name,))
        result = cursor.fetchone()
        if result:
            return {'name': result[0], 'date_of_birth': result[1]}
        else:
            return None


def update_resident_info(old_name, new_name, new_dob):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE residents SET name = ?, date_of_birth = ? WHERE name = ?", (new_name, new_dob, old_name))
        conn.commit()


def remove_resident(resident_name):
    """ Removes a resident from the database. """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM residents WHERE name = ?', (resident_name,))
        conn.commit()


def get_resident_id(resident_name):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM residents WHERE name = ?', (resident_name,))
        result = cursor.fetchone()
        return result[0] if result else None


def fetch_medications_for_resident(resident_name):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Get the resident ID
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_id_result = cursor.fetchone()
        if not resident_id_result:
            return {}  # No such resident found
        resident_id = resident_id_result[0]

        # Fetch Scheduled Medications
        cursor.execute("""
            SELECT m.medication_name, m.dosage, m.instructions, ts.slot_name
            FROM medications m
            JOIN medication_time_slots mts ON m.id = mts.medication_id
            JOIN time_slots ts ON mts.time_slot_id = ts.id
            WHERE m.resident_id = ? AND m.medication_type = 'Scheduled'
        """, (resident_id,))
        scheduled_results = cursor.fetchall()

        scheduled_medications = {}
        for med_name, dosage, instructions, time_slot in scheduled_results:
            if time_slot not in scheduled_medications:
                scheduled_medications[time_slot] = {}
            scheduled_medications[time_slot][med_name] = {'dosage': dosage, 'instructions': instructions}

        # Fetch PRN Medications
        cursor.execute("""
            SELECT medication_name, dosage, instructions
            FROM medications 
            WHERE resident_id = ? AND medication_type = 'As Needed (PRN)'
        """, (resident_id,))
        prn_results = cursor.fetchall()

        prn_medications = {med_name: {'dosage': dosage, 'instructions': instructions} for med_name, dosage, instructions in prn_results}

     # Fetch Controlled Medications
        cursor.execute("""
            SELECT medication_name, dosage, instructions, count, medication_form
            FROM medications 
            WHERE resident_id = ? AND medication_type = 'Controlled'
        """, (resident_id,))
        controlled_results = cursor.fetchall()

        controlled_medications = {med_name: {'dosage': dosage, 'instructions': instructions, 'count': count, 'form': form} 
                                  for med_name, dosage, instructions, count, form in controlled_results}

    # Combine the data into a single structure
    medications_data = {'Scheduled': scheduled_medications, 'PRN': prn_medications, 'Controlled': controlled_medications}
    return medications_data


def insert_medication(resident_name, medication_name, dosage, instructions, medication_type, selected_time_slots, medication_form=None, count=None):
    resident_id = get_resident_id(resident_name)
    if resident_id is not None:
        with sqlite3.connect('resident_data.db') as conn:
            cursor = conn.cursor()

            # Prepare values for insertion
            values_to_insert = (resident_id, medication_name, dosage, instructions, medication_type)

            # Prepare the SQL query based on medication type
            if medication_type == 'Controlled':
                # For controlled medications, include medication form and count
                sql_query = 'INSERT INTO medications (resident_id, medication_name, dosage, instructions, medication_type, medication_form, count) VALUES (?, ?, ?, ?, ?, ?, ?)'
                values_to_insert += (medication_form, count)
            else:
                # For other medication types, use the default query
                sql_query = 'INSERT INTO medications (resident_id, medication_name, dosage, instructions, medication_type) VALUES (?, ?, ?, ?, ?)'

            # Insert medication details
            cursor.execute(sql_query, values_to_insert)
            medication_id = cursor.lastrowid

            # Handle time slot relations for scheduled medications
            if medication_type == 'Scheduled':
                for slot in selected_time_slots:
                    cursor.execute('SELECT id FROM time_slots WHERE slot_name = ?', (slot,))
                    slot_id = cursor.fetchone()[0]
                    cursor.execute('INSERT INTO medication_time_slots (medication_id, time_slot_id) VALUES (?, ?)', (medication_id, slot_id))
            
            conn.commit()


def fetch_medication_details(medication_name, resident_id):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT medication_name, dosage, instructions FROM medications WHERE medication_name = ? AND resident_id = ?", (medication_name, resident_id))
        result = cursor.fetchone()
        if result:
            return {'medication_name': result[0], 'dosage': result[1], 'instructions': result[2]}
        else:
            return None


def update_medication_details(old_name, resident_id, new_name, new_dosage, new_instructions):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE medications SET medication_name = ?, dosage = ?, instructions = ? WHERE medication_name = ? AND resident_id = ?", (new_name, new_dosage, new_instructions, old_name, resident_id))
        conn.commit()


def get_controlled_medication_count_and_form(resident_name, medication_name):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Fetch the resident ID based on the resident's name
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_id_result = cursor.fetchone()
        if resident_id_result is None:
            return None, None  # Resident not found
        resident_id = resident_id_result[0]

        # Fetch the count and form for the specified controlled medication
        cursor.execute('''
            SELECT count, medication_form FROM medications 
            WHERE resident_id = ? AND medication_name = ? AND medication_type = 'Controlled'
        ''', (resident_id, medication_name))
        result = cursor.fetchone()
        if result is None:
            return None, None  # Medication not found or not a controlled type

        medication_count, medication_form = result
        return medication_count, medication_form  # Return the count and form


def save_controlled_administration_data(resident_name, medication_name, admin_data, new_count):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Retrieve resident ID and medication ID
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM medications WHERE medication_name = ? AND resident_id = ?", (medication_name, resident_id))
        medication_id = cursor.fetchone()[0]

        # Insert administration data into emar_chart, including the new count
        cursor.execute('''
            INSERT INTO emar_chart (resident_id, medication_id, date, administered, notes, current_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (resident_id, medication_id, admin_data['datetime'], admin_data['initials'], admin_data['notes'], new_count))

        # Update medication count in medications table
        cursor.execute('''
            UPDATE medications
            SET count = ?
            WHERE id = ?
        ''', (new_count, medication_id))

        conn.commit()


def discontinue_medication(resident_name, medication_name, discontinued_date):
    # Get the resident's ID
    resident_id = get_resident_id(resident_name)
    if resident_id is not None:
        with sqlite3.connect('resident_data.db') as conn:
            cursor = conn.cursor()

            # Update the medication record with the discontinued date
            cursor.execute('''
                UPDATE medications 
                SET discontinued_date = ? 
                WHERE resident_id = ? AND medication_name = ? AND (discontinued_date IS NULL OR discontinued_date = '')
            ''', (discontinued_date, resident_id, medication_name))
            
            conn.commit()


def filter_active_medications(medication_names, resident_name):
    active_medications = []

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        for med_name in medication_names:
            cursor.execute('''
                SELECT discontinued_date FROM medications
                JOIN residents ON medications.resident_id = residents.id
                WHERE residents.name = ? AND medications.medication_name = ?
            ''', (resident_name, med_name))
            result = cursor.fetchone()

            # Check if the medication is discontinued and if the discontinuation date is past the current date
            if result is None or (result[0] is None or datetime.now().date() < datetime.strptime(result[0], '%Y-%m-%d').date()):
                active_medications.append(med_name)

    return active_medications


def fetch_discontinued_medications(resident_name):
    """
    Fetches the names and discontinuation dates of discontinued medications for a given resident.

    :param resident_name: Name of the resident.
    :return: A dictionary with medication names as keys and discontinuation dates as values.
    """
    discontinued_medications = {}

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Fetch the resident's ID
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_id_result = cursor.fetchone()
        if resident_id_result is None:
            return discontinued_medications  # Resident not found
        resident_id = resident_id_result[0]

        # Fetch discontinued medications
        cursor.execute('''
            SELECT medication_name, discontinued_date FROM medications 
            WHERE resident_id = ? AND discontinued_date IS NOT NULL
        ''', (resident_id,))

        for medication_name, discontinued_date in cursor.fetchall():
            if discontinued_date:  # Ensure there is a discontinuation date
                discontinued_medications[medication_name] = discontinued_date

    return discontinued_medications


def does_adl_chart_data_exist(resident_name, year_month):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT EXISTS(
                SELECT 1 FROM adl_chart
                WHERE resident_name = ? AND strftime('%Y-%m', date) = ?
            )
        ''', (resident_name, year_month))
        return cursor.fetchone()[0]


ADL_KEYS = [
                "first_shift_sp", "second_shift_sp", "first_shift_activity1", "first_shift_activity2",
                "first_shift_activity3", "second_shift_activity4", "first_shift_bm", "second_shift_bm",
                "shower", "shampoo", "sponge_bath", "peri_care_am", "peri_care_pm", "oral_care_am", "oral_care_pm",
                "nail_care", "skin_care", "shave", "breakfast", "lunch", "dinner", "snack_am",
                "snack_pm", "water_intake"]


def fetch_adl_data_for_resident(resident_name):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM adl_chart
            WHERE resident_name = ? AND date = ?
        ''', (resident_name, today))
        result = cursor.fetchone()
        if result:
            # Convert the row to a dictionary
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, result))
        else:
            return {}


def fetch_adl_chart_data_for_month(resident_name, year_month):
    # year_month should be in the format 'YYYY-MM'
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM adl_chart
            WHERE resident_name = ? AND strftime('%Y-%m', date) = ?
            ORDER BY date
        ''', (resident_name, year_month))
        return cursor.fetchall()


def fetch_adl_data_for_resident_and_date(resident_name, date):
    """
    Fetches ADL data for a specific resident and date.

    Args:
        resident_name (str): The name of the resident.
        date (str): The date in YYYY-MM-DD format.

    Returns:
        dict: A dictionary containing ADL data for the resident and date.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM adl_chart WHERE resident_name = ? AND date = ?
        ''', (resident_name, date))
        result = cursor.fetchone()

    if result:
        # Map the SQL result to dictionary keys based on the ADL chart structure
        adl_data = {
            'first_shift_sp': result[3],
            'second_shift_sp': result[4],
            'first_shift_activity1': result[5],
            'first_shift_activity2': result[6],
            'first_shift_activity3': result[7],
            'second_shift_activity4': result[8],
            'first_shift_bm': result[9],
            'second_shift_bm': result[10],
            'shower': result[11],
            'shampoo': result[12],
            'sponge_bath': result[13],
            'peri_care_am': result[14],
            'peri_care_pm': result[15],
            'oral_care_am': result[16],
            'oral_care_pm': result[17],
            'nail_care': result[18],
            'skin_care': result[19],
            'shave': result[20],
            'breakfast': result[21],
            'lunch': result[22],
            'dinner': result[23],
            'snack_am': result[24],
            'snack_pm': result[25],
            'water_intake': result[26]
        }
        return adl_data
    else:
        # Return an empty dictionary if no data is found for the given resident and date
        return {}


def save_adl_data_from_management_window(resident_name, adl_data):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Construct the SQL statement with all the columns
        sql = '''
            INSERT INTO adl_chart (resident_name, date, first_shift_sp, second_shift_sp, 
            first_shift_activity1, first_shift_activity2, first_shift_activity3, second_shift_activity4, 
            first_shift_bm, second_shift_bm, shower, shampoo, sponge_bath, peri_care_am, 
            peri_care_pm, oral_care_am, oral_care_pm, nail_care, skin_care, shave, 
            breakfast, lunch, dinner, snack_am, snack_pm, water_intake)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(resident_name, date) DO UPDATE SET
            first_shift_sp = excluded.first_shift_sp, second_shift_sp = excluded.second_shift_sp, 
            first_shift_activity1 = excluded.first_shift_activity1, first_shift_activity2 = excluded.first_shift_activity2,
            first_shift_activity3 = excluded.first_shift_activity3, second_shift_activity4 = excluded.second_shift_activity4,
            first_shift_bm = excluded.first_shift_bm, second_shift_bm = excluded.second_shift_bm, shower = excluded.shower,
            shampoo = excluded.shampoo,sponge_bath = excluded.sponge_bath, peri_care_am = excluded.peri_care_am, 
            peri_care_pm = excluded.peri_care_pm, oral_care_am = excluded.oral_care_am, oral_care_pm = excluded.oral_care_pm,
            nail_care = excluded.nail_care, skin_care = excluded.skin_care, shave = excluded.shave, breakfast = excluded.breakfast,
            lunch = excluded.lunch, dinner = excluded.dinner, snack_am = excluded.snack_am, snack_pm = excluded.snack_pm,
            water_intake = excluded.water_intake
        '''
        
        data_tuple = (
            resident_name,
            datetime.now().strftime("%Y-%m-%d"),
            adl_data.get('first_shift_sp', ''),
            adl_data.get('second_shift_sp', ''),
            adl_data.get('first_shift_activity1', ''),
            adl_data.get('first_shift_activity2', ''),
            adl_data.get('first_shift_activity3', ''),
            adl_data.get('second_shift_activity4', ''),
            adl_data.get('first_shift_bm', ''),
            adl_data.get('second_shift_bm', ''),
            adl_data.get('shower', ''),
            adl_data.get('shampoo', ''),
            adl_data.get('sponge_bath', ''),
            adl_data.get('peri_care_am', ''),
            adl_data.get('peri_care_pm', ''),
            adl_data.get('oral_care_am', ''),
            adl_data.get('oral_care_pm', ''),
            adl_data.get('nail_care', ''),
            adl_data.get('skin_care', ''),
            adl_data.get('shave', ''),
            adl_data.get('breakfast', ''),
            adl_data.get('lunch', ''),
            adl_data.get('dinner', ''),
            adl_data.get('snack_am', ''),
            adl_data.get('snack_pm', ''),
            adl_data.get('water_intake', '')
        )
        cursor.execute(sql, data_tuple)
        conn.commit()


def save_adl_data_from_chart_window(resident_name, year_month, window_values):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Define the number of days
        num_days = 31

        # Loop over each day of the month
        for day in range(1, num_days + 1):
            # Extract values for each ADL key for the day
            adl_data = [window_values[f'-{key}-{day}-'] for key in ADL_KEYS]
            
            # Construct the date string for the specific day
            date_str = f"{year_month}-{str(day).zfill(2)}"
            
            # Prepare the SQL statement
            sql = '''
                INSERT INTO adl_chart (resident_name, date, first_shift_sp, second_shift_sp, 
                first_shift_activity1, first_shift_activity2, first_shift_activity3, second_shift_activity4, 
                first_shift_bm, second_shift_bm, shower, shampoo, sponge_bath, peri_care_am, 
                peri_care_pm, oral_care_am, oral_care_pm, nail_care, skin_care, shave, 
                breakfast, lunch, dinner, snack_am, snack_pm, water_intake)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(resident_name, date) DO UPDATE SET
                first_shift_sp = excluded.first_shift_sp, second_shift_sp = excluded.second_shift_sp, 
                first_shift_activity1 = excluded.first_shift_activity1, first_shift_activity2 = excluded.first_shift_activity2,
                first_shift_activity3 = excluded.first_shift_activity3, second_shift_activity4 = excluded.second_shift_activity4,
                first_shift_bm = excluded.first_shift_bm, second_shift_bm = excluded.second_shift_bm, shower = excluded.shower,
                shampoo = excluded.shampoo,sponge_bath = excluded.sponge_bath, peri_care_am = excluded.peri_care_am, 
                peri_care_pm = excluded.peri_care_pm, oral_care_am = excluded.oral_care_am, oral_care_pm = excluded.oral_care_pm,
                nail_care = excluded.nail_care, skin_care = excluded.skin_care, shave = excluded.shave, breakfast = excluded.breakfast,
                lunch = excluded.lunch, dinner = excluded.dinner, snack_am = excluded.snack_am, snack_pm = excluded.snack_pm,
                water_intake = excluded.water_intake
            '''
            
            # Execute the SQL statement
            cursor.execute(sql, (resident_name, date_str, *adl_data))
            
        # Commit the changes to the database
        conn.commit()


def save_prn_administration_data(resident_name, medication_name, admin_data):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Retrieve resident ID and medication ID
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM medications WHERE medication_name = ? AND resident_id = ?", (medication_name, resident_id))
        medication_id = cursor.fetchone()[0]

        # Insert administration data into emar_chart
        cursor.execute('''
            INSERT INTO emar_chart (resident_id, medication_id, date, administered, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (resident_id, medication_id, admin_data['datetime'], admin_data['initials'], admin_data['notes']))

        conn.commit()


def save_emar_data_from_chart_window(resident_name, year_month, window_values):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        num_days = 31

        for day in range(1, num_days + 1):
            date_str = f"{year_month}-{str(day).zfill(2)}"
            
            for key, value in window_values.items():
                if key.startswith('-') and key.endswith(f'-{day}-'):
                    # Extract medication name and time slot from the key
                    parts = key.strip('-').split('_')
                    medication_name = '_'.join(parts[:-1])  # Rejoin all parts except the last one
                    time_slot = parts[-1].split('-')[0]

                    sql = '''
                        INSERT INTO emar_chart (resident_id, medication_id, date, time_slot, administered)
                        SELECT residents.id, medications.id, ?, ?, ?
                        FROM residents, medications
                        WHERE residents.name = ? AND medications.medication_name = ?
                        ON CONFLICT(resident_id, medication_id, date, time_slot) DO UPDATE SET
                        administered = excluded.administered
                    '''
                    cursor.execute(sql, (date_str, time_slot, value, resident_name, medication_name))

        conn.commit()


def fetch_current_emar_data_for_resident_date(resident_name, date):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT m.medication_name, ec.time_slot, ec.administered, ec.date
                          FROM emar_chart ec
                          JOIN residents r ON ec.resident_id = r.id
                          JOIN medications m ON ec.medication_id = m.id
                          WHERE r.name = ? AND ec.date = ?''', (resident_name, date))
        rows = cursor.fetchall()
        return [{'resident_name': resident_name, 'medication_name': row[0], 'time_slot': row[1], 'administered': row[2], 'date': row[3]} for row in rows]


def save_emar_data_from_management_window(emar_data):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        for entry in emar_data:
            # Fetch medication_id based on resident_id and medication_name
            cursor.execute('''
                SELECT m.id FROM medications m
                JOIN residents r ON m.resident_id = r.id
                WHERE m.medication_name = ? AND r.name = ?
            ''', (entry['medication_name'], entry['resident_name']))
            medication_id_result = cursor.fetchone()

            if medication_id_result:
                medication_id = medication_id_result[0]

                # Insert or update emar_chart data
                cursor.execute('''
                    INSERT INTO emar_chart (resident_id, medication_id, date, time_slot, administered)
                    SELECT r.id, ?, ?, ?, ?
                    FROM residents r
                    WHERE r.name = ?
                    ON CONFLICT(resident_id, medication_id, date, time_slot) DO UPDATE SET
                    administered = excluded.administered
                ''', (medication_id, entry['date'], entry['time_slot'], entry['administered'], entry['resident_name']))

        conn.commit()


def fetch_emar_data_for_resident(resident_name):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Get the resident ID
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_id_result = cursor.fetchone()
        if not resident_id_result:
            return {}  # No such resident
        resident_id = resident_id_result[0]

        # Fetch eMAR data for the resident for today
        cursor.execute("""
            SELECT m.medication_name, e.time_slot, e.administered
            FROM emar_chart e
            JOIN medications m ON e.medication_id = m.id
            WHERE e.resident_id = ? AND e.date = ?
        """, (resident_id, today))

        results = cursor.fetchall()

    # Organize eMAR data by medication name and time slot
    emar_data = {}
    for med_name, time_slot, administered in results:
        if med_name not in emar_data:
            emar_data[med_name] = {}
        emar_data[med_name][time_slot] = administered

    return emar_data


def fetch_emar_data_for_month(resident_name, year_month):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Query to fetch eMAR data for the given month and resident
        cursor.execute('''
            SELECT m.medication_name, e.date, e.time_slot, e.administered
            FROM emar_chart e
            JOIN residents r ON e.resident_id = r.id
            JOIN medications m ON e.medication_id = m.id
            WHERE r.name = ? AND strftime('%Y-%m', e.date) = ?
        ''', (resident_name, year_month))
        return cursor.fetchall()


def fetch_prn_data_for_day(event_key, resident_name, year_month):
    _, med_name, day, _ = event_key.split('-')
    parts = med_name.split('_')
    med_name = parts[1] 
    day = day.zfill(2)  # Ensure day is two digits
    date_query = f'{year_month}-{day}'

    # Debugging: Print the values
    # print(f"Medication Name: {med_name}, Date Query: {date_query}")

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        query = '''
            SELECT e.date, e.administered, e.notes
            FROM emar_chart e
            JOIN residents r ON e.resident_id = r.id
            JOIN medications m ON e.medication_id = m.id
            WHERE r.name = ? AND m.medication_name = ? AND e.date LIKE ?
        '''
        cursor.execute(query, (resident_name, med_name, date_query + '%'))
        result = cursor.fetchall()
        
        # Debugging: Print the SQL result
        # print(f"SQL Query Result: {result}")

        return result


def fetch_controlled_data_for_day(event_key, resident_name, year_month):
    _, med_name, day, _ = event_key.split('-')
    parts = med_name.split('_')
    med_name = parts[1] 
    day = day.zfill(2)  # Ensure day is two digits
    date_query = f'{year_month}-{day}'

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.date, e.administered, e.notes, e.current_count
            FROM emar_chart e
            JOIN residents r ON e.resident_id = r.id
            JOIN medications m ON e.medication_id = m.id
            WHERE r.name = ? AND m.medication_name = ? AND e.date LIKE ? AND m.medication_type = 'Controlled'
        ''', (resident_name, med_name, date_query + '%'))
        return cursor.fetchall()


def fetch_monthly_medication_data(resident_name, medication_name, year_month, medication_type):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Fetch resident ID
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_id_result = cursor.fetchone()
        if not resident_id_result:
            return []  # Resident not found
        resident_id = resident_id_result[0]

        # Fetch medication ID
        cursor.execute("SELECT id FROM medications WHERE medication_name = ? AND resident_id = ?", (medication_name, resident_id))
        medication_id_result = cursor.fetchone()
        if not medication_id_result:
            return []  # Medication not found
        medication_id = medication_id_result[0]

        # Query for the entire month
        year, month = year_month.split('-')
        start_date = f"{year}-{month}-01"
        end_date = f"{year}-{month}-{calendar.monthrange(int(year), int(month))[1]}"

        if medication_type == 'Controlled':
            # For Controlled medications, include count information
            cursor.execute('''
                SELECT date, administered, notes, count
                FROM emar_chart
                WHERE resident_id = ? AND medication_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
            ''', (resident_id, medication_id, start_date, end_date))
        else:
            # For PRN medications
            cursor.execute('''
                SELECT date, administered, notes
                FROM emar_chart
                WHERE resident_id = ? AND medication_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
            ''', (resident_id, medication_id, start_date, end_date))

        return cursor.fetchall()


def does_emars_chart_data_exist(resident_name, year_month):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Query to check if there is any eMAR chart data for the resident in the given month
        cursor.execute('''
            SELECT EXISTS(
                SELECT 1 FROM emar_chart
                JOIN residents ON emar_chart.resident_id = residents.id
                WHERE residents.name = ? AND strftime('%Y-%m', emar_chart.date) = ?
            )
        ''', (resident_name, year_month))
        return cursor.fetchone()[0] == 1
