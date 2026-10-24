# Music Downloader V1.3.1 — correção de prévia e corte

Atualize `main.py` no GitHub com o arquivo deste pacote. Mantenha `requirements-studio.txt` e `.github/workflows/build-windows.yml` atualizados. Commit na branch main inicia a compilação.

**Prévia**: usa FFmpeg incluído no pacote para gerar um WAV PCM temporário e a API de áudio do Windows (`winsound`) para reproduzir até 30 segundos. Não requer FFplay. Digite Início e Fim e clique Prévia.

**Corte**: marque 'Ativar corte', preencha Início e Fim no formato MM:SS e inicie a conversão. O arquivo original é preservado.

A prévia é limitada a 30 segundos; o corte exportado usa o intervalo completo. Esta versão não foi executada em Windows neste ambiente e precisa ser testada.
