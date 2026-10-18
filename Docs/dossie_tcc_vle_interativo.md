# Dossiê do projeto "VLE Interativo" — material de apoio para a redação do TCC

**Gerado em 2026-10-18** a partir do `CLAUDE.md` e do `Docs/mapeamento_e_plano_TCC-1.md` do repositório (último commit lido: `68fcb6c`) e de conferências feitas no repositório nesta data.

## 0. Como usar este arquivo (leia primeiro)

Este dossiê é um **resumo de fatos já registrados e verificados no projeto**, com a fonte de cada um. Regras para quem for redigir a partir dele:

1. **Não inventar.** O que não está aqui deve ser perguntado ao autor ou marcado com `[conferir]`. Isso vale especialmente para números, páginas de livro, DOIs e nomes.
2. **Referências bibliográficas.** Só as da seção 14 foram conferidas, e cada uma tem o status dito ali. Qualquer outra é "de memória" e precisa ser conferida na fonte antes de entrar no texto.
3. **Estado dos testes.** Os resultados numéricos vêm dos scripts de `testes/` rodados nas datas registradas. **Nesta data os testes não foram reexecutados** (o ambiente de geração não tinha o `.venv` do projeto). Os 20 scripts existem: foi conferido por listagem.
4. **Decisões são do autor.** Onde o texto diz "decisão do autor", ela consta no registro com data. O que for escolha do assistente aparece como tal.
5. **Reais vs. a confirmar.** Itens da seção 15 são pendências em aberto e não devem ser escritos como resolvidos.

## 1. Identificação

- **Título de trabalho:** Ferramenta Computacional Interativa para o Ensino do Equilíbrio de Fases (nome do aplicativo: **VLE Interativo**; subtítulo na tela: "Equilíbrio líquido-vapor com modelos de Gᴱ").
- **Autor:** Leonardo de Sousa Lins, graduando em Engenharia Química (UFC).
- **Orientador:** Dr. Filipe Xavier Feitosa. **Instituição:** UFC — Centro de Tecnologia — DEQ.
- **Repositório (público):** https://github.com/Lins84/equilibrio-fases-GE-tcc
- **Aplicativo publicado (GitHub Pages):** https://lins84.github.io/equilibrio-fases-GE-tcc/
- **Contato que aparece no aplicativo ("Sobre"):** leolins22@gmail.com

## 2. Problema, solução e objetivos

- **Problema.** Os modelos de coeficiente de atividade (Margules, Van Laar, Wilson, NRTL, UNIQUAC, UNIFAC) têm matemática que dificulta a interpretação imediata dos diagramas de equilíbrio. Falta abstração ligada à intuição visual e ferramentas em tempo real para o ensino de Termodinâmica na graduação. [mapeamento 1.1]
- **Solução.** Aplicação em Python (Flet + `thermo`) em que o usuário ajusta parâmetros dos modelos e vê o efeito nos diagramas. [mapeamento 1.2]
- **Três eixos de uso** [mapeamento 1.3]:
  1. **Didático-visual:** diagramas mudando ao vivo; prioriza fluidez e clareza.
  2. **Validação de exercícios:** reproduzir exercícios de livros-texto (Koretsky; Smith, Van Ness e Abbott), com exatidão numérica comparável ao gabarito.
  3. **Pesquisa acadêmica:** instrumento de teste/análise com dados experimentais reais, importação de dados tabulados e rigor numérico.
- **Usuário final:** o **orientador**, que pretende usar a ferramenta em aulas de Termodinâmica. Implica projeção em sala (fontes grandes, alto contraste), baixa tolerância a erros e ambiente **Mac** do orientador. [mapeamento 1.4]

## 3. Arquitetura e tecnologia

