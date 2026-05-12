# ADR Retrospective

> **Milestone:** M5 — Tech Stack Retrospective
> **Date:** 2026-04-05

---

## Purpose

Review all Architecture Decision Records (ADRs) created during the project. Which decisions held up? Which would you change with hindsight?

---

## ADR Summary

| ADR | Title | Date | Status | Verdict |
|-----|-------|------|--------|---------|
| ADR-001 | Peer Discovery via UDP Broadcast with Pluggable Discovery Providers | 2026-02-01 | Accepted | ✅ Held up |
| ADR-002 | Use TCP for Control, Peer/File Search, and File Transfer. Use UDP Only for Discovery | 2026-02-01 | Accepted | ✅ Held up |
| ADR-003 | Minimal Kademlia-like DHT Scope for Lookup and Routing | 2026-02-07 | Accepted | ⚠️ Partially |
| ADR-004 | File Identity and Catalog Metadata (Hash-Based file_id) | 2026-02-07 | Accepted | ✅ Held up |
| ADR-005 | Peer Liveness and Stale Data Handling (Heartbeats + TTL) | 2026-02-07 | Accepted | ✅ Held up |
| ADR-006 | Use Secure Cryptographic ID (SCID) for Peer Identification | 2026-04-04 | Accepted | ✅ Held up |
| ADR-007 | Use Asyncio for Concurrent Network I/O and State Management | 2026-04-04 | Accepted | ✅ Held up |
| ADR-008 | Secure Storage of RSA Private Key via OS Keyring | 2026-04-04 | Accepted | ⚠️ Partially |

---

## Detailed Review

### ADR-001: Peer Discovery via UDP Broadcast with Pluggable Discovery Providers

**Original Decision:** Use UDP broadcast as the default peer discovery mechanism on LAN/localhost, and expose discovery as a pluggable provider interface so that alternative methods (e.g., manual IP entry) can be added later without touching transfer or search code.

**What Happened:** UDP broadcast discovery worked exactly as intended within our target environment of LAN/localhost. Peers were able to announce themselves and populate peer lists with minimal overhead. The pluggable provider interface proved its value when manual IP entry was needed as a fallback in environments where broadcast was less reliable. No changes to the transfer or search modules were required when the fallback was added, validating the decoupling rationale entirely.

**Verdict:** ✅ Held up

**If we could redo it:** We would not change the core decision. The one refinement we would make is to define the `DiscoveryProvider` interface earlier and more formally — even before writing the UDP implementation — so that the fallback manual provider had a cleaner integration path from day one rather than being bolted on later.

---

### ADR-002: Use TCP for Control, Peer/File Search, and File Transfer. Use UDP Only for Discovery

**Original Decision:** Route all reliable operations — catalog sharing, peer/file search, and file transfer — over TCP. Reserve UDP exclusively for broadcast-based peer discovery.

**What Happened:** This protocol split held up cleanly throughout the project. TCP's reliable delivery made debugging search and transfer behaviour straightforward, and there were no cases where we wished we had used UDP for stateful communication. The asyncio TCP stream abstractions (readers and writers) integrated naturally with the rest of the architecture. The one predicted risk — that search and transfer traffic could interfere with each other under load — was mitigated adequately by asyncio's cooperative scheduling.

**Verdict:** ✅ Held up

**If we could redo it:** No fundamental change. However, we would document the connection lifecycle more explicitly from the start — specifically, the rules around when a TCP connection is opened, reused for heartbeats and catalog exchanges, and eventually closed. This would have reduced some early ambiguity between team members about whether a new connection should be opened per-message or per-peer.

---

### ADR-003: Minimal Kademlia-like DHT Scope for Lookup and Routing

**Original Decision:** Implement a minimal Kademlia-like DHT using 160-bit XOR-distance routing, k-buckets, and a small RPC set (`FIND_NODE`, `FIND_VALUE`, `STORE`) to support decentralized file availability lookup and peer routing beyond what UDP broadcast can handle.

**What Happened:** This decision was not implemented in the codebase. The Kademlia-like DHT remained a documented architectural intention but was ultimately deferred due to scope and timeline constraints. In practice, UDP broadcast for discovery combined with direct TCP catalog exchange between connected peers was sufficient for the prototype's LAN/localhost scale. The system functioned correctly without the DHT layer, which confirms that UDP broadcast was the right pragmatic baseline — but it also means the scalability rationale for ADR-003 was never validated in code.

