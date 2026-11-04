import re

# Deliberately limited patterns; callers should minimize sensitive input at source.
PATTERNS = [
    re.compile(r'(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+'),
    re.compile(r'(?i)((?:password|passwd|api[_-]?key|access[_-]?token|secret|token)\s*[=:]\s*[\"\']?)[^\s,;\"\']+'),
    re.compile(r'\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{10,})\b'),
]


def redact(value: str) -> str:
    for pattern in PATTERNS:
        value = pattern.sub(lambda m: (m.group(1) if m.lastindex else '') + '[REDACTED]', value)
    return value