- **Linguagem e bibliotecas (versões travadas no `uv.lock`):** Python; Flet 1.0.0 e flet-charts 1.0.0; `thermo` 0.6.1; `chemicals` 1.5.2; NumPy e SciPy (o `uv.lock` traz mais de uma versão de cada, por plataforma; no ambiente do navegador o Pyodide usa NumPy 2.4.6 e SciPy 1.18.0). [uv.lock, conferido em 2026-10-18]
- **Separação em camadas:** `calculos/gemini.py` (motor de cálculo) e `interface/fletando_grafico.py` (interface). Tamanho medido em 2026-10-18: **1048 linhas** o `gemini.py` e **3831 linhas** a interface. (O `CLAUDE.md` ainda cita ~720 e ~1525, valores antigos.)
- **Decisão estrutural do autor (julho/2026):** escrever as **equações dos modelos diretamente no código**, usando a `thermo` apenas como fonte de dados (pressão de vapor, parâmetros) e como **oráculo de validação**, nunca como motor de cálculo. Consequência: a validação deixa de ser circular e a física fica visível no código. [CLAUDE.md, seção A]
- **Cálculo:** Lei de Raoult modificada, **isotérmica** (`calculate_vle_isothermal`), vapor ideal, em malha de 101 pontos de x₁ (0 a 1, extremos inclusos).
- **Fluxo de desenvolvimento:** desenvolvimento no Claude Code; Replit como IDE (hoje suspenso); Termux/proot no celular; Windows no PC do autor. [mapeamento 4]

## 4. Modelos de Gᴱ implementados e como cada um foi validado

Sete modelos em `MODELS_GE`: Margules 1-P, Margules 2-P, Van Laar, Wilson, NRTL, UNIQUAC, UNIFAC.

| Modelo | Validação registrada |
|---|---|
| Margules 1-P | Equações do Koretsky; exemplos resolvidos do livro; redução ao Margules 2-P (A₁₂ = A₂₁); dado NIST. A `thermo` não tem Margules. |
| Margules 2-P | Equações do Koretsky (Tabela 7.2); Exemplos 8.5 e 8.10; definição termodinâmica (Gᴱ → ln γ por derivada de passo complexo, Euler, Gibbs-Duhem, limites); dado NIST; planilha XSEOS só como conferência secundária (diferença máx. 0,0005 = arredondamento da planilha). |
| Van Laar | Equações do Koretsky; definição termodinâmica (como o Margules 2-P, só para parâmetros de mesmo sinal); dado NIST. A `thermo` não tem Van Laar. |
| Wilson | `Wilson_gammas` da `thermo` + Tabela 7.2 do Koretsky. |
| NRTL | `NRTL_gammas` da `thermo` (erro máx. ~1e-15) + Tabela 7.2 do Koretsky. |
| UNIQUAC | `UNIQUAC_gammas` da `thermo` + Tabela 7.4 do Koretsky (com q′: Exemplo 7.12 e Problemas 7.68 a 7.70). |
| UNIFAC | `UNIFAC.from_subgroups` da `thermo`. |

- **Critério de validação (decisão do autor):** varrer **toda a faixa de composição** (101 pontos, extremos incluídos), não só pontos de exemplo. Foi esse critério que achou os bugs de limite. [CLAUDE.md, seção A]
- **Testes:** 20 scripts avulsos em `testes/`, rodados à mão (sem runner/CI), todos automatizados e com código de saída 1 se algo fugir da tolerância. Lista em `testes/`.

## 5. De onde vêm os parâmetros

Três origens, mostradas na tela por um **selo de origem** ("Fornecido", "Banco de dados", "Calculado", variantes de cautela) [mapeamento 2.8]:

1. **Fornecido** pelo usuário (slider ou valor digitado).
2. **Banco IPDB/ChemSep** (via `thermo.interaction_parameters.IPDB`): NRTL, Wilson e UNIQUAC. Margules e Van Laar não têm tabela no IPDB. O UNIQUAC usa r/q do XML do ChemSep quando os dois componentes constam nele (decisão do autor, 2026-10-06), com grupos UNIFAC como reserva; q′ é opcional, desligado por padrão.
3. **Regressão** dos próprios pontos P-x-y digitados, pelo **método de Barker** (ajuste direto de P e y).
   - **Barker (direto), não o indireto** (decisão do autor, 2026-09-13): trata o erro onde ele foi medido, em vez de propagá-lo por uma divisão que amplifica ruído perto de x₁ → 0 e 1.
   - **α₁₂ do NRTL fixo em 0,3** na regressão (decisão do autor, 2026-09-13); a insensibilidade do resíduo a α₁₂ entre 0,2 e 0,47 foi medida com dado NIST.
   - **Mínimo de pontos = número de parâmetros + 1** (decisão do autor, 2026-09-13).
   - **Aviso de regressão suspeita** (parâmetro a menos de 1 % de um limite da busca, ou otimizador que não converge); ele **não** cobre resíduo alto com parâmetros dentro dos limites.

## 6. Métrica de comparação calculado × experimental

