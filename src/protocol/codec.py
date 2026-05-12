import json


# Encapsulates logic for converting Python dictionaries to newline-delimited
# JSON strings for network transmission, handling common serialization errors.
def encode(msg: dict) -> str:
    try:
        encoded: str = f"{json.dumps(msg)}\n"
    except (TypeError, AttributeError) as e:
        raise TypeError(f"Encoding Troubles: {e}")
    return encoded


# Decodes incoming newline-delimited strings back into Python dictionaries,
# ensuring raw network data is converted into a manageable structured format.
def decode(msg: str) -> dict:
    try:
        decodedStr: str = msg.rstrip("\n")
        decoded: dict = json.loads(decodedStr)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError("Decoding Troubles", e.doc, e.pos) from e
    except AttributeError as e:
        raise AttributeError(f"Decoding Troubles: {e}")
    return decoded