**Verdict:** ⚠️ Partially

**If we could redo it:** We would reframe this ADR at the time of writing to explicitly separate the architectural *intent* (DHT as a future scalability mechanism) from the *implementation scope* of the prototype. Concretely, we would add a "Deferred to future milestone" status and note the conditions under which it would be revisited (e.g., peer count exceeds N, or broadcast is blocked in a target environment). This would have been more honest and would have avoided the gap between what the documentation promised and what the codebase delivered — a gap that was correctly flagged in our mentor review.

---

### ADR-004: File Identity and Catalog Metadata (Hash-Based file_id)

**Original Decision:** Define `file_id` as SHA-256 of the file's bytes. Require catalog entries to include `file_id`, `name`, and `size`. Verify integrity after download by recomputing and comparing the hash.

**What Happened:** This decision held up perfectly and proved to be one of the strongest in the project. The `hash_check.py` implementation was specifically highlighted in our mentor review as excellent — it reads files in 8KB chunks for memory efficiency and deletes corrupted files on hash mismatch. Using SHA-256 as both the identity and the integrity check meant we never had to maintain a separate verification mechanism, and content-based de-duplication came as a free side effect.

**Verdict:** ✅ Held up

**If we could redo it:** No change to the decision itself. As an enhancement, we would have defined the catalog metadata schema as a formal dataclass or TypedDict earlier, so that all modules serializing and deserializing catalog entries were working against a single source of truth rather than constructing dictionaries independently.

---

### ADR-005: Peer Liveness and Stale Data Handling (Heartbeats + TTL)

**Original Decision:** Use periodic TCP `PING/PONG` heartbeats between connected peers, evict peers after N consecutive missed heartbeats, and attach TTL values to DHT entries so that stale file availability data fades out automatically.

**What Happened:** The heartbeat mechanism implemented cleanly and worked well — when a peer disconnected without a graceful shutdown, the heartbeat loop detected the failure within a predictable window and triggered local cleanup of that peer's cached catalog. This directly supported our Availability quality goal. The TTL component was partially undermined by the fact that the DHT layer was not implemented (see ADR-003), so TTL expiry for DHT entries was never exercised in practice. The local peer eviction logic, however, was fully functional.

**Verdict:** ✅ Held up

**If we could redo it:** We would keep the heartbeat design unchanged. For the TTL component, we would separate the concern more clearly in the ADR: TTL on local peer state (implemented and useful) versus TTL on DHT entries (deferred with DHT). Writing these as two distinct sub-decisions would have made it easier to track which part was implemented and which was deferred.

---

### ADR-006: Use Secure Cryptographic ID (SCID) for Peer Identification

**Original Decision:** Derive each node's `peer_id` by taking the SHA-256 hash of a freshly generated 2048-bit RSA public key. Use the Strategy Pattern to fall back to UUID v4 if cryptographic generation fails. Store the private key as an encrypted PEM file with the passphrase managed by the OS keyring.

**What Happened:** The SCID implementation worked well on standard desktop environments and was highlighted as a strength in the mentor review. The Strategy Pattern (`Primary_Identity` → `FallBack_Id`) proved its value on headless Linux environments where the OS keyring was unavailable, allowing the node to continue functioning without crashing. The identity remained stable across restarts and network changes as intended. The main friction was on headless Linux servers, which required manual D-Bus or secret service configuration that not all team members had dealt with before.

**Verdict:** ✅ Held up

**If we could redo it:** We would document the headless Linux keyring setup requirement more explicitly in the README from the outset, rather than discovering it during testing. We would also consider whether UUID v4 as a fallback is the right default for a security-focused ADR — a warning log and a clear "degraded security mode" message in the CLI output would help users understand that they are no longer operating with cryptographic identity guarantees.

---

### ADR-007: Use Asyncio for Concurrent Network I/O and State Management

**Original Decision:** Use Python's `asyncio` event loop as the single concurrency model for all network operations and file I/O. Avoid threading locks by relying on single-threaded cooperative scheduling for shared state safety. Offload the blocking CLI `input()` loop using `run_in_executor()`.

