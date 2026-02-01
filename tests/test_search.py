from dodgylegally.search import load_wordlist, generate_phrases


def test_load_default_wordlist():
    words = load_wordlist()
    assert isinstance(words, list)
    assert len(words) > 0
    assert all(isinstance(w, str) for w in words)


def test_load_custom_wordlist(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    words = load_wordlist(str(f))
    assert words == ["alpha", "beta", "gamma"]


def test_generate_phrases():
    words = ["alpha", "beta", "gamma", "delta"]
    phrases = generate_phrases(words, 3)
    assert len(phrases) == 3
    for phrase in phrases:
        parts = phrase.split()
        assert len(parts) == 2
        assert all(p in words for p in parts)


def test_generate_phrases_empty_count():
    words = ["alpha", "beta"]
    phrases = generate_phrases(words, 0)
    assert phrases == []
