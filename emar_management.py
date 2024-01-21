import PySimpleGUI as sg
import db_functions
from datetime import datetime
import resident_management
import welcome_screen

def add_medication_window(resident_name):
    medication_type_options = ['Scheduled', 'As Needed (PRN)']
    
    layout = [
        [sg.Text('Medication Type', size=(18, 1), font=(welcome_screen.FONT, 12)), sg.Combo(medication_type_options, default_value='Scheduled', key='Medication Type', readonly=True, enable_events=True, font=(welcome_screen.FONT, 12))],
        [sg.Text('Medication Name', size=(18, 1), font=(welcome_screen.FONT, 12)), sg.InputText(key='Medication Name', font=(welcome_screen.FONT, 12))],
        [sg.Text('Dosage', size=(18, 1), font=(welcome_screen.FONT, 12)), sg.InputText(key='Dosage', font=(welcome_screen.FONT, 12))],
        [sg.Text('Instructions', size=(18, 1), font=(welcome_screen.FONT, 12)), sg.InputText(key='Instructions', font=(welcome_screen.FONT, 12))],
        [sg.Text('(Required For PRN Medication)', font=(welcome_screen.FONT, 10))],
        [sg.Text('', expand_x=True), sg.Frame('Time Slots (Select All That Apply)', [[sg.Checkbox(slot, key=f'TIME_SLOT_{slot}', font=(welcome_screen.FONT, 11)) for slot in ['Morning', 'Noon', 'Evening', 'Night']]], key='Time Slots Frame', font=(welcome_screen.FONT, 12), pad=10), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Column(layout=[[sg.Button('Submit', font=(welcome_screen.FONT, 11)), sg.Button('Cancel', font=(welcome_screen.FONT, 11), pad=8)]]), 
         sg.Text('', expand_x=True)]
    ]

    window = sg.Window('Add Medication', layout)

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Medication Type':
            is_prn = values['Medication Type'] == 'As Needed (PRN)'
            window['Time Slots Frame'].update(visible=not is_prn)
        elif event == 'Submit':
            medication_name = values['Medication Name']
            dosage = values['Dosage']
            instructions = values['Instructions']
            medication_type = values['Medication Type']

            #  Check if instructions are provided for PRN medications
            if medication_type == 'As Needed (PRN)' and not instructions.strip():
                sg.popup('Instructions are required for PRN (As Needed) medications.', title='Error')
                continue

            # Retrieve time slots only for scheduled medications
            selected_time_slots = []
            if medication_type == 'Scheduled':
                for slot in ['Morning', 'Noon', 'Evening', 'Night']:
                    if values[f'TIME_SLOT_{slot}']:
                        selected_time_slots.append(slot)
            
            # Insert the new medication
            db_functions.insert_medication(resident_name, medication_name, dosage, instructions, medication_type, selected_time_slots)
            sg.popup('Medication Saved')
            window.close()

    window.close()

def open_administer_window(resident_name, medication_name):
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    layout = [
    [sg.Text("Medication:"), sg.Text(medication_name)],
    [sg.Text("Date and Time:"), sg.Text(current_datetime, key='-CURRENT_DATETIME-')],
    [sg.Text("Administered By (Initials):", size=(20, 1)), sg.InputText(key='-INITIALS-', size=(20, 1))],  # Adjusted label size and input box size
    [sg.Text("Notes (Optional):", size=(20, 1)), sg.InputText(key='-NOTES-', size=(20, 1))],  # Adjusted label size and input box size
    [sg.Button("Submit"), sg.Button("Cancel")]
    ]

    
    window = sg.Window(f"Administer PRN Medication: {medication_name}", layout)
    
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Submit":
            initials = values['-INITIALS-'].strip()
            if not initials:
                sg.popup('Please enter your initials to proceed')
                continue
            # Process the administration data
            admin_data = {
                "datetime": current_datetime,
                "initials": values['-INITIALS-'],
                "notes": values['-NOTES-']
            }
            
            db_functions.save_prn_administration_data(resident_name, medication_name, admin_data)
            sg.popup(f"Medication {medication_name} administered.")
            break
    
    window.close()


