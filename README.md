---
title: Jarvis Protocol
emoji: 🛡️
colorFrom: red
colorTo: blue
sdk: docker
app_port: 7860
---

# Jarvis Protocol — Autonomous Defensive Evolution

An OpenEnv-compliant RL environment for training LLMs to autonomously patch vulnerable Express.js code while under attack from an automated exploit engine (Ultron).

## Architecture

- **Defender (Jarvis)**: Qwen-2.5-7B-Coder fine-tuned via GRPO
- **Attacker (Ultron)**: Deterministic Python exploit engine with 3 payloads per vulnerability
- **Arena**: Express.js app with 3 vulnerability types (NoSQL Injection, Path Traversal, BOLA)
- **Reward**: 4-gate fail-fast waterfall (Format → Syntax → Happy-Path → Security)

## API Endpoints

- `POST /reset` — Start a new episode, returns vulnerable code observation
- `POST /step` — Submit agent patch, returns reward and gate-level scores
- `GET /state` — Query current environment state
- `GET /health` — Health check

## Usage

```python
import requests

# Reset environment
obs = requests.post("http://localhost:7860/reset").json()
print(f"Vulnerability: {obs['vuln_type']}")
print(f"Code:\n{obs['vulnerable_code']}")

# Submit a patch
result = requests.post("http://localhost:7860/step", json={
    "agent_output": "<reasoning>Fix the injection</reasoning>\n<patch>fixed code here</patch>"
}).json()
print(f"Reward: {result['reward']}, Gate reached: {result['info']['gate_reached']}")
```

## Training

See `train.py` for the GRPO training script using TRL + Unsloth.

## Hackathon

OpenEnv Hackathon India 2026 — Theme 3.1 (World Modeling) + Theme 4 (Self-Improvement)
