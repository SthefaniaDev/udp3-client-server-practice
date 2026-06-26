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
MAX_ATTEMPTS = 5

# Simulação de problemas no envio de dados pelo cliente.
# Em localhost, o UDP quase nunca perde pacotes naturalmente.
DATA_LOSS_RATE = 0.20
DATA_CORRUPTION_RATE = 0.15

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


def pause() -> None:
    input("\nPressione ENTER para continuar...")


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

    subtitle("CRIAÇÃO DO PACOTE DATA")
    log("CLIENTE", f"Criando pacote DATA.")
    log("PACOTE", f"Tipo: DATA")
    log("PACOTE", f"Sequência: {seq}")
    log("PACOTE", f"ACK: -1")
    log("PACOTE", f"Mensagem: {payload!r}")
    log("CHECKSUM", f"Checksum calculado com CRC32: {checksum}")

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
        log("CHECKSUM", "Checksum inválido. O ACK foi alterado ou chegou corrompido.")
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

    log("SIMULAÇÃO", "O pacote DATA foi propositalmente alterado sem atualizar o checksum.")
    log("SIMULAÇÃO", "Isso permite que o servidor detecte a corrupção usando o CRC32.")

    return damaged_packet


def send_data(sock: socket.socket, server_address: tuple[str, int], packet: Packet) -> None:
    """
    Envia um pacote DATA ao servidor usando socket UDP real.
    Também simula perda e corrupção de pacote.
    """
    packet_to_send = deepcopy(packet)

    subtitle("ENVIO DO PACOTE PELO SOCKET UDP")
    log("CLIENTE", f"Preparando envio do pacote seq={packet.seq}.")
    log("UDP", f"Destino configurado: {server_address[0]}:{server_address[1]}")

    if random_generator.random() < DATA_LOSS_RATE:
        log("SIMULAÇÃO", "Pacote DATA perdido antes de ser enviado.")
        log("SIMULAÇÃO", "O servidor não receberá este pacote.")
        log("PROTOCOLO", "O cliente continuará esperando o ACK até ocorrer timeout.")
        return

    if random_generator.random() < DATA_CORRUPTION_RATE:
        packet_to_send = corrupt_packet(packet_to_send)
        log("SIMULAÇÃO", "Pacote DATA corrompido antes do envio.")
        log("SIMULAÇÃO", "O servidor deverá detectar a alteração pelo checksum.")

    encoded_packet = encode_packet(packet_to_send)
    sock.sendto(encoded_packet, server_address)

    log("UDP", "Pacote DATA enviado via socket UDP real.")
    log("UDP", f"Bytes enviados: {len(encoded_packet)}")


# ============================================================
# CLIENTE UDP COM STOP-AND-WAIT
# ============================================================

