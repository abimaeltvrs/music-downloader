# Music Downloader V1.2.2 — corrigir FFmpeg

1. No GitHub, abra `main.py`, clique no lápis e substitua seu conteúdo pelo `main.py` deste pacote; salve com Commit changes.
2. Abra `.github/workflows/build-windows.yml`, clique no lápis, substitua o conteúdo pelo arquivo homônimo deste pacote e salve.
3. Aguarde Actions > Build Music Downloader Windows ficar verde.
4. Em Artifacts, baixe `MusicDownloader-Windows-V1.2.2`, extraia o ZIP inteiro e execute `MusicDownloader.exe`.
5. Confirme que `_internal/bin/ffmpeg.exe`, `ffprobe.exe` e `ffplay.exe` existem. Teste um arquivo local autorizado.

Se falhar, abra a execução no Actions e envie o log da etapa vermelha. O download de FFmpeg depende do servidor externo. O modelo Demucs pode requerer download na primeira utilização.
