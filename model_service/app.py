"""Minimal CPU model service for Orion's private LoRA adapter."""

from __future__ import annotations

import os
import time
from functools import lru_cache

import torch
from fastapi import FastAPI, HTTPException
from huggingface_hub import snapshot_download
from peft import PeftModel
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer


BASE_MODEL = os.getenv(
    "ORION_BASE_MODEL",
    "deepseek-ai/deepseek-coder-1.3b-instruct",
)
ADAPTER_REPO = os.getenv("ORION_ADAPTER_REPO", "ARYANPHENOM/orion-lora-adapter")
HF_TOKEN = os.getenv("HF_TOKEN")
MAX_INPUT_TOKENS = int(os.getenv("ORION_MAX_INPUT_TOKENS", "1536"))
DEFAULT_MAX_NEW_TOKENS = int(os.getenv("ORION_MAX_TOKENS", "65"))

SYSTEM_PROMPT = (
    "You are Orion, an expert code structure analyst. "
    "Given a knowledge graph context extracted from a Python repository, "
    "answer the developer's question accurately and concisely. "
    "Base your answer solely on the graph data provided."
)

app = FastAPI(title="Orion model service", version="1.0.0")


class GenerateRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    context: str = Field(..., min_length=1, max_length=20000)
    max_new_tokens: int = Field(DEFAULT_MAX_NEW_TOKENS, ge=1, le=256)
    temperature: float = Field(0.05, ge=0.0, le=1.0)


class GenerateResponse(BaseModel):
    text: str
    device: str
    latency_ms: float


def _build_prompt(tokenizer, question: str, context: str) -> str:
    content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"[GRAPH CONTEXT]\n{context}\n\n"
        f"[QUESTION]\n{question}"
    )
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": content}],
        tokenize=False,
        add_generation_prompt=True,
    )
    return prompt + "[ANSWER]\n"


@lru_cache(maxsize=1)
def load_model():
    adapter_dir = snapshot_download(repo_id=ADAPTER_REPO, token=HF_TOKEN)
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(base, adapter_dir)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(adapter_dir, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer, adapter_dir


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ready" if load_model.cache_info().currsize else "cold",
        "model_loaded": load_model.cache_info().currsize > 0,
        "base_model": BASE_MODEL,
        "adapter_repo": ADAPTER_REPO,
        "device": "cpu",
    }


@app.post("/warm")
def warm() -> dict[str, object]:
    started = time.perf_counter()
    load_model()
    return {
        "status": "ready",
        "device": "cpu",
        "load_ms": round((time.perf_counter() - started) * 1000, 1),
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    started = time.perf_counter()
    try:
        model, tokenizer, _ = load_model()
        prompt = _build_prompt(tokenizer, request.question, request.context)
        encoded = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_INPUT_TOKENS,
            add_special_tokens=False,
        )

        with torch.no_grad():
            output = model.generate(
                **encoded,
                max_new_tokens=request.max_new_tokens,
                do_sample=request.temperature > 0,
                temperature=request.temperature,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.1,
                use_cache=True,
            )

        generated = output[0][encoded["input_ids"].shape[1] :]
        text = tokenizer.decode(generated, skip_special_tokens=True).strip()
        return GenerateResponse(
            text=text,
            device="cpu",
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Model service unavailable: {exc}") from exc
