
import sys
import os
import zipfile
import subprocess
import time
from PyQt6.QtWidgets import QApplication

def create_dummy_zip():
    zip_name = "test_archive.zip"
    with zipfile.ZipFile(zip_name, 'w') as z:
        z.writestr("file1.xml", "<root>Content 1</root>")
        z.writestr("ExchangeRules.xml", "<root>Rules</root>")
    return zip_name

if __name__ == "__main__":
    zip_path = os.path.abspath(create_dummy_zip())
    print(f"Created {zip_path}")
    
    # Launch the application with the zip file as argument
    # We assume 'python main.py' is how to run it
    cmd = [sys.executable, "main.py", zip_path]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.Popen(cmd)
    
    print("Application launched. Please verify if the file chooser dialog appears.")
    print("If the editor shows binary content (PK...), then the issue is reproduced.")
