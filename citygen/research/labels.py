# Label definitions for SZZ ground truth

FIX_PATTERNS = [
    r"\bfix(e[sd])?\b", r"\bbug\b", r"\bdefect\b", r"\bissue #?\d+\b",
    r"\bcloses? #\d+\b", r"\bresolves? #\d+\b", r"\bhotfix\b", r"\bregression\b",
]

REVERT_PATTERN = r'^Revert "'

BULK_COMMIT_THRESHOLD = 100
