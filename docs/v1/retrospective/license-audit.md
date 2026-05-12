# License Audit

> **Milestone:** M5 — Tech Stack Retrospective  
> **Date:** [2026-04-06]

---

## Purpose

Document all third-party dependencies, their licenses, and compliance status. This is a professional practice required for any production software.

---

## License Compatibility

Our project uses: **[MIT / Apache 2.0 / GPL / etc.]**

### Compatible Licenses

These licenses are compatible with our project license:

- MIT
- Apache 2.0
- BSD (2-clause, 3-clause)
- ISC
- Unlicense

### Potentially Incompatible Licenses

These require careful review:

- GPL (v2, v3) — Copyleft, may require open-sourcing derivative works
- LGPL — Less restrictive than GPL but still has requirements
- AGPL — Network copyleft, triggers on server use
- Commercial — May require purchased license

---

## Dependency Audit

### Production Dependencies

| Package | Version | License | Compatible? | Notes |
|---------|---------|---------|-------------|-------|
| aiofiles | 25.1.0 | Apache Software License | ✅ | Permissive |
| cryptography | 46.0.5 | Apache-2.0 OR BSD-3-Clause | ✅ | Permissive dual license |
| keyring | 25.7.0 | MIT | ✅ | Permissive |
| textual | 8.2.1 | MIT License | ✅ | Permissive |
| rich | 14.3.3 | MIT License | ✅ | Permissive |
| Pygments | 2.19.2 | BSD License | ✅ | Permissive |

### Development Dependencies

| Package | Version | License | Compatible? | Notes |
|---------|---------|---------|-------------|-------|
| black | 26.1.0 | MIT | ✅ | Code formatter |
| pytest | 9.0.2 | MIT | ✅ | Test runner |
| pytest-cov | 7.0.0 | MIT | ✅ | Coverage plugin |
| coverage | 7.13.4 | Apache-2.0 | ✅ | Coverage tool |
| ruff | 0.15.4 | MIT License | ✅ | Linter |
| click | 8.3.1 | BSD-3-Clause | ✅ | Permissive |
| packaging | 26.0 | Apache-2.0 OR BSD-2-Clause | ✅ | Permissive |
| typing_extensions | 4.15.0 | PSF-2.0 | ✅ | Permissive |


---

## Tools for License Checking

Use these tools to generate dependency lists:

**Python:**
```bash
pip install pip-licenses
pip-licenses --format=markdown
```

**Node.js:**
```bash
npx license-checker --summary
npx license-checker --csv > licenses.csv
```

**Java/Maven:**
```bash
mvn license:third-party-report
```

---

## Compliance Issues

### Issues Found

| Package | Issue | Resolution |
|---------|-------|------------|
|requirements.txt |Production and Development dependancies are mixed in one file | Split into requirements.txt and requirements-dev.txt in the future|
|bundled virtual environment|Since we use venv it can repo larger than required| Do not commit venv rather rebuild dependencies from the requirements file instead|

### No Issues

✅ All dependencies are compatible with our project license.

---

## Attestation

We have reviewed all third-party dependencies and confirm:

- [✅] All production dependencies have compatible licenses
- [✅] No GPL/AGPL dependencies are included (or we accept copyleft obligations)
- [✅] No commercial licenses require payment for our use case
- [✅ ] Attribution requirements are met (see below)

---

## Required Attributions

If any licenses require attribution, list them here:

```
aiofiles - Apache License 2.0
License URL: https://www.apache.org/licenses/LICENSE-2.0

cryptography - Apache-2.0 OR BSD-3-Clause
License URL: https://github.com/pyca/cryptography

keyring - MIT
License URL: https://github.com/jaraco/keyring

textual - MIT License
License URL: https://github.com/Textualize/textual

rich - MIT License
License URL: https://github.com/Textualize/rich

Pygments - BSD License
License URL: https://pygments.org/

black - MIT
License URL: https://github.com/psf/black

pytest - MIT
License URL: https://github.com/pytest-dev/pytest

pytest-cov - MIT
License URL: https://github.com/pytest-dev/pytest-cov

coverage - Apache-2.0
License URL: https://github.com/nedbat/coveragepy

ruff - MIT License
License URL: https://github.com/astral-sh/ruff

click - BSD-3-Clause
License URL: https://github.com/pallets/click

packaging - Apache-2.0 OR BSD-2-Clause
License URL: https://github.com/pypa/packaging

typing_extensions - PSF-2.0
License URL: https://github.com/python/typing_extensions
```
