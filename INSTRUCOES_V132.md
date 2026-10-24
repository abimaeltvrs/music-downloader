# Music Downloader V1.3.2 — atualização GitHub

Atualize no repositório os arquivos `main.py`, `requirements-studio.txt` e `.github/workflows/build-windows.yml` (preservando a pasta `.github`). Faça commit e baixe o artefato `MusicDownloader-Windows-V1.3.2` em Actions.

Mudanças: inclui NumPy explicitamente no empacotamento e valida importações no build; registra arquivos baixados por link no Histórico/Biblioteca; adiciona caixa de seleção de playlist; mantém MP3, WAV e MP4. Para playlist, selecione a opção antes de baixar. Vídeos longos dependem de espaço livre, rede e limites da fonte. A saída MP4 tenta priorizar formatos MP4 compatíveis; nem todo site oferece os mesmos formatos.

**Atenção:** o executável ainda precisa ser testado no Windows. Se o Studio DJ continuar falhando, envie o erro completo da nova compilação/execução. O primeiro uso do Demucs pode baixar modelos grandes e levar vários minutos. Apenas faça downloads quando autorizados.
