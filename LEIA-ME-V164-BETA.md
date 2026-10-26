# V1.6.4 Beta — MP4 para Windows

- Prioriza H.264 + AAC no yt-dlp; quando indisponível, converte com FFmpeg.
- Verifica codecs com FFprobe antes de registrar como concluído.
- MP4 sem vídeo/áudio ou com falha de conversão é renomeado `.incompativel` para não ser exibido como download concluído.
- Reprodução de vídeo usa FFplay em janela própria (incluído no workflow).
- Compilação e execução real no Windows devem ser validadas após GitHub Actions.
