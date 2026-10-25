# DJ Tavares Music Downloader V1.4.2 Beta

Atualização baseada na V1.4.1. Preserve a pasta `assets` e `.github/workflows` ao enviar ao GitHub.

## Incluído
- Identidade visual DJ Tavares: logo ampliada na barra lateral, destaque da aba ativa, ícone na janela e no executável.
- Downloads em lote: cole vários links (um por linha), clique em Adicionar à fila e Iniciar fila. Processamento sequencial, progresso por item concluído e pausa/cancelamento entre itens.
- Editor de ondas: zoom +/- e navegação horizontal com a roda do mouse; botão direito reposiciona o cursor (a reprodução para e pode ser reiniciada dali).
- Limpar registros do Histórico/Biblioteca com confirmação, sem apagar arquivos físicos. Ambas as abas compartilham o mesmo cadastro, então a limpeza afeta ambas.
- Downloads MP3/MP4 existentes e Studio DJ preservados.

## Limitações conhecidas
- A pausa/cancelamento da fila só ocorre entre downloads, não durante o item em andamento.
- Spotify identifica metadados, mas não baixa áudio protegido.
- A aceleração NVIDIA, prévia independente dos stems e reformulação total do Studio DJ não estão nesta beta.
- Ainda não houve teste no Windows; valide a compilação do GitHub Actions e as funções no executável.
