# -*- coding: utf-8 -*-
import sys
import threading
import os
import re
import time
import glob
import ctypes
import json
import math
from datetime import datetime

# ==============================================================================
# VERIFICAÇÃO DE BIBLIOTECAS
# ==============================================================================
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    import customtkinter as ctk
    import win32com.client
    import pythoncom
    import fitz  # PyMuPDF
    import pyautogui
    import pyperclip
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    ctypes.windll.user32.MessageBoxW(0, f"Erro: Uma biblioteca está faltando!\n\nDetalhe: {e}", "Erro Fatal de Inicialização", 0x10)
    sys.exit()

# Ajuste de DPI
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ==============================================================================
# BANCO DE DADOS E DIRETÓRIOS BASE
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
ARQUIVO_STATS = os.path.join(BASE_DIR, "estatisticas_tmg.json")
ARQUIVO_CONFIG = os.path.join(BASE_DIR, "configuracoes.json")

CONFIG_PADRAO = {
    "caminho_raiz": r"\\tmg\intranet\Acabamentos\Manutencao\02_Técnicos\02_Equipamentos_Infraestruturas\Caldeiras\CLD-0008 - Caldeira de Vapor 8\Materia Prima\Deolinda\Guias",
    "usuarios": {
        "Bruno Silva": "8397",
        "Alexandre Pimenta": "8646",
        "João Faria": "7994"
    },
    "texto_filtro": "Ano 2026+",
    "cor_terminal": "#00FF00"
}

def carregar_configuracoes():
    if not os.path.exists(ARQUIVO_CONFIG):
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(CONFIG_PADRAO, f, indent=4, ensure_ascii=False)
        return CONFIG_PADRAO
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            config_atual = json.load(f)
            if "texto_filtro" not in config_atual: config_atual["texto_filtro"] = "Ano 2026+"
            if "cor_terminal" not in config_atual: config_atual["cor_terminal"] = "#00FF00"
            return config_atual
    except Exception:
        return CONFIG_PADRAO

CONFIG = carregar_configuracoes()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
pyautogui.FAILSAFE = True

MESES_EXTENSO = {
    1: "01-Janeiro", 2: "02-Fevereiro", 3: "03-Março", 4: "04-Abril",
    5: "05-Maio", 6: "06-Junho", 7: "07-Julho", 8: "08-Agosto",
    9: "09-Setembro", 10: "10-Outubro", 11: "11-Novembro", 12: "12-Dezembro"
}

