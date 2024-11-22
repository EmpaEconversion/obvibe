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

APP_VERSION = "0.8.0"

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

def get_information_value(df, row_to_look: str, col_to_look: str = "Value", col_to_match: str = "Metadata") -> str | None:
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


def create_jsonld_with_conditions(data_container: ExcelContainer):
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
        "schemas:productID": dict_harvested_info['Cell ID'],
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
            jsonld["rdfs:comment"][row['Metadata']] = row['Value']
            continue
        if pd.isna(row['Unit']):
            raise ValueError(f"The value '{row['Value']}' is filled in the wrong row, please check the schema")

        ontology_path = row['Ontology link'].split('-')
        add_to_structure(jsonld, ontology_path, row['Value'], row['Unit'], data_container)
    jsonld["rdfs:comment"]["BattINFO Converter version"] = APP_VERSION
    jsonld["rdfs:comment"]["Software credit"] = f"This JSON-LD was created using Battconverter (https://battinfoconverter.streamlit.app/) version: {APP_VERSION} and the schema version: {jsonld['schema:version']}, this web application was developed at Empa, Swiss Federal Laboratories for Materials Science and Technology in the Laboratory Materials for Energy Conversion lab"

    return jsonld

def convert_excel_to_jsonld(excel_file: ExcelContainer):
    print('*********************************************************')
    print(f"Initialize new session of Excel file conversion, started at {datetime.datetime.now()}")
    print('*********************************************************')
    data_container = ExcelContainer(excel_file)

    # Generate JSON-LD using the data container
    jsonld_output = create_jsonld_with_conditions(data_container)
    

    return jsonld_output

