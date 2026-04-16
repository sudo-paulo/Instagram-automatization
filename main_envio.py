import smtplib
from email.message import EmailMessage
import time
from datetime import datetime

EMAIL = "seuemail@gmail.com"
SENHA = "senha_app"

# =========================
# CONFIG HORÁRIOS
# =========================
HORARIO_1 = "10:00"
HORARIO_2 = "18:30"

# =========================
# MENSAGENS
# =========================
ASSUNTO_1 = "Proposta 1"
ASSUNTO_2 = "Proposta 2"

MSG_1 = open("mensagem1.txt", encoding="utf-8").read()
MSG_2 = open("mensagem2.txt", encoding="utf-8").read()

ANEXO_1 = "img1.jpg"
ANEXO_2 = "img2.jpg"

# =========================
# LER CONTATOS
# =========================
def contatos():
    lista = []
    with open("saida/usuarios.txt", encoding="utf-8") as f:
        for linha in f:
            partes = linha.split("|")
            if len(partes) >= 2:
                email = partes[1].strip()
                if email:
                    lista.append(email)
    return lista

# =========================
# ENVIAR EMAIL
# =========================
def enviar_lote(lista, assunto, mensagem, anexo):
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL, SENHA)

    for destino in lista:
        msg = EmailMessage()
        msg["From"] = EMAIL
        msg["To"] = destino
        msg["Subject"] = assunto
        msg.set_content(mensagem)

        # anexo
        with open(anexo, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="image",
                subtype="jpeg",
                filename=anexo
            )

        try:
            server.send_message(msg)
            print("✅", destino)
        except:
            print("❌", destino)

        time.sleep(5)

    server.quit()

# =========================
# ESPERAR HORÁRIO
# =========================
def esperar(horario):
    while True:
        agora = datetime.now().strftime("%H:%M")
        if agora == horario:
            break
        time.sleep(20)

# =========================
# EXECUÇÃO
# =========================
lista = contatos()

print("⏳ esperando horário 1...")
esperar(HORARIO_1)

print("🚀 enviando lote 1")
enviar_lote(lista, ASSUNTO_1, MSG_1, ANEXO_1)

print("⏳ esperando horário 2...")
esperar(HORARIO_2)

print("🚀 enviando lote 2")
enviar_lote(lista, ASSUNTO_2, MSG_2, ANEXO_2)

print("🔥 FINALIZADO")
