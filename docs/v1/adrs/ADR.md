
# ADR-001: Peer Discovery via UDP Broadcast with Pluggable Discovery Providers

**Date:** 2026-02-01

**Status:** Accepted

**Deciders:** Ryan Siyavudeen, Aakash Yogabalu, Shifan Pathan 

**Quality Attribute(s):** Modifiability, Performance

---

## Context

This project must support peer discovery in a **P2P** network with **no central server**, while still working within the prototype constraints (LAN/localhost, no NAT traversal).  
ARC42 already constrains us to **UDP broadcast for discovery** and defines the environment as **LAN/localhost only**. 
We also have a modifiability driver: we should be able to add a new discovery method (ex: “Manual IP Entry”) with minimal ripple effect. 

**Key questions we needed to answer:**

* What discovery mechanism fits the prototype constraints (LAN/localhost, no NAT traversal)? 
* How do we keep discovery **changeable** (add new methods later) without touching transfer/search code? 
* How do we keep the design aligned with the requirement to document discovery decisions in ADRs? 

---

## Decision

**We will use UDP broadcast as the default peer discovery mechanism, and implement discovery as a pluggable provider selected by configuration.**  

Key aspects:

* The discovery subsystem exposes a common interface (ex: `DiscoveryProvider`) that returns discovered peers (IP + port + peer id). 
* Adding new discovery methods (ex: Manual IP Entry) is done as a separate module. Selection happens at startup via configuration (defer binding time). 

---

## Alternatives Considered

### Option 1: UDP Broadcast Discovery (Chosen)

**Description:** Peers broadcast presence on LAN/localhost, others listen and populate a peer list.  

**Pros:**

* Fits prototype constraints (LAN/localhost, no NAT traversal). 
* Simple and fast for local peer discovery.

**Cons:**

* Broadcast may not cross network boundaries/subnets (depends on network setup), so “manual IP” may still be needed later. 

### Option 2: Central Tracker / Directory Server

**Description:** A single server keeps a list of peers and returns them to clients.

**Pros:**

* Works across more network setups than broadcast.
* Simpler peer discovery logic for clients.

**Cons:**

* Conflicts with the project constraint of no central coordination (or minimal coordination). 
* Introduces a single point of failure.

### Option 3: DHT-Based Discovery

**Description:** Fully decentralized lookup (distributed hash table) for peer discovery.

**Pros:**

* Scales well in “real” P2P systems.
* No central server.

**Cons:**

* Too complex for a course prototype and would increase implementation + testing risk (13-week timeline). 

---

## Consequences

### Positive

* Meets the prototype constraint: UDP broadcast discovery on LAN/localhost. 
* Supports QAS-03 modifiability goals by isolating discovery logic and selecting it via configuration. 
* Keeps discovery separate from file transfer/search logic, reducing ripple effects. 

### Negative

* Discovery may fail across subnets. Users may need a non-broadcast method (ex: Manual IP Entry) if their network blocks broadcasts. 
* Adds a bit of design overhead (provider interface + config selection), but it’s justified by QAS-03. 

### Risks

* **Risk:** Broadcast spam or noisy peer lists as peer count grows.

  * **Mitigation:** Add rate-limiting and deduplication. Keep announcements periodic with a TTL.
* **Risk:** Confusion about “different networks” vs LAN scope.

  * **Mitigation:** Document that broadcast is LAN/localhost only, and treat manual IP entry as an optional provider within reachable networks (no NAT traversal).  

---

## Related Decisions

* ADR-002: Use TCP for control/search/transfer, UDP reserved for discovery only. 

---

## Notes

* This ADR directly matches the “Peer discovery mechanism” decision area called out in the project requirements. 

---

# ADR-002: Use TCP for Control, Peer/File Search, and File Transfer. Use UDP Only for Discovery

**Date:** 2026-02-01

**Status:** Proposed

**Deciders:** Ryan Siyavudeen, Aakash Yogabalu, Md Imtiaz Ahmed

**Quality Attribute(s):** Reliability, Performance

---

## Context

The system must support:

* peer discovery, catalog sharing, and search,
* direct file transfers,
* and peers joining/leaving gracefully. 

ARC42 explicitly constrains protocol usage: **TCP for control + file transfer**, and **UDP broadcast for discovery**. 
Your technical context also maps **peer search** and **file search** to TCP, and peer discovery to UDP. 

**Key questions we needed to answer:**

