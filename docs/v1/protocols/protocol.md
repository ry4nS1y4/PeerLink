# Protocols

These are schemas for JSON messages that are sent through TCP and UDP.

# Message Framing

TCP: newline-delimited JSON. Every message ends with \n. The receiver reads until it hits a \n and that's one complete message.

UDP: no framing needed. Each UDP packet is exactly one complete message.

## General JSON Message Schema

Particularly the schemas are for the following types:
`ANNOUNCE`
`PING`
`PONG`
`CATALOG_REQUEST`
`CATALOG_RESPONSE`
`FILE_REQUEST`
`FILE_RESPONSE`
`ERROR`

```JSON
{
  "type": "...",
  "version": "1.x",
  "peer_id": "abc123"
}
```

- `type` specifies the type of message
- `version` specifies which phase of the project we are in and if any changes were made after a stable release
- `peer_id` uniquely identify a peer

## Ping (TCP)

```JSON
{
  "type": "PING",
  "version": "1.0",
  "peer_id": "abc123"
}
```

## Pong (TCP)

```JSON
{
  "type": "PONG",
  "version": "1.0",
  "peer_id": "abc123"
}
```

## CATALOG_REQUEST (TCP)

```json
{
  "type": "CATALOG_REQUEST",
  "version": "1.0",
  "peer_id": "abc123"
}
```

## CATALOG_RESPONSE (TCP)

```json
{
  "type": "CATALOG_RESPONSE",
  "version": "1.0",
  "peer_id": "abc123",
  "files": [
    {
      "file_id": "a3f5...",
      "name": "notes.pdf",
      "size": 204800
    },
    {
      "file_id": "b7c2...",
      "name": "lecture.mp4",
      "size": 987654
    }
  ]
}
```

- `files` field is what catalog entries would look like.

## FILE_REQUEST (TCP)

```json
{
  "type": "FILE_REQUEST",
  "version": "1.0",
  "peer_id": "abc123",
  "file_id": "a3f5..."
}
```

**Relay extension** (optional fields — present only when the requester has no direct connection to the file owner):

```json
{
  "type": "FILE_REQUEST",
  "version": "1.0",
  "peer_id": "abc123",
  "file_id": "a3f5...",
  "target_peer_id": "def456",
  "request_id": "<uuid4>"
}
```

- `target_peer_id`: the peer that owns the file; the receiving node must forward the request to them
- `request_id`: unique ID used by the relay node to route the FILE_RESPONSE back to the requester
- When an intermediate node receives `target_peer_id`, it strips that field and forwards to the target, recording `request_id → upstream_writer` in its routing table

## FILE_RESPONSE (TCP)

```json
{
  "type": "FILE_RESPONSE",
  "version": "1.0",
  "peer_id": "abc123",
  "file_id": "a3f5...",
  "name": "notes.pdf",
  "size": 204800,
  "request_id": ""
}
```

- The JSON header is sent first, followed immediately by the raw file bytes over the same TCP connection.
- `request_id`: echoed from the FILE_REQUEST. Empty string for direct downloads. When non-empty, the receiving node checks its routing table and forwards the header + bytes upstream if a route exists.

## ERROR (TCP)

```json
{
  "type": "ERROR",
  "version": "1.0",
  "peer_id": "abc123",
  "code": "FILE_NOT_FOUND",
  "message": "No file with that file_id exists on this peer"
}
```

- List of Error Codes
  - `FILE_NOT_FOUND` — no file with that file_id in local catalog
  - `PEER_NOT_REACHABLE` — relay was requested but the target peer is not connected to this node

## ANNOUNCE (UDP)

```json
{
  "type": "ANNOUNCE",
  "version": "1.0",
  "peer_id": "abc123",
  "host": "192.168.1.5",
  "port": 5000
}
```

## SEARCH_REQUEST (floods outward):

```json
{
  "type": "SEARCH_REQUEST",
  "version": "1.0",
  "peer_id": "<A's id>",
  "request_id": "<uuid4>",
  "filename": "blade.txt",
  "ttl": 5,
  "origin_host": "127.0.0.1",
  "origin_port": 6001
}
```

## SEARCH_RESPONSE (travels back hop-by-hop):

```json
{
  "type": "SEARCH_RESPONSE",
  "version": "1.0",
  "peer_id": "<C's id>",
  "request_id": "<same uuid4>",
  "filename": "blade.txt",
  "file_id": "<sha256>",
  "size": 1234,
  "host": "127.0.0.1",
  "port": 6003
}
```
