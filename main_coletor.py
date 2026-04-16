from selenium import webdriver
from selenium.webdriver.common.by import By
import time, os, re

# =========================
# CONFIG
# =========================
PROFILE = os.path.abspath("chrome_profile")
MAX_SEGUIDORES = 30000
SCROLL_LIMIT = 30
DELAY = 1.5

# =========================
# PASTAS
# =========================
os.makedirs("saida", exist_ok=True)

# =========================
# DRIVER
# =========================
def iniciar():
    opt = webdriver.ChromeOptions()
    opt.add_argument("--start-maximized")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument(f"--user-data-dir={PROFILE}")
    return webdriver.Chrome(options=opt)

# =========================
# EMPRESAS
# =========================
def empresas():
    with open("entrada/empresas.txt", encoding="utf-8") as f:
        txt = f.read()
    return [e.strip().replace("@","") for e in txt.split("-") if e.strip()]

# =========================
# CONVERTER NUMERO
# =========================
def num(txt):
    txt = txt.lower().replace(",", "")
    if "k" in txt:
        return int(float(txt.replace("k","")) * 1000)
    if "m" in txt:
        return int(float(txt.replace("m","")) * 1000000)
    return int(re.sub(r"\D", "", txt))

# =========================
# EXPANDIR BIO
# =========================
def expandir(driver):
    try:
        driver.find_element(By.XPATH, "//span[contains(text(),'mais')]").click()
        time.sleep(0.5)
    except:
        pass

# =========================
# ANALISAR PERFIL
# =========================
def analisar(driver, user):
    try:
        driver.get(f"https://www.instagram.com/{user}/")
        time.sleep(DELAY)

        seguidores = driver.find_element(
            By.XPATH, "//ul/li[2]//span"
        ).get_attribute("title")

        seguidores = num(seguidores)

        if seguidores > MAX_SEGUIDORES:
            return None

        expandir(driver)

        texto = driver.find_element(By.TAG_NAME, "body").text

        email = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", texto)

        link = ""
        try:
            link = driver.find_element(By.XPATH, "//a[contains(@href,'http')]").get_attribute("href")
        except:
            pass

        if email or link:
            return (user, email[0] if email else "", link)

    except:
        return None

# =========================
# SALVAR (INCREMENTAL)
# =========================
def salvar(dado):
    with open("saida/usuarios.txt", "a", encoding="utf-8") as f:
        user, email, link = dado
        f.write(f"@{user} | {email} | {link}\n")

# =========================
# COLETAR SEGUIDORES
# =========================
def coletar(driver):
    lista = set()
    popup = driver.find_element(By.XPATH, "//div[@role='dialog']")

    for _ in range(SCROLL_LIMIT):
        users = popup.find_elements(By.XPATH, ".//a[contains(@href,'/')]")

        for u in users:
            try:
                username = u.get_attribute("href").split("/")[-2]
                if username and len(username) > 2:
                    lista.add(username)
            except:
                pass

        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", popup)
        time.sleep(DELAY)

    return list(lista)

# =========================
# EXECUÇÃO
# =========================

print("⚠️ FECHA O CHROME")
input("ENTER...")

driver = iniciar()

print("👉 LOGA NO INSTAGRAM")
input("ENTER depois...")

visitados = set()

for emp in empresas():
    print(f"\n🏢 {emp}")

    driver.get(f"https://www.instagram.com/{emp}/")
    time.sleep(4)

    driver.find_element(By.XPATH, "//a[contains(@href,'/followers')]").click()
    time.sleep(3)

    seguidores = coletar(driver)

    print(f"👥 {len(seguidores)} coletados")

    for u in seguidores:
        if u in visitados:
            continue

        visitados.add(u)

        r = analisar(driver, u)

        if r:
            salvar(r)
            print("✅", u)
        else:
            print("❌", u)

driver.quit()

print("🔥 FINALIZADO")
