# ARC42 Documentation

**Project Name:** Peer-to-Peer File Sharing System

**Team Members:** Ryan Siyavudeen, Aakash Yogabalu, Md Imtiaz Ahmed, Shifan Pathan

**Date:** 31/01/2026

**Version:** 1.0

---

## Section 1: Introduction and Goals

### 1.1 Requirements Overview

_What is the system?_  
The Peer-to-Peer File Sharing System is a decentralized platform that allows users to share and download files directly with each other without relying on a central server. The system is designed to reduce bottlenecks, eliminate single points of failure, and avoid hosting costs while enabling seamless file transfer among distributed teams.

_Core Features:_

1. Peer discovery and connection management to identify and communicate with other participants.
2. File catalog sharing and search functionality among connected peers.
3. Direct file transfer between peers with support for multiple file types (whole-file transfer first. Chunking/resume is a later enhancement).

### 1.2 Quality Goals

| Priority | Quality Attribute | Motivation                                                                            |
| -------- | ----------------- | ------------------------------------------------------------------------------------- |
| 1        | Availability      | Ensure the system remains operational even if some peers go offline.                  |
| 2        | Performance       | Provide fast file transfers and responsive peer discovery to improve user experience. |
| 3        | Security          | Protect files and connections from unauthorized access or tampering.                  |

### 1.3 Stakeholders

| Role          | Description                               | Expectations                                                                                     |
| ------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------ |
| End User      | Team members or individuals sharing files | Need a reliable and easy-to-use system for discovering peers and transferring files.             |
| Administrator | Project supervisor or course instructor   | Need a documented and maintainable system that demonstrates P2P principles.                      |
| Developer     | Team members building the system          | Need a clear architecture, modular design, and well-defined responsibilities for each component. |

## Section 2: Constraints

### 2.1 Technical Constraints

| Constraint                                                                              | Explanation                                                                                                                     |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Operate on local network or localhost with multiple ports                               | The prototype can assume peers can connect directly; local network/localhost is acceptable.                                     |
| NAT traversal is not required                                                           | we assume peers can connect directly (so we don’t have to solve NAT traversal).                                                 |
| Prototype targets small files (< 10MB)                                                  | Keeps transfers manageable for a course prototype and limits performance and scale needs.                                       |
| Python version pinned (Python 3.11+)                                                    | Avoids environment mismatch and keeps async or network features consistent across the team.                                     |
| Use Python sockets for networking                                                       | Aligns with the requirements and suggested socket resource and keeps dependencies minimal.                                      |
| TCP for control and file transfer with UDP broadcast for discovery (LAN/localhost only) | Matches required peer discovery and direct transfer and fits the allowed environment assumptions.                               |
| Protocol messages are JSON and versioned                                                | Easier debugging and safer evolution across milestones.                                                                         |
| Whole file transfer first (chunking/resume optional)                                    | Initial Design will uses whole file TCP transfers. Chunking/resume may be added later to improve robustness under disconnects.  |
| File integrity verification (SHA-256 per file and optional per chunk)                   | Prevents corrupted downloads and supports reliability goals under failures.                                                     |
| Port allocation rule (configurable base port + offsets)                                 | Helps run multiple peers on localhost without collisions.                                                                       |
| DHT based routing for decentralized lookup                                              | Use a Kademlia like DHT for peer/file lookup. UDP broadcast is used only to bootstrap discovery. Manual peer add is a fallback. |

### 2.2 Organizational Constraints

| Constraint                                                   | Explanation                                                                                                                          |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| 13-week project timeline                                     | Architecture must support incremental delivery and demonstrable progress at each milestone.                                          |
| Team size: 4 Devs                                            | Limited parallel capacity. Keep modules clear and avoid over engineering.                                                            |
| Skills: Mixed experience with networking/distributed systems | Choose approachable technologies (Python sockets + JSON) and keep the protocol simple, testable, and well-documented to reduce risk. |
| Need to document key design decisions (ADRs)                 | Explicit decisions for discovery, network topology, protocol, transfers, and error handling, so time must be allocated for this.     |

### 2.3 Conventions

| Convention                                                     | Explanation                                                                                                  |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Python style: PEP 8 and consistent naming                      | Improves readability and reduces merge friction across a small team.                                         |
| Formatting enforced and linting                                | Keeps style consistent without manual policing. Catches common issues early.                                 |
| Type hints for public APIs                                     | Makes message formats and service boundaries clearer.                                                        |
| Testing convention: pytest and tests mirrored to src structure | Supports repeatable verification of discovery, search, and transfer behavior.                                |
| Documentation format: ARC42 markdown and ADR markdown          | ARC42 documentation is maintained in markdown. ADRs recorded as short markdown files to track major choices. |

