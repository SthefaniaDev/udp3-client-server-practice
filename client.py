from dataclasses import dataclass, asdict
import json
import random
import socket
import time
import zlib
from copy import deepcopy

# ============================================================
# CLIENTE UDP3 - STOP-AND-WAIT COM SOCKET UDP REAL
# ============================================================

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
BUFFER_SIZE = 4096
TIMEOUT = 0.60

# Simulação de problemas no envio de dados pelo cliente.
# Em localhost, o UDP quase nunca perde pacotes naturalmente.
DATA_LOSS_RATE = 0.20
DATA_CORRUPTION_RATE = 0.15

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


def make_data_packet(seq: int, payload: str) -> Packet:
    """
    Cria um pacote DATA com número de sequência e mensagem.
    """
    checksum = calculate_checksum("DATA", seq, -1, payload)

    log(
        "CLIENTE",
        f"Criando pacote DATA com seq={seq}, payload={payload!r} e checksum={checksum}."
    )

    return Packet(
        kind="DATA",
        seq=seq,
        ack=-1,
        payload=payload,
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
            "Checksum inválido. O ACK foi alterado ou chegou corrompido."
        )
        log("CHECKSUM", f"Checksum recebido: {packet.checksum}")
        log("CHECKSUM", f"Checksum esperado: {expected_checksum}")
        return True

    log("CHECKSUM", "Checksum válido. O ACK chegou íntegro.")
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
# SIMULAÇÃO DE CORRUPÇÃO E PERDA DE DADOS
# ============================================================

def corrupt_packet(packet: Packet) -> Packet:
    """
    Corrompe o pacote DATA sem recalcular o checksum.
    """
    damaged_packet = deepcopy(packet)

    if damaged_packet.payload:
        first_character = damaged_packet.payload[0]
        replacement = "#" if first_character != "#" else "@"
        damaged_packet.payload = replacement + damaged_packet.payload[1:]
    else:
        damaged_packet.seq = 1 - damaged_packet.seq

    log(
        "SIMULAÇÃO",
        "O pacote DATA foi propositalmente alterado sem atualizar o checksum."
    )

    return damaged_packet


def send_data(sock: socket.socket, server_address: tuple[str, int], packet: Packet) -> None:
    """
    Envia um pacote DATA ao servidor usando socket UDP real.
    Também simula perda e corrupção de pacote.
    """
    packet_to_send = deepcopy(packet)

    log(
        "CLIENTE",
        f"Preparando envio do pacote seq={packet.seq} para o servidor {server_address}."
    )

    if random_generator.random() < DATA_LOSS_RATE:
        log(
            "SIMULAÇÃO",
            "Pacote DATA perdido antes de ser enviado. O servidor não receberá este pacote."
        )
        return

    if random_generator.random() < DATA_CORRUPTION_RATE:
        packet_to_send = corrupt_packet(packet_to_send)
        log(
            "SIMULAÇÃO",
            "Pacote DATA corrompido antes do envio. O servidor deverá detectar pelo checksum."
        )

    encoded_packet = encode_packet(packet_to_send)
    sock.sendto(encoded_packet, server_address)

    log(
        "UDP",
        f"Pacote DATA enviado via socket UDP real. Bytes enviados: {len(encoded_packet)}."
    )


# ============================================================
# CLIENTE UDP COM STOP-AND-WAIT
# ============================================================

class UdpReliableClient:
    def __init__(self, server_host: str, server_port: int, timeout: float):
        self.server_address = (server_host, server_port)
        self.timeout = timeout
        self.seq = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        log("CLIENTE", "Cliente UDP3 iniciado.")
        log("CLIENTE", f"Servidor configurado em {server_host}:{server_port}.")
        log("CLIENTE", f"Timeout configurado em {timeout} segundo(s).")
        log("CLIENTE", "O cliente enviará um pacote e aguardará o ACK antes do próximo.\n")

    def close(self) -> None:
        self.sock.close()
        log("CLIENTE", "Socket UDP do cliente fechado.")

    def send(self, payload: str) -> None:
        packet = make_data_packet(self.seq, payload)
        attempt = 1

        while True:
            log(
                "PROTOCOLO",
                f"Iniciando tentativa {attempt} de envio para seq={self.seq}."
            )

            send_data(self.sock, self.server_address, packet)

            deadline = time.monotonic() + self.timeout

            log(
                "CLIENTE",
                f"Aguardando ACK {self.seq}. Se não chegar em {self.timeout}s, haverá retransmissão."
            )

            while True:
                remaining_time = deadline - time.monotonic()

                if remaining_time <= 0:
                    log(
                        "TIMEOUT",
                        f"ACK {self.seq} não chegou dentro do tempo limite. Retransmitindo pacote."
                    )
                    attempt += 1
                    break

                self.sock.settimeout(remaining_time)

                try:
                    data, server_address = self.sock.recvfrom(BUFFER_SIZE)
                except socket.timeout:
                    log(
                        "TIMEOUT",
                        f"ACK {self.seq} não chegou dentro do tempo limite. Retransmitindo pacote."
                    )
                    attempt += 1
                    break

                log(
                    "UDP",
                    f"Datagrama recebido de {server_address}. Bytes recebidos: {len(data)}."
                )

                try:
                    ack_packet = decode_packet(data)
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                    log(
                        "CLIENTE",
                        "Não foi possível decodificar o ACK recebido. Continuando a espera."
                    )
                    continue

                log(
                    "CLIENTE",
                    "ACK decodificado: "
                    f"kind={ack_packet.kind}, seq={ack_packet.seq}, "
                    f"ack={ack_packet.ack}, checksum={ack_packet.checksum}."
                )

                log("CLIENTE", "Verificando integridade do ACK com CRC32...")

                if is_corrupt(ack_packet):
                    log("CLIENTE", "ACK descartado por corrupção. Continuando a espera.")
                    continue

                if ack_packet.kind != "ACK":
                    log(
                        "CLIENTE",
                        f"Tipo de pacote inesperado: {ack_packet.kind}. O cliente esperava ACK."
                    )
                    continue

                if ack_packet.ack != self.seq:
                    log(
                        "CLIENTE",
                        f"ACK inesperado recebido: {ack_packet.ack}. Esperado: {self.seq}."
                    )
                    log(
                        "CLIENTE",
                        "Esse ACK pode ser duplicado ou atrasado. Continuando a espera."
                    )
                    continue

                log(
                    "CLIENTE",
                    f"ACK {ack_packet.ack} recebido corretamente. Pacote seq={self.seq} confirmado."
                )

                self.seq = 1 - self.seq

                log(
                    "PROTOCOLO",
                    f"Alternando número de sequência. Próximo pacote usará seq={self.seq}.\n"
                )

                return


# ============================================================
# EXECUÇÃO DO CLIENTE
# ============================================================

def main() -> None:
    messages = [
        "Mensagem 1",
        "Mensagem 2",
        "Mensagem 3",
        "Fim da transmissão"
    ]

    log("CLIENTE", f"Mensagens que serão enviadas: {messages}.\n")

    client = UdpReliableClient(SERVER_HOST, SERVER_PORT, TIMEOUT)

    try:
        for message in messages:
            log("APLICAÇÃO", f"Solicitando envio da mensagem: {message!r}.")
            client.send(message)

        log("CLIENTE", "Todas as mensagens foram enviadas e confirmadas por ACK.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
