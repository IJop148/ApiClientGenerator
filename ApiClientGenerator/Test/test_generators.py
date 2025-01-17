import unittest
from unittest.mock import MagicMock, patch
from Generators import Python
from Typing import OpenAPI, Info, Contact, License, Server, Path, Methods
from dacite import from_dict

class TestPythonGenerator(unittest.TestCase):

    def setUp(self):
        contact = from_dict(data={"name": "John Doe", "url": "http://example.com", "email": "john.doe@example.com"}, data_class=Contact)
        license = from_dict(data={"name": "MIT", "url": "http://opensource.org/licenses/MIT"}, data_class=License)
        info = from_dict(data={"title": "API", "description": "API description", "termsOfService": "http://example.com/terms", "contact": contact, "license": license, "version": "1.0.0"}, data_class=Info)
        server = from_dict(data={"url": "http://example.com", "description": "Server description", "variables": None}, data_class=Server)
        path = from_dict(data={"summary": "Path summary", "parameters": None, "responses": None, "tags": None}, data_class=Path)
        methods = from_dict(data={"get": path, "put": None, "post": None, "delete": None, "options": None, "head": None, "patch": None, "trace": None}, data_class=Methods)
        self.openapi_data = from_dict(data={"openapi": "3.0.0", "info": info, "servers": [server], "paths": {"/path": methods}, "components": None, "security": None, "tags": None, "externalDocs": None}, data_class=OpenAPI)
        self.template = MagicMock()

    @patch('Generators.Python.TypeGenerator')
    @patch('Generators.Python.ClientGenerator')
    @patch('jinja2.Template')
    def test_generate(self, MockTemplate, MockClientGenerator, MockTypeGenerator):
        mock_type_generator = MockTypeGenerator.return_value
        mock_type_generator.generate.return_value = ["type_definitions"]
        mock_client_generator = MockClientGenerator.return_value
        mock_client_generator.generate.return_value = "client_code"

        generator = Python(self.openapi_data, self.template)
        self.template.render.return_value = "rendered_template"
        generator.generate()

        mock_type_generator.generate.assert_called_once()
        mock_client_generator.generate.assert_called_once()
        self.template.render.assert_called_once_with(
            Imports=[
                "import httpx",
                "import json",
                "from typing import Any, Dict, Optional, Union, List, TypeVar, Generic, Type",
                "from enum import Enum",
                "from dataclasses import dataclass",
                "from dacite import from_dict",
            ],
            Enum="",
            DataClass="type_definitions",
            Methods="client_code"
        )

    def test_sanitize_string(self):
        self.assertEqual(Python.sanitize_string("example-string"), "example_string")
        self.assertEqual(Python.sanitize_string("123example"), "_123example")

if __name__ == '__main__':
    unittest.main()
