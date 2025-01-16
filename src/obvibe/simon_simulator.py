"""
This is a temporary modeule which will be used to generate ontologized JSON-LD file from the Excel file. 
Eventually, I would like to import this from BattInfoConverter, but as of today (22.11.2024) I still need to fix it and I have not yet made it a module.
So, I cannot directly import library from it. So, I will just be copying the required functions from that library and used it here.
This is just a temporary solution and meant to show the proof of concept for my automate Cucumber json to OpenBis with JSON-LD file generation.
After I fix the issue with BattInfoConverter, I will import the library from there.
The code here is from NukP/BattInfoConverter form commit a8cb3fd732a3bf0604e7042bef8bb6d0dda1578a, version 0.8.0 
"""
from dataclasses import dataclass, field
import pandas as pd
import numpy as np 
import datetime
import traceback
import inspect
from pandas import DataFrame
from typing import Any, Optional

APP_VERSION = "1.0.0"

@dataclass
class ExcelContainer:
    excel_file: str
    data: dict = field(init=False)

    def __post_init__(self):
        excel_data = pd.ExcelFile(self.excel_file)
        self.data = {
            "schema": pd.read_excel(excel_data, 'Schema'),
            "unit_map": pd.read_excel(excel_data, 'Ontology - Unit'),
            "context_toplevel": pd.read_excel(excel_data, '@context-TopLevel'),
            "context_connector": pd.read_excel(excel_data, '@context-Connector'),
            "unique_id": pd.read_excel(excel_data, 'Unique ID')
        }

def get_information_value(df: DataFrame, row_to_look: str, col_to_look: str = "Value", col_to_match: str = "Metadata") -> str | None:
    """
    Retrieves the value from a specified column where a different column matches a given value.

    Parameters:
    df (DataFrame): The DataFrame to search within.
    row_to_look (str): The value to match within the column specified by col_to_match.
    col_to_look (str): The name of the column from which to retrieve the value. Default is "Key".
    col_to_match (str): The name of the column to search for row_to_look. Default is "Item".

    Returns:
    str | None: The value from the column col_to_look if a match is found; otherwise, None.
    """
    if row_to_look.endswith(' '):  # Check if the string ends with a space
        row_to_look = row_to_look.rstrip(' ')  # Remove only trailing spaces
    result = df.query(f"{col_to_match} == @row_to_look")[col_to_look]
    return result.iloc[0] if not result.empty else None


