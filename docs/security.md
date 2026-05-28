# Project Security

This is the security checklist for AstraQPU while it is still early.

## GitHub Settings

Turn these on in the GitHub repo settings:

- private vulnerability reporting
- Dependabot alerts
- Dependabot security updates
- code scanning with CodeQL
- secret scanning
- branch protection for `main`

For branch protection, start with:

- require pull request before merge
- require status checks to pass
- require branch to be up to date before merge
- block force pushes
- block deletion of `main`

## What To Protect

The important things right now are:

- your authorship and citation
- the `main` branch
- serial protocol correctness
- dependency updates
- input validation
- any future board or lab credentials

## Do Not Commit

Do not commit anything like:

```text
GITHUB_TOKEN=...
OPENAI_API_KEY=...
COM port logs from a private lab machine
private calibration dumps
serial numbers from real hardware
SSH keys
```

## Development Rules

Keep changes small and reviewable.

Every runtime feature should have at least one test.

Every new input format should have bad input tests.

Every firmware protocol change should update:

- `docs/serial-protocol.md`
- `docs/main.tex`
- a Python protocol test
- the Arduino or ESP32 reference implementation

## Release Rule

Do not tag a release until:

- tests pass
- README commands work
- `SECURITY.md` is current
- the report in `docs/main.tex` mentions the release state
- the GitHub repo has branch protection turned on

