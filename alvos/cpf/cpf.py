def validar_cpf(cpf: str) -> bool:
    """Valida um CPF (identificador fiscal nacional) pelos dígitos verificadores."""
    if not cpf.isdigit() or len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        d = (soma * 10) % 11
        if d == 10:
            d = 0
        if d != int(cpf[i]):
            return False
    return True
