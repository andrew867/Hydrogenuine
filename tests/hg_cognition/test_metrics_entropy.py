from hg_cognition.metrics.basic import shannon_entropy, clamp01
from hg_cognition.metrics.diversity import average_pairwise_distance, latent_collapse_risk

def test_entropy_uniform_high():
    e = shannon_entropy([0.25,0.25,0.25,0.25])
    assert e > 0.9

def test_entropy_peaked_low():
    e = shannon_entropy([0.97,0.01,0.01,0.01])
    assert e < 0.3

def test_clamp01():
    assert clamp01(0.5) == 0.5
    assert clamp01(-0.1) == 0.0
    assert clamp01(1.5) == 1.0

def test_average_pairwise_distance():
    from hg_cognition.embeddings.hashing import hash_embed
    v1 = hash_embed("a", dim=64)
    v2 = hash_embed("b", dim=64)
    v3 = hash_embed("c", dim=64)
    d = average_pairwise_distance([v1, v2, v3])
    assert 0.0 <= d <= 2.0
    assert average_pairwise_distance([v1]) == 0.0

def test_latent_collapse_risk():
    from hg_cognition.embeddings.hashing import hash_embed
    vs = [hash_embed("x", dim=64), hash_embed("y", dim=64)]
    baseline = 0.5
    r = latent_collapse_risk(vs, baseline)
    assert 0.0 <= r <= 1.0
    assert latent_collapse_risk(vs, 0.0) == 0.0
