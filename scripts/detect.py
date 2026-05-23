#!/usr/bin/env python3
"""
AI Pattern Detector for paper-deai skill.

Reads text from stdin or a file, identifies code blocks (20+ languages),
extracts comments, classifies them into Tiers 1/2/3, and detects prose
patterns (bullet density, AI vocabulary, mechanical connectors, rhythm, etc.).

Output: JSON to stdout.

Usage:
    python detect.py < input.txt
    python detect.py path/to/file.tex
    python detect.py --json    (read stdin, output compact JSON)
"""

import sys
import re
import json
import os
from typing import Optional

# ── Language comment rules ──────────────────────────────────────────
# Each entry: (name, line_comment, block_start, block_end)
LANGUAGES = {
    "python":   ("Python",   "#",   '"""',  None),  # also supports '''
    "javascript": ("JavaScript", "//", "/*", "*/"),
    "typescript": ("TypeScript", "//", "/*", "*/"),
    "java":     ("Java",     "//", "/*", "*/"),
    "c":        ("C",        "//", "/*", "*/"),
    "cpp":      ("C++",      "//", "/*", "*/"),
    "csharp":   ("C#",       "//", "/*", "*/"),
    "rust":     ("Rust",     "//", "/*", "*/"),
    "go":       ("Go",       "//", "/*", "*/"),
    "ruby":     ("Ruby",     "#",  "=begin", "=end"),
    "php":      ("PHP",      "//", "/*", "*/"),
    "swift":    ("Swift",    "//", "/*", "*/"),
    "kotlin":   ("Kotlin",   "//", "/*", "*/"),
    "scala":    ("Scala",    "//", "/*", "*/"),
    "sql":      ("SQL",      "--", "/*", "*/"),
    "lua":      ("Lua",      "--", "--[[", "]]"),
    "haskell":  ("Haskell",  "--", "{-",  "-}"),
    "latex":    ("LaTeX",    "%",  None,  None),
    "r":        ("R",        "#",  None,  None),
    "julia":    ("Julia",    "#",  "#=",  "=#"),
    "shell":    ("Shell",    "#",  None,  None),
    "yaml":     ("YAML",     "#",  None,  None),
    "perl":     ("Perl",     "#",  None,  None),
}

# Aliases for code fence tags
LANG_ALIASES = {
    "py": "python", "js": "javascript", "ts": "typescript",
    "cs": "csharp", "rb": "ruby", "sh": "shell", "bash": "shell",
    "zsh": "shell", "ps1": "shell", "psm1": "shell",
    "kt": "kotlin", "rs": "rust", "hs": "haskell",
    "jl": "julia", "pl": "perl", "tex": "latex",
    "yml": "yaml", "md": None, "markdown": None, "txt": None,
    "text": None, "plaintext": None, "json": None, "xml": None,
    "html": None, "css": None, "scss": None, "less": None,
    "diff": None, "patch": None, "makefile": None, "cmake": None,
    "dockerfile": None, "toml": None, "ini": None, "cfg": None,
}

# ── AI Pattern Detection ────────────────────────────────────────────

AI_VOCAB = [
    "delve into", "delve",
    "leverage", "leveraging", "leveraged",
    "tapestry", "tapestries",
    "realm", "realms",
    "crucial", "crucially",
    "pivotal",
    "showcase", "showcasing", "showcased",
    "robust", "robustness",
    "intricate", "intricacies", "intricately",
    "underscore", "underscores", "underscoring",
    "landscape", "landscapes",
    "paramount",
    "groundbreaking",
    "cutting-edge",
    "state-of-the-art",
    "interplay",
    "holistic", "holistically",
    "synergistic", "synergy",
    "paradigm",
    "transformative",
]

MECHANICAL_CONNECTORS = [
    "first and foremost",
    "it is worth noting that",
    "it should be noted that",
    "in light of the above",
    "taken together",
    "in a nutshell",
    "notably,",
    "last but not least",
    "it is important to note that",
    "needless to say",
    "without further ado",
]

HEDGING_STACKS = [
    "may potentially suggest",
    "could possibly indicate",
    "might perhaps be",
    "may possibly be",
    "could potentially be",
    "might potentially have",
    "could perhaps be argued",
    "it may be possible that",
]

FILLER_PHRASES = [
    "in order to",
    "due to the fact that",
    "at this point in time",
    "in the event that",
    "has the ability to",
    "it is important to note that",
    "with regard to",
    "in terms of",
    "as a matter of fact",
    "for the purpose of",
]

SIGNIFICANCE_INFLATION = [
    "marks a pivotal moment",
    "serves as a testament",
    "underscores its vital role",
    "sets the stage for",
    "represents a paradigm shift",
    "a turning point in",
    "reshaping the landscape",
    "at the forefront of",
    "leading the charge",
    "ushering in a new era",
]

