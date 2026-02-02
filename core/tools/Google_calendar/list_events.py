import os
import pickle
import datetime
from googleapiclient.discovery import build


def get_calendar_service():
    """Carrega as credenciais e retorna o serviço do Google Calendar."""
    # Define o caminho para o arquivo token.pickle
    # Assume que a estrutura é: root/core/tools/Google_calendar/list_events.py
    # E o token está em: root/google_calendar_auth/token.pickle
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    token_path = os.path.join(base_dir, "google_calendar_auth", "token.pickle")

    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            creds.refresh(Request())
        else:
            raise Exception(
                "Credenciais inválidas ou expiradas. Por favor, execute o script de autenticação novamente."
            )

    return build("calendar", "v3", credentials=creds)


def list_events(max_results=10, time_min=None, time_max=None):
    """
    Lista os próximos eventos do calendário do usuário.

    Args:
        max_results (int): Número máximo de eventos a serem listados.
        time_min (str): Data/hora de início no formato ISO (ex: '2023-10-01T00:00:00Z').
                        Se None, usa o momento atual (utc).
        time_max (str): Data/hora de fim no formato ISO.
    """
    try:
        service = get_calendar_service()

        if time_min is None:
            time_min = (
                datetime.datetime.utcnow().isoformat() + "Z"
            )  # 'Z' indicates UTC time

        query_params = {
            "calendarId": "primary",
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeMin": time_min,
        }

        if time_max:
            query_params["timeMax"] = time_max

        events_result = service.events().list(**query_params).execute()
        events = events_result.get("items", [])

        return events

    except Exception as e:
        print(f"Ocorreu um erro ao listar eventos: {e}")
        return []


if __name__ == "__main__":
    # Teste simples se executado diretamente
    print("Listando os próximos 5 eventos...")
    eventos = list_events(max_results=5)
    if not eventos:
        print("Nenhum evento encontrado.")
    for event in eventos:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(start, event["summary"])
