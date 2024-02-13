import PySimpleGUI as sg
import adl_management
import emar_management
import info_management
import db_functions
from datetime import datetime
from adl_chart import show_adl_chart
from emars_chart import show_emar_chart
import welcome_screen
import config
import med_lists


def create_tab_layout(resident_name):
    adl_tab_layout = adl_management.get_adl_tab_layout(resident_name)
    emar_tab_layout = emar_management.get_emar_tab_layout(resident_name)
    resident_info_layout = [[sg.Button(button_text='Enter Resident Info Window', key='-INFO_WINDOW-')]]

    adl_tab = sg.Tab('ADL', adl_tab_layout)
    emar_tab = sg.Tab('eMAR', emar_tab_layout)
    resident_info_tab = sg.Tab('Resident Info', resident_info_layout)

    return [adl_tab, emar_tab, resident_info_tab]


def create_management_window(resident_names, selected_resident, default_tab_index=0):
    resident_selector = sg.Combo(resident_names, default_value=selected_resident, key='-RESIDENT-', readonly=True, enable_events=True, font=('Helvetica', 11))

    tabs = create_tab_layout(selected_resident)
    tab_group = sg.TabGroup([tabs], key='-TABGROUP-', font=(welcome_screen.FONT, 11))

    current_date = datetime.now().strftime("%m-%d-%y")  # Get today's date

    layout = [
        [sg.Text('CareTech Resident Management', font=(db_functions.get_user_font(), 20), justification='center', expand_x=True, pad=((0, 0),(20,0)))],
        [sg.Text(text='', expand_x=True), sg.Text(current_date, key='-DATE-', font=(welcome_screen.FONT, 15)), sg.Text('' ,key='-TIME-', font=(welcome_screen.FONT, 15)), sg.Text(text='', expand_x=True)],
        [sg.Text('Select Resident:', font=(welcome_screen.FONT, 14)), resident_selector],
        [tab_group],
        [sg.Text('', expand_x=True), sg.Column(layout=[[sg.Button('Next Tab', font=(welcome_screen.FONT, 11)), sg.Button('Previous Tab', font=(welcome_screen.FONT, 11), pad=10)]]), sg.Text('', expand_x=True)]
    ]

    window = sg.Window('CareTech Resident Management', layout, finalize=True)

    # Select the default tab
    window['-TABGROUP-'].Widget.select(default_tab_index)

    return window


def open_discontinue_medication_window(resident_name):
    # Fetch the list of medications for the resident
    medications = db_functions.fetch_medications_for_resident(resident_name)
    discontinued_medications = db_functions.fetch_discontinued_medications(resident_name).keys()
    
    # Extracting medication names from both Scheduled and PRN categories
    scheduled_meds = [med_name for time_slot in medications['Scheduled'].values() for med_name in time_slot]
    prn_meds = list(medications['PRN'].keys())
    control_meds = list(medications['Controlled'].keys())
    

    # Combine both lists
    all_meds = scheduled_meds + prn_meds + control_meds
    # Remove Duplicates From Scheduled Medications
    unique = set(all_meds)
    # print(unique)
    unique_list = list(unique)

    # Exclude discontinued medications
    active_meds = [med for med in unique_list if med not in discontinued_medications]


    # Check if there are medications to discontinue
    if not medications:
        sg.popup("No medications available to discontinue for this resident.")
        return

    layout = [
        [sg.Text("Select Medication to Discontinue:", font=(db_functions.get_user_font, 14)), sg.Combo(active_meds, key='-MEDICATION-', readonly=True, font=(db_functions.get_user_font, 14))],
        [sg.Text("Discontinue Date (YYYY-MM-DD):", font=(db_functions.get_user_font, 14)), sg.Input(key='-DISCONTINUE_DATE-', size=17, font=(db_functions.get_user_font, 14)), 
         sg.CalendarButton("Select Date", target='-DISCONTINUE_DATE-', format='%Y-%m-%d', font=(db_functions.get_user_font, 13))],
        [sg.Text('', expand_x=True), sg.Submit("Discontinue", font=(db_functions.get_user_font, 13)), sg.Cancel(font=(db_functions.get_user_font, 13)), sg.Text('', expand_x=True)]
    ]

    window = sg.Window("Discontinue Medication", layout, modal=True)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Discontinue':
            medication = values['-MEDICATION-']
            discontinue_date = values['-DISCONTINUE_DATE-']
            if not medication or not discontinue_date:
                sg.popup("Please select a medication and a discontinue date.")
                continue

            # Add logic to update the database for discontinuing the medication
            db_functions.discontinue_medication(resident_name, medication, discontinue_date)
            sg.popup(f"Medication '{medication}' has been discontinued as of {discontinue_date}.")
            break

    window.close()


