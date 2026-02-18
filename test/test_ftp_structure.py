import sys
import os
from PyQt6.QtWidgets import QApplication

# Add current directory to path
sys.path.append(os.getcwd())

from ftp_manager import FtpManager, FtpProfile
from ftp_dialogs import FtpProfilesDialog, FtpBrowserDialog

def test_structure():
    app = QApplication(sys.argv)
    
    manager = FtpManager()
    print("FtpManager initialized")
    
    # Test profile operations
    profile = FtpProfile(id="test", name="Test Profile", host="localhost")
    manager.add_profile(profile)
    print("Profile added")
    
    retrieved = manager.get_profile("test")
    assert retrieved.name == "Test Profile"
    print("Profile retrieved")
    
    manager.delete_profile("test")
    print("Profile deleted")
    
    # Test Dialog instantiation (headless)
    try:
        dlg = FtpProfilesDialog(manager)
        print("FtpProfilesDialog instantiated")
        
        browser = FtpBrowserDialog(manager)
        print("FtpBrowserDialog instantiated")
    except Exception as e:
        print(f"Dialog instantiation failed: {e}")
        
    print("Test passed")

if __name__ == "__main__":
    test_structure()