- **ΔP relativo (%), RMS** e **Δy absoluto, RMS**, **reportados separadamente** (decisão do autor, 2026-09-27; a fórmula foi sugestão do assistente). Motivo: é como a literatura reporta ajuste de modelos de Gᴱ, e erro relativo em y amplificaria o ruído perto de 0 e 1.
- O **argumento numérico original** ("Barker melhora P e piora y") foi **descartado**: vinha de um CSV de origem desconhecida que foi removido do repositório. **Não usar esse exemplo no texto.** Com dado NIST confiável, o Barker reduz os dois erros.
- **Veredito "bom/ruim" depois de "Comparar"** exigiria um limiar de ΔP e Δy que **não está definido**; o autor vai conversar com o orientador. Não escrever limiar como decidido.

## 7. Dados experimentais com fonte citável (NIST/TRC ThermoML)

Dados do arquivo público NIST ThermoML (doi:10.18434/mds2-2422; Riccardi et al., *J. Comput. Chem.* 43, 879, 2022). O próprio ThermoML avisa que os números foram extraídos pelo TRC e **não avaliados criticamente**. Os arquivos estão em `referencias/` com fonte no cabeçalho.

| Sistema | Fonte | Dados | Observações |
|---|---|---|---|
| Etanol + água | Cristino et al., *Fluid Phase Equilib.* **341**, 48–53 (2013), doi:10.1016/j.fluid.2012.12.014 | 5 isotermas (363,3 a 423,7 K), 76 pontos, T-P-x-y; o aplicativo oferece 90 °C (12 pontos) e 108 °C (26 pontos) | Faixa de x₁ incompleta (vão de ~0,79 a ~0,997); T e P elevadas; teste da área inconclusivo. |
| Metanol + 2,3-dimetil-2-buteno | Feng, Dong e Li, *Fluid Phase Equilib.* **309**, 201–205 (2011), doi:10.1016/j.fluid.2011.07.014 | 4 isotermas (70 a 100 °C), 85 pontos; o aplicativo oferece 70 °C | Azeótropo de pressão máxima em x₁ ≈ 0,58–0,63; teste da área D = 2,8 a 6,5 % (consistente). |
| Clorofórmio + 2-butanona | Clara, Marigliano e Solimo, *J. Chem. Eng. Data* **51**, 1473–1478 (2006), doi:10.1021/je060150a | 303,15 K, 22 pontos | Desvio negativo; azeótropo de pressão mínima em x₁ ≈ 0,19–0,20; D = 3,4 %; P da 2-butanona pura 3,2 % acima da Psat da `thermo`. |

- **Dioxano + metanol (308,5 K):** par de um **exercício do professor sem fonte conhecida**. Não há validação experimental com fonte desse par; serve só para testar a mecânica do motor. O autor vai perguntar ao professor a origem do dado. [pendência]
- **Planilha XSEOS** (MEK/tolueno, 323,15 K; canal Youtermo): usada só como conferência secundária do Margules 2-P.

## 8. Resultados numéricos registrados (cada um vem de um script de `testes/`)

**Modelos do banco, sem ajuste aos dados** (etanol/água, 5 isotermas): ΔP 0,5–3,5 % e Δy 0,016–0,038 (NRTL, Wilson, UNIQUAC); UNIFAC chega a ΔP 4,7 % a 150 °C (esperado: preditivo). Em 90–108 °C: Wilson ΔP 0,5–0,8 %; NRTL 1,1–1,4 %; UNIQUAC 1,3–1,6 %; UNIFAC 0,9–2,3 %. [`teste_validacao_nist_etanol_agua.py`, 2026-10-06]

**Regressão de Barker:** convergência nas 5 isotermas × 5 modelos, sem parâmetro no limite, resíduo 0,007–0,023. Metanol/dimetilbuteno: ΔP 1,0–2,0 %, Δy 0,011–0,025. Clorofórmio/MEK: ΔP 1,5–1,6 %, Δy 0,008–0,009; Van Laar com A₁₂ = −0,97 e A₂₁ = −1,33. O azeótropo previsto pelos modelos ajustados acerta existência e tipo; a composição acerta a menos de 0,015 em x₁ no metanol/dimetilbuteno, mas no clorofórmio/MEK fica em ~0,14–0,15 contra 0,19 medido. [`teste_validacao_azeotropos_nist.py`, 2026-10-07]

