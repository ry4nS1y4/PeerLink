from config import SUPPORTED_VERSIONS
import src.state as state


# Orchestrates the validation process by checking basic protocol requirements
# followed by specific field requirements based on the message type.
def validate(msg: dict) -> bool:
    return _validate_base(msg) and _validate_additional_fields(msg)


# Verifies that mandatory fields like 'type', 'version', and 'peer_id' exist,
# ensuring the version is supported and the message did not originate from this node.
def _validate_base(msg: dict) -> bool:
    if (
        "type" in msg
        and "version" in msg
        and "peer_id" in msg
        and msg["version"] in SUPPORTED_VERSIONS
        and msg["peer_id"] != state.PEER_ID_STUB
    ):
        return True
    return False


# Performs deep inspection on incoming messages to ensure all payload-specific
def _validate_additional_fields(msg: dict) -> bool:
    match msg["type"]:
        case "ANNOUNCE":
            if "host" in msg and "port" in msg:
                return True
        case "PING":
            return True
        case "PONG":
            return True
        case "CATALOG_REQUEST":
            return True
        case "CATALOG_RESPONSE":
            if "files" in msg and all(
                {"file_id", "name", "size"} <= f.keys() for f in msg["files"]
            ):
                return True
        case "FILE_REQUEST":
            if "file_id" in msg:
                return True
        case "FILE_RESPONSE":
            if "file_id" in msg and "name" in msg and "size" in msg:
                return True
        case "ERROR":
            if "code" in msg and "message" in msg:
                return True
        case "SEARCH_REQUEST":
            if (
                "request_id" in msg
                and "filename" in msg
                and "ttl" in msg
                and "origin_host" in msg
                and "origin_port" in msg
            ):
                return True
        case "SEARCH_RESPONSE":
            if (
                "request_id" in msg
                and "filename" in msg
                and "file_id" in msg
                and "size" in msg
                and "host" in msg
                and "port" in msg
            ):
                return True

    return False
