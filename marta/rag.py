"""Recuperação de contexto (RAG) para o agente gerador.

Em vez de despejar arquivos inteiros no prompt, indexamos o projeto-alvo em
unidades semânticas (funções, classes e funções de teste, extraídas via AST) e,
para cada mutante sobrevivente, recuperamos os trechos mais relevantes por
similaridade de embeddings. Isso segue a recuperação em nível de repositório de
RepoCoder (Zhang et al., 2023) e a representação por embeddings densos do
Sentence-BERT (Reimers e Gurevych, 2019). A motivação empírica para RAG na
geração de testes está em Shin et al. (2024).

Embeddings: sentence-transformers (modelo local, sem chamadas externas).
Índice: Chroma persistente, reconstruído a cada execução para evitar dados
obsoletos.
"""

import ast
import glob
import os
from functools import lru_cache

MODELO_EMBED = "all-MiniLM-L6-v2"
CHROMA_DIR = ".chroma"
COLECAO = "alvo"

# Arquivos do próprio framework: nunca entram no corpus do projeto-alvo.
ARQUIVOS_FRAMEWORK = ("framework.py", "rag.py", "experimento_tentativas.py", "agregar.py")


@lru_cache(maxsize=1)
def _modelo():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO_EMBED)


def _chunks_arquivo(caminho):
    """Divide um arquivo Python em unidades (def/class de nível superior)."""
    try:
        with open(caminho, encoding="utf-8") as f:
            fonte = f.read()
        arvore = ast.parse(fonte)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    chunks = []
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            trecho = ast.get_source_segment(fonte, no)
            if trecho and trecho.strip():
                chunks.append({
                    "nome": no.name,
                    "arquivo": os.path.basename(caminho),
                    "texto": trecho,
                })
    return chunks


def coletar_corpus(diretorio, ignorar=()):
    """Coleta as unidades de todos os .py do diretório do projeto-alvo."""
    corpus = []
    for caminho in sorted(glob.glob(os.path.join(diretorio, "*.py"))):
        if os.path.basename(caminho) in ignorar:
            continue
        corpus.extend(_chunks_arquivo(caminho))
    return corpus


def construir_indice(diretorio, ignorar=ARQUIVOS_FRAMEWORK):
    """Constrói (do zero) o índice vetorial do projeto-alvo.

    Retorna a coleção Chroma e o corpus indexado, ou (None, []) se não houver
    nada para indexar.
    """
    import chromadb

    corpus = coletar_corpus(diretorio, ignorar)
    if not corpus:
        return None, []

    textos = [c["texto"] for c in corpus]
    vetores = _modelo().encode(textos, normalize_embeddings=True).tolist()

    cliente = chromadb.PersistentClient(path=os.path.join(diretorio or ".", CHROMA_DIR))
    try:
        cliente.delete_collection(COLECAO)
    except Exception:
        pass
    colecao = cliente.create_collection(COLECAO, metadata={"hnsw:space": "cosine"})
    colecao.add(
        ids=[f"c{i}" for i in range(len(corpus))],
        documents=textos,
        embeddings=vetores,
        metadatas=[{"nome": c["nome"], "arquivo": c["arquivo"]} for c in corpus],
    )
    return colecao, corpus


def recuperar(colecao, consulta, k=3):
    """Recupera os k trechos mais relevantes para a consulta."""
    if colecao is None:
        return []
    total = colecao.count()
    if total == 0:
        return []
    vetor = _modelo().encode([consulta], normalize_embeddings=True).tolist()
    res = colecao.query(query_embeddings=vetor, n_results=min(k, total))
    itens = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        itens.append({
            "texto": doc,
            "arquivo": meta.get("arquivo", "?"),
            "nome": meta.get("nome", "?"),
            "distancia": float(dist),
        })
    return itens


def consulta_de_mutantes(mutantes):
    """Monta a consulta de recuperação a partir dos mutantes sobreviventes.

    `mutantes` é a lista de tuplas (operador, linha_original, linha_mutada)
    produzida por framework.listar_mutantes.
    """
    partes = []
    for op, orig, mut in mutantes:
        partes.append(op)
        if orig:
            partes.append(orig)
        if mut:
            partes.append(mut)
    return "\n".join(partes) if partes else "teste unitario"


def formatar_contexto(itens):
    """Formata os trechos recuperados para inserção no prompt."""
    if not itens:
        return ""
    blocos = []
    for it in itens:
        blocos.append(f"# de {it['arquivo']} :: {it['nome']}\n{it['texto']}")
    return "\n\n".join(blocos)


def formatar_trace(itens):
    """Resumo legível de quais trechos foram recuperados (para comprovação)."""
    if not itens:
        return "(RAG: nenhum trecho recuperado)"
    return "  ".join(f"{it['arquivo']}::{it['nome']}({it['distancia']:.3f})" for it in itens)
