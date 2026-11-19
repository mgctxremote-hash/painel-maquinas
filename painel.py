import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Painel Central - Biomassa", page_icon="🔥", layout="wide")

# 2. DADOS E LIGAÇÕES
URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vStHxFw9mRCwhbqLEs9N75ht75YMilTncgASFmVVHJMG9UmTSxuntFAPtAWcl7j-0t1cPLF8wmarryg/pub?output=csv"

# Pesos de Vapor
PESO_VAPOR = {
    "LP5": 5, "Secador 33": 5, "PAD 2": 4, "Kuster 1": 3, "Kuster 3": 3,
    "Termofixação 3": 3, "M.L.6": 4, "Escovadeira 1": 4, "Enrolador 1": 1,
    "Enrolador 2": 1, "Calandra": 2
}

# 3. ESTILOS VISUAIS (ESTILO ZSQL02 + PISCAR)
st.markdown("""
<style>
@keyframes piscar-verde-card {
    0%, 100% {
        box-shadow: 0 0 0 1px #7a7a7a;
        border-color: #7a7a7a;
    }
    50% {
        box-shadow: 0 0 14px 3px rgba(0, 230, 118, 0.85);
        border-color: #00E676;
    }
}

@keyframes piscar-verde-header {
    0%, 100% { background-color: #007A00; }
    50% { background-color: #00B838; }
}

@keyframes piscar-amarelo-card {
    0%, 100% {
        box-shadow: 0 0 0 1px #800000;
        background-color: #FFF9C4;
    }
    50% {
        box-shadow: 0 0 16px 4px rgba(255, 214, 0, 0.95);
        background-color: #FFEE58;
    }
}

@keyframes piscar-amarelo-header {
    0%, 100% { background-color: #800000; }
    50% { background-color: #E65100; }
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

.zsql-faixa {
    height: 5px;
    width: 100%;
    background-color: #FFEA00;
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

/* VERDE - EM OPERAÇÃO (PISCANDO) */
.zsql-verde {
    background-color: #EAF8FC;
    animation: piscar-verde-card 1.2s infinite;
}
.zsql-verde .zsql-header {
    background-color: #007A00;
    animation: piscar-verde-header 1.2s infinite;
}

/* VERMELHO - PARADA (ESTÁTICO) */
.zsql-vermelho {
    background-color: #D9D9D9;
}
.zsql-vermelho .zsql-header {
    background-color: #800000;
}

/* AMARELO - MANUTENÇÃO / ALERTA (PISCANDO) */
.zsql-amarelo {
    background-color: #FFF9C4;
    animation: piscar-amarelo-card 0.9s infinite;
}
.zsql-amarelo .zsql-header {
    background-color: #800000;
    animation: piscar-amarelo-header 0.9s infinite;
}
</style>
""", unsafe_allow_html=True)

st.title("🔥 Central de Comando: Caldeira Biomassa")

# 4. BLOCO DE ATUALIZAÇÃO AUTOMÁTICA INVISÍVEL (A cada 10 segundos)
@st.fragment(run_every=10)
def atualizar_conteudo():
    try:
        df = pd.read_excel(URL_CSV) if "xlsx" in URL_CSV else pd.read_csv(URL_CSV)
        df.columns = ["Timestamp", "Maquina", "Estado", "Energia", "Data"]
        df['Maquina'] = df['Maquina'].astype(str).str.strip()
        df['Estado'] = df['Estado'].astype(str).str.strip().str.upper()
        df['Energia'] = df['Energia'].astype(str).str.strip().str.upper()
        df['Data_Calc'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M:%S', errors='coerce')

        df_estado_atual = df.sort_values('Data_Calc').drop_duplicates(subset=['Maquina'], keep='last')

        # Ordena: VERDE primeiro, depois AMARELO, depois VERMELHO
        prioridade = {"VERDE": 0, "AMARELO": 1, "VERMELHO": 2}
        df_estado_atual['Ordem'] = df_estado_atual['Estado'].map(prioridade).fillna(1)
        df_estado_atual = df_estado_atual.sort_values(['Ordem', 'Maquina'])
    except Exception:
        st.warning("A sincronizar com a nuvem...")
        return

    # Cálculo da Carga Térmica
    carga_vapor_atual = 0
    for _, row in df_estado_atual.iterrows():
        if row['Estado'] == "VERDE" and row['Energia'] == "VAPOR":
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

    # Grelha de 4 colunas estilo zsql02
    for i in range(0, len(maquinas_lista), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(maquinas_lista):
                _, row = maquinas_lista[i + j]
                maquina = row['Maquina']
                estado = row['Estado']
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

                if estado == "VERDE":
                    classe_css = "zsql-verde"
                    faixa_html = ""
                elif estado == "VERMELHO":
                    classe_css = "zsql-vermelho"
                    faixa_html = ""
                else:
                    classe_css = "zsql-amarelo"
                    faixa_html = '<div class="zsql-faixa"></div>'

                card_html = (
                    f'<div class="zsql-card {classe_css}">'
                    f'<div class="zsql-header">{maquina}</div>'
                    f'{faixa_html}'
                    f'<div class="zsql-body">'
                    f'<div class="zsql-data">{data_str}</div>'
                    f'<div class="zsql-energia">{energia}</div>'
                    f'<div class="zsql-tempo">⏱️ {tempo_str}</div>'
                    f'</div>'
                    f'</div>'
                )

                with cols[j]:
                    st.markdown(card_html, unsafe_allow_html=True)

# Executar a função do painel
atualizar_conteudo()
