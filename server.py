from dataclasses import dataclass, asdict
import json
import random
import socket
import zlib
from copy import deepcopy

# ============================================================
# SERVIDOR UDP3 - STOP-AND-WAIT COM SOCKET UDP REAL
# ============================================================

HOST = "0.0.0.0"
PORT = 5000
BUFFER_SIZE = 4096

# Simulação de problemas no envio do ACK pelo servidor.
# Em localhost, o UDP quase nunca perde pacotes naturalmente.
ACK_LOSS_RATE = 0.20
ACK_CORRUPTION_RATE = 0.15

# Simula perda do pacote DATA após chegar ao servidor
SERVER_DATA_DROP_RATE = 0.20

random_generator = random.Random(7)

LINE_SIZE = 72


# ============================================================
# ESTRUTURA DO PACOTE
# ============================================================

@dataclass
class Packet:
    kind: str
    seq: int
    ack: int
    payload: str
    checksum: int


# ============================================================
# FUNÇÕES AUXILIARES DE FORMATAÇÃO
# ============================================================

def separator(symbol: str = "=") -> None:
    print(symbol * LINE_SIZE)


def title(text: str) -> None:
    print()
    separator("=")
    print(f"|| {text.center(LINE_SIZE - 6)} ||")
    separator("=")


def subtitle(text: str) -> None:
    print()
    separator("-")
    print(f"|| {text}")
    separator("-")


def log(section: str, message: str) -> None:
    """
    Exibe mensagens padronizadas para facilitar a apresentação da prática.
    """
    print(f"[{section}] {message}")


def show_received_packet(packet: Packet, client_address: tuple[str, int]) -> None:
    """
    Exibe de forma organizada as informações do pacote recebido.
    """
    subtitle("PACOTE DATA RECEBIDO DO CLIENTE")

    print(f"|| Cliente ..................... || {client_address[0]}:{client_address[1]}")
    print(f"|| Tipo do pacote .............. || {packet.kind}")
    print(f"|| Número de sequência ......... || {packet.seq}")
    print(f"|| ACK ......................... || {packet.ack}")
    print(f"|| Mensagem recebida ........... || {packet.payload!r}")
    print(f"|| Checksum recebido ........... || {packet.checksum}")

    separator("-")


def show_delivered_messages(messages: list[str]) -> None:
    """
    Exibe todas as mensagens que já foram entregues à aplicação.
    """
    subtitle("MENSAGENS ENTREGUES À APLICAÇÃO")

    if not messages:
        print("|| Nenhuma mensagem foi entregue ainda.")
    else:
        for index, message in enumerate(messages, start=1):
            print(f"|| {index:02d} || {message}")

    separator("-")


def show_server_status(expected_seq: int, last_valid_ack: int) -> None:
    """
    Exibe o estado atual do protocolo no servidor.
    """
    subtitle("ESTADO ATUAL DO SERVIDOR")

    print(f"|| Sequência esperada agora .... || {expected_seq}")
    print(f"|| Último ACK válido ........... || {last_valid_ack}")
    print(f"|| Protocolo ................... || UDP + Stop-and-Wait")
    print(f"|| Controle de sequência ....... || Alternância entre 0 e 1")

    separator("-")


def show_start_banner() -> None:
    """
    Exibe o banner inicial do servidor.
    """
    title("SERVIDOR UDP3 INICIADO")

    print(f"|| Endereço de escuta .......... || {HOST}")
    print(f"|| Porta ....................... || {PORT}")
    print(f"|| Buffer ...................... || {BUFFER_SIZE} bytes")
    print(f"|| Perda simulada de ACK ....... || {ACK_LOSS_RATE * 100:.0f}%")
    print(f"|| Corrupção simulada de ACK ... || {ACK_CORRUPTION_RATE * 100:.0f}%")
    print(f"|| Protocolo ................... || UDP + Stop-and-Wait")
    print(f"|| Sequência esperada inicial .. || 0")
    print()
    print("|| O servidor receberá pacotes DATA enviados pelo cliente.")
    print("|| Para cada pacote válido, o servidor enviará um ACK.")
    print("|| Pressione CTRL + C para encerrar o servidor.")

    separator("=")


def show_final_report(messages: list[str]) -> None:
    """
    Exibe o relatório final quando o servidor é encerrado.
    """
    title("SERVIDOR UDP3 ENCERRADO")

    print(f"|| Total de mensagens entregues || {len(messages)}")
    separator("-")

    if not messages:
        print("|| Nenhuma mensagem foi entregue à aplicação.")
    else:
        for index, message in enumerate(messages, start=1):
            print(f"|| {index:02d} || {message}")

    separator("=")


