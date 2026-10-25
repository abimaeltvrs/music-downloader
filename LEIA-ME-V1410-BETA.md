# DJ Tavares Music Downloader — V1.4.10 Beta

Correção do cancelamento de playlists:
- Ao interromper, o programa não inicia novos itens após o ponto de controle do yt-dlp.
- Após a saída do mecanismo de download, remove apenas os arquivos temporários `.part`, `.part-frag` e `.ytdl` novos identificados nesta operação; temporários preexistentes são preservados.
- MP3/MP4 já finalizados não são excluídos.
- O relatório PDF mantém baixadas, falhas e pendentes.

**Limite:** o cancelamento depende dos callbacks de progresso do yt-dlp e pode não ser instantâneo. Se o processo for encerrado à força, não há oportunidade de limpeza. A compilação Windows e os downloads reais devem ser testados.
