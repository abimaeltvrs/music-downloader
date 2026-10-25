# DJ Tavares V1.4.6 Beta

- Playlist: botões **Pausar/Retomar** e **Parar e gerar relatório**.
- Pausa ocorre no próximo callback de progresso do yt-dlp; cancelamento pode deixar um arquivo parcial `.part`, que não é contado como concluído.
- Relatório `RELATORIO_PLAYLIST_*.txt` sempre é salvo na pasta de destino, com arquivos presentes, falhas e itens não tentados após interrupção.
- O número de falhas é estimado pela listagem do YouTube e pelos itens processados; vídeos privados podem não expor metadados.
- Melhorias visuais: maior janela, barra lateral compacta, paleta azul, painel Links rolável, botões dedicados de controle e indicador de andamento.
- Spotify: mantém identificação e pesquisa no YouTube; downloads do Spotify não são extraídos.
- Necessário validar o build e testar playlists reais no Windows.
