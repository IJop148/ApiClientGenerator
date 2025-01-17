import os
from main import main

if __name__ == "__main__":
    # Set current working directory to the directory of the script
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    main()
