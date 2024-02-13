import sqlite3
from datetime import datetime, timedelta
import os
import calendar
import bcrypt
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import config
import sys
import PySimpleGUI as sg
import string
import secrets
import pyperclip


def generate_strong_passphrase(length=15):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    passphrase = ''.join(secrets.choice(alphabet) for i in range(length))
    return passphrase


# Check if the environment variable exists
passphrase_env_var = os.environ.get('RESIDENT_MGMT_DB_KEY')
if passphrase_env_var:
    passphrase = passphrase_env_var.encode()  # Proceed with encoding if exists
else:
    passphrase = generate_strong_passphrase()  # Generate a new passphrase if not found

    detailed_instructions = (
        f"Passphrase: {passphrase}\n\n"
        "Setting the Environment Variable\n\n"
        "For Windows:\n"
        "1. Open the Start Search, type in 'env', and choose 'Edit the system environment variables'.\n"
        "2. In the System Properties window, click on the 'Environment Variables…' button.\n"
        "3. In the Environment Variables window, click 'New…' under the 'System variables' section.\n"
        "4. Set the variable name as RESIDENT_MGMT_DB_KEY and paste the passphrase in the variable value. Click OK.\n\n"
        "For macOS and Linux:\n"
        "1. Open a terminal window.\n"
        "2. Enter the following command, replacing <passphrase> with the actual passphrase:\n"
        "   echo 'export RESIDENT_MGMT_DB_KEY=\"<passphrase>\"' >> ~/.bash_profile\n"
        "3. For the change to take effect, you might need to reload the profile with source ~/.bash_profile or simply restart the terminal."
    )

    layout = [
        [sg.Text("Passphrase not found. Please follow the instructions below to set it up.")],
        [sg.Multiline(detailed_instructions, size=(80, 15), disabled=True)],
        [sg.Button("Copy Passphrase")]
    ]

    window = sg.Window("Setup Passphrase", layout)

    while True:
        event, values = window.read()

        if event == sg.WINDOW_CLOSED:
            break
        elif event == "Copy Passphrase":
            pyperclip.copy(passphrase)
            sg.popup("Passphrase copied to clipboard. Please follow the instructions to set it as an environment variable.", keep_on_top=True)

    window.close()
    sys.exit()  # Exit after displaying the instructions
 

if passphrase_env_var == None:
    sg.popup(detailed_instructions)
    sys.exit()

salt = b'\x00'*16  # Use a fixed salt; TO BE CHANGED TO BE RANDOM

# Generate a key from the passphrase
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
    backend=default_backend()
)
key = base64.urlsafe_b64encode(kdf.derive(passphrase))
fernet = Fernet(key)


def encrypt_data(data):
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(data):
    return fernet.decrypt(data.encode()).decode()  # Decrypt and convert back to string


def fetch_residents():
    """ Fetches a list of resident names from the database. """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM residents')
        return [row[0] for row in cursor.fetchall()]


def get_resident_care_level():
    """Fetch and decrypt residents' care level from the database."""
    decrypted_care_levels = {}
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name, level_of_care FROM residents')
        for name, encrypted_level_of_care in cursor.fetchall():
            decrypted_level_of_care = decrypt_data(encrypted_level_of_care)  # Assuming decrypt_data is already defined
            decrypted_care_levels[name] = decrypted_level_of_care
    return decrypted_care_levels


def log_action(username, action, description):
    # Get current time in local timezone
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (username, action, description, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (username, action, encrypt_data(description), current_time))
        conn.commit()


def fetch_audit_logs(last_10_days=False, username='', action='', date=''):
    conn = sqlite3.connect('resident_data.db')
    cursor = conn.cursor()
    
    # Start building the query
    query = "SELECT timestamp, username, action, description FROM audit_logs WHERE 1=1"
    params = []
    
    # Filter for the last 10 days
    if last_10_days:
        ten_days_ago = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        query += " AND timestamp >= ?"
        params.append(ten_days_ago)
    
    # Filter by username if provided
    if username:
        query += " AND username LIKE ?"
        params.append(f"%{username}%")
    
    # Filter by action if provided
    if action:
        query += " AND action = ?"
        params.append(action)
    
    # Filter by specific date if provided
    if date:
        query += " AND DATE(timestamp) = ?"
        params.append(date)
    
    # Add ORDER BY clause to sort by timestamp in descending order
    query += " ORDER BY timestamp DESC"

    # Execute the query with the filters applied
    cursor.execute(query, params)
    
    # Fetch all matching records
    logs = cursor.fetchall()
    
    # Close the database connection
    conn.close()
    
    # Decrypt the description in each log entry
    decrypted_logs = []
    for log in logs:
        decrypted_description = fernet.decrypt(log[3].encode()).decode()
        decrypted_logs.append({'date': log[0], 'username': log[1], 'action': log[2], 'description': decrypted_description})
    
    
    return decrypted_logs


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


