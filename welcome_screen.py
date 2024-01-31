import sqlite3
import PySimpleGUI as sg
import resident_management
import db_functions
from datetime import datetime, timedelta
from tkinter import font
import sys
import database_setup
import config

database_setup.initialize_database()
logged_in_user = config.global_config['logged_in_user']

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
            name = values['Name'].title()
             # Determine the selected level of care
            level_of_care = 'Supervisory Care' if values['Supervisory_Care'] else 'Personal Care' if values['Personal_Care'] else 'Directed Care'
            db_functions.insert_resident(name, values['Date_of_Birth'], level_of_care)
            db_functions.log_action(logged_in_user, 'Resident aded', f'Resident Added {name} by {logged_in_user}')
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
    # Exclusion List
    ]

    font_options = [f for f in font.families() if f not in symbol_fonts]
    
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
            break

    theme_window.close()


def enter_resident_edit():
    # Fetch list of residents
    resident_names = db_functions.get_resident_names()

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


def create_initial_admin_account_window():
    layout = [
    [sg.Text('', expand_x=True), sg.Text("Welcome to CareTech Resident Management", font=(db_functions.get_user_font(), 18)), sg.Text('', expand_x=True)],
    [sg.Text("Please Set up Administrator Account", font=(db_functions.get_user_font(), 16))],
    [sg.Text("Username:", font=(db_functions.get_user_font(), 14)), sg.InputText(key='username',size=16, font=(db_functions.get_user_font(), 14))],
    [sg.Text("Password:", font=(db_functions.get_user_font(), 16)), sg.InputText(key='password', password_char='*', size=16, font=(db_functions.get_user_font(), 14))],
    [sg.Text("Initials:", font=(db_functions.get_user_font(), 16)), sg.InputText(key='initials', size=4, font=(db_functions.get_user_font(), 14))],
    [sg.Button("Create Admin Account", font=(db_functions.get_user_font(),12)), sg.Button("Exit", font=(db_functions.get_user_font(),12))]
]

    window = sg.Window("Admin Account Setup", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            sys.exit(0)
        elif event == "Create Admin Account":
            username = values['username']
            password = values['password']
            initials = values['initials'].strip().upper()
            # Validate input (e.g., non-empty, password strength, etc.)
            if not username or not password:
                sg.popup("Username and password are required.", title="Error")
                continue
            # Create the admin account
            try:
                db_functions.create_admin_account(username, password, initials)
                db_functions.log_action(username,'Initial Admin Creation', f'First Admin: {username}')
                sg.popup("Admin account created successfully.")
                break
            except Exception as e:
                sg.popup(f"Error creating admin account: {e}", title="Error")

    window.close()


def new_user_setup_window(username):
    layout = [
        [sg.Text(f"Welcome {username}, please set your new password and initials.")],
        [sg.Text("New Password:"), sg.InputText(key='new_password', password_char='*')],
        [sg.Text("Initials:"), sg.InputText(key='initials')],
        [sg.Button("Set Password and Initials"), sg.Button("Cancel")]
    ]

    window = sg.Window("Password Reset", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            break
        elif event == "Set Password and Initials":
            new_password = values['new_password']
            initials = values['initials'].strip().upper()

            # Validate new password and initials
            if new_password and initials:
                db_functions.update_user_password_and_initials(username, new_password, initials)
                sg.popup("Password and initials updated successfully.")
                break
            else:
                sg.popup("Please enter a new password and initials.", title="Error")

    window.close()


def add_user_window():
    logged_in_user = config.global_config['logged_in_user']
    layout = [
        [sg.Text("Add New User")],
        [sg.Text("Username:"), sg.InputText(key='username')],
        [sg.Text("Temporary Password:"), sg.InputText(key='temp_password', password_char='*')],
        [sg.Text("Role:"), sg.Combo(['User', 'Admin'], default_value='User', key='role', readonly=True)],
        [sg.Button("Add User"), sg.Button("Cancel")]
    ]

    window = sg.Window("Add User", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            break
        elif event == "Add User":
            username = values['username']
            temp_password = values['temp_password']
            role = values['role']

            # Validate input (e.g., non-empty, username uniqueness, etc.)
            if not username or not temp_password:
                sg.popup("Both username and temporary password are required.", title="Error")
                continue

            # Check for username uniqueness
            if db_functions.is_username_exists(username):
                sg.popup("This username already exists. Please choose another.", title="Error")
                continue

            # Add the new user
            try:
                db_functions.create_user(username, temp_password, role, True)  # True for is_temp_password
                db_functions.log_action(logged_in_user, 'User Created', f'new user: {username} created by: {logged_in_user}')
                sg.popup("User added successfully.")
                break
            except Exception as e:
                sg.popup(f"Error adding user: {e}", title="Error")

    window.close()


def login_window():
    
    layout = [
        [sg.Text("CareTech Resident Manager", font=(db_functions.get_user_font(), 15))],
        [sg.Text("Username:", font=(db_functions.get_user_font(), 15)), sg.InputText(key='username', size=14, font=(db_functions.get_user_font(),15))],
        [sg.Text("Password:", font=(db_functions.get_user_font(),15)), sg.InputText(key='password', password_char='*', size=14, font=(db_functions.get_user_font(),15))],
        [sg.Button("Login",size=14, font=(db_functions.get_user_font(),12)), sg.Button("Exit", size=14, font=(db_functions.get_user_font(),12))]
    ]
 
    window = sg.Window("Login", layout)


    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            sys.exit(0)
        elif event == "Login":
            username = values['username']
            password = values['password']
            
            # Validate login credentials
            if db_functions.validate_login(username, password):
                # Log the successful login action
                config.global_config['logged_in_user'] = username
                db_functions.log_action(username, "Login", f"{username} login")
                if db_functions.needs_password_reset(username):
                    window.close()
                    new_user_setup_window(username)
                    display_welcome_window(db_functions.get_resident_count(),show_login=False)

                    
                else:
                    # Proceed to main application
                    sg.popup("Login Successful!", title="Success")
                    break
            else:
                sg.popup("Invalid username or password.", title="Error")

    window.close()
    


def display_welcome_window(num_of_residents_local, show_login=False):
    
    login_window()

    if show_login and not config.global_config['logged_in_user']:
        if db_functions.is_first_time_setup():
            create_initial_admin_account_window()
            

    """ Display a welcome window with the number of residents. """
    image_path = 'ct-logo.png'

    # Define the admin panel frame
    admin_panel_layout = [
        [sg.Button('Add Resident', pad=(6, 3), font=(FONT, 12)),
        sg.Button('Remove Resident', pad=(6, 3), font=(FONT, 12)),
        sg.Button('Edit Resident', pad=(6, 3), font=(FONT, 12))],
        [sg.Text('', expand_x=True), sg.Button('Add User', pad=(6, 3), font=(FONT, 12)),
        sg.Button('Remove User', pad=(6, 3), font=(FONT, 12)), sg.Text('', expand_x=True)]
    ]
    admin_panel = sg.Frame('Admin Panel', admin_panel_layout, font=(FONT, 14), visible=db_functions.is_admin(config.global_config['logged_in_user']))

    layout = [
        [sg.Text(f'CareTech Resident Manager', font=(db_functions.get_user_font(), 20),
                 justification='center', pad=(20,20))],
        [sg.Image(image_path)],
        [sg.Text(f'Your Facility Currently has {num_of_residents_local} Resident(s)',
                 font=(FONT, 16), justification='center', pad=(10,10))],
        [sg.Text(text='', expand_x=True), sg.Button('Enter Resident Management', pad=6, font=(FONT, 12)),
          sg.Button("Change Theme", pad=6, font=(FONT, 12)), sg.Text(text='', expand_x=True)],
          [admin_panel]
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
            display_welcome_window(db_functions.get_resident_count())
        elif event == 'Edit Resident':
            window.close()
            enter_resident_edit()
            display_welcome_window(db_functions.get_resident_count())
        elif event == 'Add User':
            window.close()
            add_user_window()
            display_welcome_window(db_functions.get_resident_count())

    window.close()


if __name__ == "__main__":
    display_welcome_window(db_functions.get_resident_count(), show_login=True)


