import PySimpleGUI as sg
import resident_management
import db_functions
import os
import shutil
from datetime import datetime, timedelta, date
from tkinter import font
import sys
import database_setup
import config
import secrets
import string
import pyperclip

database_setup.initialize_database()

# Function to load and apply the user's theme
def apply_user_theme():
    user_theme = db_functions.get_user_theme()
    sg.theme(user_theme)


# Apply user theme at application startup
apply_user_theme()

FONT = db_functions.get_user_font()
FONT_BOLD = 'Arial Bold'

def backup_configuration_window():
    layout = [
        [sg.Text("Backup Folder:"), sg.InputText(key='BackupFolder'), sg.FolderBrowse()],
        [sg.Text("Backup Frequency:"), sg.Combo(['Daily', 'Weekly'], default_value='Weekly', key='BackupFrequency')],
        [sg.Text("It's highly recommended to choose a backup location that is external to your computer, such as a cloud storage service or an external hard drive. This ensures that your data remains safe even in the event of hardware failure, theft, or other physical damages to your computer.", size=(60, 4))],
        [sg.Button("Save"), sg.Button("Cancel")]
    ]
    
    window = sg.Window("Backup Configuration", layout)
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == "Cancel":
            break
        elif event == "Save":
            
            db_functions.save_backup_configuration(values['BackupFolder'], values['BackupFrequency'])
            sg.popup("Configuration Saved. Automatic backups will be performed accordingly.")
            break

    window.close()

def is_backup_due():
    backup_config = db_functions.get_backup_configuration()
    if not backup_config:
        return False

    last_backup_date = backup_config['last_backup_date']
    today = datetime.now().date()

    if backup_config['backup_frequency'] == 'Daily' and (today - last_backup_date).days >= 1:
        return True
    elif backup_config['backup_frequency'] == 'Weekly' and (today - last_backup_date).days >= 7:
        return True

    return False


def perform_backup():
    # Retrieve backup configuration
    backup_config = db_functions.get_backup_configuration()
    if not backup_config:
        print("Backup configuration not found.")
        return
    
    backup_folder = backup_config['backup_folder']
    database_path = 'resident_data.db'  # Path to your SQLite database
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{current_time}.db"
    
    # Construct the full path for the backup file
    backup_path = os.path.join(backup_folder, backup_filename)
    
    try:
        # Copy the database file to the backup folder
        shutil.copyfile(database_path, backup_path)
        print(f"Backup successful: {backup_path}")
    except Exception as e:
        print(f"Error during backup: {e}")

def startup_routine():
    if is_backup_due():
        perform_backup()
        db_functions.update_last_backup_date()
    #     print("Backup performed successfully.")
    # else:
    #     print("No backup needed at this time.")


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
            logged_in_user = config.global_config['logged_in_user']
            db_functions.log_action(logged_in_user, 'Resident Added', f'Resident Added {name}')
            sg.popup('Resident information saved!')
            window.close()
            return True

    window.close()
    

def enter_resident_removal():
    # Fetch the list of residents for the dropdown
    residents = db_functions.fetch_residents()

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
            resident_name = values['-RESIDENT-']
            if current_info:
                # Update information
                db_functions.update_resident_info(values['-RESIDENT-'], values['-NEW_NAME-'].strip(), values['-NEW_DOB-'].strip())
                db_functions.log_action(config.global_config['logged_in_user'], 'Fixed Resident Typo(s)', f'fixed typos for {resident_name}')
                sg.popup('Resident information updated')
            else:
                sg.popup('Resident not found')
            break

    window.close()


