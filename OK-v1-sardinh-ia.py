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

# --- CONFIGURAÇÕES DRIVE ---
FOLDER_BRAIN_DRIVE = '17AbJyV-ckWJFEngdsNytMBAxX_AIKQE2'   
FOLDER_SHEETS_DRIVE = '1CPrBStkj77nNzS8olKiz7mtDBVZ79pJK'  
SCOPES = ['https://www.googleapis.com/auth/drive']

# --- CONFIGURAÇÕES LOCAIS (IGUAL V4) ---
URL_CANAL = 'https://www.youtube.com/@InvestidorSardinha/playlists'
OUTPUT_FOLDER = 'cerebro_local'
GESTÃO_FOLDER = 'gestao_local'
DB_FILE = os.path.join(GESTÃO_FOLDER, 'base_conhecimento_auvp.csv')
EXCEL_FILE = os.path.join(GESTÃO_FOLDER, 'base_conhecimento_auvp.xlsx')

def sanitizar_nome(nome):
    if not nome: return "Sem_Nome"
    return re.sub(r'[<>:"/\\|?*]', '', str(nome)).strip()

def formatar_data(data_str):
    if not data_str or data_str == 'NA': return ""
    try: return datetime.strptime(str(data_str), '%Y%m%d').strftime('%d/%m/%Y')
    except: return data_str

def limpar_vtt(caminho_vtt):
    """Lógica Simples da v4"""
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
    """Lógica da v4: Captura simples de saída"""
    result = subprocess.run(cmd, capture_output=True, text=False, check=False)
    return result.stdout.decode('utf-8', errors='replace')

# ==========================================
# --- LOGICA DRIVE (SÓ NO FINAL) ---
# ==========================================

def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token: token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def sincronizar_com_drive():
    print("\n☁️  Iniciando Sincronização Final com o Drive...")
    try:
        service = get_drive_service()
        # TXTs
        for arq in os.listdir(OUTPUT_FOLDER):
            if arq.endswith(".txt"):
                caminho = os.path.join(OUTPUT_FOLDER, arq)
                media = MediaFileUpload(caminho, resumable=True)
                # Verifica se existe para atualizar ou criar
                q = f"name = '{arq}' and '{FOLDER_BRAIN_DRIVE}' in parents and trashed = false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: service.files().update(fileId=res[0]['id'], media_body=media).execute()
                else: service.files().create(body={'name': arq, 'parents': [FOLDER_BRAIN_DRIVE]}, media_body=media).execute()
                print(f"   ✅ {arq} sincronizado.")
        
        # Planilhas
        for arq_path, nome_drive in [(DB_FILE, 'base_conhecimento_auvp.csv'), (EXCEL_FILE, 'base_conhecimento_auvp.xlsx')]:
            if os.path.exists(arq_path):
                media = MediaFileUpload(arq_path, resumable=True)
                q = f"name = '{nome_drive}' and '{FOLDER_SHEETS_DRIVE}' in parents and trashed = false"
                res = service.files().list(q=q).execute().get('files', [])
                if res: service.files().update(fileId=res[0]['id'], media_body=media).execute()
                else: service.files().create(body={'name': nome_drive, 'parents': [FOLDER_SHEETS_DRIVE]}, media_body=media).execute()
                print(f"   ✅ {nome_drive} sincronizado.")
    except Exception as e:
        print(f"❌ Erro no Drive: {e}")

# ==========================================
# --- MOTOR PRINCIPAL (ALMA DA V4) ---
# ==========================================

