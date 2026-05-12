# from src.protocol.codec import encode, decode as
from src.protocol.Discovery_Protocol import Discovery_Protocol
from unittest.mock import Mock, patch

# UDP Discovery protocol


def test_datagram_received_valid_calls_handler(capsys):
    proto = Discovery_Protocol()
    msg = {"type": "ANNOUNCE"}
    handler = Mock()

    with patch("src.protocol.Discovery_Protocol.codec.decode", return_value=msg), patch(
        "src.protocol.Discovery_Protocol.validator.validate", return_value=True
    ), patch(
        "src.protocol.Discovery_Protocol.MessageHandlerFactory.get_handler",
        return_value=handler,
    ):

        proto.datagram_received(b'{"type":"ANNOUNCE"}', ("192.168.2.12", 5001))

        handler.handle.assert_called_once_with(msg)


def test_datagram_received_invalid_does_not_call_handler(capsys):
    proto = Discovery_Protocol()
    msg = {"type": "ANNOUNCE"}

    with patch("src.protocol.Discovery_Protocol.codec.decode", return_value=msg), patch(
        "src.protocol.Discovery_Protocol.validator.validate", return_value=False
    ), patch(
        "src.protocol.Discovery_Protocol.MessageHandlerFactory.get_handler"
    ) as get_handler:

        proto.datagram_received(b'{"type":"ANNOUNCE"}', ("192.168.2.12", 5001))

        get_handler.assert_not_called()


def test_datagram_received_decode_error_returns_quietly(capsys):
    proto = Discovery_Protocol()

    with patch(
        "src.protocol.Discovery_Protocol.codec.decode", side_effect=Exception("boom")
    ), patch("src.protocol.Discovery_Protocol.validator.validate") as validate:

        proto.datagram_received(b'{"bad":"data"}', ("192.168.2.12", 5001))
        validate.assert_not_called()
