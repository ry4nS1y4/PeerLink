import asyncio


class Send_Only_Protocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        return