* Which protocol(s) do we use for reliable operations like search and file transfer? 
* How do we keep discovery lightweight while ensuring transfer correctness? 
* How do we align with the project’s explicitly listed “network protocol” decision requirement? 

---

## Decision

**We will use TCP for control messages, peer/file search communication, and chunked file transfer. We will use UDP only for broadcast-based peer discovery.**  

Key aspects:

* Peer search and file search use TCP (fits the technical context mapping). 
* File transfer uses TCP and supports chunking/resume and integrity verification (separate ADR covers details).  
* UDP is not used for stateful communication, it’s limited to discovery broadcasts. 

---

## Alternatives Considered

### Option 1: TCP for Control/Search/Transfer + UDP for Discovery (Chosen)

**Description:** TCP handles all reliable operations, UDP broadcast only finds peers. 

**Pros:**

* Matches ARC42 constraints exactly. 
* Simplifies correctness for transfers and search propagation (reliable delivery, ordering).
* Aligns with the technical context mapping (TCP for search/transfer, UDP for discovery). 

**Cons:**

* More TCP connections/state to manage.
* Potential performance bottlenecks if connections are not managed carefully (timeouts, pooling, concurrency limits).

### Option 2: UDP for Search Propagation + TCP for Transfers

**Description:** Use UDP messages to flood searches quickly, use TCP only for downloads.

**Pros:**

* Potentially faster broadcast-style search propagation.
* Lower overhead per search message.

**Cons:**

* Higher complexity (loss, ordering, deduplication, retry logic).
* Harder to test and debug for a course prototype.

### Option 3: TCP for Everything (Including Discovery)

**Description:** Use TCP connections for discovery (ex: connect to candidate ports / brute-force scan within localhost ranges).

**Pros:**

* Single protocol, simpler mental model.
* Avoids UDP broadcast restrictions on some networks.

**Cons:**

* Much more connection overhead for discovery.
* Doesn’t match the ARC42 constraint calling for UDP broadcast discovery. 

---

## Consequences

### Positive

* Stronger reliability for search and transfers using TCP. 
* Keeps discovery lightweight and decoupled from stateful communication. 
* Matches the explicit protocol decision area required in the project requirements. 

### Negative

* TCP connection management adds complexity (connection lifecycle, timeouts, concurrency).
* Under high peer counts, naive designs could create many simultaneous sockets.

### Risks

* **Risk:** Search traffic could delay transfers if everything shares the same threads/resources.

  * **Mitigation:** Use asynchronous or concurrent handling for search vs transfer (aligned with the performance driver approach in QAS-01). 
* **Risk:** UDP discovery blocked by certain LAN policies.

  * **Mitigation:** Support a secondary discovery provider (manual IP entry) per ADR-001/QAS-03. 

---

## Related Decisions

* ADR-001: Peer Discovery via UDP Broadcast with Pluggable Discovery Providers.  

---

## Notes

* This ADR stays consistent with the documented technical context table (UDP for discovery, TCP for search and transfer). 


# ADR-003: Minimal Kademlia-like DHT Scope for Lookup and Routing

**Date:** 2026-02-07  
**Status:** Accepted  
**Deciders:** Ryan Siyavudeen, Aakash Yogabalu, Shifan Pathan  
**Quality Attribute(s):** Performance, Scalability, Modifiability  

## Context
The system requires decentralized peer discovery/lookup and search without a central tracker. UDP broadcast is used only for bootstrap and is not good to do scalable lookup. A full Kademlia implementation is too complex for a prototype but minimal subsets can provide efficient routing and distributed storage of file availability.

## Decision
Implement a **minimal Kademlia-like DHT** with the following scope:

- **Node ID:** 160-bit hash-based identifier (e.g., SHA-1 or SHA-256 truncated to 160 bits).
- **Distance metric:** XOR distance.
- **Routing table:** k-buckets organized by XOR distance (simplified allowed, but must be distance-based).
- **RPC set:**
  - `FIND_NODE(target_id)` – return closest known nodes to `target_id`
  - `FIND_VALUE(key)` – return stored value for `key`, or closest nodes if not found
  - `STORE(key, value)` – store `value` under `key`
- **Stored data model:** DHT stores **file availability mappings** (e.g., `file_id -> [peer endpoints]`) with **TTL**.
- **Replication:** store values to the **k closest nodes**
## Alternatives Considered
1. **UDP broadcast-only discovery/search**
   - Pros: very simple
   - Cons: does not scale, can be blocked, encourages flooding
2. **Central tracker**
   - Pros: easy to implement
   - Cons: breaks decentralization single point of failure
