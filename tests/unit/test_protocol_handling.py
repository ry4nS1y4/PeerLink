import json
import src.state as state
from src.protocol import codec
from src.protocol.message_handler_factory import MessageHandlerFactory
from src.protocol.message_handler_factory import PingHandler, FileReqHandler
from src.protocol import models


# ENCODE / DECODE
def test_encode_success():
    msg = {"type": "PING", "version": "1.0"}
    encoded = codec.encode(msg)

    assert encoded.endswith("\n")
    assert json.loads(encoded.strip()) == msg


def test_decode_success():
    msg = {"type": "PING"}
    encoded = json.dumps(msg) + "\n"
    decoded = codec.decode(encoded)

    assert decoded == msg


def test_decode_invalid_json():
    try:
        codec.decode("{bad json}")
        assert False
    except json.JSONDecodeError:
        assert True


# FACTORY + HANDLERS
def test_factory_returns_ping_handler():
    handler = MessageHandlerFactory.get_handler({"type": "PING"})
    assert isinstance(handler, PingHandler)


def test_ping_handler_returns_pong():
    state.PEER_ID_STUB = "peerA"

    handler = PingHandler()
    result = handler.handle({"version": "1.0"})

    assert result["type"] == "PONG"
    assert result["peer_id"] == "peerA"


def test_file_request_found():
    state.local_catalog = [{"file_id": "abc", "name": "a.txt", "size": 5}]
    state.PEER_ID_STUB = "peerA"

    handler = FileReqHandler()
    result = handler.handle({"file_id": "abc", "version": "1.0"})

    assert isinstance(result, models.FileResponseData)
    assert result.header["file_id"] == "abc"


def test_file_request_not_found():
    state.local_catalog = []

    handler = FileReqHandler()
    result = handler.handle({"file_id": "missing", "version": "1.0"})

    assert isinstance(result, dict)
    assert result["type"] == "ERROR"


if __name__ == "__main__":

    print("Running tests...\n")

    test_encode_success()
    print("test_encode_success passed")

    test_decode_success()
    print("test_decode_success passed")

    test_decode_invalid_json()
    print("test_decode_invalid_json passed")

    test_factory_returns_ping_handler()
    print("test_factory_returns_ping_handler passed")

    test_ping_handler_returns_pong()
    print("test_ping_handler_returns_pong passed")

    test_file_request_found()
    print("test_file_request_found passed")

    test_file_request_not_found()
    print("test_file_request_not_found passed")
