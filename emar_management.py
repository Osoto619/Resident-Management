import PySimpleGUI as sg
import db_functions
from datetime import datetime
import welcome_screen
import config
from datetime import datetime


def add_medication_window(resident_name):
    medication_type_options = ['Scheduled', 'As Needed (PRN)', 'Controlled']
    measurement_unit_options = ['Pills', 'mL', 'L', 'oz']  # Measurement units for liquids

    layout = [
        [sg.Text('Medication Type', size=(18, 1)), sg.Combo(medication_type_options, default_value='Scheduled', key='Medication Type', readonly=True, enable_events=True)],
        [sg.Text('Medication Name', size=(18, 1)), sg.InputText(key='Medication Name')],
        [sg.Text('Dosage', size=(18, 1)), sg.InputText(key='Dosage')],
        [sg.Text('Instructions', size=(18, 1)), sg.InputText(key='Instructions')],
        [sg.Text('(Instructions Required For PRN and Controlled Medication)')],
        [sg.Frame('Time Slots (Select All That Apply)', [[sg.Checkbox(slot, key=f'TIME_SLOT_{slot}') for slot in ['Morning', 'Noon', 'Evening', 'Night']]], key='Time Slots Frame', visible=True)],
        [sg.Text('Count', size=(6, 1), key=('Count Text'), visible=False), sg.InputText(key='Count', enable_events=True, visible=False, size=6), sg.Combo(measurement_unit_options, default_value='Pills', key='Measurement Unit', visible=False)],
        [sg.Submit(), sg.Cancel()]
    ]

    window = sg.Window('Add Medication', layout)

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Medication Type':
             medication_type = values['Medication Type']

             if medication_type == 'Controlled':
                window['Time Slots Frame'].update(visible=False)
                window['Count Text'].update(visible=True)
                window['Count'].update(visible=True)
                window['Measurement Unit'].update(visible=True)
             elif medication_type == 'As Needed (PRN)':
                window['Time Slots Frame'].update(visible=False)
                window['Count'].update(visible=False)
                window['Measurement Unit'].update(visible=False)
                window['Count Text'].update(visible=False)
             else:  # Default case for 'Scheduled'
                window['Time Slots Frame'].update(visible=True)
                window['Count'].update(visible=False)
                window['Measurement Unit'].update(visible=False)
                window['Count Text'].update(visible=False)
        elif event == 'Submit':
            medication_name = values['Medication Name']
            dosage = values['Dosage']
            instructions = values['Instructions']
            medication_type = values['Medication Type']

            # Check if instructions are provided for PRN and Controlled medications
            if medication_type in ['As Needed (PRN)', 'Controlled'] and not instructions.strip():
                sg.popup('Instructions are required for PRN and Controlled medications.', title='Error')
                continue

            selected_time_slots = []
            medication_form = None
            medication_count = None

            if medication_type == 'Scheduled':
                for slot in ['Morning', 'Noon', 'Evening', 'Night']:
                    if values[f'TIME_SLOT_{slot}']:
                        selected_time_slots.append(slot)

            elif medication_type == 'Controlled':
                medication_count = int(values['Count'])
                medication_form = 'Pill' if values['Measurement Unit'] == 'Pills' else 'Liquid'

                # Convert to mL if needed
                if values['Measurement Unit'] == 'L':
                    # 1 liter = 1000 mL
                    medication_count = float(medication_count) * 1000
                elif values['Measurement Unit'] == 'oz':
                    # 1 ounce = 29.5735 mL
                    medication_count = float(medication_count) * 29.5735

                medication_count = round(medication_count)  # Round to nearest whole number
                # Validate medication count
            # try:
            #     medication_count = int(medication_count)
            #     if medication_count < 0:
            #         sg.popup('Please enter a valid non-negative count for the medication.', title='Error')
            #         continue
            # except ValueError:
            #     sg.popup('Please enter a valid count for the medication.', title='Error')
            #     continue

            # Insert the new medication
            db_functions.insert_medication(resident_name, medication_name, dosage, instructions, medication_type, selected_time_slots, medication_form, medication_count)
            current_user = config.global_config['logged_in_user']
            db_functions.log_action(current_user, 'New Medication', f'Medication Added {medication_name}, type {medication_type} by {current_user}')
            sg.popup('Medication Saved')
            window.close()

    window.close()