3. **Full Kademlia**
   - Pros: robust and scalable
   - Cons: too large in scope for this course project

## Consequences
### Positive
- Reduces broadcast/flooding for lookup/search.
- Clear separation between bootstrap (UDP) and routing/lookup (DHT).
- Modifiable design: DHT module can evolve independently.

### Negative
- Increased complexity compared to UDP-only.
- Requires careful testing for routing and expiry behavior.

## Notes
- NAT traversal is out of scope. Implementation targets LAN/localhost scenarios.
- DHT entries must expire (TTL) to reduce stale search results.


---

# ADR-004: File Identity and Catalog Metadata (Hash-Based file_id)

**Date:** 2026-02-07  
**Status:** Accepted  
**Deciders:** Ryan Siyavudeen, Aakash Yogabalu, Shifan Pathan  
**Quality Attribute(s):** Correctness, Integrity, Usability  

## Context
Peers advertise and search for files across the network. Filenames are not unique and can collide across peers. A stable identifier is required for:
- uniquely referencing files during transfer,
- verifying integrity after download,
- avoiding confusion when multiple files share the same name.

## Decision
- Define `file_id` as **SHA-256(file bytes)**.
- Advertised catalog entries must include:
  - `file_id`, `name`, `size` (and optional `mtime` for future UI improvements).
- On download completion, compute SHA-256 of received bytes and compare to the expected `file_id`/checksum.

## Alternatives Considered
1. **Filename as ID**
   - Pros: simple
   - Cons: collisions, unsafe, ambiguous
2. **(name, size, something) tuple**
   - Pros: easy to compute
   - Cons: still ambiguous, not a true integrity check
3. **Hash of file bytes (Chosen)**
   - Pros: stable identity, supports integrity verification, de-duplicates identical content
   - Cons: requires reading file content to compute hash

## Consequences
### Positive
- Strong integrity check for transfers.
- Avoids filename collision problems.
- Enables content based de-duplication (same content maps to same ID).

### Negative
- Hash computation cost.


---

# ADR-005: Peer Liveness and Stale Data Handling (Heartbeats + TTL)

**Date:** 2026-02-07  
**Status:** Accepted  
**Deciders:** Ryan Siyavudeen, Aakash Yogabalu, Md Imtiaz Ahmed  
**Quality Attribute(s):** Availability, Reliability, Correctness  

## Context
Peers can join/leave at any moment. Search results and DHT mappings become invalid if peer disappears. The system handle churn gracefully without requiring clean shutdowns.

## Decision
- Maintain TCP connection liveness using periodic **heartbeats** (`PING/PONG`) between connected peers.
- If a peer misses **N** consecutive heartbeats (default: 3), treat it as offline:
  - close connection,
  - remove cached advertisements associated with that peer locally.
- DHT key/value entries must include a **TTL/expiry**:
  - expired values are ignored/removed,
  - active peers refresh/republish periodically.

## Alternatives Considered
1. **No heartbeats. Rely on socket errors only**
   - Pros: simplest
   - Cons: slow failure detection, stale state persists
2. **Heartbeats without TTL**
   - Pros: detects connection failure
   - Cons: DHT can still accumulate stale values
3. **Heartbeats + TTL (Chosen)**
   - Pros: timely failure detection. Stale DHT data fades out
   - Cons: requires periodic timers and cleanup logic

## Consequences
### Positive
- More accurate search results during churn.
- Faster detection of dead peers.
- DHT remains cleaner over time.

### Negative
- Additional periodic background tasks/timers.

---

# ADR-006: Use Secure Cryptographic ID (SCID) for Peer Identification

**Date:** 2026-04-04

**Status:** Accepted

**Deciders:** Md Imtiaz Ahmed

**Quality Attribute(s):** Security, Reliability, Extensibility

### Context

In our decentralized P2P file-sharing application, every node requires a unique identifier (`peer_id`). This identifier is critical for tracking active connections, preventing a node from connecting to itself, maintaining routing tables, and ensuring that file requests are sent to the correct peer. 

Because peers in a localized or distributed network can drop offline, change IP addresses (due to DHCP or switching networks), or operate behind NATs, we cannot rely on transient network routing data as an identity. Furthermore, as the network scales, we need a mechanism that protects against identity spoofing, where a malicious node might impersonate a trusted peer. 

**Key questions we needed to answer:**
1. How do we guarantee global uniqueness for a node's identity?
2. How do we ensure that an identity remains stable even if the peer's network location (IP/Port) changes?
3. How can we lay the groundwork for a verifiable, trustless network where messages can eventually be authenticated?

