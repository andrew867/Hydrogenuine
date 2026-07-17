from hg_cognition.emotion.valence_arousal import extract_valence_arousal
from hg_cognition.emotion.mapping import emotion_to_quad

def test_valence_positive():
    va = extract_valence_arousal("I feel good and happy and calm")
    assert va.valence > 0
    assert 0 <= va.arousal <= 1

def test_valence_negative():
    va = extract_valence_arousal("This is awful and I am angry")
    assert va.valence < 0
    assert va.arousal >= 0.5

def test_emotion_to_quad_strength():
    va = extract_valence_arousal("good calm")
    q = emotion_to_quad(va)
    assert 0 <= q.strength <= 1
