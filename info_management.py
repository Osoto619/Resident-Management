import PySimpleGUI as sg
import resident_management

def open_resident_info_window(resident_name):
    # Create layouts for each tab
    personal_info_layout = [
        # Add components for personal info (e.g., name, date of birth, contact info)
    ]

    medical_info_layout = [
        # Add components for medical info (e.g., medical history, current conditions, medications)
    ]

    # More tabs can be added as needed
    other_info_layout = [
        # Add components for other relevant information
    ]

    # Create tab group
    tab_group_layout = [
        [sg.Tab('Personal Info', personal_info_layout)],
        [sg.Tab('Medical Info', medical_info_layout)],
        # Add more tabs as needed
        [sg.Tab('Other Info', other_info_layout)]
    ]

    # Create window layout
    layout = [
        [sg.TabGroup(tab_group_layout)],
        [sg.Button('Close')]
    ]

    # Create and event loop for the window
    window = sg.Window(f'Resident Information - {resident_name}', layout, modal=True)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Close':
            break

    window.close()




# Example usage
if __name__ == "__main__":
    open_resident_info_window("John Doe")
