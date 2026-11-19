import time
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Painel Central - Biomassa", page_icon="🔥", layout="wide")

# 2. DADOS E LIGAÇÕES
URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vStHxFw9mRCwhbqLEs9N75ht75YMilTncgASFmVVHJMG9UmTSxuntFAPtAWcl7j-0t1cPLF8wmarryg/pub?output=csv"

# Pesos de Vapor (nomes curtos e extensos)
PESO_VAPOR = {
    "LP5": 5, "Secador 33": 5, "SEC 33": 5, "PAD 2": 4,
    "Kuster 1": 3, "KUST 1": 3, "Kuster 3": 3, "KUST 3": 3,
    "Termofixação 3": 3, "TERM 3": 3, "M.L.6": 4,
    "Escovadeira 1": 4, "ESC 1": 4,
    "Enrolador 1": 1, "ENR 1": 1, "Enrolador 2": 1, "ENR 2": 1,
    "Calandra": 2, "CALAND": 2
}

# 3. ESTILOS VISUAIS (ZSQL02 + PISCAR APENAS QUANDO ATIVO NO SITE)
st.markdown("""
<style>
@keyframes zsql-blink-header {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.15; }
}

@keyframes zsql-blink-borda {
    0%, 100% { box-shadow: 0 0 0 2px #8c8c8c; }
    50% { box-shadow: 0 0 14px 3px #FFD700; }
}

.zsql-card {
    border: 1px solid #8c8c8c;
    border-radius: 3px;
    overflow: hidden;
    font-family: "Segoe UI", Arial, sans-serif;
    text-align: center;
    margin-bottom: 14px;
    min-height: 112px;
}

.zsql-header {
    color: #FFFFFF;
    font-weight: 700;
    font-size: 14px;
    padding: 5px 8px;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}

.zsql-faixa-amarela {
    height: 5px;
    width: 100%;
    background-color: #FFEA00;
}

.zsql-faixa-laranja {
    height: 5px;
    width: 100%;
    background-color: #FF9800;
}

.zsql-body {
    padding: 8px 8px 10px 8px;
    color: #0D2359;
}

.zsql-data {
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 3px;
}

.zsql-energia {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.zsql-tempo {
    font-size: 12px;
    font-weight: 600;
    color: #1F356B;
}

/* Estados fixos (estáticos) */
.zsql-verde {
    background-color: #EAF8FC;
}
.zsql-verde .zsql-header {
    background-color: #007A00;
}

.zsql-vermelho {
    background-color: #D9D9D9;
}
.zsql-vermelho .zsql-header {
    background-color: #800000;
}

.zsql-setup {
    background-color: #D9D9D9;
}
.zsql-setup .zsql-header {
    background-color: #800000;
}

.zsql-manutencao {
    background-color: #FFFDE7;
}
.zsql-manutencao .zsql-header {
    background-color: #800000;
}

/* Aplicado SOMENTE quando o monitor enviou *_PISCANDO */
.piscando {
    animation: zsql-blink-borda 1s linear infinite;
}
.piscando .zsql-header {
    animation: zsql-blink-header 1s linear infinite;
}
</style>
""", unsafe_allow_html=True)

st.title("🔥 Central de Comando: Caldeira Biomassa")

