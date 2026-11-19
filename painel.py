import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Central de Comando: Caldeira Biomassa",
    layout="wide"
)

# ==============================================================================
# CSS ESTILO ZSQL02 + ANIMAÇÃO DE PISCAR
# ==============================================================================
CSS_ZSQL02 = """
<style>
@keyframes piscar-verde {
    0%, 100% {
        box-shadow: 0 0 0 2px #888888;
        filter: brightness(100%);
    }
    50% {
        box-shadow: 0 0 14px 3px #00ff44;
        filter: brightness(115%);
    }
}

@keyframes piscar-alerta {
    0%, 100% {
        box-shadow: 0 0 0 2px #888888;
        background-color: #fffbe6;
    }
    50% {
        box-shadow: 0 0 16px 4px #ffd700;
        background-color: #fff176;
    }
}

@keyframes piscar-header-alerta {
    0%, 100% { background-color: #800000; }
    50% { background-color: #ff9800; }
}

.zsql-card {
    border: 1px solid #999999;
    border-radius: 3px;
    overflow: hidden;
    font-family: "Segoe UI", Arial, sans-serif;
    text-align: center;
    margin-bottom: 12px;
    min-height: 108px;
    transition: transform 0.15s ease;
}

.zsql-header {
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    padding: 4px 6px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}

.zsql-faixa {
    height: 4px;
    width: 100%;
}

.zsql-body {
    padding: 8px 6px 10px 6px;
    color: #0d2359;
    font-weight: 700;
}

.zsql-data {
    font-size: 11px;
    margin-bottom: 4px;
}

.zsql-status {
    font-size: 11px;
    text-transform: uppercase;
}

/* Estados visuais inspirados no zsql02 */
.estado-ligada {
    background-color: #eaf8fc;
}
.estado-ligada .zsql-header {
    background-color: #008000;
}

.estado-parada {
    background-color: #d9d9d9;
}
.estado-parada .zsql-header {
    background-color: #800000;
}

.estado-manutencao {
    background-color: #d9d9d9;
}
.estado-manutencao .zsql-header {
    background-color: #800000;
}
.estado-manutencao .zsql-faixa {
    background-color: #ffea00;
}

.estado-atencao {
    background-color: #d9d9d9;
}
.estado-atencao .zsql-header {
    background-color: #800000;
}
.estado-atencao .zsql-faixa {
    background-color: #ff9800;
}

/* Classes de piscar */
.piscar-ligada {
    animation: piscar-verde 1.1s infinite;
}

.piscar-alerta {
    animation: piscar-alerta 0.9s infinite;
}

.piscar-alerta .zsql-header {
    animation: piscar-header-alerta 0.9s infinite;
}
</style>
"""

st.markdown(CSS_ZSQL02, unsafe_allow_html=True)

# ==============================================================================
# COMPONENTE REUTILIZÁVEL DO CARD
# ==============================================================================
def render_card_zsql(nome: str, data_hora: str, status: str, estado: str = "ligada", piscar: bool = False):
    """
    estado: 'ligada' | 'parada' | 'manutencao' | 'atencao'
    piscar: True para ativar o efeito pulsante/piscante
    """
    classe_pisca = ""
    if piscar:
        classe_pisca = "piscar-ligada" if estado == "ligada" else "piscar-alerta"

    faixa_html = '<div class="zsql-faixa"></div>' if estado in ("manutencao", "atencao") else ""

    html = (
        f'<div class="zsql-card estado-{estado} {classe_pisca}">'
        f'<div class="zsql-header">{nome}</div>'
        f'{faixa_html}'
        f'<div class="zsql-body">'
        f'<div class="zsql-data">{data_hora}</div>'
        f'<div class="zsql-status">{status}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

# ==============================================================================
# EXEMPLO DE USO NO PAINEL
# ==============================================================================
st.title("Central de Comando: Caldeira Biomassa")

agora = datetime.now().strftime("%Y-%m-%d %H:%M")

maquinas = [
    {"nome": "CALDEIRA BIOMASSA", "data": agora, "status": "EM PRODUÇÃO", "estado": "ligada", "piscar": True},
    {"nome": "CALDEIRA 4", "data": agora, "status": "EM PRODUÇÃO", "estado": "ligada", "piscar": False},
    {"nome": "TERMOFLUIDO 5", "data": agora, "status": "AGUARDA", "estado": "manutencao", "piscar": True},
    {"nome": "CALDEIRA 7", "data": agora, "status": "PARADA", "estado": "parada", "piscar": False},
]

colunas = st.columns(4)
for idx, maq in enumerate(maquinas):
    with colunas[idx % 4]:
        render_card_zsql(
            nome=maq["nome"],
            data_hora=maq["data"],
            status=maq["status"],
            estado=maq["estado"],
            piscar=maq["piscar"]
        )