---

## Section 3: Context and Scope

### 3.1 Business Context

**System Context Diagram:**
<img width="1292" height="448" alt="image" src="https://github.com/user-attachments/assets/e81c7a7a-ea8f-4eaa-bed5-92b7b9b54ec4" />

**External Interfaces:**

| Interface           | Description                                                                                                                                                                                                                                                                                   | Technology              |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| Users               | A person who utilises the file sharing system to download, send and search files on the network.                                                                                                                                                                                              | Desktop UI or CLI       |
| External P2P System | Same P2P file sharing system present on the device of users to be able to connect with other P2P systems. It enables to download and send files using chunked file transfer, search for files, other peers(P2P systems) over a local network and access cataloge of files of connected peers. | TCP, IPv4/IPv6, and UDP |

### 3.2 Technical Context

| Component                    | Purpose                                                                                                                                | Technology         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| User Interface               | Manages user interactions for searching, selecting peers/files, and tracking transfers.                                                | Desktop UI or CLI  |
| File Transfer                | Transfers files directly between peers (whole-file transfer first, chunking/resume later).                                             | TCP                |
| Encryption and Validation    | Ensures data integrity and Verifies file chunks using hashing to maintains secuirty.                                                   | SHA256             |
| Peer Discovery and Bootstrap | Bootstraps discovery using UDP announcements. Uses a Kademlia like DHT for decentralized lookup. Supports manual peer add as fallback. | UDP + TCP          |
| DHT Routing / Peer Lookup    | Locates peers (nodes) by ID using XOR distance routing (Kademlia-like).                                                                | TCP                |
| File Search                  | Enables searching for specific files by name or hash, asking peers and propagating the query.                                          | TCP                |
| Catalog Management           | Maintains an in memory index of local shared files and cached remote catalogs Optional persistence via JSON on disk.                   | Local file storage |

---

# Section 4: Solution Strategy

This section defines the architectural strategy for the Peer-to-Peer File Sharing System implemented in the referenced repository. It explains core technology decisions, the top-level decomposition of the system, and how key quality goals are achieved.

---

## 4.1 Technology Decisions

| Decision             | Choice                                                   | Rationale                                                                                                                                                                          |
| -------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Programming Language | Python 3.11+                                             | Matches team expertise and supports networking, concurrency, and UI integration efficiently.                                                                                       |
| User Interface       | Terminal User Interface (TUI)                            | Provides structured interaction (menus, panels, real-time updates) while remaining lightweight and terminal-based. Improves usability over CLI without introducing GUI complexity. |
| Networking           | Python sockets (TCP + UDP)                               | Enables direct peer-to-peer communication without central servers.                                                                                                                 |
| Message Protocol     | JSON (versioned messages)                                | Human-readable, flexible, and easy to debug and extend.                                                                                                                            |
| File Transfer        | Whole file transfer over TCP (chunking later)            | Reliable delivery using TCP; keeps initial implementation simple.                                                                                                                  |
| Peer Discovery       | UDP bootstrap with Kademlia-like DHT and manual fallback | Supports decentralized lookup and scalable peer discovery.                                                                                                                         |
| Persistence          | Local file storage / configuration                       | Simple and aligns with prototype constraints.                                                                                                                                      |
| Hashing              | SHA-256                                                  | Ensures file integrity during transfers.                                                                                                                                           |
| Testing              | pytest                                                   | Supports modular and automated testing.                                                                                                                                            |

---

## 4.2 Top-Level Decomposition

### Architectural Style

**Architectural Style:** _Layered Modular Monolith with Event-Driven Presentation Layer_

### Why This Style

We selected a Layered Modular Monolith to balance team constraints with the technical requirements of a peer-to-peer desktop application.

_Aligned with Deployment Model (Terminal-Based App)_:  
The system runs as a local process on a user’s machine. A monolithic structure avoids unnecessary distributed complexity.

_Supports Parallel Development (Team of 4)_:  
Clear modular separation (Discovery, Transfer, Storage, UI) allows team members to work independently.

