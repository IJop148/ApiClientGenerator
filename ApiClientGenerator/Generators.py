from __future__ import annotations
import logging
import os
import re
from jinja2 import Template
from typing import Any, Type
from enum import Enum

from . import Typing


class Generator:
    def __init__(self, data: Typing.OpenAPI, template: Template, log:logging.Logger) -> None:
        self.data = data
        self.template = template
        self.logger = log
        self.logger.debug(f"Initialized Generator with data: {data.info.title} and template: {template}")

    def set_logger_level(self, level: int) -> None:
        self.logger.setLevel(level)

    def generate(self) -> None:
        raise NotImplementedError

    @staticmethod
    def sanitize_string(value: str) -> str:
        sanitized = re.sub(r'\W|^(?=\d)', '_', value)
        # self.logger.debug(f"Sanitized string '{value}' to '{sanitized}'")
        return sanitized

    @staticmethod
    def bind_enum_values(data: Any, response_model: Type) -> Any:
        if hasattr(response_model, '__annotations__'):
            for field, field_type in response_model.__annotations__.items():
                if issubclass(field_type, Enum) and field in data:
                    data[field] = field_type(data[field])
        return data

class Python(Generator):
    
    reserved_python_words = [
        "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue",
        "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import",
        "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"
    ]
    
    def __init__(self, data: Typing.OpenAPI, template: Template, log: logging.Logger, output_folder: str) -> None:
        super().__init__(data, template, log)
        self.output_folder = output_folder
        self.logger.debug(f"Initialized Python generator with output folder: {output_folder}")

    def generate(self):
        self.logger.info("Starting Python client generation")
        types_generator = Python.TypeGenerator(self.data, self.logger)
        types_definitions, enums = types_generator.generate()
        
        if not types_definitions:
            self.logger.warning("No types found")
            return None
        
        client_generator = Python.ClientGenerator(self.data, self.logger)
        client_code = client_generator.generate(enums)
        if not client_code:
            self.logger.warning("No client code found")
            return None
        
        self.save_client_and_types(client_code, types_definitions)
        self.logger.info("Python client generation completed")
        return client_code

    def save_client_and_types(self, client_code, type_definitions):
        os.makedirs(os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title)), exist_ok=True)
        file_path = os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title), "client.py")
        self.logger.debug(f"Saving client and types at {file_path}")
        with open(file_path, "w") as file:
            file.write(self.template.render(
                Imports=[
                    "from __future__ import annotations",
                    "import httpx",
                    "import json",
                    "from typing import Any, Dict, Optional, Union, List, TypeVar, Generic, Type",
                    "from enum import Enum",
                    "from dataclasses import dataclass",
                    "from dacite import from_dict, Config",
                ],
                Enum=self.generate_enums(),
                DataClass="\n\n".join(type_definitions),
                Methods=client_code
            ))
        self.logger.info(f"Client and types saved successfully at {file_path}")

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
        def __init__(self, data: Typing.OpenAPI, log:logging.Logger):
            self.components = data.components
            self.logger = log
            self.logger.debug(f"Initialized TypeGenerator with {len(self.components.schemas.keys())} components")

        def generate(self):
            self.logger.info("Starting type generation")
            type_definitions = []
            self.enums = self.detect_enums()
            
            if self.components.schemas:
                for name, schema in self.components.schemas.items():
                    type_definitions.append(self.generate_type(name, schema))
            self.logger.info("Type generation completed")

            
            return (type_definitions, self.enums,)

        def detect_enums(self):
            enums = []
            if self.components.schemas:
                for name, schema in self.components.schemas.items():
                    if schema.enum:
                        enum_name = Generator.sanitize_string(name)
                        enums.append(enum_name)
            return enums

        def generate_type(self, name, schema: Typing.Schema):
            sanitized_name = Generator.sanitize_string(name)
            self.logger.debug(f"Generating type for {sanitized_name}")
            fields = []
            if not schema.properties:
                if schema.enum:
                    self.logger.debug(f"Enum found in generation: {schema.enum = }")
                    return ""
                self.logger.warning(f"Schema {sanitized_name} has no properties")
                return f"@dataclass\nclass {sanitized_name}:\n    pass"
                
            for field_name, field in schema.properties.items():
                fields.append(f"{field_name}: {self.get_field_type_from_property(field)}")
            return f"""
@dataclass
class {sanitized_name}:
    {f"\n    ".join(fields)}"""
            
        def get_field_type_from_property(self, field: Typing.Property|Typing.Schema):
            if field.enum:
                self.logger.debug("Enum found in property detection: " + field.enum)
            if isinstance(field, Typing.Schema):
                return self.get_field_type_from_property(field.properties)
            if field.nullable:
                field.nullable = False
                return f"Optional[{self.get_field_type_from_property(field)}]"
            if field.enum:
                return "str"
            if field.ref:
                if Generator.sanitize_string(field.ref.split('/')[-1]) in self.enums:
                    self.logger.debug(f"Enum found in client property: {Generator.sanitize_string(field.ref.split('/')[-1]) = }")
                    return "str"
                return f"{Generator.sanitize_string(field.ref.split('/')[-1])}"
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
        def __init__(self, data: Typing.OpenAPI, log:logging.Logger):
            self.data = data
            self.logger = log
            self.logger.debug(f"Initialized ClientGenerator for application: {self.data.info.title}")

        def generate(self, enums: list[str]):
            self.enums = enums
            self.logger.info(f"Starting client generation for API {self.data.info.title}")
            self.logger.debug(f"Enums found: {self.enums}")
            methods = self.generate_methods()
            client_code = "\n\n".join(methods)
            self.logger.info(f"Client generation completed for API {self.data.info.title}")
            return client_code

        def generate_methods(self):
            methods = []
            for path_url, path_item in self.data.paths.items():
                for method in path_item.__dict__.keys():
                    path = path_item.__dict__[method]
                    if path:
                        self.logger.debug(f"Generating method for {method.upper()} {path_url}")
                        methods.append(self.generate_method(method.upper(), path_url, getattr(path_item, method)))
            return methods
        
        def get_field_type_from_property(self, field: Typing.Property|Typing.Schema):
            resp = None
            if field.nullable:
                field.nullable = False
                resp = f"Optional[{self.get_field_type_from_property(field)}]"
            elif field.ref:
                # Check if the ref is an enum
                if Generator.sanitize_string(field.ref.split('/')[-1]) in self.enums:
                    self.logger.debug(f"Enum found in client property: {Generator.sanitize_string(field.ref.split('/')[-1]) = }")
                    resp = "str"
                else:
                    resp = f"{Generator.sanitize_string(field.ref.split('/')[-1])}"
            elif field.type == "array":
                resp = f"List[{self.get_field_type_from_property(field.items)}]"
            elif field.type == "object":
                resp = "Dict[str, Any]"
            elif field.type == "integer":
                resp = "int"
            elif field.type == "number":
                resp = "float"
            elif field.type == "boolean":
                resp = "bool"
            if resp is None:
                resp = "str"

            self.logger.debug(f"Field type: {resp} for {field.enum = } {field.ref = } {field.type = }")
            return resp
        
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
            
            self.logger.debug(f"Generated method {sanitized_path} with parameters: {input_parameters}")
            output_type = self.get_preferred_output_type(operation)
            
            if "List[" in output_type:
                is_list = True
                output_type2 = output_type.replace("List[", "").replace("]", "")
            else:
                is_list = False
                output_type2 = output_type
            
            return f"""
    def {sanitized_path}(self, {input_parameters + ", " if input_parameters else ""}**kwargs) -> {output_type}:
        response = self._request("{method}", "{path}".format({request_parameters}), **kwargs, response_model={output_type2.replace("'", "")}, response_model_list={is_list})
        return response"""

