from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time, os, re, json, logging, random

# =========================
# CONFIG
# =========================
PROFILE        = os.path.abspath("chrome_profile")
MAX_SEGUIDORES = 30_000
DELAY_MIN      = 1.5   # delay mínimo entre ações (segundos)
DELAY_MAX      = 3.5   # delay máximo (simula comportamento humano)
TIMEOUT        = 10    # WebDriverWait timeout

CHECKPOINT     = "saida/checkpoint.json"   # salva progresso
LOG_FILE       = "saida/coletor.log"

# =========================
# LOGGING
# =========================
os.makedirs("saida", exist_ok=True)
os.makedirs("entrada", exist_ok=True)

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
# DELAY ALEATÓRIO
# =========================
def pausa(extra=0):
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX) + extra)

# =========================
# DRIVER
# =========================
def iniciar_driver():
    opt = webdriver.ChromeOptions()
    opt.add_argument("--start-maximized")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument(f"--user-data-dir={PROFILE}")
    driver = webdriver.Chrome(options=opt)
    driver.implicitly_wait(3)
    return driver

# =========================
# EMPRESAS
# =========================
def ler_empresas():
    caminho = "entrada/empresas.txt"
    if not os.path.exists(caminho):
        log.error(f"Arquivo não encontrado: {caminho}")
        return []
    with open(caminho, encoding="utf-8") as f:
        txt = f.read()
    empresas = [e.strip().replace("@", "") for e in txt.split("-") if e.strip()]
    log.info(f"{len(empresas)} empresa(s) carregada(s): {empresas}")
    return empresas

# =========================
# CHECKPOINT (PROGRESSO)
# =========================
def carregar_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, encoding="utf-8") as f:
            return json.load(f)
    return {"visitados": [], "empresas_feitas": []}

def salvar_checkpoint(dados):
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =========================
# CONVERTER NÚMERO (ex: "12,4 mil" ou "12.4k")
# =========================
def parse_numero(txt):
    if not txt:
        return 0
    txt = txt.lower().strip().replace(",", ".").replace("\xa0", "")
    try:
        if "mil" in txt or "k" in txt:
            return int(float(re.sub(r"[^\d.]", "", txt)) * 1_000)
        if "m" in txt or "mi" in txt:
            return int(float(re.sub(r"[^\d.]", "", txt)) * 1_000_000)
        return int(re.sub(r"\D", "", txt))
    except Exception:
        return 0

# =========================
# DETECTAR BLOQUEIO
# =========================
def verificar_bloqueio(driver):
    url = driver.current_url
    texto = driver.page_source[:2000].lower()
    if any(k in texto for k in ["checkpoint", "suspicious", "atividade incomum", "captcha", "challenge"]):
        log.warning("⚠️  Possível bloqueio detectado! Pausando 60s...")
        time.sleep(60)
        return True
    if "accounts/login" in url:
        log.warning("⚠️  Redirecionado para login. Você foi deslogado.")
        input("Faça login novamente e pressione ENTER...")
        return True
    return False

# =========================
# EXPANDIR BIO
# =========================
def expandir_bio(driver):
    try:
        botao = driver.find_element(By.XPATH, "//span[contains(text(),'mais') or contains(text(),'more')]")
        botao.click()
        time.sleep(0.5)
    except Exception:
        pass

# =========================
# ANALISAR PERFIL
# =========================
def analisar_perfil(driver, username):
    try:
        driver.get(f"https://www.instagram.com/{username}/")
        pausa()

        if verificar_bloqueio(driver):
            return None

        # Tenta múltiplas estratégias para pegar seguidores
        qtd_seguidores = 0
        try:
            wait = WebDriverWait(driver, TIMEOUT)
            # Estratégia 1: atributo title no span (mais confiável)
            el = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//a[contains(@href,'followers')]//span[@title]")
            ))
            qtd_seguidores = parse_numero(el.get_attribute("title"))
        except TimeoutException:
            try:
                # Estratégia 2: texto do span dentro do link de seguidores
                el = driver.find_element(By.XPATH, "//a[contains(@href,'followers')]//span")
                qtd_seguidores = parse_numero(el.text)
            except NoSuchElementException:
                log.debug(f"Não encontrou seguidores para @{username}")
                return None

        if qtd_seguidores > MAX_SEGUIDORES:
            log.debug(f"@{username} ignorado ({qtd_seguidores:,} seguidores)")
            return None

        expandir_bio(driver)
        pausa(0.5)

        texto_pagina = driver.find_element(By.TAG_NAME, "body").text

        # Extrair e-mail
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", texto_pagina)
        email = emails[0] if emails else ""

        # Extrair link da bio (âncoras externas, não do próprio Instagram)
        link = ""
        try:
            candidatos = driver.find_elements(By.XPATH, "//a[contains(@href,'http') and not(contains(@href,'instagram.com'))]")
            if candidatos:
                link = candidatos[0].get_attribute("href")
        except Exception:
            pass

        if email or link:
            return (username, email, link, qtd_seguidores)

    except Exception as e:
        log.error(f"Erro ao analisar @{username}: {e}")

    return None

