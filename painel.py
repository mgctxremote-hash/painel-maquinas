import re
import time
import unicodedata
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
# FILTRO DE MÁQUINAS OCULTAS (IGNORA ACENTOS E MAIÚSCULAS)
# ==============================================================================
MAQUINAS_OCULTAS = [
    "ROT-PREP", "Rotativa Preparação",
    "ROT-TINT", "Rotativa Tinturaria",
    "ROT-ACAB", "Rotativa Acabamentos", "Rotativa dos Acabamentos",
    "KUST 1", "Kuster 1",
    "KUST 3", "Kuster 3",
    "TERM 3", "Termofixação 3",
    "M.L.6",
]

TERMOS_OCULTOS = [
    "ROTATIVA",
    "ROT-",
]

# ==============================================================================
# NOMES COMPLETOS PARA EXIBIÇÃO NO DISPLAY (CÓDIGO DO ZSQL02 -> NOME COMPLETO)
# ==============================================================================
NOMES_COMPLETOS = {
    # Acabamentos
    "RAM 1": "Râmula 1",
    "RAM 2": "Râmula 2",
    "RAM 3": "Râmula 3",
    "RAM 5": "Râmula 5",
    "RAM.5": "Râmula 5",
    "RAM 6": "Râmula 6",
    "RAM.6": "Râmula 6",
    "RAM 7": "Râmula 7",
    "RAM.7": "Râmula 7",
    "SANF 2": "Sanfor 2",
    "SANF 3": "Sanfor 3",
    "CALAND": "Calandra",
    "ESM.6": "Esmeriladora 6",
    "ESM 6": "Esmeriladora 6",
    "ESM.7": "Esmeriladora 7",
    "ESM 7": "Esmeriladora 7",
    "POLI 2": "Polimerizadora 2",
    "BIC 5": "BIC 5",
    "THIES 1": "Thies 1",
    "THIES 2": "Thies 2",

    # Preparação
    "SEC 33": "Secador 33",
    "GAS 1": "Gaseadeira 1",
    "GAS 2": "Gaseadeira 2",
    "ENR 1": "Enrolador 1",
    "ENR 2": "Enrolador 2",
    "OPER.EXT": "Operações Externas",
    "LP2I": "LP2I",
    "LP2II": "LP2II",
    "LP3I": "LP3I",
    "LP3II": "LP3II",
    "LP5": "LP5",
    "ROT-PREP": "Rotativa Preparação",

    # Tinturaria
    "ESC 1": "Escovadeira 1",
    "ESC 2": "Escovadeira 2",
    "ENR-TINT": "Enrolador Tinturaria",
    "PAD 2": "PAD 2",
    "TERM 3": "Termofixação 3",
    "KUST 1": "Kuster 1",
    "KUST 3": "Kuster 3",
    "M.L.6": "M.L.6",
    "ROT-TINT": "Rotativa Tinturaria",
}

# ==============================================================================
# DEFINIÇÃO DOS SETORES (NA ORDEM EM QUE APARECEM NO PAINEL)
# ==============================================================================
SETORES_MAQUINAS = {
    "Preparação": [
        "LP3I", "LP3II", "LP2I", "LP2II", "LP5",
        "SEC 33", "Secador 33",
        "GAS 1", "Gaseadeira 1",
        "GAS 2", "Gaseadeira 2",
        "ENR 1", "Enrolador 1",
        "ENR 2", "Enrolador 2",
        "OPER.EXT", "Operações Externas",
        "ROT-PREP", "Rotativa Preparação",
    ],
    "Acabamentos": [
        "RAM 1", "Râmula 1",
        "RAM 2", "Râmula 2",
        "RAM 3", "Râmula 3",
        "RAM 5", "RAM.5", "Râmula 5",
        "RAM 6", "RAM.6", "Râmula 6",
        "RAM 7", "RAM.7", "Râmula 7",
        "ESM.6", "ESM 6", "Esmeriladora 6",
        "ESM.7", "ESM 7", "Esmeriladora 7",
        "BIC 5",
        "POLI 2", "Polimerizadora 2",
        "SANF 2", "Sanfor 2",
        "SANF 3", "Sanfor 3",
        "CALAND", "Calandra",
        "THIES 1", "Thies 1",
        "THIES 2", "Thies 2",
    ],
    "Tinturaria": [
        "ESC 1", "Escovadeira 1",
        "ESC 2", "Escovadeira 2",
        "ENR-TINT", "Enrolador Tinturaria",
        "M.L.6",
        "PAD 2",
        "TERM 3", "Termofixação 3",
        "KUST 1", "Kuster 1",
        "KUST 3", "Kuster 3",
        "ROT-TINT", "Rotativa Tinturaria",
    ],
}

