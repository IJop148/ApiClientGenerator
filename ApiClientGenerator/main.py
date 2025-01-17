import json
import jinja2
from glob import glob
import os
import logging
from typing import Any, Dict
from Generators import Python as P
import Typing
from dacite import from_dict, Config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def ref_key_transformer(data: Any) -> Any:
    if isinstance(data, dict):
        return {("ref" if k == "$ref" else ("in_" if k == "in" else k)): ref_key_transformer(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [ref_key_transformer(item) for item in data]
    else:
        return data


def main() -> None:
    logger.info("Starting client generation")
    
    # Loop over all the to be generated clients
    for file in glob("ToBeGenerated/*.json"):
        logger.info(f"Processing file: {file}")
        
        # Load the file
        with open(file, "r") as f:
            data = json.load(f)
            logger.debug(f"Loaded data: {data}")
            # Modify $ref keys to ref and in keys to in_ recursively
            

            data = ref_key_transformer(data)
            logger.debug(f"Transformed data: {data}")
            config = Config()
            parsed_data = from_dict(data_class=Typing.OpenAPI, data=data, config=config)

        with open("templates/Python.jinja2", "r") as f:
            template = jinja2.Template(f.read())
        
        # Generate the client
        generator = P(parsed_data, template)
        generator.generate()
    
if __name__ == "__main__":
    # Set current working directory to the directory of the script
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    main()
