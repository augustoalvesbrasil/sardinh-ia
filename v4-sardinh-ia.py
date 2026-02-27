import os
import time
import subprocess
import re
import pandas as pd
from datetime import datetime

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
GESTÃO_FOLDER = 'gestao_local'
DB_FILE = os.path.join(GESTÃO_FOLDER, 'base_conhecimento_auvp.csv')
MAX_WORDS_PER_FILE = 150000 # Reduzido para encaixar perfeito no Google Docs

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
# --- INTEGRAÇÃO DRIVE E GOOGLE DOCS ---
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

def upload_txt_como_gdoc(service, filepath, drive_folder_id):
    """Sobe o arquivo TXT e pede pro Google Drive convertê-lo para Google Docs nativo"""
    filename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(filename)[0]
    
    file_metadata = {
        'name': name_without_ext,
        'parents': [drive_folder_id],
        'mimeType': 'application/vnd.google-apps.document' 
    }
    
    media = MediaFileUpload(filepath, mimetype='text/plain', resumable=True)
    
    q = f"name = '{name_without_ext}' and '{drive_folder_id}' in parents and trashed = false"
    res = service.files().list(q=q).execute().get('files', [])
    
    if res:
        service.files().update(fileId=res[0]['id'], media_body=media).execute()
    else:
        service.files().create(body=file_metadata, media_body=media).execute()
        
    print(f"      ⬆️ Convertido e Sincronizado: {name_without_ext} (Google Docs)")

def upload_arquivo_drive(service, filepath, drive_folder_id):
    """Utilidade para subir arquivos que não precisam de conversão (ex: CSV)"""
    filename = os.path.basename(filepath)
    media = MediaFileUpload(filepath, resumable=True)
    q = f"name = '{filename}' and '{drive_folder_id}' in parents and trashed = false"
    res = service.files().list(q=q).execute().get('files', [])
    if res:
        service.files().update(fileId=res[0]['id'], media_body=media).execute()
    else:
        service.files().create(body={'name': filename, 'parents': [drive_folder_id]}, media_body=media).execute()
    print(f"      ⬆️ Sincronizado: {filename}")

# ==========================================
# --- MOTOR SARDINHA V42 ---
# ==========================================

