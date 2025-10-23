from openai import OpenAI
from dotenv import load_dotenv
import requests
import flask
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import CSVLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.runnables import RunnablePassthrough

app = flask.Flask(__name__)
load_dotenv()

# === Inicializar o cliente OpenAI ===
client = OpenAI()

# === Carregar e processar o CSV de perguntas e respostas ===
loader = CSVLoader(file_path='Q&A.csv')
documents = loader.load()
embeddings = OpenAIEmbeddings()
vector_store = FAISS.from_documents(documents, embeddings)
retrieval = vector_store.as_retriever()

# === Modelo de linguagem ===
llm = ChatOpenAI()

# === Template do prompt ===
template = "Você é um assistente de atendimento com IA. Contexto: {context}. Pergunta: {question}"
prompt = ChatPromptTemplate.from_template(template)

chain = (
    {"context": retrieval, "question": RunnablePassthrough()}
    | prompt
    | llm
)


# === Função para gerar resposta da IA ===
def get_chat_response(message: str):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um assistente útil e educado."},
            {"role": "user", "content": message}
        ]
    )
    return completion.choices[0].message.content


# === Função para enviar mensagem via WASenderAPI ===
def enviar_mensagem_wasenderapi(numero: str, mensagem: str):
    """
    Envia uma mensagem via WASenderAPI (API REST oficial deles)
    """
    try:
        url = "https://wasenderapi.com/api/send-message"
        data = {
            "to": numero,
            "text": mensagem
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer 7214c814bdf0dc22c9c20042c80f92629e8416adfc6b60b7b56cf191f41b28e7",
            "X-Webhook-Signature" : "8b2fa5a4d6ac6775eaa8f9fcd3afea91"
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"✅ Mensagem enviada para {numero}")
        else:
            print("❌ Erro ao enviar mensagem:", response.text)
    except Exception as e:
        print("⚠️ Erro ao contactar WASenderAPI:", str(e))


# === Webhook ===
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = flask.request.json
    print("📩 Webhook recebido:", payload)

    if not payload:
        return flask.jsonify({"error": "Payload vazio"}), 400

    data = payload.get("data", {})
    messages = data.get("messages", {})

    # Extrair mensagem e remetente
    message = None
    sender = None

    if isinstance(messages, dict):
        message_data = messages.get("message", {})
        message = message_data.get("conversation")
        sender = messages.get("key", {}).get("remoteJid")

    # Limpar o número (remover sufixo @s.whatsapp.net)
    if sender and "@s.whatsapp.net" in sender:
        sender = sender.replace("@s.whatsapp.net", "")

    print(f"➡️ Mensagem: {message}")
    print(f"➡️ Remetente: {sender}")

    if not message:
        return flask.jsonify({"info": "Nenhuma mensagem detectada no payload"}), 200

    # === Gera resposta da IA (usando LangChain + CSV) ===
    try:
        response = chain.invoke(message)
        resposta_texto = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        print("⚠️ Erro ao gerar resposta:", e)
        resposta_texto = "Desculpe, ocorreu um erro ao processar sua mensagem."

    # === Envia resposta pelo WhatsApp ===
    if sender:
        enviar_mensagem_wasenderapi(sender, resposta_texto)
        print(f"📤 Resposta enviada para {sender}")
    else:
        print("⚠️ Nenhum remetente encontrado — resposta não enviada.")

    return flask.jsonify({"status": "ok"})

# === Iniciar o servidor Flask ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

