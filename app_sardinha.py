import customtkinter as ctk
import threading
import sys
import os
import re
from datetime import datetime
from PIL import Image
import motor_sardinha

# ==========================================
# --- CONFIGURAÇÃO VISUAL FUNDAMENTAL ---
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paleta de cores moderna (navy dark)
C = {
    "bg":           "#0D1117",
    "sidebar":      "#161C2B",
    "card":         "#1C2333",
    "card2":        "#212B40",
    "border":       "#2D3A52",
    "blue":         "#3B82F6",
    "blue_dk":      "#2563EB",
    "green":        "#10B981",
    "yellow":       "#F59E0B",
    "red":          "#EF4444",
    "purple":       "#A78BFA",
    "cyan":         "#22D3EE",
    "orange":       "#FB923C",
    "txt":          "#F1F5F9",
    "txt2":         "#94A3B8",
    "txt3":         "#475569",
}

# Regras de colorização para o log
LOG_COLOR_RULES = [
    (r"✅|OK!|SUCESSO|concluído|CUMPRIDA|FINALIZADO",             C["green"]),
    (r"❌|ERRO|Erro|erro|CRÍTICO|falha",                           C["red"]),
    (r"⚠️|WARN|INTERROMPIDO|corrupção",                           C["yellow"]),
    (r"\[SISTEMA\]|conectado|Inicia",                              C["blue"]),
    (r"🎬|Extraindo|inédito",                                      C["purple"]),
    (r"⬆️|🔄|Drive|Sincronizado|Atualizado|DRIVE",                C["cyan"]),
    (r"📡|Verificando|YouTube",                                    "#C084FC"),
    (r"🏆|MISSÃO|CONCLUÍDO|100%",                                  C["green"]),
    (r"📂|NOVO ARQUIVO|Cerebro",                                   C["orange"]),
    (r"📊|Relatório|auditoria|checkup",                            C["cyan"]),
    (r"🔐|CONECTANDO|GOOGLE",                                      C["blue"]),
    (r"={3,}|[-]{3,}",                                             C["border"]),
]


# ==========================================
# --- COMPONENTES ---
# ==========================================

