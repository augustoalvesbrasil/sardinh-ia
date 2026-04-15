import customtkinter as ctk
import threading
import sys
import os
from PIL import Image
import motor_sardinha 

# ==========================================
# --- CONFIGURAÇÃO VISUAL FUNDAMENTAL ---
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PrintRedirector:
    """Interceta as saídas do terminal e redireciona para a UI."""
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, texto):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", texto)
        self.textbox.see("end") 
        self.textbox.configure(state="disabled")

    def flush(self):
        pass

class AccordionItem(ctk.CTkFrame):
    """Componente customizado para criar um efeito Accordion (Sanfona/Expansível)."""
    def __init__(self, master, title, content_text):
        super().__init__(master, fg_color="transparent")
        self.is_expanded = False
        self.title = title
        
        # Botão que atua como cabeçalho do Accordion
        self.btn_toggle = ctk.CTkButton(
            self, text=f"▶  {self.title}", anchor="w", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1E1E24", hover_color="#2A2A32",
            command=self.toggle
        )
        self.btn_toggle.pack(fill="x", pady=(5, 0))
        
        # Frame de conteúdo que será ocultado/exibido
        self.content_frame = ctk.CTkFrame(self, fg_color="#111115", corner_radius=0)
        self.lbl_content = ctk.CTkLabel(
            self.content_frame, text=content_text, 
            font=ctk.CTkFont(size=13), text_color="#CCCCCC", 
            justify="left", wraplength=750
        )
        self.lbl_content.pack(padx=15, pady=15, fill="x", anchor="w")

    def toggle(self):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.btn_toggle.configure(text=f"▶  {self.title}")
            self.is_expanded = False
        else:
            self.content_frame.pack(fill="x")
            self.btn_toggle.configure(text=f"▼  {self.title}")
            self.is_expanded = True


class SardinhaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- CONFIGURAÇÕES DA JANELA ---
        self.title("$ardinh'IA - Base de Conhecimento AUVP")
        self.geometry("1150x750") 
        self.minsize(1000, 650)   

        self.evento_pausa = threading.Event()
        self.evento_pausa.set() 
        self.evento_cancelar = threading.Event()

        # Layout Principal
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Content

        # ==========================================
        # --- SIDEBAR (IDENTIDADE E COMANDOS) ---
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#111111")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1) 

        # 1. LOGO RESTAURADA
        try:
            caminho_logo = os.path.join(os.path.dirname(__file__), "logo.png")
            imagem_logo = ctk.CTkImage(light_image=Image.open(caminho_logo), dark_image=Image.open(caminho_logo), size=(180, 180))
            self.lbl_logo = ctk.CTkLabel(self.sidebar_frame, image=imagem_logo, text="")
            self.lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 10))
        except Exception:
            self.lbl_logo = ctk.CTkLabel(self.sidebar_frame, text="🦈 $ardinh'IA", font=ctk.CTkFont(size=28, weight="bold"), text_color="#00FF9D")
            self.lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 10))

        # 2. TEXTOS
        self.lbl_title = ctk.CTkLabel(self.sidebar_frame, text="AUVP Sync", font=ctk.CTkFont(size=22, weight="bold"))
        self.lbl_title.grid(row=1, column=0, padx=20, pady=(0, 5))

        self.lbl_subtitle = ctk.CTkLabel(self.sidebar_frame, text="Motor de Extração I.A.", font=ctk.CTkFont(size=13), text_color="#aaaaaa")
        self.lbl_subtitle.grid(row=2, column=0, padx=20, pady=(0, 30))

        # 3. BOTÕES
        self.btn_start = ctk.CTkButton(
            self.sidebar_frame, text="⚡ LIGAR MOTOR", font=ctk.CTkFont(size=14, weight="bold"), 
            fg_color="#0056D2", hover_color="#003D96", height=45, 
            command=self.iniciar_extracao
        )
        self.btn_start.grid(row=3, column=0, padx=30, pady=(10, 10), sticky="ew")

        self.btn_pause = ctk.CTkButton(
            self.sidebar_frame, text="⏸️ PAUSAR", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#D35400", hover_color="#A04000", height=40,
            command=self.pausar_extracao, state="disabled"
        )
        self.btn_pause.grid(row=4, column=0, padx=30, pady=(0, 10), sticky="ew")

        self.btn_cancel = ctk.CTkButton(
            self.sidebar_frame, text="⏹️ CANCELAR", font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#C0392B", hover_color="#922B21", height=40,
            command=self.cancelar_extracao, state="disabled"
        )
        self.btn_cancel.grid(row=5, column=0, padx=30, pady=(0, 30), sticky="ew")

        # ==========================================
        # --- ÁREA PRINCIPAL (STATUS E ABAS) ---
        # ==========================================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#0A0A0A")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0)
        
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1) # Tabview ocupa o resto do espaço
        
        # --- CARTÃO DE STATUS ---
        self.info_card = ctk.CTkFrame(self.main_frame, fg_color="#1E1E24", corner_radius=0)
        self.info_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.lbl_card_title = ctk.CTkLabel(self.info_card, text="Status: Ocioso 🟢", font=ctk.CTkFont(size=22, weight="bold"), text_color="#FFFFFF")
        self.lbl_card_title.pack(anchor="w", padx=25, pady=(20, 5))

        self.lbl_card_desc = ctk.CTkLabel(self.info_card, text="Leia a aba 'Guia & FAQ' para entender o processo antes de Ligar o Motor.", font=ctk.CTkFont(size=14), text_color="#BBBBBB")
        self.lbl_card_desc.pack(anchor="w", padx=25, pady=(0, 20))

        # --- TABVIEW (SISTEMA DE ABAS) ---
        self.tabview = ctk.CTkTabview(self.main_frame, fg_color="#0D0D12", corner_radius=12)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        self.tab_terminal = self.tabview.add("📄 Terminal de Extração")
        self.tab_faq = self.tabview.add("🧠 Guia & FAQ RAG")

        # Configuração da Aba: Terminal
        self.tab_terminal.grid_rowconfigure(0, weight=1)
        self.tab_terminal.grid_columnconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(
            self.tab_terminal, font=ctk.CTkFont(family="Consolas", size=13), 
            fg_color="transparent", text_color="#00FF9D", activate_scrollbars=True
        )
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.textbox.insert("0.0", "[SISTEMA] Motor $ardinh'IA conectado.\n[SISTEMA] Acesse a aba 'Guia & FAQ' para instruções.\n\n")
        self.textbox.configure(state="disabled")

        sys.stdout = PrintRedirector(self.textbox)
        sys.stderr = sys.stdout

        # Configuração da Aba: Guia & FAQ
        self.tab_faq.grid_rowconfigure(0, weight=1)
        self.tab_faq.grid_columnconfigure(0, weight=1)

        self.scroll_faq = ctk.CTkScrollableFrame(self.tab_faq, fg_color="transparent")
        self.scroll_faq.grid(row=0, column=0, sticky="nsew")

