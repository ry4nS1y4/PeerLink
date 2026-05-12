import uuid


def __checkPeerIdentity() -> bool:
    Deviceid = str("")
    try:
        with open("Identity.txt", "r") as f:
            Deviceid = f.read().strip()
            if Deviceid != "":
                return True
            else:
                return False
    except FileNotFoundError:
        return False


def createPeerIdentity() -> str:
    return str(uuid.uuid4())

    # Status = bool(__checkPeerIdentity())
    # if not Status:
    #     myId = uuid.uuid1()
    #     with open("Identity.txt", "w") as f:
    #         f.write(str(myId))


# Peer Identity creation work,  now when asked by udp or anything else a sending process is needed which cam be connected to both of these
