import csv
import os
from docx import Document
from datetime import datetime
from PyQt5.QtWidgets import QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QMessageBox

class ExportWidget(QWidget):
    def __init__(self, field_strengths = []):
        super().__init__()
        self.field_levels = field_strengths
        # Create buttons
        self.evaluation_label = QLabel("Evaluation:", self)
        self.evaluation_input = QLineEdit(self)
        self.criteria_label = QLabel("Criteria:", self)
        self.criteria_input = QLineEdit(self)
        self.csv_button = QPushButton("Save to CSV")
        self.docx_button = QPushButton("Save to DOCX")
        self.cancel_button = QPushButton("Cancel")
        self.csv_button.setToolTip("Save the data to a CSV file")
        self.docx_button.setToolTip("Save the data to a DOCX file")
        self.label = QLabel("Test Complete. Export sweep data?")
                
        # Connect signals
        self.csv_button.clicked.connect(self.save_csv)
        self.docx_button.clicked.connect(self.save_docx)
        self.cancel_button.clicked.connect(self.close)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.evaluation_label)
        layout.addWidget(self.evaluation_input)
        layout.addWidget(self.criteria_label)
        layout.addWidget(self.criteria_input)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.csv_button)
        button_layout.addWidget(self.docx_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def set_output_powers(self, field_levels):
        self.field_levels = field_levels

    def save_csv(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv)")
        if file_name:
            try:
                with open(file_name, 'w') as file:
                    self.save_to_csv(self.field_levels, self.evaluation_input.text(), self.criteria_input.text(), file)
                QMessageBox.information(self, "Success", f"Text saved to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
        self.close()

    def save_docx(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save DOCX File", "", "Word Documents (*.docx)")
        if file_name:
            try:
                with open(file_name, 'w') as file:
                    self.save_to_docx(self.field_levels, self.evaluation_input.text(), self.criteria_input.text(), file)
                QMessageBox.information(self, "Success", f"Text saved to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
        self.close()

    def save_to_csv(self, field_levels, evaluation, criteria, filename=f"output_powers_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"):
        with open(filename, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Level", "Frequency MHz", "Voltage V/m", "Evaluation", "Criteria", "Spec.", "Result"])
            for freq, field in field_levels:
                writer.writerow([self.get_level(field), freq, field, evaluation, criteria, "A", ""])
                
    def save_to_docx(self, field_levels, evaluation, criteria, filename=f"output_powers_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.docx"):
        doc = Document()
        doc.add_heading("Radiated Immunity Data", level=1)

        # Create a table with rows equal to the number of data points + 1 for the header
        table = doc.add_table(rows=len(field_levels) + 1, cols=7)
        table.style = 'Table Grid'

        # Add headers
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Level"
        hdr_cells[1].text = "Frequency MHz"
        hdr_cells[2].text = "Voltage V/m"
        hdr_cells[3].text = "Evaluation"
        hdr_cells[4].text = "Criteria"
        hdr_cells[5].text = "Spec."
        hdr_cells[6].text = "Result"

        # Add data to the table
        for idx, (freq, field) in enumerate(field_levels):
            row_cells = table.rows[idx + 1].cells
            row_cells[0].text = self.get_level(field)
            row_cells[1].text = str(freq)
            row_cells[2].text = str(field)
            row_cells[3].text = evaluation
            row_cells[4].text = criteria
            row_cells[5].text = 'A'
            row_cells[6].text = ''

        # Save the document
        doc.save(filename)
        
    def get_level(self, field):
        if field < 2.5:
            return "1"
        elif field <= 6 and field >= 2.5:
            return "2"
        else:
            return "3"
