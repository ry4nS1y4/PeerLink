# Peer-to-Peer File Sharing System

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![asyncio](https://img.shields.io/badge/asyncio-grey?logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/Textual-TUI-008080)
![TCP](https://img.shields.io/badge/TCP-Networking-orange)
![UDP](https://img.shields.io/badge/UDP-Discovery-orange)
![SHA256](https://img.shields.io/badge/SHA--256-Integrity-green)

A decentralized file sharing system built in Python. Peers discover each other autonomously, negotiate connections over a local network or localhost, search for files using a Gnutella-inspired flood search with TTL and UUID-based deduplication, and transfer files directly — no central server required.

> **Origin:** This project was originally developed as part of **SWE4403/CS4015 — Software Architecture & Design Patterns** at the **University of New Brunswick** (Winter 2026) by a team of four students. With permission from the course instructor, I have taken over the repository for continued development and maintenance beyond the course.

---

## Original Team

| Name            | GitHub          | Role               |
| --------------- | --------------- | ------------------ |
| Ryan Siyavudeen | ry4nS1y4        | Project Lead       |
| Aakash Yogabalu | Aakash-Yogabalu | Tech Lead          |
| Md Imtiaz Ahmed | imtiazahmed04   | Documentation Lead |
| Shifan Pathan   | shifan112-1     | QA Lead            |

---

## Features

- **Serverless architecture** — every node is both a client and a server
- **UDP peer discovery** — automatic announcements on the local network
- **Gnutella-style flood search** — multihop search with TTL and UUID deduplication
- **Hop-by-hop response routing** — search responses trace back through the network
- **TCP file transfer** — direct peer-to-peer with SHA-256 integrity verification
- **Heartbeat system** — peers detect and clean up dropped connections
- **Textual TUI** — rich terminal interface built with [Textual](https://github.com/Textualize/textual)
- **Async I/O** — built on Python `asyncio` with raw TCP/UDP sockets

---

## Tech Stack

- Python 3.11+
- `asyncio` — non-blocking networking
- `textual` — terminal UI framework
- TCP — peer communication and file transfer
- UDP — peer discovery and announcements
- JSON — protocol message format
- SHA-256 — file identity and integrity

---

## Getting Started

### Prerequisites

- Python **3.11+**
- `pip`
- A terminal on Windows, macOS, or Linux

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <repo-name>
```

### 2. Create and activate a virtual environment

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify shared and download folders

The application expects two folders in the project root:

- `shared/` — files this peer is offering to others
- `downloads/` — files received from other peers

Both are included in the repo. Drop any files you want to share into `shared/` before starting a peer.

---

## Running a Peer

There are two entry points:

**Textual TUI (recommended)**

```bash
python -m src.main_textual <port>
```

**Basic CLI**

```bash
python -m src.main <port>
```

### Running multiple peers locally

Open separate terminals and start peers on different ports:

```bash
# Terminal 1
python -m src.main_textual 5000

# Terminal 2
python -m src.main_textual 5002

# Terminal 3 (optional)
python -m src.main_textual 5003
```

Peers on the same LAN will discover each other automatically via UDP. For localhost testing, connect manually:

```text
connect 127.0.0.1 5002
```

---

## Commands

Once a peer is running:

| Command                        | Description                     |
| ------------------------------ | ------------------------------- |
| `connect <host> <port>`        | Manually connect to a peer      |
| `search <filename>`            | Flood search across the network |
| `download <number>`            | Download by result index        |
| `download <file_id> <peer_id>` | Download by explicit IDs        |
| `peers`                        | List connected peers            |
| `catalog`                      | List locally shared files       |
| `id`                           | Show this peer's identity       |
| `quit`                         | Shut down the peer              |

**Example flow:**

```text
connect 127.0.0.1 5002
search apple.txt
download 1
```

---

## Tests

```bash
# Unit tests only
pytest tests/unit -q

# All tests
pytest -q

# With coverage
pytest --cov=src tests/unit
```

---

## Linting

```bash
ruff check .
black .
```

---

## Architecture

Full architecture documentation is available in [`docs/arc42/arc42.md`](docs/arc42/arc42.md), including C4 diagrams, Architecture Decision Records (ADRs), and quality attribute scenarios.

---

## Repository Structure

```text
├── docs/                 # Architecture documentation, ADRs, diagrams, retrospectives
├── docker/               # Docker setup files
├── downloads/            # Files downloaded from peers
├── shared/               # Files shared by this peer
├── src/                  # Application source code
├── tests/                # Unit, integration, and e2e tests
├── config.py             # Runtime configuration
└── requirements.txt      # Python dependencies
```

---

## Roadmap

The following are planned improvements being developed post-course:

- **GUI** — replace the Textual TUI with a proper desktop or web-based user interface
- **DHT routing table** — replace the current flat peer list with a structured distributed hash table
- **Kademlia protocol** — implement a practical version of the Kademlia DHT algorithm for scalable, decentralized peer and file lookup

---

## License

[MIT](LICENSE)
