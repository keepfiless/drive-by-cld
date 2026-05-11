import os, json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io

SA_KEY = json.loads(os.environ["GDRIVE_SA_KEY"])
FOLDER_ID = os.environ["FOLDER_ID"]

creds = service_account.Credentials.from_service_account_info(
    SA_KEY, scopes=["https://www.googleapis.com/auth/drive.readonly"]
)
service = build("drive", "v3", credentials=creds)

def download_folder(folder_id, local_path="."):
    os.makedirs(local_path, exist_ok=True)
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType)"
    ).execute()

    for file in results.get("files", []):
        if file["mimeType"] == "application/vnd.google-apps.folder":
            download_folder(file["id"], f"{local_path}/{file['name']}")
        else:
            request = service.files().get_media(fileId=file["id"])
            with open(f"{local_path}/{file['name']}", "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            print(f"Downloaded: {file['name']}")

download_folder(FOLDER_ID)
