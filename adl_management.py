import PySimpleGUI as sg
from datetime import datetime
import time
import sqlite3
from adl_chart import show_adl_chart
import welcome_screen
import db_functions


def get_resident_self_care_status():
    with sqlite3.connect('resident_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name, self_care FROM residents')
        return {name: self_care for name, self_care in cursor.fetchall()}


def get_adl_tab_layout(resident_name):
    existing_data = db_functions.fetch_adl_data_for_resident(resident_name)
    resident_self_care_status = get_resident_self_care_status()
    is_self_care = resident_self_care_status.get(resident_name, False)

    # Fields to auto-populate for self-care residents
    auto_self_fields = [
        'first_shift_bm', 'second_shift_bm', 'shower', 'shampoo',
        'sponge_bath', 'peri_care_am', 'peri_care_pm', 'oral_care_am',
        'oral_care_pm', 'nail_care', 'skin_care', 'shave']

    # Build the default texts for input fields
    input_fields_defaults = {field: existing_data.get(field, '') for field in auto_self_fields}

    # Auto-populate 'Self' for self-care residents in the existing fields
    if is_self_care:
        for field in auto_self_fields:
            input_fields_defaults[field] = 'Self'

    tab_layout = [
            [sg.Text(f'Service Plan Followed (Initials)')],
            [sg.Text('1st Shift Service Plan'), sg.InputText(size=4, default_text=existing_data.get('first_shift_sp', ''), key=f'{resident_name}_first_shift_sp'),
             sg.Text('2nd Shift Service Plan'), sg.InputText(size=4, default_text=existing_data.get('second_shift_sp'), key=f'{resident_name}_second_shift_sp')],
            [sg.Text("Activities (Use Activities Legend Below)")],
            [sg.Text('1st Shift 1st Activity'), sg.InputText(size=4, default_text=existing_data.get('first_shift_activity1', ''), key=f'{resident_name}_first_shift_activity1'),
             sg.Text("1st Shift 2nd Activity"), sg.InputText(size=4, default_text=existing_data.get('first_shift_activity2', ''), key=f'{resident_name}_first_shift_activity2')],
            [sg.Text('1st Shift 3rd Activity'), sg.InputText(size=4, default_text=existing_data.get('first_shift_activity3', ''), key=f'{resident_name}_first_shift_activity3'),
             sg.Text("2nd Shift 4th Activity"), sg.InputText(size=4, default_text=existing_data.get('second_shift_activity4', ''), key=f'{resident_name}_second_shift_activity4')],
            [sg.Text('1st Shift Bowel Movement'), sg.InputText(size=4, default_text=input_fields_defaults['first_shift_bm'], key=f'{resident_name}_first_shift_bm'),
             sg.Text('2nd Shift Bowel Movement'), sg.InputText(size=4, default_text=input_fields_defaults['second_shift_bm'], key=f'{resident_name}_second_shift_bm')],
            [sg.Text("ADL's (initial when complete)")],
            [sg.Text('Shower'), sg.InputText(size=4, default_text=input_fields_defaults['shower'], key=f'{resident_name}_shower'),
             sg.Text('Shampoo'), sg.InputText(size=4, default_text=input_fields_defaults['shampoo'], key=f'{resident_name}_shampoo'),
             sg.Text('Sponge Bath'), sg.InputText(size=4, default_text=input_fields_defaults['sponge_bath'], key=f'{resident_name}_sponge_bath'),
             sg.Text('Peri Care AM'), sg.InputText(size=4, default_text=input_fields_defaults['peri_care_am'], key=f'{resident_name}_peri_care_am'),
             sg.Text('Peri Care PM'), sg.InputText(size=4, default_text=input_fields_defaults['peri_care_pm'], key=f'{resident_name}_peri_care_pm')],
            [sg.Text('Oral Care AM'), sg.InputText(size=4, default_text=input_fields_defaults['oral_care_am'], key=f'{resident_name}_oral_care_am'),
             sg.Text('Oral Care PM'), sg.InputText(size=4, default_text=input_fields_defaults['oral_care_pm'], key=f'{resident_name}_oral_care_pm'),
             sg.Text('Nail Care'), sg.InputText(size=4, default_text=input_fields_defaults['nail_care'], key=f'{resident_name}_nail_care'),
             sg.Text('Skin Care'), sg.InputText(size=4, default_text=input_fields_defaults['skin_care'], key=f'{resident_name}_skin_care'),
             sg.Text('Shave'), sg.InputText(size=4, default_text=input_fields_defaults['shave'], key=f'{resident_name}_shave')],
            [sg.Text('Meals (Record Percentage of Meal Eaten)')],
            [sg.Text('Breakfast'), sg.InputText(size=4, default_text=existing_data.get('breakfast', ''), key=f'{resident_name}_breakfast'),
             sg.Text('Lunch'), sg.InputText(size=4, default_text=existing_data.get('lunch', ''), key=f'{resident_name}_lunch'),
             sg.Text('Dinner'), sg.InputText(size=4, default_text=existing_data.get('dinner', ''), key=f'{resident_name}_dinner'),
             sg.Text('Snack AM'), sg.InputText(size=4, default_text=existing_data.get('snack_am', ''), key=f'{resident_name}_snack_am'),
             sg.Text('Snack PM'), sg.InputText(size=4, default_text=existing_data.get('snack_pm', ''), key=f'{resident_name}_snack_pm'),
             sg.Text('Water In-Take'), sg.InputText(size=4, default_text=existing_data.get('water_intake', ''), key=f'{resident_name}_water_intake')],
             [sg.Text('', expand_x=True), sg.Button('Save', key=('-ADL_SAVE-')), sg.Button('View/Edit Current Month ADL Chart', key=('-CURRENT_ADL_CHART-')),
             sg.Text('', expand_x=True)], [sg.Text('', expand_x=True), sg.Text('Or Search by Month and Year'), sg.Text('',expand_x=True)], 
             [sg.Text(text="", expand_x=True),sg.Text(text="Enter Month: (MM)"), sg.InputText(size=4, key="-ADL_MONTH-") , sg.Text("Enter Year: (YYYY)"), sg.InputText(size=5, key='-ADL_YEAR-'), 
             sg.Button("Search", key='-ADL_SEARCH-'), sg.Text(text="", expand_x=True)]
        ]
    
    # Create the activities frame
    activities_frame = create_activities_frame()

    # Append the activities frame to the tab layout
    tab_layout.append([sg.Text(text='', expand_x=True), activities_frame, sg.Text(text='', expand_x=True)])

    # Create a scrollable container for the layout
    scrollable_layout = sg.Column(tab_layout, size=(680,600)) # Adjust the size as needed


    # return tab_layout
    # Return the layout wrapped in a scrollable container
    return [[scrollable_layout]]