def sardinha_engine_v42_gdocs_lineage():
    print("\n" + "="*70)
    print("🚀 SARDINHA ENGINE V42: GDOCS & DATA LINEAGE")
    print("="*70 + "\n")
    
    for d in [LOCAL_TXT_DIR, GESTÃO_FOLDER]:
        if not os.path.exists(d): os.makedirs(d)

    # 1. Mapeamento Inteligente de Ativos
    all_videos = []
    ids_mapeados_globais = set() 
    
    print("📡 Iniciando mapeamento do ecossistema AUVP...\n")
    
    for fonte in FONTES_AUVP:
        aba = fonte['aba']
        url = fonte['url']
        print(f"   🔎 Varrendo aba: {aba}...")
        
        if aba == "Videos":
            cmd = ['yt-dlp', '--flat-playlist', '--ignore-errors', '--print', '%(id)s|||%(upload_date)s|||%(view_count)s|||%(title)s', url]
            stdout = executar_comando(cmd)
            inéditos = 0
            pulados = 0
            for line in stdout.split('\n'):
                parts = line.split('|||')
                if len(parts) >= 4:
                    v_id = parts[0]
                    if v_id in ids_mapeados_globais: pulados += 1
                    else:
                        inéditos += 1
                        all_videos.append({'id': v_id, 'date': formatar_data(parts[1]), 'views': parts[2], 'title': parts[3], 'aba': aba})
                        ids_mapeados_globais.add(v_id)
            print(f"      ✅ {inéditos} itens INÉDITOS mapeados.")
            print(f"      ⚠️  {pulados} itens IGNORADOS (já coletados).\n")
            
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
            print(f"      ✅ {contador_playlist} itens mapeados em '{aba}'.\n")
            
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
    print(f"📊 RESUMO DO MAPEAMENTO: {total_liquido} conteúdos prontos para extração.")
    print("="*70 + "\n")
    
    # 2. Gestão do Banco de Dados com nova coluna 'Local'
    if os.path.exists(DB_FILE):
        df_db = pd.read_csv(DB_FILE, dtype=str)
        # Se a planilha for antiga e não tiver a coluna Local, cria dinamicamente
        if 'Local' not in df_db.columns:
            df_db['Local'] = 'Desconhecido'
    else:
        df_db = pd.DataFrame(columns=['ID', 'Data_Pub', 'Link', 'Titulo', 'Aba', 'Views', 'Local', 'Status'])

    print("🚜 Iniciando o Trator de Extração V1...\n")

    # 3. Extração e Particionamento
    palavras_acumuladas = 0
    parte = 1
    nome_arquivo_base = f"Cerebro_AUVP_Parte_{parte}"
    caminho_txt = os.path.join(LOCAL_TXT_DIR, f"{nome_arquivo_base}.txt")

    for idx, video in df_full.iterrows():
        v_id, v_title = video['id'], video['title']
        v_link = f"https://www.youtube.com/watch?v={v_id}"
        prefix = f"[{idx+1}/{total_liquido}]"

        if v_title in ['[Private video]', '[Deleted video]']: continue

        if v_id in df_db['ID'].values:
            print(f"{prefix} ⏭️  Pular (Já minerado no banco local): {v_title[:40]}...")
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
                    
                    if palavras_acumuladas + num_palavras > MAX_WORDS_PER_FILE:
                        parte += 1
                        palavras_acumuladas = 0
                        nome_arquivo_base = f"Cerebro_AUVP_Parte_{parte}"
                        caminho_txt = os.path.join(LOCAL_TXT_DIR, f"{nome_arquivo_base}.txt")
                        print(f"      📂 NOVO ARQUIVO: Limite alcançado. Iniciando Parte {parte}...")

                    with open(caminho_txt, "a", encoding="utf-8-sig") as f:
                        f.write(f"\n{'='*70}\nTITULO: {v_title}\nABA: {video['aba']}\nDATA: {video['date']}\nLINK: {v_link}\n{'-'*70}\nCONTEÚDO:\n{texto}\n{'='*70}\n")
                    
                    palavras_acumuladas += num_palavras
                    
                    # Atualiza Planilha informando o 'Local' exato de arquivamento
                    nova_linha = {
                        'ID': v_id, 
                        'Data_Pub': video['date'], 
                        'Link': v_link, 
                        'Titulo': v_title, 
                        'Aba': video['aba'], 
                        'Views': video['views'], 
                        'Local': nome_arquivo_base, # Ex: Cerebro_AUVP_Parte_1
                        'Status': 'Sucesso'
                    }
                    df_db = pd.concat([df_db, pd.DataFrame([nova_linha])], ignore_index=True)
                    df_db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                    
                    print(f"      ✅ Sucesso Local! Salvo em: {nome_arquivo_base}")
                
                for f in vtt_files: os.remove(f)
            else:
                print(f"      ❌ YouTube sem transcrição.")
            time.sleep(2) 
        except Exception as e:
            print(f"      ❌ Erro: {e}")

    # A fase de Geração de PDFs local foi removida. Vamos direto para o Drive!

    # 4. Sincronização Final com Drive
    try:
        print("\n☁️ Sincronizando e Convertendo para Google Docs...")
        service = get_drive_service()
        
        id_docs = garantir_pasta_drive(service, "Cerebro_Docs", DRIVE_ROOT_FOLDER)
        
        print("📁 Subindo e convertendo arquivos TXT para Google Docs...")
        for f in os.listdir(LOCAL_TXT_DIR):
            if f.endswith(".txt"):
                caminho_arquivo = os.path.join(LOCAL_TXT_DIR, f)
                upload_txt_como_gdoc(service, caminho_arquivo, id_docs)
            
        print("📊 Subindo Planilha de Gestão CSV...")
        FOLDER_SHEETS_DRIVE = '1CPrBStkj77nNzS8olKiz7mtDBVZ79pJK'
        upload_arquivo_drive(service, DB_FILE, FOLDER_SHEETS_DRIVE)

        print("\n🏆 MISSÃO CONCLUÍDA! Base de conhecimento estruturada em Google Docs.")
    except Exception as e:
        print(f"❌ Erro na sincronização com Drive: {e}")

if __name__ == "__main__":
    sardinha_engine_v42_gdocs_lineage()