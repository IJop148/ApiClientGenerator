import json
import jinja2
from glob import glob
import os
from typing import Any, Dict
from .Generators import Generator

def load_template(template_path: str) -> jinja2.Template:
    with open(template_path, 'r') as template_file:
        template_content = template_file.read()
    return jinja2.Template(template_content)

def load_json(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r') as file:
        return json.load(file)

def render_template(template: jinja2.Template, data: Dict[str, Any]) -> str:
    return template.render(data)

def save_output(content: str, output_path: str) -> None:
    if not os.path.exists("Output"):
        print("Creating Output directory")
        os.mkdir("Output")
    with open(output_path, 'w') as output_file:
        output_file.write(content)

def main(__module_name_usage__: bool = False) -> None:
    base_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(base_path)

    for template_file in glob('templates/*.jinja2'):
        template = load_template(template_file)
        type_of_template = os.path.basename(template_file).replace('.jinja2', '')
        engine_to_use = f"{type_of_template}Generator"
        
        engine_class = getattr(Generator, engine_to_use, Generator.PythonGenerator)
        for file in glob('ToBeGenerated/*.json'):
            data = load_json(file)
            engine_instance = engine_class(data)
            
            file_name = engine_instance.sanitize_name(data['info']['title'])
            if getattr(engine_instance, 'file_output_folder', None) is not None:
                save_output_folder = engine_instance.file_output_folder
            else:
                save_output_folder = f"Output/{type_of_template}/{file_name}"
                
            if __module_name_usage__:
                subtract_prefix_count = save_output_folder.count("../")
                save_output_folder_module = save_output_folder.replace("../", "", subtract_prefix_count)
                save_output_folder_module = save_output_folder_module.replace("/", ".")
                prefix_as_list = __name__.split(".")[:-1]
                if(subtract_prefix_count > 0):
                    prefix_as_list = prefix_as_list[:-subtract_prefix_count]
                prefix = ".".join(prefix_as_list)
                __module_name__ = f"{prefix.removeprefix(".").replace("..", ".")}.{save_output_folder_module}"
            else:
                __module_name__ = None
                
            print(f"Generating {type_of_template} from {file} using {__module_name__}")
            engine_instance.start(__module_name__)
            
            if type_of_template == "Python":
                engine_instance.generate_types(data)
            
            output_content = render_template(template, data)
            
            if not os.path.exists(save_output_folder):
                os.makedirs(save_output_folder)
            save_output_path = f"{save_output_folder}/{file_name}{engine_class.file_extension}"
            save_output(output_content, save_output_path)
            print(f"Generated {save_output_path}")

if __name__ == "__main__":
    main()