BULLET_PATTERNS = re.compile(
    r'^\s*([-*+•·]|(\d+[\.\)]\s)|(\(?\d+\)\s)|([a-z][\.\)]\s)|([🚀✅💡🔑🎯⚡📊🎨🛠️📌])|(\*\*[^*]+\*\*:))'
)

# Parenthetical over-explanation pattern
PARENTHESIS_PATTERN = re.compile(r'\([^)]*\)')

# Academic parenthetical patterns to exclude from density (citations, refs, stats, math)
ACADEMIC_PAREN_PATTERNS = [
    re.compile(r'\(see\s+(Fig|Table|Section|Figure|Equation|Eq|Algorithm|Appendix|Chapter)\b', re.IGNORECASE),
    re.compile(r'\(\s*[§§]'),                                       # (§3.2)
    re.compile(r'\(cf\.'),                                          # (cf. ...)
    re.compile(r'\((e\.g|i\.e|etc|viz|vs)\.'),                      # (e.g., i.e., etc.)
    re.compile(r'\(p\s*[<>=]'),                                     # (p < 0.01)
    re.compile(r'\(n\s*='),                                         # (n = 100)
    re.compile(r'\(N\s*='),                                         # (N = 100)
    re.compile(r'\(\s*\d{4}\s*\)'),                                 # (2023)
    re.compile(r'\((Fig|Table|Eq|Equation|Algorithm|Theorem|Lemma|Corollary)\b', re.IGNORECASE),  # (Figure 2)
    re.compile(r'\([²³⁴⁵⁶⁷⁸⁹⁰¹]'),                                 # superscript references
    re.compile(r'\(where\s'),                                       # (where x ∈ R^n)
    re.compile(r'\([±]\s*\d+\.?\d*'),                               # (±0.5)
    re.compile(r'\(\d+%\)'),                                        # (95%)
    re.compile(r'\(\d+\.?\d*\s*[–-]\s*\d+\.?\d*\)'),               # (5–10)
]

def is_academic_paren(paren_text: str) -> bool:
    """Check if a parenthetical expression is legitimate academic notation."""
    for pattern in ACADEMIC_PAREN_PATTERNS:
        if pattern.search(paren_text):
            return True
    return False

# Bold-title opener for small-paragraph sub-total detection
BOLD_TITLE_OPENER = re.compile(r'^\s*\*\*[^*]+\*\*:\s')

# Common abbreviations ending with period (not sentence boundaries)
ABBREVIATIONS = re.compile(r'\b(' + '|'.join([
    'e\\.g', 'i\\.e', 'etc', 'vs', 'viz',
    'Dr', 'Mr', 'Ms', 'Mrs', 'Prof', 'St', 'Dept',
    'Fig', 'Table', 'Eq', 'Algo', 'Sec', 'Ch',
    'ed', 'vol', 'no', 'pp', 'et al',
    'al', 'cf', 'ca', 'approx',
]) + r')\\.', re.IGNORECASE)

TOTAL_SUB_TOTAL_OPENERS = [
    "there are several",
    "the following sections",
    "this paper makes",
    "the main contributions are",
    "this work presents",
    "we propose the following",
    "the key aspects are",
    "several factors contribute",
]

TOTAL_SUB_TOTAL_CLOSERS = [
    "in conclusion",
    "overall,",
    "in summary",
    "to summarize",
    "taken together",
    "in closing",
]

# ── Comment Extraction ──────────────────────────────────────────────