def add_to_structure(jsonld, path, value, unit, data_container):
    try:
        print('               ') # To add space between each Excel row - for debugging.
        current_level = jsonld
        unit_map = data_container.data['unit_map'].set_index('Item').to_dict(orient='index')
        context_connector = data_container.data['context_connector']
        connectors = set(context_connector['Item'])
        unique_id = data_container.data['unique_id']

        for idx, parts in enumerate(path):
            if len(parts.split('|')) == 1:
                part = parts
                special_command = None
                plf(value, part)
            elif len(parts.split('|')) == 2:
                special_command, part = parts.split('|')
                plf(value, part)
                if special_command == "rev":
                    plf(value, part)
                    if "@reverse" not in current_level:
                        plf(value, part)
                        current_level["@reverse"] = {}
                    current_level = current_level["@reverse"] ; plf(value, part)
                if special_command == "type":
                    plf(value, part)                   
                    current_level['type'] = part ; plf(value, part, current_level=current_level)
                    parts = parts[idx + 1] ; plf(value, part, current_level=current_level)
                    idx += 1 ; plf(value, part, current_level=current_level)
                    continue
            else:
                raise ValueError(f"Invalid JSON-LD at: {parts} in {path}")
            
            is_last = idx == len(path) - 1
            is_second_last = idx == len(path) - 2

            if part not in current_level:
                plf(value, part)
                if part in connectors:
                    plf(value, part)
                    connector_type = context_connector.loc[context_connector['Item'] == part, 'Key'].values[0]
                    if pd.isna(connector_type):
                        plf(value, part)
                        current_level[part] = {}
                    else:
                        plf(value, part)
                        current_level[part] = {"@type": connector_type}
                else:
                    plf(value, part)
                    current_level[part] = {}
            
            #Handle the case of the single path.
            if len(path) == 1 and unit == 'No Unit':
                plf(value, part)
                if value in unique_id['Item'].values:
                    plf(value, part)
                    if "@type" in current_level:
                        plf(value, part)
                        if "@type" in current_level[part] and isinstance(current_level[part]["@type"], list):
                            plf(value, part)
                            if not pd.isna(value):
                                plf(value, part)
                                current_level[part]["@type"].append(value)
                        else:
                            plf(value, part)
                            if not pd.isna(value):
                                plf(value, part)
                                current_level[part]["@type"] = [value]
                    else:
                        plf(value, part)
                        if not pd.isna(value):
                            plf(value, part)
                            current_level[part]["@type"] = value
                else:
                    plf(value, part)
                    current_level[part]['rdfs:comment'] = value
                break

            if is_second_last and unit != 'No Unit':
                plf(value, part)
                if pd.isna(unit):
                    plf(value, part)
                    raise ValueError(f"The value '{value}' is filled in the wrong row, please check the schema")
                unit_info = unit_map[unit] ; plf(value, part)

                new_entry = {
                    "@type": path[-1],
                    "hasNumericalPart": {
                        "@type": "emmo:Real",
                        "hasNumericalValue": value
                    },
                    "hasMeasurementUnit": unit_info['Key']
                }
                
                # Check if the part already exists and should be a list
                if part in current_level:
                    plf(value, part)
                    if isinstance(current_level[part], list):
                        current_level[part].append(new_entry) ;plf(value, part)
                    else:
                        # Ensure we do not overwrite non-dictionary values
                        existing_entry = current_level[part] ;plf(value, part)
                        current_level[part] = [existing_entry, new_entry]
                else:
                    current_level[part] = [new_entry] ;plf(value, part)
                
                # Clean up any empty dictionaries in the list
                if isinstance(current_level[part], list):
                    current_level[part] = [item for item in current_level[part] if item != {}] ;plf(value, part)
                break

            if is_last and unit == 'No Unit':
                plf(value, part)
                if value in unique_id['Item'].values:
                    plf(value, part)
                    if "@type" in current_level:
                        plf(value, part)
                        if isinstance(current_level["@type"], list):
                            plf(value, part)
                            if not pd.isna(value):
                                current_level["@type"].append(value) ; plf(value, part)
                        else:
                            plf(value, part)
                            if not pd.isna(value):
                                current_level["@type"] = [current_level["@type"], value] ; plf(value, part)
                    else:
                        if not pd.isna(value):
                            current_level["@type"] = value ; plf(value, part)
                else:
                    current_level['rdfs:comment'] = value ; plf(value, part)
                break

            current_level = current_level[part]

            if not is_last and part in connectors:
                connector_type = context_connector.loc[context_connector['Item'] == part, 'Key'].values[0] ; plf(value, part)
                if not pd.isna(connector_type):
                    plf(value, part)
                    if "@type" not in current_level:
                        current_level["@type"] = connector_type ; plf(value, part)
                    elif current_level["@type"] != connector_type:
                        plf(value, part)
                        if isinstance(current_level["@type"], list):
                            plf(value, part)
                            if connector_type not in current_level["@type"]:
                                current_level["@type"].append(connector_type) ; plf(value, part)
                        else:
                            current_level["@type"] = [current_level["@type"], connector_type] ; plf(value, part)

            if is_second_last and unit == 'No Unit':
                next_part = path[idx + 1] ; plf(value, part)
                if isinstance(current_level, dict): 
                    plf(value, part, current_level=current_level)
                    if next_part not in current_level:
                        current_level[next_part] = {} ; plf(value, part)
                    current_level = current_level[next_part]
                elif isinstance(current_level, list):
                    current_level.append({next_part: {}}) ; plf(value, part)
                    current_level = current_level[-1][next_part]

                if value in unique_id['Item'].values:
                    unique_id_of_value = get_information_value(df=unique_id, row_to_look=value, col_to_look = "ID", col_to_match="Item") ; plf(value, part)
                    if not pd.isna(unique_id_of_value):
                        current_level['@id'] = unique_id_of_value ; plf(value, part)
                    
                    if not pd.isna(value):
                        plf(value, part, current_level=current_level)
                        if "@type" in current_level:
                            plf(value, part)
                            if isinstance(current_level["@type"], list):
                                current_level["@type"].append(value) ; plf(value, part)
                            else:
                                current_level["@type"] = [current_level["@type"], value] ; plf(value, part)
                        else:
                            current_level["@type"] = value ; plf(value, part)
                else:
                    current_level['rdfs:comment'] = value ; plf(value, part)
                break

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
