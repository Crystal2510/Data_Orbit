"""
client.py — Unified LLM Client

Provides a single LLMClient class that abstracts over multiple LLM providers.
Switch between OpenAI, Anthropic (Claude), and Groq by changing one env var.

Design decisions:
 - Provider is read from settings.LLM_PROVIDER at instantiation
 - complete() returns raw text; complete_json() wraps it with JSON parsing
 - tenacity handles transient API failures (rate limits, timeouts)
 - Graceful degradation: errors are logged and surfaced as strings, never raised
   silently into the agent pipeline
"""

import json
import logging
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Provider-agnostic LLM client.

    Usage:
        client = LLMClient()
        text   = client.complete("You are an analyst.", "Summarize this table.")
        data   = client.complete_json("You are an analyst.", "Return JSON docs.")
    """

    def __init__(self) -> None:
        self.provider = getattr(settings, "LLM_PROVIDER", "openai").lower()
        self._init_client()

    def _init_client(self) -> None:
        """Lazily initialise the underlying SDK client for the chosen provider."""
        if self.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            self._model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=getattr(settings, "ANTHROPIC_API_KEY", "")
            )
            self._model = getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        elif self.provider == "groq":
            from groq import Groq
            self._client = Groq(api_key=getattr(settings, "GROQ_API_KEY", ""))
            self._model = getattr(settings, "GROQ_MODEL", "llama-3.1-70b-versatile")

        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.provider}'. "
                "Choose from: openai, anthropic, groq"
            )
        logger.info(f"LLMClient initialised — provider={self.provider}, model={self._model}")

    

    @retry(
        
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=False,         
    )
    def _call_provider(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        """
        Internal method that calls the provider SDK.
        Decorated with retry — tenacity will catch exceptions and retry.
        Returns raw text string from the model.
        """
        if self.provider == "openai":
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        elif self.provider == "anthropic":
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text or ""

        elif self.provider == "groq":
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        return ""  

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """
        Call the LLM and return raw text.
        Returns an error string on failure — never raises — so agent pipelines
        can continue even if one LLM call fails.
        """
        try:
            result = self._call_provider(system_prompt, user_prompt, temperature)
            return result
        except Exception as exc:
           
            logger.error(f"LLMClient.complete failed after retries: {exc}")
            return f"[LLM_ERROR] {str(exc)}"

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """
        Call the LLM and parse the response as JSON.

        Prompt engineering: we append an explicit JSON reminder to the system
        prompt to reduce markdown code-fence wrapping (```json ... ```) which
        would break json.loads().

        Returns an empty dict with an "error" key on parse failures.
        """
        
        json_system = (
            system_prompt
            + "\n\nCRITICAL: Respond ONLY with valid JSON. "
            "No markdown fences. No explanation before or after the JSON object."
        )

        raw = self.complete(json_system, user_prompt, temperature=0.1)

        if raw.startswith("[LLM_ERROR]"):
            return {"error": raw}

        
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            
            cleaned = cleaned.split("\n", 1)[-1]          
            cleaned = cleaned.rsplit("```", 1)[0].strip() 

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(f"JSON parse failed. Raw response:\n{raw}\nError: {exc}")
            return {"error": f"JSON parse error: {exc}", "raw_response": raw}