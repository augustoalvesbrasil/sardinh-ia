import os
import time
import subprocess
import re
import io
import pandas as pd
from datetime import datetime

# Bibliotecas Google Drive
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

# ==========================================
# --- CONFIGURAÇÕES E FUNDAMENTOS ---
# ==========================================
DRIVE_ROOT_FOLDER = '17AbJyV-ckWJFEngdsNytMBAxX_AIKQE2'   
SCOPES = ['https://www.googleapis.com/auth/drive']

FONTES_AUVP = [
    {"aba": "Shorts", "url": "https://www.youtube.com/@InvestidorSardinha/shorts", "is_playlist": False},
    {"aba": "Ao_Vivo", "url": "https://www.youtube.com/@InvestidorSardinha/streams", "is_playlist": False},
    {"aba": "Podcasts", "url": "https://www.youtube.com/@InvestidorSardinha/podcasts", "is_playlist": False},
    {"aba": "Cursos", "url": "https://www.youtube.com/@InvestidorSardinha/courses", "is_playlist": False},
    {"aba": "Playlists", "url": "https://www.youtube.com/@InvestidorSardinha/playlists", "is_playlist": True},
    {"aba": "Videos", "url": "https://www.youtube.com/@InvestidorSardinha/videos", "is_playlist": False}
]

LOCAL_TXT_DIR = 'cerebro_txt'
GESTÃO_FOLDER = 'gestao_local'
DB_FILE = os.path.join(GESTÃO_FOLDER, 'base_conhecimento_auvp.csv')

# LIMITE REDUZIDO (40k) para garantir que o GDocs nunca mais trave nos próximos
MAX_WORDS_PER_FILE = 40000 

# ==========================================
# --- UTILITÁRIOS ---
# ==========================================

def sanitizar_nome(nome):
    if not nome: return "Sem_Nome"
    return re.sub(r'[<>:"/\\|?*]', '', str(nome)).strip()

def formatar_data(data_str):
    if not data_str or data_str == 'NA': return ""
    try: return datetime.strptime(str(data_str), '%Y%m%d').strftime('%d/%m/%Y')
    except: return data_str

def limpar_vtt(caminho_vtt):
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
# --- INTEGRAÇÃO DRIVE (COM AUTO-RESGATE) ---
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

def _enviar_texto_gdoc(service, nome_arquivo, texto, drive_folder_id):
    """Motor de envio direto da memória para o Drive"""
    file_metadata = {
        'name': nome_arquivo,
        'parents': [drive_folder_id],
        'mimeType': 'application/vnd.google-apps.document' 
    }
    
    fh = io.BytesIO(texto.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)
    
    q = f"name = '{nome_arquivo}' and '{drive_folder_id}' in parents and trashed = false"
    res = service.files().list(q=q).execute().get('files', [])
    
    try:
        if res:
            service.files().update(fileId=res[0]['id'], media_body=media).execute()
            print(f"      🔄 Atualizado no Drive: {nome_arquivo} (Google Docs)")
        else:
            service.files().create(body=file_metadata, media_body=media).execute()
            print(f"      ⬆️ Convertido e Sincronizado: {nome_arquivo} (Google Docs)")
    except Exception as e:
        print(f"      ❌ Erro Crítico ao subir {nome_arquivo}: {e}")

def upload_txt_como_gdoc_seguro(service, filepath, drive_folder_id):
    """Lê o arquivo, fatia se for muito gordo, e sobe seguro"""
    filename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(filename)[0]
    
    # Se o arquivo for maior que 400KB, o GDocs chora. Vamos fatiar.
    tamanho_mb = os.path.getsize(filepath) / (1024 * 1024)
    
    with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
        conteudo = f.read()

    if tamanho_mb > 0.4:
        print(f"      ⚠️ Arquivo gordo detectado ({tamanho_mb:.2f}MB). Fatiando {name_without_ext} para evitar Erro 500...")
        blocos = conteudo.split('======================================================================')
        
        texto_temp = ""
        letra_parte = 65 # Ascii para 'A'
        
        for bloco in blocos:
            if not bloco.strip(): continue
            texto_temp += bloco + "\n" + "="*70 + "\n"
            
            # Se a fatia atual bater 300 mil caracteres, enviamos a fatia
            if len(texto_temp) > 300000: 
                sub_nome = f"{name_without_ext}_{chr(letra_parte)}"
                _enviar_texto_gdoc(service, sub_nome, texto_temp, drive_folder_id)
                letra_parte += 1
                texto_temp = ""
                
        # Envia a sobra
        if texto_temp.strip():
            sub_nome = f"{name_without_ext}_{chr(letra_parte)}"
            _enviar_texto_gdoc(service, sub_nome, texto_temp, drive_folder_id)
    else:
        # Se for magrinho, vai direto
        _enviar_texto_gdoc(service, name_without_ext, conteudo, drive_folder_id)

