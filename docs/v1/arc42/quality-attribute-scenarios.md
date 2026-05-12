# Quality Attribute Scenarios

**Project Name:** Peer-to-Peer File Sharing System
**Team Members:** Ryan Siyavudeen, Aakash Yogabalu, Md Imtiaz Ahmed, Shifan Pathan 
**Date:** 31/01/2026

---

## QAS-01: File Search Response Under Peer Load

*Quality Attribute:* Performance

| Component | Specification |
|-----------|---------------|
| *Source* | Multiple peers in the network issuing file search requests simultaneously. |
| *Stimulus* | A user initiates a file search while the system is handling high peer activity and concurrent searches. |
| *Environment* | Normal operation with 50–100 active peers connected and sharing file catalogs. |
| *Artifact* | Peer discovery mechanism, distributed file catalog, and search propagation logic. |
| *Response* | The system distributes the search request efficiently across peers, aggregates responses, and returns matching file results to the user without blocking other network activities. |
| *Response Measure* | Search results returned within *2 seconds* for 95% of requests under load; no peer CPU utilization exceeds 80% during search processing. |

*Applicable Tactics (Bass Ch. 5):*
- *Resource Management:* Limits the number of concurrent search requests processed by each peer to prevent overload.  
- *Asynchronous Processing:* Allows peers to handle search queries without blocking file transfers or other network operations.  

*Priority Assessment:*
- [x] Architectural Driver (High Value, High Risk)
- [ ] Contractual Guarantee (High Value, Low Risk)
- [ ] Nice-to-Have (Low Value, Low Risk)
- [ ] Potential Risk (Low Value, High Risk)

*Justification:*  
Performance is critical for usability in a peer-to-peer system. Slow search responses discourage users and reduce system effectiveness, especially as the number of peers increases. Since performance depends heavily on network conditions and peer behavior, it represents a high-value, high-risk concern and therefore acts as an architectural driver.

## QAS-02: Peer Disconnect During File Transfer

**Quality Attribute:** Availability / Reliability

| Component | Specification |
|-----------|--------------|
| **Source** | Sender Peer (a peer currently uploading a file) |
| **Stimulus** | Sender Peer becomes unreachable mid-transfer (process crash, app close, or network drop) |
| **Environment** | Normal operation on local network/localhost, at least **3 peers online**. One file transfer in progress for a file size **< 10 MB**; background search/catalog traffic continues during the transfer   |
| **Artifact** | Transfer Session Manager (Python sockets + transfer state machine), including chunk index tracking, checksum verification, and retry/reconnect logic  |
| **Response** | Receiver detects the disconnect, transitions the session to **PAUSED**, notifies the user, and (a) resumes from the **last verified chunk** if the sender returns within the retry window, or (b) fails cleanly and offers retry from another peer that advertises the same file |
| **Response Measure** | - Disconnect detected within **≤ 2 seconds** (socket error or heartbeat timeout)  - User notification shown within **≤ 1 second** after detection  - Resume correctness: after a successful resume, **100%** of received chunks match expected chunk indices and the final file passes checksum validation before “complete” - If sender returns within **60 seconds**, transfer resumes from the last verified chunk within **≤ 5 seconds** (no full restart)  - If sender does not return within **60 seconds**, session transitions to **FAILED** and user can retry within **≤ 3 clicks**  - Retry policy: receiver attempts reconnect with backoff, capped at **≤ 6 attempts** in the 60-second window |

**Applicable Tactics (Bass Ch. 5):**
- **Heartbeat / Fault Detection**
- **Retry with Backoff**
- **Rollback / State Restoration (resume from last verified chunk)**
- **Audit / Logging**

**Priority Assessment:**
- [x] Architectural Driver (High Value, High Risk)

**Justification:**
Peers are expected to join or leave gracefully, and direct transfers are a core requirement. The system must remain usable even when peers disconnect mid transfer. 

**How we test it:**
Run a transfer between two peers while a third peer performs searches. Kill the sender process at 30–50% progress, measure detection time and UI notification time, then restart the sender within 60 seconds to verify resume from last chunk and checksum pass.


---

## QAS-03: Adding a New Peer Discovery Protocol 

**Quality Attribute:** Modifiability

| Component | Specification |
|-----------|---------------|
| **Source** | Developer (Team member responsible for network logic) |
| **Stimulus** | A requirement to add a new discovery protocol (e.g., "Manual IP Entry") alongisde the existing "Automatic Broadcasts" to allow connection between peers on different networks |
| **Environment** | Design/Implementation time. The system is not running; code is being modified in the maintenance phase. The existing network subsystem handles discovery via a single broadcast mechanism  |
| **Artifact** | Network Discovery Subsystem (the logical components responsible for finding peers) and System Configuration Modules |
| **Response** | The developer implements the new discovery logic in seperate, isolated module. The main system detects and loads this new method via configuration without requiring changes to the core "Connection Manager" or "File Transfer" logic|
| **Response Measure** | -Effort: The new protocol is implemented and integrated in ≤ 5 person-hours. -Ripple Effect: 0 lines of code are changed in File transfer or User Interface subsystems. -Isolation: the new module can be unit tested independently of the main appilcation. -Defects: introducing the new module causes 0 regressions in the existing Broadcast feature |

**Applicable Tactics (Bass Ch. 5):**
- Abstract Common Services: Identify the common behavior of all discovery methods (finding an IP and Port) and define a generalized abstraction for them.
- Use an Intermediary: The system interacts with discovery modules through a common interface/API, preventing direct dependencies on specific network implementations.
- Configuration Files (Defer Binding Time): The specific discovery method (Broadcast vs. Static) is selected via a configuration file at startup, rather than being hard-coded.

**Priority Assessment:**
- [x] Architectural Driver (High Value, High Risk)
- [ ] Contractual Guarantee (High Value, Low Risk)
- [ ] Nice-to-Have (Low Value, Low Risk)
- [ ] Potential Risk (Low Value, High Risk)


**Justification:** 
Peer Discovery is the primary entry point for the application and is highly sensitive to the network environment (LAN vs. WAN). Hard-coding the discovery logic into the main application would create a rigid system that cannot adapt to new environments without a complete rewrite, making this a critical architectural driver.

**How we test it:** Create a "Mock" discovery module that returns a pre-defined list of fake peers. Update the system configuration to load this mock module instead of the real network module. Launch the application and verify that the fake peers appear in the peer list without the system attempting to open any real network ports.