# ==========================================
        # --- ACCORDIONS COM AS INSTRUÇÕES E FAQ ---
        # ==========================================
        
        texto_etapa1 = "O motor $ardinh'IA varre o ecossistema do YouTube da AUVP (Vídeos, Shorts, Podcasts, Ao Vivo). Ele compara o que está online com o que você já tem no banco de dados local (seu arquivo CSV). Ele nunca baixa arquivos duplicados, garantindo eficiência de custo e tempo."
        AccordionItem(self.scroll_faq, "Etapa 1: Mapeamento Inteligente", texto_etapa1).pack(fill="x", pady=20)

        texto_etapa2 = "Para cada vídeo inédito, o motor extrai o VTT (legenda oculta) sem baixar o peso em MP4. O texto é limpo (remoção de timestamps e tags HTML) e agrupado em arquivos de texto de até 40.000 palavras. Isso prepara o terreno (chunking) para a Inteligência Artificial ingerir tudo sem travar ou sofrer de alucinação."
        AccordionItem(self.scroll_faq, "Etapa 2: Ingestão e Processamento RAG", texto_etapa2).pack(fill="x", pady=20)

        texto_etapa3 = "Você pode pausar ou cancelar o processo a qualquer momento pelos botões na barra lateral. Se cancelar, o sistema fará o 'Graceful Shutdown': ele não corrompe o arquivo atual, encerra o ciclo com segurança e envia imediatamente tudo o que já processou para o seu Google Drive."
        AccordionItem(self.scroll_faq, "Etapa 3: Controle e Segurança de Dados", texto_etapa3).pack(fill="x", pady=20)

        texto_faq1 = "O NotebookLM do Google é o nosso primeiro laboratório prático. Ao fazer o upload da nossa pasta 'Cerebro_Docs' para lá, ele não apenas lê o texto, mas cria um índice semântico poderoso. Ele gera citações exatas da fonte original (indicando em qual vídeo o Raul falou aquilo), cria guias de estudo, cronogramas e garante zero alucinação externa, pois é forçado a usar APENAS a nossa base."
        AccordionItem(self.scroll_faq, "FAQ: O poder do NotebookLM (Fase 1)", texto_faq1).pack(fill="x", pady=20)

        texto_faq2 = "Uma das funções de maior ROI de tempo do NotebookLM é o 'Audio Overview'. Com um clique, ele processa todas as transcrições do Raul Sena e gera um podcast em áudio, simulando dois apresentadores que discutem e resumem os fundamentos da AUVP. É a automação máxima do reaproveitamento de conteúdo."
        AccordionItem(self.scroll_faq, "FAQ: Criação de Podcasts com IA?", texto_faq2).pack(fill="x", pady=20)

        texto_faq3 = "A Fase 2 do nosso projeto é abandonar o ambiente fechado do NotebookLM e construir nosso próprio Agente. Usaremos a API do Google Gemini 1.5 Pro/Flash. Com a janela de contexto massiva de 2 milhões de tokens do Gemini, somada a um Vector Database (como Pinecone ou ChromaDB), criaremos um bot no Telegram/WhatsApp que responde às dúvidas financeiras dos alunos com o exato tom de voz e raciocínio do Raul Sena."
        AccordionItem(self.scroll_faq, "FAQ: Próximos Passos (Implementação Gemini)", texto_faq3).pack(fill="x", pady=20)

        texto_faq4 = "No modelo RAG (Retrieval-Augmented Generation), o LLM (Gemini) é o 'motor', e a base de texto da AUVP é o 'combustível'. Ao forçar a IA a buscar a resposta primeiro nos nossos documentos antes de formular a frase, nós blindamos o sistema contra invenções financeiras. É a proteção do nosso capital intelectual: só entregamos 'A Única Verdade Possível'."
        AccordionItem(self.scroll_faq, "FAQ: Como o RAG protege a Verdade?", texto_faq4).pack(fill="x", pady=20)

    # ==========================================
    # --- LÓGICA DE CONTROLE DE THREADS ---
    # ==========================================

    def iniciar_extracao(self):
        # Obriga o app a mudar para a aba do terminal quando inicia
        self.tabview.set("📄 Terminal de Extração")
        
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("end", "[SISTEMA] Iniciando nova extração...\n\n")
        self.textbox.configure(state="disabled")

        self.evento_cancelar.clear()
        self.evento_pausa.set()
        
        self.btn_start.configure(state="disabled", text="⚙️ RODANDO...", fg_color="#333333", text_color="#aaaaaa")
        self.btn_pause.configure(state="normal", text="⏸️ PAUSAR", fg_color="#D35400")
        self.btn_cancel.configure(state="normal", text="⏹️ CANCELAR")
        
        self.lbl_card_title.configure(text="Status: Extraindo Dados 🔥", text_color="#FFA500")
        self.lbl_card_desc.configure(text="O motor está em funcionamento. Pode pausar ou cancelar o processo de forma segura.")
        
        t = threading.Thread(target=self.rodar_motor)
        t.daemon = True 
        t.start()

    def pausar_extracao(self):
        if self.evento_pausa.is_set():
            self.evento_pausa.clear()
            self.btn_pause.configure(text="▶️ RETOMAR", fg_color="#27AE60", hover_color="#1E8449")
            self.lbl_card_title.configure(text="Status: Em Pausa ⏸️", text_color="#F1C40F")
            print("\n[SISTEMA] Comando de pausa recebido. Aguardando finalização do ciclo seguro...")
        else:
            self.evento_pausa.set()
            self.btn_pause.configure(text="⏸️ PAUSAR", fg_color="#D35400", hover_color="#A04000")
            self.lbl_card_title.configure(text="Status: Extraindo Dados 🔥", text_color="#FFA500")
            print("\n[SISTEMA] Retomando a extração de dados...")

    def cancelar_extracao(self):
        self.evento_cancelar.set()
        self.evento_pausa.set() 
        
        self.btn_pause.configure(state="disabled")
        self.btn_cancel.configure(state="disabled", text="CANCELANDO...")
        self.lbl_card_title.configure(text="Status: Cancelando... 🛑", text_color="#FF4444")
        self.lbl_card_desc.configure(text="Fechando o pacote de dados e efetuando backup para a nuvem. Aguarde.")
        print("\n[SISTEMA] Cancelamento solicitado. Iniciando Graceful Shutdown...")

    def rodar_motor(self):
        try:
            print("="*65)
            print("🚀 INICIANDO ESTEIRA DE DADOS...")
            print("="*65 + "\n")
            
            motor_sardinha.sardinha_engine_v47_rescue(
                evento_pausa=self.evento_pausa, 
                evento_cancelar=self.evento_cancelar
            )
            
            if self.evento_cancelar.is_set():
                print("\n⚠️ Processo interrompido com segurança. Os dados extraídos foram salvos.")
                self.lbl_card_title.configure(text="Status: Interrompido ⚠️", text_color="#F1C40F")
                self.lbl_card_desc.configure(text="Extração cancelada pelo usuário. O progresso foi assegurado na nuvem.")
            else:
                print("\n✅ PROCESSO 100% CONCLUÍDO. A Base de Conhecimento está atualizada!")
                self.lbl_card_title.configure(text="Status: Finalizado ✅", text_color="#00FF9D")
                self.lbl_card_desc.configure(text="Todos os dados foram sincronizados com sucesso na sua máquina e no Drive.")
                
        except Exception as e:
            print(f"\n❌ ERRO CRÍTICO NO APP: {e}")
            self.lbl_card_title.configure(text="Status: Erro ❌", text_color="#FF4444")
            self.lbl_card_desc.configure(text="Ocorreu uma falha inesperada. Consulte o terminal.")
        finally:
            self.btn_start.configure(state="normal", text="⚡ REINICIAR MOTOR", fg_color="#0056D2", text_color="#ffffff")
            self.btn_pause.configure(state="disabled", text="⏸️ PAUSAR", fg_color="#D35400")
            self.btn_cancel.configure(state="disabled", text="⏹️ CANCELAR")

if __name__ == "__main__":
    app = SardinhaApp()
    app.mainloop()