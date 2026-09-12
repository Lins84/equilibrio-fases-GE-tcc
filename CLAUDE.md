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
3. **O ritmo é o do autor, e a barra de entendimento é a que o orientador
   fixou — não "linha a linha".** Orientação do Dr. Filipe Xavier Feitosa
   em tira-dúvidas (2026-09-01): entender o **básico** de cada parte,
   priorizar **entregar funcionando**; a redação do TCC vem depois, sobre
   o que já funciona. Não é convite a aceitar código sem entender nada —
   é calibragem de profundidade, não descarte do item 5.
4. **Decisão só vai para a documentação depois que o autor a toma.** Você
   pode levantar a pendência, mapear opções e recomendar; quem fecha é ele.
5. **Explique antes do aceite.** O autor não aprova o que não entende.

Isso é o que dá o **caráter crítico humano especializado** aos rumos do
projeto e torna o uso de IA aqui auditável. Detalhamento na seção 5.2 de
`Docs/mapeamento_e_plano_TCC-1.md`.

## Estrutura do projeto

Layout de pastas adotado em 2026-08-20 (item de Fase 0 do plano):
`calculos/` (motor de cálculo), `interface/` (UI Flet), `testes/`,
`Docs/`, `referencias/`.

**Cálculo — `calculos/`:**

- `calculos/gemini.py` (~405 linhas) — núcleo de cálculo. Os 7 modelos Gᴱ
  (`model_margules_1p`, `model_margules_2p`, `model_van_laar`,
  `model_wilson`, `model_nrtl`, `model_uniquac`, `model_unifac`),
  registrados em `MODELS_GE`; o adaptador `nrtl_params_from_ipdb`; e
  `calculate_vle_isothermal`, que gera os diagramas P-x-y a partir da Lei
  de Raoult modificada. Todos os modelos validados contra o `thermo`.

**UI — `interface/` (protótipos Flet, em ordem de evolução):**

- `interface/main.py` (~34 linhas) — o mais antigo/simples: gráfico
  estático de exemplo via matplotlib, exibido como `ft.Image`.
- `interface/fletando.py` (~218 linhas) — tabela dinâmica de pontos P/x/y
  com adição/remoção de linhas via `ft.DataTable`.
- `interface/fletando_grafico.py` (~218 linhas) — **a linha viva da UI**:
  a tabela do `fletando.py` mais um `flet_charts.LineChart` que plota o diagrama
  P-x-y a partir dos dados brutos digitados (`parse_ponto` +
  `pontos_para_series`), com validação de entrada e mensagem de erro.
  Ainda "Etapa 2": nenhum cálculo de modelo, só visualiza o que o usuário
  digitou.

**Apoio:**

- `testes/` — scripts avulsos, rodados direto com `python3` **a partir da
  raiz** (não há runner/pytest): `teste_margules_2p_MEK_tolueno.py`
  (validação numérica contra planilha XSEOS, sem dependências externas) e
  `teste_parse_ponto_tabela.py` (lógica da tabela; insere `interface/` no
  `sys.path` para achar o módulo, e exige `flet` instalado — ver ressalva
  no topo do arquivo).
- `Docs/mapeamento_e_plano_TCC-1.md` — documento de escopo do TCC (autor,
  orientador, problema, objetivos, plano de execução).
- `referencias/` — material de referência: print da planilha XSEOS e dois
  `.jsx` de Margules 1P/2P.
- `.replit` / `pyproject.toml` / `uv.lock` — projeto roda no Replit,
  gerenciado com `uv`.

**Lacuna central:** cálculo e UI seguem desconectados. `calculos/gemini.py`
está pronto e validado, mas **nenhum** dos protótipos de UI chama
`calculate_vle_isothermal` — é exatamente o item 1 de "Próximos passos".

