import db_functions
import PySimpleGUI as sg
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


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

# medications_data = db_functions.fetch_medications_for_resident('Dirty Diana')
# create_medication_list_pdf('Dirty Diana', medications_data)