def create_initial_admin_account_window():

    layout = [
        [sg.Text('', expand_x=True), sg.Text("Welcome to CareTech Resident Management", font=(db_functions.get_user_font(), 18)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text("Please set up the Administrator account", font=(db_functions.get_user_font(), 16)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text("Username:", font=(db_functions.get_user_font(), 14)), sg.InputText(key='username', size=16, font=(db_functions.get_user_font(), 14)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text("Password:", font=(db_functions.get_user_font(), 16)), sg.InputText(key='password', password_char='*', size=16, font=(db_functions.get_user_font(), 14)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text("Initials:", font=(db_functions.get_user_font(), 16)), sg.InputText(key='initials', size=4, font=(db_functions.get_user_font(), 14)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Button("Create Admin Account", font=(db_functions.get_user_font(), 12)), sg.Button("Exit", font=(db_functions.get_user_font(), 12)), sg.Text('', expand_x=True)]
    ]

    window = sg.Window("Admin Account Setup", layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            sys.exit(0)
        elif event == "Create Admin Account":
            username = values['username']
            password = values['password']
            initials = values['initials'].strip().upper()
            if not username or not password:
                sg.popup("Username and password are required.", title="Error")
                continue

            # No longer need to collect db_passphrase as it's automatically set
            try:
                # The initial database setup with passphrase should be done here
                db_functions.create_admin_account(username, password, initials)
                sg.popup("Admin account created successfully. Please ensure the passphrase is securely stored and set as an environment variable.", title="Success")
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

def remove_user_window():
    # Fetch usernames for the dropdown
    usernames = db_functions.get_all_usernames()

    layout = [
        [sg.Text("Select User:"), sg.Combo(usernames, key='-USERNAME-')],
        [sg.Text("Reason for Removal:"), sg.InputText(key='-REASON-')],
        [sg.Button("Remove User"), sg.Button("Cancel")]
    ]

    window = sg.Window("Remove User", layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Remove User":
            username = values['-USERNAME-']
            reason = values['-REASON-'].strip()

            if not username or not reason:
                sg.popup_error("Both username and reason for removal are required.")
                continue
            
            # Confirmation popup
            confirm = sg.popup_yes_no(f"Are you sure you want to remove '{username}'?", title="Confirm Removal")
            if confirm == "Yes":
                try:
                    db_functions.remove_user(username) 
                    db_functions.log_action(config.global_config['logged_in_user'], 'User Removal', f"User '{username}' removed. Reason: {reason}")
                    sg.popup(f"User '{username}' has been removed successfully.")
                    break
                except Exception as e:
                    sg.popup_error(f"Error removing user: {e}")
            else:
                sg.popup("User removal cancelled.")

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
                db_functions.log_action(username, "Login", f"{username}")
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
    
def audit_logs_window():
    col_widths = [20, 15, 30, 65]  # Adjusted for readability
    # Define the layout for the audit logs window
    layout = [
        [sg.Text('', expand_x=True), sg.Text('Admin Audit Logs', font=(db_functions.get_user_font(), 23)), sg.Text('', expand_x=True)],
        [sg.Text("Filter by Username:"), sg.InputText(key='-USERNAME_FILTER-', size=14)],
        [sg.Text("Filter by Action:"), sg.Combo(['Login', 'Logout', 'Resident Added', 'User Created', 'New Medication', 'Add Non-Medication Order', 'Non-Medication Order Administered'], key='-ACTION_FILTER-', readonly=True)],
        [sg.Text("Filter by Date (YYYY-MM-DD):"), sg.InputText(key='-DATE_FILTER-', enable_events=True, size=10), sg.CalendarButton("Choose Date", target='-DATE_FILTER-', close_when_date_chosen=True, format='%Y-%m-%d')],
        [sg.Button("Apply Filters"), sg.Button("Reset Filters")],
        [sg.Table(headings=['Date', 'Username', 'Action', 'Description'], values=[], key='-AUDIT_LOGS_TABLE-', auto_size_columns=False, display_row_numbers=True, num_rows=20, col_widths=col_widths, enable_click_events=True, select_mode=sg.TABLE_SELECT_MODE_BROWSE)],
        [sg.Button("Close")]
    ]

    window = sg.Window("Audit Logs", layout, finalize=True)

    # Function to load audit logs
    def load_audit_logs(username_filter='', action_filter='', date_filter=''):
        logs = db_functions.fetch_audit_logs(last_10_days=True, username=username_filter, action=action_filter, date=date_filter)
        table_data = [[log['date'], log['username'], log['action'], log['description']] for log in logs]
        window['-AUDIT_LOGS_TABLE-'].update(values=[[log['date'], log['username'], log['action'], log['description']] for log in logs])
        return table_data

    original_table_data = load_audit_logs()  # Initial loading of logs

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == "Close":
            break
        elif event[0] == '-AUDIT_LOGS_TABLE-' and event[1] == '+CLICKED+':
            row_index = event[2][0]  # Get the row index from the event tuple.
            # Access the clicked row's data using the row_index from your original dataset.
            clicked_row_data = original_table_data[row_index]
            description = clicked_row_data[3]  # Assuming the description is in the fourth column.
            sg.popup_scrolled(description, title='Detailed Description', size=(50, 10))
        elif event == "Apply Filters":
            original_table_data = load_audit_logs(username_filter=values['-USERNAME_FILTER-'], action_filter=values['-ACTION_FILTER-'], date_filter=values['-DATE_FILTER-'])
        elif event == "Reset Filters":
            window['-USERNAME_FILTER-'].update('')
            window['-ACTION_FILTER-'].update('')
            window['-DATE_FILTER-'].update('')
            original_table_data = load_audit_logs()  # Reload logs without filters

    window.close()


def display_welcome_window(num_of_residents_local, show_login=False):
    
    if db_functions.is_first_time_setup():
        create_initial_admin_account_window()
        

    if show_login:
        login_window()

    logged_in_user = config.global_config['logged_in_user']    

    """ Display a welcome window with the number of residents. """
    image_path = 'ct-logo.png'

    # Define the admin panel frame
    admin_panel_layout = [
        [sg.Button('Add Resident', pad=(6, 3), font=(FONT, 12)),
        sg.Button('Remove Resident', pad=(6, 3), font=(FONT, 12)),
        sg.Button('Edit Resident', pad=(6, 3), font=(FONT, 12))],
        [sg.Text('', expand_x=True), sg.Button('Add User', pad=(6, 3), font=(FONT, 12)),
        sg.Button('Remove User', pad=(6, 3), font=(FONT, 12)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Button('View Audit Logs', font=(FONT, 12)), sg.Button('Data Backup Setup', font=(FONT, 12 )), sg.Text('', expand_x=True)]
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
        elif event == 'Remove User':
            window.hide
            remove_user_window()
            window.un_hide()
        elif event == 'View Audit Logs':
            window.hide()
            audit_logs_window()
            window.un_hide()
        elif event == 'Data Backup Setup':
            window.hide()
            backup_configuration_window()
            startup_routine()
            window.un_hide()
            
    db_functions.log_action(logged_in_user, 'Logout', f'{logged_in_user} logout')
    config.global_config['logged_in_user'] = None
    window.close()

if __name__ == "__main__":
    startup_routine()
    display_welcome_window(db_functions.get_resident_count(), show_login=True)
