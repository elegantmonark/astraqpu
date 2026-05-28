# Security Policy

## Reporting

If you find a security issue in AstraQPU, please do not open a public issue with exploit details.

Report it privately to:

```text
https://github.com/elegantmonark/astraqpu/security/advisories/new
```

If GitHub private advisories are unavailable, contact Trishan Biswas through the GitHub profile:

```text
https://github.com/elegantmonark
```

## Scope

Security issues in scope:

- unsafe serial message parsing
- malformed instruction streams that crash the runtime
- unsafe file handling in the CLI
- dependency vulnerabilities
- GitHub Actions or release workflow issues
- firmware behavior that could lock up a board or spam a serial host

Out of scope:

- attacks that require editing local source files first
- issues in unsupported forks
- physical attacks against a microcontroller board
- claims about real quantum hardware safety, since AstraQPU is not connected to real QPU control electronics

## Supported Versions

The project is pre release. Security fixes are applied to `main` until tagged releases exist.

## Secret Handling

Do not commit:

- GitHub tokens
- serial device credentials
- private board IDs
- cloud API keys
- lab machine hostnames or credentials
- private calibration data from real devices

Use environment variables or local ignored config files for anything sensitive.

## Current Security Model

AstraQPU currently treats `.aqis`, architecture specs, and serial lines as untrusted input. The runtime should reject malformed input with clear errors instead of crashing or silently doing the wrong thing.

The Arduino firmware is a mock control unit. It must never be treated as safety certified firmware for physical lab equipment.

