# Music Downloader — começar pelo GitHub

1. Abra o repositório no GitHub.
2. Clique em **Add file → Upload files** e envie **o conteúdo desta pasta**, incluindo a pasta oculta `.github` (não envie o ZIP sem extrair).
3. Confirme que `main.py` e `.github/workflows/build-windows.yml` aparecem na raiz do repositório.
4. Clique em **Commit changes**. Se o branch padrão não for `main`, ajuste o nome no arquivo de workflow ou execute manualmente.
5. Abra **Actions → Compilar Music Downloader Windows → Run workflow** (se necessário, habilite Actions no repositório).
6. Aguarde o processo terminar. Abra a execução concluída e baixe o artefato **MusicDownloader-Windows**.
7. Extraia os ZIPs e execute `MusicDownloader.exe` dentro da pasta `MusicDownloader`. Mantenha os arquivos da pasta juntos.

**Observações:** o programa trabalha com arquivos locais próprios ou autorizados; não baixa áudio de YouTube. O pacote compilado é grande devido ao PyTorch/Demucs. Na primeira separação, o modelo de IA pode precisar ser baixado. O GitHub Actions depende de acesso à internet e pode falhar por alterações de dependências, limites de conta ou empacotamento; o executável ainda precisa ser validado em um Windows real. Windows SmartScreen pode alertar sobre executáveis não assinados. Confira o log da aba Actions caso a compilação falhe.