**Ajuste de ln γ experimental (método indireto, faixa 0,10 ≤ x₁ ≤ 0,90, 10 isotermas NIST):** RMS de ln γ do Margules 2-P 0,027–0,065; do Van Laar 0,019–0,065; do Margules 1-P 0,041–0,119 (pior em etanol/água, que é assimétrico: limite do modelo de um parâmetro). [`teste_margules_2p_nist_ln_gamma.py`, `teste_van_laar_margules_1p_nist_ln_gamma.py`, 2026-10-08]

**Koretsky (2ª ed., Wiley, 2013)** [`teste_koretsky_formulas_e_exemplos.py`, 2026-10-08]:
- Tabelas 7.2 e 7.4 transcritas contra `MODELS_GE`: erro máximo ~1e-13.
- Tabela E8.9A (benzeno/ciclo-hexano a 10 °C, 12 pontos): P calculado e γ da Tabela E8.9B reproduzidos com diferença máxima de 2,5 Pa e 0,004. Barker dá A = 1406 J/mol (livro: 1401, 1399 ou 1424 conforme a função-objetivo).
- Exemplo 8.5 (etanol/água a 70 °C): aplicativo x₁ = 0,114 e P = 0,548 bar; livro 0,12 e 0,55 bar.
- Problema 7.70 (acetona/clorofórmio, UNIQUAC): P = 268,1 torr (+2,35 % sobre 261,9 medido) e y₁ = 0,153 (0,143 medido).
- Erro tipográfico do livro: no Exemplo 7.12 o sinal de a₂₁ sai positivo para reproduzir o resultado do próprio exemplo.
- Com q′, os Problemas 7.68 e 7.69 dão resultado misto; **q′ piora o ajuste aos dados NIST de etanol/água** (ΔP 4,0–5,0 % contra 1,3–3,5 % com q), por isso a opção é desligada por padrão.

**Psat e constantes críticas da `thermo` contra o Apêndice A do Koretsky** [`teste_psat_koretsky_apendice_a.py`]: concordância dentro da faixa, em geral abaixo de 1,5 % (9 de 11 compostos) e no máximo 3,1 %; Tc a 0,3 %, Pc a 2,6 %, ω a 0,011. Os maiores desvios são da equação de Antoine de 3 parâmetros do livro, não da `thermo`.

## 9. Bugs achados e corrigidos (evidência do método de validação)

1. **Van Laar** (`8c29dcb`): γ₁ e γ₂ trocados nos limites exatos de composição.
2. **Wilson:** nos limites x₁ = 0 e x₂ = 0 trocava γ₁↔γ₂ e usava o parâmetro errado.
3. **UNIFAC, parte residual:** índices dos parâmetros τ trocados na soma do denominador (afeta pares assimétricos).
4. **UNIFAC, parte combinatorial:** zerava o termo em vez do limite analítico.
5. **Tabela de interação UNIFAC:** **41 dos 66 pares estavam errados** (erro de transcrição); a tabela foi reescrita por completo a partir da `thermo.unifac.UFIP`.
6. **UNIQUAC via IPDB:** o adaptador passava o sinal invertido (o IPDB guarda bij = −A/R). Achado a partir de uma pergunta do autor ("parece invertido?"). Corrigido; o modelo reproduz o exemplo da `thermo` (γ = 1,977 e 1,140 em x₁ = 0,252).
7. **Regressão do Van Laar com desvio negativo:** terminava em solução espúria com `sucesso=True`; corrigido com chute inicial extra. O dado real de clorofórmio/MEK confirmou o bug.
8. **Eixo do gráfico de ln γ** com `label_spacing` = 0 quando o ln γ era quase constante.

Lição de processo: a auditoria de fórmulas (item 1 a 5) **não** cobria a ponte entre o banco e o modelo (item 6), que só apareceu pela pergunta do autor.

## 10. Funcionalidades da interface (estado em 2026-10-18)

Tabela editável de pontos P (kPa), x₁, y₁ com gráficos que se atualizam ao sair do campo; importação por CSV e por texto colado; 4 exemplos NIST (com limitações descritas); escolha de modelo, componentes e temperatura; sliders e valor digitável; botões "Buscar do Banco (IPDB)", "Calcular por Regressão (Barker)" e "Comparar" (marcadores vazados + ΔP/Δy + maior desvio); gráfico P-x-y e gráfico de ln γ (com ln γ experimental da tabela); avisos (instabilidade da fase líquida, temperatura acima da crítica, regressão suspeita, unidades); selo de origem com ⓘ; ajuda por tópicos (10 tópicos, "?" por card, "Sobre"); lupa dos gráficos (só no desktop); alternância celular/computador. Estética encerrada pelo autor em 2026-10-07.

