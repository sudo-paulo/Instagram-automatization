import smtplib
import time
import os
import logging
import random
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from pathlib import Path

# =========================
# CONFIG — edite aqui
# =========================
EMAIL = "suellenrodriguesmkt@gmail.com"
SENHA = "yudw haqr owok bfvd"   # senha de app do Gmail (não a senha normal)

# Cada campanha tem: horário, assunto, arquivo de mensagem e lista de anexos
CAMPANHAS = [
    {
        "horario":  "10:00",
        "assunto":  "Proposta especial para o seu negócio",
        "mensagem": "mensagem1.txt",
        "anexos":   ["img1.jpg"],          # pode ser vazio [] ou ter vários arquivos
    },
    {
        "horario":  "18:30",
        "assunto":  "Seguimento — vamos conversar?",
        "mensagem": "mensagem2.txt",
        "anexos":   ["img2.jpg"],
    },
]

DELAY_ENTRE_EMAILS = (4, 8)   # segundos aleatórios entre cada envio
MAX_TENTATIVAS     = 3        # tentativas por e-mail antes de desistir
LOG_FILE           = "saida/envio.log"
ENVIADOS_FILE      = "saida/enviados.txt"  # evita reenviar para o mesmo e-mail

# =========================
# LOGGING
# =========================
os.makedirs("saida", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# =========================
# LER CONTATOS
# =========================
def ler_contatos():
    caminho = "saida/usuarios.txt"
    if not os.path.exists(caminho):
        log.error(f"Arquivo não encontrado: {caminho}")
        return []

    contatos = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) >= 2 and partes[1] and "@" in partes[1]:
                contatos.append({
                    "username": partes[0],
                    "email":    partes[1],
                    "link":     partes[2] if len(partes) > 2 else "",
                })

    log.info(f"{len(contatos)} contato(s) carregado(s).")
    return contatos

# =========================
# CARREGAR JÁ ENVIADOS
# =========================
def ler_enviados():
    if not os.path.exists(ENVIADOS_FILE):
        return set()
    with open(ENVIADOS_FILE, encoding="utf-8") as f:
        return {linha.strip() for linha in f if linha.strip()}

def registrar_enviado(email_destino):
    with open(ENVIADOS_FILE, "a", encoding="utf-8") as f:
        f.write(email_destino + "\n")

# =========================
# LER ARQUIVO DE MENSAGEM
# =========================
def ler_mensagem(caminho):
    if not os.path.exists(caminho):
        log.error(f"Arquivo de mensagem não encontrado: {caminho}")
        return ""
    with open(caminho, encoding="utf-8") as f:
        return f.read()

# =========================
# PERSONALIZAR MENSAGEM
# =========================
def personalizar(texto, contato):
    """
    Substitui variáveis na mensagem.
    Exemplo no .txt: Olá {username}, vimos seu perfil em {link}
    """
    return (texto
        .replace("{username}", contato.get("username", "").replace("@", ""))
        .replace("{email}",    contato.get("email", ""))
        .replace("{link}",     contato.get("link", ""))
    )

# =========================
# MONTAR E-MAIL COM ANEXOS
# =========================
def montar_email(remetente, destinatario, assunto, corpo, lista_anexos):
    msg = MIMEMultipart()
    msg["From"]    = remetente
    msg["To"]      = destinatario
    msg["Subject"] = assunto

    # Corpo do e-mail (texto simples)
    msg.attach(MIMEText(corpo, "plain", "utf-8"))

    # Anexos (imagens ou qualquer arquivo)
    for caminho_anexo in lista_anexos:
        if not os.path.exists(caminho_anexo):
            log.warning(f"Anexo não encontrado, pulando: {caminho_anexo}")
            continue

        extensao = Path(caminho_anexo).suffix.lower()
        maintype = "image" if extensao in (".jpg", ".jpeg", ".png", ".gif", ".webp") else "application"
        subtype  = {
            ".jpg": "jpeg", ".jpeg": "jpeg",
            ".png": "png",  ".gif": "gif",
            ".webp": "webp",
        }.get(extensao, "octet-stream")

        with open(caminho_anexo, "rb") as f:
            dados = f.read()

        parte = MIMEBase(maintype, subtype)
        parte.set_payload(dados)
        encoders.encode_base64(parte)
        parte.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(caminho_anexo)
        )
        msg.attach(parte)

    return msg

