import imaplib
import email
from email.header import decode_header
import os
import time
import schedule
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from dotenv import load_dotenv
import re
import uuid

load_dotenv()

gauth = GoogleAuth(settings_file="settings.yaml")
gauth.LocalWebserverAuth()  
drive = GoogleDrive(gauth)

EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

DOWNLOAD_FOLDER = "temp_downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def check_email_and_upload():
    print("Checking inbox...")
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        status, messages = mail.search(None, '(UNSEEN SUBJECT "invoice")')
        
        if status != 'OK':
            print("No messages found or search failed")
            return None
            
        email_ids = messages[0].split()
        
        if not email_ids:
            print("No unread invoice emails found")
            return None
            
        latest_email_id = email_ids[-1]
        print(f"Processing email ID: {latest_email_id.decode()}")
        
        res, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        
        if res != 'OK':
            print("Failed to fetch email")
            return None
            
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                try:
                    subject_header = msg.get("Subject", "No Subject")
                    if subject_header:
                        subject = decode_header(subject_header)[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode()
                    else:
                        subject = "No Subject"
                except Exception as e:
                    print(f"Error decoding subject: {e}")
                    subject = "No Subject"
                
                sender_email = extract_sender_email(msg)
                print(f"Processing email from: {sender_email}")
                print(f"Subject: {subject}")
                
                if msg.is_multipart():
                    attachment_found = False
                    for part in msg.walk():
                        try:
                            content_disposition = part.get("Content-Disposition", "")
                            print(f"Debug - Content-Disposition: {content_disposition}")
                            
                            if content_disposition and "attachment" in str(content_disposition):
                                attachment_found = True
                                filename = part.get_filename()
                                print(f"Debug - Original filename: {repr(filename)}")
                                
                                if not filename or filename.strip() == "":
                                    content_type = part.get_content_type() or "application/octet-stream"
                                    print(f"Debug - Content type: {content_type}")
                                    
                                    if "pdf" in content_type.lower():
                                        filename = f"invoice_{uuid.uuid4().hex[:8]}.pdf"
                                    elif "image" in content_type.lower():
                                        ext = content_type.split('/')[-1] if '/' in content_type else 'jpg'
                                        filename = f"invoice_{uuid.uuid4().hex[:8]}.{ext}"
                                    else:
                                        ext = content_type.split('/')[-1] if '/' in content_type else 'bin'
                                        filename = f"attachment_{uuid.uuid4().hex[:8]}.{ext}"
                                    
                                    print(f"Generated filename: {filename}")
                                
                                filename = clean_filename(filename)
                                print(f"Debug - Cleaned filename: {repr(filename)}")
                                
                                if not filename:
                                    filename = f"attachment_{uuid.uuid4().hex[:8]}.bin"
                                    print(f"Debug - Fallback filename: {filename}")
                                
                                try:
                                    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                                    print(f"Debug - Full filepath: {filepath}")
                                except Exception as path_error:
                                    print(f"Error creating filepath: {path_error}")
                                    print(f"DOWNLOAD_FOLDER: {repr(DOWNLOAD_FOLDER)}")
                                    print(f"filename: {repr(filename)}")
                                    continue
                                
                                try:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        with open(filepath, "wb") as f:
                                            f.write(payload)
                                        print(f"Downloaded attachment: {filename}")
                                        
                                        file_id = upload_to_drive(filepath)
                                        
                                        if file_id:
                                            print(f"Successfully uploaded. File ID: {file_id}")
                                            print(f"Sender: {sender_email}")
                                            
                                            #try:
                                                #os.remove(filepath)
                                                #print(f"Cleaned up local file: {filepath}")
                                            #except OSError as e:
                                             #   print(f"Warning: Could not remove local file {filepath}: {e}")
                                            
                                            return file_id, sender_email
                                        else:
                                            print("Failed to upload to Google Drive")
                                    else:
                                        print("No payload found in attachment")
                                        
                                except Exception as e:
                                    print(f"Error processing attachment {filename}: {e}")
                                    continue
                        except Exception as part_error:
                            print(f"Error processing email part: {part_error}")
                            continue
                    
                    if not attachment_found:
                        print("No attachments found in multipart email")
                else:
                    print("Email is not multipart - no attachments found")
        
        print("No valid attachments found in the email")
        return None
        
    except Exception as e:
        print(f"Error in check_email_and_upload: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if mail:
            try:
                mail.logout()
            except:
                pass

def clean_filename(filename):
    """Clean filename to remove problematic characters"""
    if not filename:
        return f"attachment_{uuid.uuid4().hex[:8]}"
    
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip()
    
    if not filename:
        filename = f"attachment_{uuid.uuid4().hex[:8]}"
    
    return filename

def upload_to_drive(filepath):
    """Upload file to Google Drive and return file ID"""
    try:
        if not os.path.exists(filepath):
            print(f"File does not exist: {filepath}")
            return None
            
        filename = os.path.basename(filepath)
        
        # Create file in Google Drive
        file_drive = drive.CreateFile({
            'title': filename, 
            "parents": [{"id": DRIVE_FOLDER_ID}]
        })
        
        file_drive.SetContentFile(filepath)
        file_drive.Upload()
        
        print(f"Uploaded to Google Drive: {filename}")
        return file_drive['id']
        
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
        return None

def extract_sender_email(message):
    """Extract sender email from message"""
    try:
        from_field = message.get('From', '')
        
        match = re.search(r'<(.*?)>', from_field)
        if match:
            return match.group(1)
        
        if '@' in from_field:
            return from_field.strip()
        
        return "unknown@sender.com"
        
    except Exception as e:
        print(f"Error extracting sender email: {e}")
        return "unknown@sender.com"


def main():
    schedule.every(1).minutes.do(check_email_and_upload)
    check_email_and_upload()
    print("Ingestion tool running... (Ctrl+C to stop)")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

