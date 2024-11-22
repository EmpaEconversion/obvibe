"""
This is the main module for this repository
"""

import pybis
import os
from . import keller, pathfolio, oh_my_ontology

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
    Class made to facilitate dataset upload
    """
    def __init__(self, openbis_instance, ident: Identifiers, dataset_type=None, upload_data=None) -> None:
        self.ob = openbis_instance
        self.ident = ident
        self.type = dataset_type
        self.data = upload_data
        self.experiment = self.ident.experiment_identifier.upper()  # Use the provided Identifiers instance

    def upload_dataset(self):
        """
        Upload the dataset to the openBIS
        """
        self.ob.new_dataset(type=self.type, experiment=self.experiment, file=self.data).save()


def push_exp(
        openbis_object:pybis.Openbis,
        dir_folder:str,
        dict_mapping:dict=pathfolio.metadata_mapping,
        space_code:str = 'TEST_SPACE_PYBIS',
        project_code:str = 'TEST_UPLOAD',
        experiment_type:str = 'Battery_Premise2',
        ontologize_metadata:bool = True,
        dir_metadata_excel:str = r"K:\Aurora\nukorn_PREMISE_space\Backup for ontologized xlsx",
        dir_jsonld_folder: str = r'K:\Aurora\nukorn_PREMISE_space\Backup for jsonld'
)-> None:
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

    #Analyzed JSON
    ds_analyzed_json = Dataset(ob, ident=ident)
    ds_analyzed_json.type = 'premise_cucumber_analyzed_json'
    ds_analyzed_json.data = dir_json
    ds_analyzed_json.upload_dataset()

    #Raw data json
    list_raw_json = [file for file in os.listdir(dir_folder) if file.endswith(".json.gz") and file.split('.')[1] == exp_name]
    if len(list_raw_json) != 1:
        raise ValueError("There should be exactly one raw_json file in the folder")
    dir_raw_json = os.path.join(dir_folder, list_raw_json[0])
    ds_raw_json = Dataset(ob, ident=ident)
    ds_raw_json.type = 'premise_cucumber_raw_json'
    ds_raw_json.data = dir_raw_json
    ds_raw_json.upload_dataset()

    #Ontologize the metadata. Create a new Excel file with the metadata and save it in the backup directory.
    #Create the corresponding ontologized JSON-LD file.
    if ontologize_metadata:
        #Generate the metadata Excel file for the specific experiment
        oh_my_ontology.gen_metadata_xlsx(dir_json)

        #Upload the metadata Excel file to the openBIS
        dir_metadata_excel = os.path.join(dir_metadata_excel, f"{exp_name}_excel_for_ontology.xlsx")
        ds_metadata_excel = Dataset(ob, ident=ident)
        ds_metadata_excel.type = 'premise_excel_for_ontology'
        ds_metadata_excel.data = dir_metadata_excel
        ds_metadata_excel.upload_dataset()

        #Generate the ontologized JSON-LD file
        jsonld_filename = f"ontologized_{exp_name}.json"
        oh_my_ontology.gen_jsonld(dir_metadata_excel, jsonld_filename)

        #Upload the ontologized JSON-LD file to the openBIS
        dir_jsonld = os.path.join(dir_jsonld_folder, jsonld_filename)
        ds_jsonld = Dataset(ob, ident=ident)
        ds_jsonld.type = 'premise_jsonld'
        ds_jsonld.data = dir_jsonld
        ds_jsonld.upload_dataset()
        
        


    

    

    