# =========================
# ENVIAR LOTE
# =========================
def enviar_lote(contatos, campanha, ja_enviados):
    assunto     = campanha["assunto"]
    corpo_base  = ler_mensagem(campanha["mensagem"])
    anexos      = campanha.get("anexos", [])

    if not corpo_base:
        log.error("Mensagem vazia. Abortando envio.")
        return

    enviados    = 0
    falhas      = 0
    pulados     = 0

    log.info(f"Iniciando envio — assunto: '{assunto}' — {len(contatos)} contato(s)")

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL, SENHA)
        log.info("Conectado ao Gmail com sucesso.")
    except Exception as e:
        log.error(f"Falha ao conectar ao Gmail: {e}")
        return

    for contato in contatos:
        destino = contato["email"]

        # Pular se já enviado nesta campanha
        chave = f"{assunto}|{destino}"
        if chave in ja_enviados:
            log.info(f"Pulando (já enviado): {destino}")
            pulados += 1
            continue

        corpo = personalizar(corpo_base, contato)
        msg   = montar_email(EMAIL, destino, assunto, corpo, anexos)

        # Tentativas com retry
        sucesso = False
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                server.send_message(msg)
                log.info(f"✅ Enviado ({tentativa}x): {destino}")
                registrar_enviado(chave)
                enviados += 1
                sucesso = True
                break
            except smtplib.SMTPRecipientsRefused:
                log.warning(f"❌ E-mail inválido/recusado: {destino}")
                falhas += 1
                break
            except smtplib.SMTPServerDisconnected:
                log.warning("Servidor desconectou. Reconectando...")
                try:
                    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                    server.login(EMAIL, SENHA)
                except Exception as e:
                    log.error(f"Falha ao reconectar: {e}")
                    break
            except Exception as e:
                log.error(f"Erro tentativa {tentativa} para {destino}: {e}")
                time.sleep(5)

        if not sucesso and chave not in ja_enviados:
            falhas += 1

        # Delay aleatório entre envios
        espera = random.uniform(*DELAY_ENTRE_EMAILS)
        time.sleep(espera)

    try:
        server.quit()
    except Exception:
        pass

    log.info(f"Lote concluído — ✅ {enviados} enviados | ❌ {falhas} falhas | ⏭ {pulados} pulados")

# =========================
# AGUARDAR HORÁRIO
# =========================
def esperar_horario(horario_str):
    """Espera até o horário HH:MM. Se já passou hoje, aguarda até amanhã."""
    agora = datetime.now()
    hora, minuto = map(int, horario_str.split(":"))
    alvo = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    if alvo <= agora:
        alvo += timedelta(days=1)
        log.info(f"Horário {horario_str} já passou hoje. Agendando para amanhã.")

    diff = (alvo - agora).total_seconds()
    log.info(f"⏳ Aguardando até {horario_str} ({int(diff//60)} min {int(diff%60)} seg)...")

    # Espera em blocos de 30s para não travar o processo
    while True:
        agora = datetime.now()
        if agora >= alvo:
            break
        restante = (alvo - agora).total_seconds()
        time.sleep(min(30, restante))

    log.info(f"🕐 Horário atingido: {horario_str}")

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
def main():
    print("\n" + "="*50)
    print("  INSTAGRAM EMAIL SENDER")
    print("="*50)

    contatos    = ler_contatos()
    ja_enviados = ler_enviados()

    if not contatos:
        print("❌ Nenhum contato encontrado em saida/usuarios.txt")
        return

    for i, campanha in enumerate(CAMPANHAS, 1):
        log.info(f"\n{'='*40}")
        log.info(f"Campanha {i}/{len(CAMPANHAS)}: '{campanha['assunto']}' às {campanha['horario']}")

        esperar_horario(campanha["horario"])

        log.info(f"🚀 Iniciando envio da campanha {i}...")
        enviar_lote(contatos, campanha, ja_enviados)

        # Recarregar enviados após cada lote
        ja_enviados = ler_enviados()

    log.info("\n🔥 TODAS AS CAMPANHAS FINALIZADAS.")
    print(f"\n✅ Log completo em {LOG_FILE}")
    print(f"📋 Registro de enviados em {ENVIADOS_FILE}")

if __name__ == "__main__":
    main()
