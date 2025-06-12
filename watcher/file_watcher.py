# file_watcher.py
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import tempfile
import os
from dotenv import load_dotenv

gauth = GoogleAuth(settings_file="settings.yaml")
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

load_dotenv()
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

def get_latest_file_in_folder(folder_id=FOLDER_ID):
    file_list = drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false",
        'orderBy': 'modifiedDate desc'
    }).GetList()

    if file_list:
        latest_file = file_list[0]
        file_id = latest_file['id']
        file_title = latest_file['title']

        # Create a temp file path
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file_title)
        latest_file.GetContentFile(temp_path)

        print(f"[Downloaded] {file_title} to temp path: {temp_path}")
        return temp_path, file_id
    else:
        print("No files found in the folder.")
        return None, None

if __name__ == "__main__":
    filepath, file_id = get_latest_file_in_folder()
    if filepath:
        print(f"[Success] Filepath: {filepath}")
        print(f"[Success] File ID: {file_id}")
    else:
        print("[Warning] No file found or failed to download.")
