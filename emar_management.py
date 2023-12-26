import PySimpleGUI as sg
import db_functions
from datetime import datetime

def add_medication_window():
    time_slots = ['Morning', 'Noon', 'Evening', 'Night']  # Adjust as needed
    time_slot_checkboxes = [sg.Checkbox(slot, key=f'TIME_SLOT_{slot}') for slot in time_slots]

    layout = [
        [sg.Text('Medication Name'), sg.InputText(key='Medication Name')],
        [sg.Text('Dosage'), sg.InputText(key='Dosage')],
        [sg.Text('Instructions'), sg.InputText(key='Instructions')],
        [sg.Frame('Time Slots (Select All That Apply)', [time_slot_checkboxes])],
        [sg.Button('Submit'), sg.Button('Cancel')]
    ]
    return sg.Window('Add Medication', layout)


def create_medication_entry(medication_name, dosage, instructions, time_slot, administered=''):
    return [
        sg.InputText(default_text=administered, key=f'-GIVEN_{medication_name}_{time_slot}-', size=3),
        sg.Text(medication_name, size=(20, 1)),
        sg.Text(dosage, size=(10, 1)),
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

    for time_slot, medications in medications_schedule.items():
        for medication_name, medication_info in medications.items():
            key = f'-GIVEN_{medication_name}_{time_slot}-'
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
    existing_emar_data = db_functions.fetch_emar_data_for_resident(resident_name)

    # Fetch medications for the resident
    medications_schedule = db_functions.fetch_medications_for_resident(resident_name)

    sections = []
    for time_slot, medications in medications_schedule.items():
        section_layout = [create_medication_entry(med_name, med_info['dosage'], med_info['instructions'], time_slot, existing_emar_data.get(med_name, {}).get(time_slot, '')) for med_name, med_info in medications.items()]
        section_frame = sg.Frame(time_slot, section_layout)
        sections.append([section_frame])

    layout = sections + [[sg.Text('', expand_x=True), sg.Button('Save', key='-EMAR_SAVE-'), sg.Button('Add Medication', key='-ADD_MEDICATION-'), sg.Button("Discontinue Medication"),
                          sg.Text('', expand_x=True)]]
    layout.append([sg.Text('', expand_x=True), sg.Button('View/Edit Current Month eMARS Chart', key='CURRENT_EMAR_CHART'), sg.Text('', expand_x=True)])
    layout.append([sg.Text('', expand_x=True),sg.Text('Or Search by Month and Year'), sg.Text('', expand_x=True)])
    layout.append([sg.Text(text="", expand_x=True),sg.Text(text="Enter Month: (MM)"), sg.InputText(size=4, key="-EMAR_MONTH-") , sg.Text("Enter Year: (YYYY)"), sg.InputText(size=5, key='-EMAR_YEAR-'), 
             sg.Button("Search", key='-EMAR_SEARCH-'), sg.Text(text="", expand_x=True)])

    return layout



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
