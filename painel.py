import time
import requests
import threading
from bs4 import BeautifulSoup
from datetime import datetime
from requests_negotiate_sspi import HttpNegotiateAuth
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# ==========================================
# CONFIGURAÇÕES GERAIS
# ==========================================
URL_INTRANET = "http://zsql02/te/TEAP20/App_SF/wf_CenarioAP.aspx?posto=MORODRIGUES#!"
TEMPO_ATUALIZACAO_SEGUNDOS = 5

TELEGRAM_TOKEN = "8642176831:AAFkKoCjdmd19jH_U3LuUGZcyciRMBNHbms"
TELEGRAM_CHAT_IDS = ["8881477734", "8327669176"]

# ==========================================
# CONFIGURAÇÕES DO GOOGLE SHEETS
# ==========================================
URL_GOOGLE_FORMS = "https://docs.google.com/forms/d/e/1FAIpQLSehYxyhBq4VAewYexzvAVd5y1vLZJ2p0MfLAuDpj9Q7hEJSmw/formResponse"

ENTRY_MAQUINA = "entry.1563055906"
ENTRY_ESTADO = "entry.1954910161"
ENTRY_ENERGIA = "entry.559197562"
ENTRY_DATA = "entry.994032765"

# ==========================================
# DICIONÁRIOS DE MÁQUINAS E PESOS
# ==========================================
TIPO_ENERGIA = {
    "RAM 1": "TERMOFLUIDO", "RAM 2": "GÁS", "RAM 3": "GÁS",
    "RAM 5": "GÁS", "RAM 6": "GÁS", "RAM 7": "GÁS",
    "GAS 1": "GÁS", "GAS 2": "GÁS", "ROT-TINT": "NENHUMA", "ROT-PREP": "NENHUMA"
}

PESO_VAPOR = {
    "LP5": 5, "SEC 33": 5, "PAD 2": 4, "KUST 1": 3, "KUST 3": 3,
    "TERM 3": 3, "M.L.6": 4, "ESC 1": 4, "ENR 1": 1, "ENR 2": 1, "CALAND": 2
}

NOMES_EXTENSOS = {
    "RAM 1": "Râmula 1", "RAM 2": "Râmula 2", "RAM 3": "Râmula 3",
    "RAM 5": "Râmula 5", "RAM 6": "Râmula 6", "RAM 7": "Râmula 7",
    "SEC 33": "Secador 33", "LP5": "LP5", "KUST 1": "Kuster 1",
    "KUST 3": "Kuster 3", "ROT-TINT": "Rotativa Tinturaria",
    "ROT-PREP": "Rotativa Preparação", "GAS 1": "Gaseadeira 1", "GAS 2": "Gaseadeira 2"
}

executando = True

