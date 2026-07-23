"""
Experimento de análise de sensibilidade do LIMITE DE TENTATIVAS do framework.

Objetivo: gerar a curva de convergência (mutantes sobreviventes x número de
tentativas) para fundamentar empiricamente a escolha do limite. Como o LLM é
estocástico (temperatura > 0), o experimento repete a execução várias vezes,
sempre partindo da mesma suíte-base, e agrega a média por tentativa.

O resultado mostra a partir de qual tentativa os ganhos saturam (retornos
decrescentes), respondendo: "a 6ª tentativa ainda mataria mutantes?" e
"quantas das tentativas são, de fato, úteis?".

Pré-requisito: a chave de API definida na variável de ambiente (ver README).

Uso:
    python experimento_tentativas.py --baseline test_validador_base.py \
        --repeticoes 10 --max-attempts 12
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys

import toml


def test_file_da_config(config):
    return toml.load(config).get("framework", {}).get("test-file", "test_validador.py")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="cosmic-ray.toml")
    ap.add_argument("--baseline", required=True,
                    help="suíte-base restaurada antes de cada repetição")
    ap.add_argument("--repeticoes", type=int, default=10)
    ap.add_argument("--max-attempts", type=int, default=12,
                    help="orçamento alto, para enxergar a curva inteira até saturar")
    ap.add_argument("--saida", default="convergencia.csv")
    args = ap.parse_args()

    test_file = test_file_da_config(args.config)
    if not os.path.exists(args.baseline):
        sys.exit(f"[erro] baseline não encontrada: {args.baseline}")

    # Preserva o estado atual do arquivo de testes para restaurar no fim.
    backup_atual = test_file + ".exp.bak"
    if os.path.exists(test_file):
        shutil.copy(test_file, backup_atual)

    series = []  # uma lista de sobreviventes-por-tentativa para cada repetição
    try:
        for rep in range(args.repeticoes):
            print(f"\n===== Repetição {rep + 1}/{args.repeticoes} =====")
            shutil.copy(args.baseline, test_file)
            log = f".rep_{rep}.csv"
            subprocess.run(
                [sys.executable, "framework.py", "run", args.config,
                 "--log", log, "--max-attempts", str(args.max_attempts)],
                check=False,
            )
            serie = {}
            if os.path.exists(log):
                with open(log) as f:
                    for row in csv.DictReader(f):
                        serie[int(row["tentativa"])] = int(row["sobreviventes"])
                os.remove(log)
            if serie:
                series.append(serie)
    finally:
        if os.path.exists(backup_atual):
            shutil.move(backup_atual, test_file)

    if not series:
        sys.exit("[erro] Nenhuma repetição produziu log (verifique a chave de API).")

    # Comprimento máximo (algumas repetições terminam antes; carrega-se o último
    # valor adiante, pois após saturar o nº de sobreviventes não muda).
    max_t = max(max(s) for s in series)
    with open(args.saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tentativa", "sobreviventes_medio", "sobreviventes_min",
                    "sobreviventes_max", "repeticoes"])
        for t in range(max_t + 1):
            valores = [_valor_em(s, t) for s in series]
            w.writerow([t, sum(valores) / len(valores), min(valores),
                        max(valores), len(valores)])

    print(f"\nCurva de convergência salva em: {args.saida}")
    print("Dica: o limite justificado é a tentativa a partir da qual a média para de cair.")


def _valor_em(serie, t):
    """Sobreviventes na tentativa t; se a repetição terminou antes, repete o último."""
    if t in serie:
        return serie[t]
    anteriores = [k for k in serie if k <= t]
    return serie[max(anteriores)] if anteriores else serie[min(serie)]


if __name__ == "__main__":
    main()
