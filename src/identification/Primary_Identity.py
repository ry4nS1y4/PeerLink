from src.identification.Identity_Interface import PeerIdStrategy
from src.identification.Peer_Identity import CreateKeys, CreatePeerID

# GANG OF 4 STRATEGY IMPLEMENTATION


class Primary_Identity(PeerIdStrategy):
    """
    A concrete strategy that implements cryptographic RSA-based identification.
    This provides a secure, verifiable identity derived from a public key.
    """

    def create_Id(self) -> str:
        # Create or load the public key
        publick_key = CreateKeys()
        # Convert the key from hex to bytes before making the peer ID
        return CreatePeerID(bytes.fromhex(publick_key))
