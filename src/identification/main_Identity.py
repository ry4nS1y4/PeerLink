from src.identification.PeerID_Context import PeerID_Context
from src.identification.FallBack_ID import FallBack_Id
from src.identification.Primary_Identity import Primary_Identity

# GANG OF 4 STRATEGY IMPLEMENTATION


def create_Identity_Object(mode: int) -> str:
    """
    Factory-style helper that initializes the identification system.
    Switches between Fallback (Mode 0) and Primary (Mode 1) strategies based on input.
    """
    if mode == 0:
        return PeerID_Context(FallBack_Id()).generate_Peer_Id()
    if mode == 1:
        return PeerID_Context(Primary_Identity()).generate_Peer_Id()
