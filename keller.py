"""
This module contain an axiliary functions
"""

import pybis

def make_new_property(
    openbis_object: pybis.Openbis,
    new_property_code: str,
    new_property_label: str,
    new_property_description: str,
    new_property_data_type: str,
    collection_type_code: str = 'battery_premise2'
) -> None:
    """
    Create a new property type in openBIS and assign it to a specified collection type.

    Parameters:
    openbis_object (Openbis): An authenticated instance of the openBIS API.
    new_property_code (str): The unique code for the new property type.
    new_property_label (str): The label for the new property type.
    new_property_description (str): A brief description of the new property type.
    new_property_data_type (str): The data type of the new property (e.g., 'VARCHAR', 'INTEGER').
    collection_type_code (str, optional): The code of the collection type to which the new property will be assigned.
                                          Defaults to 'battery_premise2'.

    Returns:
    None

    Raises:
    ValueError: If the specified collection type does not exist in openBIS.
    """
    # Create a new property type and save it
    new_property = openbis_object.new_property_type(
        code=new_property_code,
        label=new_property_label,
        description=new_property_description,
        dataType=new_property_data_type
    )
    new_property.save()

    # Retrieve the specified collection type
    collection_type = openbis_object.get_collection_type(collection_type_code)
    if collection_type is None:
        raise ValueError(f"Collection type '{collection_type_code}' does not exist in openBIS.")

    # Assign the newly created property to the collection type
    collection_type.assign_property(new_property_code)
    