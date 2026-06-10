"""
Agent输出JSON Schema定义

每个Agent的分析结果都使用Pydantic模型定义结构，
确保输出格式统一、可解析、可聚合。
"""

from pydantic import BaseModel, Field


# ── 市场分析 ──────────────────────────────────────────────

class MarketSizeItem(BaseModel):
    value: str = Field(description="市场规模数值（如'120亿RMB'）")
    source: str = Field(description="数据来源")
    year: str = Field(description="数据年份")


class TAMSamSom(BaseModel):
    tam: MarketSizeItem = Field(description="Total Addressable Market - 总可达市场")
    sam: MarketSizeItem = Field(description="Serviceable Addressable Market - 可服务市场")
    som: MarketSizeItem = Field(description="Serviceable Obtainable Market - 可获得市场")


class GrowthTrend(BaseModel):
    cagr: str = Field(description="复合年增长率（如'25%'）")
    drivers: list[str] = Field(description="增长驱动因素列表")
    forecast: str = Field(description="未来3-5年趋势预判")


class UserPersona(BaseModel):
    segment: str = Field(description="用户群体名称")
    description: str = Field(description="用户画像描述")
    pain_points: list[str] = Field(description="核心痛点")
    willingness_to_pay: str = Field(description="付费意愿评估（高/中/低）")
    decision_path: str = Field(description="典型决策路径")


class MarketAnalysisOutput(BaseModel):
    """市场分析师结构化输出"""
    startup_idea: str = Field(description="分析的创业方向")
    tam_sam_som: TAMSamSom = Field(description="市场规模估算")
    growth_trends: GrowthTrend = Field(description="市场增长趋势")
    user_personas: list[UserPersona] = Field(description="目标用户画像（2-4个）")
    market_timing: str = Field(description="市场时机分析")
    go_to_market: str = Field(description="建议的进入市场方式")
    key_insights: list[str] = Field(description="核心洞察（3-5条）")


# ── 竞品分析 ──────────────────────────────────────────────

class CompetitorProfile(BaseModel):
    name: str = Field(description="竞品名称")
    type: str = Field(description="类型：direct / indirect / substitute")
    business_model: str = Field(description="商业模式")
    pricing: str = Field(description="定价策略")
    funding_stage: str = Field(description="融资阶段")
    strengths: list[str] = Field(description="核心优势")
    weaknesses: list[str] = Field(description="明显短板")


class DifferentiationOpportunity(BaseModel):
    opportunity: str = Field(description="差异化机会描述")
    evidence: str = Field(description="支撑依据")
    difficulty: str = Field(description="实现难度（高/中/低）")


class EntryBarrier(BaseModel):
    barrier: str = Field(description="进入壁垒类型")
    description: str = Field(description="具体描述")
    level: str = Field(description="壁垒强度（高/中/低）")


class CompetitorAnalysisOutput(BaseModel):
    """竞品调研员结构化输出"""
    startup_idea: str = Field(description="分析的创业方向")
    competitors: list[CompetitorProfile] = Field(description="竞品列表（至少5个直接+3个间接）")
    landscape: str = Field(description="竞争格局判断（蓝海/红海/垄断）")
    market_concentration: str = Field(description="市场集中度分析")
    differentiation_opportunities: list[DifferentiationOpportunity] = Field(description="差异化机会")
    entry_barriers: list[EntryBarrier] = Field(description="行业进入壁垒")


# ── 财务分析 ──────────────────────────────────────────────

class PricingTier(BaseModel):
    tier_name: str = Field(description="定价层级名称")
    price: str = Field(description="价格")
    target_segment: str = Field(description="目标客群")
    key_features: list[str] = Field(description="包含的核心功能")


class LTVAnalysis(BaseModel):
    estimated_ltv: str = Field(description="客户生命周期价值估算")
    avg_contract_duration: str = Field(description="平均合同周期")
    monthly_arpu: str = Field(description="月均ARPU")
    churn_rate: str = Field(description="预期月流失率")
    assumptions: list[str] = Field(description="关键假设")


