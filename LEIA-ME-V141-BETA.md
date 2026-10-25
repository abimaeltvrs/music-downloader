# DJ Tavares V1.4.1 Beta — correções parciais testáveis

Atualize o repositório com todos os arquivos deste ZIP, preservando a estrutura `.github/workflows` e `assets`.

## Incluído
- Editor visual: player e reprodução da seleção, cursor de reprodução, posicionamento por botão direito do mouse, fade-in/fade-out dentro da janela.
- Links: opções de bitrate MP3 128/192/256/320 e teto de resolução MP4 360/480/720/1080/melhor disponível; resultado depende do material de origem.
- Spotify: identifica título via oEmbed, mas **não baixa áudio protegido** nem faz busca automática de fonte alternativa.
- Studio DJ: modo rápido/alta qualidade Demucs (shifts e overlap) e acesso ao editor visual.
- Marca DJ Tavares e assets existentes preservados.

## Ainda pendente
- Reprodução de stems individuais dentro do Studio, suporte CUDA NVIDIA empacotado, integração de busca autorizada a partir do Spotify e refinamento visual completo conforme o mockup.
- Validação do executável em Windows; aqui foi feita somente validação de sintaxe.

## Testes
1. GitHub Actions deve ficar verde.
2. Abrir Editor visual, reproduzir e ouvir seleção, aplicar fades e converter.
3. Baixar conteúdo autorizado em MP3 e MP4, conferir limites de qualidade.
4. Studio DJ em ambos modos e verificar arquivos gerados.
