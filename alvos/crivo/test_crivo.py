from crivo import crivo_eratostenes

# Suíte inicial fraca: cobre apenas o caso de contorno n < 2.

def test_crivo_vazio():
    assert crivo_eratostenes(1) == []