class JavaScript(Generator):
    def __init__(self, data: Typing.OpenAPI, template: Template, log: logging.Logger, output_folder: str) -> None:
        super().__init__(data, template, log)
        self.output_folder = output_folder
        self.logger.debug(f"Initialized JavaScript generator with output folder: {output_folder}")

    def generate(self):
        self.logger.info("Starting JavaScript client generation")
        types_generator = JavaScript.TypeGenerator(self.data, self.logger)
        types_definitions = types_generator.generate()
        
        if not types_definitions:
            self.logger.warning("No types found")
            return None
        
        client_generator = JavaScript.ClientGenerator(self.data, self.logger)
        client_code = client_generator.generate()
        if not client_code:
            self.logger.warning("No client code found")
            return None
        
        self.save_client_and_types(client_code, types_definitions)
        self.logger.info("JavaScript client generation completed")
        return client_code

    def save_client_and_types(self, client_code, type_definitions):
        os.makedirs(os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title)), exist_ok=True)
        file_path = os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title), "client.js")
        self.logger.debug(f"Saving client and types at {file_path}")
        with open(file_path, "w") as file:
            file.write(self.template.render(
                Imports=[],
                Types="\n\n".join(type_definitions),
                Methods=client_code
            ))
        self.logger.info(f"Client and types saved successfully at {file_path}")

    class TypeGenerator:
        def __init__(self, data: Typing.OpenAPI, log:logging.Logger):
            self.components = data.components
            self.logger = log
            self.logger.debug(f"Initialized TypeGenerator with components: {self.components}")

        def generate(self):
            self.logger.info("Starting type generation")
            type_definitions = []
            if self.components.schemas:
                for name, schema in self.components.schemas.items():
                    type_definitions.append(self.generate_type(name, schema))
            self.logger.info("Type generation completed")
            return type_definitions

        def generate_type(self, name, schema: Typing.Schema):
            sanitized_name = Generator.sanitize_string(name)
            self.logger.debug(f"Generating type for {sanitized_name}")
            fields = []
            if not schema.properties:
                self.logger.warning(f"Schema {sanitized_name} has no properties")
                return f"class {sanitized_name} {{}}"
                
            for field_name, field in schema.properties.items():
                fields.append(f"{field_name};")
            return f"""
class {sanitized_name} {{
    {f"\n    ".join(fields)}
}}"""
            
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
        def __init__(self, data: Typing.OpenAPI, log:logging.Logger):
            self.data = data
            self.logger = log
            self.logger.debug(f"Initialized ClientGenerator with data: {self.data}")

        def generate(self):
            self.logger.info(f"Starting client generation for API {self.data.info.title}")
            methods = self.generate_methods()
            client_code = "\n\n".join(methods)
            self.logger.info(f"Client generation completed for API {self.data.info.title}")
            return client_code

        def generate_methods(self):
            methods = []
            for path_url, path_item in self.data.paths.items():
                for method in path_item.__dict__.keys():
                    path = path_item.__dict__[method]
                    if path:
                        self.logger.debug(f"Generating method for {method.upper()} {path_url}")
                        methods.append(self.generate_method(method.upper(), path_url, getattr(path_item, method)))
            return methods
        
        def get_field_type_from_property(self, field: Typing.Property):
            if field.nullable:
                field.nullable = False
                return f"{self.get_field_type_from_property(field)} | null"
            if field.enum:
                return "string"
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
            
            self.logger.debug(f"Generated method {sanitized_path} with parameters: {input_parameters}")
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
    }}"""
