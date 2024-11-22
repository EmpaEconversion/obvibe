"""
This is the main module for this repository
"""

import pybis
import os
from . import keller, pathfolio

class Identifiers:
    """
    Class object help with the identification of space, project and experiment in openBIS.
    """
    def __init__(self, space_code: str, project_code: str, experiment_code: str) -> None:
        self.space_code = space_code
        self.project_code = project_code
        self.experiment_code = experiment_code

    @property
    def space_identifier(self) -> str:
        return self.space_code

    @property
    def project_identifier(self) -> str:
        return f"/{self.space_identifier}/{self.project_code}"

    @property
    def experiment_identifier(self) -> str:
        return f"{self.project_identifier}/{self.experiment_code}"
    
class Dataset:
    """
    Class made to faciliate dataset upload
    """
    ident = None

    def __init__(self, openbis_instance, dataset_type=None, upload_data=None,) -> None:
        self.ob = openbis_instance
        self.type = dataset_type
        self.data = upload_data
        self.experiment = Dataset.ident.experiment_identifier

    def upload_dataset(self):
        """
        Upload the dataset to the openbis
        """
        self.ob.new_dataset(type=self.type, experiment=self.experiment, file=self.data).save()

    
    
def push_exp(
        openbis_object:pybis.Openbis,
        dir_folder:str,
        dict_mapping:dict=pathfolio.metadata_mapping,
        space_code:str = 'TEST_SPACE_PYBIS',
        project_code:str = 'TEST_UPLOAD',
        experiment_type:str = 'Battery_Premise2',
        
        
):  
    ob = openbis_object
    list_json = [file for file in os.listdir(dir_folder) if file.endswith(".json")]
    if len(list_json) != 1:
        raise ValueError("There should be exactly one json file in the folder")
    name_json = [file for file in os.listdir(dir_folder) if file.endswith(".json")][0]
    dir_json = os.path.join(dir_folder, name_json)

    if len(os.path.basename(dir_json).split('.')) != 3:
        raise ValueError("Not recognized json file name. The recognized file name is cycle.experiment_code.json")

    exp_name = os.path.basename(dir_json).split('.')[1] #Extract the experiment name from the json file name
    ident = Identifiers(space_code, project_code, experiment_code=exp_name)

    #Create new experiment in the predefined space and project.
    exp =  ob.new_experiment(code=ident.experiment_code, type=experiment_type, project=ident.project_identifier)
    #Itterate through list of metadtata from json file and upload them to the experiment. 
    for item in dict_mapping:
        try:
            openbis_code = item['openbis_code']
            json_path = item['json_path']
            print(f'Uploading metadata for {openbis_code} from {json_path}')
            exp.p[openbis_code] = keller.get_metadata_from_json(dir_json, json_path)
            exp.save()
        except:
            print(f'Error uploading metadata for {openbis_code} from {json_path}')
            continue

    # Upload the dataset
    Dataset.ident = ident
    # Analyzed json file
    ds_analyzed_json = Dataset(ob)
    ds_analyzed_json.type = 'premise_cucumber_analyzed_json'
    ds_analyzed_json.data = dir_json
    ds_analyzed_json.experiment = '/TEST_SPACE_PYBIS/TEST_UPLOAD/240906_KIGR_GEN4_01'
    ds_analyzed_json.upload_dataset()

    

    

    