def extract_comments(code: str, lang_key: str) -> list[dict]:
    """Extract comments from code text using language-specific rules."""
    if lang_key not in LANGUAGES:
        return []

    name, line_cmt, block_open, block_close = LANGUAGES[lang_key]
    comments = []
    lines = code.split('\n')
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        # Block comments
        if block_open and stripped.startswith(block_open):
            # Multi-line block
            if block_close and block_close != block_open:
                block_lines = []
                start_line = i + 1
                j = i
                while j < len(lines):
                    block_lines.append(lines[j])
                    if block_close in lines[j] and not lines[j].strip().startswith(block_open):
                        break
                    j += 1
                text = '\n'.join(block_lines)
                # Strip delimiters
                text = re.sub(r'^\s*' + re.escape(block_open), '', text)
                text = re.sub(re.escape(block_close) + r'\s*$', '', text)
                text = text.strip()
                if text:
                    comments.append({"text": text, "line": start_line, "type": "block"})
                i = j + 1
                continue
            else:
                # Docstring-style or single-line block
                text = stripped
                for delim in [block_open, block_close] if block_close else [block_open]:
                    text = text.replace(delim, '', 1) if delim else text
                text = text.strip()
                if text:
                    comments.append({"text": text, "line": i + 1, "type": "block"})

        # Python triple-quote strings (docstrings)
        elif lang_key == "python" and ("'''" in stripped or stripped.startswith('"""')):
            delim = "'''" if "'''" in stripped else '"""'
            if stripped.count(delim) >= 2:
                # Single-line docstring
                text = stripped.split(delim)[1].strip()
                if text:
                    comments.append({"text": text, "line": i + 1, "type": "docstring"})
            else:
                # Multi-line docstring
                block_lines = []
                start_line = i + 1
                j = i
                while j < len(lines):
                    block_lines.append(lines[j])
                    if delim in lines[j] and j > i:
                        break
                    j += 1
                text = '\n'.join(block_lines)
                for _ in range(2):
                    text = text.replace(delim, '', 1)
                text = text.strip()
                if text:
                    comments.append({"text": text, "line": start_line, "type": "docstring"})
                i = j + 1
                continue

        # Line comments
        elif line_cmt:
            # Check if the line comment marker appears in a non-string context
            cmt_pos = _find_comment_pos(lines[i], line_cmt, lang_key)
            if cmt_pos is not None and cmt_pos >= 0:
                text = lines[i][cmt_pos + len(line_cmt):].strip()
                if text:
                    comments.append({"text": text, "line": i + 1, "type": "line"})

        i += 1

    return comments


def _find_comment_pos(line: str, marker: str, lang_key: str) -> Optional[int]:
    """Find comment marker position, avoiding string literals."""
    pos = line.find(marker)
    if pos == -1:
        return None

    # Simple heuristic: if marker is inside quotes, skip
    # Check if there's an odd number of quotes before pos
    in_string = False
    string_char = None
    i = 0
    while i < pos:
        if line[i] in ('"', "'"):
            if not in_string:
                in_string = True
                string_char = line[i]
            elif line[i] == string_char:
                in_string = False
        elif line[i] == '\\' and in_string:
            i += 1  # skip escaped char
        i += 1

    if in_string:
        # Try to find after the string
        after = line.find(marker, pos + 1)
        return after if after != -1 else None

    return pos


# ── Code Block Detection ─────────────────────────────────────────────

def find_code_blocks(text: str) -> list[dict]:
    """Find all code blocks (markdown fences + LaTeX environments)."""
    blocks = []

    # Markdown fenced code blocks: ```lang ... ```
    for m in re.finditer(r'```(\w*)\s*\n(.*?)```', text, re.DOTALL):
        lang = m.group(1).lower() if m.group(1) else None
        if lang in LANG_ALIASES:
            lang = LANG_ALIASES[lang]
        code = m.group(2)
        blocks.append({
            "type": "fenced",
            "language": lang,
            "code": code,
            "start": m.start(),
            "end": m.end(),
            "line": text[:m.start()].count('\n') + 1,
        })

    # LaTeX environments: lstlisting, minted, verbatim, algorithm
    latex_envs = [
        (r'\\begin\{lstlisting\}.*?\n(.*?)\\end\{lstlisting\}', "latex"),
        (r'\\begin\{minted\}\{(\w+)\}.*?\n(.*?)\\end\{minted\}', None),  # lang from arg
        (r'\\begin\{verbatim\}\s*\n(.*?)\\end\{verbatim\}', "latex"),
        (r'\\begin\{algorithm\}.*?\n(.*?)\\end\{algorithm\}', "latex"),
        (r'\\begin\{lstlisting\}.*?\[.*?language=(\w+).*?\].*?\n(.*?)\\end\{lstlisting\}', None),
    ]

    for pattern, default_lang in latex_envs:
        for m in re.finditer(pattern, text, re.DOTALL):
            groups = m.groups()
            if len(groups) == 2 and default_lang is None:
                lang, code = groups
            elif len(groups) == 1:
                lang = default_lang
                code = groups[0]
            else:
                continue
            if lang in LANG_ALIASES:
                lang = LANG_ALIASES[lang]
            blocks.append({
                "type": "latex_env",
                "language": lang,
                "code": code,
                "start": m.start(),
                "end": m.end(),
                "line": text[:m.start()].count('\n') + 1,
            })

    # Sort by position
    blocks.sort(key=lambda b: b["start"])
    return blocks


# ── Comment Classification ───────────────────────────────────────────

