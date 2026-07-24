import ast
import glob
import os
from functools import lru_cache

MODELO_EMBED = "all-MiniLM-L6-v2"
CHROMA_DIR = ".chroma"
COLECAO = "alvo"

ARQUIVOS_FRAMEWORK = ("framework.py", "rag.py", "experimento_tentativas.py", "agregar.py")


@lru_cache(maxsize=1)
def _modelo():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO_EMBED)


def _chunks_arquivo(caminho):
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
    corpus = []
    for caminho in sorted(glob.glob(os.path.join(diretorio, "*.py"))):
        if os.path.basename(caminho) in ignorar:
            continue
        corpus.extend(_chunks_arquivo(caminho))
    return corpus


def construir_indice(diretorio, ignorar=ARQUIVOS_FRAMEWORK):
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
    partes = []
    for op, orig, mut in mutantes:
        partes.append(op)
        if orig:
            partes.append(orig)
        if mut:
            partes.append(mut)
    return "\n".join(partes) if partes else "teste unitario"


def formatar_contexto(itens):
    if not itens:
        return ""
    blocos = []
    for it in itens:
        blocos.append(f"# de {it['arquivo']} :: {it['nome']}\n{it['texto']}")
    return "\n\n".join(blocos)


def formatar_trace(itens):
    if not itens:
        return "(RAG: nenhum trecho recuperado)"
    return "  ".join(f"{it['arquivo']}::{it['nome']}({it['distancia']:.3f})" for it in itens)
