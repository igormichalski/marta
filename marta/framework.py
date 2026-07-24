import argparse
import os
import re
import shlex
import subprocess
import sys
import time
import random

import toml

from . import rag

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CONFIG_PADRAO = "cosmic-ray.toml"
SESSION = "session.sqlite"
SESSION_CONFIG = ".framework_cosmic.toml"
RELATORIO_TXT = "mutants_report.txt"
FRAMEWORK_NAME = "MARTA"

_COR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(texto, codigo):
    return f"\033[{codigo}m{texto}\033[0m" if _COR else texto


def verde(t): return _c(t, "32")
def vermelho(t): return _c(t, "31")
def amarelo(t): return _c(t, "33")
def cinza(t): return _c(t, "90")
def negrito(t): return _c(t, "1")
def badge(t, cor): return _c(f" {t} ", cor)


def carregar_config(caminho):
    if not os.path.exists(caminho):
        sys.exit(f"Configuration file not found: {caminho}")
    dados = toml.load(caminho)
    cr, fw = dados.get("cosmic-ray", {}), dados.get("framework", {})
    cfg = {
        "module_path": cr.get("module-path"),
        "timeout": cr.get("timeout", 10.0),
        "test_file": fw.get("test-file"),
        "provider": fw.get("provider", "groq"),
        "model": fw.get("model", "llama-3.3-70b-versatile"),
        "temperature": fw.get("temperature", 0.1),
        "max_attempts": int(fw.get("max-attempts", 5)),
        "api_key_env": fw.get("api-key-env", "GROQ_API_KEY"),
        "rag": bool(fw.get("rag", True)),
        "rag_k": int(fw.get("rag-k", 3)),
        "mutantes_prompt": int(fw.get("mutantes-no-prompt", 12)),
    }
    for campo, valor in (("module-path", cfg["module_path"]), ("test-file", cfg["test_file"])):
        if not valor:
            sys.exit(f"Set '{campo}' in the configuration.")
        if not os.path.exists(valor):
            sys.exit(f"File not found: {valor}")
    return cfg


def gerar_config_cosmic(cfg):
    test_command = f"{shlex.quote(sys.executable)} -m pytest {shlex.quote(cfg['test_file'])}"
    conteudo = {"cosmic-ray": {
        "module-path": cfg["module_path"],
        "timeout": cfg["timeout"],
        "test-command": test_command,
        "distributor": {"name": "local"},
    }}
    with open(SESSION_CONFIG, "w") as f:
        toml.dump(conteudo, f)
    return SESSION_CONFIG


def _bin(nome):
    caminho = os.path.join(os.path.dirname(sys.executable), nome)
    return caminho if os.path.exists(caminho) else nome


def executar_cosmic_ray(config_cosmic):
    if os.path.exists(SESSION):
        os.remove(SESSION)
    subprocess.run([_bin("cosmic-ray"), "init", config_cosmic, SESSION],
                   check=True, capture_output=True)
    subprocess.run([_bin("cosmic-ray"), "exec", config_cosmic, SESSION],
                   check=True, capture_output=True)


def coletar_sobreviventes():
    saida = subprocess.run(
        [_bin("cr-report"), "--surviving-only", "--show-diff", SESSION],
        capture_output=True, text=True,
    ).stdout
    m = re.search(r"surviving mutants:\s*(\d+)\s*\(([\d.]+)%\)", saida)
    qtd = int(m.group(1)) if m else 0
    pct = float(m.group(2)) if m else 0.0
    return qtd, pct, saida


def total_mutantes(texto):
    m = re.search(r"total jobs:\s*(\d+)", texto)
    return int(m.group(1)) if m else 0


def listar_mutantes(texto):
    mutantes = []
    for bloco in texto.split("[job-id]")[1:]:
        op = re.search(r"(core/\S+)", bloco)
        orig = re.search(r"(?m)^-(?!--)(.*)$", bloco)
        mut = re.search(r"(?m)^\+(?!\+\+)(.*)$", bloco)
        if op:
            mutantes.append((op.group(1),
                             orig.group(1).strip() if orig else "",
                             mut.group(1).strip() if mut else ""))
    return mutantes