def classify_comment(comment_text: str) -> dict:
    """Classify a comment into Tier 1/2/3."""
    text_lower = comment_text.lower().strip()
    word_count = len(text_lower.split())

    # Detect bullet/numbering patterns in comments
    has_bullets = bool(BULLET_PATTERNS.match(comment_text.strip()))
    has_numbering = bool(re.match(r'^\s*(\d+[\.\)]\s|step\s*\d|phase\s*\d)', text_lower))

    # Detect AI vocabulary in comment
    ai_vocab_hits = [w for w in AI_VOCAB if w in text_lower]

    # Tier 3: Redundant — very short, narrates obvious code
    redundant_patterns = [
        r'^(increment|decrement|add|subtract|print|return|loop|iterate|set|get|initialize|assign)\b',
        r'^(the|this)\s+(function|method|class|variable|loop|array|list)\s',
        r'^(check|verify|validate)\s+(if|whether|that)\b',
        r'^#\s*(TODO|FIXME|HACK|NOTE|XXX)\b',  # keep standard tags
    ]
    
    is_redundant = False
    for pat in redundant_patterns:
        if re.match(pat, text_lower):
            is_redundant = True
            break

    if is_redundant and word_count <= 6:
        return {"tier": 3, "reason": "Redundant: narrates obvious code", "suggestion": None}

    # Tier 2: AI-flavored language or bullet-points
    if ai_vocab_hits:
        return {
            "tier": 2,
            "reason": f"AI vocabulary: {', '.join(ai_vocab_hits[:3])}",
            "suggestion": _suggest_rewrite(comment_text, ai_vocab_hits),
        }

    if has_bullets and word_count > 10:
        return {
            "tier": 2 if word_count > 8 else 3,
            "reason": "Bullet-point formatting in comment",
            "suggestion": "Condense to a single concise sentence" if word_count > 8 else None,
        }

    if has_numbering and word_count > 8:
        return {
            "tier": 2,
            "reason": "Numbered list formatting in comment",
            "suggestion": "Condense to a concise sentence without numbering",
        }

    if word_count > 25:
        return {
            "tier": 2,
            "reason": f"Overly verbose ({word_count} words)",
            "suggestion": "Shorten to ≤1 line explaining WHY, not WHAT",
        }

    # Tier 1: Concise, explains why
    quality_patterns = [
        r'(see|according to|per|following|based on|cites?|reference|cf\.|§)',
        r'(avoid|prevent|ensure|handle|because|since|due to)',
        r'(algorithm|theorem|lemma|equation|formula|section|figure|table)',
        r'(assume|assumption|note that|important:|warning:|edge case)',
    ]
    for pat in quality_patterns:
        if re.search(pat, text_lower):
            return {"tier": 1, "reason": "Concise why-comment", "suggestion": None}

    # Default: if short and not clearly redundant, keep
    if word_count <= 10:
        return {"tier": 1, "reason": "Concise (≤10 words)", "suggestion": None}

    return {"tier": 2, "reason": f"Moderate length ({word_count} words), unclear value", "suggestion": "Consider shortening or removing"}


def _suggest_rewrite(text: str, hits: list[str]) -> str:
    """Generate a simple rewrite suggestion by stripping AI vocab."""
    result = text
    replacements = {
        "delve into": "investigate",
        "delve": "explore",
        "leverage": "use",
        "leveraging": "using",
        "leveraged": "used",
        "tapestry": "context",
        "realm": "domain",
        "crucial": "key",
        "pivotal": "important",
        "showcase": "demonstrate",
        "robust": "reliable",
        "intricate": "complex",
        "underscore": "emphasize",
    }
    for old, new in replacements.items():
        if old in hits:
            result = re.sub(r'\b' + re.escape(old) + r'\b', new, result, flags=re.IGNORECASE)
    return result


# ── Prose Pattern Detection ──────────────────────────────────────────