## 11. Uso de IA no desenvolvimento (para a declaração exigida no trabalho)

- **Modelo de governança (2026-08-20):** o **autor é o diretor e gerente operacional** e decide rumo, escopo e prioridades; o **assistente (Claude Code) é o "operário"**: implementa, audita, testa e documenta. **Regra central: nenhuma decisão entra no projeto sem ordem de validação do autor.** Decisões só vão para a documentação depois de tomadas pelo autor. [CLAUDE.md; mapeamento 5.2]
- **Código herdado de outra IA:** o `gemini.py` inicial veio de outra IA sem supervisão. O autor decidiu **auditá-lo em vez de descartar ou usar às cegas** (mapeamento 5.1). Daí vieram os bugs da seção 9.
- **Protótipos de estudo** em React (`referencias/margules-*.jsx`) feitos com o Claude (chat) em julho/2026.
- **Barra de entendimento** fixada pelo orientador em 2026-09-01: entender o **básico** de cada parte e priorizar entregar funcionando; a redação do TCC vem depois, sobre o que já funciona.
- **Divisão do trabalho:** o registro cronológico "Decisões de engenharia do aluno na produção da aplicação" (no `CLAUDE.md`) separa o que foi decisão do autor do que foi execução do assistente. Para o texto do TCC, usar esse registro como fonte.
- **Texto de ajuda do aplicativo** (tópicos de "Modelos de Gᴱ", "Limitações" etc.) foi redigido pelo assistente e **ainda aguarda a leitura crítica do autor**.

## 12. Decisões do autor mais citáveis (datas do registro)

- Escrever as equações no código; `thermo` como fonte de dados e oráculo (julho/2026).
- Validar em toda a faixa de composição, com limites analíticos (2026-07-27).
- Reescrever a tabela UNIFAC inteira, não corrigir só os pares do teste (2026-07-27).
- Buscar parâmetros em banco em vez de copiar da literatura (2026-07-28/29).
- Não interpolar pontos experimentais: dado é ponto, modelo é linha (2026-08-19).
- Regressão a partir dos dados quando não houver outra fonte (2026-09-12); declarar a origem de cada parâmetro (selo) (2026-09-12).
- Barker direto; α₁₂ fixo; mínimo de pontos = parâmetros + 1 (2026-09-13).
- ΔP relativo e Δy absoluto, separados (2026-09-27).
- Dois modos de exibição em um código só, com botão (2026-10-01).
- Paleta dos gráficos: a cor identifica a fase (azul = líquido, laranja = vapor) e o estilo identifica a origem (marcador cheio = tabela, linha = modelo, marcador vazado = comparativo) (2026-10-03).
- Modo aula **sem co-op**: cada aluno com o seu aplicativo (2026-10-06).
- Remover o CSV sem fonte e recalibrar com dado NIST (2026-10-06).
- UNIQUAC com r/q do ChemSep quando existirem (2026-10-06).
- Retirar "Desfazer", "Gerar Gráfico" (automatizado) e protótipos antigos (2026-10-08).
- Opção "Usar q′" desligada por padrão (2026-10-08).

## 13. Publicação e desempenho

- **Formato web estático** (Flet publicado com Pyodide: Python no navegador). O motor roda com resultados **idênticos ao nativo** (testado em Pyodide 314.0.6, Python 3.14.2).
- **GitHub Pages**, publicado pelo autor em 2026-10-09. Tempos informados pelo autor: **~18 s** até a interface no PC (Wi-Fi) e **~40 s** no celular com dados móveis; recarga com F5 no PC ~15–18 s. O aplicativo em servidor Python local (`flet run`) recarrega em **~2 s**.
- Testado no celular em rede local: sem erro, sem queda da aba e sem aquecimento perceptível; **memória não foi medida**.
- **Não testado:** Mac do orientador.
- Cada pessoa usa o aplicativo no próprio navegador; nada é salvo entre visitas; precisa de internet na carga (CDNs).
- Hospedagem institucional (STI/UFC ou RNP) ficou em "Atualizações futuras".

