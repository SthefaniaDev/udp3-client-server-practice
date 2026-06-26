# UDP3 - Cliente e Servidor com Sockets UDP

Este repositório contém uma prática de comunicação UDP utilizando **cliente e servidor em Python** com **sockets reais**.

O projeto demonstra o funcionamento do protocolo UDP e implementa mecanismos adicionais de confiabilidade, já que o UDP, por padrão, não garante entrega, ordem ou integridade dos pacotes.

## Objetivo da prática

Desenvolver uma aplicação cliente-servidor utilizando sockets UDP reais, demonstrando:

- Envio de mensagens via UDP;
- Recebimento de pacotes no servidor;
- Digitação manual de mensagens no cliente;
- Confirmação de recebimento com ACK;
- Verificação de integridade com checksum CRC32;
- Timeout;
- Retransmissão de pacotes;
- Controle de sequência alternando entre `0` e `1`;
- Detecção de pacotes corrompidos;
- Detecção de pacotes duplicados ou fora de ordem;
- Simulação de perda e corrupção de pacotes;
- Limite máximo de tentativas de envio.

## Tecnologias utilizadas

- Python
- Sockets UDP
- JSON
- CRC32
- Dataclasses

## Estrutura do projeto

```text
udp3-client-server-practice/
│
├── client.py
├── server.py
└── README.md
```

## Descrição dos arquivos

### `client.py`

Arquivo responsável por executar o cliente UDP.

O cliente realiza as seguintes funções:

- Exibe um menu interativo no terminal;
- Permite que o usuário digite mensagens manualmente;
- Cria pacotes de dados do tipo `DATA`;
- Envia mensagens para o servidor usando socket UDP real;
- Aguarda o ACK correspondente;
- Retransmite pacotes em caso de timeout;
- Verifica se o ACK recebido está corrompido;
- Alterna o número de sequência entre `0` e `1`;
- Simula perda e corrupção de pacotes DATA;
- Limita a quantidade de tentativas para evitar loop infinito.

### `server.py`

Arquivo responsável por executar o servidor UDP.

O servidor realiza as seguintes funções:

- Aguarda pacotes enviados pelo cliente;
- Recebe mensagens por meio de socket UDP real;
- Decodifica os pacotes recebidos em formato JSON;
- Verifica se o pacote está corrompido usando checksum CRC32;
- Entrega mensagens válidas à aplicação;
- Detecta pacotes duplicados ou fora de ordem;
- Envia ACKs de confirmação para o cliente;
- Simula perda e corrupção de ACKs;
- Exibe logs formatados para facilitar a visualização da prática.

## Como executar o projeto

Não é necessário utilizar dois computadores.

O cliente e o servidor podem ser executados na mesma máquina usando o endereço `127.0.0.1`, que representa o próprio computador.

## Passo a passo de execução

### 1. Clone o repositório

```bash
git clone https://github.com/SEU-USUARIO/udp3-client-server-practice.git
```

### 2. Acesse a pasta do projeto

```bash
cd udp3-client-server-practice
```

### 3. Execute o servidor

Abra um terminal e execute:

```bash
python server.py
```

Ou, dependendo da configuração do Python no seu sistema:

```bash
python3 server.py
```

No Windows, também pode ser:

```bash
py server.py
```

O servidor ficará aguardando pacotes UDP.

### 4. Execute o cliente

Abra outro terminal na mesma pasta e execute:

```bash
python client.py
```

Ou:

```bash
python3 client.py
```

No Windows, também pode ser:

```bash
py client.py
```

O cliente exibirá um menu interativo no terminal.

## Menu do cliente

Ao executar o cliente, será exibido um menu semelhante a este:

```text
========================================================================
||                    CLIENTE UDP3 - MENU PRINCIPAL                    ||
========================================================================
|| 1 || Enviar uma mensagem
|| 2 || Ver configurações do cliente
|| 3 || Explicar funcionamento da prática
|| 0 || Encerrar cliente
========================================================================
```

### Opção 1 - Enviar uma mensagem

Permite digitar uma mensagem manualmente e enviá-la ao servidor.

### Opção 2 - Ver configurações do cliente

Mostra as configurações principais da prática, como:

- IP do servidor;
- Porta;
- Tamanho do buffer;
- Timeout;
- Taxa de perda simulada;
- Taxa de corrupção simulada;
- Protocolo utilizado.

### Opção 3 - Explicar funcionamento da prática

Exibe uma explicação resumida sobre o funcionamento da comunicação UDP e dos mecanismos de confiabilidade implementados.

### Opção 0 - Encerrar cliente

Finaliza a execução do cliente e fecha o socket UDP.

## Funcionamento da comunicação