> **Nota para a integração:** com a separação em pastas, um script rodado
> de dentro de `interface/` não enxerga `calculos/` automaticamente (o
> Python põe em `sys.path[0]` a pasta do script, não a raiz). Como a UI
> importar o motor de cálculo é decisão de arquitetura — `sys.path`,
> pacote com `__init__.py`, ou instalação editável via `pyproject.toml` —
> e fica para o autor decidir quando a integração for liberada. Nada foi
> pré-resolvido aqui.

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
3. **Regressão de parâmetros a partir dos dados de entrada** (decidido em
   2026-09-12, detalhado em `Docs/mapeamento_e_plano_TCC-1.md` seção 2.8).
   Resolve a antiga pendência do Van Laar sem tabela no `IPDB` — mas de
   forma geral: como a aplicação precisa funcionar para qualquer par que
   o usuário escolher, nenhum banco cobre tudo, então quando não houver
   parâmetro fornecido nem em banco, ele é regredido a partir dos pontos
   (P, x, y) já digitados na tabela (inverte Raoult modificada → γ
   "experimental" → ajusta o modelo por regressão não-linear). Não se
   aplica ao UNIFAC (preditivo, sem parâmetro ajustável por par).
   **Requisito de UI vinculado, padrão escolhido em 2026-09-12 (detalhe
   na seção 2.8):** selo pequeno, colorido, sempre visível perto do
   parâmetro/gráfico ("Fornecido" / "Banco de dados" / "Calculado"), com
   ícone ⓘ grudado que abre o detalhe rico ao passar o mouse/clicar
   (o que foi assumido, quantos pontos entraram na regressão). Nem
   rodapé fixo (compete com o gráfico) nem só ícone (a origem não é
   detalhe opcional — não pode depender de clique pra aparecer). O selo
   atualiza em tempo real com o parâmetro, pela regra de ouro da seção
   2.2 do mapeamento.

## Decisões de engenharia do aluno na produção da aplicação

Criada em 2026-09-12, a pedido do autor: um mapeamento cronológico que
separa explicitamente **o que foi decisão do autor** do **o que foi
execução/análise do Claude Code sob a direção dele** — a evidência
concreta da "cadeia de validação" já descrita em "Como trabalhar neste
projeto" (topo deste arquivo) e na seção 5.2 do mapeamento. Reconstruída
a partir do histórico deste arquivo, do mapeamento e das sessões de
trabalho. **Seção viva: todo novo commit registrado como "decisão
tomada" ou equivalente neste arquivo deveria ganhar uma linha aqui.**

Convenção: cada entrada é uma escolha de rumo, escopo, método ou critério
que coube ao autor — não ao assistente — fechar. Quando a origem da ideia
foi uma sugestão do Claude Code, isso é dito explicitamente; a decisão em
si (aceitar, recusar, ou pedir algo diferente) é sempre do autor. Onde
existe evidência verificável (commit, arquivo, seção do mapeamento), ela
está citada.

### A. Decisões de método e corretude — o núcleo técnico

São as decisões que determinam **se os números que a aplicação produz são
confiáveis**, e por isso as mais defensáveis perante a banca.

- **(julho/2026) Escrever as equações dos modelos Gᴱ diretamente no
  código, em vez de chamar as funções prontas da `thermo`.** A
  alternativa estava explicitamente sobre a mesa e ficou registrada na
  sessão de 2026-07-28 deste arquivo: *"dá para implementar os modelos
  TODO como adaptadores finos dessas funções + IPDB, ao invés de
  reimplementar as fórmulas"*. O autor escolheu o caminho oposto.
  Verificável em `calculos/gemini.py`: os 7 modelos têm as fórmulas
  escritas em Python; a `thermo` só aparece em `Chemical` (Psat) e em
  `nrtl_params_from_ipdb` (parâmetros). Duas consequências pesadas:
  1. **A validação deixa de ser circular.** Uma implementação
     independente comparada a uma implementação de referência é um teste
     real; um invólucro da `thermo` comparado à própria `thermo` não
     prova nada. Foi essa escolha que tornou possível encontrar os 4 bugs.
  2. **A física fica visível no código.** Para um TCC de ensino de
     Termodinâmica, o autor consegue apontar a equação na tela e
     explicá-la — o que uma chamada de biblioteca esconderia.
- **(julho/2026) Papéis atribuídos à `thermo`: fonte de dados e oráculo
  de validação, nunca motor de cálculo.** Corolário da decisão acima, e o
  que define a arquitetura do `gemini.py`: a biblioteca entrega
  propriedades (Psat por substância, com a correlação que ela julga
  melhor) e parâmetros (IPDB/ChemSep); a física dos modelos Gᴱ é código
  do projeto.
