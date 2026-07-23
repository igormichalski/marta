"""Suíte-base (fraca) usada como ponto de partida do experimento de
sensibilidade do limite de tentativas. Contém apenas casos de erro, deixando
muitos mutantes do "caminho feliz" vivos para o framework tentar matar."""

from validador import luhn_validator


def test_luhn_caracteres_invalidos():
    assert luhn_validator("1234a") == False


def test_luhn_checksum_invalido():
    assert luhn_validator("1234567812345671") == False
