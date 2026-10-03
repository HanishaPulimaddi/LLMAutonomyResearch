"""Provider-independent LLM interface.

    LLMClient  ->  GroqLLMClient  ->  Groq API
               ->  MockLLMClient  (no API calls)

Configuration (environment variables, or a .env file in the project root):
    LLM_MODE      "mock" (default) or "groq"
    GROQ_API_KEY  required when LLM_MODE=groq
    GROQ_MODEL    required when LLM_MODE=groq
"""
import os
from abc import ABC, abstractmethod
from pathlib import Path

from dotenv import load_dotenv

from prompts import Prompt

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class LLMClient(ABC):
    provider: str
    model_name: str

    @abstractmethod
    def complete(self, prompt: Prompt) -> str:
        """Send one prompt and return the raw text response."""


class GroqLLMClient(LLMClient):
    provider = "groq"

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        model = os.environ.get("GROQ_MODEL")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to .env or the environment.")
        if not model:
            raise RuntimeError("GROQ_MODEL is not set. Add it to .env or the environment.")
        from groq import Groq  # imported here so mock mode does not need the SDK

        self._client = Groq(api_key=api_key)
        self.model_name = model

    def complete(self, prompt):
        extra = {"response_format": {"type": "json_object"}} if prompt.json_mode else {}
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            temperature=0,
            **extra,
        )
        return response.choices[0].message.content or ""


class MockLLMClient(LLMClient):
    """Returns fixed, obviously fake responses in each architecture's output format.

    Responses do not depend on the applicant or on any ground-truth data.
    """
    provider = "mock"
    model_name = "mock"

    RESPONSES = {
        "arch_a_llm_only": "Mock response; no model was called.\nDECISION: INELIGIBLE\nEFFECTIVE_DATE: 1900-01-01",
        "arch_b_llm_validation": '{"eligible": false, "effective_eligibility_date": "1900-01-01", '
                                 '"claimable_interruption_months": 0, "reasoning": "Mock response; no model was called."}',
        "arch_c_extraction": '{"phd_award_date": "1900-01-01", "interruptions": []}',
    }

    def complete(self, prompt):
        return self.RESPONSES[prompt.name]


def get_client() -> LLMClient:
    mode = os.environ.get("LLM_MODE", "mock").strip().lower()
    if mode == "mock":
        return MockLLMClient()
    if mode == "groq":
        return GroqLLMClient()
    raise RuntimeError(f"Unknown LLM_MODE {mode!r}; expected 'mock' or 'groq'.")