- **(2026-07-23) Construir o caso de validação antes do modelo que ele
  vai checar.** O teste de referência do Margules 2P (MEK/Tolueno a
  323,15 K, a partir da planilha XSEOS) foi commitado em `8cea7b7`
  (23/07); o `model_margules_2p` só apareceu em `e383f1c` (26/07) — três
  dias depois. A referência externa existia antes do código, então não
  havia como o código "definir" o que seria considerado certo.
- **(2026-07-27) Critério de validação: varrer toda a faixa de
  composição, não pontos de exemplo.** x1 de 0 a 1 em 101 pontos,
  incluindo os extremos exatos. **Foi esse critério que achou os bugs**:
  três dos quatro só se manifestam em x1=0 ou x2=0. Uma conferência em
  x1=0,5 — que é o que um teste "de exemplo" faria — teria passado nos
  quatro casos sem acusar nada.
- **(2026-07-27) Resolver os limites de composição analiticamente, não
  numericamente.** Wilson, UNIQUAC e UNIFAC têm indeterminação 0/0 nos
  limites de componente puro. As saídas fáceis seriam empurrar x para
  perto de zero (usar 1e-9 no lugar de 0) ou deixar passar NaN; o autor
  optou por calcular o limite analítico de cada caso. Visível em
  `model_wilson` (`if x1 == 0: return np.exp(1 - L21 - np.log(L12)), 1.0`)
  e no bloco combinatorial do `model_unifac`. **Nota de correção:** o
  NRTL é justamente o único que **não** precisou disso — sua fórmula é
  bem-comportada nos extremos. Os limites tratados foram Van Laar
  (`8c29dcb`), Wilson e UNIFAC.
- **(2026-07-27) Tratar erro de dado com o mesmo rigor que erro de
  fórmula.** Encontrados 41 pares errados de 66 na tabela de interação
  UNIFAC (`_A`), o autor optou por **reescrever a tabela inteira** a
  partir da fonte de referência (`thermo.unifac.UFIP`), em vez de
  corrigir só os pares que afetavam o sistema em teste. Erro de
  transcrição é invisível para qualquer teste que não exercite aquele par
  específico — corrigir pontualmente deixaria bombas armadas para
  qualquer sistema futuro.
- **(2026-07-28/29) Buscar parâmetros em banco de dados em vez de
  hardcodar valores de literatura.** Descoberto o `IPDB` (fonte ChemSep)
  na `thermo`, o autor optou por construir o adaptador
  `nrtl_params_from_ipdb(cas1, cas2, T_K)` — parâmetros resolvidos por
  CAS, em tempo de execução — em vez de copiar constantes de artigos para
  dentro do código. Elimina uma classe inteira de erro de transcrição
  (a mesma que produziu os 41 pares errados do UNIFAC).
- **(2026-08-19) Não interpolar pontos experimentais.** Rejeitadas as
  três abordagens levantadas (spline PCHIP, recálculo via NRTL, ambas)
  para "suavizar" a curva poligonal. Critério: dado experimental é ponto,
  modelo é linha — interpolar seria fabricar medida que não existe, e num
  material didático de VLE isso é exatamente o que não se quer ensinar.
  A suavização virá da curva calculada. Seção própria neste arquivo.
- **(2026-09-12) Regredir o parâmetro dos dados de entrada quando não
  houver outra fonte.** O autor identificou que caçar um valor de
  literatura para um par específico não resolve o problema geral — a
  aplicação tem que funcionar para qualquer par que o usuário escolher, e
  nenhum banco cobre todo par possível. Decisão: inverter a Lei de Raoult
  modificada nos pontos digitados para obter γ "experimental" e ajustar o
  modelo por regressão não-linear. Insight do autor, não sugestão do
  assistente. Reformula a antiga pendência do Van Laar em capacidade
  geral (seção 2.8 do mapeamento).
