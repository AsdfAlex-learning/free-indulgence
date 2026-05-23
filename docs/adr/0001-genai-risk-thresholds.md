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
| 1-4 | moderate | Warn the user, let them decide |
| 0 | low | Skip, inform the user of low risk |

### Scoring Dimensions and Weights (Max 19)

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
| 9 | Parenthesis density | 2 | >1.5/sentence +2, >0.8/sentence +1 | Over-explanation signal. AI text overuses parenthetical asides to layer explanations, creating a clustered, defensive writing pattern |
| 10 | Bold-header + sub-total in small paragraphs | 1 | ≥2 paragraphs +1 | Template structure detection: small paragraphs (<100 words) with bold-header openers followed by sub-points and summary. Highly characteristic of AI survey/related-work sections |

### Weighting Rationale

- **Perplexity dimensions (#1-3, #9) carry the highest weight**: Lexical statistical features are the hardest to eliminate through simple rewriting, and detectors are most sensitive to them. Parenthesis density (#9) is added to the high-weight group because parenthetical over-explanation directly contributes to vocabulary predictability and sentence clutter.
- **Burstiness dimensions (#4-5) come second**: Structural features can be improved through deliberate sentence-level adjustments, but require the Agent to understand and actively execute them.
- **Surface patterns (#6-8, #10) are auxiliary**: These are habitual expressions in AI writing; individually insufficient for judgment, but significantly increase risk when combined.

### Threshold Selection Rationale

- **Score of 5** as the high threshold: Requires at least one primary dimension reaching a high value (e.g., AI vocab density >5% for +3), or a combination of several moderate anomalies. Set deliberately low to catch early-stage AI contamination.
- **Score of 1** as the moderate threshold: A single 1-point anomaly triggers moderate. This is intentionally sensitive — even one hit of "leverage" or one instance of "Notably," flags the text for user review.
- **Score of 0** as low: Only when no dimension triggers any anomaly. The text must be statistically clean across all 10 dimensions.

## Consequences

- Thresholds are **preliminary** and may need tuning based on false positive/negative rates observed in actual use.
- The 8-dimension coverage may be incomplete — future detection dimensions may need to be added (e.g., paragraph template structure, copula avoidance, and other LLM-judgment dimensions are currently not included in the script scoring).
- False positives caused by domain-specific terminology density (e.g., "robust optimization" is standard in operations research) need to be distinguished through LLM semantic judgment, which cannot be resolved at the script level.
