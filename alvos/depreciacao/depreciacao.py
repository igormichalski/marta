def depreciacao_linear(valor: float, residual: float, vida_util: int, ano: int) -> float:
    """Calcula o valor contábil de um ativo após 'ano' anos de depreciação linear."""
    if vida_util <= 0:
        raise ValueError("vida util deve ser positiva")
    if ano < 0 or ano > vida_util:
        raise ValueError("ano fora do intervalo")
    if residual < 0 or residual > valor:
        raise ValueError("valor residual invalido")
    depreciavel = valor - residual
    return round(valor - (depreciavel / vida_util) * ano, 2)