### Decision

We will use a **Secure Cryptographic ID (SCID)** as the primary `peer_id` for all network nodes. 

Specifically, we will generate a 2048-bit RSA key pair at node startup (storing the private key securely using the OS keyring) and derive the `peer_id` by calculating the SHA-256 hash of the node's public key. To ensure robustness, we will utilize a Strategy Pattern that gracefully falls back to a UUID v4 identity if the primary cryptographic generation fails or is unsupported by the host environment.

### Alternatives Considered

#### Option 1: SCID (SHA-256 of RSA Public Key)
**Description:** Generate an RSA key pair and hash the public key to create a fixed-length hexadecimal string.
* **Pros:**
    * **Cryptographic Proof:** The peer can prove ownership of its ID by signing messages with its private key (essential for future security goals).
    * **High Collision Resistance:** SHA-256 ensures global uniqueness.
    * **Industry Standard:** Mimics the identity generation mechanisms used by robust decentralized protocols like IPFS and Bitcoin.
* **Cons:**
    * **Computational Overhead:** RSA key generation takes time on initial startup.
    * **Storage Complexity:** Requires secure storage for the private key and passphrase management (via `keyring`).

#### Option 2: UUID v4
**Description:** Generate a random universally unique identifier using the standard UUID library.
* **Pros:**
    * Extremely fast and lightweight to generate.
    * Requires no persistent storage or OS-level secret management; can be generated statelessly.
* **Cons:**
    * **Zero Security:** A UUID provides no mechanism to verify the identity of the sender. A malicious peer can simply copy another node's UUID and impersonate them on the network.
    * Cannot support future requirements for message signing or encryption.

#### Option 3: Hash of IP Address and Port (IP:Port)
**Description:** Create a deterministic ID by hashing the node's current localized IP address and its listening port.
* **Pros:**
    * Trivially easy to generate and deterministic.
    * Automatically correlates identity with network routing location.
* **Cons:**
    * **Highly Unstable:** If a peer's IP address changes (e.g., moving from Wi-Fi to cellular, or DHCP lease renewal), their identity is lost, breaking all cached catalogs and connection histories.
    * **NAT Issues:** Multiple peers running behind the same router/NAT might appear to have the same public IP, causing massive collision issues.
    * Easily spoofed by anyone who knows the target's IP and port.

### Consequences

**Positive**
* **Spoof-Proof Identity:** The network has a strong foundation for security. By tying the `peer_id` to a public key, we guarantee that no other node can impersonate a peer without compromising their local private key.
* **Extensibility:** We are perfectly positioned to implement message signing and payload encryption in future milestones without changing the protocol schema.
* **Network Stability:** A peer's identity persists seamlessly across network disconnects, IP changes, and system reboots.

**Negative**
* We accept the added complexity of integrating with the host operating system's native keyring to manage the private key passphrase.
* Initial node startup is slightly slower during the first run while the 2048-bit RSA keys are computed.

### Risks

* **Risk:** The `keyring` library might fail or be blocked by permissions on certain Linux distributions or headless servers.
    * **Mitigation:** We implemented the `PeerID_Context` Strategy Pattern. If `Primary_Identity` (RSA/SCID) fails, the system automatically shifts to `FallBack_Id` (UUID v4) to ensure the application does not crash and remains functional, albeit with reduced security guarantees.

### Related Decisions
* **Design Pattern Implementation:** Strategy Pattern used in `src/identification/` to swap between SCID and UUID. 
* **Singleton State:** The generated SCID is cached in `state.PEER_ID_STUB` for global access across the application lifecycle.

---

# ADR-007: Use Asyncio for Concurrent Network I/O and State Management

**Date:** 2026-04-04

**Status:** Accepted

**Deciders:** Md Imtiaz Ahmed

**Quality Attribute(s):** Performance (I/O Concurrency), Maintainability, Reliability (Deadlock Prevention)

### Context

Our P2P file-sharing node must handle multiple simultaneous operations: listening for UDP discovery broadcasts, maintaining active TCP connections for multiple peers, streaming large file downloads/uploads, and accepting user input via a CLI. 

Because we are utilizing a globally shared Singleton state (`src/state.py` containing the `peers` dictionary and `local_catalog`), concurrent read/write access to this state is a primary architectural concern. We needed to choose a concurrency model that supports high I/O throughput without risking data corruption or deadlocks.