# ==============================================================================
# WIDGET ESTILO ZSQL02 (CARD DE MÁQUINA PISCANDO)
# ==============================================================================
class CardMaquinaZSQL(ctk.CTkFrame):
    def __init__(self, master, nome_maquina, data_hora, status_texto,
                 cor_header="#008000", cor_corpo="#E6F4FA", piscar=True,
                 cor_pisca_borda="#FFD700", cor_pisca_header="#FFA500", **kwargs):
        super().__init__(
            master,
            fg_color=cor_corpo,
            corner_radius=2,
            border_width=2,
            border_color="#888888",
            **kwargs
        )
        self.piscar = piscar
        self.cor_normal_borda = "#888888"
        self.cor_pisca_borda = cor_pisca_borda
        self.cor_header_normal = cor_header
        self.cor_header_pisca = cor_pisca_header
        self._estado_pisca = False
        self._after_id = None

        self.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(self, fg_color=cor_header, corner_radius=0, height=24)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)

        self.lbl_nome = ctk.CTkLabel(
            self.header,
            text=nome_maquina,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.lbl_nome.pack(expand=True)

        self.lbl_data = ctk.CTkLabel(
            self,
            text=data_hora,
            text_color="#1A2B5C",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        )
        self.lbl_data.pack(pady=(4, 0), padx=6)

        self.lbl_status = ctk.CTkLabel(
            self,
            text=status_texto,
            text_color="#1A2B5C",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        )
        self.lbl_status.pack(pady=(0, 5), padx=6)

        if self.piscar:
            self._ciclo_piscar()

    def atualizar_dados(self, nome_maquina=None, data_hora=None, status_texto=None, cor_header=None):
        if nome_maquina is not None:
            self.lbl_nome.configure(text=nome_maquina)
        if data_hora is not None:
            self.lbl_data.configure(text=data_hora)
        if status_texto is not None:
            self.lbl_status.configure(text=status_texto)
        if cor_header is not None:
            self.cor_header_normal = cor_header
            if not self._estado_pisca:
                self.header.configure(fg_color=cor_header)

    def _ciclo_piscar(self):
        if not self.winfo_exists() or not self.piscar:
            return

        self._estado_pisca = not self._estado_pisca
        if self._estado_pisca:
            self.configure(border_color=self.cor_pisca_borda, border_width=3)
            self.header.configure(fg_color=self.cor_header_pisca)
        else:
            self.configure(border_color=self.cor_normal_borda, border_width=2)
            self.header.configure(fg_color=self.cor_header_normal)

        self._after_id = self.after(450, self._ciclo_piscar)

    def set_piscar(self, ativo: bool):
        self.piscar = ativo
        if not ativo:
            if self._after_id:
                self.after_cancel(self._after_id)
                self._after_id = None
            self._estado_pisca = False
            self.configure(border_color=self.cor_normal_borda, border_width=2)
            self.header.configure(fg_color=self.cor_header_normal)
        else:
            if not self._after_id:
                self._ciclo_piscar()

# ==============================================================================
# TELA DE LOGIN
# ==============================================================================
class LoginScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TMG OS - Autenticação")
        
        largura_janela = 450
        altura_janela = 550
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = (largura_tela // 2) - (largura_janela // 2)
        pos_y = (altura_tela // 2) - (altura_janela // 2)
        self.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")
        
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.login_frame = ctk.CTkFrame(self, width=350, height=450, corner_radius=15)
        self.login_frame.grid(row=0, column=0, padx=20, pady=20)
        self.login_frame.grid_propagate(False)
        self.login_frame.grid_columnconfigure(0, weight=1)

        self.label_welcome = ctk.CTkLabel(self.login_frame, text="TMG OS", font=ctk.CTkFont(size=32, weight="bold"))
        self.label_welcome.grid(row=0, column=0, pady=(50, 5))

        self.label_sub = ctk.CTkLabel(self.login_frame, text="Faça login para continuar", font=ctk.CTkFont(size=12), text_color="gray")
        self.label_sub.grid(row=1, column=0, pady=(0, 40))

        self.entry_user = ctk.CTkEntry(self.login_frame, width=280, height=45, placeholder_text="Nome de Usuário")
        self.entry_user.grid(row=2, column=0, pady=(0, 15))

        self.entry_pass = ctk.CTkEntry(self.login_frame, width=280, height=45, placeholder_text="Senha", show="*")
        self.entry_pass.grid(row=3, column=0, pady=(0, 40))

        self.btn_login = ctk.CTkButton(self.login_frame, text="ENTRAR", command=self.validar_login, 
                                       width=280, height=45, font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_login.grid(row=4, column=0, pady=(0, 20))
        
        self.bind('<Return>', lambda event: self.validar_login())

    def validar_login(self):
        usuario_digitado = self.entry_user.get().strip().lower()
        senha_digitada = self.entry_pass.get().strip()
        usuario_autenticado = None

        for user_db, pass_db in CONFIG["usuarios"].items():
            if user_db.lower() == usuario_digitado and pass_db == senha_digitada:
                usuario_autenticado = user_db
                break
        
        if usuario_autenticado:
            self.destroy()
            app = AppDashboard(usuario_logado=usuario_autenticado)
            app.mainloop()
        else:
            messagebox.showerror("Erro de Acesso", "Usuário ou senha incorretos.\nTente novamente.")

# ==============================================================================
# TELA PRINCIPAL (DASHBOARD)
# ==============================================================================
class AppDashboard(ctk.CTk):
    def __init__(self, usuario_logado):
        super().__init__()
        self.title("TMG OS - Automação Deolinda")
        self.usuario_logado = usuario_logado
        self.cancelar_lancamento = False 
        
        self.guias_baixadas, self.ultima_guia = self.carregar_estatisticas()

        self.mapa_cores = {
            "Verde Hacker (Padrão)": "#00FF00",
            "Azul Ciano": "#00FFFF",
            "Azul Guias": "#3498db",
            "Branco Gelo": "#FFFFFF",
            "Amarelo Alerta": "#F1C40F",
            "Laranja Metálico": "#E67E22",
            "Rosa Cyberpunk": "#FF00FF",
            "Vermelho Erro": "#FF4444"
        }

        largura_janela = 920
        altura_janela = 780
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = (largura_tela // 2) - (largura_janela // 2)
        pos_y = (altura_tela // 2) - (altura_janela // 2)
        self.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")
        self.minsize(820, 650)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.criar_sidebar()
        self.criar_conteudo_principal()

    def carregar_estatisticas(self):
        try:
            if os.path.exists(ARQUIVO_STATS):
                with open(ARQUIVO_STATS, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    ultima = dados.get("ultima_guia", "Nenhuma")
                    data_salva = dados.get("data_atual", "")
                    hoje = str(datetime.now().date())
                    if data_salva == hoje:
                        guias = dados.get("guias_baixadas", 0)
                    else:
                        guias = 0 
                    return guias, ultima
        except Exception:
            pass
        return 0, "Nenhuma"

    def salvar_estatisticas(self):
        try:
            dados = {
                "data_atual": str(datetime.now().date()),
                "guias_baixadas": self.guias_baixadas,
                "ultima_guia": self.ultima_guia
            }
            with open(ARQUIVO_STATS, "w", encoding="utf-8") as f:
                json.dump(dados, f)
        except Exception as e:
            self.log(f"Aviso: Não foi possível salvar estatísticas ({e})")

    def criar_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) 

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="TMG OS", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10))

        if self.usuario_logado == "João Faria":
            texto_cargo = f"Responsável CLD:\n{self.usuario_logado}"
        else:
            texto_cargo = f"Técnico:\n{self.usuario_logado}"

        self.user_label = ctk.CTkLabel(self.sidebar_frame, text=texto_cargo, 
                                       font=ctk.CTkFont(size=14, weight="bold"), text_color="#1f538d")
        
        if self.usuario_logado == "Bruno Silva":
            self.user_label.grid(row=1, column=0, padx=20, pady=(0, 2))
            self.role_extra = ctk.CTkLabel(self.sidebar_frame, text="Programador / Automação", 
                                           font=ctk.CTkFont(size=11), text_color="#85929e")
            self.role_extra.grid(row=2, column=0, padx=20, pady=(0, 25))
        else:
            self.user_label.grid(row=1, column=0, padx=20, pady=(0, 30))

        texto_filtro_atual = CONFIG.get("texto_filtro", "Ano 2026+")
        self.info_label = ctk.CTkLabel(self.sidebar_frame, text=f"Filtro Ativo:\n{texto_filtro_atual}", font=ctk.CTkFont(size=12))
        self.info_label.grid(row=3, column=0, padx=20, pady=10)

        if self.usuario_logado == "Bruno Silva":
            self.btn_config = ctk.CTkButton(self.sidebar_frame, text="⚙️ Configurações", fg_color="#3b3b3b", hover_color="#555555",
                                            command=self.abrir_tela_configuracoes)
            self.btn_config.grid(row=4, column=0, padx=20, pady=(20, 0), sticky="s")

        self.btn_logout = ctk.CTkButton(self.sidebar_frame, text="Sair", fg_color="transparent", 
                                        border_width=1, text_color=("gray10", "#DCE4EE"), 
                                        command=self.logout)
        self.btn_logout.grid(row=6, column=0, padx=20, pady=20, sticky="s")

    def criar_conteudo_principal(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(6, weight=1) 

        self.header_label = ctk.CTkLabel(self.main_frame, text="DEOLINDA AUTOMATION GUIAS", font=ctk.CTkFont(size=24, weight="bold"))
        self.header_label.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Central de Comando: Caldeira Biomassa (estilo zsql02)
        self.central_frame = ctk.CTkFrame(self.main_frame, corner_radius=8, fg_color="#1e1e1e", border_width=1, border_color="#333333")
        self.central_frame.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self.central_frame.grid_columnconfigure(1, weight=1)

        self.lbl_central_titulo = ctk.CTkLabel(
            self.central_frame,
            text="Central de Comando: Caldeira Biomassa",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#DCE4EE"
        )
        self.lbl_central_titulo.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))

        agora_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.card_caldeira = CardMaquinaZSQL(
            self.central_frame,
            nome_maquina="CALDEIRA BIOMASSA",
            data_hora=agora_str,
            status_texto="EM OPERAÇÃO",
            cor_header="#008000",
            cor_corpo="#E6F4FA",
            piscar=True,
            cor_pisca_borda="#FFD700",
            cor_pisca_header="#FFA500",
            width=165
        )
        self.card_caldeira.grid(row=1, column=0, padx=(12, 10), pady=(2, 10), sticky="w")

        self.controles_caldeira_frame = ctk.CTkFrame(self.central_frame, fg_color="transparent")
        self.controles_caldeira_frame.grid(row=1, column=1, padx=(0, 12), pady=(2, 10), sticky="ew")

        self.btn_toggle_piscar = ctk.CTkButton(
            self.controles_caldeira_frame,
            text="Pausar / Retomar Piscar",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3b3b3b",
            hover_color="#1f538d",
            command=self.alternar_piscar_caldeira
        )
        self.btn_toggle_piscar.pack(side="left", padx=(0, 8))

        self.btn_atualizar_hora = ctk.CTkButton(
            self.controles_caldeira_frame,
            text="Atualizar Hora / Status",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3b3b3b",
            hover_color="#1f538d",
            command=self.atualizar_card_caldeira
        )
        self.btn_atualizar_hora.pack(side="left")

        self.stats_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.stats_frame.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        self.stats_frame.grid_columnconfigure((0, 1), weight=1)

        self.card1 = ctk.CTkFrame(self.stats_frame, corner_radius=8, fg_color="#1e1e1e", border_width=1, border_color="#333333")
        self.card1.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.lbl_card1_title = ctk.CTkLabel(self.card1, text="Guias Baixadas Hoje", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        self.lbl_card1_title.pack(pady=(15, 0))
        self.lbl_card1_valor = ctk.CTkLabel(self.card1, text=str(self.guias_baixadas), font=ctk.CTkFont(size=26, weight="bold"), text_color="#00FF00")
        self.lbl_card1_valor.pack(pady=(0, 15))

        self.card2 = ctk.CTkFrame(self.stats_frame, corner_radius=8, fg_color="#1e1e1e", border_width=1, border_color="#333333")
        self.card2.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        self.lbl_card2_title = ctk.CTkLabel(self.card2, text="Última Guia Lançada", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        self.lbl_card2_title.pack(pady=(15, 0))
        self.lbl_card2_valor = ctk.CTkLabel(self.card2, text=self.ultima_guia, font=ctk.CTkFont(size=26, weight="bold"), text_color="#3498db")
        self.lbl_card2_valor.pack(pady=(0, 15))

        self.actions_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.actions_frame.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        self.actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_cod1 = ctk.CTkButton(self.actions_frame, text="1. SACAR GUIAS", height=50, font=ctk.CTkFont(weight="bold"),
                                      fg_color="#3b3b3b", hover_color="#1f538d",
                                      command=lambda: self.iniciar_thread_com_barra(self.executar_codigo_1))
        self.btn_cod1.grid(row=0, column=0, padx=10, pady=15, sticky="ew")

        self.btn_cod2 = ctk.CTkButton(self.actions_frame, text="2. ORGANIZAR PASTA", height=50, font=ctk.CTkFont(weight="bold"),
                                      fg_color="#3b3b3b", hover_color="#1f538d",
                                      command=lambda: self.iniciar_thread_com_barra(self.executar_codigo_2))
        self.btn_cod2.grid(row=0, column=1, padx=10, pady=15, sticky="ew")

        self.btn_lanc = ctk.CTkButton(self.actions_frame, text="3. LANÇAR EM MWW", height=50, font=ctk.CTkFont(weight="bold"),
                                      fg_color="#3b3b3b", hover_color="#1f538d",
                                      command=lambda: self.iniciar_thread_com_barra(self.executar_lancamento_mwwin))
        self.btn_lanc.grid(row=0, column=2, padx=10, pady=15, sticky="ew")

        self.barra_progresso = ctk.CTkProgressBar(self.main_frame, mode="indeterminate", progress_color="#3498db", fg_color="#1e1e1e", height=4)
        self.barra_progresso.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.barra_progresso.set(0) 

        self.terminal_header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.terminal_header_frame.grid(row=5, column=0, sticky="ew", pady=(0, 5))
        self.terminal_header_frame.grid_columnconfigure(0, weight=1)

        self.log_label = ctk.CTkLabel(self.terminal_header_frame, text="Terminal de Execução", font=ctk.CTkFont(size=14, weight="bold"))
        self.log_label.grid(row=0, column=0, sticky="sw")

        self.btn_cancelar = ctk.CTkButton(self.terminal_header_frame, text="🛑 Cancelar Lançamento (F1)", width=120, height=24,
                                          font=ctk.CTkFont(size=11, weight="bold"), fg_color="transparent", text_color="gray", hover_color="#7a3030",
                                          state="disabled", command=self.acionar_cancelamento)
        self.btn_cancelar.grid(row=0, column=1, sticky="se")

        cor_term_atual = CONFIG.get("cor_terminal", "#00FF00")
        self.textbox = ctk.CTkTextbox(self.main_frame, font=("Consolas", 13), fg_color="#0d1117", 
                                      text_color=cor_term_atual, border_width=1, border_color="#34495e")
        self.textbox.grid(row=6, column=0, sticky="nsew")

    def alternar_piscar_caldeira(self):
        novo_estado = not self.card_caldeira.piscar
        self.card_caldeira.set_piscar(novo_estado)
        self.log(f"Piscar da Caldeira Biomassa {'ATIVADO' if novo_estado else 'PAUSADO'}.")

    def atualizar_card_caldeira(self):
        agora_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.card_caldeira.atualizar_dados(
            data_hora=agora_str,
            status_texto="EM OPERAÇÃO",
            cor_header="#008000"
        )
        self.log(f"Card da Caldeira Biomassa atualizado ({agora_str}).")

    def abrir_tela_configuracoes(self):
        janela_config = ctk.CTkToplevel(self)
        janela_config.title("Configurações do Sistema")
        janela_config.geometry("600x630")
        janela_config.attributes("-topmost", True)
        
        lbl_titulo = ctk.CTkLabel(janela_config, text="⚙️ Painel de Configurações", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(pady=(20, 15))

        lbl_caminho = ctk.CTkLabel(janela_config, text="Caminho Raiz das Pastas (Rede TMG):", font=ctk.CTkFont(weight="bold"))
        lbl_caminho.pack(anchor="w", padx=20)
        entry_caminho = ctk.CTkEntry(janela_config, width=560)
        entry_caminho.insert(0, CONFIG["caminho_raiz"])
        entry_caminho.pack(padx=20, pady=(0, 15))

        lbl_users = ctk.CTkLabel(janela_config, text="Usuários Permitidos (Formato -> Nome:Senha | Um por linha):", font=ctk.CTkFont(weight="bold"))
        lbl_users.pack(anchor="w", padx=20)
        txt_usuarios = ctk.CTkTextbox(janela_config, width=560, height=130)
        txt_usuarios.pack(padx=20, pady=(0, 15))
        
        texto_users = ""
        for user, senha in CONFIG["usuarios"].items():
            texto_users += f"{user}:{senha}\n"
        txt_usuarios.insert("0.0", texto_users.strip())

        lbl_filtro = ctk.CTkLabel(janela_config, text="Texto Exibido no Filtro Ativo:", font=ctk.CTkFont(weight="bold"))
        lbl_filtro.pack(anchor="w", padx=20)
        entry_filtro = ctk.CTkEntry(janela_config, width=560)
        entry_filtro.insert(0, CONFIG.get("texto_filtro", "Ano 2026+"))
        entry_filtro.pack(padx=20, pady=(0, 15))

        lbl_cor = ctk.CTkLabel(janela_config, text="Cor da Fonte do Terminal:", font=ctk.CTkFont(weight="bold"))
        lbl_cor.pack(anchor="w", padx=20)
        
        cor_atual_hex = CONFIG.get("cor_terminal", "#00FF00")
        nome_cor_atual = "Verde Hacker (Padrão)"
        for nome_cor, valor_hex in self.mapa_cores.items():
            if valor_hex.upper() == cor_atual_hex.upper():
                nome_cor_atual = nome_cor
                break

        combo_cor = ctk.CTkOptionMenu(janela_config, values=list(self.mapa_cores.keys()), width=560, fg_color="#3b3b3b", button_color="#1f538d")
        combo_cor.set(nome_cor_atual)
        combo_cor.pack(padx=20, pady=(0, 20))

        btn_salvar = ctk.CTkButton(janela_config, text="💾 SALVAR ALTERAÇÕES", fg_color="#27ae60", hover_color="#2ecc71", 
                                   command=lambda: self.salvar_novas_configuracoes(
                                       janela_config, entry_caminho.get(), txt_usuarios.get("0.0", "end"),
                                       entry_filtro.get(), self.mapa_cores[combo_cor.get()] 
                                   ))
        btn_salvar.pack(pady=10)

    def salvar_novas_configuracoes(self, janela, novo_caminho, texto_usuarios, novo_filtro, nova_cor_hex):
        novos_usuarios = {}
        linhas = texto_usuarios.strip().split('\n')
        for linha in linhas:
            if ":" in linha:
                nome, senha = linha.split(":", 1)
                novos_usuarios[nome.strip()] = senha.strip()
                
        if not novos_usuarios:
            messagebox.showerror("Erro", "Você precisa de pelo menos 1 usuário cadastrado no formato Nome:Senha!")
            return
            
        CONFIG["caminho_raiz"] = novo_caminho.strip()
        CONFIG["usuarios"] = novos_usuarios
        CONFIG["texto_filtro"] = novo_filtro.strip()
        CONFIG["cor_terminal"] = nova_cor_hex
        
        try:
            with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(CONFIG, f, indent=4, ensure_ascii=False)
            
            self.info_label.configure(text=f"Filtro Ativo:\n{novo_filtro.strip()}")
            self.textbox.configure(text_color=nova_cor_hex)
            self.mostrar_sucesso_customizado("Configurações atualizadas com sucesso!")
            janela.destroy()
        except Exception as e:
            self.log(f"Erro ao salvar configurações: {e}")

    def logout(self):
        self.destroy()
        LoginScreen().mainloop()

    def log(self, texto):
        agora = datetime.now().strftime('%H:%M:%S')
        self.textbox.insert("end", f"[{agora}] > {texto}\n")
        self.textbox.see("end")
        self.update()

    # ==========================================================================
    # SISTEMA DE INTERRUPÇÃO E CLIQUES 
    # ==========================================================================
    def acionar_cancelamento(self, event=None):
        self.cancelar_lancamento = True

    def checar_interrupcao(self):
        if ctypes.windll.user32.GetAsyncKeyState(0x70) != 0:
            self.cancelar_lancamento = True
            
        if self.cancelar_lancamento:
            raise Exception("Operação CANCELADA PELO USUÁRIO!")

    def esperar(self, segundos):
        passos = int(segundos / 0.1)
        for _ in range(passos):
            self.checar_interrupcao()
            time.sleep(0.1)
        resto = segundos % 0.1
        if resto > 0:
            time.sleep(resto)

    def digitar_agil(self, texto):
        self.checar_interrupcao()
        pyautogui.write(texto, interval=0.01)

    def clique_inteligente(self, nome_imagem, tempo_espera=10, clicks=1):
        caminho_imagem = os.path.join(BASE_DIR, nome_imagem)
        self.log(f"Procurando por: {nome_imagem}...")
        
        inicio = time.time()
        while time.time() - inicio < tempo_espera:
            self.checar_interrupcao()
            try:
                posicao = pyautogui.locateCenterOnScreen(caminho_imagem, confidence=0.7, grayscale=True)
                if posicao:
                    pyautogui.moveTo(posicao, duration=0.2)
                    pyautogui.click(clicks=clicks)
                    return True
            except:
                pass
            self.esperar(0.5) 
            
        self.log(f"⚠️ AVISO: A imagem {nome_imagem} não apareceu após {tempo_espera}s.")
        return False

    def clique_proximo_a(self, img_ref, img_alvo, tempo_espera=10, clicks=1):
        caminho_ref = os.path.join(BASE_DIR, img_ref)
        caminho_alvo = os.path.join(BASE_DIR, img_alvo)
        self.log(f"Procurando {img_alvo} próximo a {img_ref}...")
        
        inicio = time.time()
        while time.time() - inicio < tempo_espera:
            self.checar_interrupcao()
            try:
                pos_ref = pyautogui.locateCenterOnScreen(caminho_ref, confidence=0.7, grayscale=True)
                
                if pos_ref:
                    alvos = list(pyautogui.locateAllOnScreen(caminho_alvo, confidence=0.7, grayscale=True))
                    if alvos:
                        alvo_mais_proximo = None
                        menor_distancia = float('inf')
                        
                        for alvo in alvos:
                            centro_alvo = pyautogui.center(alvo)
                            distancia = math.hypot(centro_alvo.x - pos_ref.x, centro_alvo.y - pos_ref.y)
                            
                            if distancia < menor_distancia:
                                menor_distancia = distancia
                                alvo_mais_proximo = centro_alvo
                        
                        if alvo_mais_proximo:
                            pyautogui.moveTo(alvo_mais_proximo.x, alvo_mais_proximo.y, duration=0.2)
                            pyautogui.click(clicks=clicks)
                            return True
            except:
                pass
            self.esperar(0.5) 
            
        self.log(f"⚠️ AVISO: Não encontrou {img_alvo} perto de {img_ref}.")
        return False

    def iniciar_thread_com_barra(self, funcao):
        self.barra_progresso.start()
        threading.Thread(target=self.rodar_e_parar_barra, args=(funcao,), daemon=True).start()

    def rodar_e_parar_barra(self, funcao):
        try:
            funcao()
        finally:
            self.barra_progresso.stop()

    def mostrar_sucesso_customizado(self, mensagem):
        janela = ctk.CTkToplevel(self)
        janela.title("Sucesso")
        l_janela, a_janela = 500, 200
        l_tela = self.winfo_screenwidth()
        a_tela = self.winfo_screenheight()
        janela.geometry(f"{l_janela}x{a_janela}+{(l_tela//2)-(l_janela//2)}+{(a_tela//2)-(a_janela//2)}")
        janela.attributes("-topmost", True)
        
        lbl_msg = ctk.CTkLabel(janela, text=mensagem, font=ctk.CTkFont(size=16, weight="bold"))
        lbl_msg.pack(expand=True, pady=(20, 10))
        btn = ctk.CTkButton(janela, text="OK", command=janela.destroy, width=120)
        btn.pack(pady=10)

    # ==========================================================================
    # CÓDIGOS DE AUTOMAÇÃO
    # ==========================================================================
    def executar_codigo_1(self):
        self.log(f"INICIANDO SINCRONIZAÇÃO ({CONFIG.get('texto_filtro', 'Ano 2026+').upper()})")
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            inbox = outlook.GetDefaultFolder(6)
            messages = inbox.Items
            messages.Sort("[ReceivedTime]", True)
            data_limite = datetime(2026, 1, 1).date()
            baixados = 0
            
            for message in messages:
                try:
                    data_email = message.ReceivedTime.date()
                    if data_email < data_limite: break
                    sender = message.SenderEmailAddress.lower()
                    if "moloni" in sender or "faturas" in sender:
                        ano = str(data_email.year)
                        mes = MESES_EXTENSO[data_email.month]
                        match = re.search(r'\d{4}A[/-](\d+)', message.Subject)
                        id_numero = match.group(1) if match else None
                        
                        if id_numero:
                            pasta_final = os.path.join(CONFIG["caminho_raiz"], ano, mes)
                            if not os.path.exists(pasta_final): os.makedirs(pasta_final)
                            ja_existe = any(f"A{id_numero}" in f for f in os.listdir(pasta_final))
                            
                            if not ja_existe:
                                self.log(f"BAIXANDO: Guia {id_numero}")
                                html = message.HTMLBody.replace("=\r\n", "").replace("=3D", "=")
                                links = re.findall(r'https?://www\.moloni\.pt/downloads/\?h=[^\s\'">]+', html)
                                if links and self.baixar_chrome(links[0].split('"')[0], pasta_final):
                                    baixados += 1
                                    
                                    self.guias_baixadas += 1
                                    self.lbl_card1_valor.configure(text=str(self.guias_baixadas))
                                    self.salvar_estatisticas()

                except: 
                    continue
            self.log(f"FIM DA SINCRONIZAÇÃO: {baixados} guia(s) baixada(s).")
        finally: 
            pythoncom.CoUninitialize()

    def baixar_chrome(self, url, destino):
        try:
            options = webdriver.ChromeOptions()
            options.add_experimental_option("prefs", {"download.default_directory": destino})
            options.add_argument("--headless")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get(url)
            botao = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Descarregar')]")))
            driver.execute_script("arguments[0].click();", botao)
            self.esperar(8)
            driver.quit()
            return True
        except: 
            return False

    def executar_codigo_2(self):
        self.log("INICIANDO RENOMEAÇÃO DE ARQUIVOS...")
        pasta = filedialog.askdirectory(title="Selecione a pasta para organizar")
        if not pasta: 
            self.log("Operação cancelada pelo usuário.")
            return
            
        arquivos = glob.glob(os.path.join(pasta, "*.pdf"))
        
        for arq_path in arquivos:
            try:
                doc = fitz.open(arq_path)
                texto = " ".join([p.get_text() for p in doc])
                doc.close()
                
                m_data = re.search(r"Data de Emiss.*?(\d{2})[/-]\d{2}[/-]\d{4}", texto, re.IGNORECASE)
                m_guia = re.search(r"(\d{4}A)[/-](\d+)", texto)
                abrev = "Estil" if "Estilha" in texto.title() else "Biom" if "Biomassa" in texto.title() else ""
                
                if m_data and m_guia:
                    novo_nome = f"{m_data.group(1)}_{m_guia.group(1)}{m_guia.group(2)}_{abrev}.pdf".replace("_.pdf", ".pdf")
                    novo_path = os.path.join(pasta, novo_nome) 
                    
                    if arq_path != novo_path: 
                        os.rename(arq_path, novo_path)
                        self.log(f"OK: Arquivo renomeado para {novo_nome}")
            except: 
                continue
        self.log("RENOMEAÇÃO CONCLUÍDA.")

    def executar_lancamento_mwwin(self):
        self.log("AGUARDANDO SELEÇÃO DO PDF...")
        caminho_pdf = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")], title="Selecione a Guia para lançar")
        if not caminho_pdf: 
            self.log("Seleção cancelada.")
            return
            
        nome_arquivo = os.path.basename(caminho_pdf)
        try:
            doc = fitz.open(caminho_pdf)
            texto_pdf = " ".join([p.get_text() for p in doc])
            doc.close()
            
            m_guia = re.search(r'GT\s*(\d{4}A/\d+)', texto_pdf)
            guia_pura = m_guia.group(1) if m_guia else "0000"
            m_data = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', texto_pdf)
            data_limpa = f"{m_data.group(1)}{m_data.group(2)}{m_data.group(3)}" if m_data else ""
            m_hora = re.search(r'(\d{2}):(\d{2})', texto_pdf)
            hora_limpa = f"{m_hora.group(1)}{m_hora.group(2)}" if m_hora else ""
            m_qtd = re.search(r'(\d+)\s*m3', texto_pdf, re.IGNORECASE)
            qtd = m_qtd.group(1) if m_qtd else "0"
            m_sure = re.search(r'(SURE-EU/ES-[^\s\n]+)', texto_pdf)
            codigo_sure = m_sure.group(1) if m_sure else ""
            
            is_estilha = "ESTILHA" in texto_pdf.upper()
            cod_comb = "L.CS.010.002" if is_estilha else "L.CS.010.003"
            desc_mat = "ESTILHA" if is_estilha else "BIOMASSA"
            
            self.log(f"Iniciando Guia: {guia_pura}")
            self.log("ATENÇÃO: Mantenha as mãos fora do mouse!")
            
            self.cancelar_lancamento = False
            self.btn_cancelar.configure(state="normal", fg_color="#7a3030", text_color="white")
            
            for i in range(8, 0, -1):
                self.log(f"O robô assume o controle em {i}...")
                self.esperar(1.0)
            
            # 1. PARTE INICIAL
            pyautogui.click() 
            self.digitar_agil("GR"); pyautogui.press('tab')
            self.digitar_agil(f"{guia_pura}_4770-219"); pyautogui.press('tab')
            self.digitar_agil(f"{desc_mat} {qtd} m3")
            
            # 2. FORNECEDOR
            pyautogui.press('tab'); pyautogui.press('enter'); self.esperar(1.2)
            self.digitar_agil("pt505257297"); pyautogui.press('enter'); self.esperar(1.0)
            
            self.checar_interrupcao()
            pyautogui.press('tab', presses=7, interval=0.05)

            # 3. CÓDIGO COMB., DATAS E QTD
            self.digitar_agil(cod_comb)
            pyautogui.press('tab', presses=3, interval=0.05)
            self.digitar_agil(data_limpa); pyautogui.press('tab'); self.digitar_agil(hora_limpa)
            pyautogui.press('tab'); self.digitar_agil("0"); pyautogui.press('tab'); self.digitar_agil(qtd)

            # 4. OBSERVAÇÕES E DOCUMENTOS COM NOMES LIMPOS
            if self.clique_inteligente("Observacoes.png"):
                self.esperar(0.3)
                pyautogui.press('tab')
                pyperclip.copy(f"Código SURE: {codigo_sure}")
                pyautogui.hotkey('ctrl', 'v')
                self.esperar(0.5)
            
            self.clique_inteligente("Documentos.png")
            self.esperar(0.5)
            
            self.clique_inteligente("botao+.png")
            self.esperar(0.5)
            
            self.clique_proximo_a("data de validade.png", "Seta da data.png", clicks=2)
            self.esperar(0.5)

            # 5. FINALIZAÇÃO DO PDF
            self.checar_interrupcao()
            pyautogui.press('tab', presses=2, interval=0.1)
            self.esperar(0.3)
            pyautogui.press('enter')
            self.esperar(1.5)
            self.digitar_agil(nome_arquivo)
            self.esperar(0.3)
            pyautogui.press('enter')
            self.esperar(0.5)
            pyautogui.press('tab')
            self.esperar(0.3)
            pyautogui.press('enter')
            self.esperar(1.0)
            
            self.ultima_guia = guia_pura
            self.lbl_card2_valor.configure(text=f"{self.ultima_guia}")
            self.salvar_estatisticas()

            self.log(f"Lançamento da guia {guia_pura} finalizado.")
            self.mostrar_sucesso_customizado(f"Guia nº {guia_pura} lançada com sucesso!\nResponsável: {self.usuario_logado}")
            
        except Exception as e:
            if str(e) == "Operação CANCELADA PELO USUÁRIO!":
                self.log(f"🛑 {e}")
            else:
                self.log(f"ERRO no Lançamento: {e}")
        finally:
            self.btn_cancelar.configure(state="disabled", fg_color="transparent", text_color="gray")

# ==============================================================================
# INICIALIZAÇÃO 
# ==============================================================================
if __name__ == "__main__":
    app_login = LoginScreen()
    app_login.mainloop()