# ============================================================
# CHECKSUM
# ============================================================

def calculate_checksum(kind: str, seq: int, ack: int, payload: str) -> int:
    """
    Calcula o checksum CRC32 usando tipo, sequência, ACK e payload.
    """
    raw_data = f"{kind}|{seq}|{ack}|{payload}".encode("utf-8")
    return zlib.crc32(raw_data) & 0xFFFFFFFF


def make_ack_packet(ack: int) -> Packet:
    """
    Cria um pacote ACK para confirmar o recebimento de um DATA.
    """
    checksum = calculate_checksum("ACK", -1, ack, "")

    subtitle("CRIAÇÃO DO PACOTE ACK")

    log("SERVIDOR", f"Criando pacote ACK para confirmar a sequência {ack}.")
    log("ACK", "Tipo: ACK")
    log("ACK", "Seq: -1")
    log("ACK", f"Ack: {ack}")
    log("ACK", "Payload: ''")
    log("CHECKSUM", f"Checksum calculado com CRC32: {checksum}")

    return Packet(
        kind="ACK",
        seq=-1,
        ack=ack,
        payload="",
        checksum=checksum
    )


def is_corrupt(packet: Packet) -> bool:
    """
    Verifica se o pacote recebido foi corrompido.
    """
    expected_checksum = calculate_checksum(
        packet.kind,
        packet.seq,
        packet.ack,
        packet.payload
    )

    if packet.checksum != expected_checksum:
        log("CHECKSUM", "Checksum inválido.")
        log("CHECKSUM", "O pacote foi alterado ou chegou corrompido.")
        log("CHECKSUM", f"Checksum recebido: {packet.checksum}")
        log("CHECKSUM", f"Checksum esperado: {expected_checksum}")
        return True

    log("CHECKSUM", "Checksum válido. O pacote chegou íntegro.")
    return False


# ============================================================
# SERIALIZAÇÃO
# ============================================================

def encode_packet(packet: Packet) -> bytes:
    """
    Converte o pacote para JSON em bytes antes do envio pelo UDP.
    """
    json_packet = json.dumps(asdict(packet))
    return json_packet.encode("utf-8")


def decode_packet(data: bytes) -> Packet:
    """
    Converte bytes recebidos pelo socket UDP em um objeto Packet.
    """
    json_packet = data.decode("utf-8")
    packet_dict = json.loads(json_packet)
    return Packet(**packet_dict)


# ============================================================
# SIMULAÇÃO DE CORRUPÇÃO E PERDA DE ACK
# ============================================================

def corrupt_packet(packet: Packet) -> Packet:
    """
    Corrompe o ACK sem recalcular o checksum.
    """
    damaged_packet = deepcopy(packet)
    damaged_packet.ack = 1 - damaged_packet.ack

    log("SIMULAÇÃO", "O ACK foi propositalmente alterado sem atualizar o checksum.")
    log("SIMULAÇÃO", "O cliente deverá detectar essa alteração usando o CRC32.")

    return damaged_packet


def send_ack(sock: socket.socket, client_address: tuple[str, int], packet: Packet) -> None:
    """
    Envia um ACK ao cliente usando socket UDP real.
    Também simula perda e corrupção de ACK.
    """
    packet_to_send = deepcopy(packet)

    subtitle("ENVIO DO ACK PELO SOCKET UDP")

    log("SERVIDOR", f"Preparando envio do ACK {packet.ack}.")
    log("UDP", f"Destino do ACK: {client_address[0]}:{client_address[1]}")

    if random_generator.random() < ACK_LOSS_RATE:
        log("SIMULAÇÃO", "ACK perdido antes de ser enviado.")
        log("SIMULAÇÃO", "O cliente não receberá esse ACK.")
        log("PROTOCOLO", "O cliente deverá aguardar até ocorrer timeout e retransmitir.")
        return

    if random_generator.random() < ACK_CORRUPTION_RATE:
        packet_to_send = corrupt_packet(packet_to_send)
        log("SIMULAÇÃO", "ACK corrompido antes do envio.")
        log("SIMULAÇÃO", "O cliente deverá descartar esse ACK após verificar o checksum.")

    encoded_packet = encode_packet(packet_to_send)
    sock.sendto(encoded_packet, client_address)

    log("UDP", "ACK enviado via socket UDP real.")
    log("UDP", f"Bytes enviados: {len(encoded_packet)}")


# ============================================================
# SERVIDOR UDP
# ============================================================