**Key questions we needed to answer:**
1. How do we safely manage concurrent reads and mutations to `state.peers` without introducing race conditions?
2. Which concurrency model handles Python's Global Interpreter Lock (GIL) best for highly I/O-bound networking tasks?
3. How do we keep the application responsive to the CLI while simultaneously streaming large files?

### Decision

We will use Python's **`asyncio`** library as our primary concurrency model, utilizing an event-driven, single-threaded cooperative multitasking loop. 

All network operations (TCP/UDP) and file I/O (via `aiofiles`) will be written as asynchronous coroutines. We will completely avoid using `threading.Lock` for our shared state. The only exception to the single-thread rule will be the CLI `input()` loop, which inherently blocks and will be offloaded to a background thread using `loop.run_in_executor()`.

### Alternatives Considered

#### Option 1: Asyncio (Event-Driven Cooperative Multitasking)
**Description:** A single-threaded event loop that switches context whenever an `await` is reached (e.g., waiting for network packets or disk reads).
* **Pros:**
    * **No Thread Locks Required:** Because Python's `asyncio` runs on a single thread, synchronous operations (like updating a dictionary in memory) cannot be interrupted by another task. We can update `state.peers` safely without `Lock`, `RLock`, or `Semaphore` objects.
    * **Lightweight:** Coroutines use drastically less memory and have faster context-switch times compared to OS-level threads.
    * **Native TCP/UDP Support:** `asyncio` provides robust built-in stream readers/writers and datagram protocols.
* **Cons:**
    * **"Async Creep":** The entire core architecture must be written with `async`/`await` syntax.
    * **Blocking Vulnerability:** A single synchronous blocking call (like standard `time.sleep()` or `open().read()`) will freeze the entire node.

#### Option 2: Multithreading with `threading.Lock`
**Description:** Spawning a new OS-level thread for every peer connection and protecting shared state with thread locks.
* **Pros:**
    * Allows the use of traditional, synchronous socket programming and standard file I/O.
    * Blocking operations in one thread do not freeze the others.
* **Cons:**
    * **Deadlocks and Race Conditions:** Forgetting to acquire or release a lock around `state.peers` or `state.local_catalog` would lead to silent data corruption or application freezing.
    * **GIL Bottlenecks:** Python's Global Interpreter Lock prevents true parallel execution of Python bytecode, meaning threads mostly just trade places during I/O waiting anyway.
    * **Resource Heavy:** Hundreds of connected peers would mean hundreds of OS threads, consuming significant memory.

#### Option 3: Multiprocessing
**Description:** Spawning entirely separate Python processes for the CLI, TCP server, and UDP listeners.
* **Pros:**
    * Bypasses the GIL entirely, utilizing multiple CPU cores.
* **Cons:**
    * **State Isolation:** Processes do not share memory natively. Maintaining the `state.py` Singleton across processes would require complex Inter-Process Communication (IPC), shared memory blocks, or a local Redis instance—adding massive, unnecessary overhead to a 14-week project.

### Consequences

**Positive**
* **Simplified State Management:** By eliminating the need for `threading.Lock`, the codebase remains clean. Functions like `_upsert_peer` in `manager.py` can modify dictionaries natively without fear of race conditions.
* **High Scalability:** The node can comfortably handle thousands of simultaneous TCP connections and Heartbeat tasks since they are just lightweight coroutines.
* **Clean Orchestration:** We successfully bridged the synchronous CLI and the asynchronous server using `run_in_executor()`, getting the best of both worlds without risking the core event loop.

**Negative**
* **Dependency on `aiofiles`:** We had to introduce a third-party dependency (`aiofiles`) to ensure that file reading/writing during downloads/uploads did not block the network event loop.
* **Learning Curve:** Managing task lifecycles (e.g., properly awaiting tasks, handling `asyncio.CancelledError` on shutdown) required careful architectural planning.

### Risks

* **Risk:** An inadvertent synchronous call (like a large `hashlib.sha256` calculation on a massive file) could block the event loop, causing Heartbeats or peer requests to time out.
    * **Mitigation:** Heavy synchronous computations like `compute_file_id()` or `verify_file_hash()` process files in small, strictly defined chunks (e.g., 8192 bytes). If hashing extremely large files becomes an issue in the future, these specific functions can also be deferred to `run_in_executor()`.

### Related Decisions
* **ADR-001:** Use Secure Cryptographic ID (SCID) for Peer Identification
* **Architecture Section 5.3:** Singleton Pattern applied to `state.py` relies directly on the thread-safety guarantees provided by `asyncio`.

---

