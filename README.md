# Music Downloader V1.2 — Windows

Aplicativo desktop preto e azul para conversão, corte e separação por IA de arquivos locais próprios ou autorizados. Não baixa vídeos de plataformas.

## Instalar no Windows
1. Instale Python 3.11 (64 bits) e marque **Add Python to PATH**. Demucs/PyTorch podem não funcionar em versões muito novas do Python.
2. Instale FFmpeg (incluindo FFplay para prévia) e adicione ao PATH.
3. Abra PowerShell nesta pasta e execute:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-studio.txt
python main.py
```

Se a ativação do ambiente virtual for bloqueada, execute `.venv\Scripts\python.exe -m pip install -r requirements-studio.txt` e `.venv\Scripts\python.exe main.py`.

## Studio DJ
- **Somente voz**: exporta `vocals` (acapella).
- **Somente instrumental**: exporta `no_vocals`.
- **Voz + Instrumental**: exporta os dois.
- **4 stems**: `vocals`, `drums`, `bass` e `other`.
- Formatos WAV ou MP3 (320 kbps).
- Corte opcional antes da separação: início e fim em MM:SS.
- Cada música cria uma pasta própria na pasta de destino.
- O histórico e a biblioteca mostram os arquivos gerados.

O modelo Demucs é baixado automaticamente na primeira execução (internet necessária). As próximas separações podem funcionar offline com o modelo em cache. A velocidade depende do hardware; esta implementação usa o dispositivo padrão do Demucs (normalmente CPU). A separação pode conter artefatos e vazamentos entre instrumentos.

## Gerar EXE

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name MusicDownloader --collect-all customtkinter --collect-all demucs --collect-all torch main.py
```

**Atenção:** O empacotamento de Demucs/PyTorch é pesado e pode precisar de ajustes no computador de destino. O EXE não está pré-compilado nem testado neste pacote; para a primeira execução, use Python. FFmpeg continua sendo uma dependência externa e o modelo de IA pode ser baixado no primeiro uso.

## Dependências e direitos
Demucs é software de terceiros; verifique licenças das dependências e dos modelos antes de redistribuir. Use apenas conteúdo cujo processamento seja autorizado.


## V1.4.12 Beta
Consulte LEIA-ME-V1412-BETA.md para a nova lógica de pausa e parada entre faixas.
