import pandas as pd
import os
from datetime import datetime

def radar_atualizacao():
    caminho_db = os.path.join('gestao_local', 'base_conhecimento_auvp.csv')
    
    if not os.path.exists(caminho_db):
        print("❌ CSV não encontrado.")
        return

    df = pd.read_csv(caminho_db, encoding='utf-8-sig')
    
    # Verifica se a coluna nova já existe
    if 'Data_Extracao' not in df.columns:
        print("⚠️ A coluna 'Data_Extracao' ainda não existe no seu CSV.")
        print("Faça a alteração no v5-sardinh-ia.py e rode uma nova extração primeiro.")
        return

    # Pega a data de hoje (ou a data da última extração registrada)
    ultima_data = df['Data_Extracao'].max()
    
    # Filtra apenas os vídeos que foram extraídos nessa última rodada
    df_recentes = df[df['Data_Extracao'] == ultima_data]
    
    # Descobre quais foram os TXTs afetados
    arquivos_afetados = df_recentes['Local'].unique()

    print("=" * 60)
    print(f"🔄 RADAR NOTEBOOKLM - ATUALIZAÇÃO DELTA")
    print(f"Última extração realizada em: {ultima_data}")
    print("=" * 60)
    
    if len(arquivos_afetados) == 0:
        print("Nenhum arquivo novo para atualizar.")
    else:
        print(f"⚠️ Atenção, Sardinha! Você só precisa substituir {len(arquivos_afetados)} arquivo(s) no NotebookLM:")
        print("-" * 60)
        
        for arquivo in arquivos_afetados:
            qtd_videos = len(df_recentes[df_recentes['Local'] == arquivo])
            print(f"📄 Arquivo: {arquivo}.txt")
            print(f"   ↳ Recebeu {qtd_videos} vídeo(s) novo(s).")
            
        print("-" * 60)
        print("Ação: Vá no NotebookLM, exclua apenas esses arquivos acima e faça o upload das versões novas da sua pasta local.")
        print("=" * 60)

if __name__ == "__main__":
    radar_atualizacao()