A comunicação acontece da seguinte forma:

1. O usuário digita uma mensagem no cliente.
2. O cliente cria um pacote do tipo `DATA`.
3. O pacote recebe um número de sequência, que pode ser `0` ou `1`.
4. O cliente calcula o checksum CRC32 do pacote.
5. O cliente envia o pacote ao servidor usando socket UDP real.
6. O servidor recebe o datagrama UDP.
7. O servidor decodifica o pacote.
8. O servidor verifica o checksum.
9. Se o pacote estiver correto, a mensagem é entregue à aplicação.
10. O servidor envia um ACK confirmando o recebimento.
11. O cliente recebe o ACK.
12. Se o ACK estiver correto, o cliente considera a mensagem enviada com sucesso.
13. O número de sequência é alternado para o próximo envio.
14. Se o ACK não chegar dentro do tempo limite, o cliente retransmite o pacote.
15. Se a mensagem não for confirmada após o limite de tentativas, o envio é considerado sem sucesso.

## Mecanismos de confiabilidade implementados

Como o UDP não garante confiabilidade por padrão, foram adicionados mecanismos para controlar melhor a comunicação.

### Checksum CRC32

O checksum é utilizado para verificar se o pacote foi corrompido durante a transmissão.

Neste projeto, o checksum é calculado usando CRC32 com base nos seguintes campos:

- Tipo do pacote;
- Número de sequência;
- Número de ACK;
- Conteúdo da mensagem.

Se algum dado for alterado sem recalcular o checksum, o receptor identifica que o pacote está corrompido.

### ACK

O ACK é uma confirmação enviada pelo servidor ao cliente.

Quando o servidor recebe corretamente um pacote `DATA`, ele envia um pacote `ACK` informando qual sequência foi recebida.

Exemplo:

```text
ACK 0
ACK 1
```

### Timeout

O cliente espera o ACK por um tempo definido.

Se o ACK não chegar dentro desse tempo, ocorre timeout.

### Retransmissão

Quando ocorre timeout, o cliente retransmite o mesmo pacote.

Isso permite que a mensagem seja reenviada caso o pacote ou o ACK seja perdido.

### Número de sequência

Os pacotes usam número de sequência alternando entre `0` e `1`.

Esse controle permite identificar:

- Pacotes duplicados;
- Pacotes fora de ordem;
- ACKs inesperados;
- Retransmissões de mensagens já recebidas.

### Limite de tentativas

O cliente possui um limite máximo de tentativas para evitar que o envio fique em loop infinito.

Se a mensagem não for confirmada após o número máximo de tentativas, o cliente considera o envio como não confirmado.

Exemplo:

```text
========================================================================
||                         ENVIO NÃO CONFIRMADO                        ||
========================================================================
[ERRO] A mensagem não foi confirmada após 5 tentativa(s).
[ERRO] Envio considerado sem sucesso.
[PROTOCOLO] O cliente desistiu dessa mensagem para evitar loop infinito.
```

## Simulação de falhas

Mesmo usando sockets UDP reais, em testes locais é raro ocorrer perda de pacotes naturalmente.

Por isso, o projeto simula alguns problemas de rede, como:

- Perda de pacotes DATA;
- Corrupção de pacotes DATA;
- Perda de ACKs;
- Corrupção de ACKs.

Essas simulações ajudam a visualizar como o protocolo reage a falhas.

## Situações demonstradas pela prática

### Envio com sucesso

Quando o pacote chega corretamente ao servidor e o ACK retorna corretamente ao cliente, a mensagem é considerada enviada com sucesso.

Exemplo no cliente:

```text
[UDP] Pacote DATA enviado via socket UDP real.
[CHECKSUM] Checksum válido. O ACK chegou íntegro.
[CLIENTE] ACK recebido corretamente.
[RESULTADO] Mensagem enviada com sucesso.
```

Exemplo no servidor:

```text
========================================================================
||                    MENSAGEM RECEBIDA E ENTREGUE                    ||
========================================================================
[APLICAÇÃO] Mensagem enviada pelo cliente: 'Olá servidor'
```

### Pacote perdido

O pacote pode ser perdido antes de chegar ao servidor.

Exemplo:

```text
[SIMULAÇÃO] Pacote DATA perdido antes de ser enviado.
[TIMEOUT] ACK não chegou dentro do tempo limite.
[PROTOCOLO] Retransmitindo o mesmo pacote.
```

### Pacote corrompido

O pacote pode chegar alterado ao servidor.

Exemplo:

```text
[SIMULAÇÃO] Pacote DATA corrompido antes do envio.
[CHECKSUM] Checksum inválido.
[SERVIDOR] Pacote descartado por corrupção.
```