def detect_prose_patterns(prose_lines: list[str], raw_text: str = None) -> dict:
    """Detect AI patterns in prose text.
    
    Args:
        prose_lines: Non-empty prose lines (blank lines stripped).
        raw_text: Original prose text with blank lines preserved (for paragraph-level detection).
    """
    text = '\n'.join(prose_lines)
    text_lower = text.lower()

    # Bullet density
    bullet_count = sum(1 for line in prose_lines if BULLET_PATTERNS.match(line))
    bullet_density = bullet_count / max(len(prose_lines), 1)

    # Total-sub-total structure
    openers_found = [o for o in TOTAL_SUB_TOTAL_OPENERS if o in text_lower]
    closers_found = [c for c in TOTAL_SUB_TOTAL_CLOSERS if c in text_lower]
    has_total_sub_total = len(openers_found) > 0 and len(closers_found) > 0

    # AI vocabulary
    ai_vocab_hits = sorted(set(w for w in AI_VOCAB if w in text_lower))
    mechanical_hits = sorted(set(w for w in MECHANICAL_CONNECTORS if w in text_lower))
    hedging_hits = sorted(set(w for w in HEDGING_STACKS if w in text_lower))
    filler_hits = sorted(set(w for w in FILLER_PHRASES if w in text_lower))
    inflation_hits = sorted(set(w for w in SIGNIFICANCE_INFLATION if w in text_lower))

    # Em-dash count
    em_dash_count = text.count('—')

    # Sentence length variance (with abbreviation-aware splitting)
    # Mask abbreviation periods so they don't trigger false sentence boundaries
    text_for_split = ABBREVIATIONS.sub(lambda m: m.group(0).replace('.', '\x00'), text)
    sentences = re.split(r'[.!?]+', text_for_split)
    # Restore masked characters for display
    sentences = [s.replace('\x00', '.') for s in sentences]
    sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
    if len(sentence_lengths) >= 3:
        avg_len = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((l - avg_len) ** 2 for l in sentence_lengths) / len(sentence_lengths)
    else:
        avg_len = sum(sentence_lengths) / max(len(sentence_lengths), 1)
        variance = 0

    # More than 2 Moreover/Furthermore/Additionally in proximity
    connector_count = sum(1 for c in ["moreover", "furthermore", "additionally"]
                          if c in text_lower)

    # Parenthesis density — over-explanation signal (excluding academic notation)
    parenthesis_matches = PARENTHESIS_PATTERN.findall(text)
    # Filter out academic/citation parentheses
    non_academic_parens = [m for m in parenthesis_matches if not is_academic_paren(m)]
    parenthesis_count = len(non_academic_parens)
    parenthesis_density = parenthesis_count / max(len(sentence_lengths), 1)

    # Bold-title + sub-total in small paragraphs (relative threshold)
    # Uses raw_text (with blank lines preserved) for accurate paragraph boundary detection
    para_text = raw_text or text
    total_word_count = len(para_text.split())
    if total_word_count >= 100:
        max_small_para_words = max(50, min(100, int(total_word_count * 0.1)))  # floor 50, cap 100
        bold_sub_total_paragraphs = 0
        paragraphs = re.split(r'\n\s*\n', para_text)
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_words = len(para.split())
            if para_words > max_small_para_words:
                continue  # only small paragraphs
            para_lines = para.split('\n')
            has_bold_opener = any(BOLD_TITLE_OPENER.match(l) for l in para_lines)
            if not has_bold_opener:
                continue
            # Check for sub-points or summary signals
            para_lower = para.lower()
            has_sub_total_openers = any(o in para_lower for o in TOTAL_SUB_TOTAL_OPENERS)
            has_sub_total_closers = any(c in para_lower for c in TOTAL_SUB_TOTAL_CLOSERS)
            has_bullets_inner = sum(1 for l in para_lines if BULLET_PATTERNS.match(l)) >= 2
            # Also flag if it has 3+ sentences (definition → details → summary structure)
            para_sentences = [s for s in re.split(r'[.!?]+', para) if s.strip()]
            has_multi_sentence = len(para_sentences) >= 3
            if has_sub_total_openers or has_sub_total_closers or has_bullets_inner or has_multi_sentence:
                bold_sub_total_paragraphs += 1
    else:
        bold_sub_total_paragraphs = 0

    # Word count for perplexity proxy
    words = text_lower.split()
    total_words = len(words)
    unique_words = len(set(words))
    
    return {
        "bullet_density": round(bullet_density, 3),
        "bullet_count": bullet_count,
        "total_lines": len(prose_lines),
        "total_words": total_words,
        "unique_words": unique_words,
        "has_total_sub_total": has_total_sub_total,
        "total_sub_total_signals": {"openers": openers_found, "closers": closers_found},
        "ai_vocab_hits": ai_vocab_hits,
        "mechanical_connectors": mechanical_hits,
        "hedging_stacks": hedging_hits,
        "filler_phrases": filler_hits,
        "significance_inflation": inflation_hits,
        "em_dash_count": em_dash_count,
        "avg_sentence_length": round(avg_len, 1),
        "sentence_length_variance": round(variance, 1),
        "connector_repetition": connector_count,
        "sentence_count": len(sentence_lengths),
        "parenthesis_count": parenthesis_count,
        "parenthesis_density": round(parenthesis_density, 2),
        "bold_sub_total_paragraphs": bold_sub_total_paragraphs,
    }


# ── Connector Logic Block Detection ───────────────────────────────────

