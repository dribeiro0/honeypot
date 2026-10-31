
Readme · TXT
# AI-Endpoint Honeypot: Fake Ollama vs. SSH
 
A research honeypot that compares how attackers probe **exposed AI model servers** with how they attack **ordinary SSH servers**.
 
It runs two decoys side by side on a public cloud server:
 
- **Fake Ollama API** – a FastAPI app that imitates an unauthenticated [Ollama](https://ollama.com) server on its default port (11434). It answers like the real thing, logs every request and prompt, and returns canned responses. **No real model runs behind it.**
- **Cowrie SSH honeypot** – a widely used SSH honeypot on port 22 that records login attempts, credentials, and commands. It serves as the comparison baseline.
 
---
 
## Why
 
Self-hosted LLM servers like Ollama ship with no authentication by default, and many are exposed to the internet by mistake. Attackers scan for them to steal free compute, pull or tamper with models, or probe for further access. SSH brute-forcing, by contrast, is one of the oldest and best-understood attacks on the internet.
 
Running both on the same server answers a simple question: **do attackers treat an exposed AI endpoint differently from an exposed SSH server, and what are they after?**
 
---
 
## Architecture
 
```
                 Internet
                    │
        ┌───────────┴────────────┐
   port 22                  port 11434
        │                        │
 ┌──────▼──────┐         ┌───────▼────────┐
 │   Cowrie    │         │  Fake Ollama   │
 │ (container) │         │ FastAPI (cont.)│
 └──────┬──────┘         └───────┬────────┘
        │ JSON logs              │ JSONL logs
        ▼                        ▼
   Docker volume           Docker volume
  (cowrie-var)            (ollama-logs)
 
  AWS EC2 · Ubuntu 24.04 · Docker Compose
  Admin SSH: non-standard port, restricted by IP
```
 
## Stack
 
| Layer | Tool |
|---|---|
| Cloud | AWS EC2 (Ubuntu 24.04 LTS, t3.micro) |
| Containers | Docker, Docker Compose |
| SSH honeypot | [Cowrie](https://github.com/cowrie/cowrie) |
| AI honeypot | Python, FastAPI, Uvicorn |
| Logging | JSON / JSON Lines |
| Analysis (planned) | SQLite, pandas, matplotlib, GeoIP, MITRE ATT&CK tagging |
 
---
 
## Repository layout
 
```
honeypot/
├── docker-compose.yml     # runs both honeypots
├── ollama-fake/
│   ├── main.py            # fake Ollama API + request logger
│   └── Dockerfile         # container image for the fake Ollama
├── .gitignore             # keeps logs, keys and venvs out of the repo
└── README.md
```
 
Raw logs are deliberately **not** committed (see `.gitignore`). They contain attacker IP addresses and potentially malicious payloads.
 
---
 
## How the fake Ollama works
 
`ollama-fake/main.py` is a small FastAPI app:
 
- **A logging middleware runs on every request.** It records the timestamp, source IP, method, path, query string, headers, and body (capped at 20 KB) as one JSON object per line in `/logs/ollama.json`.
- **Routes mimic the real Ollama API**, returning realistic JSON shapes:
 
| Endpoint | Purpose for an attacker | Fake response |
|---|---|---|
| `GET /` , `HEAD /` | Fingerprinting ("is this Ollama?") | `Ollama is running` |
| `GET /api/version` | Version check | Plausible version string |
| `GET /api/tags` | List installed models | Two fake models |
| `GET /api/ps` | List loaded models | Empty list |
| `POST /api/generate` | Run a prompt | Canned reply |
| `POST /api/chat` | Chat completion | Canned reply |
| `POST /api/pull` | Download a model | Fake success |
| `POST /api/show` | Model details | Fake details |
| `GET /v1/models` | OpenAI-compatible model list | Fake list |
| `POST /v1/chat/completions` | OpenAI-compatible chat | Canned reply |
| anything else | Probing / scanning | `404 page not found` (Ollama's real text) |
 
Details that keep it convincing:
- FastAPI's auto-generated `/docs` pages are disabled, since real Ollama has none.
- Uvicorn runs with `--no-server-header`, so responses don't reveal a Python server.
- Bad or non-JSON bodies never crash the app; it simply logs them.
 
---
 
## Security hardening
 
A honeypot is meant to be attacked, so the host is locked down to keep it contained:
 
- **No IAM role on the instance.** If anything escapes, there are no AWS credentials to steal.
- **IMDSv2 required, hop limit 1.** Blocks the instance-metadata credential trick, and containers can't reach the metadata endpoint at all.
- **Real admin SSH moved off port 22** to a non-standard port, allowed only from my IP range, key-only login. (On Ubuntu 24.04 this required disabling `ssh.socket`, which otherwise ignores the `Port` setting.)
- **Honeypots run in containers as non-root users**, isolated from the host and easy to wipe and redeploy.
- **Encrypted EBS volume** and termination protection enabled.
- **Cost controls:** CPU credits set to *Standard* (abuse throttles the CPU rather than raising the bill), AWS Budget email alerts, and a budget action that automatically stops the instance if spending crosses a hard limit.
- **Passive only.** The honeypot never attacks back; it only records what is sent to it.
 
---
 
## Deploy
 
Prerequisites: a Linux server with Docker and the Compose plugin, and ports 22 and 11434 open to the internet (with your real SSH moved elsewhere first).
 
```bash
git clone <this-repo> honeypot && cd honeypot
docker compose up -d --build
docker compose ps
```
 
## Verify it's running
 
On the server, both containers should show `Up`:
 
```bash
docker compose ps
```
 
From another machine, test the fake Ollama:
 
```bash
curl http://<server-ip>:11434/            # → Ollama is running
curl http://<server-ip>:11434/api/tags    # → fake model list
curl -X POST http://<server-ip>:11434/api/generate -d '{"model":"llama3.1:8b","prompt":"hello"}'
```
 
And Cowrie (any password works for most attempts; run `whoami`, then `exit`):
 
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@<server-ip>
```
 
The extra options skip the host-key warning, since Cowrie presents a different key from the server's real SSH. Each test should then appear in the logs below.
 
## Where the logs are
 
Both honeypots write to Docker-managed volumes (used instead of bind mounts so the non-root container users can write without permission fixes):
 
```bash
# Cowrie
sudo tail /var/lib/docker/volumes/honeypot_cowrie-var/_data/log/cowrie/cowrie.json
 
# Fake Ollama
sudo tail /var/lib/docker/volumes/honeypot_ollama-logs/_data/ollama.json
```
 
Cowrie rotates its log daily at midnight UTC (older days become `cowrie.json.YYYY-MM-DD`), so stats that cover the whole run read every `cowrie.json*` file.
 
Quick stats:
 
```bash
# Total SSH connections (all days)
sudo sh -c 'cat /var/lib/docker/volumes/honeypot_cowrie-var/_data/log/cowrie/cowrie.json*' \
  | grep -c "session.connect"
 
# Most-tried SSH passwords
sudo sh -c 'cat /var/lib/docker/volumes/honeypot_cowrie-var/_data/log/cowrie/cowrie.json*' \
  | grep "login" | grep -o '"password": "[^"]*"' | sort | uniq -c | sort -rn | head
 
# Total requests to the fake Ollama (one line per request)
sudo wc -l /var/lib/docker/volumes/honeypot_ollama-logs/_data/ollama.json
 
# Most-requested Ollama paths
sudo grep -o '"path": "[^"]*"' /var/lib/docker/volumes/honeypot_ollama-logs/_data/ollama.json \
  | sort | uniq -c | sort -rn | head
```
 
---
 
## Early observations
 
- **SSH (Cowrie):** 87 connections in the first ~20 hours (live since the early morning of Oct 30, 2026), on a brand-new IP that was never published anywhere. The first bots arrived within hours.
- **AI endpoint (fake Ollama):** deployed the evening of Oct 30, 2026; collecting data. Exposed AI endpoints are a newer, more niche target than SSH, so discovery is expected to be slower.
 
The honeypot keeps running through November to build a larger dataset.
 
---
 
## Roadmap
 
- Load logs into SQLite and analyze with pandas/matplotlib
- GeoIP enrichment and MITRE ATT&CK tagging of observed behavior
- SSH vs. AI-endpoint comparison write-up / blog post
- Streaming (NDJSON) responses to better match real Ollama
- Infrastructure as code with Terraform; GitHub Actions for linting and deploys
- Postgres or the ELK stack for larger-scale log analysis
 
---
 
## Ethics & safety
 
This project only observes unsolicited traffic sent to a server I own. It does not interact with, scan, or retaliate against any external system. Raw logs are kept private. Any published results are aggregated and do not include full attacker payloads.