### ACK perdido

O servidor pode receber a mensagem corretamente, mas o ACK pode ser perdido antes de chegar ao cliente.

Exemplo:

```text
[SIMULAÇÃO] ACK perdido antes de ser enviado.
[TIMEOUT] ACK não chegou dentro do tempo limite.
[PROTOCOLO] Retransmitindo o mesmo pacote.
```

### ACK corrompido

O ACK pode chegar alterado ao cliente.

Exemplo:

```text
[CHECKSUM] Checksum inválido. O ACK foi alterado ou chegou corrompido.
[CLIENTE] ACK descartado por corrupção.
```

### Pacote duplicado

Quando o cliente retransmite uma mensagem que o servidor já recebeu, o servidor identifica a duplicidade e não entrega a mesma mensagem novamente.

Exemplo:

```text
[SERVIDOR] Pacote duplicado ou fora de ordem detectado.
[APLICAÇÃO] A mensagem não será entregue novamente.
[SERVIDOR] Reenviando ACK para confirmar o último pacote válido.
```

## Endereço IP utilizado

Por padrão, o cliente está configurado para enviar mensagens para:

```text
127.0.0.1
```

Esse endereço representa o próprio computador.

Por isso, o cliente e o servidor podem ser executados na mesma máquina.

## Executando em dois computadores

Caso deseje executar o servidor em um computador e o cliente em outro, os dois computadores precisam estar na mesma rede.

No computador do servidor, descubra o endereço IPv4 usando:

```bash
ipconfig
```

Depois, no arquivo `client.py`, altere:

```python
SERVER_HOST = "127.0.0.1"
```

Para o IP do computador onde o servidor está rodando.

Exemplo:

```python
SERVER_HOST = "192.168.0.15"
```

O servidor pode continuar usando:

```python
HOST = "0.0.0.0"
```

## Diferença entre TCP e UDP

O TCP oferece confiabilidade automaticamente, incluindo:

- Estabelecimento de conexão;
- Confirmação de recebimento;
- Controle de ordem;
- Retransmissão;
- Controle de fluxo.

O UDP não oferece essas garantias por padrão.

Por isso, nesta prática, foram implementados manualmente alguns mecanismos de confiabilidade sobre UDP.

## Por que usar UDP?

O UDP é um protocolo simples e rápido.

Ele é usado em aplicações em que velocidade é mais importante do que confiabilidade automática, como:

- Jogos online;
- Chamadas de voz;
- Transmissões ao vivo;
- DNS;
- Aplicações em tempo real.

Quando a aplicação precisa de maior controle sobre a entrega das mensagens, é possível implementar mecanismos próprios, como foi feito neste projeto.

## Roteiro sugerido para demonstração

Para apresentar a prática, siga este roteiro:

1. Abra o terminal do servidor.
2. Execute o arquivo `server.py`.
3. Mostre que o servidor está aguardando pacotes UDP.
4. Abra outro terminal.
5. Execute o arquivo `client.py`.
6. Mostre o menu interativo do cliente.
7. Escolha a opção `1`.
8. Digite uma mensagem.
9. Mostre o cliente enviando o pacote.
10. Mostre o servidor recebendo a mensagem.
11. Mostre o servidor verificando o checksum.
12. Mostre o servidor enviando o ACK.
13. Mostre o cliente recebendo o ACK.
14. Repita o envio até aparecer uma situação de perda, corrupção, timeout ou retransmissão.
15. Mostre que o servidor não entrega mensagens duplicadas.
16. Mostre que o cliente possui limite de tentativas.
17. Encerre o cliente pelo menu.
18. Encerre o servidor com `CTRL + C`.

## Exemplo de explicação oral

Esta prática implementa uma comunicação UDP real entre cliente e servidor usando sockets em Python.

Como o UDP não garante entrega, ordem ou integridade dos dados, foram adicionados mecanismos de confiabilidade, como checksum CRC32, ACK, timeout, retransmissão, controle de sequência e limite de tentativas.

O cliente permite digitar mensagens manualmente por meio de um menu interativo. O servidor recebe os pacotes, verifica sua integridade, entrega as mensagens válidas e responde com ACK.

Durante a execução, o sistema também simula perda e corrupção de pacotes e ACKs, demonstrando como a aplicação reage a falhas comuns em comunicações não confiáveis.

## Conclusão

Esta prática demonstra a comunicação entre cliente e servidor utilizando sockets UDP reais em Python.

Além disso, o projeto implementa recursos de confiabilidade sobre UDP, permitindo compreender melhor as limitações do protocolo e como uma aplicação pode tratar perda, corrupção, duplicidade e ausência de confirmação.
