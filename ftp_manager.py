import os
import json
import ftplib
import tempfile
import shutil
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from PyQt6.QtCore import QSettings

@dataclass
class FtpProfile:
    id: str
    name: str
    host: str
    port: int = 21
    user: str = "anonymous"
    password: str = ""
    passive_mode: bool = True
    remote_path: str = "/"
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class FtpManager:
    def __init__(self):
        self.settings = QSettings("visxml.net", "LotusXmlEditor")
        self.profiles: List[FtpProfile] = []
        self._load_profiles()
        
    def _load_profiles(self):
        """Load profiles from QSettings"""
        profiles_json = self.settings.value("ftp_profiles", "[]")
        try:
            profiles_data = json.loads(profiles_json)
            self.profiles = [FtpProfile.from_dict(p) for p in profiles_data]
        except Exception as e:
            print(f"Error loading FTP profiles: {e}")
            self.profiles = []

    def save_profiles(self):
        """Save profiles to QSettings"""
        profiles_data = [asdict(p) for p in self.profiles]
        self.settings.setValue("ftp_profiles", json.dumps(profiles_data))
        
    def add_profile(self, profile: FtpProfile):
        self.profiles.append(profile)
        self.save_profiles()
        
    def update_profile(self, profile: FtpProfile):
        for i, p in enumerate(self.profiles):
            if p.id == profile.id:
                self.profiles[i] = profile
                break
        self.save_profiles()
        
    def delete_profile(self, profile_id: str):
        self.profiles = [p for p in self.profiles if p.id != profile_id]
        self.save_profiles()
        
    def get_profile(self, profile_id: str) -> Optional[FtpProfile]:
        for p in self.profiles:
            if p.id == profile_id:
                return p
        return None

    def connect(self, profile: FtpProfile) -> ftplib.FTP:
        """Connect to FTP server"""
        ftp = ftplib.FTP()
        ftp.connect(profile.host, profile.port)
        ftp.login(profile.user, profile.password)
        ftp.set_pasv(profile.passive_mode)
        if profile.remote_path:
            try:
                ftp.cwd(profile.remote_path)
            except Exception:
                # If path doesn't exist, stay in root or handle error
                pass 
        return ftp

    def list_files(self, ftp: ftplib.FTP, path: str = ".") -> List[Dict]:
        """List files and directories in the given path"""
        items = []
        original_cwd = ftp.pwd()
        
        try:
            if path != ".":
                ftp.cwd(path)
            
            # Use MLSD if available (better parsing), otherwise LIST
            # For simplicity and compatibility, we'll try to use a custom parser or just LIST
            # ftplib.mlsd() is available in Python 3.3+
            
            try:
                for name, facts in ftp.mlsd():
                    if name in [".", ".."]:
                        continue
                    is_dir = facts.get('type') == 'dir'
                    size = int(facts.get('size', 0))
                    items.append({
                        "name": name,
                        "is_dir": is_dir,
                        "size": size,
                        "path": os.path.join(path, name).replace("\\", "/")
                    })
            except ftplib.error_perm:
                # Fallback to LIST if MLSD not supported
                lines = []
                ftp.dir(lines.append)
                for line in lines:
                    parts = line.split()
                    if len(parts) < 9:
                        continue
                    name = " ".join(parts[8:])
                    if name in [".", ".."]:
                        continue
                    is_dir = line.startswith("d")
                    size = int(parts[4])
                    items.append({
                        "name": name,
                        "is_dir": is_dir,
                        "size": size,
                        "path": os.path.join(path, name).replace("\\", "/")
                    })
                    
        finally:
            ftp.cwd(original_cwd)
            
        return sorted(items, key=lambda x: (not x['is_dir'], x['name']))

    def download_file(self, ftp: ftplib.FTP, remote_path: str, local_path: str):
        """Download file from FTP"""
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f"RETR {remote_path}", f.write)

    def upload_file(self, ftp: ftplib.FTP, local_path: str, remote_path: str):
        """Upload file to FTP"""
        with open(local_path, 'rb') as f:
            ftp.storbinary(f"STOR {remote_path}", f)
            
    def get_temp_file_path(self, filename: str) -> str:
        """Get a path in the temp directory"""
        return os.path.join(tempfile.gettempdir(), "lotus_ftp", filename)

    def ensure_temp_dir(self):
        """Ensure temp directory exists"""
        temp_dir = os.path.join(tempfile.gettempdir(), "lotus_ftp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        return temp_dir