def create_activities_frame():
    # Define activities
    activities = [
        "1. Movie & Snack or TV",
        "2. Exercise/Walking",
        "3. Games/Puzzles",
        "4. Outside/Patio",
        "5. Arts & Crafts",
        "6. Music Therapy",
        "7. Gardening",
        "8. Listen to Music",
        "9. Social Hour",
        "10. Cooking/Baking",
        "11. Birdwatching",
        "12. Outing/Excursion",
        "13. Hospice Visit",
        "14. Other as Listed on the Service Plan",
        "15. Social Media"
        ]

    # Divide activities into three columns
    column1 = [[sg.Text(activities[i])] for i in range(0, len(activities), 3)]
    column2 = [[sg.Text(activities[i])] for i in range(1, len(activities), 3)]
    column3 = [[sg.Text(activities[i])] for i in range(2, len(activities), 3)]
    # Create a frame with three columns
    return sg.Frame('Activities', layout=[
        [sg.Column(column1), sg.Column(column2), sg.Column(column3)]
    ], relief=sg.RELIEF_SUNKEN)


def update_clock(window):
    current_time = datetime.now().strftime("%H:%M:%S")  # Get current time
    window['-TIME-'].update(current_time)


def retrieve_adl_data_from_window(window, resident_name):
    # Define the keys as they appear in the window and database
    adl_keys = [
        'first_shift_sp', 'second_shift_sp', 'first_shift_activity1',
        'first_shift_activity2', 'first_shift_activity3',
        'second_shift_activity4',
        'first_shift_bm', 'second_shift_bm', 'shower', 'shampoo',
        'sponge_bath', 'peri_care_am', 'peri_care_pm', 'oral_care_am',
        'oral_care_pm', 'nail_care', 'skin_care', 'shave', 'breakfast',
        'lunch', 'dinner', 'snack_am', 'snack_pm', 'water_intake'
    ]

    # Initialize a dictionary to store the ADL data
    adl_data = {}

    # Get the current values from the window for the specified resident
    values = window.read(timeout=10)[
        1]  # We use a timeout to read from the window non-blocking

    # Extract the data using the keys
    for key in adl_keys:
        # The keys in the window are prefixed with the resident's name
        window_key = f'{resident_name}_{key}'
        adl_data[key] = values.get(window_key,'')  # Use .get() to handle missing keys

    return adl_data


