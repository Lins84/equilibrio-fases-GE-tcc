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

## Estado atual (última sessão — 2026-07-27)

Os 6 modelos Gᴱ registrados em `MODELS_GE` (`model_margules_1p`,
`model_margules_2p`, `model_van_laar`, `model_wilson`, `model_uniquac`,
`model_unifac`) estão todos auditados e validados por comparação direta
com as implementações de referência do `thermo` (`Wilson_gammas`,
`UNIQUAC_gammas`, `UNIFAC.from_subgroups`), varrendo toda a faixa de
composição (x1 de 0 a 1, incluindo os extremos) — não apenas com valores de
exemplo. Três bugs foram encontrados e corrigidos nessa auditoria:

1. **`model_wilson`** — nos limites exatos x1=0 e x2=0, a fórmula trocava
   γ1↔γ2 e usava o parâmetro de interação errado no termo logarítmico
   (mesma classe de bug do fix do Van Laar em `8c29dcb`).
2. **`model_unifac` (parte residual)** — os índices dos parâmetros τ na
   soma do denominador estavam trocados (`tau(n, m)` em vez de `tau(m, n)`),
   o que só afeta sistemas com parâmetros de interação assimétricos
   (a_mn ≠ a_nm — ou seja, praticamente todos os sistemas reais).
3. **`model_unifac` (parte combinatorial, limites x1=0/x2=0)** — o código
   zerava o termo em vez de calcular o limite analítico correto (mesma
   classe de bug do item 1).

Além disso, a tabela de parâmetros de interação UNIFAC `_A` embutida em
`gemini.py` tinha **41 de 66 pares errados** (erro de transcrição, não
sistemático) quando comparada à tabela de referência `UFIP` do `thermo`.
Foi reescrita por completo com os valores corretos do `thermo.unifac.UFIP`.
A tabela de subgrupos `UNIFAC_SUBGROUPS` (R, Q, grupo principal) já estava
100% correta e não precisou de ajuste. Uma função auxiliar morta (nunca
chamada) em `model_uniquac` também foi removida.

Após as correções, os 6 modelos foram revalidados de ponta a ponta via
`calculate_vle_isothermal` com o sistema etanol/água a 70 °C — todos geram
diagramas P-x-y sem NaN/Inf, com P>0 e y1 ∈ [0,1] em toda a faixa.

- Trabalho conduzido diretamente aqui no Claude Code (decisão já tomada em
  sessão anterior, abandonando o fluxo do Replit Agent para o push).
- **Push resolvido em 2026-07-28**: o bloqueio 403 do `GITHUB_TOKEN` que
  havia nesta sessão não ocorre mais; `git push origin main` volta a
  funcionar normalmente.

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

## Sessão NRTL (2026-07-29)

Implementado `model_nrtl` em `gemini.py`, o último modelo Gᴱ que faltava.
Segue o mesmo padrão dos demais (`model_xxx(x1, params)` → `(gamma1,
gamma2)`, registrado em `MODELS_GE`), mas com uma diferença notável: a
fórmula do NRTL **não** tem indeterminação 0/0 nos limites x1=0/x2=0 (ao
contrário de Wilson/UNIQUAC/UNIFAC), então não precisou de casos especiais
nos extremos.

Também foi adicionada `nrtl_params_from_ipdb(cas1, cas2, T_K)`, um adaptador
fino que busca bij/αij em `thermo.interaction_parameters.IPDB` (tabela
`'ChemSep NRTL'`) e retorna `{tau12, tau21, alpha12}` prontos para
`model_nrtl` (τij = bij / T_K) — evitando hardcodar parâmetros da
literatura, como planejado na sessão anterior.

Validado com erro máximo ~1e-15 contra `thermo.NRTL_gammas`:
- em toda a faixa de x1 (0 a 1, 101 pontos) com parâmetros sintéticos;
- em toda a faixa de x1 com parâmetros reais do par Dioxano (CAS
  `123-91-1`) / Metanol (CAS `67-56-1`) via `nrtl_params_from_ipdb`.

Teste ponta-a-ponta via `calculate_vle_isothermal('1,4-dioxane', 'methanol',
70.0, 'NRTL', ...)` gerou diagrama P-x-y sem NaN/Inf, com P>0 e y1 ∈ [0,1]
em toda a faixa — mesmo padrão de validação usado nos outros 6 modelos.

Com isso, os **7 modelos Gᴱ** (`Margules 1P/2P`, `Van Laar`, `Wilson`,
`NRTL`, `UNIQUAC`, `UNIFAC`) estão implementados e validados em `gemini.py`.

## Sessão de validação cruzada com thermo (2026-07-29)

Comparação numérica, ponto a ponto (x1 de 0 a 1, 101 pontos), entre os
modelos manuais do `gemini.py` e as implementações equivalentes da própria
`thermo` (`Wilson_gammas`, `NRTL_gammas`, `UNIQUAC_gammas`,
`UNIFAC.from_subgroups(...).gammas()`):

