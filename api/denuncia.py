import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS

import firebase_admin
from firebase_admin import credentials, firestore

# Inicializa o aplicativo Flask
app = Flask(__name__)
# Habilita o CORS para permitir requisições do seu formulário HTML
CORS(app)

# Inicializa o Firebase Admin SDK
if not firebase_admin._apps:
    try:
        # Acessa as credenciais do Firebase a partir de uma variável de ambiente
        firebase_json = os.environ.get("FIREBASE_CREDENTIALS")
        if firebase_json:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase conectado com sucesso")
        else:
            print("❌ A variável de ambiente FIREBASE_CREDENTIALS não está definida.")
    except Exception as e:
        print("❌ Erro ao inicializar Firebase:", e)

# Obtém uma referência ao cliente Firestore
db = firestore.client()
# Define o nome da coleção onde as denúncias serão salvas
colecao = 'dbdenuncia'


def enviar_email_denuncia(dados_denuncia):
    """Envia um e-mail com os detalhes da denúncia."""
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASS")
    receiver_email = os.environ.get("EMAIL_RECEIVER")

    if not all([sender_email, sender_password, receiver_email]):
        print("❌ Variáveis de ambiente de e-mail não definidas (EMAIL_USER, EMAIL_PASS, EMAIL_RECEIVER).")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Nova Denúncia Recebida!"

    body = "Uma nova denúncia foi registrada no sistema.\n\nDetalhes da Denúncia:\n--------------------\n"
    # Itera sobre os dados da denúncia para montar o corpo do e-mail
    for key, value in dados_denuncia.items():
        if isinstance(value, dict):
            # Se o valor for um dicionário aninhado (ex: 'vitima'), itera sobre ele
            body += f"{key.capitalize()}:\n"
            for sub_key, sub_value in value.items():
                body += f"  - {sub_key.capitalize()}: {sub_value}\n"
        else:
            body += f"{key.capitalize()}: {value}\n"

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("✅ E-mail de denúncia enviado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail de denúncia: {e}")
        return False


@app.route("/api/denuncias", methods=["POST"])
def receber_denuncia():
    """Trata as requisições POST para o endpoint /api/denuncias."""
    try:
        # Obtém os dados JSON da requisição
        dados = request.json
        if not dados:
            return jsonify({"status": "erro", "mensagem": "Nenhum dado JSON fornecido"}), 400

        # Adiciona o carimbo de data/hora do servidor do Firestore
        dados['dataEnvio'] = firestore.SERVER_TIMESTAMP
        # Adiciona a denúncia à coleção no Firestore
        doc_ref = db.collection(colecao).add(dados)

        # Envia o e-mail de notificação com os dados da denúncia
        enviar_email_denuncia(dados.copy())

        # Retorna uma resposta de sucesso
        return jsonify({"status": "sucesso", "id": doc_ref[1].id}), 201
    except Exception as e:
        print("❌ Erro ao salvar denúncia:", e)
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


if __name__ == "__main__":
    # Roda o servidor Flask.
    # O host '0.0.0.0' o torna acessível externamente, e a porta é configurável via variável de ambiente.
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
