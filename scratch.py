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


def create_medication_section(medication_name, medication_info):
    section_layout = []
    section_layout.append([create_row_label(medication_name)])
    section_layout.append([create_row_label(f"{medication_info['dosage']}")])
    section_layout.append([create_row_label(f"{medication_info['instructions']}")])

    for time_slot in medication_info['time_slots']:
        row = [create_row_label(time_slot)  + [sg.Text(' '* spacer_width)] + create_input_text(f"{medication_name}_{time_slot}")]
        section_layout.append(row)

    section_layout.append(create_horizontal_bar(''))  # End with a horizontal bar
    return section_layout


def show_emar_chart(resident_name, year_month):
    # Define the number of days
    num_days = 31

    # Define the width of the label cell and regular cells
    label_cell_width = 20  # This may need to be adjusted to align perfectly
    regular_cell_width = 5  # This may need to be adjusted to align perfectly

    # Empty row for the table to just show headers
    data = [[]]  # No data rows, only headers

    # Parse the year and month
    year, month_number = year_month.split('-')
    month_name = calendar.month_name[int(month_number)]

    # Fetch medication data (mocked for example)
    # Updated medication data
    medication_data = {
    'Medication A': {
        'dosage': '10mg', 
        'instructions': '',
        'time_slots': ['Morning', 'Evening']
    },
    'AveryLongfuckingName': {
        'dosage': '5mg', 
        'instructions': 'Hold if BS > 200 dskadmla',
        'time_slots': ['Noon']
    },
    # ... other medications
}

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
        create_horizontal_bar(text='')
    ]
    for med_name, med_info in medication_data.items():
        layout.extend(create_medication_section(med_name, med_info))


    # Create the window
    window = sg.Window(' CareTech Monthly eMARS', layout, finalize=True, resizable=True)

    # adl_data = fetch_adl_chart_data_for_month(resident_name, year_month) -- change for emar

    # If data is found, update the layout fields accordingly
    
    # Event Loop
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        

    window.close()


if __name__ == "__main__":
    show_emar_chart("Rosa Soto", "2023-12")
