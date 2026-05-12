import asyncio
import socket
from config import BROADCAST_PORT
from src.protocol.Discovery_Protocol import Discovery_Protocol


async def start_udp_listener():
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", BROADCAST_PORT))
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: Discovery_Protocol(),
        sock=sock,
    )
    return transport, protocol
