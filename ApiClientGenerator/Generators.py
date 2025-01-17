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


    def sort_classes_by_dependencies(self, type_definitions):
        logger.debug("Sorting classes by dependencies")
        dependency_graph = {}
        class_definitions = {}

        for type_def in type_definitions:
            class_name = type_def.split()[1]
            class_definitions[class_name] = type_def
            dependencies = re.findall(r"List\[(\w+)\]|Dict\[\w+, (\w+)\]", type_def)
            dependencies = [dep for dep in dependencies if dep]
            dependency_graph[class_name] = dependencies

        sorted_classes = []
        visited = set()

        def visit(node):
            if node not in visited:
                visited.add(node)
                for dep in dependency_graph.get(node, []):
                    visit(dep)
                sorted_classes.append(node)

        for node in dependency_graph:
            visit(node)

        sorted_type_definitions = [class_definitions[class_name] for class_name in sorted_classes if class_name in class_definitions]
        logger.debug(f"Sorted classes: {sorted_classes}")
        return sorted_type_definitions

    def save_client_and_types(self, client_code, type_definitions):
        os.makedirs(os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title)), exist_ok=True)
        file_path = os.path.join(self.output_folder, Generator.sanitize_string(self.data.info.title), "client.py")
        logger.debug(f"Saving client and types at {file_path}")
        with open(file_path, "w") as file:
            file.write(self.template.render(
                Imports=[
                    "import httpx",
                    "import json",
                    "from typing import Any, Dict, Optional, Union, List, TypeVar, Generic, Type",
                    "from enum import Enum",
                    "from dataclasses import dataclass",
                    "from dacite import from_dict",
                ],
                Enum="",  # Add enum generation logic if needed
                DataClass="\n\n".join(type_definitions),
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
            return f"""
    def {sanitized_path}(self, {input_parameters + ", " if input_parameters else ""}**kwargs) -> {output_type}:
        return self._request("{method}", "{path}".format({request_parameters}), **kwargs, response_model={output_type.replace("'", "")})
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