class CACAnalysis(BaseModel):
    estimated_cac: str = Field(description="获客成本估算")
    channels: list[str] = Field(description="主要获客渠道")
    channel_cac_breakdown: list[str] = Field(description="各渠道CAC明细")
    payback_period: str = Field(description="回本周期")
    assumptions: list[str] = Field(description="关键假设")


class UnitEconomics(BaseModel):
    ltv_cac_ratio: str = Field(description="LTV/CAC比值")
    margin: str = Field(description="毛利率估算")
    breakeven_units: str = Field(description="盈亏平衡所需客户数")
    breakeven_time: str = Field(description="预计达到盈亏平衡时间")
    assessment: str = Field(description="单位经济模型评估（健康/一般/需优化）")


class FundingRequirement(BaseModel):
    phase: str = Field(description="阶段（如：MVP/种子轮/A轮）")
    amount: str = Field(description="所需金额")
    duration: str = Field(description="覆盖周期")
    key_expenses: list[str] = Field(description="主要支出项")


class FinanceAnalysisOutput(BaseModel):
    """财务分析师结构化输出"""
    startup_idea: str = Field(description="分析的创业方向")
    revenue_model: str = Field(description="推荐的收入模式（SaaS订阅/交易抽佣/按量计费等）")
    pricing_strategy: list[PricingTier] = Field(description="定价策略")
    ltv_analysis: LTVAnalysis = Field(description="客户生命周期价值分析")
    cac_analysis: CACAnalysis = Field(description="获客成本分析")
    unit_economics: UnitEconomics = Field(description="单位经济模型")
    funding_requirements: list[FundingRequirement] = Field(description="资金需求估算")
    financial_risks: list[str] = Field(description="主要财务风险")
    key_insights: list[str] = Field(description="核心财务洞察（3-5条）")


# ── 风险评审 ──────────────────────────────────────────────

class RiskItem(BaseModel):
    dimension: str = Field(description="风险维度（技术/市场/团队/资金/政策/时机）")
    level: str = Field(description="风险等级（高/中/低）")
    description: str = Field(description="风险描述")
    mitigation: str = Field(description="缓解措施")


class RiskReviewOutput(BaseModel):
    """风险评审员结构化输出"""
    startup_idea: str = Field(description="分析的创业方向")
    risks: list[RiskItem] = Field(description="各维度风险列表")
    overall_risk_level: str = Field(description="整体风险评级（高/中/低）")
    top_risks: list[str] = Field(description="最关键的3个风险")
    risk_mitigation_priority: list[str] = Field(description="风险缓解优先级排序")


# ── 战略报告 ──────────────────────────────────────────────

class ActionItem(BaseModel):
    action: str = Field(description="具体行动项")
    timeline: str = Field(description="建议时间")
    priority: str = Field(description="优先级（P0/P1/P2）")


class StrategyReportOutput(BaseModel):
    """战略顾问结构化输出 — 最终评估报告"""
    startup_idea: str = Field(description="分析的创业方向")
    decision: str = Field(description="决策：Go / No-Go / Conditional-Go")
    executive_summary: str = Field(description="一句话结论")
    market_opportunity_summary: str = Field(description="市场机会核心结论")
    competitive_advantage: str = Field(description="推荐的差异化策略")
    financial_viability: str = Field(description="财务可行性评估")
    key_risks: list[str] = Field(description="Top 3 风险及应对")
    conditions: list[str] = Field(description="如果是Conditional-Go，需要满足的条件")
    next_steps: list[ActionItem] = Field(description="下一步行动计划")
    mvp_scope: str = Field(description="建议的MVP范围")
    funding_estimate: str = Field(description="启动阶段资金需求估算")
    final_confidence: str = Field(description="信心度（高/中/低）及理由")
