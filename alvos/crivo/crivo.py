def crivo_eratostenes(n: int) -> list:
    """Retorna a lista de números primos menores ou iguais a n."""
    if n < 2:
        return []
    e = [True] * (n + 1)
    e[0] = e[1] = False
    p = 2
    while p * p <= n:
        if e[p]:
            for m in range(p * p, n + 1, p):
                e[m] = False
        p += 1
    return [i for i in range(2, n + 1) if e[i]]
