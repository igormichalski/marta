from luhn import luhn_validator

# Suíte inicial fraca: apenas casos negativos, sem validar um cartão genuíno.

def test_luhn_caracteres_invalidos():
    assert luhn_validator("1234a") == False

def test_luhn_checksum_invalido():
    assert luhn_validator("1234567812345671") == False