_Decoupled Interface (TUI-Based Presentation Layer)_:  
The Presentation Layer is implemented as a Terminal User Interface (TUI), which provides structured navigation, real-time updates, and improved usability over a raw CLI. The UI layer is fully decoupled from networking logic, allowing future migration to a GUI without backend changes.

_Low Overhead for 13-Week Timeline_:  
Avoids the complexity of microservices or distributed internal architecture while still maintaining clean modular boundaries.

_Event-Driven Interaction Model_:  
Unlike CLI-based systems, the TUI operates through an event loop, handling user inputs, rendering updates, and background network events concurrently.

**Container Diagram:**
<img width="1181" height="681" alt="image" src="https://github.com/user-attachments/assets/3abf9443-6384-4f42-8625-f16bff0718fa" />

## 4.3 Approach to Quality Goals

| Quality Goal        | Architectural Approach                                                                                                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Availability**    | Decentralized P2P architecture eliminates single points of failure; peers can dynamically join/leave.                         |
| **Performance**     | Direct TCP transfers and local caching minimize latency; TUI updates asynchronously without blocking network operations.      |
| **Security**        | SHA-256 ensures file integrity; protocol validation prevents malformed message handling.                                      |
| **Testability**     | Modular components allow isolated unit testing; JSON protocol simplifies mocking.                                             |
| **Usability**       | TUI provides structured navigation, reducing user errors and improving interaction clarity with menus and real-time feedback. |
| **Maintainability** | Clear separation of concerns allows independent evolution of UI and core networking logic.                                    |

---

# Section 5: Building Block View

## 5.1 Level 1: Overall System

_Already shown in §3 Context Diagram_

## 5.2 Level 2: Container Internals

**Component Diagram:**

<img width="951" height="1131" alt="image" src="https://github.com/user-attachments/assets/56f5a2e2-ba15-4fd4-923d-2bc5ca9a857e" />

### Component Catalog

| Component                                | Responsibility                                                                                                      | Technology                             |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------ | :------------------------------------- |
| **`main.py` (TUI Orchestrator)**         | Entry point of the application; initializes TUI loop, networking services, and coordinates system lifecycle.        | Python, `asyncio`                      |
| **`tui/` (TUI Layer)**                   | Handles rendering of UI components (menus, peer list, file browser, transfer progress) and user interaction events. | Python (`curses` / `textual` / `rich`) |
| **`state.py` (State Manager)**           | Maintains global runtime state including peers, catalogs, and active transfers.                                     | Python                                 |
| **`catalog/` (Local Catalog)**           | Indexes local files and computes SHA-256 hashes.                                                                    | Python, `hashlib`, `pathlib`           |
| **`connection/` (Network Manager)**      | Manages TCP/UDP sockets, handles async communication and file streaming.                                            | Python, `asyncio`, `aiofiles`          |
| **`identification/` (Identity Manager)** | Generates and manages unique peer IDs using Strategy pattern (RSA/UUID).                                            | Python, `cryptography`                 |
| **`protocol/` (Protocol & Discovery)**   | Handles UDP discovery and parsing of JSON messages.                                                                 | Python, `json`                         |
| **`queries/` (Search Engine)**           | Executes file search across peers and cached catalogs.                                                              | Python                                 |
| **`security/` (Keyring Access)**         | Manages secure storage of credentials and keys.                                                                     | Python, `keyring`                      |

## 5.3 Design Patterns Applied

| Pattern                         | Where Applied                             | Rationale                                                                                                                                                                                                                                                                                                                                                                          |
| :------------------------------ | :---------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factory Method (Creational)** | `src/protocol/message_handler_factory.py` | Decouples message parsing from logic execution. The `MessageHandlerFactory` evaluates the `type` field of incoming JSON messages to dynamically instantiate the appropriate `MessageHandler` (e.g., `PingHandler`, `FileReqHandler`). This allows the protocol to be extended with new message types without modifying the core connection management loop.                        |
| **Strategy (Behavioral)**       | `src/identification/`                     | Encapsulates the Peer ID generation logic. Using the `PeerIdStrategy` interface, the system can swap between `Primary_Identity` (RSA-based) and `FallBack_Id` (UUID-based) at runtime via the `PeerID_Context`. This ensures that the application can adapt to different security requirements or environment constraints without changing the initialization flow.                |
| **Singleton (Creational)**      | `src/state.py`                            | Ensures a single, globally accessible point of truth for application state. By leveraging Python's native module caching, `state.py` acts as a Singleton, managing the `peers` registry and the `local_catalog`. This prevents data inconsistency across the various asynchronous tasks (TCP server, UDP listener, and CLI) that must concurrently access and modify system state. |

