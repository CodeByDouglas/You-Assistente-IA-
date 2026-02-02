import os.path
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Escopos de permissão necessários
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Nome do arquivo de credenciais do cliente (segredo)
CLIENT_SECRET_FILE = "client_secret_480126422359-la0hcfrq6ae685epo88fureei3ao511c.apps.googleusercontent.com.json"


def get_credentials():
    """
    Obtém as credenciais do usuário.
    Se o arquivo token.pickle existir, ele é usado.
    Caso contrário, inicia o fluxo de autenticação OAuth2.
    """
    creds = None
    # O arquivo token.pickle armazena os tokens de acesso e atualização do usuário
    # e é criado automaticamente quando o fluxo de autorização é concluído pela primeira vez.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # Se não houver credenciais válidas, deixe o usuário fazer login.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Erro: O arquivo '{CLIENT_SECRET_FILE}' não foi encontrado.")
                print(
                    "Certifique-se de que o arquivo OAuth baixado do Google Cloud esteja na raiz do projeto."
                )
                return None

            # Fluxo OAuth2 para aplicativo instalado
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Rodar servidor local para receber o callback na porta 8000
            creds = flow.run_local_server(port=8000)

        # Salve as credenciais para a próxima execução
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return creds


def build_calendar_service(creds):
    """Constrói o serviço da API do Google Calendar."""
    return build("calendar", "v3", credentials=creds)


if __name__ == "__main__":
    print("Iniciando processo de autenticação...")

    creds = get_credentials()

    if creds:
        try:
            service = build_calendar_service(creds)

            # Chamada de teste simples: listar os próximos 1 eventos
            print("Tentando listar 1 evento para validar acesso...")
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    maxResults=1,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            print("Google Calendar autenticado com sucesso")

        except Exception as e:
            print(f"Ocorreu um erro ao conectar com o Google Calendar: {e}")
    else:
        print("Falha na autenticação.")
