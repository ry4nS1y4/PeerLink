from abc import abstractmethod, ABC

# GANG OF 4 STRATEGY IMPLEMENTATION
"""
    Abstract base class defining the contract for all identity generation strategies.
    Ensures that any implemented strategy provides a consistent 'create_Id' method.
"""


class PeerIdStrategy(ABC):
    # This method will be implemented by each strategy
    @abstractmethod
    def create_Id(self) -> str:
        pass
