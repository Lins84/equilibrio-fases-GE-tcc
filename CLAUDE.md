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

- `calculos/gemini.py` (~720 linhas) — núcleo de cálculo. Os 7 modelos Gᴱ
  (`model_margules_1p`, `model_margules_2p`, `model_van_laar`,
  `model_wilson`, `model_nrtl`, `model_uniquac`, `model_unifac`),
  registrados em `MODELS_GE`; `calculate_vle_isothermal`, que gera os
  diagramas P-x-y a partir da Lei de Raoult modificada (devolve também
  `gamma1`/`gamma2` para o gráfico de ln γ vs x1); adaptadores de
  parâmetro via banco IPDB/ChemSep (`nrtl_params_from_ipdb`,
  `wilson_params_from_ipdb` — 2026-09-27 — e `uniquac_params_from_ipdb`)
  e via grupos UNIFAC/DDBST (`unifac_groups_from_name`,
  `uniquac_rq_from_groups`, `montar_parametros_automaticos` — usado por
  UNIQUAC/UNIFAC na UI, sem slider manual); `buscar_parametros_banco`
  (2026-09-27), que resolve nome/sinônimo/CAS via `thermo.Chemical` e
  despacha para o adaptador IPDB certo, para os modelos com tabela lá
  (`MODELOS_COM_BANCO_IPDB = {"NRTL", "Wilson"}` — Margules e Van Laar
  não têm tabela no IPDB); e `regress_params_barker` (2026-09-27), que
  ajusta os parâmetros livres de um modelo a partir dos pontos (P, x1,
  y1) digitados, por mínimos quadrados não-lineares diretos sobre P e y
  (método de Barker, seção 2.8 do mapeamento — `scipy.optimize`, já
  instalado indiretamente via `thermo`). Todos os modelos e adaptadores
  validados contra o `thermo`/dados sintéticos.

**UI — `interface/` (protótipos Flet, em ordem de evolução):**

- `interface/main.py` (~34 linhas) — o mais antigo/simples: gráfico
  estático de exemplo via matplotlib, exibido como `ft.Image`.
- `interface/fletando.py` (~218 linhas) — tabela dinâmica de pontos P/x/y
  com adição/remoção de linhas via `ft.DataTable`.
