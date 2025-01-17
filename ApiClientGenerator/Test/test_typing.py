import unittest
from Typing import Contact, License, Info, Tags, Response, ServerVariable, Server, ExternalDocumentation, Tag, Reference, Property, Schema, Parameter, Operation, Path, Components, Methods, OpenAPI
from dacite import from_dict, Config


class TestTyping(unittest.TestCase):

    def test_contact(self):
        contact = from_dict(data={"name": "John Doe", "url": "http://example.com", "email": "john.doe@example.com"}, data_class=Contact)
        self.assertEqual(contact.name, "John Doe")
        self.assertEqual(contact.url, "http://example.com")
        self.assertEqual(contact.email, "john.doe@example.com")

    def test_license(self):
        license = from_dict(data={"name": "MIT", "url": "http://opensource.org/licenses/MIT"}, data_class=License)
        self.assertEqual(license.name, "MIT")
        self.assertEqual(license.url, "http://opensource.org/licenses/MIT")

    def test_info(self):
        contact = from_dict(data={"name": "John Doe", "url": "http://example.com", "email": "john.doe@example.com"}, data_class=Contact)
        license = from_dict(data={"name": "MIT", "url": "http://opensource.org/licenses/MIT"}, data_class=License)
        info = from_dict(data={"title": "API", "description": "API description", "termsOfService": "http://example.com/terms", "contact": contact, "license": license, "version": "1.0.0"}, data_class=Info)
        self.assertEqual(info.title, "API")
        self.assertEqual(info.description, "API description")
        self.assertEqual(info.termsOfService, "http://example.com/terms")
        self.assertEqual(info.contact, contact)
        self.assertEqual(info.license, license)
        self.assertEqual(info.version, "1.0.0")

    def test_tags(self):
        tags = from_dict(data={"name": "tag1", "description": "Tag description"}, data_class=Tags)
        self.assertEqual(tags.name, "tag1")
        self.assertEqual(tags.description, "Tag description")

    def test_response(self):
        schema = from_dict(data={"title": "Schema", "type": "object"}, data_class=Schema)
        response = from_dict(data={"description": "Response description", "content": {"application/json": {"schema": schema}}}, data_class=Response)
        self.assertEqual(response.description, "Response description")
        self.assertEqual(response.content["application/json"]["schema"], schema)

    def test_server_variable(self):
        server_variable = from_dict(data={"enum": ["value1", "value2"], "default": "value1", "description": "Server variable description"}, data_class=ServerVariable)
        self.assertEqual(server_variable.enum, ["value1", "value2"])
        self.assertEqual(server_variable.default, "value1")
        self.assertEqual(server_variable.description, "Server variable description")

    def test_server(self):
        server_variable = from_dict(data={"enum": ["value1", "value2"], "default": "value1", "description": "Server variable description"}, data_class=ServerVariable)
        server = from_dict(data={"url": "http://example.com", "description": "Server description", "variables": {"variable": server_variable}}, data_class=Server)
        self.assertEqual(server.url, "http://example.com")
        self.assertEqual(server.description, "Server description")
        self.assertEqual(server.variables["variable"], server_variable)

    def test_external_documentation(self):
        external_docs = from_dict(data={"description": "External docs description", "url": "http://example.com"}, data_class=ExternalDocumentation)
        self.assertEqual(external_docs.description, "External docs description")
        self.assertEqual(external_docs.url, "http://example.com")

    def test_tag(self):
        external_docs = from_dict(data={"description": "External docs description", "url": "http://example.com"}, data_class=ExternalDocumentation)
        tag = from_dict(data={"name": "tag1", "description": "Tag description", "externalDocs": external_docs}, data_class=Tag)
        self.assertEqual(tag.name, "tag1")
        self.assertEqual(tag.description, "Tag description")
        self.assertEqual(tag.externalDocs, external_docs)

    def test_reference(self):
        reference = from_dict(data={"ref": "#/components/schemas/Schema"}, data_class=Reference)
        self.assertEqual(reference.ref, "#/components/schemas/Schema")

    def test_property(self):
        property = from_dict(data={"type": "string", "format": "date-time", "description": "Property description"}, data_class=Property)
        self.assertEqual(property.type, "string")
        self.assertEqual(property.format, "date-time")
        self.assertEqual(property.description, "Property description")

    def test_schema(self):
        property = from_dict(data={"type": "string", "format": "date-time", "description": "Property description"}, data_class=Property)
        schema = from_dict(data={"title": "Schema", "type": "object", "properties": {"property": property}}, data_class=Schema)
        self.assertEqual(schema.title, "Schema")
        self.assertEqual(schema.type, "object")
        self.assertEqual(schema.properties["property"], property)

    def test_parameter(self):
        schema = from_dict(data={"title": "Schema", "type": "object"}, data_class=Schema)
        parameter = from_dict(data={"in_": "query", "name": "param", "schema": schema, "required": True}, data_class=Parameter)
        self.assertEqual(parameter.in_, "query")
        self.assertEqual(parameter.name, "param")
        self.assertEqual(parameter.schema, schema)
        self.assertEqual(parameter.required, True)

    def test_operation(self):
        parameter = from_dict(data={"in_": "query", "name": "param", "schema": None, "required": True}, data_class=Parameter)
        response = from_dict(data={"description": "Response description", "content": None}, data_class=Response)
        operation = from_dict(data={"summary": "Operation summary", "description": "Operation description", "operationId": "operationId", "parameters": [parameter], "requestBody": None, "responses": {"200": response}, "tags": ["tag1"]}, data_class=Operation)
        self.assertEqual(operation.summary, "Operation summary")
        self.assertEqual(operation.description, "Operation description")
        self.assertEqual(operation.operationId, "operationId")
        self.assertEqual(operation.parameters[0], parameter)
        self.assertEqual(operation.responses["200"], response)
        self.assertEqual(operation.tags, ["tag1"])

    def test_path(self):
        parameter = from_dict(data={"in_": "query", "name": "param", "schema": None, "required": True}, data_class=Parameter)
        response = from_dict(data={"description": "Response description", "content": None}, data_class=Response)
        path = from_dict(data={"summary": "Path summary", "parameters": [parameter], "responses": {"200": response}, "tags": ["tag1"]}, data_class=Path)
        self.assertEqual(path.summary, "Path summary")
        self.assertEqual(path.parameters[0], parameter)
        self.assertEqual(path.responses["200"], response)
        self.assertEqual(path.tags, ["tag1"])

    def test_components(self):
        schema = from_dict(data={"title": "Schema", "type": "object"}, data_class=Schema)
        response = from_dict(data={"description": "Response description", "content": None}, data_class=Response)
        parameter = from_dict(data={"in_": "query", "name": "param", "schema": None, "required": True}, data_class=Parameter)
        components = from_dict(data={"schemas": {"Schema": schema}, "responses": {"Response": response}, "parameters": {"Parameter": parameter}, "examples": None, "requestBodies": None, "headers": None, "securitySchemes": None, "links": None, "callbacks": None}, data_class=Components)
        self.assertEqual(components.schemas["Schema"], schema)
        self.assertEqual(components.responses["Response"], response)
        self.assertEqual(components.parameters["Parameter"], parameter)

    def test_methods(self):
        path = from_dict(data={"summary": "Path summary", "parameters": None, "responses": None, "tags": None}, data_class=Path)
        methods = from_dict(data={"get": path, "put": None, "post": None, "delete": None, "options": None, "head": None, "patch": None, "trace": None}, data_class=Methods)
        self.assertEqual(methods.get, path)
        self.assertEqual(methods.put, None)
        self.assertEqual(methods.post, None)
        self.assertEqual(methods.delete, None)
        self.assertEqual(methods.options, None)
        self.assertEqual(methods.head, None)
        self.assertEqual(methods.patch, None)
        self.assertEqual(methods.trace, None)

    def test_openapi(self):
        contact = from_dict(data={"name": "John Doe", "url": "http://example.com", "email": "john.doe@example.com"}, data_class=Contact)
        license = from_dict(data={"name": "MIT", "url": "http://opensource.org/licenses/MIT"}, data_class=License)
        info = from_dict(data={"title": "API", "description": "API description", "termsOfService": "http://example.com/terms", "contact": contact, "license": license, "version": "1.0.0"}, data_class=Info)
        server = from_dict(data={"url": "http://example.com", "description": "Server description", "variables": None}, data_class=Server)
        path = from_dict(data={"summary": "Path summary", "parameters": None, "responses": None, "tags": None}, data_class=Path)
        methods = from_dict(data={"get": path, "put": None, "post": None, "delete": None, "options": None, "head": None, "patch": None, "trace": None}, data_class=Methods)
        openapi = from_dict(data={"openapi": "3.0.0", "info": info, "servers": [server], "paths": {"/path": methods}, "components": None, "security": None, "tags": None, "externalDocs": None}, data_class=OpenAPI)
        self.assertEqual(openapi.openapi, "3.0.0")
        self.assertEqual(openapi.info, info)
        self.assertEqual(openapi.servers[0], server)
        self.assertEqual(openapi.paths["/path"], methods)
        self.assertEqual(openapi.components, None)
        self.assertEqual(openapi.security, None)
        self.assertEqual(openapi.tags, None)
        self.assertEqual(openapi.externalDocs, None)

if __name__ == '__main__':
    unittest.main()