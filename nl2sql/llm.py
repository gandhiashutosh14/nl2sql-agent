"""
Model backends behind one tiny interface: `complete(messages) -> str`.

  mock                 scripted replies for tests
  hf:<model-id>        a local Hugging Face causal model (GPU if available)
  openai:<model>       any OpenAI-compatible chat endpoint (OpenAI, Groq, Ollama, vLLM, ...)
"""
from __future__ import annotations

import os
import time
from typing import Callable, Dict, List, Optional, Protocol, Sequence, Union

Messages = List[Dict[str, str]]


class LLM(Protocol):
    name: str

    def complete(self, messages: Messages) -> str: ...


class MockLLM:
    """Returns scripted replies in order (the last one repeats), or calls a function of the messages."""

    name = "mock"

    def __init__(self, replies: Union[Sequence[str], Callable[[Messages], str]]):
        self._fn = replies if callable(replies) else None
        self._replies = list(replies) if not callable(replies) else []
        self.calls: List[Messages] = []

    def complete(self, messages: Messages) -> str:
        self.calls.append(messages)
        if self._fn:
            return self._fn(messages)
        if not self._replies:
            return ""
        return self._replies.pop(0) if len(self._replies) > 1 else self._replies[0]


class OpenAICompatLLM:
    """POST {base_url}/chat/completions. Key from `api_key_env` (default OPENAI_API_KEY); Ollama needs none."""

    def __init__(self, model: str, base_url: Optional[str] = None, api_key_env: str = "OPENAI_API_KEY",
                 temperature: float = 0.0, max_tokens: int = 512, timeout_s: float = 120.0):
        self.name = f"openai:{model}"
        self.model = model
        self.base_url = (base_url or os.environ.get("NL2SQL_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def complete(self, messages: Messages) -> str:
        import requests
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {"model": self.model, "messages": messages, "temperature": self.temperature, "max_tokens": self.max_tokens}
        r = requests.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout_s)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"] or ""


class HFLocalLLM:
    """A local instruction-tuned causal model via transformers, greedy decoding."""

    def __init__(self, model_id: str, max_new_tokens: int = 320):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.name = f"hf:{model_id}"
        self.max_new_tokens = max_new_tokens
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype).to(self.device).eval()
        self.last_latency_ms = 0

    def complete(self, messages: Messages) -> str:
        import torch
        t0 = time.perf_counter()
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self.model.generate(**inputs, do_sample=False, max_new_tokens=self.max_new_tokens,
                                      pad_token_id=self.tokenizer.eos_token_id)
        text = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        self.last_latency_ms = int((time.perf_counter() - t0) * 1000)
        return text


def make_llm(spec: str, **kwargs) -> LLM:
    """Build a backend from a spec string: 'mock', 'hf:Qwen/Qwen2.5-Coder-1.5B-Instruct', 'openai:gpt-4o-mini'."""
    if spec == "mock":
        return MockLLM(kwargs.get("replies", [""]))
    kind, _, model = spec.partition(":")
    if kind == "hf" and model:
        return HFLocalLLM(model, **{k: v for k, v in kwargs.items() if k in {"max_new_tokens"}})
    if kind == "openai" and model:
        return OpenAICompatLLM(model, **{k: v for k, v in kwargs.items() if k in {"base_url", "api_key_env", "max_tokens"}})
    raise ValueError(f"Unknown LLM spec '{spec}'. Use mock, hf:<model-id> or openai:<model>.")
