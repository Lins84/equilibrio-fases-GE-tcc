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

## Como rodar o app — usar o `.venv` do projeto

O ambiente válido é o **`.venv` do projeto** (Flet 1.0 + flet-charts 1.0,
numpy e thermo, conforme `pyproject.toml`/`uv.lock`). Rodar sempre com ele:

```
PYTHONPATH=. .venv/bin/flet run interface/fletando_grafico.py --web --port 5000
```

(No Windows: `uv run flet run interface/fletando_grafico.py --web --port 5000`.)

- **Não usar o `flet` do PATH no Termux** (`/data/data/com.termux/files/usr/bin/flet`):
  é a 0.84.0, desatualizada, e não tem `flet_charts`, `numpy` nem `thermo`.
  Usá-lo gera erros em cascata (`ModuleNotFoundError`) e leva à tentação de
  instalar pacotes no Python global — que é o erro a evitar.
- **Não rodar `pip install` no Python global nem criar ambientes novos.** O
  que vale é o que está commitado (`pyproject.toml`, `uv.lock`) e o `.venv`
  existente. Dependência nova segue a regra central: propor e aguardar.
- Conferir a versão antes de rodar, se houver dúvida:
  `.venv/bin/python -c "import flet; print(flet.__version__)"` → `1.0.0`.
- `--web` carrega o CanvasKit de `www.gstatic.com` no navegador; sem internet
  a tela trava na splash (ver "Estado atual").

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
  instalado indiretamente via `thermo`); `verificar_xml_chemsep`
  (2026-10-07), que alerta quando uma atualização do `chemicals` pode ter
  alterado o XML de r/q do UNIQUAC; `detectar_instabilidade_liquida`
  (2026-10-08), que acusa em que faixa de x₁ o modelo prevê duas fases líquidas;
  `ln_gamma_experimental` (2026-10-08), ln γ da tabela pelo método indireto;
  e o `model_uniquac` aceita q′ opcional (`qp1`/`qp2`); `uniquac_qprime_do_par` e
  `montar_parametros_automaticos(..., usar_qprime=)` o ligam à opção "Usar q′" da UI
  (desligada por padrão). Todos os modelos e adaptadores
  validados contra o `thermo`/dados sintéticos.

**UI — `interface/`:**

- `interface/fletando_grafico.py` (~1525 linhas) — **a linha viva da UI,
  já integrada ao motor de cálculo**: tabela editável de pontos
  experimentais P/x/y (com botão "Importar dados" — arquivo CSV ou texto
  colado —, botão "Exemplos" — quatro exemplos embutidos com dado NIST —,
  "Limpar dados"; os gráficos se atualizam sozinhos ao sair de um campo da
  tabela — desde 2026-10-08 não há botão "Gerar Gráfico" nem "Desfazer"), escolha de modelo Gᴱ e de componentes/temperatura, sliders de
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
  (conferência secundária do `model_margules_2p` contra a planilha XSEOS —
  desde 2026-10-08 chama o modelo real; antes comparava uma cópia da fórmula),
  `teste_margules_2p_primeiros_principios.py` (2026-10-08 — Margules 2-P pela
  definição termodinâmica: grandeza parcial molar de Gᴱ/RT por passo complexo,
  Euler, Gibbs-Duhem, limites e redução ao Margules 1-P) e
  `teste_margules_2p_nist_ln_gamma.py` (2026-10-08 — Margules 2-P contra o
  ln γ experimental, método indireto, das 10 isotermas NIST),
  `teste_van_laar_margules_1p_nist_ln_gamma.py` (2026-10-08 — Van Laar e
  Margules 1-P contra o mesmo ln γ experimental, mais um estimador linear
  independente do Barker),
  `teste_van_laar_primeiros_principios.py` (2026-10-08 — Van Laar pela definição
  termodinâmica, como o do Margules 2-P),
  `teste_instabilidade_liquida.py` (2026-10-08 — aviso de duas fases líquidas),
  `teste_ln_gamma_experimental.py` (2026-10-08 — ln γ experimental da tabela, faixa 0,10–0,90),
  `teste_uniquac_qprime.py` (2026-10-08 — opção "usar q′" do UNIQUAC: padrão desligado, q′ do ChemSep, par sem efeito, fallback UNIFAC),
  `teste_koretsky_formulas_e_exemplos.py` (2026-10-08 — fórmulas das Tabelas
  7.2 e 7.4 do Koretsky contra `MODELS_GE` e exemplos/problemas resolvidos do
  livro com resposta publicada: Exemplos 8.5 e 8.9-8.11, Problemas 7.68 a 7.70
  e Exemplo 7.12 com q′),
  `teste_psat_koretsky_apendice_a.py` (2026-10-08 — Psat e constantes críticas
  da `thermo` contra o Apêndice A do Koretsky),
  `teste_parse_ponto_tabela.py` (lógica da tabela; insere `interface/` no
  `sys.path` para achar o módulo, e exige `flet` instalado — ver ressalva
  no topo do arquivo; importa de `fletando_grafico.py` desde 2026-10-08) e
  `teste_regressao_barker.py` (valida
  `regress_params_barker`: gera dados sintéticos sem ruído a partir de
  parâmetros conhecidos — Margules 1P, NRTL com α12 fixo, UNIQUAC com
  r/q via grupos UNIFAC — e confere que a regressão os recupera; cobre
  também os três erros esperados da seção 2.8: poucos pontos, parâmetro
  fixo obrigatório faltando, e UNIFAC sem regressão) e
  `teste_banco_ipdb.py` (2026-09-27 — valida `wilson_params_from_ipdb`
  contra a referência da própria docstring de `thermo.wilson.Wilson`
  para etanol/água a 70 °C, e `buscar_parametros_banco` para NRTL e
  Wilson via nome/sinônimo em vez de CAS, além dos erros esperados:
  modelo sem tabela no IPDB e par ausente na tabela) e
  `teste_limites_redondos.py` (2026-10-03 — regressão do passo do eixo
  vertical dos gráficos: nunca zero, mesmo com ln γ quase constante) e
  `teste_importar_texto.py` (2026-10-06 — leitura de texto colado: separadores,
  vírgula decimal, cabeçalho opcional, linhas inválidas contadas e leitura de
  CSV; roda com `PYTHONPATH=. .venv/bin/python testes/<arquivo>.py`) e
  `teste_validacao_nist_etanol_agua.py` (2026-10-06 — modelos do banco e
  regressão de Barker contra dado experimental com fonte citável, NIST
  ThermoML/Cristino 2013; sai com código 1 se algo fugir da tolerância) e
  `teste_validacao_azeotropos_nist.py` (2026-10-07 — regressão de Barker e
  azeótropo contra dois sistemas com fonte citável: metanol/2,3-dimetil-2-buteno,
  azeótropo de pressão máxima, e clorofórmio/2-butanona, desvio negativo e
  azeótropo de pressão mínima; mesmo padrão de saída/código 1) e
  `teste_aviso_regressao.py` (2026-10-07 — aviso de regressão suspeita: parâmetro a menos de 1 % de um limite da busca ou otimizador que não converge; sem falso positivo nos 4 exemplos NIST × 5 modelos) e
  `teste_temperatura_critica.py` (2026-10-07 — o motor devolve `Tc_C` e o aviso de T na crítica dispara só quando deve) e
  `teste_xml_chemsep.py` (2026-10-07 — alerta de atualização do XML interno do
  ChemSep que o UNIQUAC usa: falha com código 1 se a versão do `chemicals` ou o
  XML — nome e conteúdo — diferirem dos validados, e confere que o alerta de
  execução dispara).
- `Docs/mapeamento_e_plano_TCC-1.md` — documento de escopo do TCC (autor,
  orientador, problema, objetivos, plano de execução).
- `referencias/` — material de referência: print da planilha XSEOS, dois
  `.jsx` de Margules 1P/2P, e `esboco_manuscrito_autor.jpg` (2026-09-27 —
  o rascunho original do autor que embasou a seção 2.2 do mapeamento;
  mostra também um elemento perto do gráfico P-x-y, anotado "P"/"y exp"
  com um quadro "Salva" ao lado, ainda não implementado — ver pendência
  em "Próximos passos"), e `nist_thermoml_cristino2013_etanol_agua_isotermas.csv`
  (2026-10-06 — dado experimental etanol/água, T-P-x-y, com fonte citada no
  cabeçalho; usado pelo teste de validação e, desde 2026-10-07, pelos dois
  exemplos do botão "Exemplos"), e, desde 2026-10-07, mais dois CSVs
  NIST/ThermoML, usados como fixtures de teste e também como exemplos do botão
  "Exemplos":
  `nist_thermoml_feng2011_metanol_dimetilbuteno_isotermas.csv` e
  `nist_thermoml_clara2006_cloroformio_mek_303K.csv`.
- `.replit` / `pyproject.toml` / `uv.lock` — projeto roda no Replit,
  gerenciado com `uv`.

**Integração cálculo ↔ UI: concluída em 2026-09-26** (commit `deba9cc`).
`fletando_grafico.py` importa `calculos.gemini` e chama
`calculate_vle_isothermal`. Os protótipos `main.py` e `fletando.py`
(sem ligação com o motor de cálculo) foram **removidos em 2026-10-08** a
pedido do autor; continuam no histórico do git.

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

## Estado atual (2026-10-07)

Snapshot; o histórico por sessão vem logo abaixo.

- **Cálculo — pronto.** Os 7 modelos Gᴱ implementados e validados contra
  as referências do `thermo` em toda a faixa de x1 (0 a 1, extremos
  inclusos). Parâmetros via IPDB (NRTL, Wilson, UNIQUAC; UNIQUAC com r/q do
  ChemSep, grupos UNIFAC como reserva), via grupos UNIFAC e via regressão de
  Barker (`regress_params_barker`). Desde 2026-10-06/07 há também validação
  contra **dado experimental com fonte citável** (NIST ThermoML): etanol/água
  (modelos do banco e Barker), metanol/2,3-dimetil-2-buteno e clorofórmio/
  2-butanona (Barker e azeótropo).
- **UI — integrada.** `fletando_grafico.py` calcula e plota a curva do
  modelo sobre os pontos digitados, com banco IPDB, regressão, selo de
  origem, comparação calculado-vs-experimental (ΔP/Δy no card de
  parâmetros), importação de dados (botão "Importar dados": arquivo e texto colado) e
  botão "Exemplos" (quatro exemplos NIST: etanol/água a 90 e 108 °C,
  metanol/2,3-dimetil-2-buteno a 70 °C e clorofórmio/2-butanona a 30 °C), valor de parâmetro digitável, lupa nos gráficos (só
  no desktop), estética **encerrada** (2026-10-07) e botão para alternar entre
  layout de celular e de computador.
