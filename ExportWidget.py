import csv
import os
from docx import Document
from datetime import datetime
from PyQt5.QtWidgets import QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel

class ExportWidget(QWidget):
    def __init__(self, output_powers = []):
        super().__init__()
        self.output_powers = output_powers
        # Create buttons
        self.csv_button = QPushButton("Save to CSV")
        self.docx_button = QPushButton("Save to DOCX")
        self.csv_button.setToolTip("Save the data to a CSV file")
        self.docx_button.setToolTip("Save the data to a DOCX file")
        self.label = QLabel("Test Complete. Export sweep data?")
                
        # Connect signals
        self.csv_button.clicked.connect(self.save_csv)
        self.docx_button.clicked.connect(self.save_docx)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.csv_button)
        button_layout.addWidget(self.docx_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def set_output_powers(self, output_powers):
        self.output_powers = output_powers

    def save_csv(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv)")
        if file_name:
            self.save_to_csv(self.output_powers, file_name)

    def save_docx(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save DOCX File", "", "Word Documents (*.docx)")
        if file_name:
            self.save_to_docx(self.output_powers, file_name)

    def save_to_csv(self, filename=f"output_powers_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"):
        with open(filename, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Frequency", "Power"])
            for freq, power in self.output_powers:
                writer.writerow([freq, power])
                
    def save_to_docx(self, filename=f"output_powers_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.docx"):
        doc = Document()
        doc.add_heading("Frequency vs Power Table", level=1)

        # Create a table with rows equal to the number of data points + 1 for the header
        table = doc.add_table(rows=len(self.output_powers) + 1, cols=2)
        table.style = 'Table Grid'

        # Add headers
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Frequency"
        hdr_cells[1].text = "Power"

        # Add data to the table
        for idx, (freq, power) in enumerate(self.output_powers):
            row_cells = table.rows[idx + 1].cells
            row_cells[0].text = str(freq)
            row_cells[1].text = str(power)

        # Save the document
        doc.save(filename)