class UdpReliableClient:
    def __init__(self, server_host: str, server_port: int, timeout: float):
        self.server_address = (server_host, server_port)
        self.timeout = timeout
        self.seq = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        title("CLIENTE UDP3 INICIADO")
        log("CLIENTE", f"Servidor configurado em {server_host}:{server_port}.")
        log("CLIENTE", f"Timeout configurado em {timeout} segundo(s).")
        log("CLIENTE", "Modo de envio: Stop-and-Wait.")
        log("CLIENTE", "O cliente envia um pacote e aguarda o ACK antes do próximo.")
        log("PROTOCOLO", "O número de sequência alterna entre 0 e 1.")

    def close(self) -> None:
        self.sock.close()
        title("CLIENTE ENCERRADO")
        log("CLIENTE", "Socket UDP do cliente fechado.")

    def send(self, payload: str) -> bool:
        """
        Envia uma mensagem ao servidor usando UDP com controle de confiabilidade.

        Retorna:
        - True: se a mensagem foi confirmada por ACK.
        - False: se a mensagem não foi confirmada após o limite de tentativas.
        """
        if not payload.strip():
            log("CLIENTE", "Mensagem vazia não pode ser enviada.")
            return False

        title("NOVA MENSAGEM DA APLICAÇÃO")
        log("APLICAÇÃO", f"Mensagem digitada pelo usuário: {payload!r}")
        log("PROTOCOLO", f"Sequência atual do cliente: {self.seq}")
        log("PROTOCOLO", f"Limite máximo de tentativas: {MAX_ATTEMPTS}")

        packet = make_data_packet(self.seq, payload)
        attempt = 1

        while attempt <= MAX_ATTEMPTS:
            subtitle(f"TENTATIVA {attempt} DE {MAX_ATTEMPTS} || ENVIO DA SEQUÊNCIA {self.seq}")

            log("PROTOCOLO", f"Iniciando tentativa {attempt} de envio.")
            log("PROTOCOLO", "Enquanto o ACK correto não chegar, o pacote poderá ser retransmitido.")

            send_data(self.sock, self.server_address, packet)

            deadline = time.monotonic() + self.timeout

            subtitle("ESPERA PELO ACK")
            log("CLIENTE", f"Aguardando ACK {self.seq}.")
            log("TIMEOUT", f"Tempo máximo de espera por tentativa: {self.timeout} segundo(s).")
            log("PROTOCOLO", "Se o ACK não chegar no prazo, essa tentativa será considerada falha.")

            while True:
                remaining_time = deadline - time.monotonic()

                if remaining_time <= 0:
                    log("TIMEOUT", f"ACK {self.seq} não chegou dentro do tempo limite.")
                    log("PROTOCOLO", "Essa tentativa falhou. O cliente tentará novamente, se ainda houver tentativas.")
                    attempt += 1
                    break

                self.sock.settimeout(remaining_time)

                try:
                    data, server_address = self.sock.recvfrom(BUFFER_SIZE)

                except socket.timeout:
                    log("TIMEOUT", f"ACK {self.seq} não chegou dentro do tempo limite.")
                    log("PROTOCOLO", "Essa tentativa falhou. O cliente tentará novamente, se ainda houver tentativas.")
                    attempt += 1
                    break

                except ConnectionResetError:
                    log("ERRO", "O Windows informou que o destino UDP recusou ou não respondeu.")
                    log("ERRO", "Isso pode acontecer se o servidor não estiver rodando ou se a porta estiver incorreta.")
                    log("PROTOCOLO", "Tratando como perda de ACK.")
                    attempt += 1
                    break

                subtitle("ACK RECEBIDO")
                log("UDP", f"Datagrama recebido de {server_address}.")
                log("UDP", f"Bytes recebidos: {len(data)}")

                try:
                    ack_packet = decode_packet(data)
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                    log("CLIENTE", "Não foi possível decodificar o ACK recebido.")
                    log("CLIENTE", "O cliente continuará esperando um ACK válido até o timeout.")
                    continue

                log("CLIENTE", "ACK decodificado com sucesso.")
                log("ACK", f"Tipo: {ack_packet.kind}")
                log("ACK", f"Seq: {ack_packet.seq}")
                log("ACK", f"Ack: {ack_packet.ack}")
                log("ACK", f"Payload: {ack_packet.payload!r}")
                log("ACK", f"Checksum: {ack_packet.checksum}")

                log("CLIENTE", "Verificando integridade do ACK com CRC32...")

                if is_corrupt(ack_packet):
                    log("CLIENTE", "ACK descartado por corrupção.")
                    log("PROTOCOLO", "O cliente continuará aguardando até timeout ou ACK válido.")
                    continue

                if ack_packet.kind != "ACK":
                    log("CLIENTE", f"Tipo de pacote inesperado: {ack_packet.kind}.")
                    log("CLIENTE", "O cliente esperava um pacote do tipo ACK.")
                    continue

                if ack_packet.ack != self.seq:
                    log("CLIENTE", f"ACK inesperado recebido: {ack_packet.ack}.")
                    log("CLIENTE", f"ACK esperado: {self.seq}.")
                    log("PROTOCOLO", "Esse ACK pode ser duplicado, atrasado ou referente a outro pacote.")
                    log("PROTOCOLO", "O cliente continuará esperando o ACK correto.")
                    continue

                title("PACOTE CONFIRMADO COM SUCESSO")
                log("CLIENTE", f"ACK {ack_packet.ack} recebido corretamente.")
                log("PROTOCOLO", f"Pacote seq={self.seq} confirmado pelo servidor.")
                log("RESULTADO", "Mensagem enviada com sucesso.")

                self.seq = 1 - self.seq

                log("PROTOCOLO", f"Alternando número de sequência. Próximo pacote usará seq={self.seq}.")
                return True

        title("ENVIO NÃO CONFIRMADO")
        log("ERRO", f"A mensagem não foi confirmada após {MAX_ATTEMPTS} tentativa(s).")
        log("ERRO", "Envio considerado sem sucesso.")
        log("PROTOCOLO", "O cliente desistiu dessa mensagem para evitar loop infinito.")
        log("PROTOCOLO", f"A sequência atual continuará sendo {self.seq}, pois não houve ACK válido.")
        log("MENU", "Você pode tentar enviar a mesma mensagem novamente pelo menu.")

        return False


