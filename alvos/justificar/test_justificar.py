from justificar import justificar

# Suíte inicial fraca: cobre apenas o caso de uma única palavra.

def test_justificar_uma_palavra():
    assert justificar("oi", 5) == "oi   "
