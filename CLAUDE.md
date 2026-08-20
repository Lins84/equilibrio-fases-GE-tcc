# Equilíbrio de Fases Gᴱ — TCC (Engenharia Química, UFC)

Ferramenta interativa em **Flet** para ensino de equilíbrio líquido-vapor (VLE),
usando a biblioteca **thermo** para propriedades dos componentes (Psat, etc.).

## Como trabalhar neste projeto — ler primeiro

Este é um **TCC**, e o uso de IA no desenvolvimento **será explicitado** no
trabalho final. Os papéis são fixos:

- **O autor é o diretor geral e o gerente operacional.** Define rumos,
  escopo, prioridades e ritmo. É quem decide.
- **O assistente é o operário.** Implementa, audita, testa e documenta
  **segundo o que o autor planejou**. Não decide rumo.

> **Regra central: nenhuma decisão entra no projeto sem ordem de validação
> do autor.**

Na prática:

1. **Propor, não executar.** Diante de escolha de rumo — arquitetura,
   dependência nova, mudança de abordagem, início de etapa — apresente a
   proposta e as alternativas e **aguarde**. Não avance por conta própria.
2. **Roadmap não é autorização.** "Próximos passos" descreve o previsto,
   não o liberado. A liberação é pedido explícito do autor, item a item —
   por mais que o item pareça óbvio, urgente ou de maior valor.
3. **O ritmo é o do autor.** A evolução acompanha o aprendizado dele, que
   precisa defender cada linha na banca. Ir mais rápido que esse
   entendimento produz código indefensável na arguição.
4. **Decisão só vai para a documentação depois que o autor a toma.** Você
   pode levantar a pendência, mapear opções e recomendar; quem fecha é ele.
5. **Explique antes do aceite.** O autor não aprova o que não entende.

Isso é o que dá o **caráter crítico humano especializado** aos rumos do
projeto e torna o uso de IA aqui auditável. Detalhamento na seção 5.2 de
`Docs/mapeamento_e_plano_TCC-1.md`.

## Estrutura do projeto

**Cálculo:**

- `gemini.py` (~405 linhas) — núcleo de cálculo. Os 7 modelos Gᴱ
  (`model_margules_1p`, `model_margules_2p`, `model_van_laar`,
  `model_wilson`, `model_nrtl`, `model_uniquac`, `model_unifac`),
  registrados em `MODELS_GE`; o adaptador `nrtl_params_from_ipdb`; e
  `calculate_vle_isothermal`, que gera os diagramas P-x-y a partir da Lei
  de Raoult modificada. Todos os modelos validados contra o `thermo`.

**UI (protótipos Flet, em ordem de evolução):**

- `main.py` (~34 linhas) — o mais antigo/simples: gráfico estático de
  exemplo via matplotlib, exibido como `ft.Image`.
- `fletando.py` (~218 linhas) — tabela dinâmica de pontos P/x/y com
  adição/remoção de linhas via `ft.DataTable`.
- `fletando_grafico.py` (~218 linhas) — **a linha viva da UI**: a tabela
  do `fletando.py` mais um `flet_charts.LineChart` que plota o diagrama
  P-x-y a partir dos dados brutos digitados (`parse_ponto` +
  `pontos_para_series`), com validação de entrada e mensagem de erro.
  Ainda "Etapa 2": nenhum cálculo de modelo, só visualiza o que o usuário
  digitou.

**Apoio:**

- `testes/` — scripts avulsos, rodados direto com `python3` (não há
  runner/pytest): `teste_margules_2p_MEK_tolueno.py` (validação numérica
  contra planilha XSEOS) e `teste_parse_ponto_tabela.py` (lógica pura da
  tabela, sem dependência de `flet`).
- `Docs/mapeamento_e_plano_TCC-1.md` — documento de escopo do TCC (autor,
  orientador, problema, objetivos, plano de execução).
- `referencias/` — material de referência: print da planilha XSEOS e dois
  `.jsx` de Margules 1P/2P.
- `.replit` / `pyproject.toml` / `uv.lock` — projeto roda no Replit,
  gerenciado com `uv`.

**Lacuna central:** cálculo e UI seguem desconectados. `gemini.py` está
pronto e validado, mas **nenhum** dos protótipos de UI chama
`calculate_vle_isothermal` — é exatamente o item 1 de "Próximos passos".