def salvar_relatorio_txt(texto, qtd, equivalentes=False):
    rotulo = "Surviving mutants (candidate equivalent mutants)" if equivalentes else "Surviving mutants"
    with open(RELATORIO_TXT, "w") as f:
        f.write(f"{rotulo}: {qtd}\n")
        f.write("=" * 60 + "\n\n")
        f.write(texto)


def executar_pytest(test_file):
    r = subprocess.run([sys.executable, "-m", "pytest", test_file],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stdout


def _carregar_chaves(cfg):
    multiplas = os.environ.get("GROQ_API_KEYS", "").strip()
    if multiplas:
        chaves = [k.strip() for k in multiplas.split(",") if k.strip()]
    else:
        unica = os.environ.get(cfg["api_key_env"])
        chaves = [unica] if unica else []
    if not chaves:
        sys.exit(f"Defina {cfg['api_key_env']} (ou GROQ_API_KEYS) com sua chave de API.")
    return chaves


def criar_cliente(cfg):
    if cfg["provider"] != "groq":
        sys.exit(f"Unsupported provider: {cfg['provider']}.")
    from groq import Groq
    chaves = _carregar_chaves(cfg)
    return {"clientes": [Groq(api_key=k) for k in chaves], "idx": 0}


def _e_limite(msg):
    return any(t in msg for t in ("rate", "429", "per day", "tpd", "tpm", "too large", "timeout", "503"))


def agente_gerador(cliente, cfg, prompt):
    clientes = cliente["clientes"]
    n = len(clientes)
    espera = 20
    voltas = 0
    for _ in range(3 * n + 2):
        try:
            resposta = clientes[cliente["idx"]].chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=cfg["model"],
                temperature=cfg["temperature"],
            )
            codigo = resposta.choices[0].message.content
            return codigo.replace("```python", "").replace("```", "").strip()
        except Exception as e:
            if not _e_limite(str(e).lower()):
                raise
            if n > 1:
                cliente["idx"] = (cliente["idx"] + 1) % n
                voltas += 1
                if voltas % n == 0:
                    print(f"  {amarelo('⚠')} todas as chaves no limite; aguardando {espera}s...")
                    time.sleep(espera)
                    espera = min(espera * 2, 60)
                else:
                    proxima = cliente["idx"] + 1
                    print(f"  {cinza(f'rotacionando para a chave {proxima}/{n}...')}")
            else:
                print(f"  {amarelo('⚠')} limite da API; aguardando {espera}s...")
                time.sleep(espera)
                espera = min(espera * 2, 60)
    raise RuntimeError("Todas as chaves de API atingiram o rate limit.")


def _relatorio_prompt(relatorio, k):
    partes = relatorio.split("[job-id]")
    if len(partes) <= k + 1:
        return relatorio
    blocos = "[job-id]".join(partes[1:k + 1])
    return f"{partes[0]}[job-id]{blocos}\n\n(... outros mutantes sobreviventes omitidos)"


def montar_prompt(cfg, codigo_fonte, contexto, rotulo_contexto, relatorio, feedback, id_teste):
    relatorio = _relatorio_prompt(relatorio, cfg.get("mutantes_prompt", 12))
    prompt = f"""Você é um framework de QA especialista em teste de mutação. Escreva
testes em Pytest que matem os mutantes sobreviventes listados abaixo.

CÓDIGO-FONTE SOB TESTE ({cfg['module_path']}):
{codigo_fonte}

{rotulo_contexto}:
{contexto}

MUTANTES SOBREVIVENTES (Cosmic Ray):
{relatorio}

Escreva UMA nova função de teste que mate um ou mais desses mutantes.
REGRAS:
1. O nome da função DEVE SER `def test_mutante_morto_{id_teste}():`.
2. Importe o necessário do módulo sob teste, se preciso.
3. Retorne APENAS o código Python, sem explicações."""
    if feedback:
        prompt += f"\n\nA tentativa anterior não funcionou:\n{feedback}"
    return prompt


