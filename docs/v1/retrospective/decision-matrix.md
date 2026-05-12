# Tech Stack Decision Matrix

> **Project:** Peer-to-Peer File Sharing System  
> **Milestone:** M5 — Tech Stack Retrospective  
> **Date:** 2026-04-08

---

## Purpose

Evaluate the tools and frameworks used in this project with the benefit of hindsight. Would you make the same choices again?

---

## Evaluation Criteria

Define your criteria and weights:

| Criterion                    | Weight    | Description                                                         |
| ---------------------------- | --------- | ------------------------------------------------------------------- |
| Learning Curve               | 2/10      | How quickly could the team become productive?                       |
| Documentation                | 2/10      | Quality and availability of docs/tutorials                          |
| Performance                  | 2/10      | Did meet performance requirements?                                  |
| Team Experience              | 1/10      | Prior team familiarity                                              |
| Community Support            | 1/10      | Stack Overflow, GitHub issues, forums                               |
| Fit for Project Requirements | 2/10      | How well technology matched a local network P2P file-sharing system |
| **Total**                    | **10/10** |                                                                     |

---

## Decision Matrix

### Programming Language: Python 3.11

| Criterion                    | Score (1-5) | Weight | Weighted Score | Notes                                                                               |
| ---------------------------- | ----------- | ------ | -------------- | ----------------------------------------------------------------------------------- |
| Learning Curve               | 5           | 2/10   | 10             | Python allowed fast onboarding and fast iteration for a student team                |
| Documentation                | 5           | 2/10   | 10             | Strong documentation and many examples for sockets, hashing, async I/O, and testing |
| Performance                  | 4           | 2/10   | 8              | Performance was good enough for local peer discovery, search, and file transfer     |
| Team Experience              | 4           | 1/10   | 4              | The team was already comfortable enough Python to move quickly                      |
| Community Support            | 5           | 1/10   | 5              | Excellent community support and troubleshooting resources                           |
| Fit for Project Requirements | 5           | 2/10   | 10             | Very strong fit for networking, rapid prototyping, and file-handling tasks          |
| **Total**                    |             |        | **47/50**      |                                                                                     |

**Verdict:** Would choose again

**Hindsight:** Python was one of the strongest choices in the project. If we redid the project, we would still use Python, but we would define stricterr code conventions for async functions and shared state earlier.

---

### Framework: Textual TUI

| Criterion                    | Score (1-5) | Weight | Weighted Score | Notes                                                                                  |
| ---------------------------- | ----------- | ------ | -------------- | -------------------------------------------------------------------------------------- |
| Learning Curve               | 3           | 2/10   | 6              | Textual was learnable, but it added UI-specific complexity on top of networking work   |
| Documentation                | 4           | 2/10   | 8              | Documentation was solid enough to build tables, logs, tabs, and keyboard controls      |
| Performance                  | 4           | 2/10   | 8              | The interface performed well for a terminal-based prototype                            |
| Team Experience              | 3           | 1/10   | 3              | The team had less prior experience with Textual than with plain CLI code               |
| Community Support            | 4           | 1/10   | 4              | The ecosystem is smaller than older UI frameworks but still useful                     |
| Fit for Project Requirements | 4           | 2/10   | 8              | It improved usability through keyboard navigation, structured views, and activity logs |
| **Total**                    |             |        | **37/50**      |                                                                                        |

**Verdict:** Would reconsider

**Hindsight:** Textual improved the user experience compared to a plain CLI, especially through tables, tabs, keyboard shortcuts, and live activity output. However it also introduced extra layout and focus management work. If we redid project, we would either commit to Textual earlier and design around it from the start, or stay with a simpler CLI for a smaller prototype.

---

### Database: No Dedicated Database (In-Memory AppState + Local File System)

| Criterion                    | Score (1-5) | Weight | Weighted Score | Notes                                                                                                                 |
| ---------------------------- | ----------- | ------ | -------------- | --------------------------------------------------------------------------------------------------------------------- |
| Learning Curve               | 5           | 2/10   | 10             | Avoiding a database reduced setup and let the team focus on core P2P features                                         |
| Documentation                | 4           | 2/10   | 8              | File based and in memory designs are straightforward to understand and document                                       |
| Performance                  | 3           | 2/10   | 6              | This was acceptable for a local prototype, but not ideal for long term persistence or larger scale                    |
| Team Experience              | 4           | 1/10   | 4              | The team could work with files and Python state immediately                                                           |
| Community Support            | 4           | 1/10   | 4              | Plenty of support exists for simple file prototypes, though less structure than a DB backed design                    |
| Fit for Project Requirements | 5           | 2/10   | 10             | For a course prototype, avoiding database kept the architecture lighter and more aligned with peer-local file sharing |
| **Total**                    |             |        | **42/50**      |                                                                                                                       |

**Verdict:** Would choose again

**Hindsight:** For this milestone and scope, not using a dedicated database was reasonable. The system mainly needed peer state, file metadata, and local folders. If we expanded the system to support persistent indexing, larger search spaces, or richer history, we would introduce a lightweight database such as SQLite.

---

### Other Technology: `asyncio` + TCP/UDP Sockets

| Criterion                    | Score (1-5) | Weight | Weighted Score | Notes                                                                                          |
| ---------------------------- | ----------- | ------ | -------------- | ---------------------------------------------------------------------------------------------- |
| Learning Curve               | 3           | 2/10   | 6              | Async networking took times to debug and required careful thinking about task lifecycles       |
| Documentation                | 4           | 2/10   | 8              | There is strong documentation for Python sockets and asyncio patterns                          |
| Performance                  | 4           | 2/10   | 8              | It handled concurrent discovery, search, heartbeats, and transfers well enough for the project |
| Team Experience              | 3           | 1/10   | 3              | Some learning was required, especially for event-driven flow and cleanup                       |
| Community Support            | 4           | 1/10   | 4              | Common enough that most issues had examples or discussions available                           |
| Fit for Project Requirements | 5           | 2/10   | 10             | TCP for reliable transfer and UDP for discovery matched the project goals very well            |
| **Total**                    |             |        | **39/50**      |                                                                                                |

**Verdict:** Would choose again

**Hindsight:** The TCP/UDP separation was a great design choice. The problem wasn’t with the technology but with the overhead of debugging asynchronous connection management. If we were to do this again, we’d outline the guidelines for the connection life cycle much earlier and handle scenarios such as disconnections and stale peers earlier on.

---

## Summary

### Technologies That Worked Well

1. **Python 3.11:** It gave the team a fast development cycle, strong libraries, and a very good fit for networking and file handling.
2. **`asyncio` + TCP/UDP sockets:** This matched the P2P architecture well and supported discovery, search, and transfer without introducing unnecessary infrastructure.

### Technologies We'd Reconsider

1. **Textual TUI:** It improved usability but the extra UI complexity may not have been worth it unless the team committed to it earlier.
2. **No dedicated database for future growth:** It was fine for the prototype, but a larger or more persistent version of the system would likely benefit from SQLite or another lightweight database.

### Key Lessons Learned

1. The best technology choice is not always the most advanced one; it is the one that best matches real scope of the project.
2. Async networking was the right fit, but it requires earlier planning for debugging, cleanup, and lifecycle management.
3. Usability improvements are valuable and but UI complexity should be introduced only when the team has enough time to support it properly.
