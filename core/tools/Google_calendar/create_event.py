import os
import pickle
from googleapiclient.discovery import build


def get_calendar_service():
    """Carrega as credenciais e retorna o serviço do Google Calendar."""
    # Define o caminho para o arquivo token.pickle
    # Assume que a estrutura é: root/core/tools/Google_calendar/create_event.py
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


def create_event(
    summary,
    start_time,
    end_time,
    description="",
    location="",
    time_zone="America/Sao_Paulo",
):
    """
    Cria um evento no Google Calendar.

    Args:
        summary (str): Título do evento.
        start_time (str): Data/hora de início no formato ISO (ex: '2023-10-01T10:00:00').
        end_time (str): Data/hora de fim no formato ISO (ex: '2023-10-01T11:00:00').
        description (str): Descrição do evento.
        location (str): Local do evento.
        time_zone (str): Fuso horário do evento (default: 'America/Sao_Paulo').
    """
    try:
        service = get_calendar_service()

        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {
                "dateTime": start_time,
                "timeZone": time_zone,
            },
            "end": {
                "dateTime": end_time,
                "timeZone": time_zone,
            },
        }

        created_event = (
            service.events().insert(calendarId="primary", body=event).execute()
        )
        print(f"Evento criado: {created_event.get('htmlLink')}")
        return created_event

    except Exception as e:
        print(f"Ocorreu um erro ao criar o evento: {e}")
        return None


if __name__ == "__main__":
    # Teste simples se executado diretamente
    # Exemplo de uso: Criar um evento para amanhã
    import datetime

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    start_str = f"{tomorrow}T09:00:00"
    end_str = f"{tomorrow}T10:00:00"

    print(f"Tentando criar evento teste para {start_str}...")
    create_event(
        summary="Teste Criação Automática",
        start_time=start_str,
        end_time=end_str,
        description="Evento criado via script Python",
    )
