def truncar_sentenca(texto: str, limite: int) -> str:
    """Trunca o texto no limite de caracteres, preservando palavras inteiras."""
    if limite <= 0:
        return ""
    if len(texto) <= limite:
        return texto
    cortado = texto[:limite]
    if " " in cortado:
        cortado = cortado[:cortado.rfind(" ")]
    return cortado + "..."
