from src.identification.Identity_Interface import PeerIdStrategy
from src.identification.Identity_fallback import createPeerIdentity


# GANG OF 4 STRATEGY IMPLEMENTATION
class FallBack_Id(PeerIdStrategy):
    """
    A concrete strategy that implements basic UUID-based identification.
    Used as a fallback when cryptographic identity methods are not required or available.
    """

    def create_Id(self) -> str:
        return createPeerIdentity()