def comando_report(cfg):
    inicio = time.time()
    print(negrito(f"\n  {FRAMEWORK_NAME} — mutation report\n"))
    executar_cosmic_ray(gerar_config_cosmic(cfg))
    qtd, pct, texto = coletar_sobreviventes()
    salvar_relatorio_txt(texto, qtd)

    if qtd == 0:
        print(f"  {badge('PASS', '42;30')} {verde('no mutants survived')}")
    else:
        print(f"  {badge('FAIL', '41;37')} {negrito(cfg['module_path'])}")
        for op, orig, mut in listar_mutantes(texto):
            print(f"    {vermelho('✗')} {op}")
            if orig:
                print(f"        {vermelho('- ' + orig)}")
                print(f"        {verde('+ ' + mut)}")
    _resumo(total_mutantes(texto) - qtd, qtd, total_mutantes(texto), inicio)


def comando_run(cfg, log_path=None):
    inicio = time.time()
    cliente = criar_cliente(cfg)
    config = gerar_config_cosmic(cfg)

    print(negrito(f"\n  Starting {FRAMEWORK_NAME}...\n"))
    executar_cosmic_ray(config)
    qtd, pct, relatorio = coletar_sobreviventes()
    total = total_mutantes(relatorio)
    historico = [(0, qtd)]

    if qtd == 0:
        salvar_relatorio_txt(relatorio, 0)
        print(f"  {badge('PASS', '42;30')} {verde('no mutants survived')}")
        _resumo(0, 0, total, inicio)
        return _metricas(cfg, total, 0, 0, 0, inicio)

    print(f"  {qtd} surviving mutant(s) found.\n")

    colecao = None
    if cfg["rag"]:
        diretorio = os.path.dirname(os.path.abspath(cfg["module_path"]))
        print(f"  {cinza('building retrieval index (RAG)...')}")
        colecao, corpus = rag.construir_indice(diretorio)
        print(f"  {cinza(f'indexed {len(corpus)} code unit(s).')}\n")

    with open(cfg["test_file"]) as f:
        backup = f.read()
    id_teste = random.randint(1000, 9999)
    feedback, falhas, mortos, n = None, 0, 0, 0
    traces = []

    while qtd > 0 and falhas < cfg["max_attempts"]:
        n += 1
        with open(cfg["module_path"]) as f:
            fonte = f.read()
        with open(cfg["test_file"]) as f:
            testes = f.read()

        if cfg["rag"] and colecao is not None:
            itens = rag.recuperar(colecao, rag.consulta_de_mutantes(listar_mutantes(relatorio)), cfg["rag_k"])
            contexto, rotulo = rag.formatar_contexto(itens), "CONTEXTO RECUPERADO DO PROJETO (RAG)"
            trace = rag.formatar_trace(itens)
            print(f"  {cinza('RAG → ' + trace)}")
            traces.append((n, trace))
        else:
            contexto, rotulo = testes, "ARQUIVO DE TESTES ATUAL"

        print(f"  {cinza(f'attempt {n}: generating test...')}")
        novo = agente_gerador(cliente, cfg, montar_prompt(cfg, fonte, contexto, rotulo, relatorio, feedback, id_teste))
        with open(cfg["test_file"], "a") as f:
            f.write(f"\n\n# teste auto-gerado {id_teste}\n{novo}\n")

        passou, log = executar_pytest(cfg["test_file"])
        if not passou:
            _restaurar(cfg["test_file"], backup)
            falhas += 1
            feedback = f"O teste falhou no Pytest:\n{log[-1200:]}"
            print(f"  {amarelo('⚠')} attempt {n} — invalid test (Pytest)")
        else:
            executar_cosmic_ray(config)
            nova_qtd, _, novo_rel = coletar_sobreviventes()
            if nova_qtd < qtd:
                print(f"  {verde('✓')} attempt {n} — killed {qtd - nova_qtd} mutant(s) "
                      f"{cinza(f'({qtd} → {nova_qtd})')}")
                mortos += qtd - nova_qtd
                qtd, relatorio = nova_qtd, novo_rel
                backup = testes + f"\n\n# teste auto-gerado {id_teste}\n{novo}\n"
                feedback, falhas = None, 0
            else:
                _restaurar(cfg["test_file"], backup)
                falhas += 1
                feedback = ("O teste passou no Pytest mas não matou nenhum mutante. "
                            "Crie um teste mais rigoroso, validando o retorno para entradas válidas.")
                print(f"  {amarelo('○')} attempt {n} — no mutants killed")
        historico.append((n, qtd))
        id_teste = random.randint(1000, 9999)

    salvar_relatorio_txt(relatorio, qtd, equivalentes=True)
    _gravar_log(log_path, historico)
    _gravar_trace(traces)
    _resumo(mortos, qtd, total, inicio, equivalentes=True)
    return _metricas(cfg, total, mortos, qtd, n, inicio)


