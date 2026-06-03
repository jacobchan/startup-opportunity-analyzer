"""
示例：分析垂直行业SaaS创业方向

运行方式：
    cd startup-opportunity-analyzer
    python -m examples.analyze_saas
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crew import run_analysis

STARTUP_IDEA = """
产业园区数字化SaaS平台：
- 为中小型产业园区提供一站式数字化运营平台
- 核心模块：招商管理、物业服务、企业服务、资产管理、能源管理
- 基于IoT中台实现设备设施智能化管理
- SaaS多租户架构，按园区面积/管理单元计费
"""

if __name__ == "__main__":
    report = run_analysis(
        startup_idea=STARTUP_IDEA,
        save_to=str(Path(__file__).parent / "output" / "saas_analysis.md"),
    )
