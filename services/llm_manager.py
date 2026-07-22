from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os
import logging
import asyncio

logger = logging.getLogger(__name__)


class FallbackLLMManager:
    """
    A robust LLM manager that automatically rotates between multiple free-tier
    AI providers when a quota limit (429) or any error is encountered.

    Fallback priority order:
      1. Google Gemini 2.5 Flash
      2. Google Gemini 2.5 Flash-Lite
      3. Groq GPT-OSS 20B
      4. Groq GPT-OSS 120B
    """

    def __init__(self):
        self.providers: list[dict] = []
        self.request_timeout = max(5, int(os.getenv("RAGIFY_LLM_TIMEOUT", "45")))
        self._build_providers()

        if not self.providers:
            logger.warning(
                "No valid LLM API keys found. The system cannot generate responses. "
                "Set GEMINI_API_KEY and/or GROQ_API_KEY in your .env file."
            )
        else:
            names = [p["name"] for p in self.providers]
            logger.info(f"LLM Fallback chain ready with {len(names)} models: {names}")

    def _build_providers(self):
        """Build the ordered list of available LLM providers from env variables."""
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        groq_key = os.getenv("GROQ_API_KEY", "").strip()

        # ── 1 & 2: Google Gemini ──────────────────────────────────────────────
        if gemini_key and gemini_key not in ("your_gemini_key_here", ""):
            for model_name, label in [
                ("gemini-2.5-flash", "Gemini 2.5 Flash"),
                ("gemini-2.5-flash-lite", "Gemini 2.5 Flash-Lite"),
            ]:
                try:
                    llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=gemini_key,
                        temperature=0.2,
                    )
                    self.providers.append({"name": label, "llm": llm})
                    logger.info(f"✓ {label} loaded.")
                except Exception as exc:
                    logger.warning(f"✗ {label} failed to load: {exc}")

        # ── 3–7: Groq (multiple models = multiple independent rate limits) ────
        # Each model has its own quota → 5 independent fallback slots
        if groq_key and groq_key not in ("your_groq_key_here", ""):
            groq_models = [
                ("openai/gpt-oss-20b", "Groq GPT-OSS 20B"),
                ("openai/gpt-oss-120b", "Groq GPT-OSS 120B"),
            ]
            for model_id, label in groq_models:
                try:
                    llm = ChatGroq(
                        model_name=model_id,
                        groq_api_key=groq_key,
                        temperature=0.2,
                    )
                    self.providers.append({"name": label, "llm": llm})
                    logger.info(f"✓ {label} loaded.")
                except Exception as exc:
                    logger.warning(f"✗ {label} failed to load: {exc}")

    async def generate_response(self, prompt: str) -> str:
        """
        Try each provider in order. On any exception (rate-limit, timeout, etc.)
        immediately move on to the next provider without surfacing the error to
        the caller until every provider has been exhausted.
        """
        if not self.providers:
            raise RuntimeError(
                "No LLM providers are configured. Please add API keys to the .env file."
            )

        last_exception: Exception | None = None

        for provider in self.providers:
            name = provider["name"]
            llm  = provider["llm"]
            try:
                logger.info(f"Attempting response with {name}...")
                response = await asyncio.wait_for(
                    llm.ainvoke([HumanMessage(content=prompt)]),
                    timeout=self.request_timeout,
                )
                logger.info(f"✓ Response received from {name}.")
                return response.content
            except Exception as exc:
                logger.warning(
                    f"✗ {name} failed ({type(exc).__name__}: {exc}). "
                    "Switching to next provider..."
                )
                last_exception = exc
                # Small delay before trying next provider to avoid hammering APIs
                await asyncio.sleep(0.5)

        raise RuntimeError(
            f"All {len(self.providers)} LLM providers failed. "
            f"Last error: {last_exception}"
        )

    @property
    def available_models(self) -> list[str]:
        """Return names of all loaded models (useful for health-check endpoint)."""
        return [p["name"] for p in self.providers]


# Singleton – imported by main.py
llm_manager = FallbackLLMManager()
