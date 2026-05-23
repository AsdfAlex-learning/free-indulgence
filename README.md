# FreeIndulgence

**Academic English Polish & AI Pattern Removal for OpenCode / Claude Code**

FreeIndulgence is an agent skill that reduces GenAI detection scores in academic manuscripts by targeting both **surface patterns** (AI-favored vocabulary, mechanical connectors, bullet-heavy structure) and **statistical fingerprints** (perplexity and burstiness). It bundles a deterministic detection script with an agent workflow for surgical rewrite.

> **Why "FreeIndulgence"?** Just as indulgences absolved sins in medieval times, this skill absolves your text of its AI-generated stains—for free.

---

## Features

| Capability | Description |
|------------|-------------|
| **SCI Polish** | Grammar, clarity, and academic register correction |
| **Top-Conference Polish** | NeurIPS/ICLR/ICML zero-error publication standard |
| **Statistical De-AI** | Targets perplexity (word predictability) and burstiness (sentence length variance) |
| **Code Comment Hygiene** | Three-tier comment classification: keep → rewrite → delete |
| **Bullet→Prose Conversion** | Converts AI-typical bullet structures into flowing paragraphs |
| **Connector Block Rewrite** | Flattens "First… Second… Third… Finally" structures into coherent arguments |
| **Multi-Format Support** | Plain text, LaTeX (.tex), Markdown, code blocks (20+ languages) |

---

## Quick Start

### Prerequisites

- Python 3.8+ (for the detection script)
- OpenCode or Claude Code

### Installation

**Option A: Load as a project skill**

Clone this repo into your project or workspace:

```bash
git clone git@github.com:AsdfAlex-learning/free-indulgence.git
```

Then add to your `opencode.json`, `CLAUDE.md`, or `AGENTS.md`:

```json
{
  "skills": [".skills/free-indulgence"]
}
```

**Option B: Install as a user-level skill**

```bash
git clone git@github.com:AsdfAlex-learning/free-indulgence.git ~/.claude/skills/free-indulgence
```

### Usage

```
/fi                                 # Full pipeline: SCI polish + de-AI
/fi path/to/paper.tex               # Process a file
/fi -p                              # SCI polish only
/fi -t                              # Top-conference polish + de-AI
/fi -d                              # De-AI only (no polish)
/fi -p -t                           # Top-conference polish only
```

---

## How It Works

FreeIndulgence operates on two layers of AI text detection:

### Layer 1: Deterministic Script (`scripts/detect.py`)

A Python script scans the input and produces a structured JSON report covering:

- **Prose patterns**: AI vocabulary density, mechanical connectors, hedging stacks, filler phrases, significance inflation
- **Structural patterns**: Bullet density, total-sub-total templates, connector logic blocks
- **Code comments**: Extracts and classifies into Tier 1 (keep), Tier 2 (rewrite), Tier 3 (delete)
- **GenAI Risk Score**: 0–16 composite score based on 8 dimensions of perplexity and burstiness proxies

### Layer 2: Agent Workflow (`SKILL.md`)

The agent:

1. **Segments** input into zones (Prose, Code Block, Inline Code, Math, LaTeX Commands)
2. **Polishes** prose zones (SCI or top-conference level)
3. **Runs** the detection script
4. **Audits** via a 12-point forced checklist
5. **Presents** a combined diagnostic report to the user
6. **Rewrites** with anti-AI-smell techniques (perplexity check, burstiness check, self-audit)
7. **Verifies** with a second pass

### The Theory

AI detectors (Turnitin, GPTZero, Originality.ai) measure two statistical signals:

| Signal | What It Measures | AI-Like | Human-Like |
|--------|-----------------|---------|------------|
| **Perplexity** | How predictable each word is given its context | Low (every word is the statistically most likely choice) | High (varied, unpredictable word choices) |
| **Burstiness** | How much sentence lengths vary within a paragraph | Low (uniform sentence structure) | High (long sentences mixed with short fragments) |

FreeIndulgence rewrites to simultaneously raise both signals, breaking the statistical fingerprint without relying on synonym-swapping or "word obfuscation" tricks.

---

## Project Structure

```
free-indulgence/
├── SKILL.md               # Agent workflow instructions (main entry)
├── CONTEXT.md              # Terminology glossary for the domain
├── README.md               # This file
├── LICENSE                 # MIT License
├── CHANGELOG.md            # Version history
├── .gitignore
├── scripts/
│   └── detect.py           # Deterministic AI pattern detection (Python)
└── docs/
    └── adr/
        └── 0001-genai-risk-thresholds.md   # Architecture Decision Record
```

---

## For Developers

### Detection Script

```bash
python scripts/detect.py < input.txt
python scripts/detect.py path/to/file.tex
python scripts/detect.py --json
```

Output: JSON with keys `prose`, `connector_blocks`, `genai_risk`, `code_blocks`, `summary`.

### Architecture Decisions

See [docs/adr/0001-genai-risk-thresholds.md](docs/adr/0001-genai-risk-thresholds.md) for the rationale behind the risk scoring thresholds and dimension weights.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Why Not Just Use an AI Detector?

AI detectors tell you a problem exists. FreeIndulgence fixes it. The combination of deterministic pattern matching (script) + semantic understanding (agent) is what makes this effective—the script catches what's measurable, the agent fixes what's meaningful.
