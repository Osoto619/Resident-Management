import PySimpleGUI as sg
import adl_management
import emar_management
import info_management
import db_functions
from datetime import datetime
from adl_chart import show_adl_chart
from emars_chart import show_emar_chart
import welcome_screen


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


def main():
    resident_names = db_functions.get_resident_names()
    selected_resident = resident_names[0]
    current_tab_index = 0  # Initialize the tab index

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
            db_functions.save_adl_data_from_management_window(selected_resident, adl_data)
            sg.popup("Data saved successfully!")
        elif event == '-EMAR_SAVE-':
            emar_data = emar_management.retrieve_emar_data_from_window(window,selected_resident)
            
            db_functions.save_emar_data_from_management_window(emar_data)
            sg.popup("eMAR data saved successfully!")
        elif event == '-CURRENT_ADL_CHART-':
            # Get the current month and year
            current_month_year = datetime.now().strftime("%Y-%m")

            window.hide()
            # Call the show_adl_chart function with the selected resident and current month-year
            adl_management.show_adl_chart(selected_resident, current_month_year)
            window.un_hide()
        elif event == 'CURRENT_EMAR_CHART':
            # Get the current month and year
            current_month_year = datetime.now().strftime("%Y-%m")
            window.hide()
            show_emar_chart(selected_resident,current_month_year)
            window.un_hide()
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
            print(month_year)
            if db_functions.does_emars_chart_data_exist(selected_resident, month_year):
                window.hide()
                show_emar_chart(selected_resident, month_year)
                window.un_hide()
            else:
                sg.popup("No eMARs Chart Data Found for the Specified Month and Resident")
        elif event == '-ADD_MEDICATION-':
            window.close()
            add_med_win = emar_management.add_medication_window(selected_resident)
            window = create_management_window(resident_names,selected_resident, default_tab_index=1)
        elif event.startswith('-ADMIN_'):
            medication_name = event.split('_')[-1]
            medication_name = medication_name[:-1]
            emar_management.open_administer_window(selected_resident, medication_name)
        elif event == '-INFO_WINDOW-':
            window.hide()
            info_management.open_resident_info_window(selected_resident)
            window.un_hide()
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
