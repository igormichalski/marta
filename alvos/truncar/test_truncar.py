from truncar import truncar_sentenca

# Suíte inicial fraca: cobre apenas o caso em que o texto já cabe no limite.

def test_truncar_texto_curto():
    assert truncar_sentenca("oi", 10) == "oi"
