import re
from config.settings import STRICT_ROLE_MATCH
from config.keywords import INTERN_KEYWORDS, ROLE_KEYWORDS

# Precompile internship keywords with word boundaries
_INTERN_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in INTERN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Separate single-word and multi-word role keywords
_SINGLE_WORD_ROLES = [k for k in ROLE_KEYWORDS if len(k.split()) == 1]
_MULTI_WORD_ROLES = [k.lower() for k in ROLE_KEYWORDS if len(k.split()) > 1]

# Precompile single-word role pattern with word boundaries to avoid false positives (e.g., 'it', 'qa')
_SINGLE_WORD_ROLE_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _SINGLE_WORD_ROLES) + r")\b",
    re.IGNORECASE,
)


def matches_internship(job_title: str) -> bool:
    """
    Check if a job title contains internship-related keywords.
    Uses word-boundary matching to avoid false positives like 'internal', 'international'.
    """
    if not job_title:
        return False
    return bool(_INTERN_PATTERN.search(job_title))


def matches_role(job_title: str) -> bool:
    """
    Check if a job title matches any of the target tech/DS roles.
    Uses word-boundary matching for single-word keywords, substring for phrases.
    """
    if not job_title:
        return False
    
    # 1. Fast check single-word roles via precompiled regex
    if _SINGLE_WORD_ROLE_PATTERN.search(job_title):
        return True
    
    # 2. Check multi-word phrases via substring search
    title_lower = job_title.lower()
    return any(phrase in title_lower for phrase in _MULTI_WORD_ROLES)


def is_relevant_job(job_title: str, strict: bool = STRICT_ROLE_MATCH) -> bool:
    """
    Determine if a job posting is relevant.
    If strict is True: must match BOTH intern keyword AND role keyword.
    If False: only needs to match an intern keyword.
    """
    if not matches_internship(job_title):
        return False
    if strict:
        return matches_role(job_title)
    return True
