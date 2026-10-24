# Music Downloader V1.2.1 — FFmpeg portátil

1. No GitHub, envie os arquivos deste ZIP para a **raiz** do repositório, preservando `.github/workflows/build-windows.yml`.
2. Confirme a substituição do `main.py` e do workflow.
3. Após o commit na branch `main`, abra **Actions** e aguarde a compilação.
4. Em **Artifacts**, baixe `MusicDownloader-Windows-V1.2.1`.
5. Extraia o ZIP inteiro e execute `MusicDownloader.exe`. Não mova somente o `.exe` para fora da pasta.

**Mudanças:** corrige `CTkCheckBox(progress_color=...)` e empacota `ffmpeg.exe`, `ffprobe.exe` e `ffplay.exe` em `bin` dentro do aplicativo. O programa adiciona essa pasta ao PATH somente durante sua execução.

**Nota:** compilação verde não garante execução correta. Teste conversão e separação no Windows; a primeira execução do Demucs pode baixar modelos e exigir conexão.
