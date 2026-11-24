import time
import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from zoneinfo import ZoneInfo

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Painel Central - Biomassa", layout="wide")

# 2. LIGAÇÃO AO FIREBASE
FIREBASE_URL = "https://caldeiras-99-default-rtdb.europe-west1.firebasedatabase.app"
CAMINHO_FIREBASE = f"{FIREBASE_URL}/painel_biomassa.json"
TZ_LISBOA = ZoneInfo("Europe/Lisbon")

# ==============================================================================
# MÁQUINAS OCULTAS NO PAINEL
# Adicione ou remova aqui o código do zsql02 (ex: "RAM 2") ou o nome extenso
# (ex: "Râmula 2"). Tudo o que estiver nesta lista some do painel e do cálculo.
# ==============================================================================
MAQUINAS_OCULTAS = [
    "KUST 1", "Kuster 1",
    "KUST 3", "Kuster 3",
    "TERM 3", "Termofixação 3",
    "M.L.6",
]

OCULTAS_NORMALIZADAS = {nome.strip().upper() for nome in MAQUINAS_OCULTAS}

# Pesos de Vapor
PESO_VAPOR = {
    "LP5": 5, "Secador 33": 5, "SEC 33": 5, "PAD 2": 4,
    "Escovadeira 1": 4, "ESC 1": 4,
    "Enrolador 1": 1, "ENR 1": 1, "Enrolador 2": 1, "ENR 2": 1,
    "Calandra": 2, "CALAND": 2
}

# 3. ESTILOS VISUAIS (ZSQL02 + PISCAR EM TEMPO REAL)
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

