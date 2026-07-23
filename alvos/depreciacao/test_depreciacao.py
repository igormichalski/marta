from depreciacao import depreciacao_linear

# Suíte inicial fraca: cobre apenas o valor no ano zero.

def test_depreciacao_ano_zero():
    assert depreciacao_linear(1000.0, 100.0, 5, 0) == 1000.0
