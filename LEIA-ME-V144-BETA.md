# DJ Tavares V1.4.4 Beta

## Alterações
- Playlists: salvar diretamente ou em subpasta; campo de nome vazio usa título real da playlist; nome personalizado também funciona.
- Registro: registra caminhos físicos existentes e evita relistar arquivos antigos como downloads novos.
- Spotify: identifica faixa via oEmbed e oferece pesquisa no Bandcamp; compra/download só na fonte, quando autorizado. Não extrai DRM e não promete MP3 do Spotify.
- Preserva downloads do YouTube, conversor, editor, Studio DJ e assets.

## Instalação
Envie o conteúdo desta pasta ao repositório GitHub, preservando .github/workflows e assets. Faça commit e baixe o artifact da aba Actions.

## Testes
1. Em Links, escolha pasta de destino real no Windows.
2. Ative playlist e subpasta, deixe nome vazio para título automático ou preencha Funk 2026.
3. Baixe playlist autorizada; confira arquivos reais no Explorador e caminhos da Biblioteca.
4. Teste modo direto com outra playlist.
5. Cole link Spotify: confirme metadados e abertura de pesquisa em loja autorizada.

Sintaxe Python verificada; compilação Windows e comportamento em rede ainda exigem testes.