def save_backup_configuration(backup_folder, backup_frequency):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Check if a row exists
        cursor.execute("SELECT id FROM backup_config WHERE id = 1")
        exists = cursor.fetchone()
        
        if exists:
            # Update if row exists
            cursor.execute('''
                UPDATE backup_config
                SET backup_folder = ?, backup_frequency = ?
                WHERE id = 1
            ''', (backup_folder, backup_frequency))
        else:
            # Insert if no row exists
            cursor.execute('''
                INSERT INTO backup_config (id, backup_folder, backup_frequency)
                VALUES (1, ?, ?)
            ''', (backup_folder, backup_frequency))
        
        conn.commit()


def get_backup_configuration():
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT backup_folder, backup_frequency, last_backup_date FROM backup_config WHERE id = 1")
        config = cursor.fetchone()
        if config:
            # Parse the last_backup_date string to datetime.date
            last_backup_date = datetime.strptime(config[2], "%Y-%m-%d").date()
            return {'backup_folder': config[0], 'backup_frequency': config[1], 'last_backup_date': last_backup_date}
        else:
            return None


def update_last_backup_date():
    # Update the last backup date in the backup configuration
    last_backup_date = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE backup_config SET last_backup_date = ? WHERE id = 1", (last_backup_date,))
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


def get_all_usernames():
    conn = sqlite3.connect('resident_data.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    usernames = [row[0] for row in c.fetchall()]
    conn.close()
    return usernames


def remove_user(username):
    conn = sqlite3.connect('resident_data.db')
    c = conn.cursor() 

    # Delete the user from the users table
    c.execute("DELETE FROM users WHERE username = ?", (username,))

    conn.commit()
    conn.close()


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
    """ Insert a new resident into the database, with encryption for certain fields. """
    encrypted_dob = encrypt_data(date_of_birth)  # Assuming encrypt_data is already defined
    encrypted_level_of_care = encrypt_data(level_of_care)

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO residents (name, date_of_birth, level_of_care) VALUES (?, ?, ?)', 
                       (name, encrypted_dob, encrypted_level_of_care))
        conn.commit()


def fetch_resident_information(resident_name):
    """Fetch and decrypt a resident's information from the database."""
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, date_of_birth FROM residents WHERE name = ?", (resident_name,))
        result = cursor.fetchone()
        if result:
            name, encrypted_date_of_birth = result
            decrypted_date_of_birth = decrypt_data(encrypted_date_of_birth)  # Assuming decrypt_data is already defined
            return {'name': name, 'date_of_birth': decrypted_date_of_birth}
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
            decrypted_dosage = decrypt_data(dosage)
            decrypted_instructions = decrypt_data(instructions)
            if time_slot not in scheduled_medications:
                scheduled_medications[time_slot] = {}
            scheduled_medications[time_slot][med_name] = {
                'dosage': decrypted_dosage, 'instructions': decrypted_instructions}

        # Fetch PRN Medications
        cursor.execute("""
            SELECT medication_name, dosage, instructions
            FROM medications 
            WHERE resident_id = ? AND medication_type = 'As Needed (PRN)'
        """, (resident_id,))
        prn_results = cursor.fetchall()

        prn_medications = {med_name: {'dosage': decrypt_data(dosage), 'instructions': decrypt_data(instructions)} 
            for med_name, dosage, instructions in prn_results}

        # Fetch Controlled Medications
        cursor.execute("""
            SELECT medication_name, dosage, instructions, count, medication_form
            FROM medications 
            WHERE resident_id = ? AND medication_type = 'Controlled'
        """, (resident_id,))
        controlled_results = cursor.fetchall()

        controlled_medications = {med_name: {'dosage': decrypt_data(dosage), 'instructions': decrypt_data(instructions), 'count': count, 'form': form} 
            for med_name, dosage, instructions, count, form in controlled_results}

        # Combine the data into a single structure
        medications_data = {'Scheduled': scheduled_medications, 'PRN': prn_medications, 'Controlled': controlled_medications}
        return medications_data


