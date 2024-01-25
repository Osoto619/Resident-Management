import PySimpleGUI as sg
import sqlite3
import calendar
import datetime
import db_functions


# Define the width of the label cell and regular cells
label_cell_width = 12  # This may need to be adjusted to align perfectly
regular_cell_width = 5  # This may need to be adjusted to align perfectly

# Define the spacer width to align with the table header
spacer_width = 3  # Adjust as needed

# Define the number of days
num_days = 31


def create_horizontal_bar(text):
    return [sg.Text(f'{text}', justification='center', expand_x=True, relief=sg.RELIEF_SUNKEN)]


def create_row_label(text):
    return [sg.Text(f'{text}', size=(label_cell_width+7, 1), pad=(0,0), justification='center')]


def create_input_text(key):
    return [sg.InputText(size=(regular_cell_width, 1), pad=(3, 3), justification='center', key=f'-{key}-{i}-') for i in range(1, num_days + 1)]


def create_prn_input_text(key):
    return [sg.InputText(size=(regular_cell_width, 1), 
                         pad=(3, 3), 
                         justification='center', 
                         key=f'-{key}-{i}-', 
                         readonly=True, 
                         enable_events=True) for i in range(1, num_days + 1)]


def create_medication_section(medication_name, medication_info):
    section_layout = []
    section_layout.append(create_row_label(medication_name))
    section_layout.append(create_row_label(f"{medication_info['dosage']}"))
    section_layout.append(create_row_label(f"{medication_info['instructions']}"))

    for time_slot in medication_info['time_slots']:
        row = create_row_label(time_slot)  + [sg.Text('      ')] + create_input_text(f"{medication_name}_{time_slot}")
        section_layout.append(row)

    section_layout.append(create_horizontal_bar(''))  # End with a horizontal bar
    return section_layout


def create_prn_medication_section(medication_name, medication_info):
    section_layout = []
    section_layout.append(create_row_label(medication_name))
    section_layout.append(create_row_label(f"{medication_info['dosage']}"))
    section_layout.append(create_row_label(f"{medication_info['instructions']}"))

    # Adding a label to indicate that this is a PRN medication
    # section_layout.append(create_row_label("As Needed (PRN)"))
    row = create_row_label("As Needed (PRN)") + [sg.Text('      ')] + create_prn_input_text(f"PRN_{medication_name}")
    section_layout.append(row)

    section_layout.append(create_horizontal_bar(''))  # End with a horizontal bar
    return section_layout


def create_prn_details_window(event_key, resident_name, year_month):
    prn_data = db_functions.fetch_prn_data_for_day(event_key, resident_name, year_month)
    # print(prn_data) # Debugging
    
    layout = [[sg.Text('', expand_x=True),sg.Text("PRN Details Window", font=(db_functions.get_user_font, 17)), sg.Text("",expand_x=True)]]
    for entry in prn_data:
        date_time = entry[0]
        initials = entry[1]
        notes = entry[2]
        row = [sg.Text(f'Date/Time Administered: {date_time}', font=(db_functions.get_user_font, 14)), sg.Text(f'Administered by: {initials}', font=(db_functions.get_user_font, 14)),
               sg.Text(f"Optional Notes: {notes}", font=(db_functions.get_user_font, 14))]
        layout.append(row)
    layout.append([sg.Text("", expand_x=True), sg.Button("Close", key="-CLOSE-", font=(db_functions.get_user_font, 14)), sg.Text("", expand_x=True)])
    window = sg.Window("PRN Details", layout, modal=True)
    
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "-CLOSE-":
            break
    window.close()


