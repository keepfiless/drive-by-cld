import os
import json
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# Load credentials and folder URL from environment
SA_KEY = json.loads(os.environ["GDRIVE_SA_KEY"])
FOLDER_URL = os.environ["FOLDER_URL"]

# Extract folder ID from URL
match = re.search(r"/folders/([a-zA-Z0-9_-]+)", FOLDER_URL)
if not match:
    raise ValueError(f"Could not extract folder ID from URL: {FOLDER_URL}")
FOLDER_ID = match.group(1)

# Authenticate with service account
creds = service_account.Credentials.from_service_account_info(
    SA_KEY,
    scopes=["https://www.googleapis.com/auth/drive.readonly"]
)
service = build("drive", "v3", credentials=creds)

def download_folder(folder_id, local_path="downloads"):
    os.makedirs(local_path, exist_ok=True)

    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token
        ).execute()

        for file in results.get("files", []):
            file_path = os.path.join(local_path, file["name"])

            if file["mimeType"] == "application/vnd.google-apps.folder":
                # Recurse into subfolder
                print(f"Entering folder: {file['name']}")
                download_folder(file["id"], file_path)

            elif file["mimeType"].startswith("application/vnd.google-apps"):
                # Export Google Docs/Sheets/Slides as Office formats
                export_map = {
                    "application/vnd.google-apps.document":
                        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
                    "application/vnd.google-apps.spreadsheet":
                        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
                    "application/vnd.google-apps.presentation":
                        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
                }
                if file["mimeType"] in export_map:
                    mime, ext = export_map[file["mimeType"]]
                    request = service.files().export_media(fileId=file["id"], mimeType=mime)
                    file_path += ext
                    print(f"Exporting: {file['name']}{ext}")
                else:
                    print(f"Skipping unsupported Google type: {file['name']}")
                    continue

                with open(file_path, "wb") as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

            else:
                # Regular file download
                request = service.files().get_media(fileId=file["id"])
                print(f"Downloading: {file['name']}")
                with open(file_path, "wb") as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

        page_token = results.get("nextPageToken")
        if not page_token:
            break

print(f"Starting download from folder ID: {FOLDER_ID}")
download_folder(FOLDER_ID, local_path="downloads")
print("Done!")
