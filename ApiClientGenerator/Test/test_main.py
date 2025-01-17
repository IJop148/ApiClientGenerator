import unittest
from unittest.mock import patch, mock_open, MagicMock
import main
from Generators import Python
import json

class TestMain(unittest.TestCase):
    
    def setUp(self) -> None:
        pass
    
    
    @patch('builtins.open', new_callable=mock_open, read_data="{}")
    @patch('main.P')
    @patch("json.load")
    @patch("main.glob", return_value=["ToBeGenerated/test.json"])
    def test_main(self, mock_glob:MagicMock, mock_json_load: MagicMock, Python_Generator: MagicMock, mock_open:MagicMock) -> None:
        
        mock_json_load.return_value = {
            "openapi": "3.0.0",
            "info": {
                "title": "API",
                "version": "1.0.0"
            },
            "paths": {
                "/example": {
                    "get": {
                        "summary": "Example endpoint",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    }
                },
                "/another_example": {
                    "post": {
                        "summary": "Another example endpoint",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "201": {
                                "description": "Resource created"
                            }
                        }
                    }
                }
            }
        }

        mock_open.return_value.read.return_value = json.dumps(mock_json_load.return_value)

        mock_generator_instance = MagicMock(spec=Python)
        Python_Generator.return_value = mock_generator_instance

        main.main()

        mock_open.assert_any_call('ToBeGenerated/test.json', 'r')
        mock_open.assert_any_call('templates/Python.jinja2', 'r')
        mock_generator_instance.generate.assert_called_once()

    def test_ref_key_transformer(self):
        data = {
            "$ref": "some_ref",
            "in": "query",
            "nested": {
                "$ref": "nested_ref",
                "in": "header"
            }
        }
        transformed_data = main.ref_key_transformer(data)
        expected_data = {
            "ref": "some_ref",
            "in_": "query",
            "nested": {
                "ref": "nested_ref",
                "in_": "header"
            }
        }
        self.assertEqual(transformed_data, expected_data)

    @patch('builtins.open', new_callable=mock_open)
    @patch('main.P')
    @patch("json.load")
    @patch("main.glob", return_value=["ToBeGenerated/test.json"])
    @patch("main.P.TypeGenerator")
    def test_generate_api_client(self, python_typeGenerator:MagicMock, mock_glob: MagicMock, mock_json_load: MagicMock, Python_Generator: MagicMock, mock_open: MagicMock) -> None:
        mock_json_load.return_value = {
            "openapi": "3.0.0",
            "info": {
                "title": "API",
                "version": "1.0.0"
            },
            "paths": {
                "/example": {
                    "get": {
                        "summary": "Example endpoint",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "Example": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            }
                        }
                    }
                }
            }
        }

        mock_open.return_value.read.return_value = json.dumps(mock_json_load.return_value)

        mock_generator_instance = MagicMock(spec=Python)
        mock_generator_instance:Python = Python_Generator.return_value

        main.main()

        mock_open.assert_any_call('ToBeGenerated/test.json', 'r')
        mock_open.assert_any_call('templates/Python.jinja2', 'r')
        mock_open.assert_any_call("Output/API/ApiClient.py", "w")
        
        # Check if the generators is called
        mock_generator_instance.generate.assert_called_once()
        
        
        # Check if the file is correctly written
        mock_open.assert_any_call("Output/API/client.py", "w").write.assert_called_once()

        # Check if the output is correct
        output = mock_open.assert_any_call("Output/API/client.py", "w").write.call_args.args[0]
        functions_file_path = 'ApiClientGenerator/Output/API/ApiClient.py'
        with open(functions_file_path, "r") as f:
            expected_output = f.read()
        
        self.assertEqual(output, expected_output)
        
if __name__ == '__main__':
    unittest.main()
