"""Experimento de ablação: RAG ligado vs. desligado em todas as funções-alvo.

Para cada alvo e cada condição, restaura a suíte inicial fraca, executa o laço
completo do framework e registra as métricas em resultados/consolidado.csv.

O arquivo é salvo de forma incremental (após cada execução) e o experimento é
retomável: combinações (alvo, condição) já presentes no CSV são puladas. Se o
provedor de LLM atingir um limite de taxa, o experimento para de forma limpa,
preservando o que já foi coletado, e pode ser retomado depois.

Uso:
    python experimentos.py            # roda todos os alvos, ambas as condições
    python experimentos.py luhn cpf   # roda apenas os alvos indicados
"""

import csv
import os
import sys

from marta import framework

RAIZ = os.path.dirname(os.path.abspath(__file__))
ALVOS = os.path.join(RAIZ, "alvos")
SAIDA = os.path.join(RAIZ, "resultados")
CSV = os.path.join(SAIDA, "consolidado.csv")
CAMPOS = ["alvo", "rag", "modulo", "total", "mortos", "sobreviventes", "score", "tentativas", "tempo_s"]


def descobrir_alvos(filtro):
    alvos = []
    for nome in sorted(os.listdir(ALVOS)):
        caminho = os.path.join(ALVOS, nome)
        if not os.path.isdir(caminho) or not os.path.exists(os.path.join(caminho, "config.toml")):
            continue
        if filtro and nome not in filtro:
            continue
        alvos.append((nome, caminho))
    return alvos


def carregar_existentes():
    linhas, feitos = [], set()
    if os.path.exists(CSV):
        with open(CSV) as f:
            for linha in csv.DictReader(f):
                linhas.append(linha)
                feitos.add((linha["alvo"], str(linha["rag"])))
    return linhas, feitos


def salvar(linhas):
    with open(CSV, "w", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({c: linha.get(c) for c in CAMPOS})


def e_limite_de_taxa(erro):
    msg = str(erro).lower()
    return "rate" in msg or "429" in msg or "tpd" in msg or "per day" in msg


def main():
    filtro = set(sys.argv[1:])
    os.makedirs(SAIDA, exist_ok=True)
    linhas, feitos = carregar_existentes()

    for nome, diretorio in descobrir_alvos(filtro):
        os.chdir(diretorio)
        cfg_base = framework.carregar_config("config.toml")
        test_file = cfg_base["test_file"]
        with open(test_file) as f:
            original = f.read()

        for usar_rag in (True, False):
            if (nome, str(usar_rag)) in feitos:
                print(f"[pulando] {nome} — RAG {'ON' if usar_rag else 'OFF'} (já consta no CSV)")
                continue
            with open(test_file, "w") as f:  # suíte pristina antes de cada condição
                f.write(original)
            print(f"\n########## {nome} — RAG {'ON' if usar_rag else 'OFF'} ##########")
            cfg = framework.carregar_config("config.toml")
            cfg["rag"] = usar_rag
            try:
                metricas = framework.comando_run(cfg, log_path=None)
            except Exception as erro:
                with open(test_file, "w") as f:
                    f.write(original)
                if e_limite_de_taxa(erro):
                    os.chdir(RAIZ)
                    salvar(linhas)
                    print(f"\n[limite de taxa atingido] Dados parciais salvos em {CSV}.")
                    print("Aguarde o reset da cota diária e rode novamente para retomar.")
                    return
                raise
            metricas["alvo"] = nome
            linhas.append(metricas)
            feitos.add((nome, str(usar_rag)))
            with open(test_file, "w") as f:  # restaura para não contaminar a próxima
                f.write(original)
            os.chdir(RAIZ)
            salvar(linhas)  # incremental: nunca perde o que já foi coletado
            os.chdir(diretorio)

        os.chdir(RAIZ)

    salvar(linhas)
    print(f"\nConsolidado salvo em {CSV}")


if __name__ == "__main__":
    main()
