from hg_cognition.embeddings.hashing import hash_embed, cosine_distance

def test_hash_embed_deterministic():
    a = hash_embed("hello world", dim=64)
    b = hash_embed("hello world", dim=64)
    assert a == b

def test_cosine_distance_bounds():
    a = hash_embed("a", dim=64)
    b = hash_embed("b", dim=64)
    d = cosine_distance(a, b)
    assert 0.0 <= d <= 2.0