- **Pendências.** A fase de estética foi **encerrada pelo autor em
  2026-10-07**; o tooltip dos gráficos fica como está; a visualização no
  aparelho real (Termux) foi considerada ok pelo autor. O modo isobárico
  (T-x-y) está adiado para depois do piloto, em "Atualizações futuras". As
  escolhas do assistente que estavam marcadas "a confirmar" foram
  **confirmadas pelo autor em 2026-10-07** (ver "Decisões de engenharia do
  aluno", últimas entradas).
  **Decisões pendentes (atualizado em 2026-10-08), todas do autor:**
  (1) **Veredito "bom/ruim" depois de "Comparar"** (pedido de registro do
  autor em 2026-10-08): hoje a mensagem só informa o nº de pontos e onde estão
  os maiores desvios de P e de y₁; um veredito exigiria um **limiar** de ΔP e de
  Δy, que precisa ser definido (referência medida nos exemplos NIST: ΔP 0,5–2,3 %
  e Δy 0,017–0,030 com o banco sem ajuste; ΔP 1–2 % e Δy 0,008–0,025 com
  Barker — ordem de grandeza, não critério) e provavelmente ouvir o Dr. Filipe;
  (2) ~~Van Laar: falta o teste por primeiros princípios.~~ **Feito em
  2026-10-08** (autor: "2 faz"): `testes/teste_van_laar_primeiros_principios.py`
  (Gᴱ/RT = A₁₂A₂₁x₁x₂/(A₁₂x₁ + A₂₁x₂) → ln γ pela definição, por passo
  complexo; Euler, Gibbs-Duhem, limites, linearização clássica e redução ao
  Margules 1-P; só pares de mesmo sinal, porque com sinais opostos o denominador
  se anula no interior e o modelo é singular; auto-teste com γ₁ e γ₂ trocados);
  erro ≤ 1e-12. Mapeamento e tópico "Sobre" atualizados;
  (3) ~~ln γ experimental da tabela~~ **Feito em 2026-10-08** (autor: "faça o
  item 3 com a faixa 0,10–0,90", depois de perguntar se tinha relevância ou
  caía na redundância dos vazados): `ln_gamma_experimental` (em `gemini.py`) dá
  o ln γ₁ e ln γ₂ de cada ponto da tabela pelo método indireto, γᵢ =
  yᵢ·P/(xᵢ·Pᵢˢᵃᵗ), Psat da `thermo` na T do card "Sistema" (vapor ideal), só para
  0,10 ≤ x₁ ≤ 0,90 (constantes `LN_GAMMA_EXP_X_MIN/MAX`; ponto com P ≤ 0 ou y₁ em 0
  ou 1 é ignorado); no gráfico de ln γ aparecem como marcadores cheios (círculo
  verde = γ₁, roxo = γ₂; mesma regra "cheio = tabela" do P-x-y), por cima das
  curvas, com tooltip em peso normal e coluna "Tabela" na legenda (card e lupa).
  Não depende de "Comparar" e acompanha a tabela. **Não reabre a decisão de
  2026-09-13**: a regressão continua por Barker; o indireto é só exibição, e a
  faixa restrita é a proteção contra a amplificação do erro nas pontas. Os
  tópicos de ajuda "ln γ" e "Comparar" foram atualizados (diziam que não há ln γ
  experimental). `testes/teste_ln_gamma_experimental.py` (igual à implementação
  independente do teste do Margules 2-P nas 10 isotermas NIST; ida e volta com o
  NRTL a 4e-16; faixa, ordem e pontos inválidos). Verificado por captura a 1400
  px (etanol/água 90 °C; os marcadores se afastam da curva do Margules 1-P
  simétrico, como se espera de um sistema assimétrico), com o balão e a lupa, e a
  360 px (legenda cabe);
  (4) **`.replit` reapontado em 2026-10-08, não testado no Replit** — conferir;
  **suspenso por ordem do autor em 2026-10-08** ("esqueça o Replit até a segunda
  ordem"): não lembrar nem mexer até ele pedir;
  (5) **origem do dado de 1,4-dioxano/metanol** (abaixo, depende do professor);
  (6) ~~revisar os tópicos de ajuda "Modelos de Gᴱ" e "Limitações"~~ **Revisão do
  assistente feita em 2026-10-08 (autor: "Itens 6 e 9, faça os ajustes")**, ver a
  última entrada de "Decisões de engenharia do aluno"; a revisão do **autor** sobre
  o texto segue em aberto (o roteiro "Qual usar" é síntese do assistente);
  (7) ~~UNIQUAC sem q′~~ **Feito em 2026-10-08, como opção desligada por
  padrão** (autor: "7 prossiga"; depois da pergunta sobre o ganho, propôs "um
  check box que dá a opção de usar q′" e liberou: "Libera, faça o checkbox"). O
  `model_uniquac` aceita `qp1`/`qp2` opcionais (q′ de Anderson e Prausnitz na parte
  residual; se ausentes, valem q) e reproduz a Tabela 7.4 do Koretsky no Exemplo 7.12
  e nos Problemas 7.68 e 7.69, em toda a faixa de x₁ (erro ~1e-13;
  `teste_koretsky_formulas_e_exemplos.py`, bloco E). O q′ vem do próprio XML do
  ChemSep (`UniquacQP`: água 1,00, metanol 0,96, etanol 0,92, 1-propanol 0,89;
  37 de 429 compostos trazem o valor, 14 com q′ ≠ q; nos demais vale q).
  **Na UI:** caixa "Usar q′" (com o ⓘ na mesma linha; o nome "Anderson e Prausnitz" está no ⓘ) no card "Parâmetros do modelo",
  **só no UNIQUAC, desligada por padrão**, com ⓘ explicando; **habilitada só quando o
  par tem algum composto com q′ ≠ q no ChemSep** (`uniquac_qprime_do_par`); senão fica
  apagada com a razão ao lado ("Sem efeito neste par: …") e se desliga sozinha ao
  trocar para um par sem efeito; também vale em "Comparar". Ligada, o selo vira
  **"Banco, com q′"** (laranja, cautela) e o ⓘ avisa que os a₁₂/a₂₁ do banco foram
  ajustados com q. **Por que desligada:** com os a₁₂/a₂₁ do banco, q′ piora o ajuste
  aos dados NIST de etanol/água (ΔP 4,0–5,0 % contra 1,3–3,5 % com q, nas 5
  isotermas; `teste_validacao_nist_etanol_agua.py` registra isso, agora usando a
  própria opção). Com os parâmetros do livro o resultado é misto: no Problema 7.68 o
  γ₁ com q′ é 2,235 (−2,8 % do medido 2,30) contra 2,49 sem q′ (+8 %), mas o γ₂ fica em
  1,245 contra 1,32 (−5,7 %); no 7.69 o P com q′ é 31,7 kPa contra 41,3 medidos
  (−23 %; sem q′, 34,3 kPa, −17 %). Se o r/q do par vem dos grupos UNIFAC (ChemSep
  sem r/q), a opção não se aplica. `testes/teste_uniquac_qprime.py`. Verificado por
  captura a 1400 px (etanol/água 90 °C: ligar a caixa troca o selo e piora a curva;
  acetona/clorofórmio: caixa apagada com o motivo) e a 360 px;
  (8) ~~aviso de instabilidade da fase líquida~~ **Feito em 2026-10-08** (autor:
  "8 se o custo for baixo, implemente"): `detectar_instabilidade_liquida(x1,
  gamma1)` (em `gemini.py`) aplica a condição d ln(x₁γ₁)/dx₁ > 0 à malha do
  cálculo, valendo para qualquer modelo (no Margules 1-P reduz-se exatamente a
  A/RT > 2) e devolvendo a faixa de x₁ instável; a UI mostra um texto laranja no
  card "Parâmetros do modelo" (`aviso_instabilidade_liquida`, controle
  `aviso_instabilidade_txt`; **no card de parâmetros e não na mensagem de status**,
  porque esta fica no fim do card "Dados experimentais", fora da tela com tabela
  longa — visto na captura). Não bloqueia o gráfico. Medido: sem aviso em
  etanol/água (todos os modelos do banco e os ajustes de Barker às 5 isotermas) e
  em clorofórmio/MEK; aviso em 1-butanol/água (UNIFAC e UNIQUAC, que de fato se
  separa). **Achado:** nos dados do exemplo metanol/dimetilbuteno, Margules 1-P/2-P,
  Van Laar e NRTL ajustados por Barker chegam a A/RT ≈ 2,2 e o aviso aparece (x₁
  de ≈ 0,34 a 0,67 a 70 °C), embora o dado seja de fase única — é o que o modelo
  prevê, não falso positivo; o Wilson não prevê separação e não avisa. O texto do
  aviso diz isso ("se o sistema real é miscível em tudo, o modelo ou os parâmetros
  não descrevem bem essa região"), e os tópicos de ajuda "Limitações" e o "?" do
  exemplo metanol/dimetilbuteno foram ajustados só nessa frase (antes diziam "o
  app não avisa"). `testes/teste_instabilidade_liquida.py`;
  (9) ~~ajustar o texto dos tópicos de ajuda "Modelos de Gᴱ" e "Limitações"
  (cosmético)~~ **Feito em 2026-10-08 só nos ajustes que o assistente identificou**
  (o autor não especificou os dele); se faltar algum, é só dizer qual;
  **Pendência de informação (2026-10-07):** origem do dado de
  1,4-dioxano/metanol a 308,5 K, de um exercício do professor sem fonte
  conhecida — o autor vai perguntar ao professor; até lá a frase da seção 2 do
  mapeamento fica em redação provisória (ver "Decisões de engenharia do
  aluno", terceira rodada de busca no ThermoML).
- **Testes** são scripts avulsos rodados à mão, sem runner nem CI (20
  scripts em `testes/`, todos automatizados; o `teste_dioxano_nrtl.py`, visual e
  manual, foi removido em 2026-10-08). A interface é verificada visualmente pelo autor no dispositivo
  real **e**, desde 2026-09-30, também pelo Claude Code por captura de tela em
  ambiente de nuvem — ver sessão de 2026-09-30/10-01 para o alcance e os
  limites de cada uma.

## Sessão de auditoria dos modelos (2026-07-27)

Os 6 modelos Gᴱ então registrados em `MODELS_GE` (`model_margules_1p`,
`model_margules_2p`, `model_van_laar`, `model_wilson`, `model_uniquac`,
`model_unifac`) estão todos auditados e validados por comparação direta
com as implementações de referência do `thermo` (`Wilson_gammas`,
`UNIQUAC_gammas`, `UNIFAC.from_subgroups`), varrendo toda a faixa de
composição (x1 de 0 a 1, incluindo os extremos) — não apenas com valores de
exemplo. **Ressalva (2026-10-08):** a `thermo` (e a `chemicals`) **não têm
Margules nem Van Laar** (busca no código instalado), então a comparação com a
`thermo` vale só para Wilson, UNIQUAC e UNIFAC (e NRTL, depois); o Margules 2-P
ganhou validação própria em 2026-10-08 e o Margules 1-P pela redução ao 2-P; o
Van Laar segue sem referência independente. Três bugs foram encontrados e
corrigidos nessa auditoria:

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
   combinado esconde esse tipo de nuance — verificado, na época, com um
   CSV de etanol/água a 50 °C (`referencias/etanol_agua_50C_isotermico.csv`):
   NRTL com parâmetros-chute deu ΔP=29,4%/Δy=0,065; os mesmos parâmetros
   ajustados por Barker deram ΔP=6,2%/Δy=0,106 — Barker melhora P mas
   piora um pouco y, porque otimiza o resíduo combinado, não y sozinho.
   **Ressalva (2026-10-06): esse CSV era de origem desconhecida e foi
   removido do repositório (ver "Decisões de engenharia do aluno") por não
   passar em checagens de consistência física; os números acima não valem
   como validação. O argumento de reportar P e y separados continua de pé
   por razão teórica (literatura DECHEMA/Gmehling), mas a demonstração
   numérica precisa ser refeita com dado de fonte citável.** Esse trade-off
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

- **Sessão compartilhada em tempo real (modo "aula": professor no desktop,
  alunos em celular e desktop).** Levantada pelo autor em 2026-10-04: usar
  uma sessão em que os dados e os controles fossem compartilhados
  simultaneamente entre o professor e os alunos presentes. **Registrada
  como ideia, sem implementação, a pedido do autor ("Registre a ideia em
  Atualizações futuras") — não implementar sem pedido explícito.**
  **DECIDIDO em 2026-10-06: o co-op está descartado.** Depois de discutir
  servidor, senha e chave de sessão (abaixo, mantido como registro), o autor
  repensou: "o mais prático seria sem cooperações automatizadas. Melhor cada
  um com o seu. Na hora da aula o professor pede para o aluno ir fazendo o
  que for necessário." Cada aluno usa o app sozinho, em sessão própria — que
  é como o app já funciona hoje. Nada do desenho de `pubsub`, sala, senha ou
  chave será implementado; a análise abaixo fica só como histórico. **Única
  dificuldade reconhecida pelo autor:** compartilhar um CSV no momento da
  aula (ver "Distribuição de CSV na aula" logo após esta entrada).
  *Estado atual:* cada navegador que abre o app é uma sessão Flet
  independente (tabela, sliders e gráficos próprios); ninguém vê o que o
  outro faz. O servidor já atende vários clientes de uma vez (o `flet run
  --web` escuta em `0.0.0.0`).
  *Viabilidade (verificada em 2026-10-04):* o Flet 1.0.0 tem `page.pubsub`
  (`send_all`, `send_others`, tópicos, `subscribe`) para comunicar as
  sessões de um mesmo processo — é o mecanismo natural. Desenho esboçado:
  um **estado único da aula** no servidor (tabela, modelo, componentes,
  temperatura, parâmetros dos sliders); cada ação do professor (digitar
  ponto, mover slider, "Comparar", "Calcular por Regressão") é transmitida
  às demais sessões, que aplicam a mesma mudança e redesenham (evitando o
  eco da própria mensagem); quem entra depois recebe o estado atual; cada
  aluno vê o layout do seu aparelho, porque a detecção celular/desktop já é
  por largura da tela.
  *Três níveis levantados:* **(1) aula guiada** — só o professor controla,
  os alunos veem ao vivo sem editar, com senha de professor (o mais viável,
  e o ponto de partida sugerido); **(2) aula guiada com exploração** — cada
  aluno pode "soltar" e mexer no próprio gráfico e depois voltar à aula
  (dois estados por aluno, mais código); **(3) controle de todos** —
  qualquer um altera o estado comum (**não recomendado**: dois sliders
  simultâneos se atropelam).
  *Pontos de atenção:* (a) **rede** — todos precisam alcançar o servidor;
  numa rede de sala funciona, mas redes de universidade costumam isolar os
  aparelhos entre si, exigindo hospedagem fora ou túnel (o túnel gratuito
  já se mostrou instável); (b) **internet nos clientes** — o app carrega o
  CanvasKit de `www.gstatic.com` no navegador de cada aluno; sem internet a
  tela trava na splash (o build offline `flet build web --no-cdn` é outro
  fluxo); (c) **carga** — se cada sessão recalcula o modelo, dezenas de
  recálculos simultâneos chegam juntos ao servidor (viável, mas pede
  teste; o Termux como servidor de uma turma inteira parece fraco);
  (d) **segurança** — sem login, qualquer pessoa com o endereço entra; o
  nível 1 exige ao menos uma senha de professor; (e) **escopo** — é um
  segundo modo de uso do app, por isso fica aqui e não no piloto.
  *Se for antecipado:* sugestão de **protótipo mínimo** antes de qualquer
  coisa maior — professor e aluno compartilhando só a escolha do modelo e um
  slider, para medir latência e carga.
  *Cenário de uso e proposta do autor (2026-10-06, **ainda sem decisão de
  servidor**):* a rede da universidade é instável e os dados móveis são mais
  garantidos. O autor propôs o **PC do professor como servidor, com senha, e
  os alunos entrando com uma "chave de sessão"**, como em apps de reunião
  remota, usando internet móvel (ou a da universidade, num dia bom). Dois
  modos de uso: **(1) todos independentes** (cada aluno usa o app sozinho) e
  **(2) co-op**, quando a internet permitir (dia bom, pouca latência).
  *Análise do assistente (opções, não decisões):*
  (a) **alcance** — alunos em 4G/5G não chegam ao PC pelo endereço da rede
  local; o servidor precisa de endereço público: túnel (cloudflared/ngrok;
  conexão que sai do PC, passa pelo bloqueio de entrada da universidade) ou
  hospedagem. O PC do professor na rede instável é ponto único de falha da
  aula inteira, inclusive do modo independente. Caminhos: PC + túnel no
  hotspot do celular do professor; servidor na nuvem com instância única (o
  professor entra como cliente comum, com a senha); PC + túnel pela rede da
  universidade (o mais frágil). Recomendação do assistente: nuvem para uso
  real em aula, PC + túnel só para protótipo;
  (b) **uma implantação, dois modos** — o modo independente é o app como
  está (sem `pubsub`); o co-op é opt-in ("Entrar na aula"), com "Sair da
  aula" para voltar a trabalhar sozinho sem perder o estado, o que dá
  degradação gradual conforme a latência do dia;
  (c) **senha e chave são coisas distintas** — a senha dá o papel de
  professor (criar a sala e controlar); a chave é um código curto gerado ao
  abrir a aula, que o aluno digita para entrar, e vira o tópico do `pubsub`
  (`send_all_on_topic`), permitindo várias salas. O Flet não traz login, então
  tudo isso é lógica do próprio app, com expiração da sala e código de
  entropia suficiente, já que o endereço fica público;
  (d) **internet nos alunos é pré-requisito de qualquer modo** (CanvasKit vem
  de `www.gstatic.com`), então dados móveis não agravam o co-op; a dúvida da
  rede da universidade fica restrita ao servidor;
  (e) **riscos em aberto** — `pubsub` em memória exige um único processo;
  conexão móvel que cai pode derrubar a sessão do aluno (não se sabe se o Flet
  restaura o estado ao reconectar — testar); carga de um recálculo do modelo
  por aluno a cada movimento de slider (alternativa: só a sessão do professor
  calcula e transmite as curvas, com mais tráfego). Nada disso foi
  implementado nem testado.

- **Distribuição de CSV na aula (levantada em 2026-10-06; ~~sem decisão~~
  **feita no mesmo dia**, ver "Decisões de engenharia do aluno").** Com cada aluno no seu próprio app (co-op descartado), o único
  atrito apontado pelo autor é fazer todos terem o mesmo CSV na hora da aula.
  Hoje o app só importa por seletor de arquivo (`importar_csv`), então o aluno
  precisa ter o arquivo no aparelho. Opções levantadas pelo assistente, **para
  o autor escolher**: (1) **fora do app** — o professor manda o arquivo antes
  da aula (WhatsApp, Drive, e-mail) e o aluno baixa e importa; zero código,
  mas depende de cada um achar o arquivo no celular; (2) **exemplos embutidos**
  — um seletor "Carregar exemplo" no app com os CSVs de referência (a opção
  foi implementada e **retirada em 2026-10-06**, por falta de dataset com
  fonte; **reposta em 2026-10-07** com dado do NIST/ThermoML, ver
  "Decisões de engenharia do aluno"), sem arquivo nenhum para compartilhar; só serve para dados que o professor deixou previamente no
  repositório; (3) **colar texto** — campo para colar as linhas P, x₁, y₁
  (o professor manda o texto por mensagem e o aluno cola); funciona com qualquer
  dado novo na hora; (4) **link/QR** — importar de um endereço (ex.: arquivo
  público no repositório), em que o professor projeta um QR code. Nenhuma foi
  implementada nem escolhida.

- **Hospedagem institucional (STI/UFC ou RNP).** Levantada em 2026-10-08/09, a
  partir da pergunta do autor sobre hospedagem gratuita para dar uma amostra ao
  orientador (que usa Mac). **Adiada por ordem do autor em 2026-10-09 ("coloque a
  decisão de STI como atualizações futuras") — não abrir chamado nem mexer sem pedido
  explícito.** Motivo: com o app em formato web estático (Pyodide, testado no PC e no
  celular — ver "Decisões de engenharia do aluno", entrada de 2026-10-08 sobre o
  Pyodide), basta hospedar arquivos, e o **GitHub Pages** faz isso de graça para
  repositório público, sem servidor e sem aprovação institucional. O passo a passo do
  GitHub Pages foi preparado no chat (publicação com `flet publish --base-url`, branch
  `gh-pages`); **o autor publicou em 2026-10-09** (ver o fim da entrada do Pyodide em
  "Decisões de engenharia do aluno"). A STI só voltaria a valer
  a pena para (a) um endereço institucional `ufc.br`, que dá mais peso diante da banca
  ou numa disciplina, e (b) permanência garantida depois da formatura, já que o Pages
  depende da conta do autor. Se for retomada: o texto do chamado entregue em
  2026-10-08 pedia hospedagem de **aplicação** e precisa ser reescrito para
  hospedagem de **arquivos estáticos**; ainda não há confirmação de que aluno de
  graduação possa usar STI ou RNP.

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
6. ~~Tamanhos de fonte contra o requisito de projeção da seção 1.4: a nota
   do α12 é 11px, itálico, cinza sobre branco.~~ **Feito em 2026-10-03**
   (opção B escolhida pelo autor, com as três mudanças propostas — ver
   "Decisões de engenharia do aluno"). Medição que embasou: contraste WCAG
   (mínimo 4,5:1 para texto, 3:1 para linhas de gráfico) reprovava no aviso
   laranja (1,95:1), selo "Calculado" (2,99:1), erro vermelho (3,33:1), nota
   do α₁₂ e aviso de UNIQUAC/UNIFAC (4,17:1) e linha laranja do vapor
   (2,79:1); havia textos de 11, 12 e 13px. Aplicado: **(a) contraste** —
   aviso `#9A3B00` (6,34:1), erro `RED_800` (5,09:1), selo "Calculado" com
   texto `#7A3300` sobre `ORANGE_100` (7,2:1), notas em `GREY_800`
   (9,1:1), `COR_VAPOR` de `ORANGE_800` para `ORANGE_900` (3,43:1);
   **(b) sem itálico** na nota do α₁₂ e no aviso de UNIQUAC/UNIFAC;
   **(c) piso de 14px** — todo `size=` de 11/12/13 virou 14; **(d) escala
   dos gráficos** — os números dos eixos usam o estilo `body_medium` do
   tema, que passou de 14 para 16 (`page.theme`, `ft.TextTheme`),
   levando a escala de ~12px para ~14,5px. **Efeito colateral tratado:**
   com a escala maior os rótulos do eixo x de 0,1 em 0,1 se encostavam no
   celular ("0.10.20.3…" a 360px); o passo do eixo x passou a **0,2** nos
   dois gráficos (`label_spacing=0.2`), nos dois modos, porque os eixos são
   criados uma vez e variar por modo exigiria mutar controle já criado.
   Verificado por captura de tela a 1400, 390 e 360px. A opção C (tudo ~30%
   maior) foi testada e descartada como padrão: a 390px os números do eixo
   x se encostavam e a palavra "comparativo" da legenda era cortada.
   Possível "modo projeção" opcional fica registrado como ideia, sem
   implementação.
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

**Investigação da causa e correção (2026-10-03, mais tarde no mesmo dia):**
o autor pediu para descobrir por que o import só funcionava após o F5.
Achados, lendo o código do Flet 1.0.0 (Python e o cliente Dart compilado) e
o log do servidor (`flet run -vv`):
1. O `FilePicker(112)` do erro é o seletor da **primeira sessão** do
   processo do servidor (ids são um contador global: 112, depois 798,
   1484…). O F5 abre uma sessão nova ou reconecta a anterior, que reenvia a
   árvore completa.
2. Um seletor criado na inicialização é registrado no navegador por **uma
   única mensagem avulsa** (`PATCH_CONTROL` no `ServiceRegistry`), enviada
   logo depois do `REGISTER_CLIENT` e antes de a tela existir. Os
   `page.update()` seguintes só mandam a árvore de views, nunca reenviam o
   registro. Se o navegador não monta o serviço, nada o repara; o cliente
   espera 10 s por um ouvinte e dá "Timeout waiting for invoke method
   listener". O cliente também descarta patches de controle desconhecido
   ("dropped a patch for unknown control… needs a reload").
3. **Não reproduzido** na nuvem (Chromium, Python 3.11/3.13, CPU limitada
   até 20×, perfil persistente com F5): o seletor sempre abriu. Por que o
   Chrome/Windows do autor perde aquela mensagem na primeira carga **não
   foi provado**; a explicação acima é a mais provável, não confirmada.
**Correção aplicada:** o seletor passou a ser criado **no clique**
(`await ft.FilePicker().pick_files(...)`, padrão do Flet 1.0), sem
`page.services.append`. Validada na nuvem com servidor recém-iniciado: o
seletor abre e o CSV de etanol/água carrega (14 pontos, tabela e gráfico).
O `except` com a mensagem de F5 permanece como segunda proteção.
**Confirmado pelo autor** no Chrome/Windows (2026-10-03): "resolvido de
primeira" — o import funcionou na primeira carga, sem F5. A causa raiz
(por que o navegador perdia a mensagem de registro) segue não provada; o
que está confirmado é que criar o seletor no clique elimina o sintoma. Se
o erro voltar, o console do navegador (F12) deve mostrar a linha "dropped
a patch…".

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
  **Ressalva (2026-10-08):** a referência (a planilha) existia antes, mas o teste
  nunca chamou o `model_margules_2p` — comparava a planilha com uma cópia da
  fórmula escrita dentro do próprio teste, então não validava o código do app.
  Corrigido em 2026-10-08 (ver a entrada de mesma data, mais abaixo).
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
- **(2026-10-03) Investigar por que o import de CSV só funcionava após o
  F5 e aplicar a correção proposta (seletor criado no clique).** O autor
  pediu a investigação ("descubra pq o import só funciona após atualizar
  página"); o assistente levou a causa mais provável, deixando claro que
  não foi reproduzida, e a correção, validada numa cópia descartável; o
  autor autorizou aplicá-la ("Sim, aplique a correção"). Origem da ideia
  de correção: o padrão da documentação do Flet 1.0.
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

- **(2026-10-03) Nota do α₁₂ com cores próprias e itálico de volta.** Logo
  depois de aplicar o item 6, o autor pediu: ícone ⓘ da nota "colorido e
  destacado", o "α₁₂" da nota em outra cor (sugeriu azul) e o texto da nota
  em outra cor, em itálico como antes — deixando as cores a critério do
  assistente. Escolhas do assistente: ícone `INFO` cheio, 18px,
  `BLUE_700`; "α₁₂" em `BLUE_800`, negrito e itálico; texto em `TEAL_900`
  itálico (todas acima de 4,5:1 sobre o cartão). Isso reverte, só para
  essa nota, a retirada do itálico do item 6 (o aviso de UNIQUAC/UNIFAC
  continua sem itálico). Na sequência o autor pediu o mesmo destaque para o
  ⓘ do selo de origem do parâmetro, "em azul de tom claro, próximo ao
  celeste": `icone_info` ganhou o parâmetro `destaque`; no selo o ícone
  passou a `INFO` cheio, 18px, `LIGHT_BLUE_600` (contraste 2,79:1 sobre o
  cartão, um pouco abaixo dos 3:1 usuais para gráficos — consequência
  aceita da escolha de um azul claro; tons mais escuros perdem o aspecto
  de celeste). Depois o autor pediu que os ⓘ do erro (ΔP/Δy) ficassem
  "como os outros": o parâmetro `destaque` foi removido e todo `icone_info`
  (selo, ΔP, Δy) usa o mesmo ícone cheio, 18px, `LIGHT_BLUE_600`.

- **(2026-10-03) Fontes e contraste para projeção: opção B, com as três
  mudanças.** O assistente mediu o contraste e os tamanhos do app, testou
  três opções rodando (A só contraste; B contraste e piso de 14px; C cerca
  de 30% maior) e recomendou a B. O autor escolheu **B** e aprovou as três
  mudanças que a acompanhavam: **linha do vapor um tom mais escura** (para
  passar 3:1), **tirar o itálico** da nota do α₁₂ e do aviso de
  UNIQUAC/UNIFAC, e **subir a escala dos gráficos** (a proposta dizia que o
  assistente testaria e mostraria antes de aplicar; o autor mandou aplicar
  direto, e o resultado foi conferido por captura de tela). O passo 0,2 do
  eixo x, necessário para a escala maior caber no celular, foi decisão
  técnica do assistente, não pedida — registrada aqui e a confirmar pelo
  autor.

- **(2026-10-03) Diálogo dos ⓘ com cabeçalho e texto em cores diferentes.**
  Pedido do autor: "o texto ao clicar, cabeçalho de uma cor e texto de outra
  dentro da nossa paleta de cores". Escolha do assistente, reaproveitando
  cores já presentes no app: título em `BLUE_800` negrito (o azul da faixa e
  do "α₁₂" da nota) e texto em `TEAL_900` (a cor do texto da nota). Vale
  para os três diálogos criados por `icone_info` (origem do parâmetro, ΔP e
  Δy). O botão "Ok" ficou no estilo padrão. Verificado por captura de tela.

- **(2026-10-03) Estilo das caixas do card "Sistema".** Pedido do autor
  ("dê um estilo para as caixas do card Sistema, está muito simples"), com
  o estilo a critério do assistente. Aplicado aos quatro campos (Componente
  1, Componente 2, Modelo GE, Temperatura) por um dicionário comum,
  `ESTILO_CAIXA_SISTEMA`: fundo branco (`filled`), cantos de 12px, borda
  `BLUE_200` de 1,5px que vira `BLUE_700` de 2,5px ao focar, rótulo em
  `BLUE_800` negrito, texto `BLUE_GREY_900` com peso médio e um ícone
  `BLUE_700` na frente de cada campo (frasco, frasco vazio, sigma,
  termômetro). O texto deixou de ser centralizado (com ícone na frente,
  alinhado à esquerda fica natural). `LARGURA_CAMPO_SISTEMA` subiu de 190
  para 200px (duas caixas + espaçamento = 412px, ainda cabe nos ~420px do
  card no desktop) e o dropdown usa texto de 14px, porque com ícone e seta
  "Margules (1-P)" era cortado. Tudo definido na criação (regra de não
  mutar controle já criado). Verificado por captura de tela a 1400 e 360px.
  **Armadilha de verificação reencontrada:** durante este ajuste o servidor
  antigo continuou de pé na porta 5000 (processo filho do `flet run`, com
  outra linha de comando), o novo falhou em silêncio com "address already
  in use" e as primeiras capturas mostraram a versão velha — o aviso estava
  no log do servidor; conferir o log e `ss -ltn` antes de confiar na
  imagem.

- **(2026-10-03) Estilo do card "Dados experimentais".** Pedido do autor
  ("gostei, estilize o card dados experimentais"), na linha do card Sistema,
  com o estilo a critério do assistente; paleta já existente no app.
  **Tabela (`dt`):** cabeçalho em `BLUE_50` com texto `BLUE_800` negrito,
  linhas brancas separadas por filete `BLUE_100`, moldura `BLUE_200` de
  1,5px com cantos de 12px; `column_spacing=16`/`horizontal_margin=8`
  mantidos e `dt` segue filho direto da Column do card, sem contêiner em
  volta (embrulhá-lo quebrou a renderização em 2026-09-28). **Células:**
  fundo transparente que vira `BLUE_50` ao focar, cantos de 8px, texto
  `BLUE_GREY_900` de peso médio, cursor `BLUE_700`. Dois acertos achados
  na captura: um branco opaco cobria o filete entre as linhas (por isso
  transparente) e o `content_padding` padrão do campo preenchido cortava
  "12.33"/"0.935" nos 60px da coluna (por isso `Padding(0, 8, 0, 8)`).
  **Botões:** `estilo_botao()` — secundários (Adicionar Novo Ponto,
  Importar CSV, Comparar) com fundo `BLUE_50`, texto/ícone `BLUE_800`,
  contorno `BLUE_200` e cantos de 12px; primário ("Gerar Gráfico") em
  `BLUE_700` com texto branco; estado apagado cinza (mapa
  `ft.ControlState.DISABLED`, usado pelo Comparar sem dado). Ícone de
  "Limpar Tabela" em `BLUE_800`; a lixeira continua vermelha (vermelho
  reservado a erro/exclusão). Tudo definido na criação, sem mutar controle
  já criado. Verificado por captura de tela a 1400px (com o CSV de
  etanol/água e "Comparar") e a 360px (as 10 lixeiras continuam dentro do
  card); os 4 testes passam.

- **(2026-10-03) Estilo estendido aos demais cards.** Pedido do autor
  ("agora adapte os demais a esse mesmo estilo"), depois de aprovar o card
  "Dados experimentais". Aplicado em `cartao()`, portanto a **todos** os
  cards (Dados experimentais, Diagrama P-x-y, ln γ, Sistema, Parâmetros do
  modelo): fundo branco, moldura `BLUE_200` de 1,5px, cantos de 12px, sem
  sombra (`elevation=0`) e título em `BLUE_800` negrito. No card
  "Parâmetros do modelo": os botões "Buscar do Banco (IPDB)", "Calcular por
  Regressão (Barker)" e "Desfazer" usam `estilo_botao()` (secundário, com o
  cinza de apagado do Desfazer); os sliders ficaram com trilho ativo e
  botão `BLUE_700` e trilho inativo `BLUE_100`, e o rótulo do valor
  ("A = 0.5") em `BLUE_GREY_900` de peso médio. Gráficos mantidos como
  estavam (paleta de fase/origem já decidida). Verificado por captura de
  tela a 1400px (com CSV e "Comparar") e a 360px; os 4 testes passam.
  Não conferido por captura: NRTL/Wilson (botão "Buscar do Banco" e nota do
  α₁₂), que usam o mesmo `estilo_botao()`.

- **(2026-10-03) Tabela e botões centralizados no card "Dados
  experimentais", só no desktop.** Pedido do autor: centralizar a tabela e
  as caixas **se isso não mudasse a vista do celular**. Análise: no
  celular a tabela (~284px) já ocupa quase todo o card (~296px), então
  centralizar a tabela mal mudaria nada, mas centralizar os botões
  (Adicionar/Importar quebram em duas linhas) mudaria. Para cumprir a
  condição à risca, `construir_card_dados(centralizar=True)` é usado só no
  layout de desktop; no celular segue `False` e o card é o mesmo de antes.
  Implementação: `cartao(..., centralizar)` põe `horizontal_alignment=CENTER`
  na Column do card (título e mensagens continuam à esquerda — título numa
  Row, mensagens em Container alinhado à esquerda); os botões ganham uma
  Row nova com `alignment=CENTER` a cada montagem, em vez de mutar
  `linha_botoes_tabela`; `dt` segue filho direto da Column. Verificado:
  captura a 1400px (tabela, botões e "Gerar Gráfico" no meio) e captura a
  360px **idêntica pixel a pixel** à anterior (diferença nula); 4 testes
  passam. O modo "Ver como celular" num monitor largo também não muda (usa o
  ramo do celular).
  **Complemento (mesmo dia):** o autor notou que faltavam o "Comparar" e a
  lixeira de "Limpar Tabela", que ficam no cabeçalho do card e tinham
  continuado à esquerda. No desktop (`centralizar=True`) os dois passam a
  uma Row própria, centralizada, logo abaixo do título (o `extra_titulo`
  do cabeçalho fica vazio); no celular continuam no cabeçalho, como antes.
  Verificado: captura a 1400px com o "Comparar" funcionando, e captura a
  360px idêntica à anterior (diferença nula); 4 testes passam.

- **(2026-10-03) Tooltip dos gráficos: fundo da tabela, texto na cor da
  série.** Relatado pelo autor: "as letras do tooltip do gráfico estão em
  uma cor pouco visível". Causa, vista numa captura com o cursor sobre os
  pontos (`mouse.move` até o marcador): o Flet pinta cada linha do balão com
  a cor da própria série (azul/laranja) sobre o fundo cinza-azulado padrão —
  contraste muito baixo. Caminho percorrido, sempre a pedido do autor: texto
  branco sobre `BLUE_GREY_900`; depois fundo azul claro e texto azul-escuro
  da tabela (`BLUE_50`/`BLUE_800`, 5,0:1); por fim, "já que mudamos a cor do
  fundo, volte as cores anteriores pra ver se ainda ficam mal contrastadas"
  — texto de novo na cor da série, só que sobre o novo fundo — e o autor
  respondeu "Gostei assim". **Estado final:** balão `TOOLTIP_FUNDO =
  BLUE_50` com moldura `BLUE_200` de 1,5px (`LineChartTooltip` nos dois
  `LineChart`), texto 14px, peso 600, **sem `color`** (herda a cor da
  série). Contraste medido: azul do líquido (`BLUE_700`) 4,0:1 e laranja do
  vapor (`ORANGE_900`) 3,3:1 — **abaixo dos 4,5:1** que o projeto usa como
  piso para texto (item 6 da lista de estética); aceito pelo autor, que
  prefere ver a cor da fase na linha do balão. Se o laranja incomodar, a
  alternativa levantada é um laranja mais escuro só no texto do vapor, ou
  voltar ao azul-escuro da tabela (5,0:1).
  **Pedido não atendido: "letras em negrito e números normais".** Testado e
  descartado: (a) `text_spans` (trechos com estilo próprio) — no Flet 1.0.0
  o balão **simplesmente não aparece**, porque o cliente lê os trechos do
  tooltip como controles filhos (`eg(0,"spans")`) e o Python os envia como
  dados; sem erro no log nem no console; reproduzido com `text` vazio, com
  `text` preenchido e com estilos completos nos trechos; (b) letras em
  negrito Unicode (𝐱, 𝐲, 𝐏) — aparece, mas essas letras saem numa fonte
  serifada de fallback, destoando do resto, e dependem de baixar fonte
  extra (frágil sem internet). Ficou um estilo só para o balão inteiro
  (peso 600), com o motivo comentado em `ponto_grafico`. Alternativas a
  decidir pelo autor: tudo em negrito, tudo normal, ou esperar correção do
  Flet. Verificado por captura antes/depois; 4 testes passam.

- **(2026-10-03) Tooltip: balão dentro do gráfico, e experimental normal ×
  calculado em negrito.** Pedido do autor ("corrija o tooltip cortado no
  topo e também temos que diferenciar a cor pra não ficar confuso entre
  experimental e calculado. Deixa experimental normal e calc bold").
  **(1) Cortado no topo:** visto na captura do gráfico de ln γ — perto do
  topo o balão subia além do card e a primeira linha sumia. Correção:
  `fit_inside_vertically=True` e `fit_inside_horizontally=True` no
  `LineChartTooltip` dos dois gráficos; conferido com o balão no topo do
  ln γ e na borda direita do P-x-y (x₁ = 1). **(2) Experimental × calculado:**
  em vez de outra cor (o autor pediu o peso da letra), `ponto_grafico` ganhou
  `experimental: bool = False`; os pontos da tabela (as duas séries de
  marcadores cheios do P-x-y) passam `experimental=True` e saem em peso
  normal (W_400); todo o resto — curva do modelo e comparativo, nos dois
  gráficos — é calculado e sai em negrito (BOLD, antes W_600). Isso resolve
  o caso em que um mesmo balão mistura as duas origens (ex.: `x₁ = 0.2910`
  normal para a tabela e `x₁ = 0.2900` negrito para o modelo). O ln γ só tem
  séries calculadas, então fica todo em negrito. Verificado por captura;
  4 testes passam.

- **(2026-10-03) Legendas com inicial maiúscula; peso do tooltip no ln γ.**
  Pedido do autor ("os nomes com inicial minúscula ponha maiúscula: liq vap
  tab model; no gráfico gamma, dados vazados normais e os outros bem
  negrito"). **(1)** Rótulos das duas legendas: `Líquido`, `Vapor`,
  `Tabela`, `Modelo` — e `Comparativo`, que o autor não listou mas seguia o
  mesmo padrão (coluna de 84px comporta). Os rótulos `ln γ₁`/`ln γ₂` não
  mudam (notação). **(2)** `ponto_grafico` trocou o parâmetro `experimental`
  por `negrito: bool = True`: no **ln γ**, os marcadores vazados
  (Comparativo, o modelo calculado nos x₁ da tabela) saem em peso normal e a
  curva do modelo em negrito. **Ajuste na sequência:** o autor viu na
  captura do P-x-y que o laranja do comparativo ainda saía em negrito;
  passou a valer a mesma regra nos dois gráficos — só a curva do **modelo**
  em negrito; pontos da **tabela** e marcadores vazados do **comparativo**
  em peso normal (interpretação do assistente do "o outro laranja também
  ficou bold"; se a intenção era outra, a mudança é de uma linha em
  `ponto_grafico(..., negrito=False)`). Verificado por captura; 4 testes
  passam.

- **(2026-10-03) Erro "label_spacing cannot be 0" ao mexer no slider do
  Margules 1P.** Relatado pelo autor, com dados importados. **Causa
  (reproduzida em Python):** o "zero" do slider sai como A ≈ 1e‑16 (ruído de
  ponto flutuante, não 0 exato), então o ln γ fica praticamente constante;
  `limites_redondos` calculava um passo minúsculo (~1e‑17) que
  `round(passo, 10)` transformava em **0**, e o `ChartAxis` do Flet recusa
  `label_spacing=0`. O caso de intervalo *exatamente* constante já era
  tratado em `gerar_grafico` (abre ±1), mas o *quase* constante não.
  **Correção:** em `limites_redondos`, intervalo menor que 1e‑6 × max(1,
  |valores|) é tratado como constante (abre ±1, mesmo comportamento do caso
  exato) — a correção fica na função, então vale para os dois gráficos. Novo
  teste de regressão `testes/teste_limites_redondos.py` (passo > 0 em
  intervalos degenerados; limites normais inalterados; varredura de A de −3
  a 3 no Margules 1P) — **falha no código antigo e passa no corrigido**. Não
  reproduzido arrastando o slider pela captura de tela (o toque exato em
  ~1e‑16 não é controlável por coordenada); a reprodução e a verificação
  foram no nível da função e da varredura do modelo. Passam os 5 testes.

- **(2026-10-03) Fundo do balão do tooltip semitransparente.** Pedido do
  autor: "o balão do tooltip deve ser transparente pra poder visualizar o
  gráfico atrás dele". `TOOLTIP_FUNDO` passou a `Colors.with_opacity(
  OPACIDADE_TOOLTIP, BLUE_50)` com `OPACIDADE_TOOLTIP = 0.55` (a moldura
  `BLUE_200` continua opaca e delimita o balão). Escolhi semitransparente e
  não 100% transparente porque sem nenhum fundo o texto briga com as linhas
  do gráfico; o valor está numa constante, de uma linha para ajustar.
  **Custo visível na captura:** onde uma curva, o marcador destacado ou a
  linha vertical do cursor passam por trás do texto, essa linha atravessa as
  letras (ex.: `ln γ₂ = −0.06789` com a curva roxa por cima), o que reduz a
  legibilidade naquelas linhas — o preço de ver o gráfico atrás. Verificado
  por captura no P-x-y e no ln γ; 5 testes passam.

- **(2026-10-03) Opacidade do balão do tooltip: 55% → 70%.** Pedido do
  autor ("aumente a opacidade para 70%"), depois de ver o texto atravessado
  pelas curvas com 55%. `OPACIDADE_TOOLTIP = 0.70`; o gráfico por trás
  continua visível, com menos interferência no texto. Verificado por
  captura; 5 testes passam.

- **(2026-10-03) Lupa "Ampliar gráfico" nos cards dos gráficos, só no
  desktop (opção A).** O autor perguntou se seria possível "um ícone de lupa
  dentro do card do gráfico que de alguma forma dá um zoom". O assistente
  verificou que o `LineChart` do Flet 1.0.0 **não tem zoom nem pan** (só
  `min_x/max_x/min_y/max_y`) e levou três opções: **A** lupa que abre o
  gráfico ampliado num diálogo; **B** modo de zoom por botões `+`/`−`/
  redefinir; **C** diálogo com seletores de faixa. O autor escolheu **A** e
  disse que "o celular não precisa desse zoom". **Implementação:** ícone
  `ZOOM_IN` ao lado do título dos cards "Diagrama P-x-y" e "Coeficientes de
  atividade (ln γ)", **só no layout de desktop** (`com_lupa=True` em
  `construir_grafico_*`; no celular os cards ficam como estavam — captura a
  360px **idêntica pixel a pixel** à do commit anterior). Ao clicar abre um
  `AlertDialog` (até 92% da largura e ~88% da altura da janela, fecha no X, no
  Esc ou clicando fora) com título, legenda e um gráfico **novo** — não é o
  mesmo controle, porque um controle não pode ter dois pais: séries copiadas
  por `clonar_series` (`dataclasses.replace`, que gera ids novos; `deepcopy`
  duplicava o id interno), `novo_tooltip()` (agora função, usada também nos
  dois gráficos dos cards), eixo vertical novo com o mesmo passo e limites
  do card, eixo x com passo 0,1 (cabe no tamanho grande), e legenda montada
  por `montar_legenda_pxy`/`montar_legenda_gamma` (refatoradas de blocos
  fixos para funções), com a coluna "Comparativo" só se "Comparar" estiver
  ativo. Os botões da lupa são criados uma vez e reaproveitados entre
  montagens de layout (como `botao_comparar`); começam apagados e
  `gerar_grafico`/`calcular_comparativo` os acendem quando há gráfico.
  **Limites:** o diálogo mostra o gráfico **como está no momento do clique**
  (não acompanha mudanças feitas com ele aberto — fechar e reabrir); é
  tamanho grande, não zoom de região. Verificado por captura a 1400px com o
  CSV de etanol/água e "Comparar" ativo (P-x-y e ln γ, inclusive o tooltip
  dentro do diálogo); 5 testes passam.

- **(2026-10-06) Modo aula: sem co-op, cada aluno com o seu app.** Depois
  de levar ao autor as opções de servidor e a análise de senha + chave de
  sessão (ideia registrada em "Atualizações futuras"), o autor repensou e
  decidiu que o mais prático é **sem cooperação automatizada**: o professor
  pede para cada aluno ir fazendo o que for necessário, cada um no próprio
  app. Descartados servidor compartilhado, `pubsub`, chave de sessão e senha
  de professor. Motivo dado: praticidade, diante da rede instável da
  universidade e do custo de manter um modo compartilhado. Ponto que sobra,
  levantado por ele mesmo: compartilhar um CSV na hora da aula — opções
  registradas em "Distribuição de CSV na aula", sem escolha ainda.

- **(2026-10-06) Botão "Importar dados" com diálogo de três opções: arquivo
  CSV, colar texto e exemplo.** Fecha a pendência de distribuir dados na aula
  sem co-op. O autor escolheu reaproveitar o botão de importação existente,
  abrindo uma caixa de decisão ("importar exemplo ou a partir do
  dispositivo") e, entre as opções que o assistente levou, **gostou também de
  "colar texto de dados"**; ficaram de fora o link/QR e a distribuição só
  fora do app. **Implementação:** o botão "Importar CSV" virou "Importar
  dados" e abre um `AlertDialog` (estilo dos demais diálogos) com: *Arquivo CSV
  do dispositivo* (o seletor de antes, ainda criado no clique); *Colar texto*
  (segundo diálogo com campo multilinha; uma linha por ponto, na ordem P, x₁,
  y₁; separador espaço, tab, `;` ou vírgula; vírgula decimal aceita; cabeçalho
  opcional em qualquer ordem; erro mostrado no próprio diálogo, que continua
  aberto); *Exemplo: Etanol/água, 50 °C* (lê `referencias/
  etanol_agua_50C_isotermico.csv`, 14 pontos; o CSV só traz P, x, y, então
  componentes e temperatura continuam sendo escolhidos na tela — o rótulo diz
  de que sistema se trata). As três origens passam pela mesma
  `aplicar_importacao` (substitui a tabela, redesenha e avisa quantos pontos
  entraram e quantas linhas foram ignoradas). Para a lista de exemplos
  crescer, basta acrescentar uma linha em `EXEMPLOS_CSV`. Mensagens passaram a
  dizer a origem ("arquivo CSV", "texto colado", "exemplo: …"). **Escolhas do
  assistente, a confirmar:** rótulo do exemplo curto para caber a 360px
  (versão com "(14 pontos)" transbordava o botão); largura do diálogo
  limitada a 420px no desktop e `largura da página − 120` no celular; os
  diálogos são criados novos a cada clique (regra de não mutar controle já
  criado). Verificado por captura de tela a 1400px (os três caminhos,
  inclusive o seletor de arquivo e o texto colado com vírgula decimal e uma
  linha inválida de propósito, avisada como "1 linha(s) ignorada(s)") e a
  360px (menu e diálogo de colar); testes passam, com o novo
  `teste_importar_texto.py`. Não conferido no aparelho real (Termux).
  **Superada em parte no mesmo dia: a opção "Exemplo" foi removida** (entrada
  seguinte); o diálogo ficou com *Arquivo CSV* e *Colar texto*.

- **(2026-10-06) Remover o exemplo "Etanol/água, 50 °C" por falta de fonte
  confiável; buscar dataset de fonte aberta.** O autor perguntou a origem do
  CSV de exemplo. Resposta: não identificada. O arquivo entrou em `0cce3f8`
  (2026-09-27) vindo de uma busca no Google, sem autor, artigo ou referência;
  o próprio autor confirmou que era "apenas pra testes" e "não possui grau de
  confiança aceitável por não definir a fonte". **Checagens feitas pelo
  assistente (física, sem apontar fonte):** (a) as pontas batem com a pressão
  de vapor pura do `thermo` (12,33 kPa e 29,35 kPa contra 12,35 e 29,41 kPa a
  50 °C), logo o arquivo é plausível nos extremos; (b) mas o azeótropo do
  arquivo está em P = 34,42 kPa, quando o azeótropo etanol/água a 50 °C fica
  perto de 29,7 kPa; (c) P cai de 34,21 para 29,35 kPa entre x₁ = 0,941 e 1,
  um degrau que o par real não tem; (d) γ₁ implícito pela Raoult modificada em
  x₁ ≈ 0,9 sai 1,17, contra ≈ 1,0 esperado perto do azeótropo; (e) o teste da
  área (Redlich-Kister) deu D ≈ 24,5 %, contra o critério D < 10 %; (f) os
  modelos do banco (NRTL/UNIQUAC) erram P em 17–18 % contra ele. Conclusão: o
  dado não é confiável como validação. **Decisão do autor: "Remova o exemplo e
  procure um dataset com fonte aberta".** **Feito:** o botão "Exemplo" saiu do
  diálogo "Importar dados" (`EXEMPLOS_CSV`, `PASTA_EXEMPLOS` e
  `importar_exemplo` removidos de `fletando_grafico.py`; a opção de exemplos
  embutidos deixa de existir até haver dado com fonte), o teste de exemplos
  foi trocado por um teste de leitura de CSV em `teste_importar_texto.py`, o
  texto-dica do campo "Colar texto" deixou de usar números do arquivo, e o
  arquivo `referencias/etanol_agua_50C_isotermico.csv` foi apagado (continua
  no histórico do git, no commit `0cce3f8`). **Efeitos em registros
  anteriores:** os números de ΔP/Δy do item 4 de "Próximos passos" (NRTL
  chute × Barker) não valem como validação — ver a ressalva lá —, e as
  capturas de tela de estética feitas "com o CSV de etanol/água" serviram só
  para ver o layout, não para conferir valores. **Escolha do assistente, a
  confirmar:** apagar o arquivo em vez de mantê-lo marcado "sem fonte"; se o
  autor preferir guardá-lo, é recuperar do commit citado. **Busca do dataset
  aberto: em andamento.** Fontes verificadas até aqui: o arquivo público do
  NIST ThermoML (`doi:10.18434/mds2-2422`, dados públicos, extraídos de
  artigos de JCED, J. Chem. Thermodyn., Fluid Phase Equilib., Thermochim. Acta
  e Int. J. Thermophys., 2003–2019, com DOI do artigo de origem por entrada)
  parece o candidato mais citável; o servidor `trc.nist.gov` é bloqueado para
  `curl` neste ambiente (só a ferramenta de busca acessa as páginas), então a
  extração dos números e a checagem de consistência ainda não foram feitas.
  **Primeira rodada de busca (2026-10-06), sem dataset aproveitável:**
  descartados — tabelas em Scribd/Chegg/Studocu/ResearchGate (reproduções sem
  rastreio da fonte, mesmo problema do CSV removido); a tabela de metanol/água
  do livro da Cambridge (copyright, e isobárica, 1 atm); o artigo da UFRN
  sobre acetato de etila + metanol/etanol (isobárico a 70 kPa, copyright
  Elsevier, e a extração do PDF trouxe pontos lidos de gráfico, não a tabela
  original); o artigo MDPI sobre THF (CC BY, mas as tabelas estão como
  imagem). Revisão MDPI *Chemistry* 2023, 5(4), 165 (CC BY) lista as fontes
  primárias de etanol/água isotérmico (Pemberton & Mash 1978 a 303–363 K; Vu et
  al. a 313,15 K; Mertl 1972 a 313–343 K; Dalmolin et al., só P-x) e as
  qualifica pelo teste de consistência, mas não reproduz os números. Caminhos
  em aberto, **a escolher pelo autor:** (1) escolher no arquivo NIST ThermoML
  um artigo isotérmico de par suportado pelo app e extrair os pontos (precisa
  de um DOI; o servidor do NIST só responde à ferramenta de busca); (2) o
  autor indicar uma tabela de livro/artigo a que tenha acesso (o exemplo
  citaria a referência completa); (3) exemplo **sintético**, gerado por um
  modelo com parâmetros do banco IPDB e rotulado como tal — não é dado
  experimental, mas é transparente e serve para demonstrar o app; (4) ficar
  sem exemplo. Nenhum dataset foi incorporado.
  **Segunda rodada, caminho (1) tentado a pedido do autor ("Tente o ThermoML
  do NIST") — 2026-10-06.** O `trc.nist.gov` segue bloqueado para `curl`, mas
  a ferramenta de raspagem (Firecrawl) alcança a API de busca
  (`/ThermoML-API/objects?query=…`, Lucene, só metadados) e o JSON de cada
  artigo (`/ThermoML/<DOI>.json`, com os pontos). **Etanol + água no arquivo:**
  só dois artigos binários — Voutsas et al., *Fluid Phase Equilib.* 308 (2011)
  135–141 (`10.1016/j.fluid.2011.06.009`, **isobárico**, fora do modo atual) e
  Cristino et al., *Fluid Phase Equilib.* 341 (2013) 48–53
  (`10.1016/j.fluid.2012.12.014`, T, P, x, y, 76 pontos). Outros pares
  testados (metanol/carbonato de dimetila, `10.1016/j.fluid.2005.05.002`) têm
  só P-x, sem y, e não servem para a tabela do app. **Candidato extraído:**
  Cristino, flow apparatus, composições por calibração de densidade, em cinco
  temperaturas nominais (363,3 K — 12 pontos; 381,4 K — 26; 403,5 K — 9;
  423,2 K — 16; 423,7 K — 13). x e y são do **etanol** (componente 1 no app).
  Pontos de checagem, com as funções do próprio app (não com o CSV removido):
  (a) γ implícito por Raoult modificada varia suavemente com x₁ e tende a 1
  para o componente em excesso; (b) os modelos com parâmetros do banco IPDB,
  **sem ajuste aos dados**, reproduzem os pontos — a 363,3 K: Wilson
  ΔP 0,5 %/Δy 0,024, UNIFAC 0,9 %/0,021, NRTL 1,1 %/0,029, UNIQUAC
  1,3 %/0,030; a 381,4 K: Wilson 0,8 %/0,017, NRTL 1,4 %/0,022, UNIQUAC
  1,6 %/0,022, UNIFAC 2,3 %/0,020 — contra 17–18 % do CSV removido; (c) a
  regressão de Barker converge com resíduo ≈ 0,011–0,014 (Van Laar, NRTL com
  α₁₂ = 0,3, Wilson) e, ajustando só P e y, o Barker reduz o Δy (ex.: 363,3 K,
  Wilson 0,024 → 0,009) com ΔP ≈ 1 % — o oposto do que aquele CSV mostrava.
  **Limites a declarar:** a faixa de x₁ não é completa (363,3 K: 0,16–0,99, sem
  pontos abaixo de 0,16 nem entre 0,79 e 0,997; 381,4 K: 0,017–0,79 mais um
  ponto em 0,997), então o teste da área (Redlich-Kister) **não é conclusivo**
  nessas faixas parciais (deu D ≈ 37 % e 21 %, mas sobre meia faixa); as
  temperaturas são altas (90–108 °C, P de 125 a 296 kPa), bem acima das de
  aula típicas; a T a informar no app é 90,15 °C ou 108,25 °C; o ThermoML
  avisa que os números foram extraídos pelo TRC e **não avaliados
  criticamente**. **Citação a usar se incorporado:** Cristino, A. F. et al.
  *Fluid Phase Equilib.* **341**, 48–53 (2013), doi:10.1016/j.fluid.2012.12.014,
  via NIST/TRC ThermoML Archive (Riccardi et al., doi:10.18434/mds2-2422;
  *J. Comput. Chem.* **43**, 879, 2022; dados públicos). CSVs-rascunho fora do
  repositório (escopo da sessão). **Aguarda decisão do autor:** incorporar (e
  qual isoterma: 363,3 K tem 12 pontos e é a mais didática; 381,4 K tem 26 e é
  a mais densa) ou buscar outro par/temperatura mais baixa.
  **Auditoria do que foi "calibrado" com o CSV removido (2026-10-06, a
  pedido do autor: "minha preocupação não é o exemplo em si, mas o que foi
  calibrado através dele").** Método: histórico do git desde `0cce3f8`
  (2026-09-27, commit que trouxe o CSV), diff das constantes de ajuste e
  leitura das mensagens de commit. **Resultado: nenhum parâmetro, limite,
  chute inicial ou regra do motor de cálculo foi ajustado com esse dado.**
  (1) *Regressão de Barker* (`REGRESSAO_MODELOS`: chutes iniciais, limites,
  α₁₂ = 0,3) foi escrita em `59786e5` (2026-09-26), **um dia antes** do CSV, e
  testada só com dados sintéticos (`teste_regressao_barker.py`); essas
  constantes **não mudaram** desde então. (2) *Sliders* (faixas e valores
  iniciais) vêm de `19c3ae2` (2026-09-26); desde então só os rótulos ganharam
  subscritos. (3) *`gemini.py`* depois do CSV só mudou nos UNIQUAC (sinal do
  banco, r/q do ChemSep, selo) e em `x1_values`, validados contra o
  `thermo.UNIQUAC`, não contra o CSV. (4) *Testes automatizados*: nenhum
  lia o CSV, exceto o teste de "exemplos embutidos", já removido.
  **O que o CSV influenciou, e fica sem lastro:** (a) **o argumento empírico
  da métrica ΔP/Δy** (`048f03e`): "Barker melhora P mas piora y" era
  artefato de dado inconsistente; com o dado do NIST (Cristino 2013) o Barker
  reduz **os dois** (Wilson a 363,3 K: Δy 0,024 → 0,009, ΔP ≈ 1 %). A
  **fórmula** da métrica (ΔP relativo, Δy absoluto, RMS, separados) foi
  decidida por argumento teórico e não depende do dado — mas o exemplo
  numérico usado para ilustrá-la deve sair do texto do TCC; (b) a
  **"validação" visual** da comparação, da legenda, dos marcadores, dos
  tooltips, da lupa e do layout no celular: serviu para ver forma e
  legibilidade, **não** para conferir valores — essas decisões são de
  apresentação, não de física; (c) as capturas com "ΔP = 90,41 %"
  (Margules 1P com A = 0,5 contra esse CSV) não significam nada; (d) o
  `CLAUDE.md` e o mapeamento (seção 3, `referencias/`) citavam o CSV como
  "dataset real" — o mapeamento foi corrigido hoje. **Achado a favor:** o
  bug do slider fora do intervalo (`64567d6`) apareceu testando CSV + Barker,
  mas é real independentemente do dado (valores do banco e da regressão
  podem cair fora do recorte do slider). **Risco que sobra, não resolvido:**
  nenhum dado experimental confiável **dentro do repositório** valida a
  regressão e a métrica — **resolvido logo abaixo**.
  **Recalibração com dado confiável (2026-10-06, ordem do autor: "o que
  tiver sido calibrado tem que recalibrar com dados confiáveis").** Como a
  auditoria acima não achou constante do motor ajustada ao CSV removido, a
  recalibração foi **verificar cada constante e cada alegação contra o dado
  do NIST (Cristino 2013, 5 isotermas, 76 pontos)** e contra dados sintéticos
  de parâmetro conhecido. O dado foi para `referencias/nist_thermoml_cristino2013_etanol_agua_isotermas.csv`
  (fonte e ressalvas no cabeçalho) e a verificação virou
  `testes/teste_validacao_nist_etanol_agua.py` (reprodutível; passa). **Isso
  é fixture de teste, não exemplo da UI** (até 2026-10-07; ver a decisão do
  autor logo abaixo). Resultados:
  1. **Métrica ΔP/Δy (item 4 de "Próximos passos"): refeita.** Com dado
     confiável o Barker reduz **os dois** erros (ex.: 363,3 K, Wilson: Δy 0,024
     → 0,009, ΔP 0,5 % → 1,0 %, ou seja, ΔP ≈ constante); a alegação antiga
     ("Barker melhora P mas piora y") **era artefato** do CSV sem fonte e deve
     ser **descartada** do texto do TCC. A fórmula (dois números separados,
     RMS) segue válida por razão teórica.
  2. **Modelos do banco sem ajuste** reproduzem o dado: ΔP 0,5–3,5 % e Δy
     0,016–0,038 (NRTL, Wilson, UNIQUAC); UNIFAC chega a ΔP 4,7 % a 150 °C
     (esperado: preditivo, sem parâmetro por par). Contra 17–18 % no CSV removido.
  3. **Regressão de Barker**: todas as 5 isotermas × 5 modelos convergem, sem
     parâmetro preso no limite, resíduo 0,007–0,023. **α₁₂ = 0,3 do NRTL**:
     resíduo praticamente insensível a α₁₂ ∈ {0,2; 0,3; 0,47} (diferenças ≤
     0,0022) — a decisão de fixar é sustentada pelo dado. **Sensibilidade ao
     chute inicial** (30 chutes aleatórios por isoterma): Margules 2P, Wilson,
     NRTL e UNIQUAC chegam ao mesmo mínimo em 150/150; **o Van Laar não**.
  4. **Bug achado e corrigido (Van Laar com desvio negativo).** Testando
     recuperação com dado sintético (o teste só cobria Margules 1P, NRTL e
     UNIQUAC; Margules 2P, Van Laar e Wilson **nunca tinham sido testados**),
     o Van Laar com A₁₂, A₂₁ < 0 (desvio negativo da idealidade, como
     acetona/clorofórmio) **não recuperava os parâmetros** do chute inicial
     positivo [0,5; 0,3]: terminava em solução espúria (resíduo ≈ 0,08), num
     caso com `sucesso=True` e parâmetro colado no limite (A₁₂ = 5) — resposta
     errada com selo "Calculado". Causa: o Van Laar é singular com A₁₂ e A₂₁ de
     sinais opostos. **Correção** em `regress_params_barker`: chutes extras por
     modelo (`chutes_extras`; Van Laar ganhou [−0,5; −0,3]) e fica o de menor
     resíduo. Testes novos em `teste_regressao_barker.py` (Margules 2P, Van
     Laar e Wilson, desvio + e −, em etanol/água e acetona/clorofórmio — Van
     Laar − **falhava antes e passa agora**). Os dados reais de etanol/água
     (desvio +) não eram afetados. Correção de corretude aplicada sem
     proposta (mesmo critério do bug do UNIQUAC); escolha de chute extra em
     vez de restringir o sinal é do assistente, **a confirmar**.
  5. **Faixas dos sliders (só recorte de exploração, não limite físico):**
     valores ajustados ao dado real passam do intervalo [−2, 2] em **Van Laar
     A₁₂ (2,06 a 150 °C)** e **NRTL τ₂₁ (até 2,49)**; `64567d6` já impede que
     isso quebre a tela (a posição do botão é limitada, o cálculo usa o valor
     real). **Proposta, não aplicada (decisão de UI do autor):** ampliar para
     [−3, 3] nesses dois parâmetros. Chutes iniciais e limites da regressão
     ([−5, 5] etc.) acomodam todos os valores obtidos.
  **Nada mais foi alterado**: os chutes, limites e α₁₂ = 0,3 ficaram como
  estavam, porque o dado confiável os confirmou.
  **Decisão do autor, 2026-10-07: "Sim, amplie os sliders e incorpore o
  dado".** Executado: (1) **sliders** Van Laar (A₁₂, A₂₁) e NRTL (τ₁₂, τ₂₁) de
  [−2, 2] para **[−3, 3]** (`PARAM_SLIDERS`; sem `divisions`, então a
  granularidade não muda; Margules, Wilson e α₁₂ ficaram como estavam).
  (2) **dado incorporado como exemplo na UI**: o diálogo "Importar dados" voltou
  a ter dois botões de exemplo, **"Exemplo: etanol/água, 90 °C"** (363,3 K, 12
  pontos) e **"Exemplo: etanol/água, 108 °C"** (381,4 K, 26 pontos), lidos de
  `referencias/nist_thermoml_cristino2013_etanol_agua_isotermas.csv` por
  `carregar_exemplo_nist`. **Diferente do exemplo antigo**, ao carregar ele
  também preenche **componentes (ethanol/water) e temperatura (90,15 ou
  108,25 °C)** — só `.value` dos campos —, porque o dado só vale a essa T (o
  antigo deixava T = 70 °C e produzia ΔP sem sentido). A mensagem de status
  traz a **fonte** (Cristino et al., *Fluid Phase Equilib.* 341 (2013) 48-53,
  via NIST ThermoML) e os **limites** ("faixa de x₁ incompleta, T elevada").
  **Escolha do assistente, a confirmar:** só duas das cinco isotermas (as 403,5
  e 423 K têm T ainda mais alta e menos pontos); o rótulo arredonda a T para
  caber a 360 px. Verificado por captura a 1400 px (importar 90 °C → 12 pontos,
  T = 90,15, "Comparar" funcionando) e a 360 px (diálogo com os 4 botões, sem
  corte); novo teste `teste_exemplos_nist` em `teste_importar_texto.py`;
  testes passam. A mensagem com a fonte some quando o usuário clica em
  "Comparar" (a mensagem de status é única) — a citação continua no CSV e aqui.
  **Terceira rodada de busca no ThermoML, 2026-10-07 — pedido do autor: "vc se
  prendeu a etanol e água? ... qualquer outro par servia ... busque por outros
  pares que satisfaçam a maior parte dos pontos em aberto, pois a questão do
  azeótropo é de grande importância".** **Resposta ao pergunta:** sim — etanol/
  água foi só o par padrão do app e do CSV removido, sem mérito próprio.
  **Método:** consultas à API do ThermoML (títulos com "isothermal/vapor/
  vapour/equilibri*" e pares clássicos: acetona, metanol, etanol, aromáticos,
  clorados, água) e filtro local pelo `data_summary` (binário, com P **e**
  fração molar de y, ≥ 8 pontos); depois leitura do JSON de cada candidato,
  checagem de T, faixa de x₁, azeótropo, teste da área e modelos do app. O
  arquivo é dominado por refrigerantes (HFC/HFO); entre os de interesse didático
  (T ≤ 100 °C): **descartados** 2-propanol + n-hexano e + n-heptano (Fluid
  Phase Equilib./JCED 2003-04: "near the critical region", T ≈ 210 °C),
  cloroformio + MIBK (`10.1016/j.jct.2006.07.004`, 303,15 K, 16 pontos, desvio
  negativo, **reprovado no teste da área: D = 33–46 %**, e P do MIBK puro 12 %
  acima da Psat do thermo), propan-1-ol + dodecano (sem azeótropo), cicloexano +
  cicloexanona (sem azeótropo), ácido fórmico + água (associação em fase vapor
  invalida a Raoult com gás ideal). **Dois candidatos aprovados:**
  (1) **Metanol + 2,3-dimetil-2-buteno**, Fluid Phase Equilib. 2011,
  `10.1016/j.fluid.2011.07.014`: 4 isotermas (343,15; 353,15; 363,15; 373,15 K =
  70–100 °C), 19–23 pontos cada, **x₁ de 0 a 1 com os dois puros medidos** (P
  dos puros dentro de 0,1 % da Psat do thermo), **azeótropo de pressão máxima**
  (mínimo ponto de ebulição) em x₁ ≈ 0,58–0,63 (P_az 191 a 499 kPa contra puros
  de 91–125 a 219–354 kPa), **teste da área D = 2,8 / 4,4 / 4,8 / 6,5 %**
  (< 10 %, **consistente**). Barker: ΔP 1,0–2,0 %, Δy 0,011–0,025 (Wilson o
  melhor). O azeótropo previsto pelos modelos ajustados cai a 0,004–0,015 do
  experimental em x₁ (343 K: 0,575 exp. × 0,579 Wilson; 373 K: 0,626 × 0,641).
  (2) **Clorofórmio + 2-butanona (MEK)**, J. Chem. Eng. Data 2006,
  `10.1021/je060150a`, **303,15 K (30 °C)**, 22 pontos, x₁ de 0 a 1, desvio
  **negativo** e **azeótropo de pressão mínima** (máximo ponto de ebulição) em
  x₁ ≈ 0,19–0,20, P ≈ 15,3 kPa (confirmado pelos autores no resumo), **D =
  3,4 %** (consistente). Barker: ΔP 1,5–1,6 %, Δy 0,008–0,009; parâmetros do
  Van Laar A₁₂ = −0,97, A₂₁ = −1,33 (ambos < 0, como previsto). O azeótropo dos
  modelos ajustados sai em x₁ ≈ 0,146 (contra 0,19–0,20) — o modelo reproduz a
  existência e a P (15,0 kPa), mas **não a composição com precisão** (a região
  fica quase plana). **Efeito sobre achados anteriores:** o dado do (2) é a
  **confirmação com dado real** do bug do Van Laar com desvio negativo: sem o
  chute extra a regressão termina em A₁₂ = 0,995, A₂₁ = −0,03, resíduo 0,176,
  `sucesso=False`; com o chute extra, resíduo 0,0125 e parâmetros acima.
  Os dois pares cobrem os **dois tipos de azeótropo** (mínimo e máximo ponto de
  ebulição) e o **desvio negativo real**; etanol/água cobre a validação com
  banco IPDB. **Limites:** nenhum dos dois pares tem parâmetros no IPDB (NRTL,
  Wilson, UNIQUAC) nem grupos UNIFAC na tabela do app, então **só a regressão
  de Barker** (botão "Calcular por Regressão") se aplica — é o caso de uso
  original da regressão (par sem banco); o metanol/olefina é menos conhecido
  pelos alunos que etanol/água; os dados são do TRC/NIST, não avaliados
  criticamente.
  **Decisão do autor, 2026-10-07: "Opção 3, incorpore os dois pares como
  fixtures de teste."** Ficou **só como fixtures de teste** nesse momento
  (**revisto no mesmo dia: o autor pediu que também fossem exemplos de tela —
  ver a última entrada desta seção**). **Feito:** (1) `referencias/nist_thermoml_feng2011_metanol_dimetilbuteno_isotermas.csv`
  (Feng, Dong e Li, *Fluid Phase Equilib.* 309 (2011) 201-205,
  doi:10.1016/j.fluid.2011.07.014; 4 isotermas, 85 pontos) e
  `referencias/nist_thermoml_clara2006_cloroformio_mek_303K.csv` (Clara,
  Marigliano e Solimo, *J. Chem. Eng. Data* 51 (2006) 1473-1478,
  doi:10.1021/je060150a; 22 pontos), com fonte e ressalvas no cabeçalho;
  componente 1 = metanol / clorofórmio. (2) `testes/teste_validacao_azeotropos_nist.py`
  (sai com código 1 se algo fugir): P dos puros contra a Psat do `thermo`;
  azeótropo presente no dado e do tipo esperado; regressão de Barker
  (Margules 2P, Van Laar, Wilson, NRTL com α₁₂ = 0,3) convergindo sem parâmetro
  no limite, com ΔP/Δy pequenos; azeótropo do modelo ajustado do tipo certo e
  perto do experimental; Van Laar com A₁₂, A₂₁ < 0 no desvio negativo.
  **Medido** (tolerâncias fixadas depois de medir, nada do motor foi ajustado):
  metanol/dimetilbuteno — ΔP 1,0–2,0 %, Δy 0,011–0,025, azeótropo do modelo a
  ≤ 0,015 do experimental em x₁; clorofórmio/MEK — ΔP 1,5–1,6 %, Δy 0,008–0,009,
  Van Laar A₁₂ = −0,970, A₂₁ = −1,329, mas azeótropo do modelo em x₁ ≈ 0,14–0,15
  contra 0,191 do dado (diferença de ~0,05: a região é quase plana, o modelo
  acerta existência e tipo, não a composição com precisão). **Achados de
  honestidade:** (a) no clorofórmio/MEK o P medido da 2-butanona pura (15,74 kPa)
  fica 3,2 % acima da Psat do `thermo` (15,25 kPa); tolerância do teste nesse
  sistema é 4 % por isso; (b) no metanol/dimetilbuteno a 363,15 K há um ponto
  medido exatamente sobre o azeótropo (x = y = 0,612), tratado no teste;
  (c) a regressão do Van Laar emite um `RuntimeWarning: overflow in exp`
  durante os passos de tentativa do otimizador no metanol/dimetilbuteno a
  70 °C — não afeta o resultado final (o mesmo dos demais modelos), mas fica
  aparecendo na saída do teste. Nenhum dos dois pares tem parâmetros no IPDB
  nem grupos UNIFAC na tabela do app, então só a regressão de Barker é
  testada; UNIQUAC e os modelos do banco não se aplicam. Suíte inteira passa.
  **Sobre o 1,4-dioxano/metanol (2026-10-07):** o autor informou que o par veio
  **de um exercício do professor, sem fonte conhecida**. A busca no ThermoML
  (159 artigos com os dois termos) não achou dado binário de equilíbrio
  líquido-vapor desse par; o dioxano/metanol segue sem dado experimental com
  fonte no repositório — usado só como teste de mecânica do motor (parâmetros
  do IPDB e dados sintéticos). A frase "já testado contra dados de literatura"
  do mapeamento (seção 2, 308,5 K) foi **reescrita no mesmo dia, por ordem do
  autor ("Sim, reescreva a frase do mapeamento, depois que o professor me
  disser ai mudamos")**: agora diz que o par vem de exercício do professor, sem
  fonte conhecida, e que não há validação experimental com fonte desse par no
  repositório. Redação **provisória**: o autor vai perguntar ao professor a
  origem do dado e então a frase é revista.

- **(2026-10-06) Texto do dropdown de modelo cortado no celular.** Relatado
  pelo autor com captura do aparelho: "Margules (1-P)" saía cortado
  ("Margules (1-" e um pedaço do P) no card "Sistema". Causa: o texto precisava
  de ~10px a mais do que o espaço entre o ícone e a seta, nos 200px do campo;
  na captura da nuvem cabia por muito pouco (a fonte do aparelho renderiza um
  pouco mais larga), por isso não tinha aparecido antes. **Tentativa
  descartada:** zerar o recuo horizontal interno (`content_padding`) só do
  dropdown — o texto não se moveu um pixel, o Dropdown ignora essa propriedade.
  **Correção aplicada (escolha do assistente, **confirmada pelo autor em 2026-10-06**: "pode manter sem parênteses"):** o texto exibido
  passou a ser sem parênteses ("Margules 1-P", "Margules 2-P"), via
  `ft.dropdown.Option(key=nome, text=...)`; a chave continua sendo o nome de
  `MODELS_GE`, então nada mais muda no código. Alternativas não adotadas:
  diminuir a fonte (abaixo do piso de 14px do item 6 da estética), tirar o
  ícone (o autor pediu ícones nas caixas) ou alargar o campo (no desktop dois
  campos de 200px já ocupam os ~420px do card). Verificado por captura a 360px
  (texto com folga, lista aberta e troca para Margules 2-P com os sliders
  A₁₂/A₂₁); os 5 testes passam. Não conferido no aparelho real.

- **(2026-10-06) Valor do parâmetro digitável, além do slider.** Pedido do
  autor: "quero que o valor do parâmetro também seja digitável". O texto fixo
  "A = 0.5" ao lado de cada slider virou um **campo de texto** com o rótulo do
  parâmetro (A, A₁₂, Λ₁₂, τ₁₂, α₁₂…) flutuando na borda, no estilo das caixas
  do card "Sistema" (`ESTILO_CAIXA_SISTEMA`, 100px). Confirma com Enter ou ao
  sair do campo; vírgula decimal aceita; só entram dígitos, `.`, `,` e `-`.
  O slider acompanha (a posição do botão é limitada ao intervalo do slider, o
  **valor usado no cálculo não** — mesmo critério de banco e regressão, cujos
  valores podem cair fora dele), o selo de origem passa a "Fornecido"
  ("digitado manualmente") e o gráfico é redesenhado. Arrastar o slider
  continua atualizando o campo. **Regras de validação (escolhas do
  assistente, a confirmar):** valor não numérico ou infinito é recusado e o
  campo volta ao anterior, com aviso vermelho na mensagem de status; **Λ₁₂ e
  Λ₂₁ (Wilson) só aceitam valor maior que zero** (log de Λ); α₁₂ do NRTL
  não tem limite além de ser número (o intervalo 0,2–0,47 é só do slider) e,
  como no slider, não muda o selo. Sair do campo **sem editar** não reescreve
  o valor: o campo mostra 4 algarismos (`formatar_parametro`, antes eram 3 no
  texto fixo) e o parâmetro vindo da regressão ou do banco pode ter mais —
  sem essa guarda, só clicar e sair trocaria o valor preciso pelo
  arredondado e o selo "Calculado"/"Banco de dados" por "Fornecido". Digitar
  não empilha no histórico do "Desfazer" (mesma regra do slider: é o próprio
  usuário no controle). Verificado por captura de tela a 1400px (digitar
  `1,2` + Enter: slider e gráficos mudam; `-0.5` confirmado ao sair do campo;
  campo vazio volta ao valor com aviso) e a 360px (Wilson: Λ = 0 recusado;
  "Buscar do Banco" preenche 0.1759/0.7991 com selo "Banco de dados"; entrar
  e sair do campo sem editar não altera nada); os 5 testes passam.
  **Dois achados, tratados no mesmo dia (autor: "sim"; depois pediu
  expressamente "o erro agora no card de parâmetros"):** (a) o aviso de valor
  inválido aparecia na mensagem de status do card "Dados experimentais",
  longe do campo no celular, onde os cards ficam empilhados. Agora é um texto
  vermelho (`aviso_parametro`) **dentro do card "Parâmetros do modelo"**, logo
  abaixo dos campos; some quando um valor válido é aceito, quando o slider é
  movido e ao trocar de modelo. Criado uma vez e reaproveitado entre
  montagens (só `value`/`visible` mudam, como no selo de origem). Verificado a
  360px (Wilson, Λ₁₂ = 0 → aviso no card; `0,5` + Enter → aviso some).
  (b) o "-0.00" do eixo do ln γ: o Flet gera os marcadores somando o passo a
  cada volta, e o ruído de ponto flutuante fazia o zero sair como −2e-16.
  Reproduzido num app de teste isolado e corrigido com **rótulos explícitos**
  (`rotulos_eixo`, usado por `eixo_vertical` nos dois gráficos e na lupa):
  cada rótulo é `k × passo` e o zero é escrito "0". Efeito visível: os rótulos
  passam a ter o número mínimo de casas do passo (0,1 → "0.1", antes "0.10";
  0,25 → "0.25"). Testado em A = −0.5, 1.2, 0.35 e −2 e na lupa: todos os
  marcadores aparecem e o zero sai "0". Risco conhecido: se o Flet deixasse
  de casar um rótulo com o marcador gerado, o rótulo some — não ocorreu em
  nenhuma faixa testada. Não conferido no aparelho real (teclado numérico do
  Android com vírgula e sinal de menos).

- **(2026-10-06) ΔP/Δy no card "Parâmetros do modelo", não em "Dados
  experimentais".** Pedido do autor: "quero que o erro agora apareça no card
  de parâmetros". **Mal-entendido registrado:** o assistente leu "o erro"
  como o aviso de valor inválido dos campos de parâmetro (que então passou a
  aparecer dentro do card de parâmetros — ver entrada anterior) e só depois o
  autor esclareceu ("falo dos deltas"): era o resultado da comparação,
  `ΔP = …% (RMS)` / `Δy = … (RMS)`, com os ⓘ. **Implementação:** a
  `linha_erro_comparativo` saiu do fim do card "Dados experimentais" (nos dois
  layouts) e passou a ser o último item do card "Parâmetros do modelo", abaixo
  dos botões; o texto, os ícones ⓘ e a regra de aparecer só depois de "Comparar"
  não mudaram. Mantém o `wrap=True`: no celular o Δy desce para a linha de
  baixo, dentro do card. Racional dado: o erro fica junto dos parâmetros que o
  produzem. Verificado por captura a 1400px (exemplo etanol/água + Comparar:
  `ΔP = 90.41% (RMS)`, `Δy = 0.0704 (RMS)` no card de parâmetros) e a 360px; os
  5 testes passam. Os dois avisos (valor inválido e deltas) agora vivem no
  card de parâmetros.

- **(2026-10-06) Bug de sinal no UNIQUAC via banco IPDB (achado pela
  pergunta do autor).** O autor perguntou: "o gráfico do modelo UNIQUAC parece
  ser invertido em relação aos demais, isso é esperado?". **Não era esperado.**
  Calculado à mão para etanol/água a 70 °C, o UNIQUAC dava ln γ **negativo**
  nos dois componentes (γ < 1 em toda a faixa) — fisicamente errado: esse par
  tem desvio positivo forte da idealidade (azeótropo de mínimo ponto de
  ebulição; γ∞ do etanol em água em torno de 5). **Causa:** convenção de sinal
  na ponte com o banco. O IPDB (fonte ChemSep) guarda `bij = −A_ij/R` e o
  `thermo` usa `τ = exp(+bij/T)` (Exemplo 3 da docstring de
  `thermo.uniquac.UNIQUAC`); o `model_uniquac` usa a forma clássica
  `τ = exp(−a/T)`. O adaptador `uniquac_params_from_ipdb` passava `bij` direto
  como `a`, invertendo o sinal de τ. **Correção:** `a12 = −bij[0][1]`,
  `a21 = −bij[1][0]` (uma linha, com comentário). **Verificação:** com o sinal
  trocado, o `model_uniquac` reproduz o exemplo do `thermo` (γ = [1,977; 1,140]
  em x₁ = 0,252) e bate com `thermo.UNIQUAC` em x₁ de 0,01 a 0,99 com erro
  máximo de 1,6e-14; sem a correção o mesmo teste dá γ₁ = 0,93 e erro de 4,08.
  Teste novo em `testes/teste_banco_ipdb.py` (os dois casos acima), que
  **falha no código antigo e passa no corrigido**. No app (etanol/água, 70 °C):
  ln γ₁ de ≈1,5 em x₁=0 e ln γ₂ de ≈0,7 em x₁=1, P-x-y com o líquido acima do
  vapor. **Por que a auditoria de 2026-07-27 não pegou:** ela validou a
  **fórmula** do `model_uniquac` contra `UNIQUAC_gammas` com parâmetros dados,
  mas não a **ponte** que traduz o banco para os parâmetros do modelo — o teste
  do adaptador cobria só Wilson e NRTL (os dois conferidos e corretos: NRTL
  usa `τ = bij/T`, Wilson reproduz a referência da docstring). **Nota da
  correção:** foi aplicada sem pedido explícito, por ser defeito de corretude
  (não escolha de rumo); se o autor preferir outra coisa, a mudança é de uma
  linha. **Achado relacionado, NÃO tratado e a decidir pelo autor:** o app
  calcula r/q do UNIQUAC pelos grupos UNIFAC (decisão de 2026-09-27), mas os
  parâmetros do ChemSep foram ajustados com os r/q **originais** do UNIQUAC
  (etanol 2,11/1,97; água 0,92/1,40). Para o etanol os valores do app são
  2,5755/2,588 (≈22%/31% maiores), o que dá γ₁ = 1,66 em x₁ = 0,252 contra
  1,98 da referência `thermo`/ChemSep — o sinal agora está certo, mas a
  quantidade ainda difere por essa mistura de fontes. Opções: manter (r/q
  UNIFAC, coerente com o resto do app), ou usar r/q do banco do ChemSep quando
  existirem. **Decidido pelo autor no mesmo dia: "Use os r e q do ChemSep
  quando existirem"** — ver a entrada seguinte.

- **(2026-10-06) UNIQUAC: r/q do ChemSep quando existirem, grupos UNIFAC como
  reserva.** Decisão do autor, fechando o achado acima (reverte, para o
  UNIQUAC, o "r/q via grupos UNIFAC" de 2026-09-27). **Fonte:** o banco de
  compostos puros do ChemSep (`Misc/ChemSep8.32.xml`, licença Artistic 2.0)
  que já acompanha o pacote `chemicals` — nenhuma dependência nova; 429 dos
  431 compostos têm `UniquacR`/`UniquacQ`. `_tabela_rq_chemsep()` lê o XML uma
  vez (≈0,3 s, guardado em cache) e `uniquac_rq_from_chemsep(cas)` devolve
  (r, q) ou `None`. **Regra em `montar_parametros_automaticos`:** se os **dois**
  componentes constam no ChemSep, usa os r/q dele; senão, usa os grupos UNIFAC
  nos **dois** (não mistura fontes dentro do par — os a₁₂/a₂₁ foram ajustados
  com o par de r/q do ChemSep). Efeito colateral bom: pares cujos componentes
  não estão na tabela de grupos UNIFAC do projeto passam a funcionar no
  UNIQUAC, desde que haja a₁₂/a₂₁ no IPDB. **Verificação:** etanol sai 2,11/1,97
  e água 0,92/1,40 (os originais; antes 2,5755/2,588 para o etanol); de ponta
  a ponta, `montar_parametros_automaticos("UNIQUAC", "ethanol", "water")` →
  `model_uniquac` reproduz a referência do `thermo` (γ = 1,9775/1,1398 em
  x₁ = 0,252, antes 1,66/1,13). No app: P-x-y de etanol/água com o azeótropo
  (líquido e vapor se encontram em x₁ ≈ 0,85) e ln γ∞ ≈ 1,7 (etanol) e ≈ 1,0
  (água). Testes novos em `teste_banco_ipdb.py` (r/q, ponta a ponta contra o
  `thermo`, e o retorno aos grupos UNIFAC quando o ChemSep não tem r/q). Textos
  do selo de origem e da nota do UNIQUAC atualizados. **Ressalvas:** (a) o
  arquivo XML é dado interno do `chemicals`; a versão está travada no
  `uv.lock`, mas uma atualização do pacote pode mudar o caminho; (b) a
  regressão de Barker não ajusta r/q (são estruturais), então não muda.
  **Endurecido no mesmo dia, a partir de uma pergunta do autor ("isso é um
  problema?").** Verificado: o código do `chemicals` não usa esse XML em lugar
  nenhum (é só dado empacotado) e o nome traz a versão do ChemSep (`8.32`), então
  pode ser renomeado ou removido numa atualização; e, pior, com o arquivo
  ausente o UNIQUAC **quebrava por inteiro** (`FileNotFoundError`) em vez de
  cair nos grupos UNIFAC como a regra prevê. Agora: o arquivo é achado por
  padrão (`Misc/ChemSep*.xml`, `_caminho_xml_chemsep`); arquivo ausente,
  ilegível ou com valor malformado vira "sem dados" (`_tabela_rq_chemsep`
  devolve `{}`) e o UNIQUAC usa os grupos UNIFAC. Teste novo em
  `teste_banco_ipdb.py` (caminho inexistente → cai nos grupos, sem exceção).
  Risco que sobra: se o arquivo sumir, o UNIQUAC volta silenciosamente aos
  r/q do UNIFAC (menos coerente com os a₁₂/a₂₁ do banco, como no achado
  anterior) — sem aviso na tela; o selo de origem diz "do ChemSep (ou, se
  faltarem, UNIFAC)" mas não informa qual valeu em cada caso.
  **Resolvido no mesmo dia (autor: "Sim, o selo deve dizer a fonte"):**
  `uniquac_fonte_rq(comp1, comp2)` devolve `"chemsep"` ou `"unifac"`, pela mesma
  lógica (`_uniquac_rq_do_par`) que monta os parâmetros — não duplica a regra. O
  app chama `atualizar_selo_uniquac` **a cada cálculo** do UNIQUAC (a fonte
  depende dos componentes escolhidos, não só do modelo). **Fonte ChemSep:** chip
  verde "Banco de dados" e, no ⓘ, "r/q do banco ChemSep — os mesmos com que os
  parâmetros de interação foram ajustados; a₁₂/a₂₁ do banco IPDB/ChemSep para
  etanol/água". **Fonte UNIFAC (reserva):** chip laranja próprio, **"Banco, r/q
  via UNIFAC"** (`ORIGENS_SELO["banco_rq_unifac"]`, mesmas cores e mesmo padrão
  do "Calculado (poucos pontos)": a variante menos confiável ganha cor
  diferente, não só texto), e no ⓘ o aviso de que os parâmetros foram ajustados
  com os r/q do ChemSep e o resultado pode se afastar do esperado. **Escolha do
  assistente, a confirmar:** o chip próprio laranja para o caso de reserva (o
  autor pediu que o selo "diga a fonte"; poderia ser só o texto do ⓘ). Teste
  novo em `teste_banco_ipdb.py` (fonte `chemsep` para etanol/água e `unifac`
  quando a tabela não tem r/q). Verificado por captura a 1400px nos dois casos;
  o de reserva foi simulado num processo à parte com a tabela do ChemSep
  esvaziada (nenhum par real do app cai nele hoje: etanol, água, metanol e
  dioxano constam no ChemSep).

- **(2026-10-07) Confirmação, pelo autor, das escolhas do assistente
  pendentes ("Confirmo as escolhas do assistente").** Depois de o assistente
  listar as pendências, o autor confirmou de uma vez as escolhas que as
  entradas acima marcavam como "a confirmar", que passam a valer como
  decisões do projeto: (1) **chute inicial extra do Van Laar** na regressão de
  Barker (`chutes_extras`), em vez de restringir o sinal dos parâmetros;
  (2) **só duas das cinco isotermas de etanol/água** (90 e 108 °C) como
  exemplos do botão "Importar dados", com o rótulo da temperatura
  arredondado para caber a 360 px; (3) **regras de validação do campo de
  parâmetro digitável** (valor não numérico ou infinito recusado, com o campo
  voltando ao anterior; Λ₁₂ e Λ₂₁ do Wilson só maiores que zero; α₁₂ do NRTL
  sem limite além de ser número); (4) **chip laranja "Banco, r/q via UNIFAC"**
  no selo do UNIQUAC quando os r/q vêm dos grupos UNIFAC; (5) **passo 0,2 no
  eixo x** dos dois gráficos; (6) **apagar o CSV antigo sem fonte** em vez de
  mantê-lo marcado (continua recuperável no commit `0cce3f8`); e, no mesmo
  grupo, o rótulo curto do exemplo de importação e a largura do diálogo
  (420 px no desktop, largura da página − 120 no celular). **Não confirmado
  por essa resposta, segue aberto:** a origem do dado de 1,4-dioxano/metanol
  (depende do professor).

- **(2026-10-07) Fechamento das decisões em aberto: exemplos de tela, estética,
  tooltip, alerta do XML do UNIQUAC e Termux.** Resposta do autor à lista de
  pendências: **(1) "quero como exemplos"** — os dois pares novos viram exemplos
  do botão "Importar dados", além de fixtures de teste; **(2) "estética
  encerrada"**; **(3) "tooltip assim pode deixar então"** — o balão fica como
  está (um estilo só, peso e cor herdados da série; letras em negrito com
  números normais não são possíveis no Flet 1.0.0); **(4) "UNIQUAC emita um
  alerta sempre que for feita alguma atualização que possa vir a alterar o XML
  interno"**; **(5) "considere que a visualização no Termux está ok"** — as
  verificações que as entradas anteriores marcavam como "não conferido no
  aparelho real" passam a valer como conferidas pelo autor.
  *(1) Exemplos.* `EXEMPLOS_NIST` (em `fletando_grafico.py`) deixou de ser só
  etanol/água: cada exemplo traz arquivo, coluna, T, componentes, fonte e nota,
  e `carregar_exemplo_nist(exemplo)` lê o CSV certo; para acrescentar um
  exemplo basta uma entrada na lista. Ao carregar, o app preenche componentes e
  temperatura (`methanol`/`2,3-dimethyl-2-butene` a 70 °C; `chloroform`/
  `2-butanone` a 30 °C) e a mensagem de status traz a fonte e a nota (azeótropo
  de pressão máxima em x₁ ≈ 0,58; desvio negativo e azeótropo de pressão mínima
  em x₁ ≈ 0,19). **Escolhas do assistente, a confirmar:** só a isoterma de
  70 °C do metanol/dimetilbuteno (a mais baixa das quatro, a mais próxima de
  temperaturas de aula; 80, 90 e 100 °C seguem só como fixture de teste); os
  rótulos "metanol/dimetilbuteno, 70 °C" e "clorofórmio/MEK, 30 °C" (abreviados
  para caber); e, no diálogo, o texto das opções passou a **quebrar linha**
  (`expand=True`) em vez de transbordar a 360 px, com espaço sem quebra antes de
  "°C" para não separar o número da unidade. Verificado por captura de tela: a
  1400 px o diálogo mostra as seis opções e os dois exemplos novos importam
  (22 pontos cada; componentes e T preenchidos; "Comparar" funciona); a 360 px o
  texto quebra dentro dos botões. **Achados sem correção (cosméticos):** a
  mensagem pós-"Comparar" diz "calculada em N ponto(s) da tabela" contando
  x₁ distintos (21 no clorofórmio/MEK, que tem dois pontos em x₁ = 0,252; o erro
  ΔP/Δy usa os 22); e o campo "Componente 2" corta visualmente
  "2,3-dimethyl-2-butene" em 200 px (o valor está inteiro).
  *(4) Alerta do XML.* O XML de r/q do ChemSep é dado interno do `chemicals`
  (não interface). Em `calculos/gemini.py`: constantes
  `CHEMICALS_VERSAO_VALIDADA` ("1.5.2"), `CHEMSEP_XML_NOME_VALIDADO`
  ("ChemSep8.32.xml") e `CHEMSEP_XML_SHA256_VALIDADO`, e
  `verificar_xml_chemsep()`, que devolve os alertas se a versão do pacote, o
  nome do arquivo ou o conteúdo (SHA-256) divergirem do validado, ou se o
  arquivo sumir. `_tabela_rq_chemsep` emite cada alerta como `RuntimeWarning`
  (uma vez, ao primeiro uso do UNIQUAC; aparece no terminal onde o app roda,
  não na tela) e o UNIQUAC segue funcionando. Novo `testes/teste_xml_chemsep.py`
  **falha com código 1** nessas condições e confere que o alerta dispara quando
  a versão diverge. Procedimento depois de uma atualização do `chemicals` ou do
  `thermo`: rodar o teste; se alertar, revalidar o UNIQUAC com
  `teste_banco_ipdb.py` e, estando correto, atualizar as três constantes.
  **Interpretação do assistente, a confirmar:** "atualização" = mudança da
  versão do `chemicals` ou do conteúdo do XML (a versão sozinha já alerta, mesmo
  sem o XML ter mudado, por precaução); o alerta é de desenvolvedor (terminal e
  teste), não um aviso na tela do aluno. Não foi feito comentário no
  `pyproject.toml` (o `chemicals` não é dependência direta; vem pelo `thermo`).

- **(2026-10-07) Faixa dos sliders do Margules ampliada para [−3, 3].** Pedido
  do autor, depois de testar o exemplo metanol/dimetilbuteno ("fica bem ajustado
  no 1P se A > 2, tipo 2.2. Melhor aumentar a faixa do slide" — escreveu "etanol e
  dimetil butano", mas o exemplo é o do **metanol**). Conferido com a regressão
  de Barker: a 70 °C o Margules 1P ajusta **A = 2,25** (e 2,22/2,18/2,16 a
  80/90/100 °C), acima do limite antigo de 2. `PARAM_SLIDERS`: Margules 1P (A) de
  [−2, 2] para [−3, 3], mesmo critério do Van Laar e do NRTL em 2026-10-07 (faixa
  é recorte de exploração, não limite físico; a regressão e o banco já podiam
  passar do intervalo, com a posição do botão limitada). **Estendido pelo
  assistente ao Margules 2P, a confirmar:** o mesmo exemplo ajusta A₁₂ = 2,26 e
  A₂₁ = 2,25 no 2P, também fora de ±2, então os dois parâmetros do 2P foram a ±3
  (o pedido citava só o 1P). Wilson (Λ de 0,01 a 3) e α₁₂ do NRTL não mudaram. Os
  valores ajustados nos outros exemplos cabem em ±3 (etanol/água A ≈ 1,0–1,1 no 1P;
  clorofórmio/MEK A = −1,17).

- **(2026-10-07) Botão "Exemplos" separado de "Importar dados".** Pedido do
  autor: "crie o botão exemplo e coloque próximo ao importar e mova o conteúdo
  de exemplos pra ele". Os quatro exemplos NIST saíram do diálogo "Importar
  dados" (que ficou com *Arquivo CSV do dispositivo* e *Colar texto*) e ganharam
  o botão **"Exemplos"** (ícone de frasco), com diálogo próprio de título
  "Exemplos" e as opções sem o prefixo "Exemplo:" (o título já diz). O
  comportamento ao escolher um exemplo não mudou (preenche tabela, componentes
  e T; mensagem com fonte e nota). Código: `opcao_dialogo` e
  `mostrar_dialogo_opcoes` (comuns aos dois diálogos), `abrir_importar`,
  `abrir_exemplos` e `botao_exemplos`, criado uma vez e reaproveitado nos dois
  layouts (a regra de não mutar controle criado vale: o botão não é alterado).
  **Posição:** no celular, os três botões quebram linha sozinhos (Adicionar numa
  linha; Importar dados + Exemplos na de baixo). No desktop (card de ~420 px, onde
  os três não cabem numa linha) foi montado o mesmo arranjo de forma explícita:
  "Adicionar Novo Ponto" centralizado numa linha e "Importar dados" + "Exemplos"
  juntos na de baixo — **escolha do assistente, a confirmar** (a alternativa era
  deixar o "Exemplos" sozinho numa terceira linha). Verificado por captura de
  tela a 1400 px e a 360 px (os dois diálogos, e a importação do exemplo
  metanol/dimetilbuteno pelo botão novo, 22 pontos). Nenhum teste automatizado
  muda (a lógica dos exemplos, `EXEMPLOS_NIST`/`carregar_exemplo_nist`, é a mesma).

- **(2026-10-07) Botão "Comparar" movido para o card "Parâmetros do modelo".**
  Pedido do autor: "colocar o botão comparar junto com o card de parâmetros".
  Saiu do card "Dados experimentais" (no desktop, da Row com a lixeira abaixo
  do título; no celular, do cabeçalho) e entrou na Row de botões do card de
  parâmetros, depois de "Buscar do Banco", "Calcular por Regressão" e
  "Desfazer", acima do ΔP/Δy que ele produz. Continua visível para todos os
  modelos (UNIQUAC/UNIFAC inclusos — a visibilidade da regressão e do
  "Desfazer" depende dos sliders, a do Comparar não) e habilitado só com dado
  experimental na tabela. O botão segue criado uma vez e reaproveitado (regra
  de não mutar controle criado). **Escolha do assistente, a confirmar:** a
  posição do botão dentro da Row (por último); no desktop (card de ~420 px) ele
  quebra para uma linha própria, e no celular fica ao lado do "Desfazer".
  Verificado por captura de tela a 1400 px (exemplo metanol/dimetilbuteno +
  Comparar: curvas comparativas e `ΔP = 31.78% / Δy = 0.1530` — Margules 1P com
  A = 0,5, sem ajuste, só mecânica) e a 360 px; testes passam.

- **(2026-10-07) "Limpar Tabela" vira botão "Limpar dados", com ícone e estilo.**
  Pedido do autor: o ícone de limpar deve ter o nome junto e um estilo próprio,
  e o rótulo deve ser "Limpar dados", não "Limpar lista". O `IconButton` (só o
  ícone, escolhido em 2026-09-28 para caber ao lado do "Comparar" no cabeçalho)
  virou `ft.Button` com o ícone `DELETE_SWEEP` e o texto, no `estilo_botao()`
  dos botões secundários (fundo azul claro, apagado em cinza quando a tabela
  não tem ponto válido). O motivo de ser só ícone deixou de existir com a saída
  do "Comparar" do card. Posição inalterada: desktop, centralizado abaixo do
  título; celular, abaixo do título do card. Verificado por captura a 1400 px e
  360 px (estado apagado, tabela vazia).

- **(2026-10-07) "Comparar" ao lado do selo de origem.** Pedido do autor
  ("botão de comparar fica ao lado do selo"), refinando a posição da entrada
  anterior. No card "Parâmetros do modelo", o botão ocupa agora a mesma linha
  do selo ("Fornecido"/"Banco de dados"/…, com o ⓘ), e não mais a linha dos
  botões de banco/regressão/Desfazer. A linha do selo é uma Row nova a cada
  montagem, sempre visível (só o selo muda de `visible`); o selo passou a
  `tight=True` na criação, porque sem isso ocupava a largura toda e empurrava o
  "Comparar" para baixo. No celular as duas linhas de botões abaixo quebram como
  antes (Regressão numa, Desfazer na seguinte). Verificado por captura a 1400 px e
  360 px e com o clique real após importar o exemplo metanol/dimetilbuteno
  (ΔP/Δy aparecem).

- **(2026-10-07) Selo de origem logo depois do título "Parâmetros do modelo".**
  Pedido do autor ("mude o selo para após o texto Parâmetros do modelo"),
  substituindo a posição anterior (ao lado do "Comparar"). O selo (chip + ⓘ)
  vai para o cabeçalho do card, colado ao título: `cartao()` ganhou o parâmetro
  `extra_junto` (o extra fica logo depois do título, em vez de empurrado para a
  ponta direita, que continua sendo o padrão de `extra_titulo`). **Interpretação
  do assistente, a confirmar:** o pedido citava só o selo, então o "Comparar" não
  o acompanhou — ficou numa linha própria logo abaixo do slider, antes da nota do
  α₁₂ e dos botões Banco/Regressão/Desfazer; se a ideia era mantê-lo junto do
  selo, é só passar os dois ao cabeçalho. **Limite no celular:** a 360 px o
  título (~175 px) mais o selo ("Fornecido" ~100 px) não cabem na largura útil do
  card (~270 px) e o selo desce para a linha de baixo — a quebra (`wrap=True`) é a
  proteção contra o erro de overflow já visto; selos mais longos ("Banco, r/q via
  UNIFAC") quebram também em telas maiores. No desktop o selo fica ao lado do
  título. Verificado por captura a 1400 px e 360 px e pelo clique real em
  "Comparar" depois de importar o exemplo (ΔP/Δy aparecem).

- **(2026-10-07) Regressão e Desfazer acesos só quando aplicáveis, como o
  Comparar.** Pedido do autor: "quero que a regressão por Barker e o desfazer
  fique aceso apenas quando for aplicável, assim como o comparar". **Regressão:**
  o botão "Calcular por Regressão (Barker)" nasce apagado e acende só quando a
  regressão pode rodar — o modelo tem slider (não UNIQUAC/UNIFAC) **e** a tabela
  tem o mínimo de pontos válidos do modelo (parâmetros livres + 1, o mesmo piso
  de `regress_params_barker`, seção 2.8: 2 pontos no Margules 1P, 3 nos demais).
  Reavaliado junto com o Comparar e o "Limpar dados" por
  `atualizar_habilitacao_botoes` (em `gerar_grafico`, ao sair de um campo da
  tabela e, novo, ao excluir uma linha — antes a lixeira de linha não reavaliava
  nenhum botão, também um defeito do Comparar). Trocar de modelo reavalia pelo
  `gerar_grafico` que já seguia a troca. **Desfazer:** já era assim — nasce
  apagado, acende ao empilhar um estado (busca no banco ou regressão) e apaga ao
  esvaziar o histórico ou trocar de modelo; só confirmado, nada mudou. Digitar um
  valor ou mover o slider não empilha histórico (decisão de 2026-10-06), então
  esses dois gestos não acendem o Desfazer. Verificado por captura a 1400 px:
  estado inicial (Comparar, Regressão e Desfazer apagados); 1 ponto digitado
  (Comparar aceso, Regressão apagada); 2 pontos (Regressão acesa); exclusão de
  um ponto (volta a apagar); exemplo importado + regressão (Desfazer acende);
  testes passam.

- **(2026-10-07) Aviso ao tocar num botão apagado.** Resposta do autor à
  proposta do assistente ("Sim, mostre o aviso ao tocar no botão apagado"): o
  botão apagado explica por que está apagado. Botão desabilitado do Flet não
  dispara `on_click`, então "Comparar", "Calcular por Regressão", "Desfazer" e
  "Limpar dados" ficam cada um dentro de um `ft.GestureDetector` (`caixa_*`,
  criado uma vez e reaproveitado entre montagens de layout) cujo `on_tap` só age
  se o botão estiver `disabled` — aceso, o clique é do próprio botão (conferido:
  a regressão roda normalmente). Textos: regressão ("precisa de pelo menos N
  pontos válidos ... para <modelo> (há X)"), comparar ("a tabela precisa ter ao
  menos um ponto experimental válido"), desfazer ("o histórico guarda só as
  alterações feitas por Buscar do Banco e por Regressão") e limpar ("a tabela já
  está sem pontos válidos"). Os três primeiros aparecem no `aviso_parametro`,
  dentro do card "Parâmetros do modelo"; o do "Limpar dados", na mensagem de
  status do card "Dados experimentais". **Escolhas do assistente, a confirmar:**
  cor **laranja** (`#9A3B00`, a dos avisos do app) em vez do vermelho, que fica
  só para erro (o `aviso_parametro` volta ao vermelho quando o valor digitado é
  inválido); a dica **some** quando a tabela é reavaliada (digitar, importar,
  excluir, gerar gráfico) e ao trocar de modelo; e a visibilidade de regressão e
  Desfazer por modelo passou para os `caixa_*`. Efeito colateral: o aviso ocupa
  uma ou duas linhas no card e empurra os botões para baixo enquanto aparece.
  Verificado por captura a 1400 px (os quatro avisos, e regressão aceita
  rodando) e a 360 px (aviso da regressão); testes passam.

- **(2026-10-07) Botão "Ajuda": manual rápido por tópicos, só o sumário.** Pedido
  do autor: um botão "Ajuda" com o sumário de funcionamento do app, navegável
  por tópicos, para ajuda rápida/tira-dúvidas; "por enquanto apenas os tópicos,
  sem conteúdo". **Implementação:** botão na faixa de cabeçalho, ao lado do de
  modo de exibição, no mesmo estilo (fundo branco translúcido, criado novo a cada
  montagem). Abre um diálogo "Ajuda" com a lista de tópicos (rola, com altura de
  ~60% da janela); tocar num tópico abre outro diálogo com o título e, por ora,
  "Conteúdo em breve."; "Voltar aos tópicos" reabre a lista e "Fechar" sai (um
  diálogo novo por passo, como em "Colar texto"). Os tópicos moram em
  `AJUDA_TOPICOS` (módulo), cada um `{"titulo", "conteudo"}` com `conteudo=None`:
  escrever um tópico é trocar o `None` por texto. **Lista de tópicos —
  proposta do assistente, a confirmar pelo autor (16):** visão geral; escolher o
  sistema (componentes, temperatura, modelo Gᴱ); digitar dados na tabela; importar
  dados (CSV e texto colado); exemplos prontos (NIST); ler o diagrama P-x-y; ler
  o gráfico de ln γ; modelos de Gᴱ e quando usar cada um; parâmetros (slider e
  valor digitado); origem do parâmetro (selo); buscar no banco (IPDB); regressão
  (Barker); comparar calculado e experimental (ΔP e Δy); desfazer; limitações e
  cuidados (isotérmico, unidades, gás ideal); ver como celular/computador.
  **Layout no celular:** a faixa passou a ter "UFC", "Ajuda" e o botão de modo
  numa Row que quebra linha — a 360 px o botão de modo desce para a linha de
  baixo (sem a quebra ele estourava a faixa). No desktop, "Ajuda" e modo ficam
  lado a lado à direita. Verificado por captura a 1400 px (lista, tópico, voltar)
  e a 360 px (faixa, lista e tópico); testes passam.

- **(2026-10-07) Ajuda por card: "?" ao lado do título + sumário reorganizado.**
  Depois de o assistente levar opções de ajuda contextual (tooltips só nos
  ícones; ⓘ por card; sumário menor por card; "primeiros passos"; tour guiado),
  o autor respondeu "vamos seguir sua recomendação" (ⓘ por card + sumário menor +
  primeiros passos; tooltips só no desktop como detalhe opcional; tour adiado) e
  perguntou se não seria "mais simbólico". **Resposta/decisão de implementação
  (do assistente, a confirmar):** o acesso por card é só um símbolo, sem texto —
  um "?" (`HELP_OUTLINE`, `BLUE_700`, 20 px) colado ao título de cada um dos cinco
  cards (Dados experimentais, Sistema, Parâmetros do modelo, Diagrama P-x-y,
  Coeficientes de atividade). Distinto do ⓘ azul-claro que já existe: **"?" =
  ajuda do card; ⓘ = explicação de um valor** (selo de origem, ΔP, Δy). O botão
  "Ajuda" do cabeçalho segue com ícone e a palavra, por ser a porta do manual
  completo e precisar ser descoberto. **Implementação:** `cartao(..., ajuda=id)`
  põe o ícone logo depois do título (controle novo a cada montagem); o "?" abre
  direto o tópico daquele card (`mostrar_topico_ajuda`), com "Todos os tópicos"
  (volta ao sumário) e "Fechar". `AJUDA_TOPICOS` ganhou o campo `id` e foi
  reduzido de 16 para **9 tópicos, um por card**: primeiros passos (3 etapas);
  dados experimentais (digitar, importar, exemplos); sistema; parâmetros do modelo
  (slider, valor digitado, selo, banco, regressão); comparar (ΔP e Δy); diagrama
  P-x-y; ln γ; modelos de Gᴱ e quando usar cada um; limitações e cuidados. Saíram
  como tópicos próprios "desfazer" (vai em Parâmetros) e "ver como celular/
  computador" (o botão já diz o que faz). **Conteúdo ainda vazio** ("Conteúdo em
  breve."), a pedido do autor. **Escolha do assistente, a confirmar:** o "?"
  abre o tópico direto, e não o sumário com o tópico destacado (a pergunta ficou
  sem resposta do autor); o tooltip "Ajuda sobre este card" aparece só no
  desktop. A altura da lista de tópicos agora acompanha o número de itens (rola se
  não couber). Verificado por captura a 1400 px (os cinco "?", clique no card de
  Parâmetros, "Todos os tópicos") e a 360 px; testes passam.

- **(2026-10-07) Conteúdo do tópico "Primeiros passos" (rascunho).** Pedido do
  autor: "vamos começar pelo tópico Primeiros passos". Primeiro tópico com
  texto em `AJUDA_TOPICOS`; redação **do assistente, a revisar pelo autor**
  (comentário no código diz isso). Estrutura: três etapas — (1) **carregar
  dados** (botão "Exemplos": preenche tabela, componentes e temperatura e já
  desenha os gráficos), (2) **ajustar o modelo** (modelo no card "Sistema";
  slider ou valor digitado no card "Parâmetros do modelo"; o selo diz a origem
  do valor) e (3) **comparar com o experimental** ("Comparar": marcadores vazados
  e ΔP em %, Δy; "Calcular por Regressão (Barker)" para ajustar o parâmetro) —,
  mais um parágrafo para quem usa **dados próprios** (digitar P em kPa, x₁, y₁ ou
  "Importar dados"; componentes por nome **em inglês** ou CAS; temperatura em
  °C; "Gerar Gráfico" se digitou à mão). **Fato conferido antes de escrever:** o
  `thermo` aceita "ethanol"/"water"/CAS, mas nomes em português como "água" e
  "acetona" dão erro ("etanol" e "metanol" funcionam por coincidência) — por isso o
  texto manda usar o nome em inglês. **Mecânica nova (vale para os próximos
  tópicos):** o corpo do tópico é uma string em parágrafos separados por linha em
  branco; uma linha que começa com `# ` vira subtítulo (negrito azul); o diálogo do
  tópico é rolável (`scrollable`), porque no celular o texto não cabe. Verificado
  por captura a 1400 px e a 360 px; testes passam. Os outros oito tópicos seguem
  "Conteúdo em breve.".

- **(2026-10-07) "Primeiros passos" revisado; conteúdo do tópico "Dados
  experimentais" (rascunho).** O autor revisou o texto de "Primeiros passos"
  ("revisado, siga para o próximo") — passa a valer como aprovado — e o
  assistente seguiu para o tópico sugerido, **"Dados experimentais: digitar,
  importar e exemplos"** (o próximo da ordem do fluxo; a ordem era proposta do
  assistente). Redação **do assistente, a revisar pelo autor**. Seções (subtítulos
  `# `): o que a tabela guarda (P em kPa; x₁ e y₁ do componente 1, isotérmico);
  **digitar na tabela**; **importar dados** (arquivo CSV e colar texto); **exemplos**;
  **limpar dados**; **atenção às unidades**. **Fatos conferidos no código antes de
  escrever, que o texto reflete:** (a) as células da tabela **só aceitam dígitos,
  ponto e sinal de menos** (`filtrar_numero`) — **vírgula decimal não vale na
  tabela**, só no "Colar texto"; (b) o **CSV exige cabeçalho com as colunas `P`, `x`
  e `y`** (sem diferenciar maiúsculas, em qualquer ordem; `x1` não é aceito); (c)
  no texto colado, espaço/tabulação/`;`/vírgula separam os campos e, com os três
  primeiros, a vírgula vale como decimal; cabeçalho opcional; (d) importar
  **substitui** a tabela e redesenha; linhas inválidas são ignoradas e contadas;
  (e) "Limpar dados" volta às 10 linhas em branco (`NUM_LINHAS_INICIAIS`); (f) os
  exemplos preenchem também componentes e temperatura. O aviso sobre unidades
  repete o que o app **não** valida (P em outra unidade dá ΔP sem sentido, sem
  aviso — item 1 da lista de estética). Verificado por captura a 1400 px e a
  360 px (o diálogo rola); testes passam. Dois tópicos com texto; sete seguem
  "Conteúdo em breve.".

- **(2026-10-07) "?" por exemplo no diálogo "Exemplos", com as limitações.**
  Pedido do autor: "quero uma interrogação para os exemplos informando as
  limitações que encontramos neles". Cada exemplo ganhou, ao lado, um "?"
  (mesmo ícone do "?" de ajuda dos cards) que fecha a lista e abre o diálogo
  "Limitações: <exemplo>" (rolável, com "Voltar aos exemplos" e "Fechar").
  Código: chave `limitacoes` em cada item de `EXEMPLOS_NIST` (texto no formato
  dos tópicos de ajuda, com subtítulos `# `, lido por `corpo_ajuda`),
  `opcao_dialogo(..., largura=None)` e `abrir_limitacoes_exemplo`. **Conteúdo —
  redação do assistente, a revisar pelo autor; todos os números foram
  recalculados antes de escrever** (checagem com as funções do app): etanol/água
  90 e 108 °C — faixa de x₁ incompleta (0,16–0,997 com vão de 0,79 a 0,997, e
  0,017–0,997 com o mesmo vão), puros não medidos, teste da área inconclusivo,
  T e P elevadas com a hipótese de vapor ideal, e o que funciona (modelos do
  banco e UNIFAC sem ajuste, ΔP 0,5–2,3 %, Δy 0,017–0,030); metanol/
  dimetilbuteno 70 °C — só a regressão de Barker se aplica (sem NRTL/Wilson no
  banco; UNIQUAC e UNIFAC falham porque o 2,3-dimetil-2-buteno não está na
  tabela de grupos), azeótropo de pressão máxima reproduzido a menos de 0,015
  em x₁, nome do componente 2 cortado no campo (cosmético); clorofórmio/MEK
  30 °C — só a regressão se aplica (sem parâmetros no banco; clorofórmio fora da
  tabela de grupos), azeótropo do modelo em x₁ ≈ 0,14–0,15 contra 0,19, MEK puro
  3,2 % acima da Psat do `thermo`, x₁ = 0,252 repetido (a mensagem pós-"Comparar"
  conta 21 composições distintas). **Escolhas do assistente, a confirmar:** um "?"
  por exemplo (em vez de um aviso único no diálogo); incluir o que funciona, além
  do que limita; a seção "Cosmético" do metanol/dimetilbuteno. Verificado por
  captura a 1400 px (lista, limitações do etanol/água 90 °C e do clorofórmio/MEK,
  "Voltar aos exemplos") e a 360 px (lista e limitações do metanol/dimetilbuteno);
  os testes passam.

- **(2026-10-07) Conteúdo do tópico "Sistema" (rascunho).** Pedido do autor:
  "mantenha suas escolhas e siga para o próximo tópico" — as escolhas pendentes
  do assistente (ordem dos tópicos, um "?" por exemplo, "O que funciona" nas
  limitações) ficam como estão, e o próximo da ordem do fluxo é **"Sistema:
  componentes, temperatura e modelo Gᴱ"**. Redação **do assistente, a revisar
  pelo autor**. Seções (subtítulos `# `): **componentes** (nome em inglês ou
  CAS; maiúsculas não importam; "etanol", "metanol" e "agua" funcionam por
  coincidência, "acetona", "benzeno" e "água" com acento não; o Componente 1 é
  o dono dos índices 1; dois componentes iguais não dão erro mas não têm
  sentido; nome inválido gera "Curva do modelo não calculada" no card "Dados
  experimentais"); **temperatura** (°C, ponto decimal — "70,5" dá erro —,
  única e igual à dos dados; abaixo da temperatura crítica); **modelo Gᴱ** (os
  cinco com parâmetros ajustáveis × UNIQUAC/UNIFAC automáticos, que dependem de
  o par estar nos dados do app; trocar de modelo reinicia parâmetros e o
  histórico do "Desfazer"); e **ao trocar componentes ou temperatura**.
  **Fatos conferidos rodando o motor/lendo o código antes de escrever:** etanol/
  água a 300 °C **não dá erro** e devolve P de 8,6 a 32,7 MPa — acima da pressão
  crítica do etanol (6268 kPa; Tc 241,6 °C) —, ou seja, o app **não avisa**
  quando a temperatura passa da crítica de um componente; etanol/etanol também
  calcula sem erro; a recalculação é ao sair do campo/Enter (componentes e
  temperatura) e imediata na escolha do modelo; `parametros_atuais` só muda por
  slider, valor digitado, banco ou regressão, nunca por troca de componente ou
  temperatura.
  **Achado a decidir pelo autor, não corrigido:** (a) trocar componentes ou
  temperatura **mantém os valores dos parâmetros e o selo de origem** — se vieram
  de "Buscar do Banco" ou da regressão para o sistema anterior, o selo continua
  dizendo "Banco de dados"/"Calculado", o que pode enganar; o texto da ajuda
  descreve o comportamento atual e manda refazer a busca/regressão; (b) a falta
  de aviso de temperatura acima da crítica. Opções, se o autor quiser tratar:
  voltar o selo a "Fornecido" (ou avisar) ao mudar o sistema, e uma mensagem
  quando T passar da menor Tc dos dois componentes. Verificado por captura a
  1400 px e a 360 px (o diálogo rola); testes passam. Três tópicos com texto;
  seis seguem "Conteúdo em breve.".

- **(2026-10-07) Correções dos dois achados do tópico "Sistema".** Pedido do
  autor: "faça as correções". **(1) Selo de origem ao mudar o sistema:** o app
  guarda o sistema (Componente 1, Componente 2 e T) em que o selo foi definido
  (`sistema_do_selo`); a cada `gerar_grafico`, se o selo é "Banco de dados",
  "Calculado" ou "Calculado (poucos pontos)" e o sistema mudou, o selo volta a
  **"Fornecido"** e o ⓘ diz de que origem e de que sistema vieram os valores
  ("… para o sistema anterior (ethanol/water a 70 °C) e não foram recalculados
  para o sistema atual. Refaça a busca no banco ou a regressão."). Os valores e
  os sliders **não** mudam (só o selo, que passa a dizer a verdade). Vale só para
  os modelos com slider (UNIQUAC/UNIFAC recalculam a cada gráfico). O histórico
  do "Desfazer" guarda o sistema de cada estado, então desfazer para um estado
  de outro sistema também cai em "Fornecido". **Escolha do assistente, a
  confirmar:** "Fornecido" em vez de um selo novo ("Desatualizado") — reaproveita
  os selos que existem. **(2) Aviso de temperatura crítica:** `calculate_vle_
  isothermal` passou a devolver `Tc_C` (temperatura crítica, em °C, dos dois
  componentes — chave nova, sem alterar as demais) e, na UI,
  `aviso_temperatura_critica` mostra um texto laranja na mensagem do card "Dados
  experimentais" quando T chega à crítica de algum componente, dizendo qual
  (ex.: etanol/água a 300 °C: "ethanol: 241,6 °C"). **Só avisa; o cálculo
  continua e o gráfico aparece** (escolha do assistente, a confirmar: bloquear o
  gráfico seria decisão mais forte). O limiar é a própria crítica, sem folga
  (perto dela o vapor ideal já é ruim, mas isso é gradual e o aviso do tópico
  "Limitações" fica para o texto). Novo `testes/teste_temperatura_critica.py`
  (Tc do etanol e da água; sem aviso a 70 °C; só o etanol a 300 °C; os dois a
  400 °C; Tc ausente não dá erro). Verificado por captura a 1400 px: aviso a
  300 °C; NRTL + "Buscar do Banco" ("Banco de dados") e, ao mudar T para 90 °C,
  selo "Fornecido" com o ⓘ correto; "Desfazer" continua funcionando. O texto do
  tópico "Sistema" foi atualizado para descrever o novo comportamento; os testes
  passam.

- **(2026-10-07) Escolhas confirmadas; conteúdo do tópico "Parâmetros do modelo"
  (rascunho).** O autor respondeu "Confirmo as escolhas, siga para o próximo
  tópico": passam a valer como decisões do projeto as escolhas do assistente que
  estavam "a confirmar" nas entradas recentes — selo voltando a "Fornecido" ao
  mudar o sistema (em vez de um selo novo), aviso de temperatura crítica **sem
  bloquear** o gráfico, um "?" por exemplo com "O que funciona" e a seção
  "Cosmético", ordem e lista dos 9 tópicos de ajuda, cor laranja dos avisos. O
  próximo tópico da ordem é **"Parâmetros do modelo"**, o mais longo. Redação **do
  assistente, a revisar pelo autor**. Seções (subtítulos `# `): **o que cada
  parâmetro é** (A: ln γ₁ = A·x₂², ln γ₂ = A·x₁²; em Margules 2-P e Van Laar,
  A₁₂ e A₂₁ são ln γ à diluição infinita; Λ = 1 e τ = 0 dão solução ideal);
  **mudar o valor à mão** (slider redesenha ao soltar; campo confirma com Enter ou
  ao sair; faixas dos sliders; valor fora da faixa vale no cálculo); **o selo de
  origem** (os seis selos); **Buscar do Banco** (só NRTL/Wilson; mensagem
  "Busca no banco não realizada" para pares sem tabela, como os dois exemplos
  NIST sem banco); **Calcular por Regressão (Barker)** (mínimos de pontos, T do
  card "Sistema", α₁₂ do NRTL fixo, resíduo RMS no ⓘ); **Desfazer** (até 5
  estados, só banco e regressão); **UNIQUAC e UNIFAC**. **Fatos conferidos antes
  de escrever:** fórmulas de `gemini.py`; limites da regressão (±5 em Margules, Van
  Laar e NRTL; 1e-4 a 10 no Wilson); mensagens reais de erro (regressão com 1
  ponto, Van Laar no banco, par sem NRTL); α₁₂ não muda o selo ao ser movido; e um
  teste com 10 pontos sem relação com o par (etanol/água a 70 °C), em que a
  regressão "converge" (`sucesso=True`) com resíduo RMS ≈ 0,43–0,45 e parâmetro
  **colado no limite** (Van Laar A₂₁ = −5; Wilson Λ₁₂ = 0,0001).
  **Achado a decidir pelo autor, não corrigido:** a UI **não lê** `sucesso` nem
  olha o resíduo ou o limite: depois de uma regressão sem sentido o selo diz
  "Calculado" normalmente, e só o ⓘ traz o resíduo, sem dizer se é alto. Referência
  medida: resíduo 0,007–0,023 nos exemplos NIST × ≈ 0,4 em dados sem relação. O
  texto da ajuda manda conferir com "Comparar" e desconfiar de parâmetro no
  limite. Opções, se o autor quiser tratar: (a) aviso laranja quando o parâmetro
  ficar a menos de 1 % do limite da busca ou `sucesso` for falso; (b) aviso quando
  o resíduo passar de um limiar (a calibrar com mais dados reais); (c) deixar como
  está e só documentar. Verificado por captura a 1400 px (o diálogo rola, as
  seções aparecem) e a 360 px; testes passam. Quatro tópicos com texto; cinco
  seguem "Conteúdo em breve.".

- **(2026-10-07) Tópico "Sobre: autor, fontes e créditos" na Ajuda.** Pedido do
  autor: "quero que tenha o tópico 'sobre', onde informa o autor dessa aplicação
  (eu), as fontes e a linguagem Python e as lib thermo e flet com seus devidos
  créditos aos autores criadores". Décimo tópico de `AJUDA_TOPICOS` (`id`
  "sobre"), **o último da lista e sem "?" de card** — só no sumário do botão
  "Ajuda". Redação **do assistente, a revisar pelo autor**. Seções: **autor**
  (Leonardo de Sousa Lins, graduando em Engenharia Química na UFC; TCC);
  **linguagem e bibliotecas** (Python — Python Software Foundation; Flet 1.0 e
  flet-charts 1.0 — Appveyor Systems Inc. e colaboradores, Apache 2.0; thermo
  0.6.1 e chemicals 1.5.2 — Caleb Bell, MIT; NumPy e SciPy; e a nota de que as
  equações dos modelos são do projeto, conferidas contra a thermo); **fontes dos
  parâmetros** (banco ChemSep — Harry Kooijman e Ross Taylor, Artistic License 2.0;
  UNIFAC original — Fredenslund, Jones e Prausnitz, conforme as tabelas da thermo;
  regressão — redução de dados de ELV em Smith, Van Ness e Abbott); **fontes dos
  dados experimentais** (NIST/TRC ThermoML, doi:10.18434/mds2-2422, Riccardi et
  al. 2022, e os três artigos de origem com DOI; planilha XSEOS, canal Youtermo,
  para o Margules 2-P); **licenças** (cada biblioteca e base mantém a sua). **Fatos
  conferidos antes de escrever:** versões e licenças nos metadados dos pacotes
  instalados e no `uv.lock` (thermo 0.6.1, chemicals 1.5.2, flet e flet-charts
  1.0.0); autores e licenças nos próprios pacotes (Caleb Bell/MIT; "Appveyor
  Systems Inc."/Apache-2.0; o XML do ChemSep traz "Copyright (c) Harry Kooijman
  and Ross Taylor" e a Artistic License 2.0); `thermo.unifac.UFIP` = parâmetros do
  UNIFAC original; os três artigos e DOIs vêm dos cabeçalhos dos CSVs em
  `referencias/`. **Escolhas do assistente, a confirmar:** (1) **não** incluir o
  orientador (Dr. Filipe Xavier Feitosa) nem o uso do Claude Code como
  ferramenta — o pedido não os citava, e ambos são decisão do autor (o uso de IA
  será explicitado no trabalho final, ver o topo deste arquivo); (2) **não** declarar
  a licença do próprio projeto, que não está definida no repositório; (3) citar as
  versões das bibliotecas no texto, o que obriga a atualizá-lo quando o `uv.lock`
  mudar; (4) a atribuição do método de Barker a Smith, Van Ness e Abbott segue o
  mapeamento (seção 2.8), sem título nem edição do livro. Verificado por captura a
  1400 px (sumário com o tópico novo, texto inteiro rolando) e a 360 px (sumário
  rola); testes passam. Cinco tópicos de conteúdo em branco continuam
  "Conteúdo em breve."; o "Sobre" já tem texto (cinco com texto, ao todo).

- **(2026-10-07) Aviso laranja de regressão suspeita — opção (a).** O autor
  escolheu, entre as três saídas levadas ("vamos de (a)"), o **aviso quando o
  parâmetro ficar a menos de 1 % do limite, ou quando o otimizador não
  convergir** — resposta ao achado do tópico "Parâmetros do modelo" (a UI não
  lia `sucesso` nem olhava os limites). **Implementação:** `regress_params_
  barker` devolve uma chave nova, `no_limite` (lista de `{chave, valor, limite}`
  dos parâmetros com |valor − limite| ≤ 1 % de |limite|; constante
  `TOLERANCIA_LIMITE_REGRESSAO = 0.01`); as demais chaves não mudaram. Na UI,
  `aviso_ajuste_regressao(resultado, rotulos)` monta o texto ("Atenção: a regressão
  terminou com parâmetro no limite da busca — A₂₁ = -5.000 (limite da busca: -5).
  O modelo provavelmente não descreve estes dados, ou há erro de digitação na
  tabela. Confira com "Comparar" antes de usar este ajuste."; e/ou "o otimizador
  não convergiu"), que aparece em laranja no card "Parâmetros do modelo"
  (`mostrar_dica`, depois do `gerar_grafico` — que reavalia os botões e apagaria a
  dica) e também entra no texto do ⓘ do selo. O selo continua "Calculado": o
  aviso não o troca. Some ao mexer num parâmetro, trocar de modelo ou reavaliar a
  tabela (mesmas regras das outras dicas). **Escolha do assistente, a confirmar:**
  a tolerância é **relativa ao próprio limite** (1 % de |limite|: 0,05 em ±5,
  0,1 no limite 10, 1e-6 no 1e-4), e não 1 % da faixa — com 1 % da faixa o Wilson
  (1e-4 a 10) marcaria Λ legítimos de até ≈ 0,1 (o do etanol/água é 0,176).
  **Medido:** dados sem relação com o par (10 pontos, semente 1): Van Laar A₂₁ =
  −5 e Wilson Λ₁₂ = 1e-4 marcados; nos 4 exemplos NIST × 5 modelos com slider
  (e nas 4 isotermas do metanol/dimetilbuteno e 5 do etanol/água) **nenhum falso
  positivo**, todos com `sucesso`. **O que o aviso não cobre (dito na ajuda):**
  resíduo alto com parâmetros dentro dos limites — o Margules 1-P nos mesmos dados
  sem relação deu A = −0,13 e resíduo ≈ 0,45 **sem aviso**; seria a opção (b) (limiar
  de resíduo, a calibrar), não escolhida. Novo `testes/teste_aviso_regressao.py`.
  Verificado por captura a 1400 px: dados sem relação (CSV) com Van Laar → aviso
  laranja e selo "Calculado"; exemplo etanol/água 108 °C com Van Laar → sem aviso.
  Texto do tópico "Parâmetros do modelo" atualizado; testes passam.

- **(2026-10-07) Conteúdo do tópico "Comparar calculado e experimental (ΔP e
  Δy)" (rascunho).** Pedido do autor: "confirmo suas escolhas. siga para o
  próximo" — mesmas escolhas já confirmadas valem; o próximo tópico da ordem do
  fluxo é **"Comparar"**. Redação **do assistente, a revisar pelo autor**. Seções
  (subtítulos `# `): **como usar** (botão no card "Parâmetros do modelo"; acende
  com ≥ 1 ponto válido; vale para todos os modelos; avalia o modelo nos x₁ da
  tabela, não na malha de 101); **como ler os gráficos** (marcadores vazados, a
  coluna "Comparativo", distância cheio × vazado = erro; no ln γ só mostram onde o
  modelo foi calculado); **o que são ΔP e Δy** (relativo em % × absoluto sem
  unidade; ambos RMS; por que separados e por que um é relativo e o outro
  absoluto — os argumentos da decisão de 2026-09-27); **valores de referência**
  (nos exemplos NIST: banco sem ajuste no etanol/água ΔP 0,5–2,3 % e Δy
  0,017–0,030; Barker ΔP 1–2 % e Δy 0,008–0,025 — ordem de grandeza, não critério
  de aprovação); **cuidados**. **Fatos conferidos rodando o app:** o exemplo
  etanol/água a 108 °C com Margules 1-P (A = 0,5) dá ΔP = 14,19 % e Δy = 0,0658
  (só mecânica, sem ajuste); depois de "Comparar", digitar A = 1,2 **apaga**
  marcadores vazados, coluna "Comparativo", ΔP e Δy (o `gerar_grafico` os limpa).
  **Achado, não corrigido, a decidir pelo autor:** editar um valor na **tabela**
  (testado: P da primeira linha de 156,1 para 400, saindo do campo) **não** refaz o
  gráfico nem a comparação — o ΔP = 14,19 % e os marcadores continuam os do último
  "Comparar", calculados com a tabela de antes, até o usuário clicar em "Gerar
  Gráfico" e em "Comparar" de novo. Ou seja, o erro exibido pode estar defasado em
  relação à tabela na tela. O texto da ajuda descreve o comportamento atual e manda
  refazer os dois cliques. Opções, se o autor quiser tratar: (a) ao sair de um campo
  da tabela, esconder a comparação (mesmo efeito de mexer num parâmetro) — a mais
  simples e coerente; (b) refazer o gráfico e a comparação automaticamente — muda o
  gatilho "Gerar Gráfico" manual já decidido; (c) deixar e só documentar. O texto
  também diz que todos os pontos pesam igual, inclusive os repetidos (a mensagem
  "calculada em N ponto(s)" conta x₁ distintos). Verificado por captura a 1400 px
  e a 360 px (o diálogo rola, as seções aparecem); testes passam. Seis tópicos com
  texto; quatro seguem "Conteúdo em breve.": "Diagrama P-x-y", "ln γ", "Modelos de
  Gᴱ" e "Limitações".

- **(2026-10-07) Comparação escondida ao editar a tabela — opção (a); conteúdo
  do tópico "Diagrama P-x-y" (rascunho).** O autor respondeu "Confirmo suas
  escolhas e (A), siga para o próximo tópico": as escolhas pendentes do assistente
  passam a valer e, entre as saídas do achado do tópico "Comparar", fica a **(a)**
  (esconder a comparação ao editar a tabela). **Implementação:** `comparativo_ativo`
  (estado) e `invalidar_comparacao()`: remove as 2 séries que "Comparar" acrescentou
  a cada gráfico, esconde as colunas "Comparativo" das legendas e a linha ΔP/Δy, e
  avisa em laranja no card "Dados experimentais" ("Tabela editada: a comparação foi
  escondida. Clique em "Comparar" de novo…"). Dispara **ao editar um valor** (no
  `on_change` do campo, não só ao sair dele — pedido literal era "ao sair de um
  campo"; escolhi o gatilho de edição para que apenas entrar e sair do campo sem
  mudar nada **não** apague a comparação; **a confirmar**) e **ao excluir uma
  linha**; só age se há comparação ativa (barato a cada tecla). **Efeito colateral
  corrigido de passagem:** clicar "Comparar" duas vezes empilhava séries repetidas no
  gráfico; agora a segunda vez troca a comparação anterior em vez de somar. Os
  marcadores cheios da tabela **continuam** só atualizando em "Gerar Gráfico"
  (gatilho manual decidido em 2026-09-21; dito no texto da ajuda). Verificado por
  captura a 1400 px: exemplo etanol/água 108 °C + "Comparar" (duas vezes, sem
  duplicar), editar P da primeira linha para 400 → marcadores vazados, coluna
  "Comparativo", ΔP e Δy somem; "Comparar" de novo → ΔP = 18,95 % (antes 14,19 %),
  coerente com a tabela editada. Texto do tópico "Comparar" atualizado. **Conteúdo do
  tópico "Diagrama P-x-y"** — redação **do assistente, a revisar pelo autor**.
  Seções: **o que está desenhado** (curva azul = pressão de bolha, P × x₁; laranja =
  orvalho, P × y₁; marcadores cheios da tabela, vazados do "Comparar"); **como ler**
  (regiões líquido, vapor e bifásica; linha horizontal liga x₁ e y₁ em equilíbrio;
  nos extremos as curvas se encontram nas pressões de vapor dos puros); **azeótropo**
  (tangente horizontal; máxima × mínima; os dois exemplos NIST, x₁ ≈ 0,58 e ≈ 0,19);
  **cálculo** (Raoult modificada, vapor ideal, uma só T); **detalhes da tela**
  (quando o gráfico se refaz, balão, lupa só no desktop e "como no clique"). **Fatos
  conferidos antes de escrever:** código de `gerar_grafico`, `ponto_grafico` e da lupa;
  azeótropos dos exemplos (dados NIST já registrados); o resto é termodinâmica padrão.
  **Retirado do texto por não verificado:** que o balão aparece "tocando" no celular
  (só o cursor foi testado). Verificado por captura a 1400 px (o diálogo rola, as
  seções aparecem); testes passam. Sete tópicos com texto; três seguem "Conteúdo em
  breve.": "ln γ", "Modelos de Gᴱ" e "Limitações".

- **(2026-10-08) Conteúdo do tópico "Coeficientes de atividade (ln γ)"
  (rascunho).** Pedido do autor: "confirmo suas escolhas, siga para o próximo
  tópico" — o próximo da ordem é o do gráfico de ln γ. Redação **do assistente, a
  revisar pelo autor**. Seções (subtítulos `# `): **o que ln γ diz** (γ = 1/ln γ = 0
  é ideal; positivo = desvio positivo, negativo = desvio negativo; curva verde = γ₁,
  roxa = γ₂); **como ler as curvas** (zero no componente puro, diluição infinita na
  ponta oposta, Gibbs-Duhem, simetria do Margules 1-P, sinal de A); **relação com o
  P-x-y e o azeótropo** (ln γ₁ − ln γ₂ = ln(P₂ˢᵃᵗ/P₁ˢᵃᵗ) em x₁ = y₁); **detalhes da
  tela** (colunas "Modelo" e "Comparativo", tooltip, eixo, lupa só no desktop).
  **Fatos conferidos rodando o motor (etanol/água, 70 °C):** ln γ₁∞ = 1,73 (NRTL),
  1,94 (Wilson), 1,69 (UNIQUAC) e 1,95 (UNIFAC); ln γ₂∞ = 0,98, 1,05, 1,01 e 1,03 —
  daí "1,7 a 1,95" e "1,0 a 1,05" no texto —; ln γ = 0 nos componentes puros; a
  equação de Gibbs-Duhem por derivada numérica fecha com resíduo ≤ 0,002 nos quatro
  modelos; o Margules 1-P (A = 1,2) dá curvas espelhadas e ln γ máximo = A; com A < 0
  não há ln γ positivo; o azeótropo do NRTL do banco cai em x₁ ≈ y₁ ≈ 0,88 com
  ln γ₁ − ln γ₂ = −0,840 contra ln(P₂ˢᵃᵗ/P₁ˢᵃᵗ) = −0,836 (a pequena diferença é da malha
  de 101 pontos, que não cai exatamente no azeótropo; no texto, "−0,84" dos dois
  lados). **Escolhas do assistente, a confirmar:** citar números de um exemplo
  (etanol/água, 70 °C) no texto, o que o prende a esse par; a afirmação "uma curva em
  que as duas sobem juntas indica defeito" (consequência de Gibbs-Duhem, vale para
  os modelos do app); dizer que não há ln γ experimental no app. Verificado por
  captura a 1400 px (abre pelo "?" do card, rola) e a 360 px (abre pelo sumário da
  Ajuda); os testes passam. Oito tópicos com texto; dois seguem "Conteúdo em breve.":
  "Modelos de Gᴱ" e "Limitações".
  **Revisado em 2026-10-08, depois das três perguntas do autor** (ver entrada
  seguinte): saíram os números do exemplo etanol/água e do azeótropo; a frase de
  Gibbs-Duhem passou a dizer a condição em que vale; o texto agora diz que os
  círculos vazados caem sobre a curva e não medem erro neste gráfico.

- **(2026-10-08) Perguntas do autor sobre o tópico ln γ; conferência do
  Margules 2-P com fonte robusta (A + B + C1 + D).** O autor questionou três
  escolhas do assistente no tópico "ln γ" e, na mesma mensagem, liberou "A + B +
  C1, e depois o D" para o Margules 2-P. **(1) "É uma boa, num texto geral, se
  prender a um par?"** Não: o texto de ajuda é geral e os números dependiam do
  par, da T, do modelo e do banco; saíram. **(2) "Duas curvas subindo juntas
  indicam defeito — qual fonte?"** A afirmação é consequência da equação de
  Gibbs-Duhem (x₁·d ln γ₁ + x₂·d ln γ₂ = 0 a T e P constantes: inclinações de
  sinais opostos), válida para modelos derivados de uma Gᴱ(T, x) e sem o termo de
  pressão; a redação "defeito, não física" era forte demais e foi trocada pela
  condição de validade. Fonte citada: Smith, Van Ness e Abbott (capítulo de ELV),
  **do conhecimento do assistente, sem conferir edição e seção** — o autor deve
  conferir antes de usar no TCC. Verificado numericamente: resíduo ≤ 0,002 nos
  quatro modelos com banco (derivada por diferença finita) e ≤ 1e-10 no Margules
  2-P (passo complexo). **(3) "Se não há ln γ experimental no app, os pontos
  vazados são desnecessários?"** No gráfico de ln γ, em termos de informação,
  **sim**: o comparativo é o mesmo modelo avaliado nos x₁ da tabela e cai sobre a
  curva, e não há marcador cheio para medir distância (no P-x-y há, e a distância
  é o erro). Só marcam em que x₁ está a tabela e mantêm o mesmo código visual dos
  dois gráficos. **Decisão do autor pendente:** manter, retirar do ln γ, ou
  passar a desenhar o ln γ experimental da tabela (método indireto) como
  marcadores cheios — o que daria ao gráfico uma comparação de verdade, mas é
  funcionalidade nova e reabre o argumento de 2026-09-13 (o método indireto
  amplifica ruído perto de x₁ → 0 e 1; para exibição, restringir a faixa).
  O texto de ajuda foi ajustado só para dizer o que os vazados são hoje.
  *Margules 2-P.* Diagnóstico: o teste existente comparava a planilha XSEOS com
  uma cópia da fórmula dentro do próprio teste e **nunca chamava o
  `model_margules_2p`**; a planilha tem 3 casas e procedência sem rastreio; e a
  `thermo` **não tem Margules nem Van Laar** (busca em `thermo` e `chemicals`), então
  o "`thermo` + planilha" do mapeamento (tabela de validação) estava errado.
  **A (feito):** `testes/teste_margules_2p_primeiros_principios.py` —
  Gᴱ/RT = x₁x₂(A₂₁x₁ + A₁₂x₂), ln γᵢ como grandeza parcial molar pela definição
  (derivada por passo complexo, independente da fórmula fechada), identidade de
  Euler, Gibbs-Duhem, limites (ln γ₁(0) = A₁₂, ln γ₂(1) = A₂₁, puros), redução ao
  Margules 1-P com A₁₂ = A₂₁ e auto-teste (reprova o modelo com A₁₂ e A₂₁ trocados);
  6 pares de parâmetros, incluindo negativos e de sinais opostos, 101 pontos de x₁
  com extremos; erro ≤ 1e-12. **B (feito):** `teste_margules_2p_MEK_tolueno.py`
  agora converte A/B → A₁₂ = (A−B)/RT e A₂₁ = (A+B)/RT e compara a planilha com o
  `model_margules_2p` real (diferença máxima 0,0005 = arredondamento da planilha),
  confere a conversão contra a cópia da fórmula (1e-16) e sai com código 1 se
  falhar (antes só imprimia). **C1 (feito):** `teste_margules_2p_nist_ln_gamma.py`
  — nas 10 isotermas NIST (etanol/água ×5, metanol/dimetilbuteno ×4,
  clorofórmio/MEK ×1), ln γ experimental pelo método indireto nos pontos com
  0,10 ≤ x₁ ≤ 0,90, Psat da `thermo`; confere (1) sinal de A₁₂ e A₂₁ ajustados =
  sinal do desvio medido, (2) RMS de ln γ do Margules 2-P ajustado por Barker
  (**0,027 a 0,065**, tolerância 0,08; Van Laar e Wilson impressos para contexto) e
  (3) a linearização clássica Gᴱ/(RT·x₁x₂) = A₁₂·x₂ + A₂₁·x₁ (estimador independente
  do Barker): diferença nos parâmetros de 0,05 a 0,42 (tolerância 0,50, folgada de
  propósito: a linearização usa só o interior e extrapola às pontas). **Achado:**
  no metanol/dimetilbuteno o Wilson descreve o ln γ melhor (RMS 0,024–0,047) que o
  Margules 2-P e o Van Laar (0,053–0,065), que coincidem porque A₁₂ ≈ A₂₁ — limite
  do modelo de 2 parâmetros nesse par, não bug. **O que C1 prova e o que não
  prova:** adequação do modelo a dado real, não a fórmula (essa é a de A).
  **D (feito):** mapeamento (linha de validação e lista de testes), tópico "Sobre"
  (a planilha passa a "conferência secundária"; a frase das equações diz que
  Wilson, NRTL, UNIQUAC e UNIFAC foram conferidas contra a `thermo` e o Margules
  pela definição e pelos dados NIST), lista de testes e contagem do `CLAUDE.md`
  (14 scripts, 13 automatizados) e duas ressalvas em registros antigos
  (2026-07-23 e 2026-07-27). **Pendente, a decidir pelo autor — não alterado:**
  (a) o mapeamento ainda diz, na frase que introduz a tabela e nas linhas de
  **Margules 1P** e **Van Laar**, "validado contra `thermo`", o que é falso para os
  dois; o Margules 1P agora tem validação indireta (redução ao 2-P) e o Van Laar
  **não tem validação independente** — proposta: estender o teste de primeiros
  princípios ao Van Laar (Gᴱ/RT = A₁₂A₂₁x₁x₂/(A₁₂x₁ + A₂₁x₂)) e ao Margules 1-P
  direto, e então corrigir essas linhas; (b) a decisão sobre os círculos vazados no
  ln γ (acima).

- **(2026-10-08) Retirar o "Comparativo" do gráfico de ln γ; auditoria de
  funções de pouco valor.** Depois de o assistente responder que os círculos
  vazados do ln γ (o mesmo modelo avaliado nos x₁ da tabela) caem sobre a
  curva e não informam nada, o autor decidiu: "se os pontos [...] são
  redundantes, não há razão para plotá-los" e ordenou "pode retirar e me avise
  se tem mais inutilidades como essa na aplicação". **Feito** em
  `fletando_grafico.py`: saíram as duas séries que "Comparar" acrescentava ao
  `chart_gamma`, a coluna "Comparativo" da legenda do ln γ (no card e na lupa) e
  a lógica de limpá-las (`invalidar_comparacao`, segunda chamada de "Comparar");
  `montar_legenda_gamma()` não recebe mais coluna; o ln γ agora só tem a curva do
  modelo e **não muda com "Comparar"**. O P-x-y não mudou. Textos de ajuda dos
  tópicos "Comparar" e "ln γ" ajustados. **Revê parte das decisões de
  2026-10-03** (paleta com comparativo vazado no ln γ; peso do tooltip dos
  vazados no ln γ; legenda em grade com três colunas no ln γ). Verificado por
  captura a 1400 px (exemplo metanol/dimetilbuteno + "Comparar": P-x-y com os
  vazados e ΔP = 31,78 %/Δy = 0,1530, iguais aos de antes; ln γ só com
  "Modelo"; lupa do ln γ abre sem a coluna) e a 360 px (carrega); testes
  passam. Corrigida de passagem uma quebra de string estranha no texto do
  tópico "Comparar" (sem efeito no texto exibido).
  *Auditoria pedida (sem alteração; para o autor decidir).* Método:
  varredura estática de funções sem uso em `gemini.py` e `fletando_grafico.py`
  (nenhuma encontrada), conferência de dependências e leitura funcional de cada
  recurso da tela; **não há telemetria de uso real**, então o juízo de utilidade é
  do assistente. Candidatos, do mais ao menos claro: (1) **protótipos
  `interface/main.py` e `interface/fletando.py`** — já descritos como "só registro
  da evolução"; o `main.py` importa `matplotlib`, que **não está nas dependências**
  do projeto, então nem roda no ambiente do projeto; (2) **lupa dos gráficos** —
  abre o mesmo gráfico em tamanho maior, não é zoom de região (decidida pelo autor
  em 2026-10-03 sabendo disso); (3) **ⓘ do ΔP e do Δy** — explicam o que o tópico
  de ajuda "Comparar" já explica; (4) **"Desfazer"** — só guarda estados de
  "Buscar do Banco" e de regressão (até 5); digitar valor e mover slider não entram;
  (5) **botão "Gerar Gráfico"** — não é inútil (é o gatilho decidido em 2026-09-21),
  mas é a causa de os marcadores cheios ficarem defasados ao editar a tabela e de
  dois avisos e vários parágrafos de ajuda existirem; atualizar os pontos ao editar
  tornaria o botão e esses avisos desnecessários; (6) **`teste_dioxano_nrtl.py`**
  — teste manual visual de um par sem fonte experimental, redundante com os testes
  automatizados; (7) cosmético: a mensagem pós-"Comparar" ("calculada em N
  ponto(s)") conta composições distintas, não os pontos usados no erro.
  Nada acima foi alterado.

- **(2026-10-08) Decisões do autor sobre a auditoria: retirar protótipos,
  "Desfazer" e "Gerar Gráfico" (automatizado), teste manual do dioxano; manter
  lupa e ⓘ; mensagem do "Comparar" mais conclusiva.** Resposta item a item à
  lista de "inutilidades" da entrada anterior: **(1) "retire, é inútil e já
  atrapalhou bastante ao iniciar novas seções"** — removidos `interface/main.py`
  e `interface/fletando.py` (protótipos antigos). Consequências tratadas:
  `.replit` apontava para eles (`entrypoint`, `deployment.run` e um workflow
  "Start application"); agora `entrypoint` e `deployment.run` usam
  `interface/fletando_grafico.py` (com `uv run`, como o workflow "Start Grafico",
  que já era o que o botão Run executa) e o workflow antigo saiu — **não testado no
  Replit** (só nesta nuvem), a conferir pelo autor. **Achado:** o
  `teste_parse_ponto_tabela.py` importava `parse_ponto`/`pontos_para_series` de
  `fletando.py`, ou seja, testava a cópia do protótipo, não o código da linha
  viva (as duas eram idênticas, conferido por diff); passou a importar de
  `fletando_grafico.py`. **(2) "mantém, serve para dar ênfase numa imagem
  projetada em sala" (lupa) e (3) mesmo sentido (ⓘ do ΔP/Δy)** — mantidos, sem
  mudança; o motivo (ênfase na projeção em sala) fica registrado como razão de
  ser desses dois recursos. **(4) "pode retirar" ("Desfazer")** — removidos o
  botão, o histórico de até 5 estados (`empilhar_historico`, `desfazer`,
  `historico_parametros`), a dica ao tocar no botão apagado e os trechos de ajuda
  que o citavam. **(5) "retire e automatize como sugeriu" ("Gerar Gráfico")** —
  botão removido (e com ele o estilo "primário" de botão, que só ele usava); os
  pontos da tabela agora entram nos gráficos **ao sair do campo ou apertar Enter,
  desde que o conteúdo da tabela tenha mudado** desde o último desenho
  (`assinatura_tabela`, `ao_sair_do_campo`): entrar e sair de uma célula sem editar
  não redesenha nem apaga a comparação; a cada tecla roda só `invalidar_comparacao`
  (já era assim); excluir linha também redesenha. A mensagem "Tabela editada: a
  comparação foi escondida. Clique em "Comparar" de novo." sobrevive ao redesenho
  (flag `comparacao_escondida`). **Mudança de comportamento na contagem de
  "linhas ignoradas":** só conta a linha com os três campos preenchidos e número
  inválido; linha incompleta (um ponto ainda sendo digitado) deixa de gerar aviso —
  sem isso, cada Tab no meio de uma linha mostraria o aviso. Isso **supera a parte
  "Gerar Gráfico" da decisão de 2026-09-21** (gatilho manual) para os pontos da
  tabela; o gatilho da **regressão** continua manual (botão dedicado). Textos de
  ajuda atualizados (primeiros passos, dados experimentais, sistema, parâmetros,
  comparar, P-x-y). **(6) "não vejo relevância em manter"** — removido
  `testes/teste_dioxano_nrtl.py` (app Flet manual que só plotava o NRTL do
  dioxano/metanol; o gráfico do app já mostra isso). A contagem de testes passa a
  **13 scripts, todos automatizados**. **(7) "faça algo melhor, mais conclusivo"** —
  a mensagem pós-"Comparar" deixou de dizer "calculada em N ponto(s)" (que contava
  composições x₁ distintas, não os pontos do erro) e passou a: "Comparação feita
  com N ponto(s) da tabela. Maior desvio de pressão: X % em x₁ = …. Maior desvio de
  y₁: … em x₁ = …." — N é o nº de pontos que entram no erro, e os dois "maior
  desvio" dizem **onde** o modelo mais se afasta (o que o RMS esconde; útil para
  achar ponto digitado errado ou a região em que o modelo falha). Não há veredito
  ("bom/ruim"): isso exigiria um limiar, que é decisão do autor. Verificado por
  captura a 1400 px: digitar P, x₁ e y₁ de uma linha (Tab entre os campos) faz o
  ponto aparecer sem clique, e o foco continua passando de célula em célula;
  exemplo metanol/dimetilbuteno + "Comparar" dá ΔP = 31,78 %/Δy = 0,1530 (iguais
  aos de antes) com a mensagem nova (40,35 % em x₁ = 0,183; 0,2856 em
  x₁ = 0,068); entrar e sair de célula sem editar mantém a comparação; editar um
  valor a esconde, com a mensagem, e o gráfico se atualiza ao sair; excluir linha
  redesenha; a 360 px carrega. Bug achado e corrigido durante a verificação:
  `on_blur=ao_sair_do_campo` (referência direta) quebrava a carga porque a função é
  definida depois das linhas iniciais — trocado por `lambda`, como já era antes.
  Testes passam.

- **(2026-10-08) Van Laar e Margules 1-P validados com os dados NIST, não
  com o dioxano nem a planilha.** Ao ler a pendência (2), o autor observou que
  esses modelos "foram validados e provavelmente com dados do dioxano ou da
  planilha do YouTube", e que seria melhor usar "dados que já temos
  oficializados, já que a `thermo` não possui essas funções". **Esclarecimento
  do assistente:** não foram validados com nenhum dos dois — o dioxano/metanol não
  tem fonte, a planilha XSEOS só serve ao Margules 2-P, e o único teste do Van
  Laar até então era a ida e volta da regressão (dado sintético gerado pelo
  próprio modelo, que não é independente). **Feito:**
  `testes/teste_van_laar_margules_1p_nist_ln_gamma.py`, no padrão do teste do
  Margules 2-P: nas 10 isotermas NIST (etanol/água ×5, metanol/dimetilbuteno ×4,
  clorofórmio/MEK ×1), ln γ experimental pelo método indireto no interior
  (0,10 ≤ x₁ ≤ 0,90, Psat da `thermo`) contra o modelo ajustado por Barker, e um
  **estimador linear independente do Barker** — Van Laar: x₁x₂·RT/Gᴱ = x₁/A₂₁ +
  x₂/A₁₂ (reta em x₁); Margules 1-P: Gᴱ/(RT·x₁x₂) = A (média). **Medido
  (tolerâncias fixadas depois, nada no motor foi ajustado):** Van Laar RMS de ln γ
  0,019–0,065 (tolerância 0,080), do mesmo nível do Margules 2-P (0,027–0,065);
  Margules 1-P 0,041–0,119 (tolerância 0,150) — pior em etanol/água, sistema
  assimétrico, limite do modelo de um parâmetro e não bug; diferença Barker ×
  estimador linear até 0,41 no Van Laar (tolerância 0,50, folgada porque a reta usa
  só o interior e 1/intercepto amplifica ruído) e até 0,28 no Margules 1-P
  (tolerância 0,35); sinais corretos nas 10 isotermas; Van Laar com A₁₂, A₂₁ < 0 no
  clorofórmio/MEK (−0,97; −1,33, comparáveis ao estimador linear: −0,88; −1,42).
  **Sensibilidade do teste:** com o Van Laar propositalmente errado (γ₁ e γ₂
  trocados) o teste reprova as 10 isotermas e sai com código 1. **Ressalva:** isso
  mostra que o modelo descreve os dados, não que a fórmula está escrita certa; o
  Margules 1-P tem também a redução ao 2-P (primeiros princípios), o **Van Laar
  não tem teste por primeiros princípios** — pendência (2) acima, a decidir pelo
  autor. **Documentação corrigida junto:** as linhas de Margules 1P e Van Laar da
  tabela de validação do mapeamento (diziam "`thermo` (faixa completa)", o que era
  falso), a frase que introduz a tabela, a lista de testes (e a menção ao
  `teste_dioxano_nrtl.py`, já removido) e o tópico "Sobre" do app (agora cita o
  Van Laar). 14 scripts de teste, todos automatizados.

- **(2026-10-08) Koretsky como fonte conferida: Gibbs-Duhem, fórmulas, exemplos
  e Apêndice A; ordens do autor sobre o que fazer com ele.** O autor trouxe, do
  Google Drive e em recortes de PDF, o livro *Engineering and Chemical
  Thermodynamics* (Koretsky, 2ª ed., Wiley, 2013), "um dos livros de referência
  além do Van Ness", para (a) conferir a fonte pendente do Gibbs-Duhem e (b) ver
  se traz tabelas úteis. O livro inteiro não coube (limite de 10 MB do conector;
  a leitura em texto parou na p. 109), então o autor mandou os recortes: cap. 6
  (pp. 340-342), cap. 7 (pp. 422-496), Apêndice A e pp. 442-483. **Lido:** pp.
  340-342, 422-496 e 639-640 (Tabela A.1). **Não lido:** o resto do livro, em
  particular os problemas do cap. 8 (onde pode estar a origem do exercício de
  1,4-dioxano/metanol do professor; o Exemplo 8.7, p. 488, usa dioxano/água).
  *(1) Gibbs-Duhem — fonte confirmada.* Koretsky, seção 6.3, pp. 340-341, Eq.
  (6.19): Σ nᵢ dK̄ᵢ = 0 a T e P constantes; seção 7.4, p. 422, Eq. (7.42):
  Σ xᵢ d ln γᵢ = 0; p. 423, Eq. (7.43), forma binária a T e P constantes; Eqs.
  (7.48) e (7.49): Ḡᵢᴱ = RT ln γᵢ e gᴱ = RT Σ xᵢ ln γᵢ; Eq. (7.50) e p. 428:
  teste da área, deduzido a T e P constantes mas aplicável direto a dados
  isotérmicos porque a dependência de γ com P é pequena (sustenta a redação do
  tópico "ln γ"). A citação de Smith, Van Ness e Abbott, que era de memória,
  saiu desse tópico; continua em "Sobre" só para o método de Barker (do
  mapeamento). Eqs. (8.17) a (8.20) (azeótropo: x = y e γₐ/γ_b = P_b^sat/Pₐ^sat)
  sustentam a relação do azeótropo no mesmo tópico. *Autor: "1 sim, se for
  relevante" — citado em "ln γ", "Diagrama P-x-y" (azeótropos de pressão máxima
  mais comuns, p. 486) e "Sobre".*
  *(2) Teste das fórmulas ("2 sim").* `testes/teste_koretsky_formulas_e_exemplos.py`,
  bloco A: as Tabelas 7.2 e 7.4 transcritas à parte (notação do livro, A e B em
  J/mol) contra `MODELS_GE` em 101 composições e vários conjuntos de parâmetros —
  Margules 1-P, Margules 2-P (formas A,B e A_ab,A_ba), Van Laar, Wilson, NRTL e
  UNIQUAC (com q′ = q): erro máximo ~1e-13. Isso dá ao **Margules 1-P e ao Van
  Laar uma fonte de livro** para a fórmula (a `thermo` não os tem). A transcrição
  da Tabela 7.4 (com q′) reproduz o Exemplo 7.12 do livro (γ₁ = 2,67; γ₂ = 1,32)
  **com a₂₁ = +1380,3**: o livro imprime −1380,3, mas o próprio exemplo usa
  τ₂₁ = 0,014, que só sai com o sinal positivo (erro tipográfico do livro).
  Sensibilidade: com o Van Laar (γ₁ e γ₂ trocados) ou o Margules 2-P (A₁₂ e A₂₁
  trocados) injetados, o teste reprova e sai com código 1.
  *(3) Exemplos e problemas com resposta publicada ("3 sim").* Blocos B a D do
  mesmo teste. **B:** Tabela E8.9A (p. 492, benzeno/ciclo-hexano a 10 °C, 12
  pontos P-x-y, que o livro atribui à coletânea DECHEMA de Gmehling et al.;
  incluída no teste como constante, com a citação): com A = 1401 J/mol o app
  reproduz P_calc e γ da Tabela E8.9B com diferença máxima de 2,5 Pa e 0,004; a
  regressão de Barker dá A = 1406 J/mol no Margules 1-P (livro: 1401, 1399 e 1424
  conforme a função-objetivo) e A₁₂ = 0,5637, A₂₁ = 0,6265 no 2-P (livro: 0,5641 e
  0,6227, de A = 1397 e B = 69; regressão linear do livro: 1402 e 75,1); a
  diferença vem de o app minimizar P e y juntos e o livro só P. **C:** Exemplo
  8.5 (etanol/água a 70 °C, A = 3590 e B = −1180 J/mol, y₁ = 0,48): app x₁ =
  0,114 e P = 0,548 bar, livro 0,12 e 0,55 bar (experimental 0,13 e 0,57).
  **D:** Problema 7.70 (acetona/clorofórmio a 35,17 °C, UNIQUAC com os parâmetros
  do livro, q′ = q): P = 268,1 torr (+2,35 % contra 261,9 medido) e y₁ = 0,153
  (0,143 medido). Tolerâncias fixadas depois de medir; nada no motor foi ajustado.
  **Achado, não corrigido:** o UNIQUAC do app usa q (sem q′), como o ChemSep; nos
  Problemas 7.68 (acetona/água) e 7.69 (etanol/benzeno) o livro usa q′ e as
  respostas do app diferem (7.68: γ₁ = 2,49 sem q′ e 2,24 com q′, contra 2,30
  medido; 7.69: P 17 % abaixo do medido sem q′) — pendência (7) da lista.
  *(4) Apêndice A ("conferência de Psat") — `testes/teste_psat_koretsky_apendice_a.py`.*
  Tabela A.1.1 (Antoine: ln Psat[bar] = A − B/(T[K] + C), válida de Tmin a Tmax)
  para 11 compostos, lida da imagem; a Psat da `thermo` concorda dentro da faixa
  em geral a menos de 1,5 % (9 dos 11) e no máximo 3,1 % (acetona a 251 K, ponta
  fria); constantes críticas: Tc a 0,3 %, Pc a 2,6 %, ω a 0,011. Os maiores
  desvios são da Antoine de 3 parâmetros do livro, não da `thermo`: no ponto de
  ebulição normal a `thermo` reproduz 101,325 kPa com erro ≤ 0,05 % e a Antoine do
  livro erra até 1,8 % (clorofórmio). O livro não tem 2-butanona,
  2,3-dimetil-2-buteno nem 1,4-dioxano. *(Item 2 do Apêndice: sem dado binário de
  ELV nas tabelas; as tabelas de dados úteis do livro são esta e o E8.9A.)*
  *(5) Tópicos de ajuda ("4 sim").* Escritos como rascunho do assistente, a
  revisar pelo autor: **"Modelos de Gᴱ e quando usar cada um"** (o que é gᴱ e como
  dele saem os γ; cada um dos 7 modelos com o que o livro diz — Margules 1-P
  simétrico e a interpretação molecular de A, Van Laar com A e B de mesmo sinal,
  Wilson com Λ positivos e sem imiscibilidade parcial, NRTL e UNIQUAC para
  parcialmente miscíveis, UNIFAC preditivo; a estatística de 3563 pares DECHEMA, p.
  437; um roteiro "Qual usar", que é **síntese do assistente**; e como os modelos
  foram conferidos) e **"Limitações e cuidados"** (só isotérmico e parâmetros
  válidos à T dos dados; vapor ideal e Raoult modificada sem Poynting; uma só fase
  líquida e A/RT > 2 no Margules 1-P — limite **derivado pelo assistente** de
  d²(gᴱ/RT)/dx₁² = 1/(x₁x₂) − 2A/RT —; unidades e ausência de teste de
  consistência; Psat conferida contra o Apêndice A; o que o app não faz).
  Verificado por captura de tela a 1400 px (os dois tópicos, com rolagem); o "Sobre"
  ganhou o bloco "Livro de referência" e a frase das equações cita o Koretsky.
  *(6) "Veja se tem algo que dê um ganho sensível" (pp. 442-483).* O que foi achado:
  os Problemas 7.68 a 7.70 e o Exemplo 7.12 (UNIQUAC com parâmetros publicados) e o
  Exemplo 8.5 (já incorporados acima); a observação do q′ (pendência 7); o texto
  sobre dependência com T (Eqs. 7.75 a 7.81; o Exemplo 7.13 estima A a 60 °C a
  partir de dado a 10 °C com erro de cerca de 5 %), que o app não usa — parâmetros
  de uma T não são extrapolados; e 12 pontos de γ experimental de etanol/n-heptano
  a 50 °C (Exemplo 7.12, p. 443), **não incorporados** (seriam uma fonte de
  validação do UNIQUAC/NRTL do banco contra γ medido). Fora do escopo do app: a
  maior parte dos pontos 7.1-7.62 (fugacidade por equação de estado).

- **(2026-10-08) Ordens do autor sobre as pendências: Van Laar, q′, aviso de
  instabilidade; o resto aguarda.** Resposta item a item à lista de pendências:
  **(1)** veredito "bom/ruim": "vou falar com o orientador" — aguarda; **(2)**
  "faz" — feito (`teste_van_laar_primeiros_principios.py`); **(3)** ln γ
  experimental: o autor perguntou se tem relevância ou cai na redundância dos
  vazados — respondido no chat, **aguarda decisão**; **(4)** "esqueça o Replit até a
  segunda ordem" — suspenso; **(5)** dioxano/metanol: aguardando o contato com o
  orientador; **(6) e (9)**: "aguardar pedido"; **(7)** "prossiga" — feito no motor,
  **não ligado na UI** (ver pendência 7: com os a₁₂/a₂₁ do ChemSep, q′ piora o
  ajuste aos dados NIST; o que existe é a capacidade, conferida contra o livro, e a
  decisão de ligar fica com o autor); **(8)** "se o custo for baixo, implemente" —
  custo baixo (uma função de 15 linhas e um texto), implementado. **Escolhas do
  assistente, a confirmar:** (a) o aviso de instabilidade fica **no card
  "Parâmetros do modelo"**, e não na mensagem de status, por visibilidade; (b) o
  aviso é geral (qualquer modelo), por d ln(x₁γ₁)/dx₁ ≤ 0 na malha de 101 pontos,
  e não só o A/RT > 2 do Margules 1-P — a faixa informada é aproximada (erro de até
  ~0,02 em x₁ pela malha); (c) apesar de (6) e (9) aguardarem pedido, mudei **duas
  frases factuais** dos tópicos "Limitações" e do "?" do exemplo
  metanol/dimetilbuteno que passariam a ser falsas ("o app não avisa"); o resto do
  texto dos tópicos ficou como estava; (d) o tópico "Sobre" passou a dizer que o
  Van Laar também foi conferido pela definição termodinâmica. **Achado cosmético
  não tratado:** a nota do exemplo clorofórmio/MEK diz que a mensagem após
  "Comparar" "conta 21 composições distintas", o que deixou de valer quando a
  mensagem passou a contar os pontos do erro (decisão de 2026-10-08, item 7 da
  auditoria) — entra em (9), ajuste de texto.

- **(2026-10-08) Contato no tópico "Sobre".** Pedido do autor: no "Sobre", colocar o
  e-mail leolins22@gmail.com para sugestões de implementações futuras e feedback de
  usuários. Seção nova "Contato: sugestões e feedback", logo depois do autor e antes
  das bibliotecas (texto do assistente, a revisar). O e-mail passa a ficar público
  no app e no repositório, por pedido dele. **Escolha do assistente, a confirmar:** o
  endereço é texto simples, sem link clicável (o diálogo é texto formatado simples).

- **(2026-10-08) ln γ experimental no gráfico, faixa 0,10–0,90; contato do "Sobre"
  no fim.** Ordens do autor: **(3)** "faça o item 3 com a faixa 0,10–0,90" — feito
  (ver pendência 3); a pergunta dele sobre redundância foi respondida antes: não é
  a mesma coisa que os vazados, porque agora há um dado independente (a tabela)
  para comparar com a curva. **(7)** o autor perguntou qual o ganho de implementar
  q′ — respondido no chat (para a UI, nenhum com os parâmetros do banco; o ganho é
  reproduzir exercícios de livro com parâmetros ajustados com q′). **"Sobre"**:
  "coloque no começo ou no final" — o contato foi para o **final** do tópico, depois
  de "Licenças" (escolha do assistente, a confirmar: contato como último item;
  voltar ao começo é mover quatro linhas). **Escolhas do assistente, a confirmar:**
  círculo nos dois componentes (a cor distingue γ₁ de γ₂), marcadores desenhados
  depois das curvas, e o eixo vertical passa a incluir os marcadores (um ponto
  muito fora, por dado errado, achata o gráfico — a faixa 0,10–0,90 limita isso,
  não elimina).

- **(2026-10-08) Opção "Usar q′" no UNIQUAC (checkbox), desligada por padrão.** O
  autor propôs ("é que tal um check box que dá a opção de usar q′") e, depois de o
  assistente levar a análise (efeito só em 14 compostos; piora o ajuste com os
  a₁₂/a₂₁ do banco; risco de o aluno achar que ligar é "mais correto"), liberou:
  "Libera, faça o checkbox". Implementação na pendência 7. **Escolhas do assistente,
  a confirmar:** (a) padrão **desligado**; (b) caixa **apagada com o motivo** quando
  o par não tem q′ ≠ q (em vez de escondê-la); (c) selo próprio "Banco, com q′" com o
  aviso de que os parâmetros foram ajustados com q; (d) ao trocar para um par sem
  efeito ou sair do UNIQUAC, a caixa **volta a desligada** (sem estado escondido);
  (e) a opção usa o q′ do ChemSep, a mesma fonte dos r/q (se os r/q vêm dos grupos
  UNIFAC, não se aplica); (f) glifo: o prime "′" aparece como "'" na fonte
  renderizada (cosmético).

- **(2026-10-08) Confirmação, pelo autor, das escolhas do assistente de 2026-10-08
  ("Todos").** Ao ser perguntado qual das escolhas pendentes liberava, o autor
  respondeu "Todos". Passam a valer como decisões do projeto: (1) **contato
  (e-mail) no final do tópico "Sobre"**, depois de "Licenças"; (2) **q′ do UNIQUAC
  desligado por padrão**, com a caixa apagada e o motivo quando o par não tem
  q′ ≠ q, selo próprio "Banco, com q′" e volta a desligada ao trocar de par sem
  efeito ou sair do UNIQUAC; (3) **círculo nos dois componentes** do ln γ
  experimental da tabela (a cor distingue γ₁ de γ₂), marcadores desenhados depois
  das curvas e eixo vertical incluindo os marcadores; (4) **aviso de instabilidade
  da fase líquida no card "Parâmetros do modelo"** (e não na mensagem de status),
  geral para qualquer modelo, pela condição d ln(x₁γ₁)/dx₁ > 0 na malha de 101
  pontos. **Interpretação do assistente, a confirmar:** "Todos" foi lido como
  referente a essas quatro escolhas (a lista que a pergunta anterior apresentava),
  não como liberação dos itens que aguardam o orientador (1 e 5) nem dos ajustes
  de texto dos tópicos "Modelos de Gᴱ" e "Limitações" (6 e 9), que seguem
  aguardando pedido explícito.

- **(2026-10-08) Itens 6 e 9: ajustes de redação nos tópicos "Modelos de Gᴱ" e
  "Limitações" e na nota do exemplo clorofórmio/MEK.** Ordem do autor: "Itens 6 e 9,
  faça os ajustes", sem dizer quais. O assistente releu os dois tópicos e fez só o
  que achou verificável, **sem mudar conteúdo técnico**: (a) a nota do exemplo
  clorofórmio/MEK dizia que a mensagem após "Comparar" "conta 21 composições
  distintas", o que deixou de valer quando a mensagem passou a contar os pontos do
  erro; agora diz que os dois pontos em x₁ = 0,252 entram no erro e a mensagem conta
  os 22; (b) no tópico "Modelos de Gᴱ", o roteiro "Qual usar" passou a dizer que é
  um roteiro prático montado pelo app a partir das descrições do livro, não regra
  publicada nele (antes só dizia "um roteiro"); (c) no Margules 1-P, A/RT > 2 passou
  a ser apresentado como vindo da condição de estabilidade da fase líquida. **Não
  alterado:** o resto do texto, nem as citações de páginas e equações do Koretsky
  (não reconferidas nesta rodada). **A confirmar pelo autor:** se há outros ajustes
  que ele tinha em mente depois de ler os tópicos no celular; a leitura crítica dele
  continua sendo o que fecha o item 6.

- **(2026-10-08) Teste do motor de cálculo no Pyodide (formato web estático);
  nada decidido.** Pergunta do autor sobre hospedagem gratuita e amostra ao
  orientador (que usa **Mac**, seção 2.4 do mapeamento: um `.exe` do Windows não
  serve). O assistente testou, em rascunho fora do repositório e por Node, o
  `calculos/gemini.py` dentro do Pyodide **314.0.6 (Python 3.14.2, numpy 2.4.6,
  scipy 1.18.0, pandas 3.0.2)** — o que o `flet publish` do Flet 1.0.0 embute — e
  também no 0.27.7: NRTL e Wilson (banco), UNIQUAC, UNIFAC e a regressão de Barker
  (Van Laar e NRTL, isoterma de 90 °C do NIST) rodam e dão **resultados idênticos
  ao ambiente nativo**; o alerta do XML do ChemSep não dispara. `thermo`, `chemicals`
  e `fluids` entram como pacotes de Python puro do PyPI (no Pyodide 0.27.7 foi preciso
  carregar o pacote `sqlite3`; no 314.0.6 não). Tempos em Node: cerca de 10 s para
  carregar bibliotecas e `thermo`, mais 4 s no primeiro cálculo; pico de 1,1 GB no
  processo Node (não é medida de navegador). **Não testado:** a interface Flet em
  navegador, o seletor de arquivos, e tempo e memória no celular. **Achado de
  empacotamento:** `flet publish` empacota só a pasta do script (`interface/`) e lê
  `pyproject.toml` dessa mesma pasta; `calculos/` e `referencias/` ficam fora, então
  a publicação exige uma pasta de trabalho temporária (passo a passo entregue no
  chat). Dois caminhos de hospedagem institucional (STI/UFC e RNP) foram pesquisados,
  sem confirmação de que alunos de graduação possam usar; texto de chamado para a STI
  entregue no chat, não enviado.

  **Resultado do autor no PC (2026-10-08, Windows, Chrome):** executou o passo a
  passo (cópia temporária com `calculos/`, `interface/`, `referencias/` e
  `pyproject.toml`; `main.py` de entrada; `uv run flet publish`; servidor local na
  porta 8000) e o app em formato web estático (Pyodide) funcionou **"sem diferença
  sensível"** em relação ao app normal da porta 5000, exceto a primeira carga, que
  demorou alguns segundos a mais, como previsto. **Ainda não testado:** celular
  (Passo 6), consumo de memória no navegador, hospedagem pública (GitHub Pages ou
  similar) e o Mac do orientador. Nenhuma decisão tomada; o formato estático segue
  como candidato a avaliar, e a escolha de hospedagem é do autor.

  **F5 no formato estático (2026-10-09, PC do autor):** o autor viu uma tela de erro
  "PythonError: Traceback (most recent call last):" ao dar F5 numa publicação feita
  com uma cópia local **24 commits atrás** (HEAD local `8e9a692`; o `git status`
  dizia "up to date" porque o `fetch` não tinha sido refeito). Com o código atualizado
  (`ee99525`), um Claude Code local republicou (Python 3.14, Pyodide 314.0.6) e
  testou: **a primeira carga funcionou e o F5 não deu erro** (nada no Console).
  Tempo medido por ele: cerca de 35 a 45 s até a interface aparecer, **também no F5**
  (o worker reinicia a cada recarga). Causa do erro anterior **não provada**: pode ter
  sido a versão antiga da cópia ou estado do navegador. **Pendente:** o autor repetir
  o F5 por conta própria na publicação nova; celular; memória. O tempo de carga a
  cada recarga (~40 s) é um ponto de atenção para uso em aula.
  **Confirmação do autor (2026-10-09):** no PC dele, depois do F5, o app voltou em
  **cerca de 15 a 18 s** (menos que os 35 a 45 s medidos pelo Claude Code local num
  navegador automatizado); o F5 funcionou, sem erro. Para comparação, o app normal
  em `localhost:5000` (servidor Python) recarrega com F5 em cerca de **2 s**.
  **Teste no celular (2026-10-09, autor):** abrindo `http://IP:8000` pela rede local, o
  tempo de carga e de recarga foi **levemente menor que no PC**; os gráficos redesenham,
  a troca de modelo e a regressão de Barker respondem em bom tempo (a regressão
  "imediata"), "Comparar" funciona, a rotação do aparelho ficou boa, sem erro, sem
  crash da aba e **sem aquecimento perceptível**. Modelo e RAM do aparelho não foram
  informados; a memória não foi medida, só observado que não houve falha. Continuam
  pendentes: hospedagem pública e o Mac do orientador. Nenhuma decisão tomada; a escolha
  de formato e de hospedagem é do autor.
  **Publicação no GitHub Pages (2026-10-09, feita pelo autor no PC dele):** site estático
  gerado com `flet publish --base-url equilibrio-fases-GE-tcc` a partir de uma cópia
  temporária (`calculos/`, `interface/`, `referencias/`, `pyproject.toml` e um `main.py`),
  enviado à branch `gh-pages` (só o build, sem histórico; `push --force`) e ligado em
  Settings → Pages (Deploy from a branch, `gh-pages`, `/ (root)`). Endereço:
  `https://lins84.github.io/equilibrio-fases-GE-tcc/`. Um tropeço no caminho: o primeiro
  `git commit` falhou por falta de identidade do Git, o que impediu a criação da branch
  (o `push` dizia "src refspec gh-pages does not match any"); resolvido com
  `git config user.email/user.name` local à pasta temporária, sem `--global`. **Resultado
  (autor):** funcionou de primeira — no PC, em Wi-Fi, cerca de **18 s** até a interface;
  no celular, com **dados móveis**, cerca de **40 s**. Reproduz o que se esperava: a
  carga é maior que a do servidor Python (~2 s no F5) e depende de internet. Fica
  pendente o **Mac do orientador**. Nenhuma decisão de rumo tomada por isso: o
  repositório continua com o app normal (`flet run`) como linha viva, e o site é um
  espelho gerado a mão. Para atualizar o site é preciso repetir a publicação (não há
  automação, e não foi pedida).

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