def insert_medication(resident_name, medication_name, dosage, instructions, medication_type, selected_time_slots, medication_form=None, count=None):
    resident_id = get_resident_id(resident_name)
    if resident_id is not None:
        with sqlite3.connect('resident_data.db') as conn:
            cursor = conn.cursor()

            # Encrypt PHI fields
            encrypted_dosage = encrypt_data(dosage)
            encrypted_instructions = encrypt_data(instructions)

            # Prepare values for insertion with encrypted data
            values_to_insert = (resident_id, medication_name, encrypted_dosage, encrypted_instructions, medication_type)

            # Prepare the SQL query based on medication type
            if medication_type == 'Controlled':
                # For controlled medications, include medication form and count
                sql_query = 'INSERT INTO medications (resident_id, medication_name, dosage, instructions, medication_type, medication_form, count) VALUES (?, ?, ?, ?, ?, ?, ?)'
                # Assume medication_form and count are not considered PHI and do not need encryption
                values_to_insert += (medication_form, count)
            else:
                # For other medication types, use the default query
                sql_query = 'INSERT INTO medications (resident_id, medication_name, dosage, instructions, medication_type) VALUES (?, ?, ?, ?, ?)'

            # Insert medication details with encrypted PHI
            cursor.execute(sql_query, values_to_insert)
            medication_id = cursor.lastrowid

            # Handle time slot relations for scheduled medications
            if medication_type == 'Scheduled':
                for slot in selected_time_slots:
                    cursor.execute('SELECT id FROM time_slots WHERE slot_name = ?', (slot,))
                    slot_id = cursor.fetchone()[0]
                    cursor.execute('INSERT INTO medication_time_slots (medication_id, time_slot_id) VALUES (?, ?)', (medication_id, slot_id))
            
            conn.commit()


def remove_medication(medication_name, resident_name):
    resident_id = get_resident_id(resident_name)
    # Connect to the database
    conn = sqlite3.connect('resident_data.db')
    c = conn.cursor()

    try:
        # Start a transaction
        conn.execute('BEGIN')

        # Get the medication ID
        c.execute('SELECT id FROM medications WHERE medication_name = ? AND resident_id = ?', (medication_name, resident_id))
        medication_id = c.fetchone()
        if medication_id:
            medication_id = medication_id[0]

            # Delete related entries from medication_time_slots
            c.execute('DELETE FROM medication_time_slots WHERE medication_id = ?', (medication_id,))

            # Delete related entries from emar_chart
            c.execute('DELETE FROM emar_chart WHERE medication_id = ?', (medication_id,))

            # Finally, delete the medication itself
            c.execute('DELETE FROM medications WHERE id = ?', (medication_id,))

        # Commit the transaction
        conn.commit()
        log_action(config.global_config['logged_in_user'], 'Medication Deleted', f'{medication_name} removed')
        print(f"Medication '{medication_name}' and all related data successfully removed.")
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        print(f"Error removing medication: {e}")
    finally:
        # Close the connection
        conn.close()


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
        encrypted_new_dosage = encrypt_data(new_dosage)
        encrypted_new_instructions = encrypt_data(new_instructions)
        cursor = conn.cursor()
        cursor.execute("UPDATE medications SET medication_name = ?, dosage = ?, instructions = ? WHERE medication_name = ? AND resident_id = ?", (new_name, encrypted_new_dosage, encrypted_new_instructions, old_name, resident_id))
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
            decrypted_medication_name = decrypt_data(medication_name) if medication_name else medication_name
            if discontinued_date:  # Ensure there is a discontinuation date
                discontinued_medications[decrypted_medication_name] = discontinued_date

    return discontinued_medications


def save_non_medication_order(resident_id, order_name, frequency, specific_days, special_instructions):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        
        # Prepare the frequency and specific_days values for insertion
        # If specific_days is not empty, set frequency to None
        if specific_days:  # Assuming specific_days is a comma-separated string like 'Mon,Wed,Fri'
            frequency_value = None  # No frequency because specific days are provided
        else:
            frequency_value = frequency  # Use the frequency as provided
            specific_days = None  # No specific days because frequency is used

        # Insert the non-medication order into the database
        cursor.execute('''
            INSERT INTO non_medication_orders (resident_id, order_name, frequency, specific_days, special_instructions)
            VALUES (?, ?, ?, ?, ?)
        ''', (resident_id, order_name, frequency_value, specific_days, special_instructions))

        conn.commit()