def upload_arquivo_drive(service, filepath, drive_folder_id):
    filename = os.path.basename(filepath)
    media = MediaFileUpload(filepath, resumable=True)
    q = f"name = '{filename}' and '{drive_folder_id}' in parents and trashed = false"
    res = service.files().list(q=q).execute().get('files', [])
    if res:
        service.files().update(fileId=res[0]['id'], media_body=media).execute()
        print(f"      🔄 Atualizado no Drive: {filename}")
    else:
        service.files().create(body={'name': filename, 'parents': [drive_folder_id]}, media_body=media).execute()
        print(f"      ⬆️ Sincronizado: {filename}")

# ==========================================
# --- MOTOR SARDINHA V47 ---
# ==========================================

def sardinha_engine_v47_rescue():
    print("\n" + "="*70)
    print("🚀 SARDINHA ENGINE V47: THE RESCUE OPERATION (Safe GDocs)")
    print("="*70 + "\n")
    
    for d in [LOCAL_TXT_DIR, GESTÃO_FOLDER]:
        if not os.path.exists(d): os.makedirs(d)

    # 1. MAPEAMENTO (Pula rápido se tudo já estiver no CSV)
    all_videos = []
    ids_mapeados_globais = set()
    
    print("📡 Verificando ecossistema AUVP...\n")
    for fonte in FONTES_AUVP:
        url = fonte['url']
        if fonte['is_playlist']:
            cmd_p = ['yt-dlp', '--flat-playlist', '--get-id', '--get-title', '--ignore-errors', url]
            stdout_p = executar_comando(cmd_p)
            p_lines = [l.strip() for l in stdout_p.split('\n') if l.strip()]
            for i in range(0, len(p_lines), 2):
                if i+1 < len(p_lines):
                    cmd_v = ['yt-dlp', '--flat-playlist', '--ignore-errors', '--print', '%(id)s|||%(upload_date)s|||%(view_count)s|||%(title)s', f"https://www.youtube.com/playlist?list={p_lines[i+1]}"]
                    stdout_v = executar_comando(cmd_v)
                    for line in stdout_v.split('\n'):
                        parts = line.split('|||')
                        if len(parts) >= 4 and parts[0] not in ids_mapeados_globais:
                            all_videos.append({'id': parts[0], 'date': formatar_data(parts[1]), 'views': parts[2], 'title': parts[3], 'aba': f"Playlist: {p_lines[i]}"})
                            ids_mapeados_globais.add(parts[0])
        else:
            cmd = ['yt-dlp', '--flat-playlist', '--ignore-errors', '--print', '%(id)s|||%(upload_date)s|||%(view_count)s|||%(title)s', url]
            stdout = executar_comando(cmd)
            for line in stdout.split('\n'):
                parts = line.split('|||')
                if len(parts) >= 4 and parts[0] not in ids_mapeados_globais:
                    all_videos.append({'id': parts[0], 'date': formatar_data(parts[1]), 'views': parts[2], 'title': parts[3], 'aba': fonte['aba']})
                    ids_mapeados_globais.add(parts[0])

    df_full = pd.DataFrame(all_videos)
    total_liquido = len(df_full)
    
    # 2. GESTÃO DO BANCO DE DADOS
    if os.path.exists(DB_FILE):
        df_db = pd.read_csv(DB_FILE, dtype=str)
        if 'Local' not in df_db.columns: df_db['Local'] = 'Desconhecido'
        ids_ja_minerados = set(df_db['ID'].values)
    else:
        df_db = pd.DataFrame(columns=['ID', 'Data_Pub', 'Link', 'Titulo', 'Aba', 'Views', 'Local', 'Status'])
        ids_ja_minerados = set()

    parte_atual = 1
    palavras_atuais = 0
    arquivos_txt = [f for f in os.listdir(LOCAL_TXT_DIR) if f.startswith("Cerebro_AUVP_Parte_") and f.endswith(".txt")]
    
    if arquivos_txt:
        numeros = [int(re.search(r'Parte_(\d+)', f).group(1)) for f in arquivos_txt if re.search(r'Parte_(\d+)', f)]
        if numeros:
            parte_atual = max(numeros)
            with open(os.path.join(LOCAL_TXT_DIR, f"Cerebro_AUVP_Parte_{parte_atual}.txt"), 'r', encoding='utf-8-sig', errors='ignore') as f:
                palavras_atuais = len(f.read().split())

    nome_arquivo_base = f"Cerebro_AUVP_Parte_{parte_atual}"
    caminho_txt = os.path.join(LOCAL_TXT_DIR, f"{nome_arquivo_base}.txt")

    print("\n🚜 Verificando fila de extração...\n")

    # 3. EXTRAÇÃO
    for idx, video in df_full.iterrows():
        v_id, v_title = video['id'], video['title']
        v_link = f"https://www.youtube.com/watch?v={v_id}"

        if v_title in ['[Private video]', '[Deleted video]']: continue
        if v_id in ids_ja_minerados: continue # Silenciei o print de pulo para ir rápido pro Drive

        print(f"[{idx+1}/{total_liquido}] 🎬 Extraindo inédito: {v_title[:40]}...")
        try:
            temp_out = f"temp_{v_id}"
            subprocess.run(['yt-dlp', '--skip-download', '--write-auto-sub', '--sub-lang', 'pt', '--output', temp_out, v_link], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            vtt_files = [f for f in os.listdir('.') if f.startswith(temp_out) and f.endswith('.vtt')]
            if vtt_files:
                texto = limpar_vtt(vtt_files[0])
                if len(texto) > 150:
                    num_palavras = len(texto.split())
                    
                    if palavras_atuais + num_palavras > MAX_WORDS_PER_FILE:
                        parte_atual += 1
                        palavras_atuais = 0
                        nome_arquivo_base = f"Cerebro_AUVP_Parte_{parte_atual}"
                        caminho_txt = os.path.join(LOCAL_TXT_DIR, f"{nome_arquivo_base}.txt")
                        print(f"      📂 NOVO ARQUIVO: Limite seguro alcançado. Iniciando Parte {parte_atual}...")

                    with open(caminho_txt, "a", encoding="utf-8-sig") as f:
                        f.write(f"\n{'='*70}\nTITULO: {v_title}\nABA: {video['aba']}\nDATA: {video['date']}\nLINK: {v_link}\n{'-'*70}\nCONTEÚDO:\n{texto}\n{'='*70}\n")
                    
                    palavras_atuais += num_palavras
                    
                    ids_ja_minerados.add(v_id)
                    nova_linha = {'ID': v_id, 'Data_Pub': video['date'], 'Link': v_link, 'Titulo': v_title, 'Aba': video['aba'], 'Views': video['views'], 'Local': nome_arquivo_base, 'Status': 'Sucesso'}
                    df_db = pd.concat([df_db, pd.DataFrame([nova_linha])], ignore_index=True)
                    df_db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                    print(f"      ✅ OK!")
                for f in vtt_files: os.remove(f)
            time.sleep(1) 
        except Exception as e:
            print(f"      ❌ Erro: {e}")

    # 4. CONVERSÃO INTELIGENTE (O RESGATE)
    try:
        print("\n☁️ [INICIANDO UPLOAD SEGURO PARA O GOOGLE DOCS]...")
        service = get_drive_service()
        id_docs = garantir_pasta_drive(service, "Cerebro_Docs", DRIVE_ROOT_FOLDER)
        
        for f in os.listdir(LOCAL_TXT_DIR):
            if f.endswith(".txt"):
                caminho_arquivo = os.path.join(LOCAL_TXT_DIR, f)
                upload_txt_como_gdoc_seguro(service, caminho_arquivo, id_docs)
            
        print("\n📊 Subindo Planilha de Gestão CSV...")
        FOLDER_SHEETS_DRIVE = '1CPrBStkj77nNzS8olKiz7mtDBVZ79pJK'
        upload_arquivo_drive(service, DB_FILE, FOLDER_SHEETS_DRIVE)

        print("\n🏆 MISSÃO CUMPRIDA! Os arquivos foram fatiados e salvos com sucesso no Drive.")
    except Exception as e:
        print(f"❌ Erro crítico no ambiente de nuvem: {e}")

if __name__ == "__main__":
    sardinha_engine_v47_rescue()