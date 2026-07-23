"""Consolida resultados/consolidado.csv em uma tabela LaTeX e um gráfico.

Gera:
    resultados/score_por_alvo.png     comparação do mutation score (RAG on/off)
    resultados/tabela_resultados.tex  tabela pronta para o capítulo de Resultados
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(RAIZ, "resultados")
CSV = os.path.join(SAIDA, "consolidado.csv")


def _num(v):
    return float(v) if v not in (None, "") else 0.0


def carregar():
    dados = {}
    with open(CSV) as f:
        for linha in csv.DictReader(f):
            alvo = linha["alvo"]
            usa_rag = str(linha["rag"]).strip().lower() in ("true", "1")
            dados.setdefault(alvo, {})[usa_rag] = linha
    return dados


def virgula(x, casas=1):
    return f"{x:.{casas}f}".replace(".", ",")


def gerar_tabela(dados):
    linhas = []
    for alvo in sorted(dados):
        com = dados[alvo].get(True, {})
        sem = dados[alvo].get(False, {})
        linhas.append(
            f"{alvo} & {sem.get('total','-')} & "
            f"{virgula(_num(sem.get('score')))} & {virgula(_num(com.get('score')))} & "
            f"{com.get('mortos','-')} & {com.get('sobreviventes','-')} \\\\"
        )
    corpo = "\n".join(linhas)
    tex = (
        "\\begin{table}[htb]\n\\centering\n"
        "\\caption{Mutation score por fun\\c{c}\\~ao-alvo, com e sem RAG, e mutantes tratados pelo framework.}\n"
        "\\label{tab:resultados-framework}\n"
        "\\begin{tabular}{lccccc}\n\\toprule\n"
        "\\textbf{Alvo} & \\textbf{Mutantes} & \\textbf{Score sem RAG (\\%)} & "
        "\\textbf{Score com RAG (\\%)} & \\textbf{Mortos} & \\textbf{Sobrev.} \\\\\n"
        "\\midrule\n" + corpo + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n"
    )
    with open(os.path.join(SAIDA, "tabela_resultados.tex"), "w") as f:
        f.write(tex)


def gerar_grafico(dados):
    alvos = sorted(dados)
    com = [_num(dados[a].get(True, {}).get("score")) for a in alvos]
    sem = [_num(dados[a].get(False, {}).get("score")) for a in alvos]
    x = range(len(alvos))
    largura = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar([i - largura / 2 for i in x], sem, largura, label="Sem RAG", color="#9aa7b4")
    ax.bar([i + largura / 2 for i in x], com, largura, label="Com RAG", color="#2f6f9f")
    ax.set_ylabel("Mutation score (%)")
    ax.set_ylim(0, 100)
    ax.set_xticks(list(x))
    ax.set_xticklabels(alvos, rotation=30, ha="right")
    ax.legend()
    ax.set_title("Mutation score por funcao-alvo: com e sem RAG")
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "score_por_alvo.png"), dpi=150)


def resumo(dados):
    com = [_num(dados[a].get(True, {}).get("score")) for a in dados]
    sem = [_num(dados[a].get(False, {}).get("score")) for a in dados]
    print(f"Alvos: {len(dados)}")
    print(f"Score medio sem RAG: {sum(sem)/len(sem):.1f}%")
    print(f"Score medio com RAG: {sum(com)/len(com):.1f}%")


def main():
    dados = carregar()
    gerar_tabela(dados)
    gerar_grafico(dados)
    resumo(dados)
    print("Gerados: resultados/tabela_resultados.tex e resultados/score_por_alvo.png")


if __name__ == "__main__":
    main()