class SmartLogViewer(ctk.CTkFrame):
    """Log viewer com timestamps e colorização automática por tipo de mensagem."""

    def __init__(self, master, on_success=None, on_new_file=None, **kwargs):
        super().__init__(master, fg_color=C["bg"], **kwargs)
        self.on_success = on_success
        self.on_new_file = on_new_file
        self._buffer = ""
        self._row = 0

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=C["bg"],
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["txt3"],
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(1, weight=1)

    def _color_for(self, text):
        for pattern, color in LOG_COLOR_RULES:
            if re.search(pattern, text):
                return color
        return C["txt2"]

    def append_text(self, text):
        self._buffer += text
        lines = self._buffer.split("\n")
        self._buffer = lines[-1]
        for line in lines[:-1]:
            stripped = line.strip()
            if stripped:
                self._add_entry(stripped)

    def _add_entry(self, line):
        color = self._color_for(line)
        ts = datetime.now().strftime("%H:%M:%S")

        # Callbacks para estatísticas
        if self.on_success and re.search(r"✅|OK!", line):
            self.after(0, self.on_success)
        if self.on_new_file and re.search(r"📂|NOVO ARQUIVO", line):
            self.after(0, self.on_new_file)

        row_bg = C["card"] if self._row % 2 == 0 else "transparent"

        frame = ctk.CTkFrame(self._scroll, fg_color=row_bg, corner_radius=4)
        frame.grid(row=self._row, column=0, columnspan=2, sticky="ew", pady=1, padx=2)
        frame.grid_columnconfigure(1, weight=1)

        # Timestamp
        ctk.CTkLabel(
            frame, text=ts,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=C["txt3"], width=65, anchor="w"
        ).grid(row=0, column=0, padx=(10, 6), pady=3, sticky="w")

        # Mensagem
        ctk.CTkLabel(
            frame, text=line,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=color, anchor="w", justify="left",
            wraplength=680
        ).grid(row=0, column=1, pady=3, padx=(0, 10), sticky="ew")

        self._row += 1
        self.after(20, lambda: self._scroll._parent_canvas.yview_moveto(1.0))

    def clear(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._row = 0
        self._buffer = ""


class SmartPrintRedirector:
    def __init__(self, viewer: SmartLogViewer):
        self.viewer = viewer

    def write(self, text):
        if text:
            self.viewer.after(0, self.viewer.append_text, text)

    def flush(self):
        pass


class StatCard(ctk.CTkFrame):
    """Card compacto de estatística para a sidebar."""

    def __init__(self, master, icon, label, value="0", accent=C["blue"], **kwargs):
        super().__init__(master, fg_color=C["card"], corner_radius=10, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text=icon,
            font=ctk.CTkFont(size=22), width=36,
            text_color=accent
        ).grid(row=0, column=0, rowspan=2, padx=(14, 6), pady=12)

        ctk.CTkLabel(
            self, text=label,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C["txt3"]
        ).grid(row=0, column=1, sticky="sw", padx=(0, 12), pady=(10, 0))

        self._val_lbl = ctk.CTkLabel(
            self, text=value,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=C["txt"]
        )
        self._val_lbl.grid(row=1, column=1, sticky="nw", padx=(0, 12), pady=(0, 10))

    def set_value(self, v):
        self._val_lbl.configure(text=str(v))


class AccordionItem(ctk.CTkFrame):
    def __init__(self, master, title, body):
        super().__init__(master, fg_color=C["card"], corner_radius=10)
        self.grid_columnconfigure(0, weight=1)
        self._open = False
        self._title = title

        self._btn = ctk.CTkButton(
            self, text=f"  ▶   {title}", anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="transparent", hover_color=C["card2"],
            text_color=C["txt"], command=self._toggle
        )
        self._btn.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        self._body_frame = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=8)
        ctk.CTkLabel(
            self._body_frame, text=body,
            font=ctk.CTkFont(size=12), text_color=C["txt2"],
            justify="left", wraplength=720, anchor="w"
        ).pack(padx=16, pady=14, fill="x")

    def _toggle(self):
        if self._open:
            self._body_frame.grid_forget()
            self._btn.configure(text=f"  ▶   {self._title}")
        else:
            self._body_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
            self._btn.configure(text=f"  ▼   {self._title}")
        self._open = not self._open


# ==========================================
# --- APLICAÇÃO PRINCIPAL ---
# ==========================================

class SardinhaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SardinhIA - Base de Conhecimento AUVP")
        self.geometry("1250x800")
        self.minsize(1050, 680)
        self.configure(fg_color=C["bg"])

        self.evento_pausa = threading.Event()
        self.evento_pausa.set()
        self.evento_cancelar = threading.Event()
        self._n_videos = 0
        self._n_arquivos = 0

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.auth_em_curso = False

        self._build_sidebar()
        self._build_main()

        sys.stdout = SmartPrintRedirector(self.log_viewer)
        sys.stderr = sys.stdout

        self.verificar_login()

        self.log_viewer.append_text("[SISTEMA] SardinhIA conectado e pronto.\n")
        self.log_viewer.append_text("[SISTEMA] Acesse a aba 'Guia & FAQ' para instruções detalhadas.\n")

    # ==========================================
    # --- BUILD SIDEBAR ---
    # ==========================================
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color=C["sidebar"])
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)

        # Logo
        try:
            p = os.path.join(os.path.dirname(__file__), "logo.png")
            img = ctk.CTkImage(Image.open(p), Image.open(p), size=(130, 130))
            ctk.CTkLabel(sb, image=img, text="").grid(row=0, column=0, pady=(28, 6))
        except Exception:
            ctk.CTkLabel(
                sb, text="🦈 SardinhIA",
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=C["blue"]
            ).grid(row=0, column=0, pady=(28, 6))

        ctk.CTkLabel(sb, text="AUVP Sync", font=ctk.CTkFont(size=17, weight="bold"), text_color=C["txt"]).grid(row=1, column=0)
        ctk.CTkLabel(sb, text="Motor de Extração I.A.", font=ctk.CTkFont(size=12), text_color=C["txt2"]).grid(row=2, column=0, pady=(2, 20))

        # Divider
        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))

        # Stat Cards
        self._card_videos = StatCard(sb, "🎬", "VÍDEOS PROCESSADOS", accent=C["purple"])
        self._card_videos.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 10))

        self._card_files = StatCard(sb, "📁", "ARQUIVOS GERADOS", accent=C["cyan"])
        self._card_files.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 20))

        # Divider
        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 18))

        # Botões
        self.btn_auth = ctk.CTkButton(
            sb, text="🔑  AUTENTICAR DRIVE",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["cyan"], hover_color="#0891B2",
            height=46, corner_radius=10,
            command=self.autenticar_drive
        )
        self.btn_auth.grid(row=7, column=0, padx=18, pady=(0, 10), sticky="ew")

        self.btn_start = ctk.CTkButton(
            sb, text="⚡  LIGAR MOTOR",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["blue"], hover_color=C["blue_dk"],
            height=46, corner_radius=10,
            command=self.iniciar_extracao
        )
        self.btn_start.grid(row=8, column=0, padx=18, pady=(0, 10), sticky="ew")

        self.btn_pause = ctk.CTkButton(
            sb, text="⏸  PAUSAR",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#7C3E00", hover_color="#5C2D00",
            height=40, corner_radius=10,
            command=self.pausar_extracao, state="disabled"
        )
        self.btn_pause.grid(row=9, column=0, padx=18, pady=(0, 8), sticky="ew")

        self.btn_cancel = ctk.CTkButton(
            sb, text="⏹  CANCELAR",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#7F1D1D", hover_color="#991B1B",
            height=40, corner_radius=10,
            command=self.cancelar_extracao, state="disabled"
        )
        self.btn_cancel.grid(row=10, column=0, padx=18, pady=(0, 0), sticky="ew")

        # Spacer + versão
        sb.grid_rowconfigure(11, weight=1)
        ctk.CTkLabel(
            sb, text="SardinhIA  v1.0",
            font=ctk.CTkFont(size=10), text_color=C["txt3"]
        ).grid(row=12, column=0, pady=(0, 14))

    # ==========================================
    # --- BUILD MAIN ---
    # ==========================================
    def _build_main(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # --- STATUS CARD ---
        sc = ctk.CTkFrame(main, fg_color=C["card"], corner_radius=14)
        sc.grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 12))
        sc.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(sc, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 6))

        self._dot = ctk.CTkLabel(header, text="●", font=ctk.CTkFont(size=13), text_color=C["green"])
        self._dot.pack(side="left")

        self._status_title = ctk.CTkLabel(
            header, text="  Ocioso",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["txt"]
        )
        self._status_title.pack(side="left")

        self.btn_cancel_auth = ctk.CTkButton(
            header, text="CANCELAR",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#7F1D1D", hover_color="#991B1B",
            width=70, height=22, corner_radius=6,
            command=self.cancelar_login
        )
        # Inicialmente escondido
        self.btn_cancel_auth.pack_forget()

        self._status_desc = ctk.CTkLabel(
            sc, text="Pronto para iniciar. Leia o Guia & FAQ antes de ligar o motor.",
            font=ctk.CTkFont(size=13), text_color=C["txt2"]
        )
        self._status_desc.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 6))

        self._progress = ctk.CTkProgressBar(
            sc, height=5, corner_radius=4,
            progress_color=C["blue"], fg_color=C["border"]
        )
        self._progress.grid(row=2, column=0, sticky="ew", padx=22, pady=(4, 18))
        self._progress.set(0)

        # --- TABVIEW ---
        self.tabview = ctk.CTkTabview(
            main,
            fg_color=C["card"], corner_radius=14,
            segmented_button_fg_color=C["sidebar"],
            segmented_button_selected_color=C["blue"],
            segmented_button_selected_hover_color=C["blue_dk"],
            segmented_button_unselected_color=C["sidebar"],
            segmented_button_unselected_hover_color=C["card2"],
            text_color=C["txt"],
        )
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=22, pady=(0, 22))

        tab_log = self.tabview.add("  📋 Atividade  ")
        tab_faq = self.tabview.add("  🧠 Guia & FAQ  ")

        # Aba Atividade
        tab_log.grid_rowconfigure(0, weight=1)
        tab_log.grid_columnconfigure(0, weight=1)

        self.log_viewer = SmartLogViewer(
            tab_log,
            on_success=self._inc_videos,
            on_new_file=self._inc_files,
        )
        self.log_viewer.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Aba FAQ
        tab_faq.grid_rowconfigure(0, weight=1)
        tab_faq.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            tab_faq, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["txt3"]
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        FAQ = [
            ("Etapa 1 — Mapeamento Inteligente",
             "O motor SardinhIA varre o ecossistema do YouTube da AUVP (Vídeos, Shorts, Podcasts, Ao Vivo). "
             "Compara o que está online com o banco de dados local (CSV). Nunca baixa duplicatas, garantindo eficiência de tempo."),
            ("Etapa 2 — Download e Chunking Local",
             "Para cada vídeo inédito, baixa apenas a legenda VTT (sem MP4). O texto é limpo e particionado em arquivos "
             "de até 40.000 palavras localmente. Esse fluxo evita bloqueios do YouTube e prepara os chunks ideais para a IA."),
            ("Etapa 3 — Upload para o Google Drive",
             "Somente após todo o processamento local, o motor conecta ao Drive e faz o upload. "
             "Você sempre terá uma cópia local segura antes de qualquer envio para a nuvem."),
            ("Etapa 4 — Controle Total",
             "Pausar ou Cancelar a qualquer momento. No cancelamento, o sistema salva o progresso, finaliza o ciclo atual "
             "com segurança e sincroniza tudo com o Drive antes de encerrar."),
            ("FAQ — NotebookLM como primeiro laboratório",
             "Importe a pasta 'Cerebro_Docs' do Drive no NotebookLM. Ele cria um índice semântico com citações exatas "
             "da fonte original, opera exclusivamente na nossa base e garante zero alucinação."),
            ("FAQ — Próximos Passos (100% gratuito)",
             "A Fase 2 é um Agente RAG usando os arquivos locais gerados aqui. "
             "Utilizaremos a API gratuita do Google Gemini (Google AI Studio) — sem custo adicional de infraestrutura."),
            ("FAQ — Como o RAG protege a Verdade?",
             "No RAG, o LLM consulta nossa base antes de formular qualquer resposta, eliminando invenções financeiras. "
             "O SardinhIA garante que o 'combustível' (dados) seja sempre local, limpo e particionado corretamente."),
        ]

        for i, (t, b) in enumerate(FAQ):
            AccordionItem(scroll, t, b).grid(row=i, column=0, sticky="ew", padx=10, pady=6)

    # ==========================================
    # --- ESTATÍSTICAS (CALLBACKS) ---
    # ==========================================
    def _inc_videos(self):
        self._n_videos += 1
        self._card_videos.set_value(self._n_videos)

    def _inc_files(self):
        self._n_arquivos += 1
        self._card_files.set_value(self._n_arquivos)

    # ==========================================
    # --- AUTENTICAÇÃO ---
    # ==========================================
    def verificar_login(self):
        """Verifica se já existe o token de acesso."""
        if os.path.exists("token.json"):
            self._set_status("Ocioso", C["green"], "Pronto para iniciar. Tudo configurado.")
            self.btn_start.configure(state="normal")
            return True
        else:
            self._set_status("Aguardando Login", C["cyan"], "Credenciais ausentes. Autentique no Google Drive e tente novamente.")
            self.btn_start.configure(state="disabled")
            return False

    def autenticar_drive(self):
        if self.auth_em_curso: return
        self.auth_em_curso = True
        
        self.btn_auth.configure(state="disabled", text="CONECTANDO...")
        self.btn_cancel_auth.pack(side="left", padx=15)
        self._set_status("Autenticando...", C["cyan"], "Siga as instruções que abrirão no seu navegador.")

        def _thread_auth():
            try:
                motor_sardinha.get_drive_service()
                self.after(0, self._finalizar_auth, True)
            except Exception as e:
                print(f"Erro na autenticação: {e}")
                self.after(0, self._finalizar_auth, False)

        t = threading.Thread(target=_thread_auth, daemon=True)
        t.start()

    def cancelar_login(self):
        self.auth_em_curso = False
        self._finalizar_auth(False)
        self.log_viewer.append_text("⚠️ Autenticação interrompida pelo usuário.\n")

    def _finalizar_auth(self, sucesso):
        self.auth_em_curso = False
        self.btn_auth.configure(state="normal", text="🔑  AUTENTICAR DRIVE")
        self.btn_cancel_auth.pack_forget()
        self.verificar_login()
        if sucesso:
            self.log_viewer.append_text("✅ Drive autenticado com sucesso!\n")

    # ==========================================
    # --- CONTROLE DE EXECUÇÃO ---
    # ==========================================
    def iniciar_extracao(self):
        self.tabview.set("  📋 Atividade  ")
        self.log_viewer.clear()
        self._n_videos = 0
        self._n_arquivos = 0
        self._card_videos.set_value(0)
        self._card_files.set_value(0)

        self.evento_cancelar.clear()
        self.evento_pausa.set()

        self.btn_start.configure(state="disabled", text="⚙  RODANDO...", fg_color=C["border"], text_color=C["txt3"])
        self.btn_pause.configure(state="normal", text="⏸  PAUSAR", fg_color="#7C3E00")
        self.btn_cancel.configure(state="normal")

        self._set_status("Extraindo Dados", C["yellow"], "Motor em operação. Use Pausar ou Cancelar a qualquer momento.")
        self._progress.configure(progress_color=C["yellow"])
        self._progress.start()

        t = threading.Thread(target=self._rodar_motor, daemon=True)
        t.start()

    def pausar_extracao(self):
        if self.evento_pausa.is_set():
            self.evento_pausa.clear()
            self.btn_pause.configure(text="▶  RETOMAR", fg_color="#14532D", hover_color="#166534")
            self._set_status("Em Pausa", C["yellow"], "Motor pausado. Clique em Retomar para continuar.")
            self._progress.stop()
        else:
            self.evento_pausa.set()
            self.btn_pause.configure(text="⏸  PAUSAR", fg_color="#7C3E00", hover_color="#5C2D00")
            self._set_status("Extraindo Dados", C["yellow"], "Motor em operação. Use Pausar ou Cancelar a qualquer momento.")
            self._progress.start()

    def cancelar_extracao(self):
        self.evento_cancelar.set()
        self.evento_pausa.set()
        self.btn_pause.configure(state="disabled")
        self.btn_cancel.configure(state="disabled", text="CANCELANDO...")
        self._set_status("Cancelando...", C["red"], "Fechando ciclo atual e sincronizando. Aguarde.")

    def _rodar_motor(self):
        try:
            motor_sardinha.sardinha_engine_v47_rescue(
                evento_pausa=self.evento_pausa,
                evento_cancelar=self.evento_cancelar
            )
            if self.evento_cancelar.is_set():
                self.after(0, self._set_status, "Interrompido", C["yellow"],
                           "Extração cancelada. Todo o progresso foi salvo no Drive.")
            else:
                self.after(0, self._set_status, "Finalizado ✓", C["green"],
                           "Base de conhecimento atualizada com sucesso!")
                self.after(0, lambda: self._progress.set(1))
        except Exception as e:
            self.after(0, self._set_status, "Erro Crítico", C["red"], "Falha inesperada. Consulte o log.")
            self.log_viewer.after(0, self.log_viewer.append_text, f"\n❌ ERRO CRÍTICO: {e}\n")
        finally:
            self.after(0, self._progress.stop)
            self.after(0, self._reset_ui)

    def _reset_ui(self):
        self.btn_start.configure(state="normal", text="⚡  REINICIAR MOTOR",
                                  fg_color=C["blue"], text_color=C["txt"])
        self.btn_pause.configure(state="disabled", text="⏸  PAUSAR", fg_color="#7C3E00")
        self.btn_cancel.configure(state="disabled", text="⏹  CANCELAR")

    def _set_status(self, title, color, desc):
        self._dot.configure(text_color=color)
        self._status_title.configure(text=f"  {title}", text_color=color)
        self._status_desc.configure(text=desc)
        self._progress.configure(progress_color=color)


if __name__ == "__main__":
    app = SardinhaApp()
    app.mainloop()