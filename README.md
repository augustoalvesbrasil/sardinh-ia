# 🦈 SardinhIA — Motor de Extração e Base de Conhecimento AUVP

> Extração automatizada, processamento local e sincronização em nuvem do ecossistema de conteúdo do **Investidor Sardinha (AUVP)** — preparado para arquitetura RAG.

---

## 🎯 O que é este projeto?

O **SardinhIA** é uma ferramenta desktop que automatiza a construção de uma base de conhecimento estruturada a partir do conteúdo público do canal [@InvestidorSardinha](https://www.youtube.com/@InvestidorSardinha) no YouTube.

O motor varre todo o ecossistema de conteúdo (Vídeos, Shorts, Podcasts, Lives, Playlists e Cursos), extrai as legendas, limpa o texto e o particiona em arquivos otimizados para serem ingeridos por sistemas de IA — seguindo os princípios de **RAG (Retrieval-Augmented Generation)**.

Todo o processamento é feito **localmente** antes de qualquer envio à nuvem, evitando bloqueios do YouTube e garantindo que você sempre tenha uma cópia de segurança na sua máquina.

---

## ⚙️ Como funciona

O pipeline tem quatro etapas sequenciais:

```
YouTube ──▶ [1. Mapeamento] ──▶ [2. Extração Local + Chunking] ──▶ [3. Deduplicação + CSV] ──▶ [4. Upload Google Drive]
```

### 1. Mapeamento Inteligente
Usa o `yt-dlp` para varrer todas as seções do canal e montar uma lista completa de vídeos com ID, título, data e visualizações. Compara com o banco de dados local (CSV) para processar **somente o conteúdo inédito**, nunca duplicando trabalho.

### 2. Extração e Chunking Local
Para cada vídeo novo, baixa apenas o arquivo de **legenda VTT** (sem baixar o vídeo em si). O texto é então:
- Limpo de timestamps, tags HTML e linhas duplicadas
- Agrupado em arquivos `.txt` de até **40.000 palavras** cada

Esse tamanho foi calibrado para o contexto ideal de modelos de linguagem, evitando truncamentos e alucinações por excesso de contexto.

### 3. Banco de Dados Local (CSV)
Toda extração é registrada em `gestao_local/base_conhecimento_auvp.csv` com metadados completos: ID, título, aba, data de publicação, visualizações, arquivo de destino e status. Isso garante rastreabilidade total e permite auditorias.

### 4. Sincronização com o Google Drive
**Somente após toda a extração local estar concluída**, o motor conecta à API do Google Drive e sobe os arquivos como **Google Docs** (conversão automática) na pasta `AUVP - Base de Conhecimento`. Também sincroniza o CSV e gera um relatório de cobertura.

---

## 🖥️ Interface

O app tem uma UI desktop construída com `customtkinter`, com tema dark moderno:

- **Sidebar**: logo, cards de estatísticas ao vivo (vídeos processados, arquivos gerados), botões de controle
- **Aba Atividade**: log inteligente com timestamps e colorização automática por tipo de mensagem
- **Aba Guia & FAQ**: accordion com explicações detalhadas de cada etapa
- **Header de Status**: indicador colorido + progress bar animado

### Controles
| Botão | Ação |
|---|---|
| ⚡ Ligar Motor | Inicia o pipeline completo |
| ⏸ Pausar | Pausa entre ciclos (sem corromper dados) |
| ⏹ Cancelar | Graceful shutdown: salva tudo e sobe pro Drive antes de encerrar |

---

## 🚀 Como usar

### Pré-requisitos

```bash
pip install customtkinter pillow yt-dlp pandas google-auth google-auth-oauthlib google-api-python-client
```

Você também precisa do `yt-dlp` acessível no PATH do sistema.

### Configuração do Google Drive (uma única vez)

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto, habilite a **Google Drive API**
3. Crie credenciais do tipo **OAuth 2.0 (Aplicativo Desktop)**
4. Baixe o arquivo e salve como `credentials.json` na raiz do projeto
5. Na primeira execução, uma janela de autenticação abrirá no browser — após autorizar, o `token.json` é gerado automaticamente

> ⚠️ **Nunca suba `credentials.json` ou `token.json` para o git.** Eles estão no `.gitignore`.

### Executando

```bash
python app_sardinha.py
```

Ou use o executável gerado (veja seção Build abaixo).

---

## 📦 Build do Executável (.exe)

O projeto usa **PyInstaller** para gerar um executável Windows sem dependência de Python instalado:

```bash
pyinstaller app_sardinha.spec --noconfirm
```

O executável gerado estará em `dist/SardinhIA/SardinhIA.exe`.

> **Atenção:** Os arquivos `credentials.json` e `token.json` **não são empacotados** no `.exe` por segurança. Eles devem estar na pasta de trabalho a partir da qual o executável é iniciado.

---

## 📁 Estrutura do Projeto

```
sardinh-ia/
├── app_sardinha.py        # Interface gráfica (customtkinter)
├── motor_sardinha.py      # Engine de extração e sincronização
├── app_sardinha.spec      # Configuração do PyInstaller
├── logo.png               # Logo da sidebar
├── logo_AUVP.png          # Logo AUVP
├── sardinh-ia.ico         # Ícone do executável
│
├── cerebro_txt/           # 📄 Arquivos .txt gerados (ignorados pelo git)
├── gestao_local/          # 📊 CSV e relatórios (CSV ignorado pelo git)
├── dist/                  # 📦 Build do executável (ignorado pelo git)
└── build/                 # 🔧 Artefatos do PyInstaller (ignorado pelo git)
```

---

## 🧠 Uso com IA (RAG)

Os arquivos gerados em `cerebro_txt/` estão prontos para serem usados com qualquer sistema de IA:

### Google NotebookLM (recomendado para começar)
1. Acesse [notebooklm.google.com](https://notebooklm.google.com)
2. Crie um novo notebook e importe os arquivos da pasta `Cerebro_Docs` do seu Drive
3. Faça perguntas sobre finanças e investimentos — o modelo só consultará a base AUVP, sem inventar respostas

### API Gemini (gratuita via Google AI Studio)
Use os arquivos `.txt` diretamente via [Google AI Studio](https://aistudio.google.com/) para construir agentes, chatbots ou análises sem custo adicional.

---

## 🔒 Segurança e Privacidade

- Credenciais OAuth nunca são subidas para o repositório
- Todo o conteúdo processado é de acesso público do YouTube
- Nenhuma API paga é necessária — o projeto foi projetado para ser **100% gratuito**

---

## 📄 Licença

Projeto interno AUVP. Todos os direitos reservados.
