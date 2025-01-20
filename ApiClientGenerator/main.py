import json
import jinja2
from glob import glob
import os
import logging
from typing import Any, Dict
from dacite import from_dict, Config

from .Generators import Python as P, JavaScript as JS
from . import Typing


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def ref_key_transformer(data: Any) -> Any:
    if isinstance(data, dict):
        return {("ref" if k == "$ref" else ("in_" if k == "in" else k)): ref_key_transformer(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [ref_key_transformer(item) for item in data]
    else:
        return data

class Settings:
    Python: Dict[str, bool] = {}
    Javascript: Dict[str, bool] = {}


def main(input_folder: str|None=None, output_folder:str|None=None, settings: Settings|None=None) -> None:
    logger.info("Starting client generation")
    
    if input_folder is None:
        input_folder = "ToBeGenerated"
    if output_folder is None:
        output_folder = "Output"
    if settings is None:
        settings = Settings()
    
    # Loop over all the to be generated clients
    for file in glob(f"{input_folder}/*.json"):
        logger.info(f"Processing file: {file}")

        # Load the file
        with open(file, "r") as f:
            data = json.load(f)
            # Modify $ref keys to ref and in keys to in_ recursively
            data = ref_key_transformer(data)
            # logger.debug(f"Transformed data: {data}")
            config = Config()
            parsed_data = from_dict(data_class=Typing.OpenAPI, data=data, config=config)

        # Load the template folder
        folder_dir = os.path.dirname(os.path.realpath(__file__))
        logger.debug(f"Folder directory: {folder_dir}")

        file_name = os.path.basename(file)[:-5]
        print(f"Generating client for {file_name}")

        # Generate Python client if enabled in settings
        if file_name in settings.Python and settings.Python[file_name]:
            with open(os.path.join(folder_dir, "templates", "Python.jinja2"), "r") as f:
                template = jinja2.Template(f.read())
            generator = P(parsed_data, template, output_folder)
            generator.generate()

        # Generate JavaScript client if enabled in settings
        if file_name in settings.Javascript and settings.Javascript[file_name]:
            with open(os.path.join(folder_dir, "templates", "Javascript.jinja2"), "r") as f:
                template = jinja2.Template(f.read())
            generator = JS(parsed_data, template, output_folder)
            generator.generate()
    
if __name__ == "__main__":
    # Set current working directory to the directory of the script
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    main()
