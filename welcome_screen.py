import sqlite3
import PySimpleGUI as sg
import adl_management
import resident_management
import db_functions
         

# Connect to SQLite database
# The database file will be 'resident_data.db'
conn = sqlite3.connect('resident_data.db')
c = conn.cursor()

# Create table for user settings
c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_name TEXT UNIQUE,
    setting_value TEXT)''')

# Create  Resident table
c.execute('''CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER,
    additional_info TEXT,
    self_care INTEGER)''')

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


# Function to load and apply the user's theme
def apply_user_theme():
    user_theme = db_functions.get_user_theme()
    sg.theme(user_theme)


# Apply user theme at application startup
apply_user_theme()


def enter_resident_info():
    """ Display GUI for entering resident information. """
    layout = [
        [sg.Text('Please Enter Resident Information')],
        [sg.Text('Name', size=(15, 1)), sg.InputText(key='Name')],
        [sg.Text('Age', size=(15, 1)), sg.InputText(key='Age')],
        [sg.Text('Additional Info', size=(15, 1)), sg.InputText(key='Additional_Info')],
        [sg.Checkbox('Supervisory Level of Care', key='Self_Care')],
        [sg.Submit(), sg.Cancel()]
    ]

    window = sg.Window('Enter Resident Info', layout)

    while True:
        event, values = window.read()
        if event in (None, 'Cancel'):
            display_welcome_window(db_functions.get_resident_count())
            break
        elif event == 'Submit':
            db_functions.insert_resident(values['Name'], values['Age'], values['Additional_Info'], values['Self_Care'])
            sg.popup('Resident information saved!')
            window.close()
            return True

    window.close()
    return False


def fetch_residents():
    """ Fetches a list of resident names from the database. """
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM residents')
        return [row[0] for row in cursor.fetchall()]


def enter_resident_removal():
    # Fetch the list of residents for the dropdown
    residents = fetch_residents()

    # Define the layout for the removal window
    layout = [
        [sg.Text('Warning: Removing a resident is irreversible.', text_color='red')],
        [sg.Text('Please ensure you have saved any required data before proceeding.')],
        [sg.Text('Select a resident to remove:'), sg.Combo(residents, key='-RESIDENT-')],
        [sg.Button('Remove Resident'), sg.Button('Cancel')]
    ]

    # Create the removal window
    window = sg.Window('Remove Resident', layout)

    # Event loop for the removal window
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Cancel':
            break
        elif event == 'Remove Resident':
            # Confirm the removal
            resident_to_remove = values['-RESIDENT-']
            if resident_to_remove:  # Proceed only if a resident is selected
                confirm = sg.popup_yes_no('Are you sure you want to remove this resident? This action cannot be undone.')
                if confirm == 'Yes':
                    db_functions.remove_resident(resident_to_remove)
                    sg.popup(f'Resident {resident_to_remove} has been removed.')
                    window.close()
                    break

    window.close()


def change_theme_window():
    # Define the theme options available
    theme_options = sg.theme_list()

    # Layout for the theme selection window
    layout = [
        [sg.Text('Select Theme')],
        [sg.Combo(theme_options, default_value=sg.theme(), key='-THEME-', readonly=True)],
        [sg.Button('Ok'), sg.Button('Cancel')]
    ]

    # Create the theme selection window
    theme_window = sg.Window('Change Theme', layout)

    # Event loop for the theme window
    while True:
        event, values = theme_window.read()
        if event in (None, 'Cancel'):
            theme_window.close()
            display_welcome_window(db_functions.get_resident_count())
            break
        elif event == 'Ok':
            selected_theme = values['-THEME-']
            sg.theme(values['-THEME-'])
            db_functions.save_user_theme_choice(selected_theme)
            theme_window.close()
            display_welcome_window(db_functions.get_resident_count())
            break

    theme_window.close()


def display_welcome_window(num_of_residents_local):
    """ Display a welcome window with the number of residents. """
    

    image_path = 'ct-logo.png'
    layout = [
        [sg.Text(f'Welcome to CareTech Resident Manager', font=("Helvetica", 16),
                 justification='center')],
        [sg.Image(image_path)],
        [sg.Text(f'Your Facility Currently has {num_of_residents_local} Resident(s)',
                 font=("Helvetica", 14), justification='center')],
        [sg.Button('Enter Resident Management'),
         sg.Button('Add Resident', button_color='green'), sg.Button('Remove Resident', button_color='red')], 
         [sg.Text(text='', expand_x=True), sg.Button("Change Theme"), sg.Text(text='', expand_x=True)]
    ]

    window = sg.Window('CareTech Resident Manager', layout, element_justification='c')

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'Add Resident':
            window.close()
            enter_resident_info()
            break
        elif event == 'Remove Resident':
            enter_resident_removal()
        elif event == 'Enter Resident Management':
            if db_functions.get_resident_count() == 0:
                sg.popup("Your Facility Has No Residents. Please Select Click Add Resident.")
                continue
            else:
                window.hide()  # Hide the welcome window
                resident_management.main()
                window.un_hide()
                
        elif event == 'Change Theme':
            window.close()
            change_theme_window()

    window.close()
    conn.close()


if __name__ == "__main__":
    display_welcome_window(db_functions.get_resident_count())


