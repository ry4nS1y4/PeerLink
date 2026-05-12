import asyncio
import src.protocol.codec as codec
import src.protocol.validator as validator
from src.protocol.message_handler_factory import MessageHandlerFactory


# Implements the logic for handling asynchronous UDP datagrams.
# It decodes incoming packets and utilizes the MessageHandlerFactory to process peer announcements.
class Discovery_Protocol(asyncio.DatagramProtocol):
    # print("reaching")

    def datagram_received(self, data: bytes, addr):
        try:
            text = data.decode("utf-8")
            # print("this -> " + text)
            msg: dict = codec.decode(text)
        except Exception:
            return
        if validator.validate(msg):
            handler = MessageHandlerFactory.get_handler(msg)
            handler.handle(msg)
            # print("running")

    # else:
    # print("same id")
