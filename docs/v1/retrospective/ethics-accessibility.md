# Ethics & Accessibility Statement

> **Project:** Peer-to-Peer File Sharing System  
> **Milestone:** M5 — Tech Stack Retrospective  
> **Date:** 2026-04-08

---

## Purpose

Reflect on the ethical considerations and accessibility features of your system. This is increasingly important in professional software development and aligns with engineering ethics requirements.

---

## Ethical Considerations

### Data Privacy

**What data does your system collect?**

| Data Type                                                    | Purpose                                            | Sensitivity | Retention                                                         |
| ------------------------------------------------------------ | -------------------------------------------------- | ----------- | ----------------------------------------------------------------- |
| Peer connection data (`peer_id`, host, port, liveness state) | Peer discovery, routing, and connection management | Medium      | Runtime memory while application is active                        |
| File metadata (`file_id`, file name, file size)              | Catalog exchange, search and download coordination | Medium      | Runtime memory and local shared download folders as needed        |
| File content selected by users for sharing / downloading     | Actual file transfer between peers                 | High        | Stored in local shared or downloads folders until user removes it |

**Privacy measures implemented:**

- [x] Data minimization (only collect what's needed)
- [ ] Encryption at rest
- [ ] Encryption in transit (HTTPS)
- [ ] User consent for data collection
- [ ] Data deletion capability
- [ ] Access controls

**Privacy considerations we would address in production:**

- Add clear user facing consent and sharing warnings before exposing files to peers
- Add encrypted transport rather than sending the protocol and the ile data in plain TCP/UDP
- Add explicit unshare/delete controls and clearer retention rules inside the application

---

### Bias and Fairness

**Could your system produce biased outcomes?**

This system is not a recommendation engine and does not make decisions based on user identity, demographics, or personal profiles, so traditional algorithmic bias is limited. Search and transfer behavior are mostly based on file names, file identifiers, peer availability, and network conditions.

However, fairness concerns still exist. Search visibility may depend on which peers are currently connected and how quickly they respond. The system could also be misused for unsafe or unlawful sharing if stronger controls are not added.

**Mitigation measures:**

- Keep search behavior deterministic and based on technical criteria rather than personal profiling
- Be transparent that visibility depends on connected peers and current network state
- Add stronger authentication, authorization, and usage restrictions in a production version

---

### Security

**Security measures implemented:**

- [x] Input validation
- [ ] Authentication
- [ ] Authorization
- [ ] Protection against common vulnerabilities (SQL injection, XSS, etc.)
- [ ] Secure password storage (hashing)
- [ ] Audit logging

**Known security limitations:**

- Transport traffic is not encrypted, so the system should not be treated as production secure
- Authorization and fine grained access control are not implemented
- Cryptographic identity and keyring support are stronger on some environments than others
- The system validates protocol structure and verifies file integrity, but that does not replace full end to end security

---

### Environmental Impact

**Considerations for production deployment:**

- Estimated resource usage: Low to Medium
- Cloud provider sustainability: Not applicable for current peer hosted prototype
- Optimization opportunities: reduce unnecessary broadcast traffic, avoid repeated hashing where not needed, reuse connections when practical, and limit excessive search flooding

---

## Accessibility

### Current State

**What accessibility features are implemented?**

- [ ] Semantic HTML
- [x] Keyboard navigation
- [ ] Screen reader compatibility
- [ ] Color contrast compliance (WCAG AA)
- [ ] Alt text for images
- [ ] Form labels
- [x] Error messages accessible
- [ ] Responsive design

This prototype is manly terminal based through a cli and a Textual TUI. That gives it a useful accessibility strength: the system can be operated entirely with the keyboard, and feedback is presented mainly as text. At the same time, it has not been formally tested for screen readers or WCAG conformance, so accessibility claims should remain modest.

### WCAG Compliance

**Target level:** AA

**Current assessment:**

| Criterion      | Status | Notes                                                                                                             |
| -------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| Perceivable    | ⚠️     | The interface is text based, but color contrast and assistive technology support were not formally verified       |
| Operable       | ✅     | Keyboard based operation is a clear strength of CLI/Textual interface                                             |
| Understandable | ✅     | Commands, tables, and status messages are relatively direct and readable                                          |
| Robust         | ⚠️     | Accessibility behavior across the terminals, screen readers, and smaller terminal sizes has not been fully tested |

### Accessibility Improvements for Future

1. Test the interface with screen readers and different terminal environments instead of assuming terminal text is automatically accessible
2. Improve non-color cues, contrast consistency, and help/error text for users who are new to CLI/TUI systems
3. Add a simpler guided mode or future GUI option for users who may struggle with command-based interaction

---

## Professional Responsibility

As software engineers, we recognize our responsibility to:

- [x] Build software that respects user privacy
- [x] Consider the impact of our systems on all users
- [x] Design for inclusivity and accessibility
- [x] Be transparent about system limitations
- [x] Continuously improve based on user feedback

---

## References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ACM Code of Ethics](https://www.acm.org/code-of-ethics)
- [IEEE Code of Ethics](https://www.ieee.org/about/corporate/governance/p7-8.html)
- [Engineers Canada Code of Ethics](https://engineerscanada.ca/publications/public-guideline-on-the-code-of-ethics)
