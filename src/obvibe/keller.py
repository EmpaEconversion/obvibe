"""Auxiliary functions."""

import os
import shutil
from functools import wraps

import pybis


def make_new_property(
    openbis_object: pybis.Openbis,
    new_property_code: str,
    new_property_label: str,
    new_property_description: str,
    new_property_data_type: str,
    collection_type_code: str = "battery_premise3",
) -> None:
    """Create a new property type in openBIS and assign it to a specified collection type.

    Args:
        openbis_object (Openbis): An authenticated instance of the openBIS API.
        new_property_code (str): The unique code for the new property type.
        new_property_label (str): The label for the new property type.
        new_property_description (str): A brief description of the new property type.
        new_property_data_type (str): The data type of the new property (e.g., 'VARCHAR', 'INTEGER').
        collection_type_code (str, optional): The code of the collection type to which the new
            property will be assigned. Defaults to 'battery_premise3'.

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
        dataType=new_property_data_type,
    )
    new_property.save()

    # Retrieve the specified collection type
    collection_type = openbis_object.get_collection_type(collection_type_code)
    if collection_type is None:
        msg = f"Collection type '{collection_type_code}' does not exist in openBIS."
        raise ValueError(msg)

    # Assign the newly created property to the collection type
    collection_type.assign_property(new_property_code)

def get_openbis_obj(dir_pat: str,
                     url: str = r"https://openbis-empa-lab501.ethz.ch/",
                     ) -> pybis.Openbis:
    """Get the openbis object from PAT.

    Args:
        dir_pat (str): The directory of the PAT file.
        url (str, optional): The URL of the openBIS server.
            Defaults to r"https://openbis-empa-lab501.ethz.ch/".

    Returns:
        pybis.Openbis: The openbis object.

    """
    with open(dir_pat) as f:
        token = f.read().strip()
    ob = pybis.Openbis(url)
    ob.set_token(token)
    return ob

def get_permid_specific_type(
        experiment_name:str,
        dataset_type:str,
        openbis_obj:pybis.Openbis,
        default_space:str ="/TEST_SPACE_PYBIS/TEST_UPLOAD",
    ) -> str:
    """Retrieve the permId of a dataset of a specific type in a specific experiment.

    Ensures names are uppercase as required by openBIS.

    Args:
        experiment_name (str): The name of the experiment. For example: 240906_kigr_gen4_01,
        dataset_type (str): The type of the dataset. For example: premise_cucumber_raw_json.
        openbis_obj (str): The openBIS object.
        default_space (str): The default space to search in.

    Returns:
        str: The permId of the dataset.

    """
    ob = openbis_obj
    # Construct the experiment identifier
    experiment_identifier = f"{default_space}/{experiment_name.upper()}"

    # Get the experiment object
    experiment = ob.get_experiment(experiment_identifier)

    # Retrieve datasets associated with the experiment
    datasets = experiment.get_datasets()

    # Filter datasets by type, comparing in uppercase
    filtered_datasets = [ds for ds in datasets if ds.type.code.upper() == dataset_type.upper()]

    # Extract permIds from the filtered datasets
    perm_ids = [ds.permId for ds in filtered_datasets]

    if len(perm_ids) == 0:
        msg = f"No datasets of type '{dataset_type}' found in experiment '{experiment_name}'"
        raise ValueError(msg)
    if len(perm_ids) > 1:
        msg = f"Multiple datasets of type '{dataset_type}' found in experiment '{experiment_name}'"
        raise ValueError(msg)

    return perm_ids[0]

# This trick will download the file, pass the path to the decorated function, and clean up the file afterward.
def with_downloaded_file(openbis_obj: pybis.Openbis, destination: str = "temp_files") -> callable:
    """Generate decorator function to handle file downloads.

    Download file, pass path and permID to decorated function, then remove file.

    Args:
        openbis_obj: The OpenBIS object.
        destination: The base folder where files will be downloaded.

    Returns:
        Decorated function that receives the path to the downloaded file and the permId as arguments.

    """
    def decorator(func: callable) -> callable:
        @wraps(func)
        def wrapper(perm_id: str, *args: dict, **kwargs: dict) -> any:
            # Download the dataset
            dataset = openbis_obj.get_dataset(perm_id)
            dataset.download(destination=destination, create_default_folders=True)
            dir_downloaded = os.path.join(destination, perm_id, "original")
            downloaded_filename = os.listdir(dir_downloaded)[0]
            path_downloaded_file = os.path.join(dir_downloaded, downloaded_filename)

            try:
                # Call the decorated function with the downloaded file path and permId
                result = func(path_downloaded_file, perm_id, *args, **kwargs)
            finally:
                # Clean up: Delete the downloaded files
                shutil.rmtree(os.path.join(destination, perm_id))
            return result
        return wrapper
    return decorator
