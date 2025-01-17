from __future__ import annotations
import logging
import os
import re
from jinja2 import Template

from . import Typing

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Generator:
    def __init__(self, data: Typing.OpenAPI, template: Template) -> None:
        self.data = data
        self.template = template
        logger.debug(f"Initialized Generator with data: {data} and template: {template}")

    def set_logger_level(self, level: int) -> None:
        logger.setLevel(level)

    def generate(self) -> None:
        raise NotImplementedError

    @staticmethod
    def sanitize_string(value: str) -> str:
        sanitized = re.sub(r'\W|^(?=\d)', '_', value)
        logger.debug(f"Sanitized string '{value}' to '{sanitized}'")
        return sanitized


class Python(Generator):
    
    reserved_python_words = [
        "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue",
        "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import",
        "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"
    ]
    
    def __init__(self, data: Typing.OpenAPI, template: Template, output_folder: str) -> None:
        super().__init__(data, template)
        self.output_folder = output_folder
        logger.debug(f"Initialized Python generator with output folder: {output_folder}")

    def generate(self):
        logger.info("Starting Python client generation")
        types_generator = Python.TypeGenerator(self.data)
        types_definitions = types_generator.generate()
        
        if not types_definitions:
            logger.warning("No types found")
            return None
        
        client_generator = Python.ClientGenerator(self.data)
        client_code = client_generator.generate()
        if not client_code:
            logger.warning("No client code found")
            return None
        
        self.save_client_and_types(client_code, types_definitions)
        logger.info("Python client generation completed")
        return client_code

    def save_client_and_types(self, client_code, type_definitions):
        os.makedirs(os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title)), exist_ok=True)
        file_path = os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title), "client.py")
        logger.debug(f"Saving client and types at {file_path}")
        with open(file_path, "w") as file:
            file.write(self.template.render(
                Imports=[
                    "from __future__ import annotations",
                    "import httpx",
                    "import json",
                    "from typing import Any, Dict, Optional, Union, List, TypeVar, Generic, Type",
                    "from enum import Enum",
                    "from dataclasses import dataclass",
                    "from dacite import from_dict",
                ],
                Enum=self.generate_enums(),
                DataClass="\n\n".join(type_definitions),
                Methods=client_code
            ))
        logger.info(f"Client and types saved successfully at {file_path}")

    def generate_enums(self):
        enums = []
        if self.data.components.schemas:
            for name, schema in self.data.components.schemas.items():
                if schema.enum:
                    enum_name = Generator.sanitize_string(name)
                    enum_values = "\n    ".join([f"{'_'+value if value in self.reserved_python_words else value} = '{value}'" for value in schema.enum])
                    enums.append(f"class {enum_name}(Enum):\n    {enum_values}")
        return "\n\n".join(enums)

    class TypeGenerator:
        def __init__(self, data: Typing.OpenAPI):
            self.components = data.components
            logger.debug(f"Initialized TypeGenerator with components: {self.components}")

        def generate(self):
            logger.info("Starting type generation")
            type_definitions = []
            if self.components.schemas:
                for name, schema in self.components.schemas.items():
                    type_definitions.append(self.generate_type(name, schema))
            logger.info("Type generation completed")
            return type_definitions

        def generate_type(self, name, schema: Typing.Schema):
            sanitized_name = Generator.sanitize_string(name)
            logger.debug(f"Generating type for {sanitized_name}")
            fields = []
            if not schema.properties:
                if schema.enum:
                    return ""
                logger.warning(f"Schema {sanitized_name} has no properties")
                return f"@dataclass\nclass {sanitized_name}:\n    pass"
                
            for field_name, field in schema.properties.items():
                fields.append(f"{field_name}: {self.get_field_type_from_property(field)}")
            return f"""
@dataclass
class {sanitized_name}:
    {f"\n    ".join(fields)}
            """
            
        def get_field_type_from_property(self, field: Typing.Property|Typing.Schema):
            print(field)
            if isinstance(field, Typing.Schema):
                return self.get_field_type_from_property(field.properties)
            if field.nullable:
                field.nullable = False
                return f"Optional[{self.get_field_type_from_property(field)}]"
            if field.ref:
                return f"'{Generator.sanitize_string(field.ref.split('/')[-1])}'"
            if field.type == "array":
                return f"List[{self.get_field_type_from_property(field.items)}]"
            if field.type == "object":
                return "Dict[str, Any]"
            if field.type == "integer":
                return "int"
            if field.type == "number":
                return "float"
            if field.type == "boolean":
                return "bool"
            if field.type == "string":
                return "str"
            if field.allOf:
                d = []
                for i in field.allOf:
                    d.append(self.get_field_type_from_property(i))
                return f"Union[{', '.join(d)}]"
            return "Any"
        
        
    class ClientGenerator:
        def __init__(self, data: Typing.OpenAPI):
            self.data = data
            logger.debug(f"Initialized ClientGenerator with data: {self.data}")

        def generate(self):
            logger.info(f"Starting client generation for API {self.data.info.title}")
            methods = self.generate_methods()
            client_code = "\n\n".join(methods)
            logger.info(f"Client generation completed for API {self.data.info.title}")
            return client_code

        def generate_methods(self):
            methods = []
            for path_url, path_item in self.data.paths.items():
                for method in path_item.__dict__.keys():
                    path = path_item.__dict__[method]
                    if path:
                        logger.debug(f"Generating method for {method.upper()} {path_url}")
                        methods.append(self.generate_method(method.upper(), path_url, getattr(path_item, method)))
            return methods
        
        def get_field_type_from_property(self, field: Typing.Property):
            if field.nullable:
                field.nullable = False
                return f"Optional[{self.get_field_type_from_property(field)}]"
            if field.ref:
                return f"'{Generator.sanitize_string(field.ref.split('/')[-1])}'"
            if field.type == "array":
                return f"List[{self.get_field_type_from_property(field.items)}]"
            if field.type == "object":
                return "Dict[str, Any]"
            if field.type == "integer":
                return "int"
            if field.type == "number":
                return "float"
            if field.type == "boolean":
                return "bool"
            return "str"
        
        def get_preferred_output_type(self, operation: Typing.Operation):
            output_type = "Any"
            preferred_output_type = operation.responses.get("200") or operation.responses.get("default")
            response_content = preferred_output_type.content.get("application/json") if preferred_output_type and preferred_output_type.content else None
            if response_content:
                output_type = self.get_field_type_from_property(response_content["schema"])
            return output_type

        def generate_method(self, method: str, path: str, operation: Typing.Operation):
            sanitized_path = Generator.sanitize_string(path.replace("{", "").replace("}", ""))
            sanitized_path = f"{method.lower()}_{sanitized_path.removeprefix('_')}"
            
            input_parameters_list = []
            for i in operation.parameters or []:
                input_parameters_list.append(f"{i.name}: {self.get_field_type_from_property(i.schema)}")
            
            input_parameters = ", ".join([param.name for param in operation.parameters]) if operation.parameters else ""
            request_parameters = ", ".join([f"{param.name}={param.name}" for param in operation.parameters]) if operation.parameters else ""
            
            logger.debug(f"Generated method {sanitized_path} with parameters: {input_parameters}")
            output_type = self.get_preferred_output_type(operation)
            response_model_to_underlying_type = output_type.replace("'", "")
            is_list = False
            if(response_model_to_underlying_type.startswith("List[")):
                response_model_to_underlying_type = response_model_to_underlying_type.replace("List[", "").replace("]", "")
                is_list = True
            return f"""
    def {sanitized_path}(self, {input_parameters + ", " if input_parameters else ""}**kwargs) -> {output_type}:
        return self._request("{method}", "{path}".format({request_parameters}), response_model={response_model_to_underlying_type}, response_model_list={is_list}, **kwargs)
            """

