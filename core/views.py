from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import requests
import datetime
import datetime
from groq import Groq
from core.tools.Google_calendar.create_event import create_event
from core.tools.Google_calendar.create_event import create_event
from core.tools.Google_calendar.list_events import list_events
from core.tools.Google_drive.drive_utils import upload_base64_file

# Create your views here.


@csrf_exempt
def webhook_evolution(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            try:
                # Verifica se a mensagem foi enviada pelo próprio usuário E se é para ele mesmo (Note to Self)
                payload_data = data.get("data", {})
                key = payload_data.get("key", {})
                sender = data.get("sender")
                remote_jid = key.get("remoteJid")
                from_me = key.get("fromMe")

                if from_me and remote_jid == sender:
                    print("=== MENSAGEM RECEBIDA (NOTE TO SELF) ===")
                    print(json.dumps(data, indent=4))
                    print("========================================")

                    # Recupera o conteúdo da mensagem
                    message = data.get("data", {}).get("message", {})
                    conversation = message.get("conversation") or message.get(
                        "extendedTextMessage", {}
                    ).get("text")

                    # === NOVA LÓGICA: Upload de Mídia para o Google Drive ===
                    media_types = [
                        "imageMessage",
                        "documentMessage",
                        "videoMessage",
                        "audioMessage",
                    ]
                    media_found = None
                    media_type_key = None

                    for m_type in media_types:
                        if message.get(m_type):
                            media_found = message.get(m_type)
                            media_type_key = m_type
                            break

                    if media_found:
                        print(f"=== MÍDIA DETECTADA: {media_type_key} ===")
                        base64_content = media_found.get("base64") or message.get(
                            "base64"
                        )

                        if base64_content:
                            mimetype = media_found.get("mimetype")
                            file_name = media_found.get("fileName")
                            if not file_name:
                                caption = media_found.get("caption")
                                timestamp = datetime.datetime.now().strftime(
                                    "%Y%m%d_%H%M%S"
                                )
                                ext = mimetype.split("/")[-1] if mimetype else "bin"
                                if caption and len(caption) < 30:
                                    safe_caption = "".join(
                                        [
                                            c
                                            for c in caption
                                            if c.isalnum() or c in (" ", "_", "-")
                                        ]
                                    ).strip()
                                    file_name = f"{safe_caption}_{timestamp}.{ext}"
                                else:
                                    file_name = f"whatsapp_upload_{timestamp}.{ext}"

                            print(
                                f"Iniciando upload para Drive: {file_name} ({mimetype})"
                            )
                            file_id = upload_base64_file(
                                base64_content, file_name, mimetype
                            )

                            if file_id:
                                print(
                                    f"SUCESSO: Arquivo salvo no Drive com ID: {file_id}"
                                )
                            else:
                                print("FALHA: Erro ao salvar arquivo no Drive.")
                        else:
                            print("AVISO: Base64 não encontrado na mensagem de mídia.")

                    if conversation:
                        api_key = os.environ.get("API_KEY_GROQ")
                        if api_key:
                            client = Groq(api_key=api_key)

                            current_date = datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )

                            system_prompt = f"""
Você é um assistente de IA experiente. Sua tarefa é analisar a mensagem do usuário e identificar se ele deseja agendar um evento ou lembrete.
Hoje é {current_date}.

Responda EXCLUSIVAMENTE com um objeto JSON válido no seguinte formato:
{{
  "mensagem": "Sua resposta natural e útil para o usuário aqui.",
  "agendamento": true ou false,
  "listar_agendamento": true ou false,
  "summary": "Título do evento" (se agendamento=true, senão null),
  "start_time": "YYYY-MM-DDTHH:MM:SS" (se agendamento=true, senão null),
  "end_time": "YYYY-MM-DDTHH:MM:SS" (se agendamento=true, senão null),
  "description": "Descrição do evento" (se agendamento=true, senão null),
  "time_min": "YYYY-MM-DDTHH:MM:SS" (se listar_agendamento=true, data de inicio da busca, senão null, se não especificado usar {current_date}),
  "time_max": "YYYY-MM-DDTHH:MM:SS" (se listar_agendamento=true, data de fim da busca, senão null)
}}

Se for um agendamento:
1. Extraia o título, data/hora de início e fim, e descrição.
2. Se o usuário não fornecer horário de fim, assuma 1 hora de duração.
3. Se o usuário não fornecer descrição, deixe vazio ou infira do contexto.

Se for para listar agendamentos:
1. Identifique o intervalo de tempo desejado pelo usuário.
2. Defina time_min e time_max no formato ISO.
"""

                            chat_completion = client.chat.completions.create(
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {
                                        "role": "user",
                                        "content": conversation,
                                    },
                                ],
                                model="llama-3.3-70b-versatile",
                                response_format={"type": "json_object"},
                            )

                            response_content = chat_completion.choices[
                                0
                            ].message.content
                            print("=== RESPOSTA DA GROQ (JSON) ===")
                            print(response_content)

                            try:
                                response_json = json.loads(response_content)
                                print("--- Dados Extraídos ---")
                                print(f"Mensagem: {response_json.get('mensagem')}")
                                print(
                                    f"Agendamento: {response_json.get('agendamento')}"
                                )
                                if response_json.get("agendamento") is True:
                                    print(
                                        ">>> Iniciando criação de evento automático..."
                                    )
                                    summary = response_json.get("summary")
                                    start_time = response_json.get("start_time")
                                    end_time = response_json.get("end_time")
                                    description = response_json.get("description")

                                    if summary and start_time and end_time:
                                        evento_criado = create_event(
                                            summary=summary,
                                            start_time=start_time,
                                            end_time=end_time,
                                            description=description,
                                        )
                                        if evento_criado:
                                            print(
                                                f"SUCESSO: Evento criado. Link: {evento_criado.get('htmlLink')}"
                                            )
                                        else:
                                            print(
                                                "FALHA: Não foi possível criar o evento."
                                            )
                                    else:
                                        print(
                                            "AVISO: Dados incompletos para criação de evento (summary, start_time ou end_time ausentes)."
                                        )
                                print(f"Summary: {response_json.get('summary')}")
                                print(f"Start Time: {response_json.get('start_time')}")
                                print(f"End Time: {response_json.get('end_time')}")
                                print(
                                    f"Description: {response_json.get('description')}"
                                )

                                # Lógica para listar agendamentos
                                if response_json.get("listar_agendamento") is True:
                                    print(">>> Iniciando listagem de eventos...")
                                    time_min_str = response_json.get("time_min")
                                    time_max_str = response_json.get("time_max")

                                    # Se a API não retornou time_min, usa agora
                                    if not time_min_str:
                                        time_min_str = (
                                            datetime.datetime.utcnow().isoformat() + "Z"
                                        )
                                    # Formata para adicionar Z se faltar e garantir validade básica
                                    # (list_events espera string ISO com timezone)
                                    if (
                                        time_min_str
                                        and not time_min_str.endswith("Z")
                                        and "+" not in time_min_str
                                    ):
                                        time_min_str += "Z"
                                    if (
                                        time_max_str
                                        and not time_max_str.endswith("Z")
                                        and "+" not in time_max_str
                                    ):
                                        time_max_str += "Z"

                                    eventos_encontrados = list_events(
                                        max_results=10,
                                        time_min=time_min_str,
                                        time_max=time_max_str,
                                    )

                                    if eventos_encontrados:
                                        lista_msg = "\n\n📅 *Eventos Encontrados:*"
                                        for evt in eventos_encontrados:
                                            start = evt["start"].get(
                                                "dateTime", evt["start"].get("date")
                                            )
                                            summary = evt.get("summary", "Sem título")
                                            # Tenta formatar a data para ficar mais legível
                                            try:
                                                dt_obj = (
                                                    datetime.datetime.fromisoformat(
                                                        start
                                                    )
                                                )
                                                start_formatted = dt_obj.strftime(
                                                    "%d/%m %H:%M"
                                                )
                                            except ValueError:
                                                start_formatted = start

                                            lista_msg += (
                                                f"\n- {start_formatted}: {summary}"
                                            )

                                        # Anexa a lista à mensagem existente
                                        mensagem_extra = response_json.get(
                                            "mensagem", ""
                                        )
                                        response_json["mensagem"] = (
                                            f"{mensagem_extra}{lista_msg}"
                                        )
                                    else:
                                        mensagem_extra = response_json.get(
                                            "mensagem", ""
                                        )
                                        response_json["mensagem"] = (
                                            f"{mensagem_extra}\n\nNenhum evento encontrado para este período."
                                        )

                                # Envio da mensagem de resposta via Evolution API
                                mensagem_texto = response_json.get("mensagem")
                                if mensagem_texto:
                                    mensagem_texto = f"*BOT*: {mensagem_texto}"
                                    print(
                                        ">>> Iniciando envio de resposta via WhatsApp..."
                                    )
                                    evolution_api_url = os.environ.get("SERVER_URL")
                                    evolution_api_key = os.environ.get(
                                        "AUTHENTICATION_API_KEY"
                                    )
                                    evolution_instance = os.environ.get("INSTANCE_NAME")

                                    if (
                                        evolution_api_url
                                        and evolution_api_key
                                        and evolution_instance
                                    ):
                                        url = f"{evolution_api_url}/message/sendText/{evolution_instance}"
                                        headers = {
                                            "apikey": evolution_api_key,
                                            "Content-Type": "application/json",
                                        }
                                        payload = {
                                            "number": sender,
                                            "text": mensagem_texto,
                                            "delay": 1200,
                                            "linkPreview": False,
                                        }
                                        try:
                                            response = requests.post(
                                                url, json=payload, headers=headers
                                            )
                                            print(
                                                f"Status Code Envio: {response.status_code}"
                                            )
                                            print(f"Response Envio: {response.text}")
                                        except Exception as e:
                                            print(
                                                f"Erro ao enviar mensagem via Evolution API: {e}"
                                            )
                                    else:
                                        print(
                                            "ERRO: Credenciais da Evolution API não configuradas corretamente no .env"
                                        )
                            except json.JSONDecodeError:
                                print("Erro ao fazer parse do JSON da Groq")

                            print("========================")
                        else:
                            print("ERRO: API_KEY_GROQ não configurada no .env")

                    else:
                        if not media_found:
                            print(
                                "Mensagem de texto não encontrada no payload e nenhuma mídia processada."
                            )

            except Exception as e:
                print(f"Erro ao processar dados: {e}")

        except json.JSONDecodeError:
            print("Erro ao decodificar JSON")
        return HttpResponse(status=200)
    return HttpResponse(status=405)