# Sequential connector patterns that indicate AI-structured logical blocks.
# Each entry: (sequence_name, [ordered_markers])
CONNECTOR_SEQUENCES = [
    ("first-second-third", [
        r'\bfirst\b', r'\bsecond\b', r'\bthird\b', r'\b(fourth|fifth)\b',
        r'\b(finally|lastly|last)\b'
    ]),
    ("firstly-secondly-thirdly", [
        r'\bfirstly\b', r'\bsecondly\b', r'\bthirdly\b', r'\b(fourthly|fifthly)\b',
        r'\b(finally|lastly)\b'
    ]),
    ("to-begin-with-next-then-finally", [
        r'\bto begin with\b', r'\bnext\b', r'\bthen\b', r'\b(finally|lastly|last)\b'
    ]),
    ("one-another-a-third", [
        r'\bone\b', r'\banother\b', r'\ba third\b', r'\b(finally|lastly)\b'
    ]),
    ("initially-subsequently-ultimately", [
        r'\binitially\b', r'\bsubsequently\b', r'\bultimately\b'
    ]),
    ("the-first-the-second-the-third", [
        r'\bthe first\b', r'\bthe second\b', r'\bthe third\b', r'\bthe (fourth|fifth)\b',
        r'\b(finally|the last)\b'
    ]),
    ("first-next-then-finally", [
        r'\bfirst\b', r'\bnext\b', r'\bthen\b', r'\b(finally|last|lastly)\b'
    ]),
]


def detect_connector_blocks(prose_text: str) -> list[dict]:
    """Find logical blocks connected by sequential signposting markers.

    Returns list of blocks, each containing the full text span from the first
    marker to the last, the detected sequence type, and individual marker positions.
    """
    text_lower = prose_text.lower()
    blocks = []

    for seq_name, markers in CONNECTOR_SEQUENCES:
        # Find all occurrences of each marker
        found_positions = []
        for marker in markers:
            for m in re.finditer(marker, text_lower):
                found_positions.append({
                    "marker": m.group(),
                    "position": m.start(),
                    "end": m.end(),
                })

        if len(found_positions) < 2:
            continue  # Need at least 2 markers to form a meaningful block

        # Sort by position
        found_positions.sort(key=lambda x: x["position"])

        # Check if markers appear in the expected order and reasonable proximity
        # (within ~200 words of each other)
        ordered_markers = []
        last_end = -1
        for fp in found_positions:
            if fp["position"] > last_end:
                # Check word distance from previous marker
                if ordered_markers:
                    prev_end = ordered_markers[-1]["end"]
                    between_text = prose_text[prev_end:fp["position"]]
                    word_count = len(between_text.split())
                    if word_count > 200:
                        break  # Too far apart — different logical block
                ordered_markers.append(fp)
                last_end = fp["end"]

        if len(ordered_markers) < 2:
            continue

        # Extract the full block: from first marker to ~50 words after last marker
        block_start = ordered_markers[0]["position"]
        last_end = ordered_markers[-1]["end"]

        # Extend to end of paragraph/sentence after last marker
        after_text = prose_text[last_end:]
        # Find the next paragraph break or ~100 words
        end_candidates = []
        for sep in ['\n\n', '\n##', '\n# ']:
            idx = after_text.find(sep)
            if idx != -1:
                end_candidates.append(idx)
        # Also consider ~100 words
        words_after = after_text.split()
        if len(words_after) > 0:
            word_limit = min(100, len(words_after))
            word_limit_pos = len(' '.join(words_after[:word_limit]))
            end_candidates.append(word_limit_pos)

        extend_by = min(end_candidates) if end_candidates else min(500, len(after_text))

        block_end = last_end + extend_by
        block_text = prose_text[block_start:block_end].strip()

        # Find the start of the sentence containing the first marker (go back to period or paragraph start)
        before_text = prose_text[:block_start]
        sentence_starts = []
        for sep in ['\n\n', '\n##', '\n# ']:
            idx = before_text.rfind(sep)
            if idx != -1:
                sentence_starts.append(idx + len(sep))
        # Also find last period
        last_period = before_text.rfind('. ')
        if last_period != -1:
            sentence_starts.append(last_period + 2)

        if sentence_starts:
            block_start = max(sentence_starts)

        block_text = prose_text[block_start:block_end].strip()

        blocks.append({
            "sequence_type": seq_name,
            "markers_found": [m["marker"] for m in ordered_markers],
            "marker_count": len(ordered_markers),
            "block_text": block_text,
            "char_start": block_start,
            "char_end": block_end,
        })

    # Sort by position, deduplicate overlapping blocks
    blocks.sort(key=lambda b: b["char_start"])
    deduped = []
    for b in blocks:
        if deduped and b["char_start"] < deduped[-1]["char_end"]:
            # Overlapping — keep the one with more markers
            if b["marker_count"] > deduped[-1]["marker_count"]:
                deduped[-1] = b
        else:
            deduped.append(b)

    return deduped