def create_jsonld_with_conditions(data_container: ExcelContainer) -> dict:
    """
    Creates a JSON-LD structure based on the provided data container containing schema and context information.

    This function extracts necessary information from the schema and context sheets of the provided
    `ExcelContainer` to generate a JSON-LD object. It performs validation on required fields, handles
    ontology links, and structures data in compliance with the EMMO domain for battery context.

    Args:
        data_container (ExcelContainer): A datalcass container with data extracted from the input Excel schema required for generating JSON-LD,
            including schema, context, and unique identifiers.

    Returns:
        dict: A JSON-LD dictionary representing the structured information derived from the input data.

    Raises:
        ValueError: If required fields are missing or have invalid data in the schema or unique ID sheets.
    """
    schema = data_container.data['schema']
    context_toplevel = data_container.data['context_toplevel']
    context_connector = data_container.data['context_connector']

    #Harvest the information for the required section of the schemas
    ls_info_to_harvest = [
    "Cell type", 
    "Cell ID", 
    "Date of cell assembly", 
    "Institution/company",
    "Scientist/technician/operator" 
    ]

    dict_harvested_info = {}

    #Harvest the required value from the schema sheet. 
    for field in ls_info_to_harvest:
        if get_information_value(df=schema, row_to_look=field) is np.nan:
            raise ValueError(f"Missing information in the schema, please fill in the field '{field}'")
        else:
            dict_harvested_info[field] = get_information_value(df=schema, row_to_look=field)

    #Harvest unique ID value for the required value from the schema sheet.
    ls_id_info_to_harvest = [ "Institution/company", "Scientist/technician/operator"]
    dict_harvest_id = {}
    for id in ls_id_info_to_harvest:
        try:
            dict_harvest_id[id] = get_information_value(df=data_container.data['unique_id'],
                                                        row_to_look=dict_harvested_info[id],
                                                        col_to_look = "ID",
                                                        col_to_match="Item")
            if dict_harvest_id[id] is None:
                raise ValueError(f"Missing unique ID for the field '{id}'")
        except:
            raise ValueError(f"Missing unique ID for the field '{id}'")

    jsonld = {
        "@context": ["https://w3id.org/emmo/domain/battery/context", {}],
        "@type": dict_harvested_info['Cell type'],
        "schema:version": get_information_value(df=schema, row_to_look='BattINFO CoinCellSchema version'),
        "schema:productID": dict_harvested_info['Cell ID'],
        "schema:dateCreated": dict_harvested_info['Date of cell assembly'],
        "schema:creator": {
                            "@type": "schema:Person",
                            "@id": dict_harvest_id['Scientist/technician/operator'],
                            "schema:name": dict_harvested_info['Scientist/technician/operator']
                            },
        "schema:manufacturer": {
                            "@type": "schema:Organization",
                            "@id": dict_harvest_id['Institution/company'],
                            "schema:name": dict_harvested_info['Institution/company']
                            },
        "rdfs:comment": {}
    }

    for _, row in context_toplevel.iterrows():
        jsonld["@context"][1][row['Item']] = row['Key']

    connectors = set(context_connector['Item'])

    for _, row in schema.iterrows():
        if pd.isna(row['Value']) or row['Ontology link'] == 'NotOntologize':
            continue
        if row['Ontology link'] == 'Comment':
            jsonld["rdfs:comment"] = f"{row['Metadata']}: {row['Value']}"
            continue

        ontology_path = row['Ontology link'].split('-')

        # Handle schema:productID specifically
        if 'schema:productID' in row['Ontology link']:
            product_id = str(row['Value']).strip()  # Ensure the value is treated as a string
            # Explicitly assign the value to avoid issues with add_to_structure
            current = jsonld
            for key in ontology_path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[ontology_path[-1]] = product_id
            continue

        # Handle schema:manufacturer entries
        if 'schema:manufacturer' in row['Ontology link']:
            manufacturer_entry = {
                "@type": "schema:Organization",
                "schema:name": row['Value']
            }
            # Add manufacturer entry to the structure
            if ontology_path[0] not in jsonld:
                jsonld[ontology_path[0]] = {}
            jsonld[ontology_path[0]]["schema:manufacturer"] = manufacturer_entry
            continue

        # Default behavior for other entries
        if pd.isna(row['Unit']):
            raise ValueError(
                f"The value '{row['Value']}' is filled in the wrong row, please check the schema"
            )
        add_to_structure(jsonld, ontology_path, row['Value'], row['Unit'], data_container)


    jsonld["rdfs:comment"] = f"BattINFO Converter version: {APP_VERSION}"
    jsonld["rdfs:comment"] = f"Software credit: This JSON-LD was created using BattINFO converter (https://battinfoconverter.streamlit.app/) version: {APP_VERSION} and the coin cell battery schema version: {jsonld['schema:version']}, this web application was developed at Empa, Swiss Federal Laboratories for Materials Science and Technology in the Laboratory Materials for Energy Conversion"
    
    return jsonld

def convert_excel_to_jsonld(excel_file: ExcelContainer):
    print('*********************************************************')
    print(f"Initialize new session of Excel file conversion, started at {datetime.datetime.now()}")
    print('*********************************************************')
    data_container = ExcelContainer(excel_file)

    # Generate JSON-LD using the data container
    jsonld_output = create_jsonld_with_conditions(data_container)
    

    return jsonld_output

