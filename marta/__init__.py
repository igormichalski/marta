"""MARTA: Multi-Agent Retrieval-augmented Test Augmentation.

Framework multiagente que fortalece suítes de teste guiado por análise de
mutação, recuperação de contexto (RAG) e um laço de geração e crítica com um LLM.
"""

__version__ = "0.1.0"

from .framework import main

__all__ = ["main", "__version__"]
