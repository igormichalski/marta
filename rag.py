"""Atalho de compatibilidade. A implementação vive em marta/rag.py."""

from marta.rag import *  # noqa: F401,F403
from marta import rag as _rag

__all__ = getattr(_rag, "__all__", [n for n in dir(_rag) if not n.startswith("_")])
