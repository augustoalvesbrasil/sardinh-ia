import os
import time
import subprocess
import re
import pandas as pd
from datetime import datetime

# Bibliotecas PDF (fpdf2)
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Bibliotecas Google Drive
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# --- CONFIGURAÇÕES E FUNDAMENTOS ---
# ==========================================
DRIVE_ROOT_FOLDER = '17AbJyV-ckWJFEngdsNytMBAxX_AIKQE2'   
SCOPES = ['https://www.googleapis.com/auth/drive']

# Mapeamento Estratégico: Aba VÍDEOS posicionada por ÚLTIMO intencionalmente
FONTES_AUVP = [
    {"aba": "Shorts", "url": "https://www.youtube.com/@InvestidorSardinha/shorts", "is_playlist": False},
    {"aba": "Ao_Vivo", "url": "https://www.youtube.com/@InvestidorSardinha/streams", "is_playlist": False},
    {"aba": "Podcasts", "url": "https://www.youtube.com/@InvestidorSardinha/podcasts", "is_playlist": False},
    {"aba": "Cursos", "url": "https://www.youtube.com/@InvestidorSardinha/courses", "is_playlist": False},
    {"aba": "Playlists", "url": "https://www.youtube.com/@InvestidorSardinha/playlists", "is_playlist": True},
    {"aba": "Videos", "url": "https://www.youtube.com/@InvestidorSardinha/videos", "is_playlist": False} # A rede de segurança
]

LOCAL_TXT_DIR = 'cerebro_txt'
LOCAL_PDF_DIR = 'cerebro_pdf'
GESTÃO_FOLDER = 'gestao_local'
DB_FILE = os.path.join(GESTÃO_FOLDER, 'base_conhecimento_auvp.csv')
MAX_WORDS_PER_FILE = 400000 

# ==========================================
# --- UTILITÁRIOS (A ALMA DA V1) ---
# ==========================================

def sanitizar_nome(nome):
    if not nome: return "Sem_Nome"
    return re.sub(r'[<>:"/\\|?*]', '', str(nome)).strip()

def formatar_data(data_str):
    if not data_str or data_str == 'NA': return ""
    try: return datetime.strptime(str(data_str), '%Y%m%d').strftime('%d/%m/%Y')
    except: return data_str

def limpar_vtt(caminho_vtt):
    """Lógica purista da v1 - Evita duplicatas e limpa sujeira de HTML/VTT"""
    if not os.path.exists(caminho_vtt): return ""
    with open(caminho_vtt, 'r', encoding='utf-8', errors='replace') as f:
        linhas = f.readlines()
    texto_limpo = []
    for linha in linhas:
        if '-->' not in linha and not linha.strip().isdigit() and 'WEBVTT' not in linha:
            linha = re.sub(r'<[^>]*>', '', linha)
            if linha.strip(): texto_limpo.append(linha.strip())
    resultado = []
    if texto_limpo:
        resultado.append(texto_limpo[0])
        for i in range(1, len(texto_limpo)):
            if texto_limpo[i] != texto_limpo[i-1]:
                resultado.append(texto_limpo[i])
    return " ".join(resultado).strip()

def executar_comando(cmd):
    result = subprocess.run(cmd, capture_output=True, text=False, check=False)
    return result.stdout.decode('utf-8', errors='replace')

# ==========================================
# --- GERAÇÃO DE PDF ---
# ==========================================

class AUVP_PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'BASE DE CONHECIMENTO AUVP - FILOSOFIA SARDINHA', border=0, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

def criar_pdf_de_txt(caminho_txt, caminho_pdf):
    pdf = AUVP_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    with open(caminho_txt, 'r', encoding='utf-8-sig') as f:
        for linha in f:
            msg = linha.encode('latin-1', 'replace').decode('latin-1')
            if "TITULO:" in msg:
                pdf.set_font("helvetica", 'B', 11)
                pdf.multi_cell(0, 8, msg)
                pdf.set_font("helvetica", size=10)
            else:
                pdf.multi_cell(0, 5, msg)
    pdf.output(caminho_pdf)

# ==========================================
# --- INTEGRAÇÃO DRIVE ---
# ==========================================

