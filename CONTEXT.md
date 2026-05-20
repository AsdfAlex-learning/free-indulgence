# CONTEXT.md — FreeIndulgence Skill Glossary

> This document defines the domain language of the Skill. When modifying Skill behavior, terminology must be consistent with this document.
> Does not contain implementation details, threshold tuning records, or design decisions.

---

## Zone

The input text is split into mutually exclusive zones before processing. Each zone has independent processing rules.

| Term | Definition |
|------|------------|
| **Prose** | Natural language paragraphs, sentences, captions. The Skill's core processing target. |
| **Code Block** | Code blocks: Markdown fences (```), LaTeX environments (lstlisting/minted/verbatim/algorithm), indented code. **Code body is never modified**; comments and print strings are handled separately. |
| **String Literal in Code** | String literals inside code: `print(f"...")`, `logger.info("...")`, `raise ValueError("...")`, `assert ... , "..."`. Content is treated as Prose embedded in code. |
| **Inline Code** | Inline code: `` `code` ``, `\texttt{...}`, `\lstinline{...}`. Skipped entirely. |
| **Math** | Mathematical formulas: `$...$`, `$$...$$`, `\begin{equation}`. Skipped entirely. |
| **LaTeX Commands** | LaTeX commands: `\cite{}`, `\ref{}`, `\label{}`, `\textbf{}`. Preserved without modification. |

---

## Operation

| Term | Definition | Corresponding Command |
|------|------------|----------------------|
| **Polish** | Fix grammar, spelling, clarity, and academic register. Does not change content meaning. Executed on Prose zones. | `--polish-only` |
| **De-AI** | Remove AI generation traces — both surface patterns (vocabulary, connectors) and statistical fingerprints (perplexity, burstiness). Executed on Prose zones + code comments. | `--deai-only` |
| **Humanize** | Full pipeline of Polish + De-AI. Default behavior. | `/humanize` (no arguments) |

---

## Detection Signal

AI detectors do not look at specific words; they measure statistical features.

| Term | Definition | Low = AI-like | High = Human-like |
|------|------------|---------------|-------------------|
| **Perplexity** | How difficult it is to predict the next word given the preceding context. Proxy metrics: AI vocabulary density, mechanical connector density, vocabulary diversity (unique/total ratio). | Every word is the statistically most likely choice | Varied, unpredictable word choices |
| **Burstiness** | The degree of variation in sentence lengths within a paragraph. Proxy metrics: sentence length variance, bullet density. | Uniform sentence lengths, structured formatting | Mixed long and short sentences, varied structure |
| **GenAI Risk** | Composite score of Perplexity + Burstiness (0-16). Quantified by the `detect.py` script. Three tiers: high (≥5, overly conformant), moderate (2-4, somewhat conformant), low (0-1, normal range). |

---

## Structural Pattern

Three types of structured writing patterns that appear in Prose, each triggering a different rewrite strategy.

| Term | Definition | Trigger Condition | Rewrite Direction |
|------|------------|-------------------|-------------------|
| **Connector Logic Block** | Cross-sentence/cross-paragraph sequences of sequential connectors (First... Second... Third... Finally...). 7 sequence types total. | Script detects ≥2 sequential markers within 200 words | Rewrite the entire block as one coherent argument. Focus: break mechanical repetition, uniform sentence patterns, enforce coherence, low perplexity + low burstiness. |
| **Bullet Density** | Proportion of bullet points or numbered lists in Prose. | `bullet_density > 30%` | Force rewrite into coherent paragraphs. Specify "ensure slightly elevated burstiness." For coordinate relationships, emphasize differences; for subordinate relationships, explain the logic. |
| **Total-Sub-Total** | Template structure within a single paragraph: overview sentence → sub-point group → summary sentence (often repeats the first). | LLM semantic judgment (script-assisted) | Restructure the paragraph, break the templated opening and repetitive ending. |

> These are three different levels of problems and must not be handled together. Connector Block is a cross-sentence logical connection issue, Bullet is a visual formatting issue, and Total-Sub-Total is an internal paragraph structure issue.

---

## Comment Tier

Three-tier classification system for code comments.

| Term | Definition | Example | Action |
|------|------------|---------|--------|
| **Tier 1** | Concise "Why" comments: explain rationale, assumptions, algorithm choices, literature references. ≤1 line preferred. | `# Apply L2 regularization (§3.2)` | Keep |
| **Tier 2** | Comments containing AI vocabulary, overly verbose, or using bullets/numbering but with informative content. | `// This function leverages the robust pipeline...` | Rewrite to be concise and natural |
| **Tier 3** | Redundant "What" comments: narrating obvious code behavior. Comments with bullets/numbering and >10 words are always classified here. | `# increment counter by 1` | Delete |

---

## Key Script Output Fields

Fields that the Agent needs to understand when reading script JSON output.

| Field | Meaning | Source |
|-------|---------|--------|
| `prose.bullet_density` | Proportion of bullet lines in Prose (0-1) | Script calculation |
| `prose.ai_vocab_hits` | List of matched AI high-frequency vocabulary | Script regex |
| `prose.sentence_length_variance` | Sentence length variance (lower = more uniform) | Script calculation |
| `prose.total_words` / `unique_words` | Total word count / unique word count | Script calculation |
| `connector_blocks[].sequence_type` | Logical block type (e.g., "first-second-third") | Script detection |
| `genai_risk.risk_tier` | high / moderate / low | Script scoring |
| `genai_risk.score` | Quantitative risk score (0-16) | Script scoring |
| `code_blocks[].comments[].tier` | Per-comment Tier classification (1/2/3) | Script classification + LLM verification |
