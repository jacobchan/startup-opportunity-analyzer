from __future__ import annotations

from typing import TYPE_CHECKING

from dotenv import load_dotenv
import os

load_dotenv()

if TYPE_CHECKING:
    from crewai import LLM

# LLM Configuration
# 支持切换：deepseek-v4-pro | anthropic/claude-sonnet-4-6
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")

# DeepSeek API（OpenAI兼容格式）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Tools
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Output
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "output")


def build_llm() -> "LLM":
    """Construct the configured LLM instance.

    The same factory is used by the CLI (hierarchical) and the web runner
    (deliberation engine) so they share behaviour when ``LLM_MODEL`` is
    switched at runtime via the environment.
    """
    from crewai import LLM
    model = os.getenv("LLM_MODEL", "deepseek-v4-pro")
    if "deepseek" in model:
        return LLM(
            model=model,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    return LLM(model=model)
