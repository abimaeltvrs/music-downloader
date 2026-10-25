# DJ Tavares V1.4.7 Beta - relatórios sob demanda em PDF

- Pausar e parar preservam as músicas concluídas.
- Ao concluir/interromper, escolher **Relatório completo (falhas + pendentes)**, **Somente erros ocorridos** ou **Não gerar relatório**.
- PDFs são gerados apenas mediante escolha e ficam em `%LOCALAPPDATA%\MusicDownloader\Relatorios`, nunca na pasta das músicas.
- Não são gerados arquivos TXT automáticos.
- Os arquivos pendentes não são classificados como falhas quando a playlist é interrompida antes de serem tentados, sempre que for possível distinguir pelo histórico de eventos do yt-dlp.
- Algumas falhas de vídeos privados podem não revelar título ou índice; o relatório apresenta os dados disponíveis.
- Recursos de conversão, cortes, Spotify (pesquisa no YouTube) e download existentes foram preservados.

**Nota:** teste a compilação Windows e o comportamento de uma playlist real antes de considerar a versão estável.