def normalizar_texto(texto: str) -> str:
    texto = str(texto or "").strip().upper()
    sem_acento = "".join(
        ch for ch in unicodedata.normalize("NFD", texto)
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join(sem_acento.split())

def chave_natural(texto: str):
    """Ordena números de forma natural (ex: Râmula 2 antes de Râmula 10)."""
    partes = re.split(r"(\d+)", normalizar_texto(texto))
    return [int(p) if p.isdigit() else p for p in partes]

OCULTAS_NORMALIZADAS = {normalizar_texto(nome) for nome in MAQUINAS_OCULTAS}
TERMOS_OCULTOS_NORMALIZADOS = [normalizar_texto(termo) for termo in TERMOS_OCULTOS]

MAPA_NOMES_COMPLETOS = {
    normalizar_texto(chave): valor
    for chave, valor in NOMES_COMPLETOS.items()
}

MAPA_SETOR = {}
for nome_setor, lista_maqs in SETORES_MAQUINAS.items():
    for item_maq in lista_maqs:
        MAPA_SETOR[normalizar_texto(item_maq)] = nome_setor

def obter_estado_base(m: dict) -> str:
    return normalizar_texto(m.get("estado_base", "VERMELHO"))

def obter_nome_completo(m: dict) -> str:
    codigo_norm = normalizar_texto(m.get("codigo", ""))
    maquina_norm = normalizar_texto(m.get("maquina", ""))
    if codigo_norm in MAPA_NOMES_COMPLETOS:
        return MAPA_NOMES_COMPLETOS[codigo_norm]
    if maquina_norm in MAPA_NOMES_COMPLETOS:
        return MAPA_NOMES_COMPLETOS[maquina_norm]
    return str(m.get("maquina") or m.get("codigo") or "--").strip()

def deve_ocultar(m: dict) -> bool:
    codigo = normalizar_texto(m.get("codigo", ""))
    nome = normalizar_texto(m.get("maquina", ""))
    nome_completo = normalizar_texto(obter_nome_completo(m))

    if (
        codigo in OCULTAS_NORMALIZADAS
        or nome in OCULTAS_NORMALIZADAS
        or nome_completo in OCULTAS_NORMALIZADAS
    ):
        return True

    for termo in TERMOS_OCULTOS_NORMALIZADOS:
        if termo and (termo in codigo or termo in nome or termo in nome_completo):
            return True

    return False

def identificar_setor(m: dict) -> str:
    codigo = normalizar_texto(m.get("codigo", ""))
    nome = normalizar_texto(m.get("maquina", ""))
    nome_completo = normalizar_texto(obter_nome_completo(m))
    return (
        MAPA_SETOR.get(codigo)
        or MAPA_SETOR.get(nome)
        or MAPA_SETOR.get(nome_completo)
        or "Outros"
    )

def chave_ordenacao_maquina(m: dict):
    """
    Garante dentro de cada setor:
      1º Online (VERDE) -> piscando primeiro, depois fixas
      2º Manutenção (AMARELO_MANUTENCAO) -> piscando primeiro
      3º Setup (AMARELO_SETUP) -> piscando primeiro
      4º Paradas (VERMELHO) -> piscando primeiro, depois fixas
    """
    estado = obter_estado_base(m)
    piscando = bool(m.get("piscando", False))
    prioridade_estado = {
        "VERDE": 0,
        "AMARELO_MANUTENCAO": 1,
        "AMARELO_SETUP": 2,
        "VERMELHO": 3,
    }.get(estado, 2)

    return (
        prioridade_estado,
        0 if piscando else 1,
        chave_natural(obter_nome_completo(m)),
    )

# Pesos de Vapor
PESO_VAPOR = {
    "LP5": 5, "Secador 33": 5, "SEC 33": 5, "PAD 2": 4,
    "Escovadeira 1": 4, "ESC 1": 4,
    "Enrolador 1": 1, "ENR 1": 1, "Enrolador 2": 1, "ENR 2": 1,
    "Calandra": 2, "CALAND": 2
}

MAPA_PESO_VAPOR = {
    normalizar_texto(chave): valor
    for chave, valor in PESO_VAPOR.items()
}

def obter_peso_vapor(m: dict) -> int:
    for campo in (obter_nome_completo(m), m.get("maquina", ""), m.get("codigo", "")):
        chave = normalizar_texto(campo)
        if chave in MAPA_PESO_VAPOR:
            return MAPA_PESO_VAPOR[chave]
    return 2

# 3. ESTILOS VISUAIS (ZSQL02 + SETORES + DESTAQUE ONLINE + PISCAR)
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

.zsql-setor-titulo {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    border-left: 5px solid #4682B4;
    background-color: rgba(70, 130, 180, 0.14);
    padding: 8px 14px;
    border-radius: 4px;
    margin: 20px 0 12px 0;
    font-family: "Segoe UI", Arial, sans-serif;
}

.zsql-setor-ativo {
    border-left-color: #00A83F;
}

.zsql-setor-nome {
    color: #4682B4;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

.zsql-setor-badges {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
}

.zsql-badge {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 999px;
    letter-spacing: 0.3px;
}

.zsql-badge-online {
    background-color: rgba(0, 168, 63, 0.22);
    color: #00E676;
    border: 1px solid rgba(0, 168, 63, 0.55);
}

.zsql-badge-alerta {
    background-color: rgba(255, 193, 7, 0.20);
    color: #FFD54F;
    border: 1px solid rgba(255, 193, 7, 0.50);
}

.zsql-badge-parada {
    background-color: rgba(150, 150, 150, 0.18);
    color: #BDBDBD;
    border: 1px solid rgba(150, 150, 150, 0.40);
}

.zsql-badge-piscar {
    background-color: rgba(255, 215, 0, 0.25);
    color: #FFD700;
    border: 1px solid #FFD700;
}

.zsql-card {
    border: 1px solid #8c8c8c;
    border-radius: 4px;
    overflow: hidden;
    font-family: "Segoe UI", Arial, sans-serif;
    text-align: center;
    margin-bottom: 14px;
    min-height: 118px;
}

.zsql-header {
    color: #FFFFFF;
    font-weight: 700;
    font-size: 14px;
    padding: 6px 8px;
    letter-spacing: 0.3px;
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
    padding: 7px 8px 10px 8px;
    color: #0D2359;
}

.zsql-status-pill {
    display: inline-block;
    font-size: 10px;
    font-weight: 800;
    padding: 1px 7px;
    border-radius: 10px;
    margin-bottom: 5px;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}

.pill-online {
    background-color: #D1F2DC;
    color: #006B27;
    border: 1px solid #009938;
}

.pill-manut {
    background-color: #FFF3B0;
    color: #7A4F01;
    border: 1px solid #D4A000;
}

.pill-setup {
    background-color: #FFE0B2;
    color: #8A4300;
    border: 1px solid #E67E00;
}

.pill-parada {
    background-color: #C9C9C9;
    color: #5C1A1A;
    border: 1px solid #9E9E9E;
}

.zsql-data {
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 2px;
}

.zsql-energia {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 5px;
}

.zsql-tempo {
    font-size: 12px;
    font-weight: 600;
    color: #1F356B;
}

/* ONLINE (VERDE) - Destaque principal */
.zsql-verde {
    background-color: #EAF8FC;
    border: 2px solid #009938;
    box-shadow: 0 3px 10px rgba(0, 153, 56, 0.22);
}
.zsql-verde .zsql-header {
    background-color: #007A00;
}

/* PARADA (VERMELHO) - Mais discreta quando não está a piscar */
.zsql-vermelho {
    background-color: #D9D9D9;
    opacity: 0.72;
}
.zsql-vermelho .zsql-header {
    background-color: #800000;
}

.zsql-setup {
    background-color: #E2E2E2;
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

.piscando {
    opacity: 1 !important;
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

def montar_card_html(m: dict, agora: datetime) -> str:
    maquina = obter_nome_completo(m)
    estado_base = obter_estado_base(m)
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
        pill_html = '<div class="zsql-status-pill pill-online">● Online</div>'
    elif estado_base == "VERMELHO":
        classe_cor = "zsql-vermelho"
        faixa_html = ""
        pill_html = '<div class="zsql-status-pill pill-parada">● Parada</div>'
    elif estado_base == "AMARELO_MANUTENCAO":
        classe_cor = "zsql-manutencao"
        faixa_html = '<div class="zsql-faixa-amarela"></div>'
        pill_html = '<div class="zsql-status-pill pill-manut">● Manutenção</div>'
    else:
        classe_cor = "zsql-setup"
        faixa_html = '<div class="zsql-faixa-laranja"></div>'
        pill_html = '<div class="zsql-status-pill pill-setup">● Setup</div>'

    classe_pisca = "piscando" if piscando else ""

    return (
        f'<div class="zsql-card {classe_cor} {classe_pisca}">'
        f'<div class="zsql-header">{maquina}</div>'
        f'{faixa_html}'
        f'<div class="zsql-body">'
        f'{pill_html}'
        f'<div class="zsql-data">{data_str}</div>'
        f'<div class="zsql-energia">{energia}</div>'
        f'<div class="zsql-tempo">⏱️ {tempo_str}</div>'
        f'</div>'
        f'</div>'
    )

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

    # Remove as máquinas ocultas antes de agrupar e calcular carga
    maquinas = [m for m in maquinas if not deve_ocultar(m)]

    # Métricas gerais
    total_online = sum(1 for m in maquinas if obter_estado_base(m) == "VERDE")
    carga_vapor_atual = sum(
        obter_peso_vapor(m)
        for m in maquinas
        if obter_estado_base(m) == "VERDE" and normalizar_texto(m.get("energia", "")) == "VAPOR"
    )

    col_online, col_gauge1, col_gauge2 = st.columns([1, 1, 2.5])
    with col_online:
        st.metric(label="Máquinas Online", value=f"{total_online} / {len(maquinas)}")
    with col_gauge1:
        st.metric(label="Carga Térmica (Vapor)", value=f"{carga_vapor_atual} Pts")
    with col_gauge2:
        st.progress(min(carga_vapor_atual / 30.0, 1.0))
        if carga_vapor_atual > 20:
            st.warning("⚠️ ALERTA: Carga Alta. Prepare a fornalha.")

    st.markdown("---")
    st.subheader("Estado das Máquinas por Setor (Online Primeiro)")

    # Agrupa as máquinas mantendo cada uma no seu setor
    ordem_setores = ["Preparação", "Acabamentos", "Tinturaria", "Outros"]
    grupos = {setor: [] for setor in ordem_setores}
    for m in maquinas:
        grupos[identificar_setor(m)].append(m)

    for setor_nome in ordem_setores:
        lista_setor = grupos[setor_nome]
        if not lista_setor:
            continue

        # Ordena estritamente com ONLINE (VERDE) primeiro dentro do setor
        lista_setor.sort(key=chave_ordenacao_maquina)

        qtd_online = sum(1 for m in lista_setor if obter_estado_base(m) == "VERDE")
        qtd_alerta = sum(1 for m in lista_setor if obter_estado_base(m) in ("AMARELO_MANUTENCAO", "AMARELO_SETUP"))
        qtd_parada = sum(1 for m in lista_setor if obter_estado_base(m) == "VERMELHO")
        qtd_piscar_setor = sum(1 for m in lista_setor if m.get("piscando"))

        badges_html = [f'<span class="zsql-badge zsql-badge-online">🟢 {qtd_online} Online</span>']
        if qtd_alerta > 0:
            badges_html.append(f'<span class="zsql-badge zsql-badge-alerta">⚠️ {qtd_alerta} Manut./Setup</span>')
        badges_html.append(f'<span class="zsql-badge zsql-badge-parada">🔴 {qtd_parada} Paradas</span>')
        if qtd_piscar_setor > 0:
            badges_html.append(f'<span class="zsql-badge zsql-badge-piscar">🔔 {qtd_piscar_setor} A piscar</span>')

        classe_setor_ativo = "zsql-setor-ativo" if qtd_online > 0 else ""

        st.markdown(
            f'<div class="zsql-setor-titulo {classe_setor_ativo}">'
            f'<span class="zsql-setor-nome">{setor_nome}</span>'
            f'<div class="zsql-setor-badges">{"".join(badges_html)}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        for i in range(0, len(lista_setor), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(lista_setor):
                    with cols[j]:
                        st.markdown(montar_card_html(lista_setor[i + j], agora), unsafe_allow_html=True)

    qtd_piscando = sum(1 for m in maquinas if m.get("piscando"))
    st.caption(f"🟢 Último pulso do monitor: {atualizado_em} | Máquinas online: {total_online} | A piscar: {qtd_piscando}")

atualizar_conteudo()
render_barra_relogio_zsql()