def get_medication_list(medication_data):
    med_list = []
    for category in medication_data:
        if category == 'Scheduled':
            for time_slot in medication_data[category]:
                med_list.extend(medication_data[category][time_slot].keys())
        else:
            med_list.extend(medication_data[category].keys())
    return list(set(med_list))  # Remove duplicates


def edit_medication_window(selected_resident):
    resident_id = db_functions.get_resident_id(selected_resident)
    medication_names = db_functions.fetch_medications_for_resident(selected_resident)
    med_list = get_medication_list(medication_names)


    layout = [
        [sg.Text('Select Medication:'), sg.Combo(med_list, key='-MEDICATION-', readonly=True)],
        [sg.Text('New Medication Name:'), sg.InputText(key='-NEW_MED_NAME-')],
        [sg.Text('New Dosage:'), sg.InputText(key='-NEW_DOSAGE-')],
        [sg.Text('New Instructions:'), sg.InputText(key='-NEW_INSTRUCTIONS-')],
        [sg.Button('Update'), sg.Button('Cancel')]
    ]

    window = sg.Window('Edit Medication Details', layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Update':
            # Fetch current medication details
            current_details = db_functions.fetch_medication_details(values['-MEDICATION-'], resident_id)
            if current_details:
                # Update medication details
                db_functions.update_medication_details(values['-MEDICATION-'], resident_id, values['-NEW_MED_NAME-'].strip(), values['-NEW_DOSAGE-'].strip(), values['-NEW_INSTRUCTIONS-'].strip())
                sg.popup('Medication details updated')
            else:
                sg.popup('Medication not found')
            break

    window.close()


def compare_emar_data_and_log_changes(user_input_data, resident_name, date):
    # Fetch current eMAR data from the database
    current_data = db_functions.fetch_current_emar_data_for_resident_date(resident_name, date)
    
    changes_made = []
    for entry in user_input_data:
        matching_entry = next((item for item in current_data if item['medication_name'] == entry['medication_name'] and item['time_slot'] == entry['time_slot']), None)
        if matching_entry:
            if matching_entry['administered'] != entry['administered']:
                changes_made.append(f"Administered {entry['medication_name']} at {entry['time_slot']}: {entry['administered']}")
        else:
            changes_made.append(f"Administered {entry['medication_name']} at {entry['time_slot']}: {entry['administered']}")

    # Construct the audit log description
    audit_description = f"eMAR changes for {resident_name} on {date}: " + "; ".join(changes_made)
    return audit_description


def prn_administer_window(resident_name, medication_name):
    # Set current date and time for default values
    curent_datetime = datetime.now()
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    current_user = config.global_config['logged_in_user']
    user_initials = db_functions.get_user_initials(current_user)
    
    layout = [
        [sg.Text("Medication:"), sg.Text(medication_name)],
        [sg.Text("Date:"), sg.InputText(current_date, key='-DATE-', size=(10, 1)), 
         sg.Text("Time:"), sg.Spin(values=[i for i in range(0, 24)], initial_value=current_hour, key='-HOUR-', size=(2, 1)),
         sg.Text(":"), sg.Spin(values=[i for i in range(0, 60)], initial_value=current_minute, key='-MINUTE-', size=(2, 1))],
        [sg.Text("Administered By (Initials):", size=(20, 1)), sg.InputText(key='-INITIALS-', size=(20, 1), readonly=True, default_text=user_initials)],
        [sg.Text("Notes (Optional):", size=(20, 1)), sg.InputText(key='-NOTES-', size=(20, 1))],
        [sg.Button("Submit"), sg.Button("Cancel")]
    ]

    window = sg.Window(f"Administer PRN Medication: {medication_name}", layout)
    
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Submit":
            # Combine date and time
            admin_datetime_str = f"{values['-DATE-']} {values['-HOUR-']:02d}:{values['-MINUTE-']:02d}"
            admin_datetime = datetime.strptime(admin_datetime_str, "%Y-%m-%d %H:%M")

            # Prevent future date/time selection
            if admin_datetime > curent_datetime:
                sg.popup("The selected date/time is in the future. Please choose a current or past time.")
                continue

            admin_data = {
                "datetime": admin_datetime_str,
                "initials": user_initials,
                "notes": values['-NOTES-']
            }
            
            db_functions.save_prn_administration_data(resident_name, medication_name, admin_data)
            db_functions.log_action(current_user,'Administer PRN Med', f'user: {current_user} medication: {medication_name} resident: {resident_name} ')
            sg.popup(f"Medication {medication_name} administered.")
            break
    
    window.close()


def controlled_administer_window(resident_name, medication_name, med_count, med_form):
    # Set current date and time for default values
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute

    # Create layout based on medication form
    if med_form == 'Pill':
        count_layout = [[sg.Text("Number of Pills Administered:"), sg.InputText(key='-ADMINISTERED_COUNT-', size=(5, 1))]]
    elif med_form == 'Liquid':
        count_layout = [[sg.Text("Amount Administered (mL):"), sg.InputText(key='-ADMINISTERED_COUNT-', size=(5, 1))]]
    
    layout = [
        [sg.Text("Medication:"), sg.Text(medication_name)],
        [sg.Text("Date:"), sg.InputText(current_date, key='-DATE-', size=(10, 1)), 
         sg.Text("Time:"), sg.Spin(values=[i for i in range(0, 24)], initial_value=current_hour, key='-HOUR-', size=(2, 1)),
         sg.Text(":"), sg.Spin(values=[i for i in range(0, 60)], initial_value=current_minute, key='-MINUTE-', size=(2, 1))],
        [sg.Text("Administered By (Initials):", size=(20, 1)), sg.InputText(key='-INITIALS-', size=(20, 1))],
        [sg.Text("Notes:", size=(20, 1)), sg.InputText(key='-NOTES-', size=(20, 1))],
        count_layout,  # Include count input based on medication form
        [sg.Button("Submit"), sg.Button("Cancel")]
    ]

    window = sg.Window(f"Administer Controlled Medication: {medication_name}", layout)
    
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Submit":
            initials = values['-INITIALS-'].strip().upper()
            if not initials:
                sg.popup('Please enter your initials to proceed')
                continue

            # Validate the administered count
            try:
                administered_count = int(values['-ADMINISTERED_COUNT-'])
                if administered_count <= 0 or administered_count > med_count:
                    raise ValueError
            except ValueError:
                sg.popup('Invalid count. Please enter a valid number.')
                continue

            # Process the administration data
            admin_datetime = f"{values['-DATE-']} {values['-HOUR-']:02d}:{values['-MINUTE-']:02d}"
            admin_data = {
                "datetime": admin_datetime,
                "initials": values['-INITIALS-'].upper(),
                "notes": values['-NOTES-'],
                "administered_count": administered_count
            }

            # Save administration data and update medication count
            db_functions.save_controlled_administration_data(resident_name, medication_name, admin_data, med_count - administered_count)
            sg.popup(f"Medication {medication_name} administered.")

            break
    
    window.close()


def create_prn_medication_entry(medication_name, dosage, instructions):
    return [
        sg.Text(text=medication_name + " " + dosage, size=(23, 1), font=(welcome_screen.FONT, 11)),
        sg.Text(instructions, size=(30, 1), font=(welcome_screen.FONT, 11)),
        sg.Button('Administer', key=f'-ADMIN_PRN_{medication_name}-', font=(welcome_screen.FONT, 11))
    ]


def create_controlled_medication_entry(medication_name, dosage, instructions, count, form):
    return [
        sg.Text(text=f"{medication_name} {dosage}", size=(23, 1), font=(welcome_screen.FONT, 11)),
        sg.Text(instructions, size=(25, 1), font=(welcome_screen.FONT, 11)),
        sg.Text(f"Count: {count}{'mL' if form == 'Liquid' else ' Pills'}", size=(13, 1), font=(welcome_screen.FONT, 11)),
        sg.Button('Administer', key=f'-ADMIN_CONTROLLED_{medication_name}-', font=(welcome_screen.FONT, 11))
    ]


def create_medication_entry(medication_name, dosage, instructions, time_slot, administered=''):
    return [
        sg.Checkbox('', key=f'-CHECK_{medication_name}_{time_slot}-', enable_events=True, tooltip='Check if administered', disabled=True if administered != '' else False,
                    default=True if administered != '' else False),
        sg.InputText(default_text=administered, key=f'-GIVEN_{medication_name}_{time_slot}-', size=3, readonly=True),
        sg.Text(text=medication_name + " " + dosage, size=(25, 1), font=(welcome_screen.FONT, 13)),
        sg.Text(instructions, size=(30, 1), font=(welcome_screen.FONT, 13))
    ]


def create_time_slot_section(time_slot, medications):
    layout = [create_medication_entry(med_name, med_info['dosage'], med_info['instructions'], time_slot) for med_name, med_info in medications.items()]
    return sg.Frame(time_slot, layout, font=(welcome_screen.FONT, 13))


def retrieve_emar_data_from_window(window, resident_name):
    emar_data = []

    # Fetch medications for the resident
    medications_schedule = db_functions.fetch_medications_for_resident(resident_name)
    # print(medications_schedule)  # Testing

    for category in ['Scheduled', 'PRN']:
        for time_slot, medications in medications_schedule[category].items():
            if category == 'Scheduled':
                for medication_name, medication_info in medications.items():
                    key = f"-GIVEN_{medication_name}_{time_slot}-"
                    administered = window[key].get().upper()
                    emar_data.append({
                    'resident_name': resident_name,
                    'medication_name': medication_name,
                    'time_slot': time_slot,
                    'administered': administered,
                    'date': datetime.now().strftime("%Y-%m-%d")
                })

    return emar_data


def filter_medications_data(all_medications_data, active_medications):
    filtered_data = {'Scheduled': {}, 'PRN': {}, 'Controlled': {}}

    # Filter Scheduled Medications
    for time_slot, meds in all_medications_data['Scheduled'].items():
        for med_name, details in meds.items():
            if med_name in active_medications:
                if time_slot not in filtered_data['Scheduled']:
                    filtered_data['Scheduled'][time_slot] = {}
                filtered_data['Scheduled'][time_slot][med_name] = details

    # Remove empty time slots from Scheduled medications
    filtered_data['Scheduled'] = {ts: meds for ts, meds in filtered_data['Scheduled'].items() if meds}

    # Filter PRN Medications
    for med_name, details in all_medications_data['PRN'].items():
        if med_name in active_medications:
            filtered_data['PRN'][med_name] = details

    # Filter Controlled Medications
    for med_name, details in all_medications_data.get('Controlled', {}).items():
        if med_name in active_medications:
            filtered_data['Controlled'][med_name] = details

    return filtered_data


def get_emar_tab_layout(resident_name):
    # Fetch medications for the resident, including both scheduled and PRN
    all_medications_data = db_functions.fetch_medications_for_resident(resident_name)
    # Extracting medication names and removing duplicates
    scheduled_meds = [med_name for time_slot in all_medications_data['Scheduled'].values() for med_name in time_slot]
    prn_meds = list(all_medications_data['PRN'].keys())
    controlled_meds = list(all_medications_data['Controlled'].keys())
    all_meds = list(set(scheduled_meds + prn_meds + controlled_meds))
    # Filter out discontinued medications
    active_medications = db_functions.filter_active_medications(all_meds, resident_name)
    # print('testing active medications')
    # print(active_medications)
    # Filter the medications data
    filtered_medications_data = filter_medications_data(all_medications_data, active_medications)
    # print(filtered_medications_data)
    # print('--------------------------------------')
    # print(all_medications_data)

    existing_emar_data = db_functions.fetch_emar_data_for_resident(resident_name)
    all_administered = True

    # Predefined order of time slots
    time_slot_order = ['Morning', 'Noon', 'Evening', 'Night']

     # Group Scheduled Medications by Time Slot
    time_slot_groups = {}
    for time_slot, medications in filtered_medications_data['Scheduled'].items():
        for med_name, med_info in medications.items():
            administered_value = existing_emar_data.get(med_name, {}).get(time_slot, '')
            if time_slot not in time_slot_groups:
                time_slot_groups[time_slot] = []
            time_slot_groups[time_slot].append(create_medication_entry(med_name, med_info['dosage'], med_info['instructions'], time_slot, administered_value))
            if administered_value == '':
                all_administered = False  # Set to False if any medication is not administered
    
    # Create Frames for Each Time Slot in the predefined order
    sections = []
    for time_slot in time_slot_order:
        if time_slot in time_slot_groups:
            section_frame = sg.Frame(time_slot, time_slot_groups[time_slot], font=(welcome_screen.FONT_BOLD, 12))
            sections.append([section_frame])

    # Handle PRN Medications
    if filtered_medications_data['PRN']:
        prn_section_layout = [create_prn_medication_entry(med_name, med_info['dosage'], med_info['instructions']) 
                          for med_name, med_info in filtered_medications_data['PRN'].items()]
        prn_section_frame = sg.Frame('As Needed (PRN)', prn_section_layout, font=(welcome_screen.FONT_BOLD, 12))
        sections.append([prn_section_frame])

    # print(filtered_medications_data)
    
    # Handle Controlled Medications
    if filtered_medications_data['Controlled']:
        controlled_section_layout = [create_controlled_medication_entry(med_name, med_info['dosage'], med_info['instructions'], med_info['count'], med_info['form'])
            for med_name, med_info in filtered_medications_data['Controlled'].items()]
        controlled_section_frame = sg.Frame('Controlled Medications', controlled_section_layout, font=(welcome_screen.FONT_BOLD, 12))
        sections.append([controlled_section_frame])

    logged_in_user = config.global_config['logged_in_user']
    # Bottom part of the layout with buttons
    bottom_layout = [
        [sg.Text('', expand_x=True), sg.Button('Save', key='-EMAR_SAVE-', font=(welcome_screen.FONT, 11), disabled=all_administered), 
         sg.Button('Add Medication', key='-ADD_MEDICATION-', font=(welcome_screen.FONT, 11), visible=db_functions.is_admin(logged_in_user)), 
         sg.Button('Edit Medication', key='-EDIT_MEDICATION-', font=(welcome_screen.FONT, 11)), sg.Button("Discontinue Medication", key='-DC_MEDICATION-' , font=(welcome_screen.FONT, 11)), 
         sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Button('View/Edit Current Month eMARS Chart', key='CURRENT_EMAR_CHART', font=(welcome_screen.FONT, 11)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text('Or Search by Month and Year', font=(welcome_screen.FONT, 11)), sg.Text('', expand_x=True)],
        [sg.Text(text="", expand_x=True), sg.Text(text="Enter Month: (MM)", font=(welcome_screen.FONT, 11)), sg.InputText(size=4, key="-EMAR_MONTH-"), sg.Text("Enter Year: (YYYY)", font=(welcome_screen.FONT, 11)), sg.InputText(size=5, key='-EMAR_YEAR-'), sg.Button("Search", key='-EMAR_SEARCH-', font=(welcome_screen.FONT, 11)), sg.Text(text="", expand_x=True)]
    ]


    combined_layout = sections + bottom_layout
    #print(combined_layout)

    # Create a scrollable container for the combined layout
    scrollable_layout = sg.Column(combined_layout, scrollable=True, vertical_scroll_only=True, size=(750, 695))  # Adjust the size as needed

    # Return the scrollable layout
    return [[scrollable_layout]]


if __name__ == "__main__":
    # Create the eMAR tab layout for a specific resident
    eMAR_tab_layout = get_emar_tab_layout("Resident Name")
    eMAR_tab = sg.Tab('eMAR Management', eMAR_tab_layout)  # Create the eMAR tab with the layout

    # Create the window with the eMAR tab
    window = sg.Window('Resident Management', [[sg.TabGroup([[eMAR_tab]])]], finalize=True)

    # Event Loop
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break

    window.close()