# =========================
# SALVAR LEAD
# =========================
def salvar_lead(dado):
    username, email, link, seguidores = dado
    with open("saida/usuarios.txt", "a", encoding="utf-8") as f:
        f.write(f"@{username} | {email} | {link} | {seguidores} seguidores\n")

# =========================
# COLETAR SEGUIDORES DE UMA PÁGINA
# =========================
def coletar_seguidores(driver, empresa):
    log.info(f"Abrindo perfil: @{empresa}")
    driver.get(f"https://www.instagram.com/{empresa}/")
    pausa(2)

    if verificar_bloqueio(driver):
        return []

    # Clicar no link de seguidores
    try:
        wait = WebDriverWait(driver, TIMEOUT)
        btn_seguidores = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@href,'/followers/') or contains(@href,'followers')]")
        ))
        btn_seguidores.click()
        pausa(2)
    except TimeoutException:
        log.error(f"Não encontrou botão de seguidores para @{empresa}")
        return []

    # Aguardar modal abrir
    try:
        wait = WebDriverWait(driver, TIMEOUT)
        popup = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
    except TimeoutException:
        log.error(f"Modal de seguidores não abriu para @{empresa}")
        return []

    lista = set()
    sem_novos = 0
    MAX_SEM_NOVOS = 4  # para se ficou 4 scrolls sem novos usuários

    log.info(f"Coletando seguidores de @{empresa}...")

    while True:
        links = popup.find_elements(By.XPATH, ".//a[contains(@href,'/') and not(contains(@href,'javascript'))]")
        antes = len(lista)

        for link in links:
            try:
                href = link.get_attribute("href") or ""
                partes = [p for p in href.rstrip("/").split("/") if p]
                if partes:
                    username = partes[-1]
                    if len(username) > 1 and username not in ("explore", "reels", "stories"):
                        lista.add(username)
            except Exception:
                pass

        novos = len(lista) - antes
        if novos == 0:
            sem_novos += 1
            if sem_novos >= MAX_SEM_NOVOS:
                log.info(f"Sem novos usuários há {MAX_SEM_NOVOS} scrolls. Finalizando coleta.")
                break
        else:
            sem_novos = 0

        # Scroll dentro do modal
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", popup)
        pausa()

        log.info(f"  {len(lista)} usuários coletados até agora...")

    log.info(f"Total coletado de @{empresa}: {len(lista)} usuários")
    return list(lista)

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
def main():
    print("\n" + "="*50)
    print("  INSTAGRAM LEAD COLLECTOR")
    print("="*50)
    print("⚠️  Feche qualquer instância do Chrome antes de continuar.")
    input("Pressione ENTER para iniciar o navegador...\n")

    driver = iniciar_driver()

    print("👉 Faça login no Instagram no navegador que abriu.")
    input("Pressione ENTER quando estiver logado...\n")

    empresas = ler_empresas()
    if not empresas:
        print("❌ Nenhuma empresa encontrada em entrada/empresas.txt")
        driver.quit()
        return

    checkpoint = carregar_checkpoint()
    visitados  = set(checkpoint.get("visitados", []))
    feitas     = set(checkpoint.get("empresas_feitas", []))

    total_leads = 0

    for empresa in empresas:
        if empresa in feitas:
            log.info(f"@{empresa} já processada (checkpoint). Pulando.")
            continue

        log.info(f"\n{'='*40}")
        log.info(f"Processando empresa: @{empresa}")

        seguidores = coletar_seguidores(driver, empresa)

        novos = [u for u in seguidores if u not in visitados]
        log.info(f"{len(novos)} usuários novos para analisar de @{empresa}")

        for username in novos:
            visitados.add(username)

            resultado = analisar_perfil(driver, username)

            if resultado:
                salvar_lead(resultado)
                total_leads += 1
                log.info(f"✅ Lead salvo: @{username} | {resultado[1]} | {resultado[2]}")
            else:
                log.debug(f"❌ Sem contato: @{username}")

            # Salvar checkpoint a cada usuário analisado
            checkpoint["visitados"] = list(visitados)
            salvar_checkpoint(checkpoint)

        feitas.add(empresa)
        checkpoint["empresas_feitas"] = list(feitas)
        salvar_checkpoint(checkpoint)

        log.info(f"@{empresa} concluída. Total de leads até agora: {total_leads}")

        # Pausa entre empresas para não levantar suspeita
        pausa(random.uniform(5, 10))

    driver.quit()
    log.info(f"\n🔥 FINALIZADO. Total de leads coletados: {total_leads}")
    print(f"\n✅ Leads salvos em saida/usuarios.txt")
    print(f"📋 Log completo em {LOG_FILE}")

if __name__ == "__main__":
    main()