**What Happened:** This was arguably the best foundational decision in the project. The absence of threading locks kept the codebase clean and avoided an entire class of concurrency bugs that would have been very difficult to debug in a 13-week timeline. The `aiofiles` dependency for non-blocking file I/O worked as expected. The `run_in_executor()` bridge for the CLI worked without issues. The predicted risk of accidental blocking calls was managed by the chunked hashing approach in `hash_check.py`.

**Verdict:** ✅ Held up

**If we could redo it:** No fundamental change. We would enforce a team-wide convention from week one that any function doing file I/O must use `aiofiles` and be documented as a coroutine — early in the project there was occasional confusion about when to use `async def` versus a regular function, which required some later refactoring.

---

### ADR-008: Secure Storage of RSA Private Key via OS Keyring

**Original Decision:** Encrypt the RSA private key as a PEM file and store the decryption passphrase in the native OS credential store using the `keyring` library. On first run, generate a cryptographically secure random 32-byte passphrase and store it automatically. On subsequent runs, retrieve it silently.

**What Happened:** On Windows and macOS the implementation worked seamlessly. On headless Linux (SSH-only environments without a running GUI session), the `keyring` library threw errors because no backend was available by default. The Strategy Pattern fallback to UUID prevented crashes, but it also meant that nodes running in those environments silently lost their cryptographic identity. This was a usability issue that required ad-hoc documentation and manual setup steps that were not anticipated in the ADR.

**Verdict:** ⚠️ Partially

**If we could redo it:** We would add explicit environment detection at startup. If the keyring backend is unavailable, rather than silently falling back to UUID, the application should emit a clear warning explaining the degraded security mode and provide concise setup instructions for configuring a headless keyring backend (e.g., `keyrings.alt` as a file-based fallback for development, or `gnome-keyring` daemon setup for production Linux). We would also add this scenario explicitly to the Risks section of the ADR at the time of writing, rather than discovering it during integration testing.

---

## Decisions We Wish We'd Made Earlier

1. **Formal `AppState` as an injectable dataclass:** We started with `global` variables in `state.py` and refactored to an injectable `AppState` model mid-project in response to the SOLID refactor. Defining this structure in week one would have saved the refactor effort and made unit testing straightforward from the beginning.

2. **Explicit catalog metadata schema (TypedDict or dataclass):** File catalog entries were serialized and deserialized as plain dictionaries in multiple modules with no shared schema definition. A formal schema defined early would have prevented several small inconsistency bugs during integration and made the protocol easier to document.

3. **Headless Linux environment testing policy:** We did not test on headless Linux until late in the project. Deciding in week two to include a headless environment in the regular test matrix would have surfaced the keyring and asyncio event loop issues much earlier and with lower remediation cost.

---

## Key Takeaways

### What Made Good ADRs

- Grounding decisions in explicit project constraints (e.g., referencing the 13-week timeline, LAN/localhost scope, and team size as rationale) made the trade-offs honest and traceable rather than aspirational.
- Listing concrete alternatives with pros and cons — not just the chosen option — made it much easier during the mentor review to explain why we didn't do something, which is often just as important as explaining why we did.
- Linking ADRs to each other (e.g., ADR-006 referencing ADR-007's state-safety guarantees) created a coherent decision graph rather than isolated records.

### What Made Poor ADRs

- ADR-003 documented an architectural intention (Kademlia-like DHT) without acknowledging that implementation was contingent on available time. The gap between the documented decision and the actual codebase created confusion that required a mentor correction to address.
- Some ADRs were written after the implementation was already done (particularly ADR-006, ADR-007, ADR-008, all dated 2026-04-04), which means they describe what was built rather than guiding what should be built. This reduces their value as decision-making tools and makes it harder to trace when and why a choice was made.

### Advice for Future Teams

1. **Write the ADR before you write the code, not after.** An ADR written retroactively is documentation, not decision-making. Even a rough draft during design discussion is more valuable than a polished record written after the fact.
2. **Separate intent from implementation scope explicitly.** If a decision describes something you plan to build in a future milestone, say so. A "Deferred" status with clear conditions for revisiting is far more honest — and more useful to reviewers — than an "Accepted" ADR for a feature that was never built.
3. **Test on your full target environment matrix from week two.** Environment-specific issues (like headless Linux keyring failures) are much cheaper to fix early. Don't let deployment friction be a late-project surprise.
