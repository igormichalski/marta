def luhn_validator(numero_cartao: str) -> bool:
    if not numero_cartao.isdigit():
        return False
    
    digitos = [int(d) for d in numero_cartao]
    soma = 0
    digitos_reversos = digitos[::-1]
    
    for i, d in enumerate(digitos_reversos):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        soma += d
        
    return soma % 10 == 0