from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import requests
import datetime
import datetime
from groq import Groq
from core.tools.Google_calendar.create_event import create_event

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
  "summary": "Título do evento" (se agendamento=true, senão null),
  "start_time": "YYYY-MM-DDTHH:MM:SS" (se agendamento=true, senão null),
  "end_time": "YYYY-MM-DDTHH:MM:SS" (se agendamento=true, senão null),
  "description": "Descrição do evento" (se agendamento=true, senão null)
}}

Se for um agendamento:
1. Extraia o título, data/hora de início e fim, e descrição.
2. Se o usuário não fornecer horário de fim, assuma 1 hora de duração.
3. Se o usuário não fornecer descrição, deixe vazio ou infira do contexto.
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
                        print("Mensagem de texto não encontrada no payload.")

            except Exception as e:
                print(f"Erro ao processar dados: {e}")

        except json.JSONDecodeError:
            print("Erro ao decodificar JSON")
        return HttpResponse(status=200)
    return HttpResponse(status=405)