# 4. BLOCO DE ATUALIZAÇÃO AUTOMÁTICA (A cada 10 segundos)
@st.fragment(run_every=10)
def atualizar_conteudo():
    try:
        url_sem_cache = f"{URL_CSV}&cb={int(time.time())}"
        df = pd.read_excel(url_sem_cache) if "xlsx" in URL_CSV else pd.read_csv(url_sem_cache)
        if df.empty:
            st.info("Ainda não existem registos na planilha.")
            return

        df.columns = ["Timestamp", "Maquina", "Estado", "Energia", "Data"]
        df['Maquina'] = df['Maquina'].astype(str).str.strip()
        df['Estado'] = df['Estado'].astype(str).str.strip().str.upper()
        df['Energia'] = df['Energia'].astype(str).str.strip().str.upper()
        df['Data_Calc'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df['Estado_Base'] = df['Estado'].str.replace('_PISCANDO', '', regex=False)
        df = df.sort_values('Data_Calc', na_position='first')

        # Monta o estado atual preservando o início da cor base (sem zerar o tempo ao parar de piscar)
        registos = []
        for maq, grupo in df.groupby('Maquina', sort=False):
            ultima = grupo.iloc[-1]
            estado_atual = ultima['Estado']
            estado_base = ultima['Estado_Base']
            piscando = estado_atual.endswith('_PISCANDO')

            data_inicio = ultima['Data_Calc']
            for idx in range(len(grupo) - 1, -1, -1):
                if grupo.iloc[idx]['Estado_Base'] == estado_base:
                    data_inicio = grupo.iloc[idx]['Data_Calc']
                else:
                    break

            registos.append({
                "Maquina": maq,
                "Estado": estado_atual,
                "Estado_Base": estado_base,
                "Piscando": piscando,
                "Energia": ultima['Energia'],
                "Data_Calc": data_inicio
            })

        df_estado_atual = pd.DataFrame(registos)

        prioridade = {"VERDE": 0, "AMARELO_MANUTENCAO": 1, "AMARELO_SETUP": 2, "AMARELO": 2, "VERMELHO": 3}
        df_estado_atual['Ordem_Pisca'] = df_estado_atual['Piscando'].map({True: 0, False: 1})
        df_estado_atual['Ordem_Cor'] = df_estado_atual['Estado_Base'].map(prioridade).fillna(2)
        df_estado_atual = df_estado_atual.sort_values(['Ordem_Pisca', 'Ordem_Cor', 'Maquina'])
    except Exception:
        st.warning("A sincronizar com a nuvem...")
        return

    # Cálculo da Carga Térmica (conta VERDE e VERDE_PISCANDO)
    carga_vapor_atual = 0
    for _, row in df_estado_atual.iterrows():
        if row['Estado_Base'] == "VERDE" and row['Energia'] == "VAPOR":
            carga_vapor_atual += PESO_VAPOR.get(row['Maquina'], 2)

    col_gauge1, col_gauge2 = st.columns([1, 3])
    with col_gauge1:
        st.metric(label="Carga Térmica (Vapor)", value=f"{carga_vapor_atual} Pts")
    with col_gauge2:
        st.progress(min(carga_vapor_atual / 30.0, 1.0))
        if carga_vapor_atual > 20:
            st.warning("⚠️ ALERTA: Pico de Carga Detetado. Prepare a fornalha!")

    st.markdown("---")
    st.subheader("Estado das Máquinas (Tempo Real)")

    try:
        agora = datetime.now(ZoneInfo("Europe/Lisbon")).replace(tzinfo=None)
    except Exception:
        agora = datetime.now()

    maquinas_lista = list(df_estado_atual.iterrows())

    for i in range(0, len(maquinas_lista), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(maquinas_lista):
                _, row = maquinas_lista[i + j]
                maquina = row['Maquina']
                estado_base = row['Estado_Base']
                piscando = row['Piscando']
                energia = row['Energia']
                data_alteracao = row['Data_Calc']

                if pd.notnull(data_alteracao):
                    total_seg = max(0, int((agora - data_alteracao).total_seconds()))
                    horas, resto = divmod(total_seg, 3600)
                    minutos, segundos = divmod(resto, 60)
                    tempo_str = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"
                    data_str = data_alteracao.strftime('%Y-%m-%d %H:%M')
                else:
                    tempo_str = "Desconhecido"
                    data_str = "--"

                if estado_base == "VERDE":
                    classe_cor = "zsql-verde"
                    faixa_html = ""
                elif estado_base == "VERMELHO":
                    classe_cor = "zsql-vermelho"
                    faixa_html = ""
                elif estado_base == "AMARELO_MANUTENCAO":
                    classe_cor = "zsql-manutencao"
                    faixa_html = '<div class="zsql-faixa-amarela"></div>'
                else:
                    classe_cor = "zsql-setup"
                    faixa_html = '<div class="zsql-faixa-laranja"></div>'

                classe_pisca =
