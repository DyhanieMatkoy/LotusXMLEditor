import sys
import os
import winreg
from PyQt6.QtWidgets import QMessageBox

def register_context_menu(app_path=None):
    """
    Register LotusXMLEditor in Windows Explorer context menu for .xml and .zip files.
    """
    if app_path is None:
        # Assuming running as python script
        python_exe = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        # If frozen (installer), logic would differ, but for this env:
        command_str = f'"{python_exe}" "{script_path}" "%1"'
    else:
        command_str = f'"{app_path}" "%1"'

    extensions = ['.xml', '.zip']
    menu_name = "Open with Lotus XMLEditor"
    
    success_count = 0
    errors = []

    for ext in extensions:
        try:
            # We use SystemFileAssociations for cleaner integration that doesn't override defaults
            # HKCU\Software\Classes\SystemFileAssociations\{ext}\shell\Open with Lotus XMLEditor\command
            key_path = f"Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\{menu_name}"
            
            # Create shell key
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, menu_name)
                # Optional: Add icon
                # winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, script_path) 
            
            # Create command key
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\command") as cmd_key:
                winreg.SetValue(cmd_key, "", winreg.REG_SZ, command_str)
            
            success_count += 1
        except Exception as e:
            errors.append(f"{ext}: {str(e)}")

    if errors:
        return False, "\n".join(errors)
    return True, f"Successfully registered for {success_count} extensions."

def unregister_context_menu():
    """
    Remove LotusXMLEditor from Windows Explorer context menu.
    """
    extensions = ['.xml', '.zip']
    menu_name = "Open with Lotus XMLEditor"
    
    success_count = 0
    errors = []

    for ext in extensions:
        try:
            key_path = f"Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\{menu_name}"
            
            # Delete command subkey
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\command")
            except FileNotFoundError:
                pass # Already gone
            
            # Delete shell key
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            except FileNotFoundError:
                pass # Already gone
                
            success_count += 1
        except Exception as e:
            errors.append(f"{ext}: {str(e)}")

    if errors:
        return False, "\n".join(errors)
    return True, "Context menu entries removed."