# ADR-008: Secure Storage of RSA Private Key via OS Keyring

**Date:** 2026-04-04

**Status:** Accepted

**Deciders:** Md Imtiaz Ahmed

**Quality Attribute(s):** Security (Data Confidentiality), Usability (Automated Startup), Reliability

### Context

As decided in ADR-006, our P2P nodes utilize a Secure Cryptographic ID (SCID) derived from a 2048-bit RSA key pair. While the public key is shared freely, the private key must be kept strictly confidential. If a malicious actor gains access to a node's private key, they can fully impersonate that node on the network.

However, the P2P application is designed to run in the background and automatically restart or reconnect without constant user intervention. 

**Key questions we needed to answer:**
1. How do we protect the RSA private key file stored on the local disk from unauthorized access or malware?
2. How do we decrypt the private key automatically when the application starts, without halting the startup sequence to prompt the user for a password?
3. How do we manage this across different operating systems (Windows, macOS, Linux) consistently?

### Decision

We will store the RSA private key as an **encrypted PEM file** on the local filesystem (`~/scid/private_key.pem`), and we will store the passphrase required to decrypt it inside the **operating system's native credential store (Keyring/Keychain)**.

We will use the Python `keyring` library to interface with the OS. On initial startup, if no passphrase exists, the application will generate a cryptographically secure 32-byte random token (`secrets.token_bytes(32)`), encode it securely, and save it to the OS keychain under the service name `scid-app`. This passphrase is then used to encrypt the PEM file. On subsequent startups, the application will silently retrieve this passphrase from the OS keyring to unlock the key.

### Alternatives Considered

#### Option 1: Plaintext PEM File
**Description:** Store the RSA private key in a standard, unencrypted `.pem` file on the hard drive.
* **Pros:** Extremely simple to implement; requires zero external dependencies; fast startup.
* **Cons:** **Highly Insecure.** Any local process, script, or malware with user-level read permissions can steal the private key and permanently compromise the node's identity.

#### Option 2: User-Prompted Password
**Description:** Encrypt the PEM file with a user-defined password. Every time the P2P application launches, the CLI blocks and asks the user to manually type the password.
* **Pros:** Very secure. The key is only decrypted in RAM when the user explicitly authorizes it.
* **Cons:** **Poor Usability.** Prevents the node from auto-starting on system boot. If the application crashes and restarts, it cannot rejoin the network until the user physically interacts with the terminal.

#### Option 3: `.env` or Configuration File
**Description:** Encrypt the PEM file, but store the decryption passphrase in a local `.env` or `config.json` file.
* **Pros:** Allows for automated, headless startup without user intervention.
* **Cons:** Security theater. An attacker who can read the `private_key.pem` file can almost certainly read the `.env` file right next to it, completely bypassing the encryption.

### Consequences

**Positive**
* **High Security:** The decryption passphrase is never stored in plaintext on the filesystem. It is managed by enterprise-grade OS security modules (e.g., Windows Credential Locker, macOS Keychain, Linux Secret Service).
* **Seamless UX:** The node can start up, recover from crashes, and join the network automatically without user intervention, fully supporting background or daemonized operations.
* **Automated Rotation:** Because the passphrase is a randomly generated 32-byte token rather than a human-memorized password, we guarantee maximum entropy (strength) against brute-force attacks.

**Negative**
* **External Dependency:** Introduces a reliance on the `keyring` Python library.
* **Headless Linux Complexity:** On desktop operating systems, `keyring` works out of the box. On headless Linux servers (like a VPS without a GUI), D-Bus and a headless secret service (like `pass` or `gnome-keyring` daemon) must be configured manually by the user, which adds deployment friction.

### Risks

* **Risk:** The OS keyring service is unavailable or locked (common in SSH-only headless Linux environments), causing the application to crash on startup.
    * **Mitigation:** We have wrapped the identity generation in a Strategy Pattern (`PeerID_Context`). If the primary identity generation fails due to a keyring error, the system will fall back to the `FallBack_Id` (UUID v4) strategy, allowing the node to still participate in the network safely, though without cryptographic identity.

### Related Decisions
* **ADR-001:** Use Secure Cryptographic ID (SCID) for Peer Identification.
* **Design Pattern:** The Strategy Pattern used in `main_Identity.py` handles the fallback logic if keyring access is denied.

### Notes
* Implemented in `src/Security/Private_Key_Pass.py`.
* The passphrase token is `base64.urlsafe_b64encode` formatted before storage to ensure safe string handling across all OS backends.