def show_emar_chart(resident_name, year_month):
    # Define the number of days
    num_days = 31

    # Define the width of the label cell and regular cells
    label_cell_width = 22  # This may need to be adjusted to align perfectly
    regular_cell_width = 5  # This may need to be adjusted to align perfectly

    # Empty row for the table to just show headers
    data = [[]]  # No data rows, only headers

    # Parse the year and month
    year, month_number = year_month.split('-')
    month_name = calendar.month_name[int(month_number)]

    # Fetch eMAR data for the month
    emar_data = db_functions.fetch_emar_data_for_month(resident_name, year_month)

    original_structure = db_functions.fetch_medications_for_resident(resident_name)
    
    # Process Scheduled Medications
    new_structure = {}
    for time_slot, medications in original_structure['Scheduled'].items():
        for medication_name, details in medications.items():
            if medication_name not in new_structure:
                new_structure[medication_name] = {
                    'dosage': details['dosage'], 
                    'instructions': details['instructions'],
                    'time_slots': [time_slot],
                    'type': 'Scheduled'
            }
            else:
                new_structure[medication_name]['time_slots'].append(time_slot)
    
    # Process PRN Medications
    prn_structure = {}
    for medication_name, details in original_structure['PRN'].items():
        prn_structure[medication_name] = {
            'dosage': details['dosage'],
            'instructions': details['instructions'],
            'type': 'PRN'
    }


    # Medication layout
    medication_layout = []
    for med_name, med_info in new_structure.items():
        medication_layout.extend(create_medication_section(med_name, med_info))
    for med_name, med_info in prn_structure.items():
        medication_layout.extend(create_prn_medication_section(med_name, med_info))

    # Define the layout of the window
    layout = [
        [sg.Text('CareTech Monthly eMAR Chart', font=('Helvetica', 16), justification='center', expand_x=True)],
        [sg.Text('RESIDENT:', size=(10, 1)), sg.Text(f'{resident_name}', key='-RESIDENT-', size=(20, 1)),
        sg.Text('MONTH:', size=(10, 1)), sg.Text(f'{month_name} {year}', key='-MONTH-', size=(20, 1))],
        # Table as a header row of cells
        [sg.Table(values=data,
              headings=[''] + [str(i) for i in range(1, num_days + 1)],
              max_col_width=regular_cell_width,
              auto_size_columns=False,
              col_widths=[label_cell_width] + [regular_cell_width]*num_days,
              display_row_numbers=False,
              justification='center',
              num_rows=0,
              key='-TABLE-',
              row_height=25,
              pad=(0,0),
              hide_vertical_scroll=True)],
        create_horizontal_bar(text=''),
        [sg.Column(medication_layout, scrollable=True, vertical_scroll_only=True, size=(1600, 750))]
    ]

    instruction_text = (
    "Instructions for Viewing PRN Medication Details:\n"
    "1. Select the PRN Medication Day: Click on the input box for the day you wish to view.\n"
    "2. Press Any Alphanumeric Key (A-Z or 0-9) to view the detailed administration records for that day."
    )
    layout.append([sg.Text(instruction_text, key='-INSTRUCTIONS-', font=(db_functions.get_user_font, 11))])
    layout.append([sg.Button('Save Changes Made'), sg.Button('Hide Buttons/Instructions')])
    # Create the window
    window = sg.Window(' CareTech Monthly eMARS', layout, finalize=True, resizable=True)

    # Convert the eMAR data into a more convenient structure
    emar_data_dict = {}
    for med_name, date, time_slot, administered in emar_data:
        if med_name not in emar_data_dict:
            emar_data_dict[med_name] = {}
        if date not in emar_data_dict[med_name]:
            emar_data_dict[med_name][date] = {}
        emar_data_dict[med_name][date][time_slot] = administered

    # print(original_structure)
    
    # print(prn_structure)
    
    # print(new_structure)

    # print(emar_data_dict)

    # If data is found, update the layout fields accordingly
    for med_name, med_info in new_structure.items():
        if med_info['type'] == 'Scheduled':
            # Handle scheduled medications
            for date, slots in emar_data_dict.get(med_name, {}).items():
                day = int(date.split('-')[2])  # Extract the day from 'YYYY-MM-DD'
                for time_slot, administered in slots.items():
                    key = f'-{med_name}_{time_slot}-{day}-'
                    if window[key]:
                        window[key].update(administered)

        # Update layout for PRN medications
    for med_name in prn_structure.keys():
        for datetime_string, slots in emar_data_dict.get(med_name, {}).items():
            # Split the date and time, and then extract the day
            date_part = datetime_string.split()[0]  # Get the 'YYYY-MM-DD' part
            day = int(date_part.split('-')[2])  # Extract the day

            prn_key = f'-PRN_{med_name}-{day}-'
            # Check if there is any administration data for the day
            if any(slots.values()):
                administered_text = 'ADM'  # Indicating at least one administration
                administered_color = 'lightgreen'
                if window[prn_key]:
                    window[prn_key].update(administered_text, background_color='yellow')
                    
    # Event Loop
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'Hide Buttons/Instructions':
            window['Save Changes Made'].update(visible=False)
            window['Hide Buttons/Instructions'].update(visible=False)
            window['-INSTRUCTIONS-'].update(visible=False)
        elif event == 'Save Changes Made':
            db_functions.save_emar_data_from_chart_window(resident_name,year_month,values)
            sg.popup("Changes Have Been Saved")
        elif event.startswith('-PRN'):
            print(event) # Debugging
            # print(year_month) 
            create_prn_details_window(event, resident_name, year_month)

    window.close()


if __name__ == "__main__":
    show_emar_chart("Snoop Dawg", "2023-12")