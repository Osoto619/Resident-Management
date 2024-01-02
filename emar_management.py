import PySimpleGUI as sg
import db_functions
from datetime import datetime
import resident_management

def add_medication_window(resident_name):
    medication_type_options = ['Scheduled', 'As Needed (PRN)']
    
    layout = [
        [sg.Text('Medication Type'), sg.Combo(medication_type_options, default_value='Scheduled', key='Medication Type', readonly=True, enable_events=True)],
        [sg.Text('Medication Name'), sg.InputText(key='Medication Name')],
        [sg.Text('Dosage'), sg.InputText(key='Dosage')],
        [sg.Text('Instructions'), sg.InputText(key='Instructions')],
        [sg.Frame('Time Slots (Select All That Apply)', [[sg.Checkbox(slot, key=f'TIME_SLOT_{slot}') for slot in ['Morning', 'Noon', 'Evening', 'Night']]], key='Time Slots Frame')],
        [sg.Button('Submit'), sg.Button('Cancel')]
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
        [sg.Text("Administered By (Initials):"), sg.InputText(key='-INITIALS-')],
        [sg.Text("Notes (Optional):"), sg.InputText(key='-NOTES-')],
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
        sg.Text(text=medication_name + " " + dosage, size=(15, 1)),
        sg.Text(instructions, size=(30, 1)),
        sg.Button('Administer', key=f'-ADMIN_PRN_{medication_name}-')
    ]



def create_medication_entry(medication_name, dosage, instructions, time_slot, administered=''):
    return [
        sg.InputText(default_text=administered, key=f'-GIVEN_{medication_name}_{time_slot}-', size=3),
        sg.Text(text=medication_name + " " + dosage, size=(15, 1)),
        sg.Text(instructions, size=(30, 1))
    ]


def create_time_slot_section(time_slot, medications):
    layout = [create_medication_entry(med_name, med_info['dosage'], med_info['instructions'], time_slot) for med_name, med_info in medications.items()]
    return sg.Frame(time_slot, layout)


def retrieve_emar_data_from_window(window, resident_name):
    emar_data = []

    # Fetch medications for the resident
    medications_schedule = db_functions.fetch_medications_for_resident(resident_name)
    print(medications_schedule)  # Testing

    for category in ['Scheduled', 'PRN']:
        for time_slot, medications in medications_schedule[category].items():
            if category == 'Scheduled':
                for medication_name, medication_info in medications.items():
                    key = f"-GIVEN_{medication_name}_{time_slot}-"
                    administered = window[key].get() 
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

    sections = []
    
    # Handle Scheduled Medications
    for time_slot, medications in medications_data['Scheduled'].items():
        for med_name, med_info in medications.items():
            administered_value = existing_emar_data.get(med_name, {}).get(time_slot, '')
            section_layout = create_medication_entry(med_name, med_info['dosage'], med_info['instructions'], time_slot, administered_value)
            section_frame = sg.Frame(time_slot, [section_layout])
            sections.append([section_frame])

    # Handle PRN Medications
    if medications_data['PRN']:
        prn_section_layout = [create_prn_medication_entry(med_name, med_info['dosage'], med_info['instructions']) 
                          for med_name, med_info in medications_data['PRN'].items()]
        prn_section_frame = sg.Frame('As Needed (PRN)', prn_section_layout)
        sections.append([prn_section_frame])


    # Bottom part of the layout with buttons
    bottom_layout = [
        [sg.Text('', expand_x=True), sg.Button('Save', key='-EMAR_SAVE-'), sg.Button('Add Medication', key='-ADD_MEDICATION-'), sg.Button("Discontinue Medication"), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Button('View/Edit Current Month eMARS Chart', key='CURRENT_EMAR_CHART'), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text('Or Search by Month and Year'), sg.Text('', expand_x=True)],
        [sg.Text(text="", expand_x=True), sg.Text(text="Enter Month: (MM)"), sg.InputText(size=4, key="-EMAR_MONTH-"), sg.Text("Enter Year: (YYYY)"), sg.InputText(size=5, key='-EMAR_YEAR-'), sg.Button("Search", key='-EMAR_SEARCH-'), sg.Text(text="", expand_x=True)]
    ]

    return sections + bottom_layout


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