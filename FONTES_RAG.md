# Fontes que fundamentam o RAG do framework

Documento de vetação das fontes usadas para justificar, com base em estudos, a
decisão de usar RAG e o método de recuperação adotado. Segue o mesmo espírito da
seleção de fontes já feita no TCC.

## Lacuna identificada
O `referencias.bib` só tinha `lewis2020` (RAG genérico para NLP). Não havia
nenhuma fonte sobre RAG aplicado a geração de testes/código, nem sobre o método
de recuperação (embeddings densos). As fontes abaixo foram acrescentadas.

## Fontes adotadas

1. `shin2024rag` — Shin et al. (2024), *Retrieval-Augmented Test Generation: How
   Far Are We?* (arXiv:2409.12682, aceito no ICSE 2026).
   - Justifica: RAG aplicado à geração de testes unitários melhora a cobertura
     (ganho médio de 6,5 pontos percentuais em cobertura de linha em cinco
     bibliotecas Python). Ressalva honesta a registrar: não melhorou métricas de
     correção. É a evidência empírica direta de que recuperar contexto ajuda a
     tarefa de geração de testes.

2. `zhang2023repocoder` — Zhang et al. (2023), *RepoCoder: Repository-Level Code
   Completion Through Iterative Retrieval and Generation* (EMNLP 2023).
   - Justifica: recuperação de contexto em nível de repositório combinada com o
     gerador, em um laço iterativo de recuperação e geração. Sustenta a escolha
     do corpus (o código do projeto-alvo) e o formato iterativo do nosso laço.

3. `reimers2019sbert` — Reimers e Gurevych (2019), *Sentence-BERT: Sentence
   Embeddings using Siamese BERT-Networks* (EMNLP-IJCNLP 2019).
   - Justifica: o método de representação por embeddings densos e busca por
     similaridade (base do `sentence-transformers` usado na implementação).

## Como o RAG é montado (consistente com a Seção 2.6 do TCC)
O corpus de recuperação é o próprio projeto-alvo: código-fonte (assinaturas,
exemplos de uso, definições de tipos) e a suíte de testes existente. Para cada
mutante sobrevivente, o operador de mutação e o diff formam a consulta; os
trechos mais relevantes são recuperados e inseridos no prompt, no lugar de
despejar os arquivos inteiros.
