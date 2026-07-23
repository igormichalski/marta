from caixa import para_snake_case

# Suíte inicial fraca: cobre apenas a entrada vazia.

def test_caixa_vazio():
    assert para_snake_case("") == ""
