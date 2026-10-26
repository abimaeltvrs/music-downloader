# TavaresMusic Studio Pro V1.6.2 Beta

## Correções
- Tela Links: controles redundantes unificados em Iniciar download, Pausar/Retomar e Parar.
- Iniciar download prioriza a fila quando houver links adicionados; sem fila, usa a URL atual.
- Pausa e parada solicitam conclusão do item atual, respeitando o processamento já existente.
- Biblioteca: 'Abrir local' revela o arquivo no Explorador do Windows em vez de executá-lo.
- Biblioteca: player integrado com Ouvir, Play, Pause, Stop, barra de progresso e tempo, usando pygame.
- Controles desabilitados quando não há download em andamento.
- Identidade de versão e workflow atualizados.

## Testes
- Verificação de sintaxe Python efetuada.
- Necessário compilar no GitHub Actions e validar a execução no Windows, incluindo seek de arquivos WAV/FLAC e playlists longas.

## Observações
- O player suporta os formatos decodificados pelo pygame/SDL_mixer; compatibilidade de busca (seek) varia conforme o formato.
- Nenhum arquivo original é excluído ao abrir local ou reproduzir.