# ==========================================
# LÓGICA PRINCIPAL (CÉREBRO COM TELEGRAM E ÍCONE)
# ==========================================
class MonitorInteligente:
    def __init__(self):
        self.maquinas_a_piscar = {}
        self.estados_nuvem = {}  # Guarda o último estado enviado à planilha por máquina
        self.sessao = requests.Session()
        self.sessao.auth = HttpNegotiateAuth()

        self.historico_arranque = {}
        self.silenciadas = {}
        self.relatorio_enviado = ""

    def enviar_telegram(self, titulo, mensagem):
        for chat_id in TELEGRAM_CHAT_IDS:
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                dados = {"chat_id": chat_id, "text": f"*{titulo}*\n{mensagem}", "parse_mode": "Markdown"}
                requests.post(url, data=dados, timeout=5)
            except Exception:
                pass

    def enviar_lote_nuvem(self, lista_envios):
        for maquina, estado, energia in lista_envios:
            try:
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                dados_form = {
                    ENTRY_MAQUINA: maquina,
                    ENTRY_ESTADO: estado,
                    ENTRY_ENERGIA: energia,
                    ENTRY_DATA: data_atual
                }
                requests.post(URL_GOOGLE_FORMS, data=dados_form, timeout=5)
                time.sleep(0.1)
            except Exception:
                pass

    def verificar_dados(self):
        agora = time.time()
        hora_texto = datetime.now().strftime("%H:%M")

        horarios_turno = ["05:45", "13:45", "21:45"]
        if hora_texto in horarios_turno and self.relatorio_enviado != hora_texto:
            self.enviar_telegram(
                "📋 Relatório de Transição de Turno",
                "Os dados completos deste turno já estão fechados e disponíveis no painel na nuvem."
            )
            self.relatorio_enviado = hora_texto

        try:
            resposta = self.sessao.get(URL_INTRANET, timeout=10)
            resposta.raise_for_status()
            site = BeautifulSoup(resposta.text, 'lxml')

            atuais_piscando = {}
            estados_pagina = {}

            for maq in site.find_all('input', {'type': 'submit'}):
                nome = maq.get('value', '').strip()
                if not nome:
                    continue
                classes = maq.get('class', [])

                if "apxCenarioMAQ" in classes:
                    cor_base = "VERDE"
                elif "apxCenarioINA" in classes:
                    cor_base = "VERMELHO"
                elif "apxCenarioSTP" in classes:
                    cor_base = "AMARELO_SETUP"
                elif "apxCenaMANOFF" in classes:
                    cor_base = "AMARELO_MANUTENCAO"
                else:
                    continue

                piscando = "blink_me" in classes
                estados_pagina[nome] = f"{cor_base}_PISCANDO" if piscando else cor_base

                if piscando:
                    atuais_piscando[nome] = cor_base

            # Garantia: se uma máquina estava piscando e mudou para uma classe não mapeada, tira o piscar
            for maq_antiga, cor_antiga in self.maquinas_a_piscar.items():
                if maq_antiga not in estados_pagina:
                    estados_pagina[maq_antiga] = cor_antiga

            # 1. Envia para o Google Sheets apenas o que mudou (começou ou parou de piscar, ou trocou de cor)
            envios_nuvem = []
            for maq, estado_novo in estados_pagina.items():
                if self.estados_nuvem.get(maq) != estado_novo:
                    nome_real = NOMES_EXTENSOS.get(maq, maq)
                    energia = TIPO_ENERGIA.get(maq, "VAPOR")
                    envios_nuvem.append((nome_real, estado_novo, energia))
                    self.estados_nuvem[maq] = estado_novo

            if envios_nuvem:
                threading.Thread(target=self.enviar_lote_nuvem, args=(envios_nuvem,), daemon=True).start()

            # 2. Alertas do Telegram (somente quando começa a piscar / muda de cor piscando)
            for maq, cor_atual in atuais_piscando.items():
                if maq not in self.maquinas_a_piscar or self.maquinas_a_piscar[maq] != cor_atual:
                    nome_real = NOMES_EXTENSOS.get(maq, maq)
                    energia = TIPO_ENERGIA.get(maq, "VAPOR")

                    if maq in self.silenciadas and agora < self.silenciadas[maq]:
                        continue

                    if maq not in self.historico_arranque:
                        self.historico_arranque[maq] = []
                    self.historico_arranque[maq].append(agora)
                    self.historico_arranque[maq] = [t for t in self.historico_arranque[maq] if agora - t <= 300]

                    if len(self.historico_arranque[maq]) >= 3:
                        self.enviar_telegram(
                            f"⚠️ SPAM / AFINAÇÃO: {nome_real}",
                            "A máquina alterou o estado 3 vezes em menos de 5 min.\nAlertas silenciados por 15 minutos."
                        )
                        self.silenciadas[maq] = agora + 900
                        self.historico_arranque[maq] = []
                        continue

                    prefixo = "A" if "Rotativa" in nome_real else "A máquina"
                    if cor_atual == "VERDE":
                        self.enviar_telegram(f"🟢 LIGAR: {nome_real}", f"{prefixo} {nome_real} está a piscar a VERDE.\nConsumo de {energia} ativado.")
                    elif cor_atual == "VERMELHO":
                        self.enviar_telegram(f"🔴 PARAR: {nome_real}", f"{prefixo} {nome_real} está a piscar a VERMELHO.\nConsumo de {energia} cortado.")
                    elif cor_atual == "AMARELO_SETUP":
                        self.enviar_telegram(f"🟡 SETUP: {nome_real}", f"{prefixo} {nome_real} entrou em Limpeza/Setup (amarelo).")
                    elif cor_atual == "AMARELO_MANUTENCAO":
                        self.enviar_telegram(f"🟠 AVARIA: {nome_real}", f"{prefixo} {nome_real} aguarda manutenção (laranja).")

            self.maquinas_a_piscar = atuais_piscando
        except Exception:
            pass

def loop_monitorizacao():
    monitor = MonitorInteligente()
    while executando:
        monitor.verificar_dados()
        time.sleep(TEMPO_ATUALIZACAO_SEGUNDOS)

def sair_do_programa(icon, item):
    global executando
    executando = False
    icon.stop()

def criar_imagem_icone():
    imagem = Image.new('RGB', (64, 64), color='darkgreen')
    desenho = ImageDraw.Draw(imagem)
    desenho.rectangle((24, 24, 40, 40), fill='white')
    return imagem

if __name__ == "__main__":
    threading.Thread(target=loop_monitorizacao, daemon=True).start()
    icone_bandeja = pystray.Icon("Caldeira", criar_imagem_icone(), "Monitor", pystray.Menu(item('Encerrar', sair_do_programa)))
    icone_bandeja.run()
