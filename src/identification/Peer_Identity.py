from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from src.Security.Private_Key_Pass import get_or_create_passphrase
from pathlib import Path

status = Path.home() / "scid" / "private_key.pem"
status.parent.mkdir(parents=True, exist_ok=True)


def __CheckKey() -> bool:
    try:
        with open(status, "rb") as f:
            key = f.read()
            if not key:
                return False
            else:
                return True
    except FileNotFoundError:
        return False


def CreateKeys() -> str:

    if not __CheckKey():
        private_key_object = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        private_key = private_key_object.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                get_or_create_passphrase()
            ),
        )

        status.parent.mkdir(parents=True, exist_ok=True)

        with open(status, "wb") as f:
            f.write(private_key)
            public_key_object = private_key_object.public_key()
            public_key = public_key_object.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            return public_key.hex()

    else:  # done if private key is stored in __innnit__ file
        with open(status, "rb") as f:
            content = f.read()
            private_key_reobject = serialization.load_pem_private_key(
                content,
                get_or_create_passphrase(),
            )  # converts the conetent of the file back into the rsa private key object !!!
            public_key_reobject = private_key_reobject.public_key()
        republic_key = public_key_reobject.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return republic_key.hex()


def CreatePeerID(Public_Key: bytes) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(Public_Key)
    peer_id = digest.finalize()
    return peer_id.hex()
