from cpf import validar_cpf

# Suíte inicial fraca: cobre apenas um caso de tamanho inválido.

def test_cpf_tamanho_invalido():
    assert validar_cpf("123") == False
