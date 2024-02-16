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
            medication_name = values['Medication Name'].title()
            dosage = values['Dosage']
            instructions = values['Instructions'].upper()
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
            db_functions.log_action(current_user, 'New Medication', f'Medication Added {medication_name}, type {medication_type} for resident {resident_name}')
            sg.popup('Medication Saved')
            window.close()

    window.close()


def add_non_medication_order_window(resident_name):
    resident_id = db_functions.get_resident_id(resident_name)
    layout = [
        [sg.Text('Order Name:'), sg.InputText(key='-ORDER_NAME-')],
        [sg.Text('Special Instructions:'), sg.InputText(key='-INSTRUCTIONS-')],
        [sg.Frame('Scheduling Options', [
            [sg.Radio('Set Frequency (in days):', "RADIO1", default=True, key='-FREQ_OPTION-', enable_events=True),
             sg.InputText(size=(5,1), key='-FREQUENCY-', enable_events=True)],
            [sg.Radio('Select Specific Days:', "RADIO1", key='-DAYS_OPTION-', enable_events=True),
             sg.Checkbox('Mon', key='-MON-'), sg.Checkbox('Tue', key='-TUE-'),
             sg.Checkbox('Wed', key='-WED-'), sg.Checkbox('Thu', key='-THU-'),
             sg.Checkbox('Fri', key='-FRI-'), sg.Checkbox('Sat', key='-SAT-'),
             sg.Checkbox('Sun', key='-SUN-')]
        ])],
        [sg.Button('Add Order'), sg.Button('Cancel')]
    ]

    window = sg.Window('Add Non-Medication Order', layout, finalize=True)

    # Initially disable specific days checkboxes
    for day in ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
        window[f'-{day}-'].update(disabled=True)

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Cancel':
            break
        elif event == '-FREQ_OPTION-':
            # Disable specific days checkboxes and enable frequency input
            window['-FREQUENCY-'].update(disabled=False)
            for day in ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
                window[f'-{day}-'].update(disabled=True, value=False)
        elif event == '-DAYS_OPTION-':
            # Disable frequency input and enable specific days checkboxes
            window['-FREQUENCY-'].update(disabled=True, value='')
            for day in ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
                window[f'-{day}-'].update(disabled=False)
        elif event == 'Add Order':
            order_name = values['-ORDER_NAME-'].strip()
            instructions = values['-INSTRUCTIONS-'].strip()
            if values['-FREQ_OPTION-']:
                frequency = values['-FREQUENCY-'].strip()
                specific_days = ''  # No specific days when frequency is chosen
                if not frequency.isdigit() or int(frequency) < 1:
                    sg.popup_error('Please enter a valid positive integer for frequency.')
                    continue
            else:
                frequency = ''  # No frequency when specific days are chosen
                days_selected = [day for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] if values[f'-{day.upper()}-']]
                if not days_selected:
                    sg.popup_error('Please select at least one day.')
                    continue
                specific_days = ', '.join(days_selected)

            # Proceed to save the non-medication order
            if order_name and (frequency or specific_days):
                db_functions.save_non_medication_order(resident_id, order_name, frequency, specific_days, instructions)
                sg.popup('Non-medication order added successfully.')
                # Optionally, log this action in the audit log with a description
                db_functions.log_action(config.global_config['logged_in_user'], 'Add Non-Medication Order', f'Order for {resident_name}: {order_name}')
            else:
                sg.popup_error('Order name, frequency, or specific days are required.')

            break

    window.close()