def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token: token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def garantir_pasta_drive(service, nome, parent_id):
    query = f"name = '{nome}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res = service.files().list(q=query).execute().get('files', [])
    if res: return res[0]['id']
    meta = {'name': nome, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    return service.files().create(body=meta, fields='id').execute().get('id')

def upload_arquivo_drive(service, filepath, drive_folder_id):
    filename = os.path.basename(filepath)
    media = MediaFileUpload(filepath, resumable=True)
    q = f"name = '{filename}' and '{drive_folder_id}' in parents and trashed = false"
    res = service.files().list(q=q).execute().get('files', [])
    if res:
        service.files().update(fileId=res[0]['id'], media_body=media).execute()
    else:
        service.files().create(body={'name': filename, 'parents': [drive_folder_id]}, media_body=media).execute()

# ==========================================
# --- MOTOR SARDINHA V41 ---
# ==========================================

def sardinha_engine_v41_exclusao_mutua():
    print("\n" + "="*70)
    print("🚀 SARDINHA ENGINE V41: EXCLUSÃO MÚTUA & V1 CORE")
    print("="*70 + "\n")
    
    for d in [LOCAL_TXT_DIR, LOCAL_PDF_DIR, GESTÃO_FOLDER]:
        if not os.path.exists(d): os.makedirs(d)

    # 1. Mapeamento Inteligente de Ativos
    all_videos = []
    ids_mapeados_globais = set() # Memória ativa para evitar redundância
    
    print("📡 Iniciando mapeamento do ecossistema AUVP...\n")
    
    for fonte in FONTES_AUVP:
        aba = fonte['aba']
        url = fonte['url']
        print(f"   🔎 Varrendo aba: {aba}...")
        
        # Lógica Específica para a Aba VÍDEOS (Rede de Segurança)
        if aba == "Videos":
            cmd = ['yt-dlp', '--flat-playlist', '--ignore-errors', '--print', '%(id)s|||%(upload_date)s|||%(view_count)s|||%(title)s', url]
            stdout = executar_comando(cmd)
            
            inéditos = 0
            pulados = 0
            
            for line in stdout.split('\n'):
                parts = line.split('|||')
                if len(parts) >= 4:
                    v_id = parts[0]
                    # SE O VÍDEO JÁ ESTIVER NA MEMÓRIA (VEIO DE PLAYLIST, LIVES, ETC), PULA!
                    if v_id in ids_mapeados_globais:
                        pulados += 1
                    else:
                        inéditos += 1
                        all_videos.append({'id': v_id, 'date': formatar_data(parts[1]), 'views': parts[2], 'title': parts[3], 'aba': aba})
                        ids_mapeados_globais.add(v_id)
            
            print(f"      ✅ {inéditos} itens INÉDITOS mapeados em 'Videos'.")
            print(f"      ⚠️  {pulados} itens IGNORADOS nesta aba (já coletados em Playlists/Shorts/etc).\n")
            
        # Lógica para Playlists
        elif fonte['is_playlist']:
            cmd_p = ['yt-dlp', '--flat-playlist', '--get-id', '--get-title', '--ignore-errors', url]
            stdout_p = executar_comando(cmd_p)
            p_lines = [l.strip() for l in stdout_p.split('\n') if l.strip()]
            
            contador_playlist = 0
            for i in range(0, len(p_lines), 2):
                if i+1 < len(p_lines):
                    p_title, p_id = p_lines[i], p_lines[i+1]
                    cmd_v = ['yt-dlp', '--flat-playlist', '--ignore-errors', '--print', '%(id)s|||%(upload_date)s|||%(view_count)s|||%(title)s', f"https://www.youtube.com/playlist?list={p_id}"]
                    stdout_v = executar_comando(cmd_v)
                    for line in stdout_v.split('\n'):
                        parts = line.split('|||')
                        if len(parts) >= 4:
                            v_id = parts[0]
                            if v_id not in ids_mapeados_globais:
                                all_videos.append({'id': v_id, 'date': formatar_data(parts[1]), 'views': parts[2], 'title': parts[3], 'aba': f"Playlist: {p_title}"})
                                ids_mapeados_globais.add(v_id)
                                contador_playlist += 1
            print(f"      ✅ {contador_playlist} itens únicos mapeados em '{aba}'.\n")
            
        # Lógica para Shorts, Podcasts, Cursos, Lives
        else:
            cmd = ['yt-dlp', '--flat-playlist', '--ignore-errors', '--print', '%(id)s|||%(upload_date)s|||%(view_count)s|||%(title)s', url]
            stdout = executar_comando(cmd)
            
            contador_aba = 0
            for line in stdout.split('\n'):
                parts = line.split('|||')
                if len(parts) >= 4:
                    v_id = parts[0]
                    if v_id not in ids_mapeados_globais:
                        all_videos.append({'id': v_id, 'date': formatar_data(parts[1]), 'views': parts[2], 'title': parts[3], 'aba': aba})
                        ids_mapeados_globais.add(v_id)
                        contador_aba += 1
            print(f"      ✅ {contador_aba} itens mapeados em '{aba}'.\n")

    df_full = pd.DataFrame(all_videos)
    total_liquido = len(df_full)
    
    print("="*70)
    print(f"📊 RESUMO DO MAPEAMENTO LÍQUIDO: {total_liquido} conteúdos prontos para extração.")
    print("="*70 + "\n")
    
    # 2. Gestão do Banco de Dados (CSV Padrão V1, apenas alterando 'Playlist' por 'Aba')
    if os.path.exists(DB_FILE):
        df_db = pd.read_csv(DB_FILE, dtype=str)
    else:
        df_db = pd.DataFrame(columns=['ID', 'Data_Pub', 'Link', 'Titulo', 'Aba', 'Views', 'Status'])

    print("🚜 Iniciando o Trator de Extração V1...\n")

    # 3. Extração e Particionamento
    palavras_acumuladas = 0
    parte = 1
    caminho_txt = os.path.join(LOCAL_TXT_DIR, f"Cerebro_AUVP_Parte_{parte}.txt")

    for idx, video in df_full.iterrows():
        v_id, v_title = video['id'], video['title']
        v_link = f"https://www.youtube.com/watch?v={v_id}"
        prefix = f"[{idx+1}/{total_liquido}]"

        if v_title in ['[Private video]', '[Deleted video]']: continue

        # Check V1: Se o ID já está na planilha CSV, pula (economia de recursos)
        if v_id in df_db['ID'].values:
            print(f"{prefix} ⏭️  Pular (Já minerado no banco local): {v_title[:40]} (OK)")
            continue

        print(f"{prefix} 🎬 Extraindo [{video['aba']}]: {v_title[:40]}...")
        
        try:
            temp_out = f"temp_{v_id}"
            subprocess.run(['yt-dlp', '--skip-download', '--write-auto-sub', '--sub-lang', 'pt', '--output', temp_out, v_link], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            vtt_files = [f for f in os.listdir('.') if f.startswith(temp_out) and f.endswith('.vtt')]
            if vtt_files:
                texto = limpar_vtt(vtt_files[0])
                if len(texto) > 150:
                    num_palavras = len(texto.split())
                    
                    # Lógica V6: Particionamento RAG-Friendly (Max 400k words)
                    if palavras_acumuladas + num_palavras > MAX_WORDS_PER_FILE:
                        parte += 1
                        palavras_acumuladas = 0
                        caminho_txt = os.path.join(LOCAL_TXT_DIR, f"Cerebro_AUVP_Parte_{parte}.txt")
                        print(f"      📂 NOVO ARQUIVO: Limite alcançado. Iniciando Parte {parte}...")

                    # Salvamento V1 Style no TXT
                    with open(caminho_txt, "a", encoding="utf-8-sig") as f:
                        f.write(f"\n{'='*70}\nTITULO: {v_title}\nABA: {video['aba']}\nDATA: {video['date']}\nLINK: {v_link}\n{'-'*70}\nCONTEÚDO:\n{texto}\n{'='*70}\n")
                    
                    palavras_acumuladas += num_palavras
                    
                    # Atualiza Planilha V1 Style
                    nova_linha = {'ID': v_id, 'Data_Pub': video['date'], 'Link': v_link, 'Titulo': v_title, 'Aba': video['aba'], 'Views': video['views'], 'Status': 'Sucesso'}
                    df_db = pd.concat([df_db, pd.DataFrame([nova_linha])], ignore_index=True)
                    df_db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                    
                    print(f"      ✅ Sucesso Local!")
                
                for f in vtt_files: os.remove(f)
            else:
                print(f"      ❌ YouTube sem transcrição.")
            time.sleep(2) # Pausa estratégica fiel à V1
        except Exception as e:
            print(f"      ❌ Erro: {e}")

    # 4. Geração de PDFs (Lote Sequencial pós-fechamento do TXT)
    print("\n📑 Convertendo Cérebro TXT para PDF Particionado...")
    for arq in os.listdir(LOCAL_TXT_DIR):
        if arq.endswith(".txt"):
            txt_path = os.path.join(LOCAL_TXT_DIR, arq)
            pdf_path = os.path.join(LOCAL_PDF_DIR, arq.replace(".txt", ".pdf"))
            if not os.path.exists(pdf_path): 
                criar_pdf_de_txt(txt_path, pdf_path)
                print(f"   ✅ PDF Gerado: {os.path.basename(pdf_path)}")

    # 5. Sincronização Final com Drive
    try:
        print("\n☁️ Sincronizando com o Google Drive...")
        service = get_drive_service()
        
        id_txt = garantir_pasta_drive(service, "Cerebro_TXT", DRIVE_ROOT_FOLDER)
        id_pdf = garantir_pasta_drive(service, "Cerebro_PDF", DRIVE_ROOT_FOLDER)
        
        print("📁 Subindo arquivos TXT e PDF...")
        for local_dir, drive_id in [(LOCAL_TXT_DIR, id_txt), (LOCAL_PDF_DIR, id_pdf)]:
            for f in os.listdir(local_dir):
                upload_arquivo_drive(service, os.path.join(local_dir, f), drive_id)
                print(f"      ⬆️ Sincronizado: {f}")
            
        print("📊 Subindo Planilha de Gestão CSV...")
        FOLDER_SHEETS_DRIVE = '1CPrBStkj77nNzS8olKiz7mtDBVZ79pJK'
        upload_arquivo_drive(service, DB_FILE, FOLDER_SHEETS_DRIVE)

        print("\n🏆 MISSÃO CONCLUÍDA! Base de conhecimento estruturada e RAG-Ready.")
    except Exception as e:
        print(f"❌ Erro na sincronização com Drive: {e}")

if __name__ == "__main__":
    sardinha_engine_v41_exclusao_mutua()