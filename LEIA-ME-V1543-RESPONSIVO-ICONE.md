# V1.5.4.3 — Layout responsivo e ícone Windows

- Cabeçalho acompanha a largura da janela ao maximizar e restaurar.
- Ícone Windows regenerado com resoluções 16–256 px.
- Identidade AppUserModelID definida antes da criação da janela no Windows.
- Ícone da janela carregado com iconbitmap e iconphoto; ícone do executável incorporado no PyInstaller.
- Funcionalidades do aplicativo preservadas.

## Teste

Compile no GitHub Actions e baixe o artefato **completo**. Extraia toda a pasta e execute o EXE dentro dela. Verifique o banner com a janela normal e maximizada, e os ícones do EXE, da barra de tarefas e do Alt+Tab. Se o Explorer continuar exibindo o ícone antigo, pode ser cache de ícones do Windows: teste renomeando o EXE ou reiniciando o Explorer.

**Limitação:** testes de sintaxe e recursos realizados, mas não foi possível executar o Windows nesta sessão.