def update_non_med_order_details(order_name, resident_id, new_order_name, new_instructions):
    """
    Updates the details of a non-medication order for a specific resident.
    
    Parameters:
        order_name (str): The current name of the order.
        resident_id (int): The ID of the resident to whom the order belongs.
        new_order_name (str): The new name for the order.
        new_instructions (str): The new special instructions for the order.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Prepare the SQL statement for updating the order details.
        # This statement updates the order's name and special instructions
        # only if the new values are provided (not empty).
        sql = """
        UPDATE non_medication_orders
        SET order_name = COALESCE(NULLIF(?, ''), order_name),
            special_instructions = COALESCE(NULLIF(?, ''), special_instructions)
        WHERE order_name = ? AND resident_id = ?
        """

        # Execute the SQL statement with the new values and the original order name and resident ID.
        cursor.execute(sql, (new_order_name, new_instructions, order_name, resident_id))
        
        # Commit the transaction to save changes.
        conn.commit()
        
        if cursor.rowcount == 0:
            # If no rows were updated, it could mean the order name/resident ID didn't match.
            print("No order was updated. Please check the order name and resident ID.")
        else:
            log_action(config.global_config['logged_in_user'], 'Non-Medication Order Updated', f'{order_name} updated for {resident_id}')


def remove_non_med_order(order_name, resident_name):
    """
    Removes a non-medication order for a specific resident.
    
    Parameters:
        order_name (str): The name of the non-medication order to be removed.
        resident_name (str): The name of the resident from whom the order is to be removed.
    """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # First, get the resident ID for the given resident name to ensure accuracy
        cursor.execute("SELECT id FROM residents WHERE name = ?", (resident_name,))
        resident_result = cursor.fetchone()
        
        if resident_result is None:
            print(f"No resident found with the name {resident_name}.")
            return

        resident_id = resident_result[0]

        # Prepare the SQL statement for deleting the non-medication order
        sql = """
        DELETE FROM non_medication_orders
        WHERE order_name = ? AND resident_id = ?
        """

        # Execute the SQL statement with the order name and resident ID
        cursor.execute(sql, (order_name, resident_id))
        
        # Commit the transaction to save changes
        conn.commit()
        
        if cursor.rowcount == 0:
            # If no rows were deleted, it means the order name/resident ID didn't match any record
            print("No non-medication order was removed. Please check the order name and resident name.")
        else:
            log_action(config.global_config['logged_in_user'], 'Non-Medication Order Removed', f'{order_name} removed for {resident_name}')


def fetch_all_non_medication_orders_for_resident(resident_name):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        resident_id = get_resident_id(resident_name)

        # Fetch all non-medication orders for the resident ID
        cursor.execute('''
            SELECT order_id, order_name, frequency, specific_days, special_instructions,  discontinued_date, last_administered_date
            FROM non_medication_orders
            WHERE resident_id = ?
        ''', (resident_id,))
        orders = cursor.fetchall()

        # Prepare and return the list of orders
        non_medication_orders = [{
            'order_id': order[0],
            'order_name': order[1],
            'frequency': order[2],
            'specific_days': order[3],
            'special_instructions': order[4],
           'discontinued_date': order[5],
           'last_administered_date': order[6]
           
        } for order in orders]

    return non_medication_orders


def fetch_administrations_for_order(order_id, month, year):
    # Connect to the SQLite database
    conn = sqlite3.connect('resident_data.db')
    cursor = conn.cursor()

    # Update the query to include the initials field
    query = """
    SELECT administration_date, notes, initials
    FROM non_med_order_administrations
    WHERE order_id = ? AND strftime('%m', administration_date) = ? AND strftime('%Y', administration_date) = ?
    ORDER BY administration_date ASC
    """

    # Execute the query
    cursor.execute(query, (order_id, month.zfill(2), year))

    # Fetch and format the results, now including initials
    results = cursor.fetchall()
    formatted_results = [[datetime.strptime(row[0], '%Y-%m-%d').strftime('%b %d, %Y'), row[1], row[2]] for row in results]

    # Close the database connection
    conn.close()

    return formatted_results


def record_non_med_order_performance(order_name, resident_id, notes, user_initials):
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()

        # Step 1: Look up the order_id
        cursor.execute('''
            SELECT order_id FROM non_medication_orders
            WHERE order_name = ? AND resident_id = ?
        ''', (order_name, resident_id))
        order_result = cursor.fetchone()
        if not order_result:
            print("Order not found.")
            return
        order_id = order_result[0]

        # Step 2: Insert a new record into the non_med_order_administrations table with initials
        current_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT INTO non_med_order_administrations (order_id, resident_id, administration_date, notes, initials)
            VALUES (?, ?, ?, ?, ?)
        ''', (order_id, resident_id, current_date, notes, user_initials))

        # Step 3: Update the last_administered_date for the order
        cursor.execute('''
            UPDATE non_medication_orders
            SET last_administered_date = ?
            WHERE order_id = ?
        ''', (current_date, order_id))

        conn.commit()
        log_action(config.global_config['logged_in_user'], 'Non-Medication Order Administered', f'{order_name} administered for {resident_id}')


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
    resident_id = get_resident_id(resident_name)  # Ensure this function exists and correctly fetches the ID

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Adjust the query to use resident_id instead of resident_name
        cursor.execute('''
            SELECT * FROM adl_chart
            WHERE resident_id = ? AND date = ?
        ''', (resident_id, today))
        result = cursor.fetchone()
        
        if result:
            # Convert the row to a dictionary
            columns = [col[0] for col in cursor.description]
            # Mapping each column to its value, excluding resident_id to maintain data abstraction
            adl_data = {columns[i]: result[i] for i in range(1, len(columns))}  # Skipping index 0 assuming it's resident_id
            return adl_data
        else:
            return {}


def fetch_adl_chart_data_for_month(resident_name, year_month):
    # year_month should be in the format 'YYYY-MM'
    resident_id = get_resident_id(resident_name)
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM adl_chart
            WHERE resident_id = ? AND strftime('%Y-%m', date) = ?
            ORDER BY date
        ''', (resident_id, year_month))
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
    resident_id = get_resident_id(resident_name)
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM adl_chart WHERE resident_id = ? AND date = ?
        ''', (resident_id, date))
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
    resident_id = get_resident_id(resident_name)

    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        # Construct the SQL statement with all the columns
        sql = '''
            INSERT INTO adl_chart (resident_id, date, first_shift_sp, second_shift_sp, 
            first_shift_activity1, first_shift_activity2, first_shift_activity3, second_shift_activity4, 
            first_shift_bm, second_shift_bm, shower, shampoo, sponge_bath, peri_care_am, 
            peri_care_pm, oral_care_am, oral_care_pm, nail_care, skin_care, shave, 
            breakfast, lunch, dinner, snack_am, snack_pm, water_intake)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(resident_id, date) DO UPDATE SET
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
            resident_id, 
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
    resident_id = get_resident_id(resident_name)
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
                INSERT INTO adl_chart (resident_id, date, first_shift_sp, second_shift_sp, 
                first_shift_activity1, first_shift_activity2, first_shift_activity3, second_shift_activity4, 
                first_shift_bm, second_shift_bm, shower, shampoo, sponge_bath, peri_care_am, 
                peri_care_pm, oral_care_am, oral_care_pm, nail_care, skin_care, shave, 
                breakfast, lunch, dinner, snack_am, snack_pm, water_intake)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(resident_id, date) DO UPDATE SET
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
            cursor.execute(sql, (resident_id, date_str, *adl_data))
            
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
            # Fetch the resident_id
            cursor.execute("SELECT id FROM residents WHERE name = ?", (entry['resident_name'],))
            resident_id_result = cursor.fetchone()
            if resident_id_result is None:
                continue  # Skip if resident not found
            resident_id = resident_id_result[0]

            # Fetch medication_id based on resident_id and unencrypted medication_name
            cursor.execute("SELECT id FROM medications WHERE resident_id = ? AND medication_name = ?", (resident_id, entry['medication_name']))
            medication_id_result = cursor.fetchone()
            if medication_id_result is None:
                continue  # Skip if medication not found
            medication_id = medication_id_result[0]

            # Insert or update emar_chart data
            cursor.execute('''
                INSERT INTO emar_chart (resident_id, medication_id, date, time_slot, administered)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(resident_id, medication_id, date, time_slot) 
                DO UPDATE SET administered = excluded.administered
            ''', (resident_id, medication_id, entry['date'], entry['time_slot'], entry['administered']))

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

