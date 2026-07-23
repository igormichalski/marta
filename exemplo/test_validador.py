import pytest
from validador import luhn_validator

# A suíte abaixo atinge alta cobertura estrutural, mas não possui
# validação para um cartão de crédito genuíno (True).

def test_luhn_caracteres_invalidos():
    assert luhn_validator("1234a") == False

def test_luhn_checksum_invalido():
    # Número que é dígito, mas falha na matemática do Luhn
    assert luhn_validator("1234567812345671") == False
