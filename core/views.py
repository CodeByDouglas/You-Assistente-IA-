from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import logging
import os
import requests
import datetime
from groq import Groq
from core.tools.Google_calendar.create_event import create_event
from core.tools.Google_calendar.list_events import list_events
from core.tools.Google_drive.drive_utils import upload_base64_file

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook_evolution(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            try:
                payload_data = data.get("data", {})
                key = payload_data.get("key", {})
                sender = data.get("sender")
                remote_jid = key.get("remoteJid")
                from_me = key.get("fromMe")

                if from_me and remote_jid == sender:
                    message = data.get("data", {}).get("message", {})
                    conversation = message.get("conversation") or message.get("extendedTextMessage", {}).get("text")

                    media_types = [
                        "imageMessage",
                        "documentMessage",
                        "videoMessage",
                        "audioMessage",
                    ]
                    media_found = None

                    for m_type in media_types:
                        if message.get(m_type):
                            media_found = message.get(m_type)
                            break

                    if media_found:
                        base64_content = message.get("base64")

                        if base64_content:
                            mimetype = media_found.get("mimetype")
                            file_name = media_found.get("fileName")

                            if not file_name:
                                timestamp = datetime.datetime.now().strftime(
                                    "%Y%m%d_%H%M%S"
                                )
                                ext = mimetype.split("/")[-1] if mimetype else "bin"
                                file_name = f"whatsapp_upload_{timestamp}.{ext}"

                            file_id = upload_base64_file(
                                base64_content, file_name, mimetype
                            )

                            if file_id:
                                logger.info(f"SUCESSO: Arquivo salvo no Drive com ID: {file_id}")
                            else:
                                logger.error("FALHA: Erro ao salvar arquivo no Drive.")
                        else:
                            logger.warning("AVISO: Base64 não encontrado na mensagem de mídia.")

                    if conversation:
                        api_key = os.environ.get("API_KEY_GROQ")
                        if api_key:
                            client = Groq(api_key=api_key)

                            # Map week days to Portuguese
                            dias_semana = {
                                0: "Segunda-feira",
                                1: "Terça-feira",
                                2: "Quarta-feira",
                                3: "Quinta-feira",
                                4: "Sexta-feira",
                                5: "Sábado",
                                6: "Domingo"
                            }
                            now = timezone.localtime(timezone.now())
                            dia_semana = dias_semana[now.weekday()]
                            current_date = f"{dia_semana}, {now.strftime('%Y-%m-%d %H:%M:%S')}"

                            calendar_context = ""
                            for i in range(7):
                                future_date = now + datetime.timedelta(days=i)
                                d_semana = dias_semana[future_date.weekday()]
                                d_str = future_date.strftime("%Y-%m-%d")
                                label = " (Hoje)" if i == 0 else " (Amanhã)" if i == 1 else ""
                                calendar_context += f"- {d_semana}: {d_str}{label}\n"

                            system_prompt = f"""
Você é um assistente de IA experiente. Sua tarefa é analisar a mensagem do usuário e identificar se ele deseja agendar um evento ou lembrete ou se ele deseja listar seus agendamentos.

Contexto de Datas (Use ISTO para resolver datas relativas como 'próxima quinta', 'sábado que vem', etc):
{calendar_context}
Hora atual: {now.strftime('%H:%M:%S')}

Leve sempre em consideração o fuso horário de Brasília (-3).

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
4. Sua mensagem deve informar sobre o agendamento realizado.

Se for para listar agendamentos:
1. Identifique o intervalo de tempo desejado pelo usuário.
2. Defina time_min e time_max no formato ISO.
3. Sua mensagem deve informar sobre os agendamentos encontrados.
"""

                            chat_completion = client.chat.completions.create(
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user","content": conversation,},
                                ],
                                model="llama-3.3-70b-versatile",
                                response_format={"type": "json_object"},
                            )

                            response_content = chat_completion.choices[0].message.content

                            try:
                                response_json = json.loads(response_content)
                                if response_json.get("agendamento") is True:
                                    summary = response_json.get("summary")
                                    start_time = response_json.get("start_time")
                                    print(start_time)
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
                                            logger.info(
                                                f"SUCESSO: Evento criado. Link: {evento_criado.get('htmlLink')}"
                                            )
                                        else:
                                            logger.error(
                                                "FALHA: Não foi possível criar o evento."
                                            )
                                    else:
                                        logger.warning(
                                            "AVISO: Dados incompletos para criação de evento (summary, start_time ou end_time ausentes)."
                                        )

                                if response_json.get("listar_agendamento") is True:
                                    time_min_str = response_json.get("time_min")
                                    time_max_str = response_json.get("time_max")

                                    if not time_min_str:
                                        time_min_str = (
                                            datetime.datetime.utcnow().isoformat() + "Z"
                                        )

                                    eventos_encontrados = list_events(
                                        max_results=10,
                                        time_min=time_min_str,
                                        time_max=time_max_str,
                                    )

                                    if eventos_encontrados:
                                        lista_msg = "\n\n📅 *Eventos Encontrados:*"
                                        for evt in eventos_encontrados:
                                            start = evt["start"].get("dateTime", evt["start"].get("date"))
                                            summary = evt.get("summary", "Sem título")
                                            try:
                                                dt_obj = (datetime.datetime.fromisoformat(start))
                                                start_formatted = dt_obj.strftime("%d/%m %H:%M")
                                            
                                            except ValueError:
                                                start_formatted = start

                                            lista_msg += (f"\n- {start_formatted}: {summary}")

                                        mensagem_extra = response_json.get("mensagem", "")
                                        response_json["mensagem"] = f"{mensagem_extra}{lista_msg}"
                                    else:
                                        mensagem_extra = response_json.get("mensagem", "")
                                        response_json["mensagem"] = f"{mensagem_extra}\n\nNenhum evento encontrado para este período."

                                mensagem_texto = response_json.get("mensagem")
                                if mensagem_texto:
                                    mensagem_texto = f"*BOT*: {mensagem_texto}"
                                    evolution_api_url = os.environ.get("SERVER_URL")
                                    evolution_api_key = os.environ.get("AUTHENTICATION_API_KEY")
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
                                            logger.info(
                                                f"Status Code Envio: {response.status_code}"
                                            )
                                            logger.info(f"Response Envio: {response.text}")
                                        except Exception as e:
                                            logger.error(
                                                f"Erro ao enviar mensagem via Evolution API: {e}"
                                            )
                                    else:
                                        logger.error(
                                            "ERRO: Credenciais da Evolution API não configuradas corretamente no .env"
                                        )
                            except json.JSONDecodeError:
                                logger.error("Erro ao fazer parse do JSON da Groq")

                        else:
                            logger.error("ERRO: API_KEY_GROQ não configurada no .env")

                    else:
                        if not media_found:
                            logger.error(
                                "Mensagem de texto não encontrada no payload e nenhuma mídia processada."
                            )

            except Exception as e:
                logger.error(f"Erro ao processar dados: {e}")

        except json.JSONDecodeError:
            logger.error("Erro ao decodificar JSON")
        return HttpResponse(status=200)
    return HttpResponse(status=405)
