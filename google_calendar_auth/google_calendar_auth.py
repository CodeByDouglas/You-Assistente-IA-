import os.path
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Diretório base do script para garantir que arquivos sejam encontrados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Escopos de permissão necessários (Calendar e Drive)
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]

# Arquivos de credenciais
CLIENT_SECRET_FILE = os.path.join(
    BASE_DIR,
    "client_secret_480126422359-la0hcfrq6ae685epo88fureei3ao511c.apps.googleusercontent.com.json",
)
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")


def get_credentials():
    """
    Obtém as credenciais do usuário.
    Se o arquivo token.pickle existir, ele é usado.
    Verifica se as credenciais salvas possuem todos os escopos necessários.
    Caso contrário, inicia o fluxo de autenticação OAuth2.
    """
    creds = None
    # O arquivo token.pickle armazena os tokens de acesso e atualização do usuário
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # Verifica se as credenciais são válidas e possuem os escopos corretos
    if not creds or not creds.valid or not creds.has_scopes(SCOPES):
        if creds and creds.expired and creds.refresh_token and creds.has_scopes(SCOPES):
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Erro ao atualizar token: {e}. Iniciando novo login.")
                creds = None

        # Se após tentar dar refresh o creds for None ou não tiver escopos, faz login
        if not creds or not creds.valid or not creds.has_scopes(SCOPES):
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Erro: O arquivo '{CLIENT_SECRET_FILE}' não foi encontrado.")
                print("Certifique-se de que o arquivo OAuth esteja na pasta correta.")
                return None

            print(
                "Iniciando fluxo de autenticação (novos escopos ou token expirado)..."
            )
            # Fluxo OAuth2 para aplicativo instalado
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Rodar servidor local para receber o callback na porta 8000
            creds = flow.run_local_server(port=8000)

        # Salve as credenciais para a próxima execução
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return creds


def build_calendar_service(creds):
    """Constrói o serviço da API do Google Calendar."""
    return build("calendar", "v3", credentials=creds)


def build_drive_service(creds):
    """Constrói o serviço da API do Google Drive."""
    return build("drive", "v3", credentials=creds)


if __name__ == "__main__":
    print("Iniciando processo de autenticação unificada (Calendar + Drive)...")

    creds = get_credentials()

    if creds:
        try:
            # --- Teste Calendar ---
            print("\n--- Testando Google Calendar API ---")
            service_cal = build_calendar_service(creds)
            print("Tentando listar 1 evento para validar acesso...")
            events_result = (
                service_cal.events()
                .list(
                    calendarId="primary",
                    maxResults=1,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            if not events:
                print("Nenhum evento futuro encontrado.")
            else:
                for event in events:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    print(f"Evento encontrado: {start} - {event['summary']}")
            print("Google Calendar: Autenticado e verificado com sucesso!")

            # --- Teste Drive ---
            print("\n--- Testando Google Drive API ---")
            service_drive = build_drive_service(creds)
            print("Tentando listar 5 arquivos para validar acesso...")
            results = (
                service_drive.files()
                .list(pageSize=5, fields="nextPageToken, files(id, name)")
                .execute()
            )
            items = results.get("files", [])

            if not items:
                print("Nenhum arquivo encontrado no Drive.")
            else:
                print("Arquivos encontrados:")
                for item in items:
                    print(f"- {item['name']} ({item['id']})")
            print("Google Drive: Autenticado e verificado com sucesso!")

        except Exception as e:
            print(f"\nOcorreu um erro durante a validação: {e}")
            print(
                f"Dica: Se o erro for de permissão, tente apagar o arquivo '{TOKEN_FILE}' e rodar novamente."
            )
    else:
        print("Falha na autenticação.")