def create_adl_management_window():
    resident_names_local = db_functions.get_resident_names()
    resident_self_care_status = get_resident_self_care_status()


    # Create tabs for each resident
    resident_tabs = []
    for name in resident_names_local:
        tab_layout = get_adl_tab_layout(name)
        resident_tabs.append(sg.Tab(name, tab_layout, key=f"TAB_{name}"))

    # Create the tab group
    tab_group = sg.TabGroup([resident_tabs], tab_location='top', key='-TABGROUP-')

    current_date = datetime.now().strftime("%m-%d-%y")  # Get today's date

    # Layout for the ADL Management window
    layout = [
        [sg.Text('CareTech ADL Management', font=('Helvetica', 16), justification='center', expand_x=True)],
        [sg.Text(text='', expand_x=True),sg.Text(current_date, key='-DATE-', font=('Helvetica', 12)), sg.Text('', key='-TIME-', font=('Helvetica', 12)), sg.Text(text='', expand_x=True)],
        [tab_group],
        [sg.Text(text='', expand_x=True), sg.Button('Previous'), sg.Button('Next'),
        sg.Text(text='', expand_x=True)],
    ]

    # Create and event loop for the window
    window = sg.Window('ADL Management', layout)

    # Event loop
    while True:
        event, values = window.read(timeout=1000)
        if event in (None, 'Exit', sg.WIN_CLOSED):
            window.close()
            welcome_screen.display_welcome_window(welcome_screen.get_resident_count())
            break
        elif event == 'Next':
            # Get the key of the currently selected tab
            selected_tab_key = values['-TABGROUP-']
            if selected_tab_key == None:
                continue
            # Extract the resident name from the selected tab key
            selected_resident = selected_tab_key.split('_')[1]
            # Get the index of the currently selected resident
            selected_tab_index = resident_names_local.index(selected_resident)
            # Calculate the new tab index for the next tab
            new_tab_index = (selected_tab_index + 1) % len(
                resident_names_local)
            # Set the new tab as visible
            window['-TABGROUP-'].Widget.select(new_tab_index)
        elif event == 'Previous':
            # Get the key of the currently selected tab
            selected_tab_key = values['-TABGROUP-']
            # Extract the resident name from the selected tab key
            if selected_tab_key == None:
                continue
            selected_resident = selected_tab_key.split('_')[1]
            # Get the index of the currently selected resident
            selected_tab_index = resident_names_local.index(selected_resident)
            # Calculate the new tab index for the previous tab
            new_tab_index = (selected_tab_index - 1) % len(
                resident_names_local)
            # Set the new tab as visible
            window['-TABGROUP-'].Widget.select(new_tab_index)
        elif event == '-ADL_SAVE-':
            # Get the name of the selected tab which corresponds to the selected resident
            selected_tab_key = values['-TABGROUP-']  # Use the key you've assigned to the TabGroup when creating it
            if selected_tab_key == None:
                continue
            selected_resident = selected_tab_key.split('_')[1]  # Assuming key format is "TAB_residentname"
            adl_data = retrieve_adl_data_from_window(window, selected_resident)
            # For Testing
            # print("ADL Data to be saved:", adl_data)
            db_functions.save_adl_data_from_management_window(selected_resident, adl_data)
            sg.popup("Data saved successfully!")
        elif event == "-CURRENT_CHART-":
            # Get the name of the selected resident
            selected_tab_key = values['-TABGROUP-']
            if selected_tab_key == None:
                continue
            selected_resident = selected_tab_key.split('_')[1]

            # Get the current month and year
            current_month_year = datetime.now().strftime("%Y-%m")

            # Call the show_adl_chart function with the selected resident and current month-year
            show_adl_chart(selected_resident, current_month_year)
        elif event == "-ADL_SEARCH-":
            # year_month should be in the format 'YYYY-MM'
            month = values['-ADL_MONTH-'].zfill(2)
            year = values['-ADL_YEAR-']
            month_year = f'{year}-{month}'
            print(month_year)
            selected_tab_key = values['-TABGROUP-']
            if selected_tab_key == None:
                continue
            selected_resident = selected_tab_key.split('_')[1]
            if db_functions.does_adl_chart_data_exist(selected_resident, month_year):
                show_adl_chart(selected_resident, month_year)
            else:
                sg.popup("No ADL Chart Data Found for the Specified Month and Resident")

        update_clock(window)

    window.close()


# Example usage from main.py:
if __name__ == "__main__":
    create_adl_management_window()
