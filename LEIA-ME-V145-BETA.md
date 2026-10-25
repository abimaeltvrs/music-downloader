# DJ Tavares Music Downloader V1.4.5 Beta

- Playlists: `ignoreerrors=True` permite continuar quando um item não está disponível.
- Cria `RELATORIO_FALHAS_*.txt` na pasta de destino com títulos e links das entradas não encontradas, quando disponíveis, e mensagens de erro.
- Exibe resumo ao finalizar e permite abrir o relatório.
- Spotify: identifica faixa/artista via oEmbed e oferece pesquisa no YouTube; o usuário escolhe a versão e copia o link. Não extrai áudio do Spotify nem ignora permissões de download.
- Preserva organização de pastas e biblioteca da V1.4.4.

**Limitações:** Alguns vídeos privados não expõem título; nesses casos o relatório mostra o identificador ou posição. O relatório depende da listagem que o YouTube disponibiliza. Se a listagem falhar, inclui os erros capturados. Testar no Windows após compilar.
