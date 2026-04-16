# Instagram-automatization

<h2>Bem-Vindo(a)!</h2>
Meu nome é Paulo, e eu sou um estudante de programação, fiz esse programa juntamente com algumas inteligencias artificiais para poder fazer um freelance. Aceito quaisquer críticas e feedbacks sobre meu programa!

Use como preferir, mas lembre-se de me dar os créditos!!

Sistema automatizado para:

- Coletar seguidores de empresas no Instagram
- Filtrar perfis com até 30k seguidores
- Extrair e-mails e links de contato
- Enviar e-mails automaticamente via Gmail

## Estrutura

- `main_coletor.py` → coleta leads
- `main_envio.py` → envia e-mails
- `entrada/empresas.txt` → lista de empresas
- `saida/usuarios.txt` → leads coletados

## Como usar

### 1. Instalar dependências

pip install -r requirements.txt

### 2. Rodar coletor

python main_coletor.py

### 3. Rodar envio

python main_envio.py


## Observações

- Use conta do Instagram logada
- Evite rodar por longos períodos (risco de bloqueio)
- Use senha de app no Gmail
