import re
from itertools import pairwise

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


def word_ngrams(text: str) -> list[str]:
    tokens = tokenize(text)
    return tokens + [f"{left}_{right}" for left, right in pairwise(tokens)]


def normalized_text(text: str) -> str:
    return " ".join(text.split())
