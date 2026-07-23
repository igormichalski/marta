def justificar(texto: str, largura: int) -> str:
    """Justifica um texto de linha única para a largura dada, distribuindo espaços."""
    palavras = texto.split()
    if largura <= 0:
        return texto
    if len(palavras) <= 1:
        return texto.ljust(largura)
    total = sum(len(p) for p in palavras)
    espacos = largura - total
    if espacos <= 0:
        return " ".join(palavras)
    lacunas = len(palavras) - 1
    base = espacos // lacunas
    extra = espacos % lacunas
    resultado = ""
    for i, p in enumerate(palavras[:-1]):
        resultado += p + " " * (base + (1 if i < extra else 0))
    return resultado + palavras[-1]
