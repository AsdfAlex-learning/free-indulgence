# ADR-0001: GenAI Risk Scoring Thresholds and Weighting Scheme

## Status

Accepted (pending validation through real-world testing)

## Context

The Skill needs to quantify the GenAI detector risk (perplexity + burstiness) of a text and decide on a rewrite strategy accordingly. A scoring system is needed to map multi-dimensional detection signals to three action levels: force rewrite, suggest review, skip.

## Decision

### Thresholds

| Score Range | Risk Level | Action |
|-------------|------------|--------|
| ≥5 | high | Flag for recommended forced rewrite (user can override) |
| 2-4 | moderate | Warn the user, let them decide |
| 0-1 | low | Skip, inform the user of low risk |

### Scoring Dimensions and Weights (Max 16)

| # | Dimension | Max Score | Threshold | Rationale |
|---|-----------|-----------|-----------|-----------|
| 1 | AI vocabulary density | 3 | >5% +3, >2% +1 | Primary proxy for perplexity. AI-generated text has significantly higher AI vocabulary density than human writing |
| 2 | Mechanical connector density | 2 | >2% +2, >0.5% +1 | Connector density is one of the most reliable detector signals |
| 3 | Vocabulary diversity (unique/total) | 2 | <40% +2, <55% +1 | Low diversity = predictable word choice = low perplexity |
| 4 | Sentence length variance | 3 | <3.0 and >5 sentences +3, <5.0 and >3 sentences +1 | Core proxy for burstiness. Low variance → uniform sentence structure → pronounced AI features |
| 5 | Bullet density | 2 | >30% +2, >15% +1 | Bullet formatting is one of the most prominent structural features in AI-generated text |
| 6 | Hedging density | 1 | >0.3/sentence +1 | Auxiliary metric: excessive hedging increases predictability |
| 7 | Filler density | 1 | >0.3/sentence +1 | Auxiliary metric: filler phrases are a common AI writing pattern |
| 8 | Significance inflation | 1 | Present +1 | Auxiliary metric: inflated language is highly correlated with AI text |

### Weighting Rationale

- **Perplexity dimensions (#1-3) carry the highest weight**: Lexical statistical features are the hardest to eliminate through simple rewriting, and detectors are most sensitive to them.
- **Burstiness dimensions (#4-5) come second**: Structural features can be improved through deliberate sentence-level adjustments, but require the Agent to understand and actively execute them.
- **Surface patterns (#6-8) are auxiliary**: These are habitual expressions in AI writing; individually insufficient for judgment, but significantly increase risk when combined.

### Threshold Selection Rationale

- **Score of 5** as the high threshold: Requires at least one primary dimension (AI vocabulary or sentence variance) to reach a high value, or two moderate dimensions to combine. This avoids forced rewriting triggered by a single false match.
- **Score of 2** as the moderate threshold: A single mild anomaly in any dimension (a 1-point dimension hit) does not trigger a warning; requires at least two mild anomalies or one moderate anomaly.
- **Score of 0-1** as low: The text is statistically very close to human writing.

## Consequences

- Thresholds are **preliminary** and may need tuning based on false positive/negative rates observed in actual use.
- The 8-dimension coverage may be incomplete — future detection dimensions may need to be added (e.g., paragraph template structure, copula avoidance, and other LLM-judgment dimensions are currently not included in the script scoring).
- False positives caused by domain-specific terminology density (e.g., "robust optimization" is standard in operations research) need to be distinguished through LLM semantic judgment, which cannot be resolved at the script level.