- **(2026-09-12) Exigir que a aplicação declare a origem de cada
  parâmetro.** Requisito de transparência científica levantado pelo
  autor: quem usa precisa saber se está vendo valor fornecido, de banco,
  ou regredido de poucos pontos, **antes** de tirar conclusão do gráfico.
  Um parâmetro ajustado a 5 pontos digitados e um parâmetro medido e
  publicado não têm a mesma força, e a interface não pode apagar essa
  diferença.

### B. Decisões de arquitetura e stack

- **(pré-julho/2026) Escopo e stack do TCC** — Flet + `thermo`, três
  eixos de uso (didático-visual, validação de exercícios, pesquisa),
  usuário final é o orientador, não o autor (seção 1 do mapeamento).
- **(2026-08-20) Separar o código em `calculos/` e `interface/`**,
  fechando um item da Fase 0 que estava aberto desde julho.
- **Manter Python + `thermo` na camada de cálculo**, recusando reescrever
  em outra linguagem — a `thermo` não tem equivalente fora do Python, e
  trocar descartaria toda a validação já feita.
- **Manter Flet na camada de UI**, recusando migrar para React/Recharts
  mesmo diante de um protótipo visualmente mais atraente
  (`referencias/margules-1-parametro.jsx`) — praticidade sobre estética,
  em linha com o "entregar funcionando" do orientador.
- **Recusar Flutter nativo (Dart)**, mesmo sendo mais maduro que o Flet
  beta: quebraria o processo único (UI e cálculo juntos em Python) e
  exigiria manter um backend separado rodando durante a aula.
- **Recusar embutir um assistente de IA dentro do app** — custo
  recorrente por uso, novo ponto de falha de rede em aula ao vivo, e
  escopo fora dos três eixos do projeto.
- **(2026-09-12) Adotar o padrão selo + ícone ⓘ** para a nota de origem
  do parâmetro (sugestão do Claude Code; a decisão de adotá-la, em vez de
  rodapé fixo ou só ícone flutuante, foi do autor).

### C. Decisões de processo e prestação de contas

- **(julho/2026) Nem descartar nem usar às cegas o `gemini.py`
  herdado.** Código gerado por outra IA sem supervisão: em vez de jogar
  fora pela origem ou aceitar sem checar, o autor decidiu submetê-lo a
  auditoria técnica documentada como condição para incorporá-lo (seção
  5.1 do mapeamento). É a decisão-raiz de todo o método de validação da
  parte A.
- **(julho/2026) Abandonar o fluxo do Replit Agent para push**, passando
  a conduzir o desenvolvimento diretamente no Claude Code.
- **(2026-09-12, registrado) Combinar três ambientes de trabalho por
  necessidade real de mobilidade, não por preferência técnica.** Claude
  Code como ferramenta de desenvolvimento; Replit como IDE, usado quando
  havia internet, por dar acesso tanto pelo celular quanto pelo PC;
  Termux com Ubuntu adaptado (proot-Ubuntu) para rodar e testar a
  aplicação localmente — **a única forma de produzir a aplicação fora de
  casa, sem internet e sem acesso a um PC.** Detalhe e log de testes de
  instalação na seção 4.1 e 7.2 do mapeamento.
- **(2026-08-20) Estabelecer o modelo de governança** — autor como
  diretor geral e gerente operacional, assistente como executor, nenhuma
  decisão entrando sem ordem de validação. Esta seção nasce desse modelo.
- **(2026-09-01) Consultar o orientador sobre a profundidade de
  entendimento exigida** e adotar a resposta ("entender o básico,
  priorizar entregar funcionando") como barra do projeto, substituindo a
  formulação anterior, mais rígida, de "entender e defender cada linha".
- **(2026-09-02) Corrigir uma imprecisão técnica antes do envio ao
  orientador.** Revisando o rascunho do e-mail sobre UNIFAC, o autor
  identificou sozinho que "lista fixa e finita" sugeria um recorte
  arbitrário do projeto, quando é a tabela clássica publicada do método.
  Corrigido antes de enviar, não depois (`d4408e8`) — revisão crítica
  humana sobre texto técnico gerado com apoio de IA.
- **(2026-09-12) Criar esta seção**, formalizando o registro cronológico
  de decisões do autor como prática permanente do projeto.

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