---

# Section 6: Runtime View

> **Due: M4 (Week 10)**

## 6.1 Scenario: [Primary Use Case]

**Description:** This primary use case illustrates how a node requests and receives a file from a connected peer using the refactored, SOLID-compliant architecture. The user issues a command which is parsed and routed by the `TUIhandler`. The handler fetches the peer's writer from the injected `AppState` and sends a `FILE_REQUEST`. On the receiving node, the `ConnectionHandler` reads the message, routes it through the Factory, and passes the resulting `FileResponseData` to the `MessageDispatcher`. The dispatcher streams the raw bytes back to the requester, where it is saved and the hash is verified.

**Sequence Diagram:**

<img width="1410" height="801" alt="image" src="https://github.com/user-attachments/assets/6d5c2d29-a51f-4478-8f7d-7d1cbcb24786" />

## 6.2 Scenario: [Second Use Case]

**Description:** This scenario demonstrates how a new node joins the network and establishes its initial state using the refactored, SOLID-compliant architecture. The process begins when a User activates discovery via the TUI Layer, prompting the Discovery Service to broadcast its presence via UDP. When an existing node receives the `ANNOUNCE` packet, its `ConnectionHandler` initiates a TCP connection. They exchange `CATALOG_REQUEST` and `CATALOG_RESPONSE` messages. Once the payload is validated and parsed by the Factory, the `PeerRegistry` handles the single responsibility of upserting the new peer's catalog into the injected `AppState`, and a Heartbeat loop is started. Finally, the Discovery Service updates the TUI, allowing the User to view the newly connected peers.

**Sequence Diagram:**

<img width="1324" height="921" alt="image" src="https://github.com/user-attachments/assets/78167f1f-c98d-4cf6-be57-337097076ba6" />

## 6.3 Scenario: [Change Scenario Response]

**Change Requested:** A comprehensive architectural refactor was required to resolve systemic violations of the SOLID principles—specifically Single Responsibility (SRP), Open/Closed (OCP), Dependency Inversion (DIP), and Interface Segregation (ISP). The goal was to move away from procedural "God-functions" and global state variables toward a modular, testable, and extensible design.

**How Architecture Accommodated It:** The system's new architecture utilizes **Dependency Injection** and the **Factory Method** pattern to decouple components. By defining clear interfaces (such as the `MessageHandler` and `PeerIdStrategy`) and passing dependencies like `AppState` through constructors, the system can now be extended with new protocols or identity methods without modifying the core orchestration logic.

**What Had to Change:**

1.  **Orchestration Logic (`main.py` & `TUI Layer`):** The previous monolithic CLI loop was replaced with an event-driven TUI architecture. This allows the `main()` function to focus strictly on the lifecycle of the event loop and server startup (SRP), while new commands can be added to the handler without breaking existing ones (OCP).
2.  **State Encapsulation (`state.py`):** We transitioned from using `global` keywords and scattered variables to a centralized `AppState` model. This allows the state to be injected into handlers, making the system easier to unit test with "mock" states and ensuring that data mutations are controlled and predictable.

3.  **Protocol Handling (`manager.py` & `MessageHandlerFactory`):** The original `handle_connection` function, which contained a large `if/elif` chain for message types, was replaced. We implemented a `MessageHandlerFactory` that returns specific strategy objects (e.g., `FileReqHandler`, `CatalogResHandler`). This ensures that adding a new message type only requires creating a new class, rather than modifying the core networking loop (OCP).

4.  **Identity Strategy:**
    By implementing the `PeerIdStrategy` interface, we separated the logic for generating IDs (RSA-based vs. UUID-based). This allows the application to swap identity modes at runtime via the `PeerID_Context` without the rest of the system needing to know how the ID was generated (DIP).

---

# Section 7: Deployment View

## 7.1 Infrastructure

**Deployment Diagram:**

<img width="1023" height="635" alt="image" src="https://github.com/user-attachments/assets/3ca27cfe-71ca-4ec1-9cc0-d90703b6bd31" />

## 7.2 Component-to-Infrastructure Mapping