- `interface/fletando_grafico.py` (~1525 linhas) — **a linha viva da UI,
  já integrada ao motor de cálculo**: tabela editável de pontos
  experimentais P/x/y (com importação de CSV, "Desfazer" e "Limpar
  Tabela"), escolha de modelo Gᴱ e de componentes/temperatura, sliders de
  parâmetros, gráfico P-x-y com a curva do modelo
  (`calculate_vle_isothermal`) sobreposta aos pontos, e gráfico de ln γ vs
  x1. Botões de apoio ao parâmetro: "Buscar do Banco (IPDB)" (NRTL/Wilson),
  "Calcular por Regressão (Barker)" e "Comparar" (curva calculada nos x1
  exatos da tabela + ΔP/Δy). Selo de origem do parâmetro com ⓘ em diálogo.
  Layout adaptativo desktop/mobile (com botão para alternar os dois à mão),
  tema claro fixo. Histórico e decisões em "Próximos passos" (itens 1-4),
  em "Sessão de estética e bug de renderização intermitente
  (2026-09-28/29)" e em "Sessão de verificação visual, lixeira no celular
  e modo de exibição (2026-09-30/10-01)".

**Apoio:**

- `testes/` — scripts avulsos, rodados direto com `python3` **a partir da
  raiz** (não há runner/pytest): `teste_margules_2p_MEK_tolueno.py`
  (validação numérica contra planilha XSEOS, sem dependências externas),
  `teste_parse_ponto_tabela.py` (lógica da tabela; insere `interface/` no
  `sys.path` para achar o módulo, e exige `flet` instalado — ver ressalva
  no topo do arquivo) e `teste_dioxano_nrtl.py` (teste manual visual —
  app Flet próprio que roda `calculate_vle_isothermal` com NRTL e
  parâmetros reais via `nrtl_params_from_ipdb`/IPDB para dioxano/metanol
  a 70 °C, e plota o diagrama P-x-y calculado; recuperado em 2026-09-26
  de um commit que existia só numa cópia do Replit sem sincronia por
  git, nunca antes enviado ao GitHub — mesmo teste citado na sessão de
  2026-07-29 acima) e `teste_regressao_barker.py` (valida
  `regress_params_barker`: gera dados sintéticos sem ruído a partir de
  parâmetros conhecidos — Margules 1P, NRTL com α12 fixo, UNIQUAC com
  r/q via grupos UNIFAC — e confere que a regressão os recupera; cobre
  também os três erros esperados da seção 2.8: poucos pontos, parâmetro
  fixo obrigatório faltando, e UNIFAC sem regressão) e
  `teste_banco_ipdb.py` (2026-09-27 — valida `wilson_params_from_ipdb`
  contra a referência da própria docstring de `thermo.wilson.Wilson`
  para etanol/água a 70 °C, e `buscar_parametros_banco` para NRTL e
  Wilson via nome/sinônimo em vez de CAS, além dos erros esperados:
  modelo sem tabela no IPDB e par ausente na tabela).
- `Docs/mapeamento_e_plano_TCC-1.md` — documento de escopo do TCC (autor,
  orientador, problema, objetivos, plano de execução).
- `referencias/` — material de referência: print da planilha XSEOS, dois
  `.jsx` de Margules 1P/2P, e `esboco_manuscrito_autor.jpg` (2026-09-27 —
  o rascunho original do autor que embasou a seção 2.2 do mapeamento;
  mostra também um elemento perto do gráfico P-x-y, anotado "P"/"y exp"
  com um quadro "Salva" ao lado, ainda não implementado — ver pendência
  em "Próximos passos").
- `.replit` / `pyproject.toml` / `uv.lock` — projeto roda no Replit,
  gerenciado com `uv`.

**Integração cálculo ↔ UI: concluída em 2026-09-26** (commit `deba9cc`).
`fletando_grafico.py` importa `calculos.gemini` e chama
`calculate_vle_isothermal`. Os protótipos `main.py` e `fletando.py`
continuam como estavam, sem ligação com o motor de cálculo, e ficam só
como registro da evolução da UI.

> **Nota para a integração:** com a separação em pastas, um script rodado
> de dentro de `interface/` não enxerga `calculos/` automaticamente (o
> Python põe em `sys.path[0]` a pasta do script, não a raiz). Como a UI
> importar o motor de cálculo é decisão de arquitetura — `sys.path`,
> pacote com `__init__.py`, ou instalação editável via `pyproject.toml` —
> e fica para o autor decidir quando a integração for liberada. Nada foi
> pré-resolvido aqui.

> **Atualização para Flet 1.0.0 — concluída e testada de verdade
> (2026-09-21).** O que era análise teórica (2026-09-20) virou migração
> real, autorizada e executada pelo autor. Resultado:
>
> 1. **`pyproject.toml` atualizado** para `flet>=1.0.0` e
>    `flet-charts>=1.0.0`. `uv lock --upgrade-package flet
>    --upgrade-package flet-charts` resolveu os dois em `1.0.0`/`1.0.0`
>    — confirmado no `uv.lock`, sem desalinhamento.
> 2. **`ft.InputBorder.NONE` → `ft.NoInputBorder()`** corrigido nos dois
>    lugares (`fletando.py:58`, `fletando_grafico.py:58`) — já que
>    estávamos mexendo no código de qualquer forma.
> 3. **Suíte de testes** (`teste_margules_2p_MEK_tolueno.py`,
>    `teste_parse_ponto_tabela.py`) rodada depois da atualização
>    completa — ambos passam sem alteração.
> 4. **App rodado de verdade e testado visualmente** (`flet run
>    interface/fletando_grafico.py -d --web`, dirigido via Playwright +
>    Chromium headless): tabela edita, botões ("Adicionar Novo Ponto",
>    "Gerar Gráfico") funcionam, `LineChart` do `flet_charts` 1.0.0
>    desenha eixos/escala/legenda corretamente, e a validação de linha
>    inválida ("1 linha(s) ignorada(s) por dado inválido") disparou como
>    esperado. Prints em anexo na conversa com o autor.
>
> **Achado novo, não previsto na análise teórica:** `flet run --web`
> (modo dev) carrega o motor de renderização (CanvasKit/Skia WASM) de
> `www.gstatic.com` no **navegador**, na primeira carga da página — sem
> internet nesse momento, a tela trava indefinidamente na splash screen
> do Flet. `flet build web --no-cdn` embute esses arquivos localmente,
> mas essa flag **não existe** em `flet run --web`, só no build de
> produção. Isso importa para o fluxo Termux-sem-internet já registrado
> na seção 4.1 do mapeamento: testar/demonstrar o app **offline** exige
> `flet build web --no-cdn` (+ servir os arquivos estáticos gerados),
> não `flet run --web` direto. Não é regra nova do projeto nem decisão
> — é um fato técnico descoberto ao rodar de verdade, registrado para
> quando isso importar.

## Estado atual (2026-10-01)

Snapshot; o histórico por sessão vem logo abaixo.

- **Cálculo — pronto.** Os 7 modelos Gᴱ implementados e validados contra
  as referências do `thermo` em toda a faixa de x1 (0 a 1, extremos
  inclusos). Parâmetros via IPDB (NRTL, Wilson, UNIQUAC), via grupos
  UNIFAC e via regressão de Barker (`regress_params_barker`).
- **UI — integrada.** `fletando_grafico.py` calcula e plota a curva do
  modelo sobre os pontos digitados, com banco IPDB, regressão, selo de
  origem, comparação calculado-vs-experimental (ΔP/Δy), estética em
  andamento e botão para alternar entre layout de celular e de computador.
- **Pendências.** A estética segue em andamento (escopo: app inteiro); a
  lista de itens levantados e ainda não atacados está na sessão de
  2026-09-30/10-01. O modo isobárico (T-x-y) está adiado para depois do
  piloto, em "Atualizações futuras". Não há decisão de rumo em aberto
  neste momento.
- **Testes** são scripts avulsos rodados à mão, sem runner nem CI (5
  scripts em `testes/`, 4 automatizados). A interface é verificada
  visualmente pelo autor no dispositivo real **e**, desde 2026-09-30,
  também pelo Claude Code por captura de tela em ambiente de nuvem — ver
  sessão de 2026-09-30/10-01 para o alcance e os limites de cada uma.

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

1. ~~Integrar `gemini.py` (cálculo, já validado — todos os 7 modelos Gᴱ)
   com a UI (hoje `fletando_grafico.py` é a linha viva; `fletando.py`/
   `main.py` são protótipos anteriores). Esse é o próximo item de maior
   valor: sem essa integração o núcleo de cálculo não é utilizável pelo
   usuário final. Aguardando o "vamos integrar" do autor.~~ **Feito em
   2026-09-26** (commit `deba9cc`, "Liga a UI a calculate_vle_isothermal
   — curva do modelo no gráfico"): `gerar_grafico` passou a chamar
   `calculate_vle_isothermal` com modelo/parâmetros/componentes/
   temperatura escolhidos na UI, sobrepondo a curva calculada aos pontos
   digitados na tabela. Os itens 2-4 abaixo (banco IPDB, regressão de
   Barker, comparação calculado-vs-experimental) já partem dessa
   integração pronta. Esta entrada estava desatualizada — sinalizado
   pelo autor em 2026-09-27.
2. ~~Considerar expor `nrtl_params_from_ipdb` (e, futuramente, adaptadores
   equivalentes para Wilson/UNIQUAC via IPDB) na UI, para que o usuário
   possa escolher buscar parâmetros reais em vez de digitá-los
   manualmente.~~ **Feito em 2026-09-27** (autorizado pelo autor: "vamos
   expor as opções pro usuário escolher"). Adicionado
   `wilson_params_from_ipdb` (novo — a tabela `'ChemSep Wilson'` do IPDB
   guarda Λ12/Λ21 já prontos via `ln(Λij) = aij + bij/T`, sem precisar de
   volume molar à parte) e `buscar_parametros_banco(model_name,
   component1_id, component2_id, T_K)`, que resolve nome/sinônimo/CAS via
   `thermo.Chemical` e despacha para NRTL ou Wilson
   (`MODELOS_COM_BANCO_IPDB`). Na UI (`fletando_grafico.py`), botão
   "Buscar do Banco (IPDB)" aparece só para NRTL/Wilson, ao lado do botão
   de regressão — o usuário escolhe entre digitar manualmente, buscar no
   banco ou regredir dos pontos da tabela. UNIQUAC continua resolvendo
   a12/a21 automaticamente (sem esse botão — já é banco por padrão);
   Margules/Van Laar não têm tabela no IPDB, então não ganham o botão.
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
   na seção 2.8), implementado em 2026-09-27** ("implemente agora o selo
   de origem"): selo pequeno, colorido, sempre visível perto do
   parâmetro/gráfico ("Fornecido" / "Banco de dados" / "Calculado"), com
   ícone ⓘ grudado que abre o detalhe rico ao passar o mouse/clicar
   (o que foi assumido, quantos pontos entraram na regressão). Nem
   rodapé fixo (compete com o gráfico) nem só ícone (a origem não é
   detalhe opcional — não pode depender de clique pra aparecer). O selo
   atualiza em tempo real com o parâmetro, pela regra de ouro da seção
   2.2 do mapeamento. Em `fletando_grafico.py`: `ORIGENS_SELO` (cor +
   rótulo por tipo) e `atualizar_selo_origem(tipo, detalhe)`; cobre os
   quatro modelos com slider manual (Margules 1P/2P, Van Laar, Wilson,
   NRTL — volta para "Fornecido" assim que qualquer slider é arrastado
   manualmente, mesmo depois de um valor vir do banco ou da regressão) e
   também UNIQUAC ("Banco de dados", fixo — a12/a21 sempre vêm do IPDB)
   e UNIFAC ("Preditivo", fixo — sem parâmetro de interação ajustável).
   Validado na UI rodando: Margules 1P (Fornecido), NRTL/Wilson após
   "Buscar do Banco" (Banco de dados, com τ12/τ21/α12 ou Λ12/Λ21 reais),
   reversão para Fornecido ao arrastar um slider manualmente, e UNIQUAC/
   UNIFAC nos seus selos fixos.
   **Método de redução escolhido em 2026-09-13: Barker (direto).** O
   modelo é ajustado contra o resíduo de P e y diretamente, não contra γ
   "experimental" calculado ponto a ponto (método indireto, descartado).
   Motivo: rigor estatístico — trata o erro no espaço onde ele foi de
   fato medido (P, y), em vez de propagá-lo por uma divisão que amplifica
   ruído perto de x1→0/1. Custo de desempenho analisado e descartado como
   preocupação: para o tamanho de tabela esperado (dezenas de pontos, não
   milhares), a regressão inteira fica na casa de poucos milissegundos —
   irrelevante perto do custo de renderizar o gráfico, que é o mesmo nos
   dois métodos. Implica otimização aninhada (resolver P/y a cada
   iteração do ajuste dos parâmetros) — mais complexa de implementar que
   o indireto, aceita conscientemente pelo autor em troca do rigor
   estatístico.
   **α12 do NRTL, decidido em 2026-09-13: fixado, não ajustado.** Evita o
   mau-condicionamento de regredir 3 parâmetros com poucos pontos.
   **Requisito de UI vinculado, implementado em 2026-09-27:** nota
   explicativa junto ao valor de α, no mesmo padrão selo+ícone ⓘ já
   definido para a origem do parâmetro — avisando que aquele α foi
   fixado por convenção (valor de referência comum na literatura, algo
   entre 0,2 e 0,47 conforme o tipo de sistema), não obtido por
   regressão. Sem essa nota, o usuário pode presumir que os 3 parâmetros
   do NRTL foram ajustados igualmente, quando só τ12/τ21 foram. Como
   α12 real e medido também pode vir do banco IPDB (item 2 acima) — caso
   em que não é convenção, é dado —, a nota ficou redigida para ser
   verdadeira nos dois casos ("quando não vier do banco, fica fixado por
   convenção"), em vez de rastrear a origem de α12 separadamente do
   resto do selo.
   **Mínimo de pontos, decidido em 2026-09-13: nº de parâmetros do
   modelo + 1.** Abaixo disso a regressão não tem grau de liberdade
   nenhum — encaixa a curva exatamente nos pontos digitados (resíduo
   zero), sem nenhuma evidência de que o modelo descreve o sistema fora
   deles, e arrisca mau-condicionamento numérico no Barker. Com o piso
   em parâmetros + 1, sobra o mínimo de folga pra existir algum resíduo
   a examinar. Mínimos concretos por modelo:
   | Modelo | Parâmetros livres | Mínimo de pontos |
   |---|---|---|
   | Margules 1P | 1 (A) | 2 |
   | Margules 2P, Van Laar, Wilson, UNIQUAC | 2 | 3 |
   | NRTL (α12 fixo) | 2 (τ12, τ21) | 3 |
   | UNIFAC | — (preditivo) | não se aplica |

   **Requisito de UI vinculado, implementado em 2026-09-27:** quando a
   tabela tiver exatamente o mínimo (grau de liberdade = 1), o selo de
   origem (já definido acima) ganha uma variante — "Calculado (poucos
   pontos)" — avisando que o ajuste tem baixa confiança. Abaixo do
   mínimo, a regressão não roda; a UI mostra a mensagem de erro (mínimo
   de pontos, modelo, quantos foram digitados) em vez de falhar
   silenciosamente — validado na UI rodando (Van Laar com 0 pontos
   válidos, mensagem correta).
   **Gatilho da regressão — duas decisões em paralelo, reconciliadas em
   2026-09-27 na integração dos branches:** em 2026-09-21, numa sessão
   que só tinha a tabela/gráfico básico (`fletando_grafico.py` ainda na
   "Etapa 2", sem regressão implementada), o autor decidiu manter manual
   reaproveitando o botão "Gerar Gráfico" já existente
   (`botao_gerar_grafico`/`gerar_grafico`), pra não coexistirem dois
   comportamentos diferentes no mesmo app. Em paralelo, em outra sessão
   que já tinha construído e testado ponta a ponta o motor de regressão
   (`regress_params_barker`) e a UI (sliders, banco IPDB, selo), o autor
   confirmou manual de novo em 2026-09-27, mas com o desenho já
   implementado: botão dedicado "Calcular por Regressão (Barker)",
   separado de "Gerar Gráfico". Na integração dos dois branches, ficou o
   desenho de 2026-09-27 — é o que existe como código real, testado
   (aqui e no Termux) —, e o de 2026-09-21 registra a intenção original,
   nunca chegou a ser implementada antes de a outra sessão construir a
   versão que já existe. **O item 3 está fechado** com o botão
   dedicado.
4. **Comparação calculado-vs-experimental** (levantado pelo autor em
   2026-09-27, a partir do rascunho original — `referencias/
   esboco_manuscrito_autor.jpg`, que já indicava um elemento perto do
   gráfico P-x-y, anotado "P"/"y exp"). Faltava no mapeamento porque o
   esboço nunca tinha sido digitalizado/registrado antes.
   **Desenho de UI, decidido em 2026-09-27 (evoluiu ao longo da
   conversa — descartadas as ideias intermediárias de dois "modos"
   single/comparativo e de tabelas separadas):** um único botão
   "Comparar", no mesmo padrão dos botões já existentes (Buscar do
   Banco, Calcular por Regressão). Ao clicar, avalia o modelo
   exatamente nos x1 da tabela (não na malha genérica de 101 pontos
   usada para desenhar a curva do "Gerar Gráfico"), plota essa curva
   "calculado nos pontos experimentais" junto da já existente, em cor
   diferente, e calcula o erro. **Habilitação do botão:** apagado/não
   clicável quando não há dado experimental de verdade na tabela
   (digitado ou importado via CSV) para comparar contra; aceso/
   clicável assim que houver — mesmo padrão visual de estado
   habilitado/desabilitado que qualquer botão desabilitado já usa no
   Flet, sem componente novo.
   **Parte visual implementada e testada em 2026-09-27** — o autor
   liberou explicitamente a parte visual adiantada, deixando só o
   número do erro para depois ("já podemos implementar o botão para
   visualizar... e depois adicionar a parte do erro"). Em
   `calculos/gemini.py`: `calculate_vle_isothermal` ganhou o parâmetro
   opcional `x1_values` (default `None` → comportamento antigo
   inalterado; passado → usa esses x1 em vez da malha de 101 pontos).
   Em `fletando_grafico.py`: botão "Comparar" (`calcular_comparativo`),
   habilitado/desabilitado dentro de `gerar_grafico` conforme haja ou
   não ponto experimental válido na tabela; ao clicar, adiciona duas
   séries novas ao gráfico P-x-y existente — "líquido — comparativo"
   (roxo) e "vapor — comparativo" (ciano) — calculadas nos x1 exatos da
   tabela, com chips de legenda próprios que só aparecem depois do
   clique. `gerar_grafico` limpa essas séries/chips sempre que
   reconstrói o gráfico do zero, pra não sobrar comparação desatualizada
   em relação a modelo/tabela/componentes novos. Mensagem de status após
   o clique já avisa que o erro em si ainda não foi calculado. Validado:
   suíte de testes completa + UI rodando de verdade (botão apagado sem
   dado experimental, aceso e funcional com 1 ponto digitado, série
   comparativa e legenda aparecendo corretamente).
   **Métrica do erro implementada em 2026-09-27** — revertendo a
   decisão anterior de não decidir isso sozinho: o autor pediu
   explicitamente para implementar a sugestão do Claude Code em vez de
   aguardar a orientação do Dr. Filipe ("implemente sua sugestão e
   guarde esses argumentos pra justificar"). Dois números separados
   (não um resíduo combinado), mostrados em `mensagem_status` depois de
   "Comparar":
   - **ΔP relativo (%), RMS** —
     `sqrt(mean(((P_calc−P_exp)/P_exp)²)) × 100`. Relativo é seguro
     aqui porque P nunca passa perto de zero.
   - **Δy absoluto (fração molar), RMS** —
     `sqrt(mean((y_calc−y_exp)²))`. Tem que ser absoluto, não
     relativo: y passa por 0/1 nas bordas de composição, e erro
     relativo em y sofreria a mesma amplificação de ruído perto das
     bordas que já descartou o método indireto de regressão (seção
     2.8).
   **Por que separado em vez de um resíduo combinado** como o
   `residual_rms` de `regress_params_barker`: é assim que ajuste de
   modelo Gᴱ é reportado na literatura de termodinâmica (ex.:
   compilações DECHEMA/Gmehling) — cada grandeza testa uma parte
   diferente da física (P testa o desvio da idealidade como um todo; y
   é mais sensível a erro em componente individual). Um resíduo
   combinado esconde esse tipo de nuance — confirmado ao validar com o
   dataset real etanol/água a 50°C
   (`referencias/etanol_agua_50C_isotermico.csv`): NRTL com parâmetros-
   chute deu ΔP=29,4%/Δy=0,065; os mesmos parâmetros ajustados por
   Barker deram ΔP=6,2%/Δy=0,106 — Barker melhora P mas piora um pouco
   y, porque otimiza o resíduo combinado, não y sozinho. Esse trade-off
   só fica visível porque os dois números são reportados separados, não
   combinados num só.
   Posicionamento fino/estilo visual do botão e da exibição do erro
   ganharam ícone ⓘ com explicação (2026-09-27, ajustado para diálogo ao
   toque em 2026-09-28 — ver "Decisões de engenharia do aluno"). O
   restante do acabamento visual segue para a fase de estética, cujo
   escopo foi ampliado em 2026-09-28 para a interface inteira, não só
   este item (ver mesma seção).

## Atualizações futuras (pós-projeto piloto)

Criada em 2026-09-13. Ideias explicitamente **adiadas para depois da
entrega do TCC** — não fazem parte do escopo do projeto piloto e não
devem ser implementadas sem novo pedido explícito do autor, mesmo que
pareçam pequenas. Diferem de "Próximos passos": aquela lista é o que
falta para o piloto funcionar; esta é o que vem **depois**, se o projeto
continuar sendo mantido.

- **α12 do NRTL não fixo.** Hoje decidido como fixo (seção "Próximos
  passos", item 3), por simplicidade e estabilidade numérica com poucos
  pontos experimentais. Se a aplicação amadurecer e passar a lidar com
  tabelas maiores/mais confiáveis (uso de pesquisa, Eixo 3), ajustar os
  três parâmetros do NRTL simultaneamente (ou expor a escolha ao usuário)
  vira uma opção viável a reconsiderar.

- **Modo isobárico (diagrama T-x-y).** Hoje o app só calcula no modo
  isotérmico (`calculate_vle_isothermal`: T fixo, P varia por ponto) —
  não existe função equivalente para P fixo com T variando ponto a
  ponto. Motivado por um dataset real trazido em sessão de trabalho
  (2026-09-27): etanol/água a 101,325 kPa, 14 pontos, T de 100 °C a
  78,15 °C — o clássico VLE isobárico do azeótropo etanol-água a 1 atm.
  Pra comparar o modelo contra esse tipo de dado seria preciso uma
  `calculate_vle_isobaric(comp1, comp2, P_kPa, modelo, params,
  x1_values)` que resolve T por busca de raiz (ex.: `scipy.optimize.
  brentq`) tal que `x1·γ1(T)·Psat1(T) + x2·γ2(T)·Psat2(T) = P`, mais um
  segundo tipo de gráfico/tabela na UI (T-x-y ao lado do P-x-y
  existente) — não é ajuste pequeno, é um segundo modo de diagrama.
  Adiado para depois da entrega do piloto; **não implementar sem pedido
  explícito do autor**.

## Sessão de estética e bug de renderização intermitente (2026-09-28/29)

Sessão longa dedicada à "fase de estética" (autorizada em 2026-09-28, ver
"Decisões de engenharia do aluno" abaixo): tema claro fixo, escala de
espaçamento, cards por seção, layout adaptativo desktop/mobile com
gráficos e "Sistema"/"Parâmetros do modelo" reorganizados, botão
"Desfazer" (histórico de parâmetros), "Limpar Tabela", "Comparar" movido
pro cabeçalho do card, e mais uma dúzia de ajustes finos — tudo em
`interface/fletando_grafico.py`, commits entre `2795aea` e `929ed60`.

### O bug: renderização quebrada, intermitente, no carregamento

No meio dessa sessão, o autor relatou que a página às vezes carregava no
celular mostrando **só o dropdown de modelo**, com uma área cinza/marrom
no lugar de todo o resto — **sem nenhuma interação do usuário**, o
problema já vinha "de fábrica" no carregamento. Investigação seguiu por
eliminação sistemática, com um obstáculo real: o Chromium headless deste
ambiente Termux/proot não renderiza a página de verdade (erros de shader
WebGL/CanvasKit mesmo com software rendering), então boa parte da
depuração dependeu de o autor testar no celular e reportar o resultado.

**Hipóteses testadas e descartadas** (nenhuma resolveu, então nenhuma era
a causa raiz):
- Filtro de caracteres da tabela (`ft.InputFilter`) — suspeito inicial
  por ser o recurso mais novo/exótico; revertido para filtro em Python
  puro (`on_change`) de qualquer forma, por ser mais simples.
- Quebra de linha ausente no cabeçalho do card (Row sem `wrap=True`) —
  bug real por si só (corrigido), mas não a causa deste problema.
- Número de linhas iniciais da tabela (10 vs. 1).
- Botão "Desfazer" e o mecanismo `extra_titulo` do cabeçalho do card,
  isolados via bisseção de código.
- `key` estável nos sliders (prática padrão contra bugs de reconciliação
  de listas dinâmicas no Flutter) — mantido por ser boa prática, mas não
  resolveu sozinho.
- Debounce no `on_select` do dropdown (hipótese: seleções rápidas
  disparando atualizações sobrepostas) — descartada quando o autor
  esclareceu que o problema **já aparecia no carregamento**, sem precisar
  tocar no dropdown.
- Juntar duas chamadas `page.update()` seguidas no final da inicialização
  em uma só.
- Trocar o motor de renderização web de CanvasKit/WebGL para HTML puro
  (editando `webRenderer` no template do pacote `flet_web` instalado, só
  para teste local).
- Cache do navegador (refresh forçado, aba anônima, force-stop do app do
  navegador) — descartado porque o problema persistia mesmo assim.
- Túnel público (`localtunnel`) como causa — descartado testando via
  `http://localhost:PORTA` direto no celular (mesmo aparelho que roda o
  servidor Termux), reproduzindo o mesmo problema sem nenhum túnel no
  meio.

**Confirmação de que não era regressão do dia:** publicadas duas branches
de checkpoint (`checkpoint-mobile-ok-2026-09-28` no commit `153c14e`,
antes da reorganização do layout desktop; `checkpoint-pc-ok-2026-09-28`
no estado então atual) para o autor testar em isolamento. **O bug
reproduziu até na versão antiga**, confirmando que era um problema
pré-existente, não introduzido pelas mudanças de estética — e o autor
relatou já ter visto esse mesmo tipo de trava antes, "como se fosse um
erro do Flet mesmo". As branches foram apagadas depois de servirem seu
propósito (os commits continuam no histórico normal do branch).

**Causa isolada por eliminação:** o trecho de `montar_layout` que ajustava
a largura dos campos de componente/temperatura conforme desktop ou
mobile **mutava propriedades (`width`, `expand`) de `TextField`s já
criados**, bem no momento da primeira montagem da página. Era o único
lugar do app inteiro que fazia isso — todo o resto do código sempre cria
controles novos a cada reconstrução, nunca muda propriedades de layout de
um controle já existente. Desativar esse trecho (isolado por bisseção,
testando peça por peça) foi a única mudança, dentre todas as testadas,
que consistentemente resolveu o problema — confirmado pelo autor em
múltiplas recargas, no celular e no PC.

**Diagnóstico:** não foi possível confirmar a causa raiz exata do lado do
Flutter (exigiria investigar o código-fonte Dart do framework), mas o
padrão é consistente com uma falha de sincronização interna do Flet/
Flutter ao mutar propriedades de um controle exatamente no momento em
que ele é anexado à árvore da página pela primeira vez — não um erro de
lógica desta aplicação.

**Correção aplicada:** os campos de componente/temperatura voltaram a ter
largura fixa (220px) sempre, sem o ajuste dinâmico. **Custo aceito:**
perda do ajuste fino ao card "Sistema" mais estreito no desktop (efeito
cosmético — os campos não preenchem toda a largura disponível), em troca
de não quebrar a renderização. Mantidos como reforços de robustez, mesmo
não sendo a causa raiz: `key` estável nos sliders/texto do card
"Parâmetros do modelo", e parâmetros `atualizar`/`atualizar_pagina` em
`adicionar_linha`/`gerar_grafico` para suprimir `page.update()` em
chamadas de lote (menos tráfego desnecessário, mesmo não tendo sido a
causa deste bug específico).

**Lição de processo para a banca:** o ambiente de desenvolvimento
(Termux/proot) não permite verificação visual confiável do app rodando
— nem localmente (Chromium headless quebrado) nem sempre via túnel
(serviço gratuito instável). A depuração deste bug dependeu inteiramente
de reportes do autor testando no dispositivo real, com bisseção de
código guiada por hipóteses e eliminação sistemática — um exemplo
concreto de como a cadeia de validação (seção 5.2 do mapeamento) funciona
na prática quando a ferramenta de IA não tem como verificar o resultado
sozinha.

> **Ressalva acrescentada em 2026-10-01:** o parágrafo acima continua
> verdadeiro **para o ambiente Termux**, que segue sem renderização
> confiável. Deixou de ser verdadeiro para o projeto como um todo: em
> 2026-09-30 montou-se, no ambiente de nuvem do Claude Code, uma captura
> de tela que funciona (ver sessão seguinte). Os reportes do autor no
> aparelho real continuam sendo a palavra final — mas não são mais a
> única fonte de evidência visual.

## Sessão de verificação visual, lixeira no celular e modo de exibição (2026-09-30/10-01)

Sessão que começou com uma pergunta do autor — "como fazer com que você
consiga ver mais precisamente o resultado das alterações?" — e acabou
achando e corrigindo uma funcionalidade perdida no celular.

### A captura de tela no ambiente de nuvem

Ao contrário do Termux, o ambiente de nuvem do Claude Code **consegue**
renderizar o app e fotografar o resultado. Três obstáculos tiveram que ser
contornados, todos sem afrouxar nenhuma verificação de segurança:

1. **CanvasKit/Skia vem de `www.gstatic.com`**, host bloqueado ali. Os
   mesmos arquivos existem em disco, dentro do pacote `flet_web`
   instalado — a requisição é interceptada e servida do disco. (É o mesmo
   fato técnico já registrado na nota do Flet 1.0.0, agora explorado a
   favor.)
2. **As fontes vinham erradas.** Na primeira tentativa o `fonts.gstatic.com`
   foi bloqueado por precaução, e o Flutter caiu numa serifa de fallback
   com acentos e γ faltando — prints inúteis justamente para julgar
   tipografia. O host responde normalmente; o que falha é o Chromium não
   confiar no certificado do proxy do ambiente. Em vez de desligar a
   verificação de TLS do navegador, cada fonte é baixada com `curl` (que
   usa o CA correto), guardada em cache e servida do disco.
3. **`fullPage` não funciona com Flutter**, que pinta tudo num `<canvas>`
   do tamanho da viewport; e a página pode ser fotografada antes da
   primeira pintura, saindo em branco. Resolvido com viewport alta o
   suficiente para a página caber inteira e uma espera que só captura
   depois que a tela deixa de estar em branco, com várias tentativas —
   salvaguarda que já pegou um caso real de página que só pintou na
   segunda tentativa.

**O que a ferramenta não faz:** não interage. Como o Flutter desenha no
canvas, não há texto no DOM para procurar — só clique por coordenada
calculada. Ela enxerga o estado de carregamento, que já traz as duas
curvas do modelo, mas não pontos experimentais nem a comparação. E não
ajuda no Termux, onde o problema continua.

**Duas armadilhas da própria ferramenta**, registradas porque fazem uma
verificação *parecer* confiável sem ser: (a) `pkill -f "fletando_grafico"`
mata o próprio shell que o executa, porque o padrão casa com a linha de
comando dele — resolvido com o truque do colchete, `[f]letando_grafico`;
(b) `flet run` deixa um processo filho com outra linha de comando, que
sobrevive ao encerramento do pai e continua servindo o código antigo —
chegou a produzir um print "provando" que uma correção não funcionava
quando ela nem tinha subido. Sempre conferir quantas instâncias restam
antes de capturar.

### O achado: não dava para excluir um ponto pelo celular

Com a página inteira visível no modo celular, apareceu o que nenhuma
leitura de código tinha mostrado: **a coluna da lixeira não existia**.
Medido objetivamente, varrendo seis larguras e contando blocos de pixel
vermelho forte (a cor do ícone de excluir; o texto de aviso é laranja e
não entra no filtro):

| Largura | Antes da correção |
|---|---|
| 360 px | nenhuma lixeira |
| 390 px | nenhuma lixeira |
| 430 px | 10, mas desenhadas **fora** do card |
| 500 / 600 / 800 px | 10, na borda do card |

**Causa:** a `DataTable` tem largura própria de ~440px, sendo quase metade
só espaço vazio (o padrão do Material reserva 56px entre colunas e 24px
nas bordas; o conteúdo real — 3 campos de 60px mais a lixeira — soma
~228px). No celular o card oferece ~296px úteis, então a quarta coluna
caía fora. **Rolagem horizontal não alcançava**: testado com roda e com
arrasto, a imagem ficou idêntica — coerente com o código, já que `dt` é
filho direto da `Column` do card, e com o registro de que embrulhar `dt`
num contêiner rolável quebrou a renderização do ícone em 2026-09-28.

Efeito prático: no dispositivo principal de uso, restavam "Limpar Tabela"
(que apaga tudo) ou invalidar a linha na mão — nenhum dos dois é excluir
aquele ponto.

### A correção, e por que não foi a que se cogitou primeiro

A conversa tinha caminhado para um redesenho da apresentação da tabela no
celular. A medição mostrou que bastava **apertar o espaçamento**
(`column_spacing` 56→16, `horizontal_margin` 24→8): commit `0551055`. As
10 lixeiras passaram a aparecer dentro do card em todas as larguras
testadas, inclusive 360px, e o autor confirmou no aparelho real, pelo
Termux. Com isso o redesenho foi **descartado** (ver decisões abaixo).

Valor único de espaçamento para os dois modos, de propósito: ajustá-lo
conforme desktop/mobile exigiria mutar propriedade de controle já criado
— o gatilho do bug de renderização de 2026-09-28.

**Efeito colateral cosmético, não tratado:** a tabela agora é mais estreita
que o card, sobrando um vão à direita, mais visível no desktop (card de
420px fixos).

### O botão de alternar modo de exibição

Commit `191b4c4`. A detecção automática por largura continua sendo o
padrão; o botão apenas a sobrepõe, e a escolha manual passa a mandar — um
resize não a desfaz. O botão é criado novo a cada montagem, junto com os
cards, em vez de ser um controle fixo com ícone/rótulo trocados a cada
clique: mesmo motivo de sempre, este app não muta propriedade de controle
já criado.

**Correção de rumo no meio da implementação:** a primeira versão empilhava
os cards mas deixava eles esticando pelos 1400px do monitor — tecnicamente
o layout mobile, mas inútil como previsão. Acrescentado um limite de 420px
centralizado, que **só entra quando há janela sobrando**; num telefone de
verdade a condição é falsa e o empilhamento fica idêntico ao já validado.

Verificado por captura de tela (ida e volta a 1400px, com o rótulo do botão
invertendo a cada clique; e a 390px o botão presente sem a moldura de
simulação) e confirmado pelo autor no aparelho — inclusive ao ligar o
"Modo para PC" nas configurações do navegador do celular, caso em que a
largura reportada cresce, a detecção automática escolhe desktop e o botão
continua permitindo forçar o celular. Esse teste confirma a decisão de
deixar o manual sobrepor o automático: no desenho inverso, o modo ficaria
pulando.

### Itens de estética levantados e ainda não atacados

Levantados por leitura de código e pelos prints, **sem autorização ainda**:

1. ~~A tabela não diz a unidade de P. O cabeçalho é só `P`, mas o cálculo
   trabalha em kPa e `calcular_comparativo` divide P calculado por P
   experimental direto — digitar mmHg ou bar produz ΔP sem sentido, sem
   nenhum aviso.~~ **Feito em 2026-10-01** (commit `9eb6a0c`): cabeçalho
   `P (kPa)`.
2. ~~Os dois gráficos não têm rótulo de eixo (`ChartAxis` aceita
   `title`).~~ **Feito em 2026-10-01** (commit `9eb6a0c`): rótulos nos
   eixos dos dois gráficos.
3. ~~O dado experimental é desenhado como linha, e mais grossa que a
   curva do modelo (`stroke_width` 3 contra 2) — o inverso de "dado é
   ponto, modelo é linha". É a pendência que a decisão de 2026-08-19
   deixou explicitamente em aberto para quando a curva do modelo
   dividisse o gráfico com os pontos.~~ **Feito em 2026-10-03** (opção C
   escolhida pelo autor, ver "Decisões de engenharia do aluno"): só
   marcadores, sem linha — quadrado azul = líquido (`ChartSquarePoint`,
   8px), círculo vermelho = vapor (`ChartCirclePoint`, raio 4,5px) — com
   `stroke_width=0` escondendo a linha; chip da legenda do líquido virou
   quadrado. Verificado por captura de tela com o CSV de etanol/água,
   inclusive o tooltip (continua aparecendo ao passar o cursor sobre os
   marcadores, sem a linha). *(Cores revistas no item 4: o vapor deixou
   de ser vermelho e passou a laranja.)*
4. ~~Seis cores de série sem relação entre si; e o vermelho, que no app
   já significa erro e exclusão, é também uma série de dados.~~ **Feito em
   2026-10-03** (opção A com marcadores vazados, escolhida pelo autor — ver
   "Decisões de engenharia do aluno"): **a cor identifica a fase e o estilo
   identifica a origem.** P-x-y: líquido azul (`COR_LIQUIDO`, `BLUE_700`) e
   vapor laranja (`COR_VAPOR`, `ORANGE_800`); marcador cheio = tabela
   (quadrado/círculo), linha contínua = modelo, **marcador vazado** =
   modelo calculado nos x1 da tabela ("Comparar", sem linha). ln γ: γ1
   verde (`COR_GAMMA1`) e γ2 roxo (`COR_GAMMA2`), modelo em linha e
   comparativo em círculos vazados. O vermelho ficou só para erro/exclusão.
   `glifo_legenda(cor, forma)` espelha o estilo da série (`circulo`,
   `quadrado`, `linha`, `quadrado_vazado`, `circulo_vazado`) na legenda —
   que, desde o item 7, é uma grade fase × origem.
   Verificado por captura de tela com o CSV de etanol/água: os marcadores
   vazados caem sobre as curvas do modelo e a distância vertical até os
   marcadores cheios é o erro. **Achado novo, vai para o item 7:** com a
   comparação ativa a legenda do P-x-y tem três linhas e a terceira
   encosta no "78" do topo do eixo vertical (altura fixa
   `ALTURA_LEGENDA = 64` não comporta) — era o "S" solto visto antes.
5. ~~O app não tem nome nem cabeçalho visível (`page.title` ainda é
   "Fletando - Gráfico Dinâmico", nome de desenvolvimento).~~ **Feito em
   2026-10-03** (opção H2 escolhida pelo autor, ver "Decisões de engenharia
   do aluno"): faixa azul (`BLUE_700`, cantos de 12px) no topo com o nome
   **VLE Interativo**, o subtítulo "Equilíbrio líquido-vapor com modelos de
   Gᴱ" e o crédito "UFC"; `page.title` passou a "VLE Interativo". O botão
   de modo de exibição foi para dentro da faixa, com fundo branco
   translúcido (18%) para se destacar (pedido do autor). Desktop: título à
   esquerda, crédito e botão à direita; celular: título, subtítulo e, na
   linha de baixo, crédito e botão. Faixa criada nova a cada `montar_layout`
   (regra de não mutar controle criado). Verificado por captura de tela a
   1400px e a 390px. **Ressalva:** o "ᴱ" do subtítulo sai bem pequeno na
   fonte renderizada (glifo sobrescrito Unicode), legível mas discreto.
6. Tamanhos de fonte contra o requisito de projeção da seção 1.4: a nota
   do α12 é 11px, itálico, cinza sobre branco.
7. ~~`ALTURA_LEGENDA = 64` é paliativo e vira espaço morto no card do ln
   γ. Agravante achado no item 4: com "Comparar" ativo a legenda do P-x-y
   passa a três linhas e invade o topo do eixo vertical.~~ **Feito em
   2026-10-03** (opção B escolhida pelo autor, ver "Decisões de engenharia
   do aluno"): a legenda de chips que quebrava linha virou uma **grade**
   — linhas = fase (líquido/vapor; ln γ1/ln γ2), colunas = origem (tabela,
   modelo, comparativo) —, sempre com três linhas (cabeçalho + 2). Helpers
   `glifo_legenda`, `celula_legenda` e `coluna_legenda`; a coluna
   "comparativo" de cada gráfico (`coluna_comparativo_pxy`,
   `coluna_comparativo_gamma`) só aparece depois de "Comparar".
   `ALTURA_LEGENDA` passou de 64 para 72 e comporta as duas legendas em
   qualquer largura. Larguras de coluna fixas (56+60+60+84 + 3×4 de
   espaçamento ≈ 272px) para caber no card do celular. Verificado por
   captura de tela a 1400px e a 390px, com "Comparar" ativo: os dois
   cards ficam do mesmo tamanho, sem espaço morto, e o rótulo do topo do
   eixo vertical deixa de ser coberto. **Achado novo, corrigido na
   sequência (2026-10-03):** a 390px a linha "ΔP = … / Δy = …" do rodapé do
   card "Dados experimentais" passava da borda direita do card; a
   `linha_erro_comparativo` ganhou `wrap=True` e agora o Δy desce para a
   linha de baixo, dentro do card.
8. ~~Achado nos prints: os rótulos de mínimo/máximo dos eixos colidem com
   a escala regular (claro no ln γ, onde "-0.05" quebra em duas linhas por
   cima do "0.00").~~ **Feito em 2026-10-03:** os limites do eixo vertical
   (antes `min − 10%` / `max + 10%`, valores "quebrados" como 27.1 e 76.1)
   passam por `limites_redondos(vmin, vmax)`, que devolve início/fim
   múltiplos de um passo em 1, 2, 2.5 ou 5 × 10^k (cerca de 7 intervalos), e
   o eixo é recriado com esse `label_spacing` por `eixo_vertical(titulo,
   passo)` — novo a cada `gerar_grafico`, sem mutar eixo existente. Com os
   extremos sobre múltiplos do passo, o rótulo do extremo coincide com um
   marcador regular. Verificado por captura de tela: P de 0 a 80 de 10 em
   10; ln γ de −0,10 a 0,60 de 0,10 em 0,10. **Defeito residual achado e
   corrigido no mesmo dia (relatado pelo autor como "o gamma não renderiza
   correto"):** no gráfico de ln γ o rótulo "−0,10" quebrava em duas linhas
   ("-0.1" / "0") porque a coluna de rótulos (40px) era estreita demais, e
   o "0.60" do topo saía em negrito, desenhado duas vezes — o último
   marcador sai como 0.6000000000000001 (ruído de `inicio + k·passo`),
   diferente do máximo 0.6, então o extremo e o marcador regular não se
   fundiam. Correção em `eixo_vertical`: `label_size` 52px para o ln γ
   (`largura_rotulo`), `show_min`/`show_max` desligados, e
   `margem_extremos` abre os limites em 0,2% do passo (invisível) para o
   marcador exato do extremo cair dentro do intervalo e ser desenhado uma
   vez só. Nota: ligar só `show_min`/`show_max` sem essa folga fazia os
   rótulos dos extremos sumirem.
9. ~~Achado nos prints: a mensagem laranja "10 linha(s) da tabela
   ignorada(s) por dado inválido" aparece **no carregamento, com a tabela
   vazia** — linha em branco está sendo contada como dado inválido.~~
   **Feito em 2026-10-03:** em `gerar_grafico`, linha com os 3 campos
   vazios deixou de entrar na contagem; só conta como "ignorada" a linha
   com algum campo preenchido que não vira número. Antes/depois simulados:
   tabela vazia 10 → 0 avisos; 1 linha inválida + 9 em branco 10 → 1;
   1 válida + 1 inválida + 8 em branco 9 → 1. Confirmado também na tela
   (captura da nuvem, sem a mensagem laranja no carregamento).

## Sessão de ajustes no PC: card Sistema, tooltip e importação de CSV (2026-10-03)

Primeira sessão com o app rodando no PC do autor (Windows, Chrome,
Python 3.13, `uv run flet run interface/fletando_grafico.py --web --port
5000`), em vez de só no celular via Termux. Quatro coisas saíram dela, todas
em `interface/fletando_grafico.py`.

### 1. Card "Sistema" em grade 2×2 (commit `6b253a7`)

No desktop o card "Sistema" divide a linha com "Parâmetros do modelo" e
fica com ~400-450px úteis. Os quatro controles (dropdown de modelo,
Componente 1, Componente 2, Temperatura) tinham 220px fixos: dois lado a
lado (~452px) não cabiam, então cada um caía numa linha própria — o
dropdown à esquerda e os campos com `alignment=CENTER`, num degrau sem
harmonia (relatado pelo autor). Agora: **componentes em cima, modelo e
temperatura embaixo**, alinhados à esquerda, com largura única
`LARGURA_CAMPO_SISTEMA = 190` definida na criação (duas linhas `ft.Row`
com `wrap=True`). No celular, onde dois não cabem, cada um vai para uma
linha própria, também à esquerda. **A largura é definida na criação, nunca
mutada depois** — mesma regra do bug de renderização de 2026-09-28.
Alternativa descartada pelo autor: coluna única com 220px (mais simples,
mas deixava um vão à direita no card). Verificado por captura de tela da
nuvem (1400px): a grade aparece como desenhada.

### 2. Tooltip dos pontos nos gráficos (commits `601b5b3`, `1e099eb`, `3df887d`, `c53b46f`)

O tooltip padrão do Flet mostra só o valor de y, como float inteiro (ex.:
`45.234871620938`). Em quatro passos, a pedidos do autor:

1. **Algarismos significativos:** `formatar_valor` (4 algarismos, sem
   notação científica; ruído de ponto flutuante < 1e-9 vira `0`; NaN/inf
   passam como texto, sem estourar o `log10`).
2. **x, nome e unidade:** `ponto_grafico(x, y, nome_x, nome_y, unidade_y)`
   — `x1` na curva do líquido, `y1` na do vapor (o eixo horizontal do
   P-x-y carrega as duas composições), `P ... kPa`; no gráfico de ln γ,
   `x1` e `ln γ1`/`ln γ2`, sem unidade.
3. **Duas linhas** (`\n`), com x em cima e y embaixo.
4. **Alinhado à esquerda** (`text_align=START`; o padrão do Flet é
   `CENTER`).

Resultado: `x1 = 0.3500` / `P = 45.23 kPa`. Vale para todas as séries
(tabela, modelo, comparativo). O balão em si só o autor vê no navegador —
a captura de tela da nuvem não passa o cursor sobre os pontos.

### 3. Erro ao importar CSV: "Timeout waiting for invoke method listener" (commit `e1004b3`)

No PC, "Importar CSV" falhou **sempre**, com a tela de erro do Flet:
`TimeoutException after 0:00:10 ... Timeout waiting for invoke method
listener for FilePicker(112).pick_files`. O traceback mostra o lado do
navegador dizendo que não tinha o serviço do seletor registrado.

**Tentativa de reprodução na nuvem, sem sucesso:** Chromium 141 (que usa o
mesmo build WebAssembly do Flutter que o Chrome), Linux, Python 3.11 **e**
3.13, página recém-aberta **e** aba aberta durante reinício do servidor —
em todos os casos o seletor abriu, o CSV de etanol/água carregou e a tabela
e os gráficos foram preenchidos, sem erro no log. Descartadas como causa a
versão do Python (suspeita levantada pelo assistente: o formato do
traceback indicava 3.13 ou mais novo)
e uma aba antiga religada ao servidor novo. Hipótese seguinte (cache do
service worker do cliente Flet no `localhost:5000`) foi proposta ao autor
com um teste de janela anônima.

**Desfecho:** o autor deu `F5` e **funcionou normalmente**. Causa raiz
**não identificada** — o estado do lado do navegador (carregamento
incompleto ou sessão antiga) é a explicação mais provável, mas não foi
provada. Parente do bug de carregamento intermitente de 2026-09-28
(também um serviço/controle que o navegador não montava).

**O que ficou no código:** `importar_csv` captura `RuntimeError`/
`TimeoutError` e mostra na tabela "Não foi possível abrir o seletor de
arquivos (o navegador não respondeu). Recarregue a página (F5) e tente de
novo." — em vez da tela de erro. Não corrige a causa; só troca um erro
assustador por uma instrução. Validado por simulação da falha.

### 4. Atualização da ferramenta de captura de tela da nuvem

Reaproveitada nesta sessão, com três achados novos: (a) o Chromium
automatizado precisa de `locale: 'en-US'`, senão o Flutter falha com
`RangeError: Incorrect locale information provided`; (b) o app carrega o
build **WebAssembly** (`main.dart.wasm`, skwasm), com `crossOriginIsolated`
verdadeiro; (c) o seletor de arquivo **dá para exercitar**:
`page.waitForEvent('filechooser')` depois de um clique por coordenada,
seguido de `chooser.setFiles(...)`. Isso atualiza o limite registrado em
2026-09-30 ("não interage") — agora a importação de CSV pode ser testada de
ponta a ponta, ainda por coordenada. **Correção da ferramenta, feita mais
tarde no mesmo dia:** as capturas dessa sessão feitas sem servir as fontes
reais (bloqueando `fonts.gstatic.com` em vez de baixá-las com `curl`)
mostravam o "γ" como um quadrado e acentos trocados — artefato do ambiente
de captura, não do app, e foi isso que gerou a dúvida sobre o γ. A
ferramenta passou a baixar as fontes com `curl` (que confia no CA do proxy)
e a servi-las do disco, como já registrado na sessão de 2026-09-30; com ela,
o γ sai correto e dá para julgar índices e tipografia. O item 9 da lista acima (mensagem
laranja "10 linha(s) ... ignorada(s)" com a tabela vazia no carregamento)
aparecia nos prints desta sessão e foi **corrigido na sequência** (ver o
próprio item 9).

### 5. Índices como subscritos (2026-10-03)

Pedido do autor: "os índices quero como índices, e não como apenas 1 e 2
normal". Todo índice visível passou a usar os subscritos Unicode `₁` e `₂`
(em vez de `1` e `2` na linha): `x₁`, `y₁` (cabeçalhos da tabela, títulos de
eixo, tooltip), `ln γ₁`/`ln γ₂` (legenda e tooltip), rótulos dos sliders
(`A₁₂`, `A₂₁`, `Λ₁₂`, `Λ₂₁`, `τ₁₂`, `τ₂₁`, `α₁₂`) e as duas notas de texto
(`α₁₂`, `a₁₂/a₂₁`). Unicode, e não texto formatado, porque o tooltip e o
título de eixo do gráfico são desenhados pelo Flutter como texto simples.
Chaves internas (`"x1"`, `tau12`, `A12`…) não mudaram. Verificado por
captura de tela com as fontes reais: os subscritos aparecem corretos.

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
  nenhum banco cobre todo par possível. Decisão: ajustar o modelo por
  regressão não-linear a partir dos pontos (P, x, y) digitados. Insight
  do autor, não sugestão do assistente. Reformula a antiga pendência do
  Van Laar em capacidade geral (seção 2.8 do mapeamento).
- **(2026-09-13) Método de redução: Barker (direto), não o indireto.**
  Entre ajustar o modelo contra γ "experimental" calculado ponto a ponto
  (invertendo Raoult) ou contra o resíduo de P e y diretamente (Barker),
  o autor escolheu Barker — mais rigoroso estatisticamente, pois trata o
  erro no espaço onde ele foi medido (P, y) em vez de propagá-lo por uma
  divisão que amplifica ruído perto das bordas de composição. Antes de
  decidir, o autor levantou a preocupação de que o custo computacional
  extra do Barker (otimização aninhada) pudesse se somar a outros custos
  futuros e prejudicar a fluidez da aplicação — preocupação analisada e
  descartada: pelo tamanho de tabela esperado (dezenas de pontos), a
  regressão fica na casa de milissegundos, irrelevante perto do custo de
  renderizar o gráfico, que independe do método escolhido.
- **(2026-09-12) Exigir que a aplicação declare a origem de cada
  parâmetro.** Requisito de transparência científica levantado pelo
  autor: quem usa precisa saber se está vendo valor fornecido, de banco,
  ou regredido de poucos pontos, **antes** de tirar conclusão do gráfico.
  Um parâmetro ajustado a 5 pontos digitados e um parâmetro medido e
  publicado não têm a mesma força, e a interface não pode apagar essa
  diferença.
- **(2026-09-13) Fixar α12 do NRTL na regressão, com nota explicativa
  obrigatória.** Entre fixar α num valor convencional (ajustando só
  τ12/τ21) ou tentar ajustar os três parâmetros simultaneamente, o autor
  escolheu fixar — mesmo raciocínio de mau-condicionamento já aplicado ao
  método de Barker. Mas exigiu que isso não fique escondido: a mesma
  transparência de origem do parâmetro (item acima) se aplica aqui —
  reaproveita o padrão selo+ícone ⓘ para avisar que α foi fixado por
  convenção, não regredido.
- **(2026-09-13) Mínimo de pontos para a regressão: nº de parâmetros do
  modelo + 1.** Fechando o assunto que ele mesmo levantou (por que um
  mínimo é necessário), o autor estabeleceu o piso concreto — abaixo
  disso a regressão não tem grau de liberdade nenhum, encaixando a curva
  exatamente nos pontos sem nenhuma evidência de que o modelo descreve o
  sistema fora deles. No limite exato, o selo de origem ganha uma
  variante de baixa confiança ("Calculado, poucos pontos"), estendendo o
  padrão já definido em vez de criar um novo.
- **(2026-09-21) Gatilho da regressão: manual, reaproveitando o botão
  "Gerar Gráfico" já existente.** Decisão tomada numa sessão em que
  `fletando_grafico.py` ainda estava na "Etapa 2" (sem regressão
  implementada): em vez de tornar a regressão automática e criar dois
  comportamentos diferentes no mesmo app, o autor preferiu manter o
  padrão que já existia — um clique só, produzindo pontos e curva
  calculada juntos. **Superada em 2026-09-27** (ver entrada abaixo): a
  regressão acabou sendo construída em paralelo, em outro branch, antes
  de essa intenção virar código — quando os dois branches foram
  integrados, o desenho que já existia implementado e testado (botão
  dedicado) foi o que ficou.
- **(2026-09-27) Implementar agora o selo de origem, sem mais adiar.**
  Depois de liberar só o motor de cálculo + botão de regressão em
  2026-09-13/-2026-09-26 ("sem selo por agora"), o autor decidiu fechar
  essa pendência: "implemente agora o selo de origem". Cobre os quatro
  modelos com slider manual, mais UNIQUAC/UNIFAC com selo fixo.
- **(2026-09-27) Expor a busca no banco IPDB como opção ao usuário,
  para NRTL e Wilson.** Fechando o item 2 do roadmap (em aberto desde
  julho/2026): "em 2) vamos expor as opções pro usuário escolher".
  Adicionado `wilson_params_from_ipdb` (novo adaptador, mesma lógica de
  `nrtl_params_from_ipdb`) e um botão na UI que busca no banco em vez de
  exigir digitação manual — sem substituir o manual, só oferecendo a
  alternativa.
- **(2026-09-27) Gatilho da regressão de Barker: manual, botão
  dedicado.** Fechando a pendência deixada em aberto em 2026-09-13
  ("segue em aberto: gatilho automático vs. manual"): "3) deixa
  manual". Construído (nesta sessão, em paralelo à decisão de
  2026-09-21 acima) como botão dedicado "Calcular por Regressão
  (Barker)", separado do "Gerar Gráfico" — esse foi o desenho que
  prevaleceu na integração dos dois branches.
- **(2026-09-27) Integrar o branch da migração para Flet 1.0.0 (main)
  com o branch da regressão de Barker/selo de origem
  (`claude/opusplan-model-8nreog`).** Os dois avançaram em paralelo sem
  se comunicar — descoberto quando o autor foi checar, numa conversa
  separada, se a migração (que ele lembrava de ter autorizado) estava
  registrada. Autorizado o merge (`git merge origin/main`); único
  conflito de conteúdo foi nesta seção do CLAUDE.md (as duas entradas
  de "gatilho da regressão" acima), resolvido preservando as duas como
  registro histórico e marcando qual desenho de fato foi implementado.
- **(2026-09-27) Comparação calculado-vs-experimental: um botão só, não
  dois "modos".** Depois de cogitar (em conversa) dois modos
  single/comparativo com tabelas separadas, o autor simplificou:
  um único botão "Comparar", que só faz sentido — e só fica clicável —
  quando há dado experimental de verdade na tabela. Ideia dele, não
  sugestão do assistente. Na sequência, autorizou implementar a parte
  visual (botão + curva comparativa nos x1 exatos da tabela) desde já,
  deixando o cálculo do erro para depois da orientação do Dr. Filipe
  sobre a métrica — separando o que dependia dele do que não dependia.
- **(2026-09-27) Métrica do erro: implementar a sugestão do Claude Code
  agora, sem esperar o Dr. Filipe.** Diferente das outras entradas desta
  seção, a fórmula em si (ΔP relativo % + Δy absoluto, separados, RMS —
  ver "Próximos passos", item 4) foi sugestão do assistente, pedida
  explicitamente pelo autor ("me diga qual faz mais sentido... a luz
  dessa parte da disciplina de termodinâmica"); a **decisão** de seguir
  com ela em vez de aguardar o orientador, e de registrar o porquê no
  `CLAUDE.md`, foi do autor ("implemente sua sugestão e guarde esses
  argumentos pra justificar"). Reverte a postura de 2026-09-27 (entrada
  acima) de não decidir isso sozinho — se o Dr. Filipe pedir outra
  métrica depois, é revisão, não reescrita do zero (a estrutura de dois
  números separados por ponto continua igual, só a fórmula mudaria).

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
  em linha com o "entregar funcionando" do orientador. Na época da
  decisão, o Flet ainda era beta — risco aceito conscientemente, não
  ignorado (ver discussão da época). **Atualização factual (não é
  decisão do autor, é evento externo): em 2026-09-20 o Flet lançou a
  versão 1.0**, deixando de ser beta. Não muda a decisão, remove o risco
  que ela havia aceitado.
- **Recusar Flutter nativo (Dart)**: quebraria o processo único (UI e
  cálculo juntos em Python) e exigiria manter um backend separado
  rodando durante a aula. O motivo original também citava "Flutter é
  mais maduro que o Flet, que ainda é beta" — essa parte ficou
  desatualizada com o lançamento do Flet 1.0 (nota acima). A decisão de
  recusar Flutter continua de pé pelo motivo arquitetural, que nunca
  dependeu do status beta do Flet.
- **Recusar embutir um assistente de IA dentro do app** — custo
  recorrente por uso, novo ponto de falha de rede em aula ao vivo, e
  escopo fora dos três eixos do projeto.
- **(2026-09-12) Adotar o padrão selo + ícone ⓘ** para a nota de origem
  do parâmetro (sugestão do Claude Code; a decisão de adotá-la, em vez de
  rodapé fixo ou só ícone flutuante, foi do autor).
- **(2026-10-01) Dois modos de exibição num código só, com botão para
  alternar — recusando a separação em dois códigos.** A ideia original do
  autor foi "códigos diferentes independentes, interligados no mesmo
  ambiente, com o app perguntando se é celular ou computador". Posta a
  conta na mesa — de 1455 linhas do `fletando_grafico.py`, apenas ~180 são
  layout; os outros ~1270 (tabela, CSV, sliders, selo, banco, regressão,
  comparação) são iguais nos dois modos, então "dois códigos" significaria
  duplicá-los ou extrair o comum, que é o que já existe —, o autor
  esclareceu que por "dois códigos" queria dizer **modos de exibição**, e
  adotou a recomendação: um código, lógica compartilhada, um montador de
  layout por modo, e um botão de alternância. Duas escolhas dentro dela
  também foram dele: **botão em vez de pergunta na abertura** (sem atrito
  no caso comum, que importa numa demonstração ao vivo) e **detecção
  automática como padrão, sobreposta pela escolha manual**. Esta última se
  mostrou acertada no teste em aparelho real: ligando o "Modo para PC" do
  navegador do celular, a largura reportada cresce e a detecção automática
  escolhe desktop — no desenho inverso, o modo ficaria pulando.

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
- **(2026-09-21) Alertar via comentário no `pyproject.toml`, não
  automatizar (script/hook/CI), o risco de desalinhamento entre `flet`
  e `flet-charts`.** Avaliando as opções que o assistente levantou
  (script manual, git hook, CI), o autor julgou que a atualização do
  Flet pós-piloto será pontual — talvez nunca aconteça — e o repositório
  não tem CI hoje, então automação seria esforço desproporcional ao
  risco real. Preferiu um alerta simples no ponto exato onde um futuro
  mantenedor (o próprio autor ou outra pessoa, já que o projeto é
  público) mexeria ao atualizar a dependência.
- **(2026-09-21) Autorizar a atualização real para Flet 1.0.0 e exigir
  teste de verdade, não só análise.** Depois de fechar a estratégia de
  alerta acima, o autor decidiu não deixar a migração só documentada —
  pediu para atualizar o código e **testar o funcionamento com o novo
  chart**. Resultado: `flet`/`flet-charts` em `1.0.0`/`1.0.0` sem
  desalinhamento, `ft.NoInputBorder()` corrigido, suíte de testes
  passando, e o app rodado de ponta a ponta num navegador de verdade
  (tabela, botões, `LineChart`) — não apenas leitura de changelog.
  Nota técnica completa acima, com um achado novo que a análise teórica
  não previa (CanvasKit via CDN no navegador, sem opção `--no-cdn` em
  `flet run --web`).
- **(2026-09-28) Trocar tooltip por hover por diálogo ao toque no ícone
  ⓘ.** Testando no celular, o autor percebeu que o `tooltip` nativo do
  Flet (selo de origem do parâmetro, seção 2.8, e o novo ΔP/Δy — ver
  entrada abaixo) depende de hover ou long-press, gesto pouco discoberto
  num dispositivo sem mouse, que é justamente o ambiente de uso real do
  projeto. Entre as opções levantadas (diálogo ao toque vs. texto
  expansível inline), o autor escolheu diálogo — funciona de forma
  idêntica em qualquer dispositivo, sem depender de hover. Aplicado nos
  dois lugares que usavam tooltip: o selo de origem (já existente) e o
  resultado de ΔP/Δy (novo, ver item 4 abaixo).
- **(2026-09-27) Adicionar ícone ⓘ com explicação de ΔP/Δy na
  comparação calculado-vs-experimental.** Pedido do autor, fechando o
  último detalhe de UX do item 4 de "Próximos passos": o resultado
  numérico (`ΔP = X% (RMS)` / `Δy = Y (RMS)`) ganhou um texto sempre
  visível mais um ícone que explica o que cada Δ significa (ver decisão
  acima sobre diálogo vs. tooltip).
- **(2026-09-28) Escopo da "fase de estética": app inteiro, não só o
  item 4.** A entrada de 2026-09-27 sobre o item 4 ("posicionamento
  fino/estilo visual... seguem para a fase de estética") tratava o
  acabamento visual como algo restrito ao botão "Comparar" e à exibição
  do erro. Ao encerrar a etapa de fazer tudo funcionar, o autor decidiu
  que a passada de estética vale para a interface inteira (tabela,
  sliders, gráficos, botões), não só esse item — mudança de escopo em
  relação ao que estava registrado antes.
  **Primeira rodada implementada e validada no mesmo dia** (commit
  `2795aea`): tema claro fixo (independente do modo escuro do
  sistema/navegador, por contraste em projeção — seção 1.4), escala
  única de espaçamento, agrupamento em cards por seção, e — depois de
  duas iterações que só espremiam o padding sem resolver — os dois
  gráficos passaram a ficar lado a lado no desktop em vez de
  empilhados, resolvendo de vez a necessidade de reduzir o zoom do
  navegador pra caber tudo na tela.
- **(2026-09-28) Sincronizar `Docs/mapeamento_e_plano_TCC-1.md` seção 3
  com o código real antes de iniciar a estética.** Verificação de
  conformidade pedida pelo autor revelou que a seção "Estado Atual do
  Código" do mapeamento estava parada em 2026-08-20 e descrevia como
  "não implementado" (CSV, sliders, dropdown, integração com
  `calculate_vle_isothermal`) coisas que já estavam prontas há semanas,
  registradas só no `CLAUDE.md`. O autor autorizou a atualização da
  seção 3 para refletir o estado real antes de seguir para qualquer
  trabalho novo — evita que o documento de prestação de contas para a
  banca fique incoerente com o código.
- **(2026-09-30) Montar uma ferramenta de captura de tela antes de seguir
  com a estética, e deixá-la descartável por ora.** Partiu de uma pergunta
  do autor ("como fazer com que você consiga ver mais precisamente o
  resultado das alterações?"). Entre fazê-la versionada no repositório —
  reprodutível e defensável como método, mas trazendo `playwright-core`
  como primeira dependência de desenvolvimento do projeto — ou descartável
  do lado do assistente, o autor escolheu **ver funcionando primeiro e
  decidir depois**. Também definiu a ordem: a ferramenta antes dos itens
  de estética, pelo argumento de que implementar estética antes dela faria
  cada rodada voltar a depender de ele descobrir no aparelho o que
  quebrou. Nada foi commitado nem adicionado ao `pyproject.toml`.
- **(2026-10-01) Fatiar a correção e começar pela mais barata, descartando
  o redesenho.** A conversa tinha caminhado para reapresentar a tabela no
  celular como cartões por ponto — trabalho de verdade, porque hoje os
  valores digitados moram dentro da própria tabela e separar dados de
  apresentação viria antes. Quando a medição mostrou que apertar o
  espaçamento resolveria, o autor aprovou essa ordem (espaçamento → botão
  de modo → redesenho só se necessário) e, confirmada a correção no
  aparelho, **descartou o redesenho**. Decisão de escopo: não gastar a
  parte mais arriscada depois que o problema que a justificava sumiu.
- **(2026-10-01) Manter a ideia do localizador por cor como plano B, não
  implementar.** Ideia do autor: para achar um elemento que só é
  alcançável por coordenada, pintá-lo temporariamente com uma cor
  inconfundível, localizá-lo por varredura de pixel e devolver a cor
  original — generalizando o que funcionou por acaso com o vermelho da
  lixeira. O assistente apontou que a ideia coincide com uma técnica
  estabelecida de computação gráfica (*color picking*), mas que o custo é
  precisar mexer no código do app para pintar o alvo, e que uma
  alternativa possivelmente melhor (ligar a camada de acessibilidade do
  Flutter, procurando os botões pelo nome) existe, embora não verificada.
  O autor decidiu **não implementar nada agora** e deixar a própria ideia
  arquivada como plano B garantido — ela funciona com certeza, enquanto a
  camada de acessibilidade é aposta.
- **(2026-10-03) Card "Sistema" em grade 2×2, não em coluna única.** O
  autor relatou o degrau (dropdown à esquerda, campos centralizados) no
  desktop. Entre grade 2×2 com campos de 190px e coluna única com 220px
  (mais simples, mas com vão à direita), escolheu a grade — aceitando mexer
  também no celular, onde o ganho é só o fim do degrau. Origem da ideia de
  largura menor: análise do assistente (dois campos de 220px não cabem em
  ~420px); a escolha entre as duas opções foi do autor.
- **(2026-10-03) Conteúdo e formato do tooltip dos gráficos.** Quem ditou
  foi o autor, em passos: reduzir os algarismos significativos, incluir o x
  e a unidade, quebrar em duas linhas e alinhar à esquerda. O assistente só
  levantou que o padrão mostrava apenas o y e deixou a decisão de incluir x
  e unidade para ele.
- **(2026-10-03) Como desenhar o dado experimental: só marcadores, com forma
  diferente por fase (opção C).** Fechando a pendência que a decisão de
  2026-08-19 deixou em aberto ("dado é ponto, modelo é linha", sem dizer
  como desenhar o ponto). O assistente levou três opções, testadas no app
  de verdade com o CSV de etanol/água e comparadas lado a lado: **A** só
  círculos; **B** círculos mais linha fina tracejada; **C** quadrado para
  o líquido e círculo para o vapor. O autor escolheu **C**. Argumentos
  levantados na proposta: não sugere interpolação (o que B faria, e que a
  decisão de 2026-08-19 recusou); as fases se distinguem sem depender só
  da cor, útil em projeção em sala e impressão em preto e branco. O
  tamanho dos marcadores (quadrado 8px, círculo raio 4,5px) é o testado na
  proposta — o autor não pediu ajuste. Cores azul/vermelho e curva
  comparativa (roxo/ciano) ficam para o item 4 da lista de estética.
- **(2026-10-03) Paleta dos gráficos: a cor é a fase, o estilo é a origem
  (opção A), com o comparativo em marcadores vazados.** O assistente levou
  duas opções com imagens do app rodando, mais a situação de hoje: **B**
  (troca mínima — só tirar o vermelho dos dados, as seis cores continuam
  sem relação) e **A** (azul = líquido, laranja = vapor; marcador cheio =
  tabela, linha = modelo, tracejado = comparativo; no ln γ, verde/roxo por
  componente). O autor escolheu **A** e, num segundo ponto, **marcadores
  vazados em vez de tracejado para o comparativo** — alternativa que o
  próprio assistente levantou ao ver que o comparativo, por ser o mesmo
  modelo avaliado nos x1 da tabela, fica em cima da linha do modelo e o
  tracejado quase some. Argumentos da proposta: de seis cores
  independentes para duas; azul/laranja é o par que melhor se distingue em
  daltonismo; o vermelho fica livre para erro e exclusão; e "o calculado
  nos pontos da tabela também é ponto" é coerente com a decisão de
  2026-10-03 sobre o dado experimental (opção C) e com "dado é ponto,
  modelo é linha". Custo aceito: o laranja continua sendo a cor dos avisos
  em texto e do selo "Calculado" (texto e fundo pastel, não linha).
- **(2026-10-03) Legenda dos gráficos em grade (fase × origem), não em chips
  com altura maior (opção B).** A causa do problema era a legenda de seis
  chips com altura fixa de 64px: com "Comparar" ativo ela precisava de três
  linhas e a terceira cobria o rótulo do topo do eixo vertical. O
  assistente levou duas saídas testadas no app: **A** manter os chips e
  subir a altura reservada para 96px (resolve a colisão, mas deixa um vão
  no card do ln γ, que só usa duas linhas) e **B** uma grade de três linhas
  fixas (cabeçalho + 2) com linhas = fase e colunas = origem. O autor
  escolheu **B**. Argumentos da proposta: os dois cards ficam do mesmo
  tamanho sem espaço morto; a grade ensina a regra "cor = fase, estilo =
  origem" (o símbolo de cada coluna é o mesmo em todas as linhas); e,
  segundo a estimativa do assistente, a legenda de chips quebraria em cerca
  de seis linhas no celular e seria cortada pela altura fixa, enquanto a
  grade tem a mesma altura em qualquer largura — a estimativa foi
  conferida na implementação (grade cabe a 390px). Custo aceito: o rótulo
  "(x)"/"(y)" que dizia qual composição vai no eixo horizontal saiu da
  legenda; o título do eixo ("x1, y1 (fração molar)") e o tooltip
  (`x1 = …` / `y1 = …`) continuam dizendo.
- **(2026-10-03) Índices como subscritos Unicode em todo o app.** O autor
  pediu explicitamente que `x1`, `ln γ1`, `τ12` etc. aparecessem com o índice
  abaixo da linha, não como dígito comum. A forma de implementar (subscritos
  Unicode `₁`/`₂` em vez de texto formatado) foi escolha técnica do
  assistente, porque o tooltip e o título de eixo do gráfico não aceitam
  texto formatado; o pedido e o escopo ("todo índice") são do autor.
- **(2026-10-03) Corrigir o rótulo quebrado do eixo do ln γ e a quebra do
  ΔP/Δy no celular, sem nova proposta.** Eram defeitos de renderização (não
  escolha de visual), levantados pelo próprio assistente e relatados pelo
  autor ("o gamma não renderiza correto"); o autor autorizou a correção
  ("Sim, corrija o defeito do celular, além do gamma").
- **(2026-10-03) Nome e cabeçalho do app: faixa de cabeçalho (H2), "VLE
  Interativo".** O assistente levou duas disposições (H1: título solto à
  esquerda com o botão de modo à direita; H2: faixa colorida) e quatro
  candidatos de nome, com imagens no desktop e no celular. O autor escolheu
  **H2**, o nome **VLE Interativo**, o subtítulo **"Equilíbrio
  líquido-vapor com modelos de Gᴱ"** e o crédito **"UFC"** (o assistente
  tinha recomendado H1 e sugerido "TCC — Engenharia Química — UFC"; o autor
  preferiu a faixa e o crédito curto). Na sequência pediu o botão de modo
  "com uma cor levemente destacada" dentro da faixa, atendido com fundo
  branco translúcido.

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
  dividir o mesmo gráfico com os dados da tabela. **Resolvido em
  2026-10-03:** só marcadores, sem linha ligando os pontos (ver item 3 da
  lista de estética e a entrada correspondente em "Decisões de engenharia
  do aluno").

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