def main():
    resident_names = db_functions.get_resident_names()
    selected_resident = resident_names[0]
    current_tab_index = 0  # Initialize the tab index
    logged_in_user = config.global_config['logged_in_user']
    user_initials = db_functions.get_user_initials(logged_in_user)
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    window = create_management_window(resident_names, selected_resident)

    while True:
        event, values = window.read(timeout=1000)
        if event == sg.WIN_CLOSED:
            break
        elif event == '-RESIDENT-':
            window.close()
            selected_resident = values['-RESIDENT-']
            window = create_management_window(resident_names, selected_resident)
        elif event == '-ADL_SAVE-':
            adl_data = adl_management.retrieve_adl_data_from_window(window,selected_resident)
            existing_adl_data = db_functions.fetch_adl_data_for_resident_and_date(selected_resident,current_date)
            audit_description = adl_management.generate_adl_audit_description(adl_data, existing_adl_data)

            db_functions.save_adl_data_from_management_window(selected_resident, adl_data)
            db_functions.log_action(logged_in_user, f'ADL Data Saved Resident: {selected_resident}', audit_description)
            sg.popup("Data saved successfully!")
        elif event.startswith('-CHECK'): # Checkbox for Scheduled Medications IputText
             
             # Split the event string
             event_parts = event.split('_')
             # Combine the necessary parts to form the medication name and time slot
             med_name = '_'.join(event_parts[1:-1])
             time_slot = event_parts[-1]
             given_key = f'-GIVEN_{med_name}_{time_slot}' # time_slot adds the ending '-'
                
             # Check the state of the checkbox
             if values[event]:  # If checked
                 window[given_key].update(value=user_initials)  # Update with user initials
             else:  # If unchecked
                 window[given_key].update(value='')  # Clear the input box
        elif event == '-EMAR_SAVE-':
            emar_data = emar_management.retrieve_emar_data_from_window(window, selected_resident)
            audit_description = emar_management.compare_emar_data_and_log_changes(emar_data, selected_resident, current_date)
            db_functions.save_emar_data_from_management_window(emar_data)
            logged_in_user = config.global_config['logged_in_user']
            db_functions.log_action(logged_in_user, f'eMAR Data Saved Resident: {selected_resident}', audit_description)
            sg.popup("eMAR data saved successfully!")
        elif event == '-CURRENT_ADL_CHART-':
            # Get the current month and year
            current_month_year = datetime.now().strftime("%Y-%m")
            window.hide()
            # Call the show_adl_chart function with the selected resident and current month-year
            adl_management.show_adl_chart(selected_resident, current_month_year)
            window.un_hide()
        elif event.startswith('CHECK'): # Checkbox for ADL InputText
            key = event.replace('CHECK_', '')
            # Check the state of the checkbox
            if values[event]:  # If checked
                window[key].update(value=user_initials)
            else:  # If unchecked
                 window[key].update(value='')  # Clear the input box
        elif event == 'CURRENT_EMAR_CHART':
            # Get the current month and year
            current_month_year = datetime.now().strftime("%Y-%m")
            window.hide()
            show_emar_chart(selected_resident,current_month_year)
            window.un_hide()
        elif event == '-MED_LIST-':
            medication_data = db_functions.fetch_medications_for_resident(selected_resident)
            med_lists.create_medication_list_pdf(selected_resident, medication_data)
        elif event == '-ADL_SEARCH-':
            # year_month should be in the format 'YYYY-MM'
            month = values['-ADL_MONTH-'].zfill(2)
            year = values['-ADL_YEAR-']
            month_year = f'{year}-{month}'
            print(month_year)
            if db_functions.does_adl_chart_data_exist(selected_resident, month_year):
                window.hide()
                show_adl_chart(selected_resident, month_year)
                window.un_hide()
            else:
                sg.popup("No ADL Chart Data Found for the Specified Month and Resident")
        elif event == '-EMAR_SEARCH-':
            # year_month should be in the format 'YYYY-MM'
            month = values['-EMAR_MONTH-'].zfill(2)
            year = values['-EMAR_YEAR-']
            month_year = f'{year}-{month}'
            if db_functions.does_emars_chart_data_exist(selected_resident, month_year):
                window.hide()
                show_emar_chart(selected_resident, month_year)
                window.un_hide()
            else:
                sg.popup("No eMARs Chart Data Found for the Specified Month and Resident")
        elif event == '-ADD_MEDICATION-':
            window.close()
            emar_management.add_medication_window(selected_resident)
            window = create_management_window(resident_names,selected_resident, default_tab_index=1)
        elif event == '-EDIT_MEDICATION-':
            window.close()
            edit_med_win = emar_management.edit_medication_window(selected_resident)
            window = create_management_window(resident_names,selected_resident, default_tab_index=1)
        elif event == '-ADD_NON-MEDICATION-':
            window.close()
            emar_management.add_non_medication_order_window(selected_resident)
            window = create_management_window(resident_names,selected_resident, default_tab_index=1)
        elif event == '-EDIT_NON_MEDICATION-':
            window.close()
            emar_management.edit_non_med_order_window(selected_resident)
            window = create_management_window(resident_names,selected_resident, default_tab_index=1)
        elif event == '-NON_MEDICATION_ORDERS-':
            window.hide()
            emar_management.open_non_med_orders_window(selected_resident)
            window.un_hide()
        elif event.startswith('-ADMIN_'):
            med_type = event.split('_')[1]
            medication_name = event.split('_')[-1][:-1]  # Remove the last character which is a '-'
            if med_type == 'PRN':
                emar_management.prn_administer_window(selected_resident, medication_name)
            elif med_type == 'CONTROLLED':
                count, form = db_functions.get_controlled_medication_count_and_form(selected_resident, medication_name)
                emar_management.controlled_administer_window(selected_resident,medication_name, count, form)
        elif event.startswith('-PERFORM_NON_MED_'):
            order_name = event.split('_')[-1][:-1]  # Remove the last character which is a '-'
            window.close()
            emar_management.perform_non_med_order_window(selected_resident,order_name)
            window = create_management_window(resident_names,selected_resident, default_tab_index=1)

        elif event == '-INFO_WINDOW-':
            window.hide()
            info_management.open_resident_info_window(selected_resident)
            window.un_hide()
        elif event == '-DC_MEDICATION-':
            # Fetch the list of medications for the resident
            medications = db_functions.fetch_medications_for_resident(selected_resident)
            discontinued_medications = db_functions.fetch_discontinued_medications(selected_resident).keys()
            
            # Extracting medication names from both Scheduled and PRN categories
            scheduled_meds = [med_name for time_slot in medications['Scheduled'].values() for med_name in time_slot]
            prn_meds = list(medications['PRN'].keys())

            # Combine both lists
            all_meds = scheduled_meds + prn_meds
            # Remove Duplicates From Scheduled Medications
            unique = set(all_meds)
            # print(unique)
            unique_list = list(unique)

            # Exclude discontinued medications
            active_meds = [med for med in unique_list if med not in discontinued_medications]
            if len(active_meds) > 0:
                open_discontinue_medication_window(selected_resident)
            else:
                sg.popup('No Active Medications to Discontinue Available')
            
        # Handling 'Next Tab' and 'Previous Tab' button events
        if event in ['Next Tab', 'Previous Tab']:
            if event == 'Next Tab':
                current_tab_index = (current_tab_index + 1) % 3  # Assuming 3 tabs
            elif event == 'Previous Tab':
                current_tab_index = (current_tab_index - 1) % 3  # Assuming 3 tabs

            window.close()
            window = create_management_window(resident_names, selected_resident)
            window['-TABGROUP-'].Widget.select(current_tab_index)

        adl_management.update_clock(window)

    window.close()


if __name__ == "__main__":
    main()
