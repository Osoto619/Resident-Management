import sqlite3
import PySimpleGUI as sg
import adl_management
import resident_management
import db_functions
from datetime import datetime, timedelta
from tkinter import font

# Connect to SQLite database
# The database file will be 'resident_data.db'
conn = sqlite3.connect('resident_data.db')
c = conn.cursor()

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


# Function to load and apply the user's theme
def apply_user_theme():
    user_theme = db_functions.get_user_theme()
    sg.theme(user_theme)


# Apply user theme at application startup
apply_user_theme()

FONT = db_functions.get_user_font()
FONT_BOLD = 'Arial Bold'

def enter_resident_info():
    # Calculate the default date (85 years ago from today)
    past = datetime.now() - timedelta(days=85*365)
    
    """ Display GUI for entering resident information. """
    layout = [
    [sg.Text('Please Enter Resident Information', justification='center', expand_x=True, font=(FONT, 18))],
    [sg.Text('Name', size=(15, 1), font=(FONT, 12)), sg.InputText(key='Name', size=(20,1), font=(FONT, 12))],
    [sg.Text('Date of Birth', size=(15, 1), font=(FONT, 12)), 
     sg.InputText(key='Date_of_Birth', size=(20,1), disabled=True, font=(FONT, 12)), 
     sg.CalendarButton('Choose Date', target='Date_of_Birth', 
                       default_date_m_d_y=(past.month, past.day, past.year), 
                       format='%Y-%m-%d', font=(FONT, 12))],
    [sg.Text('Level of Care', justification='center', expand_x=True, font=(FONT, 15))],
    [sg.Radio('Supervisory Care', "RADIO1", default=True, key='Supervisory_Care', size=(15,1), font=(FONT, 12)), 
     sg.Radio('Personal Care', "RADIO1", key='Personal_Care', size=(15,1), font=(FONT, 12)), 
     sg.Radio('Directed Care', "RADIO1", key='Directed_Care', size=(15,1), font=(FONT, 12))],
    [sg.Text('', expand_x=True), sg.Submit(font=(FONT, 12)), sg.Cancel(font=(FONT, 12)), sg.Text('', expand_x=True)]
]


    window = sg.Window('Enter Resident Info', layout)

    while True:
        event, values = window.read()
        if event in (None, 'Cancel'):
            break
        elif event == 'Submit':
             # Determine the selected level of care
            level_of_care = 'Supervisory Care' if values['Supervisory_Care'] else 'Personal Care' if values['Personal_Care'] else 'Directed Care'
            db_functions.insert_resident(values['Name'].title(), values['Date_of_Birth'], level_of_care)
            sg.popup('Resident information saved!')
            window.close()
            return True

    window.close()
    

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
        [sg.Text('Warning: Removing a resident is irreversible.', text_color='red', font=(FONT_BOLD, 16))],
        [sg.Text('Please ensure you have saved any required data before proceeding.', font=(FONT, 12))],
        [sg.Text('Select a resident to remove:', font=(FONT, 12)), sg.Combo(residents, key='-RESIDENT-', font=(FONT, 12))],
        [sg.Button('Remove Resident', font=(FONT, 12)), sg.Button('Cancel', font=(FONT, 12))]
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
    global FONT
    # Define the theme options available
    theme_options = sg.theme_list()

    # Define the font options available
    symbol_fonts = [
    'Webdings', 'Wingdings', 'Wingdings 2', 'Wingdings 3', 'Symbol', 
    'MS Outlook', 'Bookshelf Symbol 7', 'MT Extra', 
    'HoloLens MDL2 Assets', 'Segoe MDL2 Assets', 'Segoe UI Emoji', 
    'Segoe UI Symbol', 'Marlett', 'Cambria Math', 'Terminal'
    # Add any other symbol fonts you want to exclude
    ]

    font_options = [f for f in font.families() if f not in symbol_fonts]
    # print(font_options)
    
    layout = [
        [sg.Text(text= 'Select Theme Colors:', font=(FONT, 20))],
        [sg.Combo(theme_options, default_value=sg.theme(), key='-THEME-', readonly=True, font=(FONT, 12))],
        [sg.Text(text='Select Font:', font=(FONT,20))],
        [sg.Combo(font_options, default_value=db_functions.get_user_font(), key='-FONT_CHOICE-', font=(FONT, 12))],
        [sg.Text(text='', expand_x=True), sg.Button(button_text= 'Ok', font=(FONT, 15), pad= ((10,10), (12,0))), 
         sg.Button(button_text='Cancel', font=(FONT, 15), pad= ((10,10), (12,0))),
         sg.Text(text='', expand_x=True)]
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

            selected_font = values['-FONT_CHOICE-']
            db_functions.save_user_font_choice(selected_font)
            FONT = db_functions.get_user_font()

            theme_window.close()
            display_welcome_window(db_functions.get_resident_count())
            break

    theme_window.close()

def enter_resident_info():
    # Fetch list of residents
    resident_names = db_functions.get_resident_names()  # Assume this function returns a list of resident names

    layout = [
        [sg.Text('Select Resident:'), sg.Combo(resident_names, key='-RESIDENT-', readonly=True)],
        [sg.Text('New Name:'), sg.InputText(key='-NEW_NAME-')],
        [sg.Text('New Date of Birth:(YYYY-MM-DD)'), sg.InputText(key='-NEW_DOB-')],
        [sg.Button('Update'), sg.Button('Cancel')]
    ]

    window = sg.Window('Edit Resident Information', layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Update':
            # Fetch current information
            current_info = db_functions.fetch_resident_information(values['-RESIDENT-'])
            if current_info:
                # Update information
                db_functions.update_resident_info(values['-RESIDENT-'], values['-NEW_NAME-'].strip(), values['-NEW_DOB-'].strip())
                sg.popup('Resident information updated')
            else:
                sg.popup('Resident not found')
            break

    window.close()


def display_welcome_window(num_of_residents_local):
    """ Display a welcome window with the number of residents. """
    
    image_path = 'ct-logo.png'
    layout = [
        [sg.Text(f'CareTech Resident Manager', font=(db_functions.get_user_font(), 20),
                 justification='center', pad=(20,20))],
        [sg.Image(image_path)],
        [sg.Text(f'Your Facility Currently has {num_of_residents_local} Resident(s)',
                 font=(FONT, 16), justification='center', pad=(10,10))],
        [sg.Text(text='', expand_x=True), sg.Button('Enter Resident Management', pad=6, font=(FONT, 12)),
          sg.Button("Change Theme", pad=6, font=(FONT, 12)), sg.Text(text='', expand_x=True)],
         [sg.Button('Add Resident', button_color='green', pad=6, font=(FONT, 12)), sg.Button('Remove Resident', button_color='red', pad=6, font=(FONT, 12)), 
          sg.Button('Edit Resident', pad=6, font=(FONT, 12))]
    ]

    window = sg.Window('CareTech Resident Manager', layout, element_justification='c')

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'Add Resident':
            window.close()
            enter_resident_info()
            display_welcome_window(db_functions.get_resident_count())
        elif event == 'Remove Resident':
            window.close()
            enter_resident_removal()
            display_welcome_window(db_functions.get_resident_count())
        elif event == 'Enter Resident Management':
            if db_functions.get_resident_count() == 0:
                sg.popup("Your Facility Has No Residents. Please Select Click Add Resident.", font=(FONT, 12), 
                         title='Error- No Residents')
                continue
            else:
                window.hide()
                resident_management.main()
                window.un_hide()   
        elif event == 'Change Theme':
            window.close()
            change_theme_window()
        elif event == 'Edit Resident':
            window.close()
            enter_resident_info()
            display_welcome_window(db_functions.get_resident_count())

    window.close()
    conn.close()


if __name__ == "__main__":
    display_welcome_window(db_functions.get_resident_count())


