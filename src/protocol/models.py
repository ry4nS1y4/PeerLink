class FileResponseData:
    def __init__(self, header: dict, filepath: str):
        self.header = header
        self.filepath = filepath


class FileReceiveData:
    def __init__(self, size: int, filepath: str):
        self.size = size
        self.filepath = filepath


class FileRelayData:
    """Returned when this node must relay a FILE_REQUEST to another peer."""

    def __init__(self, target_peer_id: str, request_id: str):
        self.target_peer_id = target_peer_id
        self.request_id = request_id


class FileForwardData:
    """Returned when this node must forward a FILE_RESPONSE upstream to the requester."""

    def __init__(self, size: int, upstream_writer):
        self.size = size
        self.upstream_writer = upstream_writer