| Component                         | Deployed On                | Notes                                                                                                                                                      |
| :-------------------------------- | :------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TCP Server (`manager.py`)**     | Host Network Interface     | Binds to `0.0.0.0` on the user-specified port to accept direct, bidirectional peer connections.                                                            |
| **UDP Discovery (`protocol`)**    | Local Network Gateway      | Sends and listens for periodic broadcast packets to resolve peer IP addresses natively on the LAN.                                                         |
| **File Indexer (`catalog.py`)**   | Host Storage Disk          | Scans `SHARED_FOLDER` and writes to `DOWNLOADS_FOLDER`, requiring local read/write I/O access.                                                             |
| **Identity Manager (`Security`)** | OS Secure Credential Store | Integrates with the native OS keyring (e.g., Windows Credential Manager, macOS Keychain) to store the RSA private key passphrase securely.                 |
| **TUI Interface (`main.py`)**     | Host OS Execution Thread   | Runs in an isolated thread (`run_in_executor`) or specialized UI event loop to prevent the user interface from blocking the core `asyncio` network events. |

## 7.3 Configuration

| Environment     | Configuration                                                                      | Purpose                                                                                                                    |
| :-------------- | :--------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| **Development** | `MODE = 0` (Fallback ID), Localhost IPs (`127.0.0.1`), Mock directories.           | Allows for rapid, localized testing using standard UUIDs without the overhead of generating or storing cryptographic keys. |
| **Production**  | `MODE = 1` (Primary Identity), Auto-resolved LAN IPs, OS-backed secret management. | Enforces secure, verifiable RSA-based peer identification and dynamic network discovery for real-world deployment.         |

---

# Section 8: Crosscutting Concepts

## 8.1 Domain Model

**Domain Model:**

<img width="452" height="922" alt="image" src="https://github.com/user-attachments/assets/bc2785d8-360d-4a7f-86ea-11515fa727a5" />

### Key Entities

| Entity           | Description                                                                                                 | Key Attributes                                    |
| :--------------- | :---------------------------------------------------------------------------------------------------------- | :------------------------------------------------ |
| **AppState**     | The central singleton maintaining the node's local identity, network settings, and indexed shared files.    | `PEER_ID_STUB`, `host`, `port`, `local_catalog`   |
| **PeerRegistry** | A logical component that manages the lifecycle of remote nodes within the global state registry.            | `peers`                                           |
| **PeerNode**     | Represents a discovered participant in the network, including its connection metadata and remote file list. | `peer_id`, `host`, `port`, `last_pong`, `catalog` |
| **CatalogEntry** | A standardized metadata record for a file, using a unique hash identifier.                                  | `file_id` (SHA-256), `name`, `size`               |
| **Message**      | The fundamental communication unit for all network packets, adhering to a defined protocol schema.          | `type`, `version`, `peer_id`                      |

## 8.2 Error Handling

How does the system handle errors consistently?

| Error Type          | Handling Strategy                                                                                                                                                                                    |
| :------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Protocol Format** | Incoming JSON is validated against a strict schema. If fields are missing or the version is unsupported, an `ERROR` message is sent back to the peer with the code `INCORRECT_PROTOCOL_FORMAT`.      |
| **Connection Loss** | The `heartbeat_loop` monitors liveness. If a peer fails to respond to pings, the `asyncio.StreamWriter` is closed, and the peer is purged from the global state.                                     |
| **Data Corruption** | After a file transfer, the system re-computes the SHA-256 hash. If it does not match the `file_id`, the file is deleted from the `DOWNLOADS_FOLDER` and the mismatch is logged.                      |
| **Disk/OS Errors**  | Operations involving file I/O (hashing, reading, writing) or secure keyring access use `try-except` blocks to catch `OSError` or `FileNotFoundError`, logging the failure without crashing the node. |

## 8.3 Logging and Monitoring

| Aspect         | Approach                                                                                                                                                                                             |
| :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Log format** | Uses a consistent string-based format with component-specific tags, such as `[HEARTBEAT]`, `[HASH_CHECK]`, or `[PONG]`, to simplify log filtering.                                                   |
| **Log levels** | Employs `DEBUG` for high-frequency events like heartbeats, `INFO` for major lifecycle events like connection handshakes, and `WARNING`/`ERROR` for protocol violations or failed file verifications. |
| **Monitoring** | The system monitors network health by tracking the `last_pong` timestamp for every connected peer in the global state. If the gap exceeds a defined deadline, the peer is marked as offline.         |

## 8.4 Security