# ── GenAI Risk Classification ──────────────────────────────────────────

def classify_genai_risk(prose_result: dict) -> dict:
    """Classify prose into GenAI detection risk tiers based on perplexity
    and burstiness proxies.

    Returns: {
        "risk_tier": "high" | "moderate" | "low",
        "score": int,
        "breakdown": {...}
    }
    """
    score = 0
    breakdown = {}

    # ── Perplexity Proxy: AI vocabulary density ──
    total_words = max(prose_result.get("total_words", 1), 1)
    ai_vocab_count = len(prose_result.get("ai_vocab_hits", []))
    ai_density = ai_vocab_count / total_words
    breakdown["ai_vocab_density"] = round(ai_density, 4)
    if ai_density > 0.05:
        score += 3
        breakdown["ai_vocab_verdict"] = "high (>5% of words are AI vocabulary)"
    elif ai_density > 0.02:
        score += 1
        breakdown["ai_vocab_verdict"] = "moderate (2-5%)"
    else:
        breakdown["ai_vocab_verdict"] = "low (<2%)"

    # ── Perplexity Proxy: Mechanical connector density ──
    mech_count = len(prose_result.get("mechanical_connectors", []))
    mech_density = mech_count / total_words
    breakdown["mechanical_density"] = round(mech_density, 4)
    if mech_density > 0.02:
        score += 2
        breakdown["mechanical_verdict"] = "high"
    elif mech_density > 0.005:
        score += 1
        breakdown["mechanical_verdict"] = "moderate"
    else:
        breakdown["mechanical_verdict"] = "low"

    # ── Perplexity Proxy: Vocabulary diversity (unique/total ratio) ──
    unique_words = prose_result.get("unique_words", 0)
    vocab_diversity = unique_words / total_words if total_words > 0 else 0
    breakdown["vocab_diversity"] = round(vocab_diversity, 3)
    if vocab_diversity < 0.4 and total_words > 50:
        score += 2
        breakdown["vocab_diversity_verdict"] = "low (<40% unique — predictable word choice)"
    elif vocab_diversity < 0.55 and total_words > 50:
        score += 1
        breakdown["vocab_diversity_verdict"] = "moderate (40-55%)"
    else:
        breakdown["vocab_diversity_verdict"] = "high (>55% — varied vocabulary)"

    # ── Burstiness Proxy: Sentence length variance ──
    variance = prose_result.get("sentence_length_variance", 999)
    sentence_count = prose_result.get("sentence_count", 0)
    breakdown["sentence_length_variance"] = variance
    if variance < 3.0 and sentence_count > 5:
        score += 3
        breakdown["burstiness_verdict"] = "very low (variance <3, >5 sentences — highly uniform)"
    elif variance < 5.0 and sentence_count > 3:
        score += 1
        breakdown["burstiness_verdict"] = "low (variance 3-5)"
    else:
        breakdown["burstiness_verdict"] = "adequate (variance >5 — varied rhythm)"

    # ── Burstiness Proxy: Bullet density ──
    bullet_density = prose_result.get("bullet_density", 0)
    breakdown["bullet_density"] = bullet_density
    if bullet_density > 0.3:
        score += 2
        breakdown["bullet_verdict"] = "high (>30% of lines are bullets)"
    elif bullet_density > 0.15:
        score += 1
        breakdown["bullet_verdict"] = "moderate (15-30%)"
    else:
        breakdown["bullet_verdict"] = "low (<15%)"

    # ── Hedge stack density ──
    hedge_count = len(prose_result.get("hedging_stacks", []))
    hedge_density = hedge_count / max(sentence_count, 1)
    breakdown["hedge_density"] = round(hedge_density, 3)
    if hedge_density > 0.3:
        score += 1
        breakdown["hedge_verdict"] = "high"
    else:
        breakdown["hedge_verdict"] = "acceptable"

    # ── Filler density ──
    filler_count = len(prose_result.get("filler_phrases", []))
    filler_density = filler_count / max(sentence_count, 1)
    breakdown["filler_density"] = round(filler_density, 3)
    if filler_density > 0.3:
        score += 1
        breakdown["filler_verdict"] = "high"
    else:
        breakdown["filler_verdict"] = "acceptable"

    # ── Significance inflation ──
    inflation_count = len(prose_result.get("significance_inflation", []))
    if inflation_count > 0:
        score += 1
        breakdown["inflation_count"] = inflation_count
    else:
        breakdown["inflation_count"] = 0

    # ── Perplexity Proxy: Parenthesis density (over-explanation) ──
    parenthesis_density = prose_result.get("parenthesis_density", 0)
    breakdown["parenthesis_density"] = parenthesis_density
    if parenthesis_density > 1.5:
        score += 2
        breakdown["parenthesis_verdict"] = "high (>1.5 parentheses per sentence — over-explanation)"
    elif parenthesis_density > 0.8:
        score += 1
        breakdown["parenthesis_verdict"] = "moderate (0.8-1.5 per sentence)"
    else:
        breakdown["parenthesis_verdict"] = "low (<0.8 per sentence)"

    # ── Structural: Bold-header + sub-total in small paragraphs ──
    bold_sub_total_count = prose_result.get("bold_sub_total_paragraphs", 0)
    breakdown["bold_sub_total_paragraphs"] = bold_sub_total_count
    if bold_sub_total_count >= 2:
        score += 1
        breakdown["bold_sub_total_verdict"] = (
            f"present ({bold_sub_total_count} paragraphs with bold-header + sub-total pattern)"
        )
    else:
        breakdown["bold_sub_total_verdict"] = "absent"

    # ── Final classification ──
    if score >= 5:
        tier = "high"
        tier_cn = "High GenAI risk — forced rewrite recommended"
    elif score >= 1:
        tier = "moderate"
        tier_cn = "Moderate GenAI risk — warn the user"
    else:
        tier = "low"
        tier_cn = "Low GenAI risk — no action needed"

    return {
        "risk_tier": tier,
        "risk_tier_cn": tier_cn,
        "score": score,
        "max_score": 19,
        "breakdown": breakdown,
    }