# ============================================================
# MENU INTERATIVO DO CLIENTE
# ============================================================

def show_menu() -> None:
    title("CLIENTE UDP3 - MENU PRINCIPAL")
    print("|| 1 || Enviar uma mensagem")
    print("|| 2 || Ver configurações do cliente")
    print("|| 3 || Explicar funcionamento da prática")
    print("|| 0 || Encerrar cliente")
    separator("=")


def show_settings() -> None:
    title("CONFIGURAÇÕES DO CLIENTE")
    print(f"|| Servidor .................... || {SERVER_HOST}:{SERVER_PORT}")
    print(f"|| Tamanho do buffer ........... || {BUFFER_SIZE} bytes")
    print(f"|| Timeout ..................... || {TIMEOUT} segundo(s)")
    print(f"|| Máximo de tentativas ........ || {MAX_ATTEMPTS}")
    print(f"|| Perda simulada de DATA ...... || {DATA_LOSS_RATE * 100:.0f}%")
    print(f"|| Corrupção simulada de DATA .. || {DATA_CORRUPTION_RATE * 100:.0f}%")
    print(f"|| Protocolo ................... || UDP + Stop-and-Wait")
    print(f"|| Sequência ................... || Alternância entre 0 e 1")
    separator("=")


def explain_practice() -> None:
    title("EXPLICAÇÃO DA PRÁTICA UDP3")

    print("|| Esta prática usa sockets UDP reais em Python.")
    print("|| O cliente envia mensagens para um servidor UDP.")
    print("|| Como o UDP não garante entrega, foram adicionados controles manuais.")
    print()

    print("|| MECANISMOS IMPLEMENTADOS")
    print("|| - Checksum CRC32 para detectar corrupção.")
    print("|| - ACK para confirmar recebimento.")
    print("|| - Timeout para detectar ausência de resposta.")
    print("|| - Retransmissão quando o ACK não chega.")
    print("|| - Limite de tentativas para evitar loop infinito.")
    print("|| - Número de sequência alternando entre 0 e 1.")
    print()

    print("|| O QUE PODE ACONTECER DURANTE A EXECUÇÃO")
    print("|| - O pacote pode ser enviado normalmente.")
    print("|| - O pacote pode ser perdido antes do envio.")
    print("|| - O pacote pode ser corrompido de propósito.")
    print("|| - O ACK pode não chegar ao cliente.")
    print("|| - O ACK pode chegar corrompido.")
    print("|| - O cliente pode retransmitir a mensagem.")
    print()

    print("|| OBJETIVO")
    print("|| Mostrar como implementar confiabilidade sobre UDP.")
    separator("=")


def read_user_message() -> str:
    title("DIGITAR MENSAGEM")
    print("|| Digite a mensagem que será enviada ao servidor.")
    print("|| Para cancelar, deixe vazio e pressione ENTER.")
    separator("-")

    return input("Mensagem: ")


# ============================================================
# EXECUÇÃO DO CLIENTE
# ============================================================

def main() -> None:
    client = UdpReliableClient(SERVER_HOST, SERVER_PORT, TIMEOUT)

    try:
        while True:
            show_menu()
            option = input("Escolha uma opção: ").strip()

            if option == "1":
                message = read_user_message()

                if not message.strip():
                    log("CLIENTE", "Envio cancelado. Nenhuma mensagem foi digitada.")
                    pause()
                    continue

                success = client.send(message)

                if success:
                    log("MENU", "A mensagem foi enviada e confirmada com sucesso.")
                else:
                    log("MENU", "A mensagem não foi confirmada após o limite de tentativas.")
                    log("MENU", "Você pode tentar enviar novamente pelo menu.")

                pause()

            elif option == "2":
                show_settings()
                pause()

            elif option == "3":
                explain_practice()
                pause()

            elif option == "0":
                title("ENCERRANDO CLIENTE UDP3")
                log("CLIENTE", "O usuário solicitou o encerramento do cliente.")
                break

            else:
                log("MENU", "Opção inválida. Escolha 1, 2, 3 ou 0.")
                pause()

    finally:
        client.close()


if __name__ == "__main__":
    main()