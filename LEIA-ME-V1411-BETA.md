# DJ Tavares Music Downloader V1.4.11 Beta

## Correção de arquivos temporários

- Cada transferência usa pasta temporária exclusiva em `%LOCALAPPDATA%\MusicDownloader\transfer_tmp\<id>`.
- yt-dlp salva arquivos `.part`, fragmentos e intermediários na pasta temporária, não na pasta de músicas.
- Ao terminar ou interromper, remove apenas a pasta temporária dessa operação.
- Preserva MP3/MP4 finalizados, a biblioteca, a organização das playlists e o relatório PDF.
- O relatório continua opcional e fica em `%LOCALAPPDATA%\MusicDownloader\Relatorios`.

## Atenção

Arquivos `.part` de versões anteriores que já estejam em pastas de músicas não são apagados automaticamente para evitar exclusão indevida. Se não houver downloads em andamento e não desejar retomá-los, exclua-os manualmente.

A pausa e o cancelamento podem aguardar o yt-dlp liberar o arquivo atual. Código verificado por compilação sintática; necessário testar o executável no Windows.