| Concern             | Approach                                                                                                                                                                |
| :------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Authentication**  | Cryptographic identities are established using RSA-2048 key pairs. A peer's unique ID is derived from a SHA-256 hash of their public key, ensuring verifiable identity. |
| **Authorization**   | The application limits network access to two specific directories: the `SHARED_FOLDER` for outbound transfers and the `DOWNLOADS_FOLDER` for inbound files.             |
| **Data protection** | Private keys are never stored in plain text. They are encrypted using an AES-based algorithm with a passphrase managed by the OS-native secure keyring.                 |

## 8.5 Testing Strategy

| Test Type       | Scope                                                                                                                             | Tools                       |
| :-------------- | :-------------------------------------------------------------------------------------------------------------------------------- | :-------------------------- |
| **Unit**        | Validating SHA-256 hash computation, JSON serialization logic, and protocol field requirements.                                   | `pytest` / `unittest`       |
| **Integration** | Verifying that the `MessageHandlerFactory` correctly routes different message types to their respective handlers.                 | `asyncio.test_utils`        |
| **End-to-end**  | Simulating a full discovery and transfer cycle: UDP announcement, TCP handshake, catalog exchange, and file download via the TUI. | Local multi-node simulation |

---

# ADR Index

Architecture Decision Records are maintained separately. See `docs/ADRs/`.

| ADR     | Title                                                               | Date       | Status   |
| ------- | ------------------------------------------------------------------- | ---------- | -------- |
| ADR-001 | Peer Discovery via UDP Broadcast with Pluggable Discovery Providers | 2026-02-01 | Accepted |
| ADR-002 | Use TCP for Control, Search, and Transfer; UDP for Discovery        | 2026-02-01 | Proposed |
| ADR-003 | Minimal Kademlia-like DHT for Lookup and Routing                    | 2026-02-07 | Accepted |
| ADR-004 | File Identity using SHA-256 Hash                                    | 2026-02-07 | Accepted |
| ADR-005 | Peer Liveness using Heartbeats + TTL                                | 2026-02-07 | Accepted |
| ADR-006 | Secure Cryptographic Peer ID (SCID)                                 | 2026-04-04 | Accepted |
| ADR-007 | Asyncio for Concurrent Network I/O                                  | 2026-04-04 | Accepted |
| ADR-008 | Secure Storage of Private Key via OS Keyring                        | 2026-04-04 | Accepted |

---

# Glossary

| Term                         | Definition                                                                        |
| ---------------------------- | --------------------------------------------------------------------------------- |
| Peer                         | A node in the P2P network capable of sharing and downloading files                |
| P2P (Peer-to-Peer)           | A decentralized network where nodes communicate directly without a central server |
| DHT (Distributed Hash Table) | A decentralized lookup system used to find peers or data efficiently              |
| SCID                         | Secure Cryptographic ID derived from hashing a public key                         |
| Catalog                      | Metadata list of files shared by a peer                                           |
| File ID                      | SHA-256 hash uniquely identifying a file                                          |
| Heartbeat                    | Periodic ping/pong messages to check if a peer is alive                           |
| TTL (Time-To-Live)           | Expiry time for cached data such as peer info or file mappings                    |
| TUI                          | Terminal User Interface for interacting with the system                           |
| Message Handler              | Component responsible for processing protocol messages                            |
| Discovery                    | Process of finding other peers in the network                                     |
| Bootstrap                    | Initial step to connect to the network (via UDP broadcast or manual entry)        |

---

# Document History

| Version | Date       | Author | Changes                                                                                            |
| ------- | ---------- | ------ | -------------------------------------------------------------------------------------------------- |
| 1.0     | 2026-01-31 | Team   | Initial M1 submission (§1–2)                                                                       |
| 2.0     | 2026-02-15 | Team   | Added context, constraints, and solution strategy (§3–4)                                           |
| 3.0     | 2026-03-01 | Team   | Added building block view and component structure (§5)                                             |
| 4.0     | 2026-03-20 | Team   | Added runtime scenarios and sequence diagrams (§6)                                                 |
| 5.0     | 2026-04-01 | Team   | Added deployment view and infrastructure (§7)                                                      |
| 6.0     | 2026-04-06 | Team   | Final submission with domain model, error handling, logging, security, and testing (§1–8 complete) |

---

## References

- [ARC42 Template](https://arc42.org/overview)
- [C4 Model](https://c4model.com/)
- [Course ADR Template](../adrs/ADR-000-template.md)
- [Milestone Requirements](../MILESTONE_MAPPING.md)
