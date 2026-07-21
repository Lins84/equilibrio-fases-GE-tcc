# Equilíbrio de Fases Gᴱ — TCC (Engenharia Química, UFC)

Ferramenta interativa em **Flet** para ensino de equilíbrio líquido-vapor (VLE),
usando a biblioteca **thermo** para propriedades dos componentes (Psat, etc.).

## Estrutura do projeto

- `gemini.py` — núcleo de cálculo: modelos de coeficiente de atividade (Gᴱ) e a
  função `calculate_vle_isothermal` que gera os diagramas P-x-y a partir da
  Lei de Raoult modificada.
- `fletando.py` — protótipo de UI Flet (tabela dinâmica de pontos P/x/y com
  adição/remoção de linhas via `ft.DataTable`).
- `main.py` — protótipo de UI Flet mais simples, gera um gráfico estático
  (matplotlib) de exemplo e exibe via `ft.Image`. Ainda não integrado ao
  `gemini.py`.
- `.replit` / `pyproject.toml` / `uv.lock` — projeto roda no Replit, gerenciado
  com `uv`.

Esses três arquivos ainda estão desconectados: `gemini.py` tem a lógica de
cálculo, `fletando.py` e `main.py` são protótipos de interface que ainda
não consomem `calculate_vle_isothermal`.

## Estado atual (última sessão — 2026-07-20/21)

Auditoria em `gemini.py`, focada nos modelos `model_margules_1p` e
`model_van_laar`:

- **Bug encontrado e corrigido**: em `model_van_laar`, os casos-limite de
  divisão por zero (`x1 == 0` e `x2 == 0`) estavam trocando γ1 e γ2. O valor
  `np.exp(A12)` deve corresponder a γ1 quando x1→0 (não γ2), e
  `np.exp(A21)` a γ2 quando x2→0. Correção já aplicada em `gemini.py`
  (linhas ~20-21), **mas ainda não commitada** (`git status` mostra
  `gemini.py` modificado, working tree à frente do commit `f58049b`).
- **Validação**: resultados conferidos com dados reais do `thermo` para o
  sistema **Dioxano/Metanol**. Os parâmetros `A12`/`A21` usados no teste
  foram valores de exemplo (não os parâmetros reais do sistema).

## Próximos passos

1. Buscar os valores reais de `A12`/`A21` (Van Laar) para o sistema
   Dioxano/Metanol na literatura (ou banco de dados do `thermo`, se
   disponível) e revalidar com eles.
2. Commitar a correção do bug de troca γ1↔γ2 em `model_van_laar`.
3. Integrar `gemini.py` (cálculo) com a UI (`fletando.py`/`main.py`), que
   hoje são protótipos isolados.

## Notas

- `x1_array` cobre 0 a 1 em 101 pontos (`np.linspace(0, 1, 101)`), então os
  casos-limite `x1 == 0` e `x2 == 0` do Van Laar são sempre exercitados —
  qualquer bug de troca γ1↔γ2 ali afeta diretamente as extremidades do
  diagrama P-x-y.
- Ao adicionar novos modelos Gᴱ (Wilson, NRTL, UNIQUAC — já sinalizados como
  TODO no código), seguir o mesmo padrão: função `model_xxx(x1, params)` que
  retorna `(gamma1, gamma2)`, registrada no dicionário `MODELS_GE`.
