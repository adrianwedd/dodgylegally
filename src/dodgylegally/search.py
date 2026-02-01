import random
from importlib.resources import files


def load_wordlist(path: str | None = None) -> list[str]:
    """Load word list from file path, or bundled default."""
    if path is None:
        resource = files("dodgylegally").joinpath("wordlist.txt")
        text = resource.read_text()
    else:
        with open(path) as f:
            text = f.read()
    return [line.strip() for line in text.splitlines() if line.strip()]


def generate_phrases(word_list: list[str], count: int) -> list[str]:
    """Return count random 2-word phrases."""
    if len(word_list) < 2:
        raise ValueError(f"Word list must contain at least 2 words, got {len(word_list)}.")
    phrases = []
    for _ in range(count):
        words = random.sample(word_list, 2)
        phrases.append(" ".join(words))
    return phrases
