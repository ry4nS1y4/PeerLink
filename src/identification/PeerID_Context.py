from src.identification.Identity_Interface import PeerIdStrategy

# GANG OF 4 STRATEGY IMPLEMENTATION
"""
    Acts as the Context in the Strategy pattern. It maintains a reference to a 
    PeerIdStrategy object and delegates the ID generation task to it.
    """


class PeerID_Context:
    def __init__(self, strategy: PeerIdStrategy):
        # Save the strategy that will be used
        self.strategy = strategy

    def generate_Peer_Id(self) -> str:
        """Executes the specific identity generation algorithm defined by the strategy."""
        return self.strategy.create_Id()
