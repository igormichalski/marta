def para_snake_case(texto: str) -> str:
    """Converte um texto para snake_case."""
    resultado = []
    for i, c in enumerate(texto):
        if c == " " or c == "-":
            resultado.append("_")
        elif c.isupper():
            if i > 0 and texto[i - 1] not in (" ", "-"):
                resultado.append("_")
            resultado.append(c.lower())
        else:
            resultado.append(c)
    return "".join(resultado)