def perform_non_med_order_window(resident_name, order_name):
    resident_id = db_functions.get_resident_id(resident_name)
    user_initials = db_functions.get_user_initials(config.global_config['logged_in_user'])

    layout = [
        [sg.Text('Resident Name:'), sg.Text(resident_name)],
        [sg.Text('Order Name:'), sg.Text(order_name)],
        [sg.Text('Performed By (Initials):'), sg.Text(user_initials)],
        [sg.Text('Notes/Measurements:'), sg.InputText(key='-NON_MED_NOTES-')],
        [sg.Button('Record Completion'), sg.Button('Cancel')]
    ]

    window = sg.Window(f'Perform Non-Medication Order for {resident_name}', layout)

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Cancel':
            break
        elif event == 'Record Completion':
            notes = values['-NON_MED_NOTES-'].strip()
            db_functions.record_non_med_order_performance(order_name, resident_id, notes, user_initials)
            sg.popup('Non-medication order performance recorded successfully.')
            break

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
    med_data = db_functions.fetch_medications_for_resident(selected_resident)
    med_list = get_medication_list(med_data)
    layout = [
        [sg.Text('Select Medication:'), sg.Combo(med_list, key='-MEDICATION-', readonly=True)],
        [sg.Text('New Medication Name:'), sg.InputText(key='-NEW_MED_NAME-')],
        [sg.Text('New Dosage:'), sg.InputText(key='-NEW_DOSAGE-')],
        [sg.Text('New Instructions:'), sg.InputText(key='-NEW_INSTRUCTIONS-')],
        [sg.Button('Update'), sg.Button('Remove'), sg.Button('Cancel')]
    ]

    window = sg.Window('Edit Medication Details', layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Update':
            # Fetch current medication details
            current_details = db_functions.fetch_medication_details(values['-MEDICATION-'], resident_id)
            med_name = values['-MEDICATION-']
            if current_details:
                # Update medication details
                db_functions.update_medication_details(values['-MEDICATION-'], resident_id, values['-NEW_MED_NAME-'].strip(), values['-NEW_DOSAGE-'].strip(), values['-NEW_INSTRUCTIONS-'].strip())
                db_functions.log_action(config.global_config['logged_in_user'], 'Medication Typo Correction', f'Typos fixes for {med_name}')
                sg.popup('Medication details updated')
            else:
                sg.popup('Medication not found')
            break
        elif event == 'Remove':
            # Confirm removal
            if sg.popup_yes_no('Are you sure you want to remove this medication?') == 'Yes':
                db_functions.remove_medication(values['-MEDICATION-'], selected_resident)
                sg.popup('Medication removed successfully')
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
    audit_description = f"eMAR changes for {resident_name}: " + "; ".join(changes_made)
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
    user_initials = db_functions.get_user_initials(config.global_config['logged_in_user'])

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
        [sg.Text("Administered By (Initials):", size=(20, 1)), sg.InputText(key='-INITIALS-', size=(20, 1), default_text=user_initials, readonly=True)],
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

            # Validate the administered count for both integer and float values
            try:
                if med_form == 'Pill':
                    administered_count = int(values['-ADMINISTERED_COUNT-'])
                elif med_form == 'Liquid':
                    administered_count = float(values['-ADMINISTERED_COUNT-'])
                if administered_count > med_count or administered_count < 0:
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


def create_non_med_order_entry(order_name, special_instructions):
    return [
        sg.Text(text=order_name, size=(23, 1), font=(welcome_screen.FONT, 11)),
        sg.Text(special_instructions, size=(30, 1), font=(welcome_screen.FONT, 11)),
        sg.Button('Performed', key=f'-PERFORM_NON_MED_{order_name}-', font=(welcome_screen.FONT, 11))
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


def order_due_today(order):
    today = datetime.now().date()

    # Check based on frequency
    if order['frequency']:
        if order['last_administered_date'] is None:
            # If there's no last administered date, the order is due today for the first time
            return True
        else:
            last_administered_date = datetime.strptime(order['last_administered_date'], '%Y-%m-%d').date()
            days_since_last_administered = (today - last_administered_date).days
            # Check if the days since last administered is equal or greater than the frequency
            if days_since_last_administered >= int(order['frequency']):
                return True

    # Check based on specific days
    if order['specific_days']:
        specific_days = order['specific_days'].split(', ')
        current_weekday = today.strftime('%a')
        if current_weekday in specific_days:
            return True

    return False


def filter_active_non_medication_orders(orders):
    active_and_due_orders = []

    for order in orders:
        # Check if the order is not discontinued or discontinued in the future
        if order['discontinued_date'] is None or datetime.strptime(order['discontinued_date'], '%Y-%m-%d').date() > datetime.now().date():
            # Check if today matches the order's frequency or specific day
            if order_due_today(order):
                active_and_due_orders.append(order)

    return active_and_due_orders


def open_non_med_order_chart(resident_name, order_id, initial_month=None, initial_year=None):
    # If no month/year specified, default to current month/year
    if not initial_month or not initial_year:
        initial_month, initial_year = datetime.now().strftime('%m'), datetime.now().strftime('%Y')

    def fetch_chart_data(order_id, month, year):
        return db_functions.fetch_administrations_for_order(order_id, month, year)

    layout = [
        [sg.Text('Administration Records', font=('Helvetica', 16), justification='center')],
        [sg.Text('Month:'), sg.InputText(initial_month, size=(4, 1), key='-MONTH-'),
         sg.Text('Year:'), sg.InputText(initial_year, size=(4, 1), key='-YEAR-'),
         sg.Button('Refresh', key='-REFRESH-')],
        # Updated to include the 'Initials' column
        [sg.Table(values=[], headings=['Date', 'Notes', 'Initials'], key='-CHART-', auto_size_columns=True, display_row_numbers=True)],
        [sg.Button('Close')]
    ]

    window = sg.Window(f'Chart for {resident_name}', layout, modal=True, finalize=True)

    # Initial fetch and display
    chart_data = fetch_chart_data(order_id, initial_month, initial_year)
    window['-CHART-'].update(values=chart_data)

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, 'Close'):
            break
        elif event == '-REFRESH-':
            month, year = values['-MONTH-'], values['-YEAR-']
            chart_data = fetch_chart_data(order_id, month, year)
            window['-CHART-'].update(values=chart_data)

    window.close()


def open_non_med_orders_window(resident_name):
    # Fetch all non-medication orders for the resident
    non_med_orders = db_functions.fetch_all_non_medication_orders_for_resident(resident_name)

    # Define the layout for displaying orders
    layout = []

    # Add a title or header to the window
    layout.append([sg.Text(f'Non-Medication Orders for {resident_name}', font=('Helvetica', 16), justification='center')])

    # If there are no orders, display a message instead
    if not non_med_orders:
        layout.append([sg.Text("No non-medication orders found for this resident.")])
    else:
        # Iterate through each non-medication order and add it to the layout
        for order in non_med_orders:
            order_details = f"Order Name: {order['order_name']}, Frequency: {order['frequency'] if order['frequency'] else 'N/A'}, Specific Days: {order['specific_days'] if order['specific_days'] else 'N/A'}, Special Instructions: {order['special_instructions']}"
            layout.append([sg.Text(order_details, size=(50, 2))])
            layout.append([sg.Button('View Chart', key=f'-VIEW_CHART_{order["order_id"]}-')])

    # Add a Close button at the bottom
    layout.append([sg.Button('Close', key='-CLOSE-')])

    # Create the window
    window = sg.Window(f'Non-Medication Orders for {resident_name}', layout, modal=True)

    # Event loop
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == '-CLOSE-':
            break
        elif event.startswith('-VIEW_CHART_'):
            order_id = event.split('_')[-1][:-1]
            open_non_med_order_chart(resident_name,order_id)

    window.close()


def edit_non_med_order_window(selected_resident):
    resident_id = db_functions.get_resident_id(selected_resident)
    non_med_orders = db_functions.fetch_all_non_medication_orders_for_resident(selected_resident)
    non_med_order_list = [order['order_name'] for order in non_med_orders]

    layout = [
        [sg.Text('Select Order:'), sg.Combo(non_med_order_list, key='-NON_MED_ORDER-', readonly=True)],
        [sg.Text('New Order Name:'), sg.InputText(key='-NEW_ORDER_NAME-')],
        [sg.Text('New Special Instructions:'), sg.InputText(key='-NEW_INSTRUCTIONS-')],
        [sg.Button('Update'), sg.Button('Remove'), sg.Button('Cancel')]
    ]

    window = sg.Window('Edit Non-Medication Order Details', layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Update':
            order_name = values['-NON_MED_ORDER-']
            new_order_name = values['-NEW_ORDER_NAME-'].strip()
            new_instructions = values['-NEW_INSTRUCTIONS-'].strip()

            if order_name and (new_order_name or new_instructions):  # Check if user has entered new values
                # Update non-medication order details
                db_functions.update_non_med_order_details(order_name, resident_id, new_order_name, new_instructions)
                sg.popup('Non-medication order details updated')
            else:
                sg.popup('Please enter new values to update.')
            break
        elif event == 'Remove':
            # Confirm removal
            if sg.popup_yes_no('Are you sure you want to remove this non-medication order?') == 'Yes':
                db_functions.remove_non_med_order(values['-NON_MED_ORDER-'], selected_resident)
                sg.popup('Non-medication order removed successfully')
            break

    window.close()


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
    
    filtered_medications_data = filter_medications_data(all_medications_data, active_medications)
    
    existing_emar_data = db_functions.fetch_emar_data_for_resident(resident_name)
    all_administered = True

    # Fetch non-medication orders for the resident
    non_medication_orders = db_functions.fetch_all_non_medication_orders_for_resident(resident_name)
    #print(f'non-medication orders:{non_medication_orders}')
    # Filter active and due non-medication orders
    active_and_due_orders = filter_active_non_medication_orders(non_medication_orders)
    
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

    # Handle Non-Medication Orders Due Today
    if active_and_due_orders:
        non_med_section_layout = [create_non_med_order_entry(order['order_name'], order['special_instructions']) 
                                for order in active_and_due_orders]
        non_med_section_frame = sg.Frame('Non-Medication Orders Due Today', non_med_section_layout, font=(welcome_screen.FONT_BOLD, 12), title_color='red')
        sections.append([non_med_section_frame])

    # Handle PRN Medications
    if filtered_medications_data['PRN']:
        prn_section_layout = [create_prn_medication_entry(med_name, med_info['dosage'], med_info['instructions']) 
                          for med_name, med_info in filtered_medications_data['PRN'].items()]
        prn_section_frame = sg.Frame('As Needed (PRN)', prn_section_layout, font=(welcome_screen.FONT_BOLD, 12))
        sections.append([prn_section_frame])

    
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
         sg.Button('Edit Medication', key='-EDIT_MEDICATION-', font=(welcome_screen.FONT, 11), visible=db_functions.is_admin(config.global_config['logged_in_user'])), sg.Button("Discontinue Medication", key='-DC_MEDICATION-' , font=(welcome_screen.FONT, 11), visible=db_functions.is_admin(config.global_config['logged_in_user'])), 
         sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Button('Add Non-Medication Order', key='-ADD_NON-MEDICATION-', visible=db_functions.is_admin(config.global_config['logged_in_user']), font=(welcome_screen.FONT, 11)), 
         sg.Button('Edit Non-Medication Order', key='-EDIT_NON_MEDICATION-', font=(welcome_screen.FONT, 11)), sg.Button('View Non-Medication Orders', font=(welcome_screen.FONT, 11), key='-NON_MEDICATION_ORDERS-'), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Button('View Current Month eMARS Chart', key='CURRENT_EMAR_CHART', font=(welcome_screen.FONT, 11)), sg.Button('Generate Medication List', key='-MED_LIST-', font=(welcome_screen.FONT, 11)), sg.Text('', expand_x=True)],
        [sg.Text('', expand_x=True), sg.Text('Search eMARS Chart by Month and Year', font=(welcome_screen.FONT, 11)), sg.Text('', expand_x=True)],
        [sg.Text(text="", expand_x=True), sg.Text(text="Enter Month: (MM)", font=(welcome_screen.FONT, 11)), sg.InputText(size=4, key="-EMAR_MONTH-"), sg.Text("Enter Year: (YYYY)", font=(welcome_screen.FONT, 11)), sg.InputText(size=5, key='-EMAR_YEAR-'), sg.Button("Search", key='-EMAR_SEARCH-', font=(welcome_screen.FONT, 11)), sg.Text(text="", expand_x=True)]
    ]

    combined_layout = sections + bottom_layout
    #print(combined_layout)

    # Create a scrollable container for the combined layout
    scrollable_layout = sg.Column(combined_layout, scrollable=True, vertical_scroll_only=True, size=(750, 695))  # Adjust the size as needed

    # Return the scrollable layout
    return [[scrollable_layout]]


# if __name__ == "__main__":
#     # Create the eMAR tab layout for a specific resident
#     eMAR_tab_layout = get_emar_tab_layout("Resident Name")
#     eMAR_tab = sg.Tab('eMAR Management', eMAR_tab_layout)  # Create the eMAR tab with the layout

#     # Create the window with the eMAR tab
#     window = sg.Window('Resident Management', [[sg.TabGroup([[eMAR_tab]])]], finalize=True)

#     # Event Loop
#     while True:
#         event, values = window.read()
#         if event == sg.WIN_CLOSED:
#             break

#     window.close()
