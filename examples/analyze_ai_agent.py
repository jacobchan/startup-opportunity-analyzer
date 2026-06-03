"""
示例：分析AI Agent创业方向

运行方式：
    cd startup-opportunity-analyzer
    python -m examples.analyze_ai_agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crew import run_analysis

STARTUP_IDEA = """
面向中小企业的AI Agent客服平台：
- 基于LLM构建智能客服Agent，支持多轮对话、工单自动创建、
  知识库问答
- 提供低代码的Agent编排界面，企业可自定义业务流程
- 集成主流客服渠道（微信、钉钉、飞书、网页）
- SaaS模式，按坐席/对话量计费
"""

if __name__ == "__main__":
    report = run_analysis(
        startup_idea=STARTUP_IDEA,
        save_to=str(Path(__file__).parent / "output" / "ai_agent_analysis.md"),
    )
