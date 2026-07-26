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

## Estado atual (última sessão — 2026-07-26)

`gemini.py` cresceu bastante desde a auditoria do Van Laar: além de
`model_margules_1p` e `model_van_laar` (com o fix de γ1/γ2 já commitado em
`8c29dcb`), foram adicionados `model_margules_2p`, `model_wilson`,
`model_uniquac` e `model_unifac` (este último com tabelas de subgrupos e
parâmetros de interação embutidas), todos registrados em `MODELS_GE`.

- **Histórico local vs. GitHub**: local e `origin/main` haviam divergido
  (commits novos dos 4 modelos só localmente; fix do Van Laar, CLAUDE.md e
  outros só no GitHub). Resolvido via `git rebase origin/main` — histórico
  local limpo, sem `.claude-config/` rastreado, 15 commits à frente de
  `origin/main`, prontos para push.
- **Push pendente/bloqueado**: `git push origin main` falha com
  `403 Permission denied to Lins84`, mesmo com o `GITHUB_TOKEN` autenticando
  corretamente na API (leituras funcionam). Causa provável: o token é
  *fine-grained* e não tem a permissão **"Contents: Read and write"**
  habilitada para este repositório — sem isso a API de leitura funciona mas
  o `git push` (que exige essa permissão) é negado. Ação pendente: revisar
  em GitHub → Settings → Developer settings → Fine-grained tokens.
- **Decisão do usuário**: abandonar o relatório/fluxo do Replit Agent para
  esse push e conduzir o restante do trabalho diretamente por aqui (Claude
  Code).

## Próximos passos

1. **(retomar daqui)** Buscar os valores reais de `A12`/`A21` (Van Laar)
   para o sistema Dioxano/Metanol na literatura (ou banco de dados do
   `thermo`, se disponível) e revalidar com eles.
2. Integrar `gemini.py` (cálculo) com a UI (`fletando.py`/`main.py`), que
   hoje são protótipos isolados.
3. Resolver a permissão do `GITHUB_TOKEN` (Contents: Read and write) e
   fazer o `git push origin main` pendente (15 commits locais).

## Notas

- `x1_array` cobre 0 a 1 em 101 pontos (`np.linspace(0, 1, 101)`), então os
  casos-limite `x1 == 0` e `x2 == 0` do Van Laar são sempre exercitados —
  qualquer bug de troca γ1↔γ2 ali afeta diretamente as extremidades do
  diagrama P-x-y.
- Ao adicionar novos modelos Gᴱ (Wilson, NRTL, UNIQUAC — já sinalizados como
  TODO no código), seguir o mesmo padrão: função `model_xxx(x1, params)` que
  retorna `(gamma1, gamma2)`, registrada no dicionário `MODELS_GE`.