def add_to_structure(jsonld: dict, path: list[str], value: Any, unit: str, data_container: 'ExcelContainer') -> None:
    """
    Adds a value to a JSON-LD structure at a specified path, incorporating units and other contextual information.

    This function processes a path to traverse or modify the JSON-LD structure and handles special cases like 
    measured properties, ontology links, and unique identifiers. It uses data from the provided `ExcelContainer` 
    to resolve unit mappings and context connectors.

    Args:
        jsonld (dict): The JSON-LD structure to modify.
        path (list[str]): A list of strings representing the hierarchical path in the JSON-LD where the value should be added.
        value (any): The value to be inserted at the specified path.
        unit (str): The unit associated with the value. If 'No Unit', the value is treated as unitless.
        data_container (ExcelContainer): An instance of the `ExcelContainer` dataclass (from son_convert module) containing supporting data 
                                         for unit mappings, connectors, and unique identifiers.

    Returns:
        None: This function modifies the JSON-LD structure in place.

    Raises:
        ValueError: If the value is invalid, a required unit is missing, or an error occurs during path processing.
        RuntimeError: If any unexpected error arises while processing the value and path.
    """
    try:
        print('               ')  # Debug separator
        current_level = jsonld
        unit_map = data_container.data['unit_map'].set_index('Item').to_dict(orient='index')
        context_connector = data_container.data['context_connector']
        connectors = set(context_connector['Item'])
        unique_id = data_container.data['unique_id']

        # Skip processing if value is invalid
        if not value or pd.isna(value):
            print(f"Skipping empty value for path: {path}")
            return

        for idx, parts in enumerate(path):
            if len(parts.split('|')) == 1:
                part = parts
                special_command = None
                plf(value, part)

            elif "type|" in parts:
                # Handle "type|" special command
                _, type_value = parts.split('|', 1)
                plf(value, type_value)

                # Assign type value only if it's valid
                if type_value:
                    current_level["@type"] = type_value
                plf(value, type_value, current_level=current_level)
                continue

            elif len(parts.split('|')) == 2:
                special_command, part = parts.split('|')
                plf(value, part)
                if special_command == "rev":
                    plf(value, part)
                    if "@reverse" not in current_level:
                        plf(value, part)
                        current_level["@reverse"] = {}
                    current_level = current_level["@reverse"]
                    plf(value, part)

            else:
                raise ValueError(f"Invalid JSON-LD at: {parts} in {path}")

            is_last = idx == len(path) - 1
            is_second_last = idx == len(path) - 2

            if part not in current_level:
                if value or unit:  # Only add the part if value or unit exists
                    plf(value, part)
                    if part in connectors:
                        connector_type = context_connector.loc[context_connector['Item'] == part, 'Key'].values[0]
                        if pd.isna(connector_type):
                            current_level[part] = {}
                        else:
                            current_level[part] = {"@type": connector_type}
                    else:
                        current_level[part] = {}

            # Handle unit-based measured properties
            if is_second_last and unit != 'No Unit':
                if pd.isna(unit):
                    raise ValueError(f"The value '{value}' is missing a valid unit.")
                unit_info = unit_map.get(unit, {})
                new_entry = {
                    "@type": path[-1],
                    "hasNumericalPart": {
                        "@type": "emmo:Real",
                        "hasNumericalValue": value
                    },
                    "hasMeasurementUnit": unit_info.get('Key', 'UnknownUnit')
                }
                if isinstance(current_level.get(part), list):
                    current_level[part].append(new_entry)
                else:
                    current_level[part] = new_entry
                break

            # Handle final value assignment
            if is_last and unit == 'No Unit':
                if value in unique_id['Item'].values:
                    unique_id_of_value = get_information_value(
                        df=unique_id, row_to_look=value, col_to_look="ID", col_to_match="Item"
                    )
                    if not pd.isna(unique_id_of_value):  # Only assign if the ID is valid
                        current_level["@id"] = unique_id_of_value
                    current_level["@type"] = value
                elif value:
                    current_level["rdfs:comment"] = value
                break

            current_level = current_level[part]

    except Exception as e:
        traceback.print_exc()  # Print the full traceback
        raise RuntimeError(f"Error occurred with value '{value}' and path '{path}': {str(e)}")


def plf(value, part, current_level = None, debug_switch = True):
    """Print Line Function.
    This function is used for debugging.
    """
    if debug_switch:
        current_frame = inspect.currentframe()
        line_number = current_frame.f_back.f_lineno
        if current_level is not None:
            print(f'pass line {line_number}, value:', value,'AND part:', part, 'AND current_level:', current_level)
        else:
            print(f'pass line {line_number}, value:', value,'AND part:', part)
    else:
        pass 
