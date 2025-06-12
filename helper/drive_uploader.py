from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


gauth = GoogleAuth(settings_file="settings.yaml")
gauth.LocalWebserverAuth()  
drive = GoogleDrive(gauth)

def get_drive_uploader_email(file_id):
    try:
        file = drive.CreateFile({'id': file_id})
        file.FetchMetadata(fields='owners')
        owners = file.get('owners', [])
        if owners:
            return owners[0].get('emailAddress', 'unknown@uploader.com')
        return 'unknown@uploader.com'
    except Exception as e:
        print(f"Error fetching uploader email from Drive: {e}")
        return 'unknown@uploader.com'
