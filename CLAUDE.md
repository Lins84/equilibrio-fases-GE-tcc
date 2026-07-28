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

## Estado atual (última sessão — 2026-07-21)

Auditoria em `gemini.py`, focada nos modelos `model_margules_1p` e
`model_van_laar`:

- **Bug encontrado e corrigido**: em `model_van_laar`, os casos-limite de
  divisão por zero (`x1 == 0` e `x2 == 0`) estavam trocando γ1 e γ2. O valor
  `np.exp(A12)` deve corresponder a γ1 quando x1→0 (não γ2), e
  `np.exp(A21)` a γ2 quando x2→0. Correção aplicada e **commitada** em
  `8c29dcb` ("Corrige troca de gamma1/gamma2 nos limites do modelo Van
  Laar").
- **Validação**: resultados conferidos com dados reais do `thermo` para o
  sistema **Dioxano/Metanol**. Os parâmetros `A12`/`A21` usados no teste
  foram valores de exemplo (não os parâmetros reais do sistema).

## Sessão de aprendizado `thermo` (2026-07-28)

Sessão dedicada a entender, na prática, como o `gemini.py` usa a `thermo`:

- **`Chemical(id, T=...)`**: resolve o identificador (nome/sinônimo/CAS) e dá
  acesso a propriedades constantes (`MW`, `Tc`, `Pc`, `omega`) e a
  sub-objetos "calculadores" por propriedade termofísica.
- **`Chemical.Psat`** é um atalho para `Chemical.VaporPressure(T)`. O objeto
  `VaporPressure` escolhe automaticamente, por substância, o melhor método
  disponível entre várias correlações (ex.: `HEOS_FIT` para etanol/metanol,
  `DIPPR_PERRY_8E` para 1,4-dioxano) — consultável via
  `.VaporPressure.method` e `.VaporPressure.all_methods`.
- **Achado importante para os próximos passos**: a `thermo` tem um banco de
  parâmetros de interação binária real (`thermo.interaction_parameters.IPDB`,
  fonte ChemSep) com tabelas `'ChemSep NRTL'`, `'ChemSep Wilson'` e
  `'ChemSep UNIQUAC'` — e o par Dioxano (CAS `123-91-1`) / Metanol (CAS
  `67-56-1`) tem dados nas três. Não há tabela de Van Laar no IPDB (modelo
  mais antigo, pouco usado em bancos modernos).
  ```python
  from thermo.interaction_parameters import IPDB
  from thermo import NRTL_gammas

  bij = IPDB.get_ip_asymmetric_matrix('ChemSep NRTL', [cas1, cas2], 'bij')
  alphaij = IPDB.get_ip_asymmetric_matrix('ChemSep NRTL', [cas1, cas2], 'alphaij')
  tau = [[bij[i][j] / T for j in range(2)] for i in range(2)]
  gamma1, gamma2 = NRTL_gammas([x1, x2], tau, alphaij)
  ```
  A `thermo` também expõe `Wilson_gammas` e `UNIQUAC_gammas` prontas — dá
  para implementar os modelos TODO (`model_wilson`, `model_nrtl`,
  `model_uniquac`) como adaptadores finos dessas funções + `IPDB`, ao invés
  de reimplementar as fórmulas ou procurar parâmetros manualmente na
  literatura.

## Próximos passos

1. Implementar `model_nrtl`/`model_wilson`/`model_uniquac` em `gemini.py`
   como adaptadores para `NRTL_gammas`/`Wilson_gammas`/`UNIQUAC_gammas` da
   `thermo`, buscando os parâmetros binários via `IPDB` (tabelas ChemSep)
   em vez de hardcodar valores da literatura.
2. Revalidar o sistema Dioxano/Metanol com os parâmetros NRTL reais do
   `IPDB` (substituindo os valores de exemplo usados para o Van Laar).
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
