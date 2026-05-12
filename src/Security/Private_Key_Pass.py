import base64
import secrets
import keyring

SERVICE = "scid-app"
ACCOUNT = "private-key-passphrase"


# Interfaces with the operating system's native keyring to securely manage
# the passphrase required for RSA private key encryption and decryption.
# If no passphrase exists, it generates a cryptographically secure 32-byte
# token, encodes it for storage, and saves it to the system keychain.
def get_or_create_passphrase() -> bytes:
    saved = keyring.get_password(SERVICE, ACCOUNT)
    if saved is None:
        pw_bytes = secrets.token_bytes(32)
        saved = base64.urlsafe_b64encode(pw_bytes).decode("utf-8")
        keyring.set_password(SERVICE, ACCOUNT, saved)
    return base64.urlsafe_b64decode(saved.encode("utf-8"))