def main() -> None:
    expected_seq = 0
    last_valid_ack = 1
    delivered_messages: list[str] = []

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((HOST, PORT))

        show_start_banner()
        show_server_status(expected_seq, last_valid_ack)

        try:
            while True:
                title("AGUARDANDO PACOTE DO CLIENTE")

                log("SERVIDOR", f"Aguardando pacote DATA com sequência esperada {expected_seq}.")
                log("UDP", f"Servidor escutando em {HOST}:{PORT}.")
                log("UDP", "O servidor está bloqueado em recvfrom(), esperando um datagrama UDP.")

                data, client_address = server_socket.recvfrom(BUFFER_SIZE)

                subtitle("DATAGRAMA UDP RECEBIDO")

                log("UDP", f"Datagrama recebido de {client_address[0]}:{client_address[1]}.")
                log("UDP", f"Bytes recebidos: {len(data)}")
                log("SERVIDOR", "Tentando decodificar o datagrama recebido como JSON.")

                try:
                    packet = decode_packet(data)
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                    log("SERVIDOR", "Não foi possível decodificar o datagrama recebido.")
                    log("SERVIDOR", "Pacote ignorado.")
                    continue

                show_received_packet(packet, client_address)

# ============================================================
# SIMULAÇÃO DE PERDA DE PACOTE DATA NO SERVIDOR
# ============================================================

if random_generator.random() < SERVER_DATA_DROP_RATE:
    subtitle("SIMULAÇÃO DE PERDA DE PACOTE")

    log("SIMULAÇÃO", "Pacote DATA chegou ao servidor.")
    log("SIMULAÇÃO", "O pacote foi descartado propositalmente.")
    log("SIMULAÇÃO", "Nenhum ACK será enviado ao cliente.")
    log("PROTOCOLO", "O cliente deverá detectar timeout e retransmitir.")

    show_server_status(expected_seq, last_valid_ack)

    continue

                subtitle("VERIFICAÇÃO DE INTEGRIDADE")

                log("SERVIDOR", "Verificando integridade do pacote com CRC32.")

                if is_corrupt(packet):
                    log("SERVIDOR", "Pacote descartado por corrupção.")
                    log("SERVIDOR", f"Reenviando último ACK válido: {last_valid_ack}.")
                    send_ack(server_socket, client_address, make_ack_packet(last_valid_ack))
                    show_server_status(expected_seq, last_valid_ack)
                    continue

                subtitle("VALIDAÇÃO DO TIPO DE PACOTE")

                if packet.kind != "DATA":
                    log("SERVIDOR", f"Tipo de pacote inválido: {packet.kind}.")
                    log("SERVIDOR", "O servidor esperava um pacote do tipo DATA.")
                    log("SERVIDOR", "Pacote ignorado.")
                    show_server_status(expected_seq, last_valid_ack)
                    continue

                log("SERVIDOR", "Tipo de pacote válido: DATA.")

                subtitle("VALIDAÇÃO DO NÚMERO DE SEQUÊNCIA")

                if packet.seq != expected_seq:
                    log("SERVIDOR", "Pacote duplicado ou fora de ordem detectado.")
                    log("SERVIDOR", f"Sequência recebida: {packet.seq}.")
                    log("SERVIDOR", f"Sequência esperada: {expected_seq}.")
                    log("APLICAÇÃO", "A mensagem não será entregue novamente.")
                    log("SERVIDOR", f"Reenviando ACK {last_valid_ack} para confirmar o último pacote válido.")

                    send_ack(server_socket, client_address, make_ack_packet(last_valid_ack))
                    show_server_status(expected_seq, last_valid_ack)
                    continue

                log("SERVIDOR", "Número de sequência correto.")
                log("SERVIDOR", f"Sequência recebida: {packet.seq}.")
                log("SERVIDOR", f"Sequência esperada: {expected_seq}.")

                title("MENSAGEM RECEBIDA E ENTREGUE")

                log("SERVIDOR", "Pacote correto recebido.")
                log("SERVIDOR", "Entregando dados para a camada de aplicação.")
                log("APLICAÇÃO", f"Mensagem enviada pelo cliente: {packet.payload!r}")

                delivered_messages.append(packet.payload)

                last_valid_ack = packet.seq

                subtitle("ATUALIZAÇÃO DO PROTOCOLO")

                log("PROTOCOLO", f"Último ACK válido atualizado para {last_valid_ack}.")
                log("PROTOCOLO", f"O servidor enviará ACK {packet.seq} ao cliente.")

                send_ack(server_socket, client_address, make_ack_packet(packet.seq))

                expected_seq = 1 - expected_seq

                log("PROTOCOLO", f"Próximo pacote esperado agora possui sequência {expected_seq}.")

                show_delivered_messages(delivered_messages)
                show_server_status(expected_seq, last_valid_ack)

        except KeyboardInterrupt:
            show_final_report(delivered_messages)


if __name__ == "__main__":
    main()