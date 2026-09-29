"""
orion_model_server.py
=====================
A standalone FastAPI process that loads the model ONCE and serves it forever.
Run this separately from your main uvicorn server:

    python orion_model_server.py

Then your main app proxies to it via http://localhost:8001/generate.
This way the main app can --reload freely without ever touching the GPU model.
"""
import os, time, logging
from functools import lru_cache
from threading import Thread
from typing import Iterator

import torch
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("orion.model_server")

MODEL_BASE     = os.getenv("ORION_BASE_MODEL",   "deepseek-ai/deepseek-coder-1.3b-instruct")
ADAPTER_PATH   = os.getenv("ORION_ADAPTER_PATH", "./fine_tuned_model")
MAX_NEW_TOKENS = int(os.getenv("ORION_MAX_TOKENS", "150"))
TEMPERATURE    = 0.05
PORT           = int(os.getenv("ORION_MODEL_PORT", "8001"))

app = FastAPI(title="Orion Model Server")

SYSTEM_PROMPT = (
    "You are Orion, an expert code structure analyst. "
    "Given a knowledge graph context extracted from a Python repository, "
    "answer the developer's question accurately and concisely. "
    "Base your answer solely on the graph data provided."
)


@lru_cache(maxsize=1)
def _load():
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    cuda = torch.cuda.is_available()
    device = "cuda" if cuda else "cpu"
    logger.info(f"Loading base model on {device.upper()}: {MODEL_BASE}")

    if cuda:
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        base = AutoModelForCausalLM.from_pretrained(
            MODEL_BASE, quantization_config=bnb, device_map="auto", trust_remote_code=True
        )
    else:
        base = AutoModelForCausalLM.from_pretrained(
            MODEL_BASE, torch_dtype=torch.float32, device_map="cpu",
            trust_remote_code=True, low_cpu_mem_usage=True,
        )

    model = PeftModel.from_pretrained(base, ADAPTER_PATH)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Build stop IDs from added_tokens_encoder only
    stop_ids = set()
    if tokenizer.eos_token_id is not None:
        stop_ids.add(tokenizer.eos_token_id)
    added = getattr(tokenizer, "added_tokens_encoder", {})
    for tok in ["<|user|>", "<|system|>", "<|assistant|>", "<|EOT|>", "<EOT>"]:
        if tok in added:
            stop_ids.add(added[tok])
    stop_ids = sorted(stop_ids)
    logger.info(f"Model ready on {device.upper()}. Stop token IDs: {stop_ids}")

    return model, tokenizer, stop_ids, device


def _build_prompt(question: str, context: str) -> str:
    return (
        f"<|system|>\n{SYSTEM_PROMPT}\n"
        f"<|user|>\n[GRAPH CONTEXT]\n{context}\n\n"
        f"[QUESTION]\n{question}\n"
        f"<|assistant|>\n"
    )


def _clean(text: str) -> str:
    for tag in ["<|user|>", "<|system|>", "<|assistant|>", "<|EOT|>"]:
        if tag in text:
            text = text.split(tag)[0]
    return text.strip()


class GenerateRequest(BaseModel):
    question: str
    context: str


class GenerateResponse(BaseModel):
    answer: str
    latency_ms: float
    device: str


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    model, tokenizer, stop_ids, device = _load()
    prompt = _build_prompt(req.question, req.context)
    enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    enc = {k: v.to(device) for k, v in enc.items()}

    t0 = time.perf_counter()
    with torch.no_grad():
        out = model.generate(
            **enc,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            do_sample=TEMPERATURE > 0,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=stop_ids,
        )
    ms = (time.perf_counter() - t0) * 1000

    new_toks = out[0][enc["input_ids"].shape[1]:]
    answer = _clean(tokenizer.decode(new_toks, skip_special_tokens=True))
    return GenerateResponse(answer=answer, latency_ms=round(ms, 1), device=device)


@app.post("/stream")
async def stream(req: GenerateRequest):
    from transformers import TextIteratorStreamer
    model, tokenizer, stop_ids, device = _load()
    prompt = _build_prompt(req.question, req.context)
    enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    enc = {k: v.to(device) for k, v in enc.items()}
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    Thread(target=model.generate, kwargs=dict(
        **enc, max_new_tokens=MAX_NEW_TOKENS, temperature=TEMPERATURE,
        do_sample=TEMPERATURE > 0, pad_token_id=tokenizer.eos_token_id,
        eos_token_id=stop_ids, streamer=streamer,
    ), daemon=True).start()

    def token_iter() -> Iterator[str]:
        buf = ""
        for token in streamer:
            buf += token
            for tag in ["<|user|>", "<|system|>", "<|assistant|>"]:
                if tag in buf:
                    yield buf.split(tag)[0]
                    return
            yield token

    return StreamingResponse(token_iter(), media_type="text/plain")


@app.get("/health")
async def health():
    cache_info = _load.cache_info()
    cuda = torch.cuda.is_available()
    info = {"model_loaded": cache_info.currsize > 0, "device": "cuda" if cuda else "cpu"}
    if cuda:
        info["vram"] = [
            {"gpu": i, "used_gb": round((t-f)/1e9, 2), "total_gb": round(t/1e9, 2)}
            for i, (f, t) in enumerate(torch.cuda.mem_get_info(i) for i in range(torch.cuda.device_count()))
        ]
    return info


@app.post("/warm")
async def warm():
    t0 = time.perf_counter()
    _load()
    ms = (time.perf_counter() - t0) * 1000
    _, _, _, device = _load()
    return {"status": "ready", "device": device, "load_ms": round(ms, 1)}


if __name__ == "__main__":
    logger.info(f"Starting Orion Model Server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
