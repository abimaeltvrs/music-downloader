# V1.5.4.1 — correção de recursos visuais

A captura da V1.5.4 mostrou que logo, ícones e cabeçalho eram substituídos por texto.

## Correção aplicada
- Imagens da logo, seis ícones e cabeçalho **embutidas em `embedded_ui.py`**. Não dependem mais da localização de `assets` em `_internal` do PyInstaller.
- O carregamento usa os bytes embutidos e preserva referências a `CTkImage`.
- Erros dos ícones são exibidos ao usuário em vez de apenas escondidos.
- Validação das imagens embutidas no GitHub Actions.
- Nenhuma alteração nas rotinas de conversão, download, playlist ou editor.

## Atenção
Esta versão corrige o carregamento das imagens e melhora o cabeçalho, mas **não é uma reprodução exata do mockup**. A execução no Windows deve ser validada por captura de tela. Baixe e extraia o artefato inteiro do GitHub Actions; não copie somente o .exe da pasta.
