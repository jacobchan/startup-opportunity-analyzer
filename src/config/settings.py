from dotenv import load_dotenv
import os

load_dotenv()

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
