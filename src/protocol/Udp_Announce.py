import asyncio
import src.state as state
from config import BROADCAST_PORT
from src.protocol.Local_Address import get_lan_ip
from src.protocol import codec
from src.protocol.Send_Only_Protocol import Send_Only_Protocol


# Manages the periodic transmission of UDP 'ANNOUNCE' packets.
# This notifies other nodes on the local area network of this node's existence and availability.
async def Announcer(BASE_PORT: int) -> None:
    loop = asyncio.get_running_loop()

    A_transport, protocol = await loop.create_datagram_endpoint(
        lambda: Send_Only_Protocol(),
        local_addr=(get_lan_ip(), 0),
        allow_broadcast=True,
    )
    data = {
        "type": "ANNOUNCE",
        "version": "1.0",
        "peer_id": state.PEER_ID_STUB,
        "host": get_lan_ip(),
        "port": BASE_PORT,
    }
    # print("Announce (my ip) -> " + get_lan_ip())
    # print("Announce (my peer_id) -> " + state.PEER_ID_STUB)
    packet = codec.encode(data).encode("utf-8")
    A_transport.sendto(packet, ("192.168.2.70", BROADCAST_PORT))
    # A_transport.sendto(packet, ("127.0.0.1", BROADCAST_PORT))
    A_transport.close()


# Loops the announcement process at a defined interval to ensure continuous
# network presence as peers join or leave the network.
async def periodic_announces(BASE_PORT: int):
    while True:
        await Announcer(BASE_PORT)
        await asyncio.sleep(300)
