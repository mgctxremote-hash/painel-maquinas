import streamlit as st
import pandas as pd
from datetime import datetime

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

# 3. ESTILOS VISUAIS (CSS)
st.markdown("""
<style>
    .maq-verde { border-left: 5px solid #00E676; background-color: #112211; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,255,0,0.1); }
    .maq-vermelho { border-left: 5px solid #FF1744; background-color: #221111; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(255,0,0,0.1); }
    .maq-amarelo { border-left: 5px solid #FFEA00; background-color: #222211; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(255,255,0,0.1); }
    .maq-titulo { font-size: 18px; font-weight: bold; margin-bottom: 5px; color: #FFFFFF; }
    .maq-info { font-size: 13px; color: #AAAAAA; }
    .maq-tempo { font-size: 15px; font-weight: bold; margin-top: 10px; color: #DDDDDD; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 Central de Comando: Caldeira Biomassa")

# 4. BLOCO DE ATUALIZAÇÃO AUTOMÁTICA INVISÍVEL (A cada 10 segundos)
@st.fragment(run_every=10)
def atualizar_conteudo():
    try:
        df = pd.read_excel(URL_CSV) if "xlsx" in URL_CSV else pd.read_csv(URL_CSV)
        df.columns = ["Timestamp", "Maquina", "Estado", "Energia", "Data"]
        df['Data_Calc'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df_estado_atual = df.sort_values('Data_Calc').drop_duplicates(subset=['Maquina'], keep='last')
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

    agora = datetime.now()
    maquinas_lista = list(df_estado_atual.iterrows())

    # Grelha perfeita de 4 colunas
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
                    diferenca = agora - data_alteracao
                    horas, resto = divmod(diferenca.seconds, 3600)
                    minutos, segundos = divmod(resto, 60)
                    tempo_str = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"
                else:
                    tempo_str = "Desconhecido"

                if estado == "VERDE":
                    classe_css = "maq-verde"
                    icone = "⚙️"
                elif estado == "VERMELHO":
                    classe_css = "maq-vermelho"
                    icone = "🛑"
                else:
                    classe_css = "maq-amarelo"
                    icone = "⚠️"

                with cols[j]:
                    st.markdown(f"""
                    <div class="{classe_css}">
                        <div class="maq-titulo">{icone} {maquina}</div>
                        <div class="maq-info">⚡ {energia}</div>
                        <div class="maq-tempo">⏱️ {tempo_str}</div>
                    </div>
                    """, unsafe_allow_html=True)

# Executar a função do painel
atualizar_conteudo()