def create_prn_medication_entry(medication_name, dosage, instructions):
    return [
        sg.Text(text=medication_name + " " + dosage, size=(15, 1), font=(welcome_screen.FONT, 11)),
        sg.Text(instructions, size=(30, 1), font=(welcome_screen.FONT, 11)),
        sg.Button('Administer', key=f'-ADMIN_PRN_{medication_name}-', font=(welcome_screen.FONT, 11))
    ]


def create_medication_entry(medication_name, dosage, instructions, time_slot, administered=''):
    return [
        sg.InputText(default_text=administered, key=f'-GIVEN_{medication_name}_{time_slot}-', size=3),
        sg.Text(text=medication_name + " " + dosage, size=(15, 1), font=(welcome_screen.FONT, 13)),
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


def get_emar_tab_layout(resident_name):
    # Fetch medications for the resident, including both scheduled and PRN
    medications_data = db_functions.fetch_medications_for_resident(resident_name)
    existing_emar_data = db_functions.fetch_emar_data_for_resident(resident_name)

    # Predefined order of time slots
    time_slot_order = ['Morning', 'Noon', 'Evening', 'Night']

     # Group Scheduled Medications by Time Slot
    time_slot_groups = {}
    for time_slot, medications in medications_data['Scheduled'].items():
        for med_name, med_info in medications.items():
            if time_slot not in time_slot_groups:
                time_slot_groups[time_slot] = []
            administered_value = existing_emar_data.get(med_name, {}).get(time_slot, '')
            time_slot_groups[time_slot].append(create_medication_entry(med_name, med_info['dosage'], med_info['instructions'], time_slot, administered_value))
    
    # Create Frames for Each Time Slot in the predefined order
    sections = []
    for time_slot in time_slot_order:
        if time_slot in time_slot_groups:
            section_frame = sg.Frame(time_slot, time_slot_groups[time_slot], font=(welcome_screen.FONT_BOLD, 12))
            sections.append([section_frame])

    # Handle PRN Medications
    if medications_data['PRN']:
        prn_section_layout = [create_prn_medication_entry(med_name, med_info['dosage'], med_info['instructions']) 
                          for med_name, med_info in medications_data['PRN'].items()]
        prn_section_frame = sg.Frame('As Needed (PRN)', prn_section_layout, font=(welcome_screen.FONT_BOLD, 12))
        sections.append([prn_section_frame])


    # Bottom part of the layout with buttons
    bottom_layout = [
        [sg.Text('', expand_x=True), sg.Button('Save', key='-EMAR_SAVE-', font=(welcome_screen.FONT, 11)), sg.Button('Add Medication', key='-ADD_MEDICATION-', font=(welcome_screen.FONT, 11)), sg.Button("Discontinue Medication", font=(welcome_screen.FONT, 11)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Button('View/Edit Current Month eMARS Chart', key='CURRENT_EMAR_CHART', font=(welcome_screen.FONT, 11)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text('Or Search by Month and Year', font=(welcome_screen.FONT, 11)), sg.Text('', expand_x=True)],
        [sg.Text(text="", expand_x=True), sg.Text(text="Enter Month: (MM)", font=(welcome_screen.FONT, 11)), sg.InputText(size=4, key="-EMAR_MONTH-"), sg.Text("Enter Year: (YYYY)", font=(welcome_screen.FONT, 11)), sg.InputText(size=5, key='-EMAR_YEAR-'), sg.Button("Search", key='-EMAR_SEARCH-', font=(welcome_screen.FONT, 11)), sg.Text(text="", expand_x=True)]
    ]


    combined_layout = sections + bottom_layout
    #print(combined_layout)

    # Create a scrollable container for the combined layout
    scrollable_layout = sg.Column(combined_layout, scrollable=True, vertical_scroll_only=True, size=(740, 685))  # Adjust the size as needed

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