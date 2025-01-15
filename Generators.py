import os
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING
import json

class Generator:
    class PythonGenerator:
        
        file_extension = ".py"
        invalid_chars = [".", "[", "]", ",", "=", " ", ":", "`", "-", "/", "<", ">", "(", ")", "&", "%", "$", "#", "@", "!", "^", "*", "+", "?", "|", "\\"]
        python_conversion = {
            "types": {
                "string": "str",
                "number": "float",
                "integer": "int",
                "boolean": "bool",
                "object": "dict",
                "array": "list",
                "$ref": "Any"
            }
        }
        
        def __init__(self, data: Dict[str, Any]):
            self.data = data
            self.data["sorted_types"] = self.sort_types(self.data["components"]["schemas"])
            self.visited_references = set()

        def start(self, module_name: str|None = None):
            self.module_name = module_name
            self.data["module_name"] = module_name
            self.data["python_conversion"] = self.python_conversion
            self.data["invalid_chars"] = self.invalid_chars
            self.data["sanitize_name"] = lambda name: self.sanitize_name(name)
            self.data["generate_types"] = self.generate_types(self.data)
            self.data["generate_response_dict"] = self.generate_response_dict()
            self.data["generate_api_methods"] = self.generate_api_methods(self.data["paths"], self.data["info"], self.python_conversion)

        def sort_types(self, schemas: Dict[str, Any]) -> List[str]:
            sorted_types = []
            visited = set()

            def visit(type_name: str):
                if type_name in visited:
                    return
                visited.add(type_name)
                schema = schemas[type_name]
                if schema["type"] == "object" and "properties" in schema:
                    for prop in schema["properties"].values():
                        if "$ref" in prop:
                            ref_type = prop["$ref"].split("/")[-1]
                            visit(ref_type)
                sorted_types.append(type_name)

            for type_name in schemas:
                visit(type_name)

            return sorted_types

        def generate_types(self, data: Dict[str, Any], sublevel: int = 0) -> None:
            if getattr(self, "file_output_folder", None) is not None:
                output_folder = f"{self.file_output_folder}/{self.sanitize_name(data['info']['title'])}/Types"
            else:
                output_folder = f"Output/Python/{self.sanitize_name(data['info']['title'])}/Types"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            with open(f"{output_folder}/__init__.py", "w") as init_file:
                init_file.write("import importlib\n\n")
                init_file.write(f"from typing import TYPE_CHECKING\n")
                init_file.write(f"if TYPE_CHECKING:\n")
                for type in self.data["sorted_types"]:
                    schema = data["components"]["schemas"][type]
                    print(f"Starting type generation for: {type}")
                    parent_class = f"{self.sanitize_name(data['info']['title'])}_Types" if 'info' in data else ""
                    type_code = ""
                    ref = self.Object_Class_Generator.detect_reference(schema, self.module_name, resident=type)
                    if "enum" in schema:
                        type_code = self.Enum_Generator.generate_enum(self.sanitize_name(type), schema["enum"])
                    elif schema["type"] == "string":
                        type_code = self.generate_string(self.sanitize_name(type), sublevel)
                    elif schema["type"] == "object" and "properties" in schema:
                        type_code = self.Object_Class_Generator.generate_object_class(self.sanitize_name(type), schema["properties"], self.python_conversion, parent_class, sublevel, self.module_name)
                        for prop in schema["properties"].values():
                            if "$ref" in prop:
                                ref_type = prop["$ref"].split("/")[-1]
                    else:
                        type_code = self.Object_Class_Generator.find_type(schema, self.python_conversion, parent_class, resident=type)
                    with open(f"{output_folder}/{self.sanitize_name(type)}.py", "w") as type_file:
                        type_file.write(f"from typing import List, Optional, Union, Any, Dict, Type, TYPE_CHECKING\n")
                        type_file.write(f"from dataclasses import dataclass, field, fields\n")
                        type_file.write(f"\n{ref}\n")
                        type_file.write(f"\n{type_code}")
                    init_file.write(f"    from .{self.sanitize_name(type)} import {self.sanitize_name(type)}\n")
                init_file.write("\n")
                for type in self.data["sorted_types"]:
                    init_file.write(f"{self.sanitize_name(type)} = importlib.import_module('.{self.sanitize_name(type)}', __name__).{self.sanitize_name(type)}\n")

        def generate_response_dict(self) -> str:
            return """
class ResponseDict[T]:
    data: Optional[T]
    text: str
    status_code: int
"""

        def generate_api_methods(self, paths: Dict[str, Any], info: Dict[str, Any], python_conversion: Dict[str, str]) -> str:
            methods_code = ""
            indent_amount = 1
            for function, methods in paths.items():
                for method, details in methods.items():
                    params = []
                    for param in details.get("parameters", []):
                        if param["in"] == "path":
                            if 'schema' in param and 'type' in param['schema']:
                                param_type = python_conversion['types'].get(param['schema']['type'], 'Any')
                            elif 'schema' in param and '$ref' in param['schema']:
                                param_type = self.sanitize_name(param['schema']['$ref'].split('/')[-1])
                            else:
                                param_type = 'Any'
                            params.append({"name": param["name"], "type": param_type})
                    response_types = {}
                    for status_code, response in details['responses'].items():
                        if (
                            'content' in response
                            and 'application/json' in response['content']
                            and 'schema' in response['content']['application/json']
                            and '$ref' in response['content']['application/json']['schema']
                        ):
                            ref = response['content']['application/json']['schema']['$ref']
                            type_name = self.sanitize_name(ref.split('/')[-1])
                            response_types[status_code] = f"{self.sanitize_name(self.data["info"]["title"])}_Type.{type_name}"
                        elif(
                            'content' in details['responses'][status_code]
                                and 'application/json' in details['responses'][status_code]['content']
                                and 'items' in details['responses'][status_code]['content']['application/json']['schema']
                                and '$ref' in details['responses'][status_code]['content']['application/json']['schema']['items']
                        ):
                            ref = details['responses'][status_code]['content']['application/json']['schema']['items']['$ref']
                            type_name = self.sanitize_name(ref.split('/')[-1])
                            response_types[status_code] = f"List[{self.sanitize_name(self.data["info"]["title"])}_Type.{type_name}]"
                        else:
                            response_types[status_code] = 'Any'
                    methods_code += self.generate_api_method(method, function, params, response_types, indent_amount)
            return methods_code

        @staticmethod
        def generate_api_method(method: str, function: str, params: List[Dict[str, str]], response_types: Dict[int, str], indent_amount: int) -> str:
            indent = "    " * indent_amount
            param_str = ", ".join([f"{param['name']}:{param['type']}" for param in params])
            wanted_output = Generator.PythonGenerator.get_response_type(response_types, 200)
            response_type = Generator.PythonGenerator.get_response_type(response_types)
            if response_type == "Any":
                response_type_annotation = "Any"
            else:
                response_type_annotation = response_type
            
            return f"""
{indent}def {method}{Generator.PythonGenerator.sanitize_name(function.replace("{", "").replace('}', ""))}(
{indent}    self, 
{indent}    {param_str}
{indent}) -> ResponseDict[{response_type_annotation}]:
{indent}    url = self._base_url + "{function}".format(
{indent}        {", ".join([f"{param['name']}={param['name']}" for param in params])}
{indent}    )
{indent}    self._client.headers["Content-Type"] = "application/json"

{indent}    httpResponse = self._client.request(
{indent}        method="{method}",
{indent}        url=url,
{indent}    )

{indent}    response_data = ResponseDict[{response_type_annotation}]()
{indent}    try:
{indent}        json_data = httpResponse.json()
{indent}        if isinstance(json_data, list):
{indent}            response_data.data = [ {wanted_output.removeprefix('List[').removesuffix(']') + '(**item)' if wanted_output != 'Any' else 'item'} for item in json_data ]
{indent}        else:
{indent}            response_data.data = { wanted_output.removeprefix('List[').removesuffix(']') + '(**json_data)' if wanted_output != 'Any' else 'json_data' }
{indent}    except:
{indent}        response_data.data = None
{indent}    response_data.text = httpResponse.text
{indent}    response_data.status_code = httpResponse.status_code

{indent}    return response_data
"""

        class Object_Class_Generator:

            @staticmethod
            def detect_circular_import(schema: Dict[str, Any], parent_class: str) -> bool:
                if "$ref" in schema:
                    ref = schema["$ref"].split("/")[-1]
                    return ref == parent_class
                if "properties" in schema:
                    for prop in schema["properties"].values():
                        if Generator.PythonGenerator.Object_Class_Generator.detect_circular_import(prop, parent_class):
                            return True
                return False
            
            @staticmethod
            def detect_reference(schema: Dict[str, Any], module: str = "", visited_references: Optional[set] = None, resident: str = "") -> str:
                if visited_references is None:
                    visited_references = set()
                print("Detecting references in schema...")
                if "properties" not in schema:
                    return None
                print(f"Checking schema: {schema}")
                properties = schema["properties"]
                references = []
                for name, prop in properties.items():
                    print(f"Checking property: {name}")
                    if "$ref" in prop:
                        ref = prop["$ref"].split("/")[-1]
                        if ref in visited_references or ref == module.split('.')[-1] or ref == resident:
                            continue
                        print(f"Found reference: {ref}")
                        if ref not in references:
                            print(f"Adding reference: {ref}")
                            references.append(ref)
                            visited_references.add(ref)
                    elif "allOf" in prop:
                        for sub_prop in prop["allOf"]:
                            if "$ref" in sub_prop:
                                ref = sub_prop["$ref"].split("/")[-1]
                                if ref in visited_references or ref == module.split('.')[-1] or ref == resident:
                                    continue
                                print(f"Found reference in allOf: {ref}")
                                if ref not in references:
                                    print(f"Adding reference: {ref}")
                                    references.append(ref)
                                    visited_references.add(ref)
                    elif "type" in prop and prop["type"] == "array" and "items" in prop:
                        items = prop["items"]
                        if "$ref" in items:
                            ref = items["$ref"].split("/")[-1]
                            if ref in visited_references or ref == module.split('.')[-1] or ref == resident:
                                continue
                            print(f"Found reference in list: {ref}")
                            if ref not in references:
                                print(f"Adding reference: {ref}")
                                references.append(ref)
                                visited_references.add(ref)
                ref_code = None
                for ref in references:
                    if ref_code is None:
                        ref_code = ""
                    print(f"Generating reference code for: {ref}")
                    # ref_code += f"from {module+'.Types' if module else ''}.{Generator.PythonGenerator.sanitize_name(ref)} import {Generator.PythonGenerator.sanitize_name(ref)}\n"
                print(f"Generated reference code: {ref_code}")
                return ref_code

                
                
            @staticmethod
            def find_type(schema: Dict[str, Any], python_conversion: Dict[str, str], parent_class: str = "", sub: bool=False, resident: str = "") -> str:
                if "enum" in schema:
                    return f"Type['{Generator.PythonGenerator.sanitize_name(schema['$ref'].split('/')[-1])}']" if '$ref' in schema else "Any"
                if "$ref" in schema:
                    print(f"Checking reference: {schema['$ref'].split('/')[-1]} == {resident}")
                    if resident == Generator.PythonGenerator.sanitize_name(schema['$ref'].split('/')[-1]):
                        return "Any"
                    return f"Type['{Generator.PythonGenerator.sanitize_name(schema['$ref'].split('/')[-1])}']"
                if "allOf" in schema:
                    r = []
                    for sub_schema in schema["allOf"] if isinstance(schema["allOf"], list) else [schema["allOf"]]:
                        s = Generator.PythonGenerator.Object_Class_Generator.find_type(sub_schema, python_conversion, parent_class, True, resident=resident)
                        if s is not None and f"Type['{Generator.PythonGenerator.sanitize_name(sub_schema['$ref'].split('/')[-1])}']" not in r:
                            r.append(f"Type['{Generator.PythonGenerator.sanitize_name(sub_schema['$ref'].split('/')[-1])}']" if s is None else s)
                    if len(r) == 1:
                        return r[0]
                    return f"Union[{', '.join(r)}]"
                if "type" in schema:
                    if schema["type"] == "string":
                        return "str"
                    if schema["type"] == "array":
                        return f"List[{Generator.PythonGenerator.Object_Class_Generator.find_type(schema['items'], python_conversion, parent_class, resident=resident) if 'items' in schema else 'Any'}]"
                    if schema["type"] == "object" and "properties" in schema:
                        for prop_name, prop_schema in schema["properties"].items():
                            s = Generator.PythonGenerator.Object_Class_Generator.find_type(prop_schema, python_conversion, parent_class, True, resident=resident)
                            if s is None:
                                return None
                        if "$ref" in schema:
                            return f"Type['{Generator.PythonGenerator.sanitize_name(schema['$ref'].split('/')[-1])}']"
                        else:
                            if sub:
                                return None
                            else:
                                return "Any"
                    return python_conversion['types'][schema['type']]
                if sub:
                    return None
                else:
                    return "Any"

            @staticmethod
            def generate_object_class(class_name: str, properties: Dict[str, Any], python_conversion: Dict[str, str], parent_class: str, sublevel: int = 0, module: str = "") -> str:
                indent = "    " * sublevel
                class_code = f"{indent}@dataclass\n"
                class_code += f"{indent}class {class_name}:\n"
                class_code += f"{indent}    def __init__(self, **kwargs):\n"
                class_code += f"{indent}        self.bind_dict_to_dataclass(kwargs)\n\n"
                class_code += f"{indent}    def __dict__(self):\n"
                class_code += f"{indent}        return {{\n"
                for prop_name in properties.keys():
                    class_code += f"{indent}            '{prop_name}': self.{Generator.PythonGenerator.sanitize_name(prop_name)},\n"
                class_code += f"{indent}        }}\n\n"
                class_code += f"{indent}    def bind_dict_to_dataclass(cls, data: Dict[str, Any]):\n"
                class_code += f"{indent}        fieldtypes = {{f.name: f.type for f in fields(cls)}}\n"
                class_code += f"{indent}        bound_data = {{}}\n"
                class_code += f"{indent}        for key, value in data.items():\n"
                class_code += f"{indent}            if key in fieldtypes:\n"
                class_code += f"{indent}                field_type = fieldtypes[key]\n"
                class_code += f"{indent}                if hasattr(field_type, '__dataclass_fields__'):\n"
                class_code += f"{indent}                    bound_data[key] = cls.bind_dict_to_dataclass(field_type, value)\n"
                class_code += f"{indent}                elif isinstance(value, list) and hasattr(field_type.__args__[0], '__dataclass_fields__'):\n"
                class_code += f"{indent}                    bound_data[key] = [cls.bind_dict_to_dataclass(field_type.__args__[0], item) for item in value]\n"
                class_code += f"{indent}                else:\n"
                class_code += f"{indent}                    bound_data[key] = value\n"
                class_code += f"{indent}        return cls(**bound_data)\n\n\n\n"
                imports = []
                imports.append(f"import importlib\n")
                for prop_name, prop_schema in properties.items():
                    prop_type = Generator.PythonGenerator.Object_Class_Generator.find_type(prop_schema, python_conversion, parent_class, resident=class_name)
                    if "$ref" in prop_schema:
                        ref_type = prop_schema["$ref"].split("/")[-1]
                        imports.append(f"{Generator.PythonGenerator.sanitize_name(ref_type)} = importlib.import_module('{module}.Types.{Generator.PythonGenerator.sanitize_name(ref_type)}.{Generator.PythonGenerator.sanitize_name(ref_type)}')")
                    types = 'None'
                    if prop_type is None:
                        types = 'Any'
                    elif prop_type.startswith('List['):
                        types = 'field(init=False, default_factory=list[' + prop_type.removeprefix('List[').removesuffix(']') + '])'
                    else:
                        types = 'field(init=False, default_factory=' + prop_type + ')' if prop_type != 'Any' else None
                    
                    class_code += f"{indent}    {Generator.PythonGenerator.sanitize_name(prop_name)}: {prop_type} = {types}\n"
                    if "type" in prop_schema and prop_schema["type"] == "object" and "properties" in prop_schema:
                        nested_class_code = Generator.PythonGenerator.Object_Class_Generator.generate_object_class(
                            Generator.PythonGenerator.sanitize_name(prop_name), prop_schema["properties"], python_conversion, parent_class, sublevel + 1, module
                        )
                        class_code += nested_class_code
                return "\n".join(imports) + "\n\n" + class_code

            @staticmethod
            def ensure_class_type(schema: Dict[str, Any], class_name: str) -> str:
                if "type" in schema and schema["type"] == "string":
                    return f"class {class_name}:\n    value: str\n"
                return ""

        class Enum_Generator:
            python_keywords = {"False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"}

            @staticmethod
            def generate_enum(enum_name: str, enum_values: List[str]) -> str:
                enum_code = f"class {enum_name}:\n"
                for value in enum_values:
                    if value in Generator.PythonGenerator.Enum_Generator.python_keywords:
                        enum_code += f"    {value}_ = '{value}'\n"
                    else:
                        enum_code += f"    {value} = '{value}'\n"
                return enum_code

        @staticmethod
        def generate_string(name: str, sublevel: int) -> str:
            if(sublevel == 0):
                return f"class {name}:\n\
    value: str\n"
            return ("    " * sublevel) + f"{name}: str\n"

        @staticmethod
        def sanitize_name(name: str) -> str:
            for char in Generator.PythonGenerator.invalid_chars:
                name = name.replace(char, "_")
            return name
        
        @staticmethod
        def get_response_type(response: Dict[str, Any], requested_status_code:int|None = None) -> str:
            r = []
            if requested_status_code is not None:
                return response.get(str(requested_status_code), 'Any')
            for status_code, response_type in response.items():
                if response_type != 'Any':
                    r.append(response_type)
            if(len(r) == 0):
                return "Any"
            if len(r) == 1:
                return r[0]
            return f"Union[{', '.join(r)}]"

    class JavascriptGenerator:
        file_extension = ".js"
        
        def __init__(self, data: Dict[str, Any]):
            self.data = data
            
        def start(self, module_name: str|None = None):
            self.data["sanitize_name"] = lambda name: self.sanitize_name(name)
            self.data["generate_api_methods"] = self.generate_api_methods(self.data["paths"], self.data["info"])

        @staticmethod
        def sanitize_name(name: str) -> str:
            invalid_chars = [".", "[", "]", ",", "=", " ", ":", "`", "-", "/", "<", ">", "(", ")", "&", "%", "$", "#", "@", "!", "^", "*", "+", "?", "|", "\\"]
            for char in invalid_chars:
                name = name.replace(char, "_")
            return name

        def generate_api_methods(self, paths: Dict[str, Any], info: Dict[str, Any]) -> str:
            methods_code = ""
            for function, methods in paths.items():
                for method, details in methods.items():
                    params = []
                    for param in details.get("parameters", []):
                        if param["in"] == "path":
                            param_type = 'Any'
                            params.append({"name": param["name"], "type": param_type})
                    methods_code += self.generate_api_method(method, function, params)
            return methods_code

        def generate_api_method(self, method: str, function: str, params: List[Dict[str, str]]) -> str:
            param_str = ", ".join([f"{param['name']}" for param in params])
            return f"""
    async {method}{self.sanitize_name(function.replace("{", "").replace('}', ""))}({param_str}) {{
        const url = `{'${this.baseUrl}'}{function.replace("{", "${")}`;
        const response = await fetch(url, {{
            method: '{method.upper()}',
            headers: {{
                'Content-Type': 'application/json'
            }}
        }});
        return response.json();
    }}
"""