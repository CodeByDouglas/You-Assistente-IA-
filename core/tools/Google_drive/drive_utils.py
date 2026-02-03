import os
import pickle
import base64
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from django.conf import settings

# Caminho para o token.pickle
# Assumindo que o script pode ser rodado do diretório raiz ou importado
# O caminho relativo do arquivo em relação à raiz do projeto
TOKEN_PATH = os.path.join(os.getcwd(), "google_calendar_auth", "token.pickle")


def get_drive_service():
    """Carrega as credenciais e constrói o serviço do Google Drive."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception(
                "Credenciais inválidas ou inexistentes. Execute o script de autenticação novamente."
            )

    service = build("drive", "v3", credentials=creds)
    return service


def find_or_create_folder(service, folder_name):
    """Encontra uma pasta pelo nome ou cria se não existir."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    items = results.get("files", [])

    if not items:
        # Criar pasta
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = service.files().create(body=file_metadata, fields="id").execute()
        return folder.get("id")
    else:
        return items[0].get("id")


def upload_base64_file(base64_content, file_name, mime_type):
    """
    Decodifica base64 e faz upload para a pasta 'Arquivos-WhatsApp' no Google Drive.

    Args:
        base64_content (str): Conteúdo do arquivo em base64.
        file_name (str): Nome do arquivo a ser salvo.
        mime_type (str): Tipo MIME do arquivo (ex: 'image/png', 'application/pdf').

    Returns:
        str: ID do arquivo criado no Google Drive.
    """
    try:
        service = get_drive_service()
        folder_id = find_or_create_folder(service, "Arquivos-WhatsApp")

        # Decodificar base64
        # Remove header se existir (ex: data:image/png;base64,...)
        if "," in base64_content:
            base64_content = base64_content.split(",")[1]

        decoded_data = base64.b64decode(base64_content)
        file_stream = io.BytesIO(decoded_data)

        file_metadata = {"name": file_name, "parents": [folder_id]}

        media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)

        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )

        print(f"Arquivo '{file_name}' enviado com sucesso. ID: {file.get('id')}")
        return file.get("id")

    except Exception as e:
        print(f"Erro ao enviar arquivo para o Google Drive: {e}")
        return None