def _metricas(cfg, total, mortos, restantes, tentativas, inicio):
    sobreviventes_iniciais = mortos + restantes
    return {
        "modulo": cfg["module_path"],
        "rag": cfg["rag"],
        "total": total,
        "mortos": mortos,
        "sobreviventes": restantes,
        "score_inicial": (total - sobreviventes_iniciais) / total * 100 if total else 100.0,
        "score": (total - restantes) / total * 100 if total else 100.0,
        "tentativas": tentativas,
        "tempo_s": round(time.time() - inicio, 1),
    }


def _gravar_trace(traces):
    if not traces:
        return
    with open("rag_trace.txt", "w") as f:
        f.write("Trace de recuperação (RAG) por tentativa\n")
        f.write("=" * 60 + "\n\n")
        for n, trace in traces:
            f.write(f"tentativa {n}: {trace}\n")


def _restaurar(test_file, conteudo):
    with open(test_file, "w") as f:
        f.write(conteudo)


def _gravar_log(log_path, historico):
    if not log_path:
        return
    with open(log_path, "w") as f:
        f.write("tentativa,sobreviventes\n")
        for t, s in historico:
            f.write(f"{t},{s}\n")


def _resumo(mortos, restantes, total, inicio, equivalentes=False):
    score = (total - restantes) / total * 100 if total else 100.0
    print()
    print(f"  {negrito('Mutants:')} {verde(f'{mortos} killed')}, "
          f"{vermelho(f'{restantes} surviving')}, {total} total")
    print(f"  {negrito('Score:')}   {score:.1f}%")
    print(f"  {negrito('Time:')}    {time.time() - inicio:.1f} s")
    if restantes:
        if equivalentes:
            print(f"\n  {amarelo('Remaining mutants are candidate equivalent mutants.')}")
        else:
            print(f"\n  {amarelo('These mutants survive the current test suite.')}")
        print(f"  {cinza(f'Report saved to {RELATORIO_TXT}')}")
    else:
        print(f"\n  {verde('All mutants were killed.')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Framework multiagente guiado por mutação.")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome, ajuda in (("run", "gera testes para matar os mutantes"),
                        ("report", "lista os mutantes sobreviventes")):
        p = sub.add_parser(nome, help=ajuda)
        p.add_argument("config", nargs="?", default=CONFIG_PADRAO)
        if nome == "run":
            p.add_argument("--log", default=None, help="CSV com sobreviventes por tentativa")
            p.add_argument("--max-attempts", type=int, default=None, help="sobrescreve o limite")
            p.add_argument("--no-rag", action="store_true", help="desliga o RAG (ablação)")
            p.add_argument("--rag-k", type=int, default=None, help="nº de trechos recuperados pelo RAG")

    args = parser.parse_args()
    cfg = carregar_config(args.config)
    if args.comando == "report":
        comando_report(cfg)
    else:
        if args.max_attempts is not None:
            cfg["max_attempts"] = args.max_attempts
        if args.no_rag:
            cfg["rag"] = False
        if args.rag_k is not None:
            cfg["rag_k"] = args.rag_k
        comando_run(cfg, log_path=args.log)


if __name__ == "__main__":
    main()