# ── Main ──────────────────────────────────────────────────────────────

def main():
    # Read input
    if len(sys.argv) >= 2 and sys.argv[1] not in ("--json", "-j"):
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(json.dumps({"error": f"File not found: {filepath}"}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    if not text.strip():
        print(json.dumps({"error": "No input provided"}, ensure_ascii=False))
        sys.exit(1)

    # Find code blocks
    code_blocks = find_code_blocks(text)

    # Extract prose (text outside code blocks)
    prose_parts = []
    last_end = 0
    for block in code_blocks:
        prose_parts.append(text[last_end:block["start"]])
        last_end = block["end"]
    prose_parts.append(text[last_end:])
    prose_text = '\n'.join(prose_parts)

    prose_lines = [l for l in prose_text.split('\n') if l.strip()]

    # Analyze prose (pass raw_text for paragraph-level detection)
    prose_result = detect_prose_patterns(prose_lines, raw_text=prose_text)

    # Detect connector logic blocks in prose
    connector_blocks = detect_connector_blocks(prose_text)

    # Classify GenAI risk tier for prose
    genai_risk = classify_genai_risk(prose_result)

    # Extract and classify comments from each code block
    code_results = []
    for block in code_blocks:
        lang = block["language"]
        if lang not in LANGUAGES:
            continue

        comments = extract_comments(block["code"], lang)
        classified = []
        for c in comments:
            result = classify_comment(c["text"])
            classified.append({
                "text": c["text"],
                "line_in_block": c["line"],
                "type": c["type"],
                "tier": result["tier"],
                "reason": result["reason"],
                "suggestion": result.get("suggestion"),
            })

        if classified:
            code_results.append({
                "language": LANGUAGES[lang][0],
                "block_start_line": block["line"],
                "comment_count": len(classified),
                "comments": classified,
            })

    # Build output
    output = {
        "prose": prose_result,
        "connector_blocks": connector_blocks,
        "genai_risk": genai_risk,
        "code_blocks": code_results,
        "summary": {
            "total_ai_vocab": len(prose_result["ai_vocab_hits"]),
            "total_mechanical": len(prose_result["mechanical_connectors"]),
            "total_hedging": len(prose_result["hedging_stacks"]),
            "total_filler": len(prose_result["filler_phrases"]),
            "total_inflation": len(prose_result["significance_inflation"]),
            "em_dash_count": prose_result["em_dash_count"],
            "bullet_density": prose_result["bullet_density"],
            "has_total_sub_total": prose_result["has_total_sub_total"],
            "connector_blocks_count": len(connector_blocks),
            "parenthesis_density": prose_result["parenthesis_density"],
            "bold_sub_total_paragraphs": prose_result["bold_sub_total_paragraphs"],
            "genai_risk_tier": genai_risk["risk_tier"],
            "genai_risk_score": genai_risk["score"],
            "total_comments_tier2": sum(
                1 for cb in code_results for c in cb["comments"] if c["tier"] == 2
            ),
            "total_comments_tier3": sum(
                1 for cb in code_results for c in cb["comments"] if c["tier"] == 3
            ),
            "total_code_blocks": len(code_results),
        },
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
