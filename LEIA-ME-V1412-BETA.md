# DJ Tavares V1.4.12 Beta — pausa e parada entre músicas

- Pausar: termina o download e a conversão da faixa atual antes de aguardar. Retomar continua a próxima faixa.
- Parar: termina a faixa atual, não inicia outra e oferece relatório PDF completo, somente erros ou nenhum.
- Playlists são processadas uma faixa por vez para permitir esse controle.
- Temporários isolados por operação são removidos no encerramento do worker, depois de o relatório ser disponibilizado.
- Músicas baixadas são preservadas.

**Teste no Windows**: esta alteração passou por validação de sintaxe, mas não foi testada com download real. Em casos em que a fonte não fornece a lista da playlist, o fallback usa o fluxo anterior.
