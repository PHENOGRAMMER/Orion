---
title: Orion Model Service
emoji: 🛰️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
---

# Orion model service

This service loads the public DeepSeek Coder base model and Orion's private
LoRA adapter from Hugging Face. Configure `HF_TOKEN` as a Space secret. Never
commit the token.

Required environment variables:

```text
ORION_ADAPTER_REPO=ARYANPHENOM/orion-lora-adapter
ORION_BASE_MODEL=deepseek-ai/deepseek-coder-1.3b-instruct
HF_TOKEN=<Space secret with read access to the private adapter repository>
```

Endpoints:

- `GET /health`
- `POST /warm`
- `POST /generate`