## Estado atual (2026-08-19)

Snapshot; o histórico por sessão vem logo abaixo.

- **Cálculo — pronto.** Os 7 modelos Gᴱ implementados e validados contra
  as referências do `thermo` em toda a faixa de x1 (0 a 1, extremos
  inclusos), não só em pontos de exemplo. Parâmetros reais disponíveis via
  `IPDB` (ChemSep) para NRTL, com `nrtl_params_from_ipdb`.
- **UI — protótipos.** `fletando_grafico.py` é o mais avançado: tabela
  editável + gráfico P-x-y dos dados digitados, com validação de entrada.
  Não faz nenhum cálculo de modelo.
- **Integração — não iniciada.** É o gargalo: nada na UI chama
  `calculate_vle_isothermal`, então o núcleo validado ainda não chega ao
  usuário final.
- **Testes** são scripts avulsos rodados à mão, sem runner nem CI.
- **Sem pendências de decisão em aberto** — a última (curva poligonal) foi
  fechada em 2026-08-19, ver seção própria.

## Sessão de auditoria dos modelos (2026-07-27)

Os 6 modelos Gᴱ então registrados em `MODELS_GE` (`model_margules_1p`,
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

## Próximos passos

> **Roadmap, não fila de tarefas autorizadas** — ver "Como trabalhar neste
> projeto" no topo. Nenhum item abaixo está liberado por estar listado
> aqui; cada um aguarda pedido explícito do autor. Vale em especial para a
> integração (item 1), mesmo sendo o de maior valor. Combinado em
> 2026-08-20.

1. Integrar `gemini.py` (cálculo, já validado — todos os 7 modelos Gᴱ) com
   a UI (hoje `fletando_grafico.py` é a linha viva; `fletando.py`/`main.py`
   são protótipos anteriores). Esse é o próximo item de maior valor: sem
   essa integração o núcleo de cálculo não é utilizável pelo usuário final.
   **Aguardando o "vamos integrar" do autor.**
2. Considerar expor `nrtl_params_from_ipdb` (e, futuramente, adaptadores
   equivalentes para Wilson/UNIQUAC via IPDB) na UI, para que o usuário
   possa escolher buscar parâmetros reais em vez de digitá-los manualmente.

## Decisão tomada: curva poligonal em fletando_grafico.py (2026-08-19)

**Contexto (levantado em 2026-08-10):** comparando visualmente
`fletando_grafico.py` (plota os pontos brutos da tabela editável, hoje só
~9 pontos no exemplo dioxano/metanol) com `teste_dioxano_nrtl.py` (curva
suave com ~50-100 pontos calculados via NRTL), o formato bate, mas o
traçado do `fletando_grafico.py` fica poligonal por ter poucos pontos.
Três abordagens foram levantadas: (1) interpolação matemática (spline
monotônica/PCHIP via scipy) sobre os pontos digitados; (2) recalcular via
NRTL usando `gemini.calculate_vle_isothermal`; (3) as duas combinadas.

**Decisão (2026-08-19): nenhuma das três — não haverá interpolação.**
Os pontos experimentais ficam **discretos**, ou seja: o gráfico mostra
apenas os pontos que foram medidos e digitados na tabela, sem gerar
nenhum ponto intermediário entre eles. A aparência poligonal **não é
defeito**: dado experimental é ponto, modelo é linha. A suavização virá
da **curva calculada**, quando a integração `gemini.py` + UI acontecer
(item 1 de "Próximos passos").

Consequências práticas:

- **Não** adicionar `scipy` como dependência direta em `pyproject.toml`
  para esse fim — a opção 1 está descartada.
- Interpolar pontos experimentais seria inventar dado que não foi medido;
  para um material didático de VLE isso é justamente o que não se quer
  ensinar.
- **Nenhuma mudança de código é necessária agora**: `fletando_grafico.py`
  já plota só os pontos brutos da tabela. A decisão fecha a pendência sem
  gerar tarefa.
- Essa decisão não trata de como os pontos são desenhados (marcador,
  traço ligando-os, espessura) — isso segue como está e é assunto de UI,
  a ser revisto junto com a integração, quando a curva do modelo passar a
  dividir o mesmo gráfico com os dados da tabela.

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
