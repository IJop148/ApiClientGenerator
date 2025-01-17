import os
import argparse
from .main import main, Settings

if __name__ == "__main__":
    # Set current working directory to the directory of the script
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    input_folder = None
    output_folder = None
    settings = Settings()
    parser = argparse.ArgumentParser(description="API Client Generator")
    parser.add_argument("--input", "-i", type=str, help="Input folder")
    parser.add_argument("--output", "-o", type=str, help="Output folder")
    parser.add_argument("--python", "-py", nargs='*', help="Enable Python clients")
    parser.add_argument("--javascript", "-js", nargs='*', help="Enable JavaScript clients")

    args = parser.parse_args()

    input_folder = args.input
    output_folder = args.output

    if args.python:
        for client in args.python:
            settings.Python[client] = True

    if args.javascript:
        for client in args.javascript:
            settings.Javascript[client] = True
    
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Python clients: {settings.Python}")
    print(f"JavaScript clients: {settings.Javascript}")

    main(input_folder=input_folder, output_folder=output_folder, settings=settings)