def sardinha_v19_master():
    print("\n" + "="*60)
    print("🚀 SARDINHA ENGINE V19: THE LEGACY (v4 core)")
    print("="*60 + "\n")
    
    if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)
    if not os.path.exists(GESTÃO_FOLDER): os.makedirs(GESTÃO_FOLDER)

    # 1. Mapeamento Playlists (Igual v4)
    print("📡 Localizando playlists...")
    cmd_p = ['yt-dlp', '--flat-playlist', '--get-id', '--get-title', '--ignore-errors', URL_CANAL]
    stdout_p = executar_comando(cmd_p)
    p_lines = [l.strip() for l in stdout_p.split('\n') if l.strip()]
    
    playlists_info = []
    for i in range(0, len(p_lines), 2):
        if i+1 < len(p_lines):
            playlists_info.append({'title': p_lines[i], 'id': p_lines[i+1]})

    # 2. Varredura de Vídeos (Igual v4/v8)
    all_videos = []
    print(f"✅ {len(playlists_info)} Playlists mapeadas. Escaneando vídeos...")
    for p in playlists_info:
        print(f"   📂 Mapeando: {p['title'][:40]}...")
        cmd_v = ['yt-dlp', '--flat-playlist', '--ignore-errors', '--print', '%(id)s|||%(upload_date)s|||%(view_count)s|||%(title)s', f"https://www.youtube.com/playlist?list={p['id']}"]
        stdout_v = executar_comando(cmd_v)
        for line in stdout_v.split('\n'):
            parts = line.split('|||')
            if len(parts) >= 4:
                all_videos.append({'id': parts[0], 'date': formatar_data(parts[1]), 'views': parts[2], 'title': parts[3], 'playlist': p['title']})

    total = len(all_videos)
    print(f"\n📊 {total} vídeos identificados. Iniciando Mineração Local...")

    df_db = pd.DataFrame(columns=['ID', 'Data_Pub', 'Link', 'Titulo', 'Playlist', 'Views', 'Status'])

    # 3. Mineração (O "Trator" v4)
    for idx, video in enumerate(all_videos, 1):
        v_id, v_title, v_link = video['id'], video['title'], f"https://www.youtube.com/watch?v={video['id']}"
        nome_txt = f"{sanitizar_nome(video['playlist'])}.txt"
        caminho_local = os.path.join(OUTPUT_FOLDER, nome_txt)
        prefix = f"[{idx}/{total}]"

        if v_title in ['[Private video]', '[Deleted video]']: continue

        # Pular se já estiver no arquivo físico local
        if os.path.exists(caminho_local):
            with open(caminho_local, 'r', encoding='utf-8-sig') as f:
                if v_link in f.read():
                    print(f"{prefix} ⏭️  Pular: {v_title[:45]} (OK)")
                    continue

        print(f"{prefix} 🎬 Extraindo: {v_title[:45]}...")
        
        try:
            temp_out = f"temp_{v_id}"
            # Comando v4 Exato
            subprocess.run(['yt-dlp', '--skip-download', '--write-auto-sub', '--sub-lang', 'pt', '--output', temp_out, v_link], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            vtt_file = f"{temp_out}.pt.vtt"
            if os.path.exists(vtt_file):
                texto = limpar_vtt(vtt_file)
                if len(texto) > 150:
                    with open(caminho_local, "a", encoding="utf-8-sig") as f:
                        f.write(f"\n{'='*70}\nTITULO: {v_title}\nDATA: {video['date']}\nLINK: {v_link}\n{'-'*70}\nCONTEÚDO:\n{texto}\n{'='*70}\n")
                    
                    nova_linha = {'ID': v_id, 'Data_Pub': video['date'], 'Link': v_link, 'Titulo': v_title, 'Playlist': video['playlist'], 'Views': video['views'], 'Status': 'Sucesso'}
                    df_db = pd.concat([df_db, pd.DataFrame([nova_linha])], ignore_index=True)
                    df_db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                    print(f"      ✅ Sucesso Local!")
                
                if os.path.exists(vtt_file): os.remove(vtt_file)
            else:
                print(f"      ❌ YouTube sem transcrição.")
            time.sleep(2) # Pausa estratégica
        except Exception as e:
            print(f"      ❌ Erro: {e}")

    # 4. Geração do Excel e Sincronização Final
    df_db['Views'] = pd.to_numeric(df_db['Views'], errors='coerce').fillna(0).astype(int)
    df_db.to_excel(EXCEL_FILE, index=False)
    
    sincronizar_com_drive()
    print("\n🏆 MISSÃO CONCLUÍDA! Seu Cérebro local e na Nuvem estão atualizados.")

if __name__ == "__main__":
    sardinha_v19_master()