- **Wilson** e **NRTL**: erro máximo de `~1e-16` contra `thermo`, em toda a
  faixa de x1 incluindo os extremos (x1=0 e x1=1). Equivalência total.
- **UNIQUAC** e **UNIFAC**: erro máximo de `~1e-14`/`1e-15` contra `thermo`
  no interior da faixa (0 < x1 < 1). Equivalência total onde a `thermo`
  consegue calcular.

**Achado**: nos extremos exatos (x1=0 e x1=1), a própria `thermo` **falha**
para UNIQUAC — tanto a função solta `UNIQUAC_gammas` (retorna `NaN`, com
`RuntimeWarning: invalid value encountered in scalar divide`) quanto a
classe completa `thermo.UNIQUAC` (`ZeroDivisionError: float division by
zero`). O `model_uniquac` do `gemini.py` trata esses limites analiticamente
(mesmo padrão dos outros `model_xxx`) e por isso **não tem esse problema**
— ou seja, nesse caso específico a implementação manual do projeto é mais
robusta que a implementação de referência da própria `thermo`. Já o
`UNIFAC.from_subgroups(...).gammas()` da `thermo` lida bem com os extremos
(testado x1=0 e x1=1), então esse problema é específico do UNIQUAC.

**Decisão**: manter todos os 7 modelos Gᴱ manuais em `gemini.py`, sem
migrar nenhum para chamar `thermo` diretamente (nem Wilson/NRTL, que
poderiam ser substituídos sem perda). Motivos: (1) já validados
exaustivamente contra a `thermo`, migrar não ganha corretude; (2) evita
risco de regressão em código que já funciona; (3) evita depender de
versão da `thermo` para resultados reproduzirem igual no futuro; (4) valor
pedagógico de ter a matemática implementada e compreendida na mão, com o
achado do bug de fronteira do UNIQUAC como evidência extra de rigor de
validação. Margules (1P/2P) e Van Laar continuam sendo os únicos
"obrigatoriamente" manuais, por não existir equivalente na `thermo`.

## Próximos passos

1. Integrar `gemini.py` (cálculo, já validado — todos os 7 modelos Gᴱ) com
   a UI (`fletando.py`/`main.py`), que hoje são protótipos isolados. Esse é
   o próximo item de maior valor: sem essa integração o núcleo de cálculo
   não é utilizável pelo usuário final.
2. Considerar expor `nrtl_params_from_ipdb` (e, futuramente, adaptadores
   equivalentes para Wilson/UNIQUAC via IPDB) na UI, para que o usuário
   possa escolher buscar parâmetros reais em vez de digitá-los manualmente.

## Sessão de tutoria — fundamentos de `Chemical` (2026-07-29)

Explorando `thermo.chemical.Chemical` além do `Psat` já usado em `gemini.py`:

- **`Chemical.Hvap` está em J/kg (base mássica), não J/mol.** Testado com
  água a 298.15 K: `Chemical('water', T=298.15).Hvap` retorna `2441674.29`,
  que só bate com o valor conhecido de literatura (~44000 J/mol) depois de
  multiplicar por `MW/1000` (`Hvap * MW / 1000 ≈ 43987 J/mol`). A própria
  docstring confirma: "in units of [J/kg]... converts its results from
  molar to mass units". `gemini.py` não usa `Hvap` hoje, mas é uma pegadinha
  de unidade real caso o projeto venha a precisar dessa propriedade —
  **nunca assumir unidade pelo nome do atributo, sempre checar a docstring**
  (`MW` também foge do padrão SI: é g/mol, não kg/mol).
- **`Chemical(id, ...)` aceita nome, sinônimo, fórmula ou CAS** como
  identificador — inclusive testado `'Agua'` (português, sem acento), que
  resolveu corretamente para água (`CAS 7732-18-5`). Provavelmente
  coincidência de correspondência ampla no banco de sinônimos, não suporte
  i18n oficial, mas relevante para a UI do projeto (que é em português) —
  vale testar a robustez disso com mais nomes em português antes de confiar
  como recurso de UX.
- Composto não reconhecido lança `ValueError` claro
  (`"Chemical name (...) not recognized"`), útil para tratamento de erro na
  UI ao validar entrada do usuário.

## Notas

- `x1_array` cobre 0 a 1 em 101 pontos (`np.linspace(0, 1, 101)`), então os
  casos-limite `x1 == 0` e `x2 == 0` são sempre exercitados em qualquer
  modelo. Essa classe de bug (fórmula do limite errada ou γ1↔γ2 trocados)
  já apareceu três vezes — Van Laar (`8c29dcb`), Wilson e UNIFAC (sessão
  2026-07-27) — vale conferir esse caso específico ao mexer em qualquer
  `model_xxx`.
- Ao adicionar novos modelos Gᴱ, seguir o mesmo padrão: função
  `model_xxx(x1, params)` que retorna `(gamma1, gamma2)`, registrada no
  dicionário `MODELS_GE`, e validar contra a implementação de referência
  do `thermo` (ex.: `thermo.NRTL_gammas`) em toda a faixa de x1, não só em
  um ponto.
