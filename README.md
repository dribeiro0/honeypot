# AI Endpoint Honeypot

Comparing how attackers target exposed AI endpoints vs. traditional SSH.

- **SSH baseline:** Cowrie on port 22
- **AI endpoint:** fake Ollama API (FastAPI) on port 11434 — logs requests, returns canned responses, runs no model

Deployed on AWS EC2 with Docker Compose. Analysis in `analysis/`.

## Status
- [ ] Cowrie deployed
- [ ] Fake Ollama deployed
- [ ] Analysis + write-up