.zsql-verde { background-color: #EAF8FC; }
.zsql-verde .zsql-header { background-color: #007A00; }

.zsql-vermelho { background-color: #D9D9D9; }
.zsql-vermelho .zsql-header { background-color: #800000; }

.zsql-setup { background-color: #D9D9D9; }
.zsql-setup .zsql-header { background-color: #800000; }

.zsql-manutencao { background-color: #FFFDE7; }
.zsql-manutencao .zsql-header { background-color: #800000; }

.piscando {
    animation: zsql-blink-borda 1s linear infinite;
}
.piscando .zsql-header {
    animation: zsql-blink-header 1s linear infinite;
}
</style>
""", unsafe_allow_html=True)

st.title("Central de Comando: Caldeira Biomassa")

@st.cache_data(ttl=2, show_spinner=False)
def buscar_dados_firebase():
    resp = requests.get(CAMINHO_FIREBASE, timeout=5)
    resp.raise_for_status()
    return resp.json()

def calcular_offset_zsql_ms(dados):
    """Calcula a diferença exata (ms) entre o relógio do zsql02 e o relógio UTC."""
    try:
        relogio_zsql = dados.get("relogio_zsql")
        firebase_ts = dados.get("firebase_ts")
        if relogio_zsql and isinstance(firebase_ts, (int, float)):
            dt_zsql = datetime.strptime(relogio_zsql, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_LISBOA)
            return int(dt_zsql.timestamp() * 1000) - int(firebase_ts)
    except Exception:
        pass
    return 0

def obter_agora_zsql(offset_ms):
    agora_ms = int(time.time() * 1000) + offset_ms
    return datetime.fromtimestamp(agora_ms / 1000.0, TZ_LISBOA).replace(tzinfo=None)

def render_barra_relogio_zsql():
    """Barra inferior estilo zsql02 com relógio em tempo real (JS) sincronizado com o servidor."""
    try:
        dados_ini = buscar_dados_firebase() or {}
    except Exception:
        dados_ini = {}

    offset_ms = calcular_offset_zsql_ms(dados_ini)
    fonte = dados_ini.get("relogio_fonte", "lisboa")
    server_zsql_ms = int(time.time() * 1000) + offset_ms

    html_relogio = f"""
    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        background:#0B0B0B;
        color:#FFFFFF;
        padding:7px 14px;
        border-radius:4px;
        font-family:'Segoe UI', Arial, sans-serif;
        font-size:13px;
        font-weight:700;
        border:1px solid #2a2a2a;
        box-sizing:border-box;
    ">
        <span>ZSQL02 | SINCRONIZAÇÃO: {fonte.upper()}</span>
        <div style="display:flex; align-items:center; gap:10px;">
            <span id="relogio-zsql">--</span>
            <span style="
                width:12px;
                height:12px;
                border-radius:50%;
                background:radial-gradient(circle at 35% 35%, #9cff9c, #00c800 60%, #006600);
                display:inline-block;
                box-shadow:0 0 6px #00e600;
            "></span>
        </div>
    </div>
    <script>
        const baseZsqlMs = {server_zsql_ms};
        const inicioLocal = performance.now();
        const fmt = new Intl.DateTimeFormat('en-GB', {{
            timeZone: 'Europe/Lisbon',
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            hourCycle: 'h23'
        }});

        function atualizarRelogio() {{
            const agoraMs = baseZsqlMs + (performance.now() - inicioLocal);
            const partes = Object.fromEntries(
                fmt.formatToParts(new Date(agoraMs)).map(p => [p.type, p.value])
            );
            document.getElementById('relogio-zsql').textContent =
                `${{partes.day}}-${{partes.month}}-${{partes.year}} ${{partes.hour}}:${{partes.minute}}:${{partes.second}}`;
        }}

        atualizarRelogio();
        setInterval(atualizarRelogio, 1000);
    </script>
    """
    components.html(html_relogio, height=42)

# 4. ATUALIZAÇÃO DOS CARDS EM TEMPO REAL (A cada 2 segundos)
@st.fragment(run_every=2)
def atualizar_conteudo():
    try:
        dados = buscar_dados_firebase()
        if not dados or not dados.get("maquinas"):
            st.info("Aguardando o primeiro envio do monitor local...")
            return
    except Exception:
        st.warning("A sincronizar com o servidor em tempo real...")
        return

    atualizado_em = dados.get("atualizado_em", "--")
    offset_ms = calcular_offset_zsql_ms(dados)
    agora = obter_agora_zsql(offset_ms)

    maquinas = dados.get("maquinas", [])
    if isinstance(maquinas, dict):
        maquinas = list(maquinas.values())

    # Filtra as máquinas ocultas antes de ordenar, calcular carga e desenhar a grelha
    maquinas = [
        m for m in maquinas
        if str(m.get("codigo", "")).strip().upper() not in OCULTAS_NORMALIZADAS
        and str(m.get("maquina", "")).strip().upper() not in OCULTAS_NORMALIZADAS
    ]

    prioridade = {"VERDE": 0, "AMARELO_MANUTENCAO": 1, "AMARELO_SETUP": 2, "VERMELHO": 3}
    maquinas.sort(key=lambda m: (
        0 if m.get("piscando") else 1,
        prioridade.get(m.get("estado_base", "VERMELHO"), 2),
        m.get("maquina", "")
    ))

    # Cálculo da Carga Térmica
    carga_vapor_atual = sum(
        PESO_VAPOR.get(m.get("maquina", ""), PESO_VAPOR.get(m.get("codigo", ""), 2))
        for m in maquinas
        if m.get("estado_base") == "VERDE" and m.get("energia") == "VAPOR"
    )

    col_gauge1, col_gauge2 = st.columns([1, 3])
    with col_gauge1:
        st.metric(label="Carga Térmica (Vapor)", value=f"{carga_vapor_atual} Pts")
    with col_gauge2:
        st.progress(min(carga_vapor_atual / 30.0, 1.0))
        if carga_vapor_atual > 20:
            st.warning("⚠️ ALERTA: Carga Alta. Prepare a fornalha.")

    st.markdown("---")
    st.subheader("Estado das Máquinas (Tempo Real)")

    qtd_piscando = sum(1 for m in maquinas if m.get("piscando"))

    for i in range(0, len(maquinas), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(maquinas):
                m = maquinas[i + j]
                maquina = m.get("maquina", "--")
                estado_base = m.get("estado_base", "VERMELHO")
                piscando = bool(m.get("piscando", False))
                energia = m.get("energia", "VAPOR")
                inicio_str = m.get("inicio", "")

                try:
                    dt_inicio = datetime.strptime(inicio_str, "%d/%m/%Y %H:%M:%S")
                    total_seg = max(0, int((agora - dt_inicio).total_seconds()))
                    dias, resto_dia = divmod(total_seg, 86400)
                    horas, resto = divmod(resto_dia, 3600)
                    minutos, segundos = divmod(resto, 60)

                    if dias > 0:
                        tempo_str = f"{dias}d {horas:02d}h {minutos:02d}m {segundos:02d}s"
                    else:
                        tempo_str = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"

                    data_str = dt_inicio.strftime("%Y-%m-%d %H:%M")
                except Exception:
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

                classe_pisca = "piscando" if piscando else ""

                card_html = (
                    f'<div class="zsql-card {classe_cor} {classe_pisca}">'
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

    st.caption(f"🟢 Último pulso do monitor: {atualizado_em} | Máquinas a piscar: {qtd_piscando}")

atualizar_conteudo()
render_barra_relogio_zsql()
