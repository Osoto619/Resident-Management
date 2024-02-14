import db_functions
import PySimpleGUI as sg
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter,inch, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import calendar


# def create_medication_schedule_pdf(resident_name, medications_data):
#     pdf_name = f"{resident_name}_Medication_Schedule.pdf"
#     doc = SimpleDocTemplate(pdf_name, pagesize=letter)
#     elements = []
#     styleSheet = getSampleStyleSheet()

#     # Add title
#     title = Paragraph(f"Medication Schedule for {resident_name}", styleSheet['Title'])
#     elements.append(title)
#     elements.append(Spacer(1, 12))

#     # For each timeslot, generate a section in the PDF
#     for timeslot, med_info in medications_data['Scheduled'].items():
#         elements.append(Paragraph(timeslot, styleSheet['Heading2']))
#         # Prepare data for table
#         data = [['Medication', 'Dosage', 'Instructions']]
#         for med_name, details in med_info.items():
#             data.append([med_name, details['dosage'], details['instructions']])
#         # Create table
#         table = Table(data, [120, 120, 240])
#         table.setStyle(TableStyle([
#             ('GRID', (0,0), (-1,-1), 1, colors.black),
#             ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
#             ('BACKGROUND', (0,0), (-1,0), colors.grey),
#         ]))
#         elements.append(table)
#         elements.append(Spacer(1, 12))

#     # Add sections for PRN and Controlled medications similarly, if required

#     doc.build(elements)
#     print(f"PDF generated: {pdf_name}")

def create_medication_list_pdf(resident_name, medications_data):
    pdf_name = f"{resident_name}_Medication_Schedule.pdf"
    doc = SimpleDocTemplate(pdf_name, pagesize=letter)
    elements = []
    styleSheet = getSampleStyleSheet()

    # Add title
    title = Paragraph(f"Medication List for {resident_name}", styleSheet['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Scheduled Medications
    if medications_data['Scheduled']:
        for timeslot, med_info in medications_data['Scheduled'].items():
            elements.append(Paragraph(timeslot, styleSheet['Heading2']))
            data = [['Medication', 'Dosage', 'Instructions']]
            for med_name, details in med_info.items():
                data.append([med_name, details['dosage'], details['instructions']])
            table = Table(data, [120, 120, 240])
            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))

    # PRN Medications
    if medications_data['PRN']:
        elements.append(Paragraph("PRN (As Needed)", styleSheet['Heading2']))
        data = [['Medication', 'Dosage', 'Instructions']]
        for med_name, details in medications_data['PRN'].items():
            data.append([med_name, details['dosage'], details['instructions']])
        table = Table(data, [120, 120, 240])
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    # Controlled Medications
    if medications_data['Controlled']:
        elements.append(Paragraph("Controlled Medications", styleSheet['Heading2']))
        data = [['Medication', 'Dosage', 'Instructions', 'Form']]
        for med_name, details in medications_data['Controlled'].items():
            data.append([med_name, details['dosage'], details['instructions'], details['form']])
        table = Table(data, [150, 80, 180, 60])
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    doc.build(elements)
    sg.Popup('Medication List PDF Created!')


def generate_adl_chart_pdf(resident_name, year_month, adl_data):
    pdf_name = f"{resident_name}_ADL_Chart_{year_month}.pdf"
    doc = SimpleDocTemplate(pdf_name, pagesize=landscape(letter), topMargin=20, leftMargin=36, rightMargin=36, bottomMargin=36)
    elements = []
    
    # Styles for the document
    styles = getSampleStyleSheet()
    title_style = styles['Title']

    # Adding a title at the top of the document
    title = f"ADL Chart {resident_name} - {year_month}"
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 8))  # Adding some space after the title

    # Days of the month as column headers
    days_in_month = calendar.monthrange(int(year_month.split('-')[0]), int(year_month.split('-')[1]))[1]
    headers = ["ADL Activity"] + [str(day) for day in range(1, days_in_month + 1)]
    
    # ADL Activities as row headers
    adl_activities = [
        "First Shift SP", "Second Shift SP", "First Shift Activity 1", "First Shift Activity 2",
        "First Shift Activity 3", "Second Shift Activity 4", "First Shift BM", "Second Shift BM",
        "Shower", "Shampoo", "Sponge Bath", "Peri Care AM", "Peri Care PM",
        "Oral Care AM", "Oral Care PM", "Nail Care", "Skin Care", "Shave",
        "Breakfast", "Lunch", "Dinner", "Snack AM", "Snack PM", "Water Intake"
    ]
    
    # Initialize table data
    table_data = [headers]  # Adding the headers as the first row
    
    # Filling the table with ADL activities and placeholders for each day's data
    for activity in adl_activities:
        row = [activity] + ['' for _ in range(days_in_month)]  # Placeholder for each day
        table_data.append(row)
    
    # Update the table with actual ADL data
    for entry in adl_data:
        date = entry[2]  # Assuming this is where the date is
        day = int(date.split('-')[2]) - 1  # Convert date to day of month and adjust for 0 indexing
        for i, activity_data in enumerate(entry[3:]):  # Skip id, resident_id, and date
            if activity_data:  # If there's data for this activity, update the cell
                table_data[i + 1][day + 1] = activity_data  # +1 because of headers row
    
    # Creating the table
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    elements.append(table)

    # Add some space before the activities legend
    elements.append(Spacer(1, 6))

    # # Activities legend title
    # elements.append(Paragraph("Activities", styles['Heading3']))

    # Activities list
    activities = [
        "1. Movie & Snack or TV",
        "2. Exercise/Walking",
        "3. Games/Puzzles",
        "4. Outside/Patio",
        "5. Arts & Crafts",
        "6. Music Therapy",
        "7. Gardening",
        "8. Listen to Music",
        "9. Social Hour",
        "10. Cooking/Baking",
        "11. Birdwatching",
        "12. Outing/Excursion",
        "13. Hospice Visit",
        "14. Other as Listed on the Service Plan",
        "15. Social Media"
    ]

    # Calculate the number of activities in each column (assuming 3 columns with roughly equal distribution)
    num_per_column = len(activities) // 3 + (1 if len(activities) % 3 > 0 else 0)

    # Prepare data for the table, ensuring each row has three columns
    table_data = [activities[i:i+num_per_column] for i in range(0, len(activities), num_per_column)]
    # Ensure all rows have 3 columns (fill missing with empty strings)
    for row in table_data:
        while len(row) < 3:
            row.append("")

    # Create the table for activities legend
    activities_table = Table(table_data)
    activities_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        # Adjust paddings and spacing as necessary
        ('LEFTPADDING', (0,0), (-1,-1), 1),  # Reduced padding
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))

    # Add the table to the elements
    elements.append(activities_table)
    
    # Build and save the PDF
    doc.build(elements)
    print(f"PDF generated: {pdf_name}")
