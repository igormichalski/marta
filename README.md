# MARTA

**M**ulti-**A**gent **R**etrieval-augmented **T**est **A**ugmentation.

MARTA é um framework que fortalece automaticamente uma suíte de testes em Python.
Ele usa o **Cosmic Ray** para identificar mutantes sobreviventes (defeitos que a
suíte não detecta), recupera do próprio projeto o contexto mais relevante para
cada mutante (**RAG**) e emprega um **LLM** como agente gerador, que escreve
novos testes para matá-los. Cada teste gerado passa por uma validação dupla:
estrutural (roda no Pytest) e de eficácia (reexecução da análise de mutação).
Quando os mutantes restantes não podem ser mortos após o limite de tentativas,
eles são classificados como **candidatos a mutantes equivalentes**, que exigem
inspeção humana, pois a equivalência de programas é indecidível no caso geral.

## Como funciona

1. O Cosmic Ray gera os mutantes do módulo sob teste e aponta os sobreviventes.
2. Para cada mutante, o componente de RAG recupera do projeto os trechos mais
   relevantes por similaridade de *embeddings*.
3. O agente gerador (LLM) escreve uma nova função de teste com esse contexto.
4. O teste é validado: precisa passar no Pytest e reduzir o número de mutantes
   sobreviventes. Caso contrário, é descartado e o gerador é acionado de novo com
   um retorno explicativo (agente crítico).
5. O laço termina quando todos os mutantes são mortos ou o limite de tentativas
   é atingido.

## Instalação

Requer **Python 3.11+**.

```bash
pip install .
# ou, direto do repositório:
pip install git+https://github.com/igormichalski/marta
```

Para uso a partir do código-fonte, sem instalar:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Chave de API

O agente gerador usa um LLM via **Groq**. A chave é lida da variável de ambiente
`GROQ_API_KEY` e **nunca** fica no código. Crie um arquivo `.env` (não versionado)
a partir de `.env.example`:

```bash
cp .env.example .env
# edite .env e coloque sua chave
```

## Uso

A configuração fica em um arquivo `.toml` e a ferramenta é acionada por
subcomandos, de modo semelhante ao Cosmic Ray. O diretório `exemplo/` traz um
caso mínimo pronto (o algoritmo de Luhn):

```bash
cd exemplo

# Apenas analisar e listar os mutantes sobreviventes (não usa o LLM):
marta report

# Executar o ciclo multiagente completo (usa o LLM):
marta run
```

## Configuração

Edite o arquivo `.toml`. A seção `[cosmic-ray]` é a configuração padrão do Cosmic
Ray; a seção `[framework]` reúne os parâmetros da MARTA.

| Seção          | Campo               | Significado                                           |
|----------------|---------------------|-------------------------------------------------------|
| `[cosmic-ray]` | `module-path`       | código-fonte alvo a ser mutado                        |
| `[cosmic-ray]` | `timeout`           | tempo máximo (s) por mutante                          |
| `[framework]`  | `test-file`         | arquivo de testes onde os testes serão injetados      |
| `[framework]`  | `provider`          | provedor do LLM (atualmente `groq`)                   |
| `[framework]`  | `model`             | modelo usado como agente gerador                      |
| `[framework]`  | `temperature`       | temperatura de geração                                |
| `[framework]`  | `max-attempts`      | tentativas consecutivas sem progresso antes de parar  |
| `[framework]`  | `api-key-env`       | nome da variável de ambiente com a chave de API       |
| `[framework]`  | `rag`               | liga (`true`) ou desliga o RAG                        |
| `[framework]`  | `rag-k`             | número de trechos recuperados por consulta            |
| `[framework]`  | `mutantes-no-prompt`| máximo de mutantes descritos no prompt                |

## Estrutura

- `marta/` — o pacote: `framework.py` (CLI e laço) e `rag.py` (recuperação de contexto).
- `exemplo/` — caso mínimo de uso (código-alvo, suíte e configuração).
- `pyproject.toml`, `requirements.txt` — empacotamento e dependências.

## Licença

MIT.