class JavaScript(Generator):
    def __init__(self, data: Typing.OpenAPI, template: Template, output_folder: str) -> None:
        super().__init__(data, template)
        self.output_folder = output_folder
        logger.debug(f"Initialized JavaScript generator with output folder: {output_folder}")

    def generate(self):
        logger.info("Starting JavaScript client generation")
        types_generator = JavaScript.TypeGenerator(self.data)
        types_definitions = types_generator.generate()
        
        if not types_definitions:
            logger.warning("No types found")
            return None
        
        client_generator = JavaScript.ClientGenerator(self.data)
        client_code = client_generator.generate()
        if not client_code:
            logger.warning("No client code found")
            return None
        
        self.save_client_and_types(client_code, types_definitions)
        logger.info("JavaScript client generation completed")
        return client_code

    def save_client_and_types(self, client_code, type_definitions):
        os.makedirs(os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title)), exist_ok=True)
        file_path = os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title), "client.js")
        logger.debug(f"Saving client and types at {file_path}")
        with open(file_path, "w") as file:
            file.write(self.template.render(
                Imports=[],
                Types="\n\n".join(type_definitions),
                Methods=client_code
            ))
        logger.info(f"Client and types saved successfully at {file_path}")

    class TypeGenerator:
        def __init__(self, data: Typing.OpenAPI):
            self.components = data.components
            logger.debug(f"Initialized TypeGenerator with components: {self.components}")

        def generate(self):
            logger.info("Starting type generation")
            type_definitions = []
            if self.components.schemas:
                for name, schema in self.components.schemas.items():
                    type_definitions.append(self.generate_type(name, schema))
            logger.info("Type generation completed")
            return type_definitions

        def generate_type(self, name, schema: Typing.Schema):
            sanitized_name = Generator.sanitize_string(name)
            logger.debug(f"Generating type for {sanitized_name}")
            fields = []
            if not schema.properties:
                logger.warning(f"Schema {sanitized_name} has no properties")
                return f"class {sanitized_name} {{}}"
                
            for field_name, field in schema.properties.items():
                fields.append(f"{field_name};")
            return f"""
class {sanitized_name} {{
    {f"\n    ".join(fields)}
}}
            """
            
        def get_field_type_from_property(self, field: Typing.Property|Typing.Schema):
            if isinstance(field, Typing.Schema):
                return self.get_field_type_from_property(field.properties)
            if field.nullable:
                field.nullable = False
                return f"{self.get_field_type_from_property(field)} | null"
            if field.ref:
                return f"{Generator.sanitize_string(field.ref.split('/')[-1])}"
            if field.type == "array":
                return f"Array<{self.get_field_type_from_property(field.items)}>"
            if field.type == "object":
                return "Record<string, any>"
            if field.type == "integer":
                return "number"
            if field.type == "number":
                return "number"
            if field.type == "boolean":
                return "boolean"
            if field.type == "string":
                return "string"
            if field.allOf:
                d = []
                for i in field.allOf:
                    d.append(self.get_field_type_from_property(i))
                return f"({', '.join(d)})"
            return "any"
        
        
    class ClientGenerator:
        def __init__(self, data: Typing.OpenAPI):
            self.data = data
            logger.debug(f"Initialized ClientGenerator with data: {self.data}")

        def generate(self):
            logger.info(f"Starting client generation for API {self.data.info.title}")
            methods = self.generate_methods()
            client_code = "\n\n".join(methods)
            logger.info(f"Client generation completed for API {self.data.info.title}")
            return client_code

        def generate_methods(self):
            methods = []
            for path_url, path_item in self.data.paths.items():
                for method in path_item.__dict__.keys():
                    path = path_item.__dict__[method]
                    if path:
                        logger.debug(f"Generating method for {method.upper()} {path_url}")
                        methods.append(self.generate_method(method.upper(), path_url, getattr(path_item, method)))
            return methods
        
        def get_field_type_from_property(self, field):
            if field.nullable:
                field.nullable = False
                return f"{self.get_field_type_from_property(field)} | null"
            if field.ref:
                return f"{Generator.sanitize_string(field.ref.split('/')[-1])}"
            if field.type == "array":
                return f"Array<{self.get_field_type_from_property(field.items)}>"
            if field.type == "object":
                return "Record<string, any>"
            if field.type == "integer":
                return "number"
            if field.type == "number":
                return "number"
            if field.type == "boolean":
                return "boolean"
            return "string"
        
        def get_preferred_output_type(self, operation: Typing.Operation):
            output_type = "any"
            preferred_output_type = operation.responses.get("200") or operation.responses.get("default")
            response_content = preferred_output_type.content.get("application/json") if preferred_output_type and preferred_output_type.content else None
            if response_content:
                output_type = self.get_field_type_from_property(response_content["schema"])
            return output_type

        def generate_method(self, method: str, path: str, operation: Typing.Operation):
            sanitized_path = Generator.sanitize_string(path.replace("{", "").replace("}", ""))
            sanitized_path = f"{method.lower()}_{sanitized_path.removeprefix('_')}"
            
            input_parameters_list = []
            for i in operation.parameters or []:
                input_parameters_list.append(f"{i.name}")
            
            input_parameters = ", ".join([param.name for param in operation.parameters]) if operation.parameters else ""
            request_parameters = ", ".join([f"{param.name}={param.name}" for param in operation.parameters]) if operation.parameters else ""
            
            logger.debug(f"Generated method {sanitized_path} with parameters: {input_parameters}")
            return f"""
    async {sanitized_path}({input_parameters + ", " if input_parameters else ""}config = {{}}) {{
        const url = `{'{this.baseUrl}'}${path}`;
        const response = await fetch(url, {{
            method: "{method}",
            ...config
        }});
        if (!response.ok) {{
            throw new Error(`HTTP error! status: ${'{response.status}'}`);
        }}
        return response.json();
    }}
            """
