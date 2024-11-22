"""
This module contains function desgined to handle ontology xlsx file generation and upload
"""

from openpyxl import load_workbook

def update_metadata_value(file_path, metadata, input_value, sheet_name="Schema"):
    """
    Update the value of a specified metadata key in an Excel sheet.

    Args:
        file_path (str): Path to the Excel file.
        metadata (str): The metadata key to search for.
        input_value (str): The new value to set.
        sheet_name (str): Name of the sheet to search in (default is "Schema").
    """
    try:
        # Load the workbook and select the specified sheet
        workbook = load_workbook(file_path)
        if sheet_name not in workbook.sheetnames:
            print(f"Sheet '{sheet_name}' not found in the workbook.")
            return

        sheet = workbook[sheet_name]

        # Find the row with the specified metadata and update the corresponding value
        for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=2):
            metadata_cell, value_cell = row
            if metadata_cell.value == metadata:
                value_cell.value = input_value
                print(f"Updated metadata '{metadata}' with value '{input_value}'.")
                break
        else:
            print(f"Metadata '{metadata}' not found in sheet '{sheet_name}'.")

        # Save the changes to the Excel file
        workbook.save(file_path)

    except Exception as e:
        print(f"An error occurred: {e}")

