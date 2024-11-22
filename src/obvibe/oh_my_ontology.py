"""
This module contains function desgined to handle ontology xlsx file generation and upload
"""

from openpyxl import load_workbook
import os
import shutil 
from . import pathfolio, keller

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

def gen_blank_metadata_xlsx(experiment_name: str, 
                            dir_template: str = r"K:\Aurora\nukorn_PREMISE_space\Battinfo_template.xlsx"):
    """
    Generate a blank metadata Excel file for a specific experiment based on a template.

    This Excel file will then be used as a metadata excel file used in generating a corresponding ontologized JSON-LD file. 

    Args:
        experiment_name (str): The name of the experiment to be used in naming the new Excel file.
        dir_template (str): The path to the template Excel file. Defaults to 
                            'K:\\Aurora\\nukorn_PREMISE_space\\Battinfo_template.xlsx'.

    Returns:
        None: Creates a new Excel file in the backup directory with the experiment name as part of the file name.
    """
    # Get the name of the new xlsx file
    new_xlsx_name = f"{experiment_name}_excel_for_ontology.xlsx"
    dir_xlsx_folder = r"K:\Aurora\nukorn_PREMISE_space\Backup for ontologized xlsx"
    dir_new_xlsx = os.path.join(dir_xlsx_folder, new_xlsx_name)
    # Copy the template file
    shutil.copy(dir_template, dir_new_xlsx)

def curate_metadata_dict(dir_json: str):
    """
    This function is used to come generate a dictionary that contain a metadata item and its value 

    This metadata will be used to fill an Excel file that will be used to generate an ontologized JSON-LD file.
    

    Args:
        dir_json (str): The directory of the analyzed JSON file.
    """
    dict_metadata = {}

    #Extract metadata from the analyzed json file. 
    for key, value in pathfolio.dict_excel_to_json.items():
        dict_metadata[key] = keller.get_metadata_from_json(dir_json, value)

    return dict_metadata

