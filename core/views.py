from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
from groq import Groq

# Create your views here.


@csrf_exempt
def webhook_evolution(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            # Inner try block for processing logic
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
                            chat_completion = client.chat.completions.create(
                                messages=[
                                    {
                                        "role": "user",
                                        "content": conversation,
                                    }
                                ],
                                model="llama-3.3-70b-versatile",
                            )

                            print("=== RESPOSTA DA GROQ ===")
                            print(chat_completion.choices[0].message.content)
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
