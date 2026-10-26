# TavaresMusic Studio Pro V1.6.1 Beta — implementação incremental

## Implementado nesta entrega
- Nova aba **DJ Playlist** com importação de arquivos, pastas e músicas do histórico; lista editável e reordenação manual.
- Projetos virtuais salvos localmente e recuperáveis; exportação de cópias numeradas, M3U8 e PDF, sem alterar originais.
- Análise opcional de BPM, tonalidade aproximada/Camelot, energia e gênero via librosa e mutagen. A análise é estimativa e depende da qualidade do áudio.
- Em **Links**, botão para consultar playlist antes do download; janela com busca, seleção individual, selecionar/desmarcar todas. Ao confirmar, o download usa somente a seleção.
- Progresso individual de download com percentual, velocidade e ETA quando disponibilizados pelo yt-dlp, além das etapas de finalização.

## Limitações e próximos passos
- **Não é a V1.6.0 completa**: player integrado da Biblioteca, mixer e editor avançado ainda pendentes.
- O gênero é obtido de metadados; classificação de gênero por IA não foi implementada.
- Organização harmônica combinada (pontuação de transições) ainda não implementada; disponível ordenação por tom/BPM/energia.
- Prévia da playlist depende de acesso à origem e disponibilidade dos metadados.
- Build Windows pelo GitHub Actions deve ser validada em máquina real. Librosa aumenta significativamente o tamanho e o tempo de compilação.
- Não exclua a instalação estável antes de validar esta beta.