## 14. Referências citadas no projeto e status de conferência

| Referência | Status |
|---|---|
| Koretsky, M. D. *Engineering and Chemical Thermodynamics*, 2ª ed., Wiley, 2013 (cap. 6, seção 6.3; cap. 7; Apêndice A; Tabelas 7.2, 7.4 e A.1; Exemplos 7.12, 8.5, 8.9–8.11; Problemas 7.68–7.70) | **Lido e conferido** em recortes de PDF (pp. 340–342, 422–496 e 639–640). Páginas citadas no projeto: Gibbs-Duhem (6.19, 7.42, 7.43), teste da área (7.50, p. 428), azeótropo (8.17–8.20), estatística DECHEMA (p. 437). O resto do livro **não foi lido**. |
| Cristino et al. (2013); Feng, Dong e Li (2011); Clara, Marigliano e Solimo (2006) | DOIs e dados conferidos nos arquivos do ThermoML. |
| Riccardi et al. (2022), *J. Comput. Chem.* 43, 879; NIST/TRC ThermoML Archive, doi:10.18434/mds2-2422 | Citado como fonte dos dados; **conferir a formatação** antes de usar. |
| Smith, Van Ness e Abbott (atribuição do método de Barker) | **Citado de memória**, seguindo o mapeamento (seção 2.8), sem edição nem páginas. **Conferir antes de usar.** |
| Fredenslund, Jones e Prausnitz (UNIFAC original) | Atribuição conforme as tabelas da `thermo` (`UFIP`); **conferir a referência original**. |
| Kooijman e Taylor (banco ChemSep, Artistic License 2.0); Caleb Bell (`thermo`, `chemicals`, MIT); Flet / Appveyor Systems Inc. (Apache 2.0) | Créditos conforme metadados dos pacotes; está no tópico "Sobre" do aplicativo. |
| Gmehling et al. (coletânea DECHEMA) | Mencionada pelo Koretsky como fonte da Tabela E8.9A; **não consultada diretamente**. |

## 15. Limitações conhecidas (pode entrar na discussão do TCC)

- Só modo **isotérmico**; o isobárico (T-x-y) está adiado para depois do piloto.
- **Vapor ideal** e Raoult modificada sem correção de Poynting; imprecisão perto da região crítica (há aviso quando T passa da crítica de um componente).
- Uma só fase líquida; há aviso de instabilidade, mas não há cálculo de equilíbrio líquido-líquido.
- **Sem teste de consistência termodinâmica** dos dados digitados (o teste da área foi usado só para escolher os dados NIST).
- Parâmetros do banco valem à temperatura dos dados; o aplicativo não extrapola com T.
- Unidade de P só em **kPa**; o aplicativo não valida unidade.
- Nomes de componentes em inglês ou CAS.
- UNIQUAC e UNIFAC dependem de o par constar nos dados do aplicativo (grupos UNIFAC ou ChemSep).
- A regressão não avisa resíduo alto com parâmetros dentro dos limites.
- Dados NIST usados **não são avaliados criticamente**; os de etanol/água têm faixa incompleta e T alta.
- Dioxano/metanol sem fonte experimental.
- Tempo de carga do formato estático (20–40 s) e dependência de internet.

## 16. Plano de execução do TCC (mapeamento, seção 6)

Fase 0 preparação (jul–ago/2026); Fase 1 núcleo funcional (ago–out/2026); Fase 2 validação e robustez (out–dez/2026); Fase 3 folga (dez/2026–fev/2027); Fase 4 escrita e fechamento (mar–mai/2027); Fase 5 reta final (jun/2027). Em 2026-10-18 o núcleo funcional está pronto e a Fase 2 começou (Koretsky e NIST). **Pendente da Fase 2:** exercícios de Smith, Van Ness e Abbott; mais exercícios do Koretsky com resposta publicada (os problemas do cap. 8 não foram lidos); transformar os scripts avulsos em suíte com runner.

## 17. Pendências do autor (não escrever como resolvidas)

1. Limiar de ΔP e Δy para um veredito "bom/ruim" (com o orientador).
2. Origem do dado de 1,4-dioxano/metanol (com o professor).
3. Leitura crítica do autor dos tópicos de ajuda "Modelos de Gᴱ" e "Limitações".
4. Teste no Mac do orientador.
5. Conferir as referências marcadas na seção 14.
6. Hospedagem institucional e automatização da publicação: adiadas.
