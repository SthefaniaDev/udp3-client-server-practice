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

random_generator = random.Random(7)


@dataclass
class Packet:
    kind: str
    seq: int
    ack: int
    payload: str
    checksum: int


# ============================================================
# FUNÇÕES AUXILIARES DE LOG
# ============================================================

def log(section: str, message: str) -> None:
    """
    Exibe mensagens padronizadas para facilitar a apresentação da prática.
    """
    print(f"[{section}] {message}")


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

    log(
        "SERVIDOR",
        f"Criando pacote ACK para confirmar o recebimento da sequência {ack}."
    )

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
        log(
            "CHECKSUM",
            "Checksum inválido. O pacote foi alterado ou chegou corrompido."
        )
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

    log(
        "SIMULAÇÃO",
        "O ACK foi propositalmente alterado sem atualizar o checksum."
    )

    return damaged_packet


def send_ack(sock: socket.socket, client_address: tuple[str, int], packet: Packet) -> None:
    """
    Envia um ACK ao cliente usando socket UDP real.
    Também simula perda e corrupção de ACK.
    """
    packet_to_send = deepcopy(packet)

    log(
        "SERVIDOR",
        f"Preparando envio do ACK {packet.ack} para o cliente {client_address}."
    )

    if random_generator.random() < ACK_LOSS_RATE:
        log(
            "SIMULAÇÃO",
            "ACK perdido antes de ser enviado. O cliente deverá aguardar até dar timeout."
        )
        return

    if random_generator.random() < ACK_CORRUPTION_RATE:
        packet_to_send = corrupt_packet(packet_to_send)
        log(
            "SIMULAÇÃO",
            "ACK corrompido antes do envio. O cliente deverá detectar pelo checksum."
        )

    encoded_packet = encode_packet(packet_to_send)
    sock.sendto(encoded_packet, client_address)

    log(
        "UDP",
        f"ACK enviado via socket UDP real para {client_address}. Bytes enviados: {len(encoded_packet)}."
    )


# ============================================================
# SERVIDOR UDP
# ============================================================

def main() -> None:
    expected_seq = 0
    last_valid_ack = 1
    delivered_messages: list[str] = []

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((HOST, PORT))

        log("SERVIDOR", "Servidor UDP3 iniciado.")
        log("SERVIDOR", f"Escutando em {HOST}:{PORT}.")
        log("SERVIDOR", "O servidor espera pacotes DATA alternando sequência 0 e 1.")
        log("SERVIDOR", "Pressione CTRL+C para encerrar.\n")

        try:
            while True:
                log(
                    "SERVIDOR",
                    f"Aguardando pacote DATA com sequência esperada {expected_seq}..."
                )

                data, client_address = server_socket.recvfrom(BUFFER_SIZE)

                log(
                    "UDP",
                    f"Datagrama recebido de {client_address}. Bytes recebidos: {len(data)}."
                )

                try:
                    packet = decode_packet(data)
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                    log(
                        "SERVIDOR",
                        "Não foi possível decodificar o datagrama recebido. Pacote ignorado."
                    )
                    continue

                log(
                    "SERVIDOR",
                    "Pacote decodificado: "
                    f"kind={packet.kind}, seq={packet.seq}, ack={packet.ack}, "
                    f"payload={packet.payload!r}, checksum={packet.checksum}."
                )

                log("SERVIDOR", "Verificando integridade do pacote com CRC32...")

                if is_corrupt(packet):
                    log(
                        "SERVIDOR",
                        f"Pacote descartado. Reenviando último ACK válido: {last_valid_ack}."
                    )
                    send_ack(server_socket, client_address, make_ack_packet(last_valid_ack))
                    print()
                    continue

                if packet.kind != "DATA":
                    log(
                        "SERVIDOR",
                        f"Tipo de pacote inválido: {packet.kind}. O servidor esperava DATA."
                    )
                    print()
                    continue

                if packet.seq != expected_seq:
                    log(
                        "SERVIDOR",
                        "Pacote duplicado ou fora de ordem detectado. "
                        f"Recebido seq={packet.seq}, esperado seq={expected_seq}."
                    )
                    log(
                        "SERVIDOR",
                        f"Mensagem não será entregue novamente. Reenviando ACK {last_valid_ack}."
                    )
                    send_ack(server_socket, client_address, make_ack_packet(last_valid_ack))
                    print()
                    continue

                log(
                    "SERVIDOR",
                    "Pacote correto recebido. Entregando dados para a aplicação."
                )

                delivered_messages.append(packet.payload)

                log(
                    "APLICAÇÃO",
                    f"Mensagem entregue: {packet.payload!r}."
                )

                last_valid_ack = packet.seq

                log(
                    "PROTOCOLO",
                    f"Atualizando último ACK válido para {last_valid_ack}."
                )

                send_ack(server_socket, client_address, make_ack_packet(packet.seq))

                expected_seq = 1 - expected_seq

                log(
                    "PROTOCOLO",
                    f"Próximo pacote esperado agora possui sequência {expected_seq}."
                )

                log(
                    "SERVIDOR",
                    f"Mensagens entregues até agora: {delivered_messages}.\n"
                )

        except KeyboardInterrupt:
            log("SERVIDOR", "Servidor encerrado pelo usuário.")
            log("SERVIDOR", f"Mensagens entregues: {delivered_messages}")


if __name__ == "__main__":
    main()
