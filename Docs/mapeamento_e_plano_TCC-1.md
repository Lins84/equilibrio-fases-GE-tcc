# Ferramenta Computacional Interativa para o Ensino do Equilíbrio de Fases
## Mapeamento Holístico e Plano de Execução

**Autor:** Leonardo de Sousa Lins
**Orientador:** Dr. Filipe Xavier Feitosa
**Instituição:** UFC — Centro de Tecnologia — DEQ
**Documento gerado em:** Julho de 2026

---

## 1. Visão Geral do Projeto

### 1.1 Problema
Modelos de coeficiente de atividade (Margules, Van Laar, NRTL, Wilson, UNIFAC) têm complexidade matemática que dificulta a interpretação imediata de diagramas de equilíbrio de fases (T-x-y, P-x-y). Falta abstração ligada à intuição visual e ferramentas em tempo real para o ensino de Termodinâmica na graduação em Engenharia Química.

### 1.2 Solução
Aplicação em Python (Flet + thermo) que permite ao usuário ajustar parâmetros de modelos de atividade e visualizar, em tempo real, o efeito nos diagramas de equilíbrio.

### 1.3 Objetivos do projeto (três eixos)

**Eixo 1 — Didático-visual**
- Ver os diagramas mudando ao vivo conforme parâmetros são ajustados
- Prioriza fluidez e clareza visual sobre precisão de input manual
- Uso: aula expositiva, exploração livre

**Eixo 2 — Validação de exercícios**
- Reproduzir e conferir exercícios específicos de livros-texto (Koretsky; Smith, Van Ness & Abbott)
- Prioriza exatidão numérica comparável ao gabarito
- Uso: verificação de resultados, funciona como teste de regressão do próprio código

**Eixo 3 — Uso em pesquisa acadêmica**
- A ferramenta não se limita ao ensino: serve também como instrumento de teste/análise em contextos de pesquisa
- Eleva o projeto de "ferramenta de sala de aula" para "ferramenta com utilidade científica" — justificativa relevante para a banca
- Diferenciais em relação ao Eixo 2: precisão numérica rigorosa (não apenas "visualmente correto"), capacidade de importar/exportar dados tabulados, e flexibilidade para sistemas fora dos exemplos clássicos de livros-texto (ex: dados experimentais reais)
- Conecta diretamente com a importação via CSV (ver seção 2.2): pesquisa acadêmica tipicamente trabalha com dados tabelados/experimentais, não input manual ponto a ponto

### 1.4 Usuário final
**Não é o autor — é o orientador**, que pretende usar a ferramenta durante suas aulas de Termodinâmica na graduação. Isso implica:
- Prioridade em robustez e simplicidade de execução sobre elegância de deploy
- UI legível em projeção de sala de aula (fontes grandes, alto contraste, controles fáceis de manipular com mouse)
- Tolerância baixa a erros/exceptions quebrando a interface durante a aula
- Ambiente de uso: Mac do orientador (diferente do ambiente de desenvolvimento do autor, que é Android/Termux)
- Empacotamento final (.exe / app local / web) — **decisão adiada deliberadamente** para a fase de robustez, quando o núcleo funcional já estiver pronto

---

## 2. Arquitetura Técnica

### 2.1 Stack
- **Python** — linguagem base
- **Flet** — interface gráfica interativa (rodando em modo web/navegador, sem build nativo)
- **thermo** — biblioteca de cálculos termodinâmicos (fugacidade, coeficientes de atividade)

### 2.2 Estrutura de interface (baseada em rascunho do autor)
Layout: **tabela de dados à esquerda** + dois gráficos sincronizados à direita, todos alimentados pela **mesma função de cálculo**.

**Tabela de dados (entrada):**
- Colunas P, x, y (já implementada em `fletando.py`, ainda sem os outros elementos)
- Dois modos de entrada, ambos necessários:
  - **Manual**: linha por linha, com botão de adicionar/excluir (já implementado)
  - **Importação via CSV**: carregar um arquivo com colunas P, x, y de uma vez, populando a tabela automaticamente
- Modo manual serve melhor ao Eixo 1 (exploração rápida em aula); importação CSV serve melhor aos Eixos 2 e 3 (exercícios de livro já tabelados, dados experimentais de pesquisa)
- Decisão em aberto para a fase de implementação: se os dados importados via CSV permanecem editáveis na tabela após a importação, ou ficam fixos como referência

**Gráficos (saída):**

```
[modelo selecionado] + [slider A] + [slider B] + [dados da tabela: x]
              ↓
    calcular(modelo, A, B, x)
              ↓
    retorna: γ1(x), γ2(x), P(x) [ou T(x)], y(x)
              ↓
       ┌──────┴──────┐
  Gráfico 1 (ln γ vs x)   Gráfico 2 (P vs x,y — bolha/orvalho)
```

- **Dropdown de modelo:** Margules 1P, Margules 2P, NRTL, Wilson, UNIFAC
- **Sliders A e B:** genéricos na UI, mas seu significado muda por modelo (ex: NRTL usa τ/α, Van Laar usa A/B, Wilson usa Λ)
- **Regra de ouro:** tudo que for sensível à mudança de parâmetros deve atualizar em tempo real, nos dois gráficos, a partir do mesmo ciclo de cálculo

### 2.3 Decisões de arquitetura já alinhadas
- Função de cálculo genérica desde o início (`calcular(modelo, param_A, param_B, dados)`), mesmo com apenas NRTL implementado inicialmente — evita retrabalho ao generalizar para múltiplos modelos
- Cálculo **vetorizado** (numpy), evitando chamadas ponto a ponto ao `thermo` — crítico para performance no Termux
- Separação clara entre **camada de cálculo** e **camada de interface**, permitindo dois modos de uso (exploração livre vs. validação de exercício específico) sobre o mesmo motor
- Interatividade via `on_change_end` nos sliders (recalcula só ao soltar, não a cada pixel arrastado) — trade-off aceito entre fluidez de arraste e performance; alternativa híbrida (valor numérico ao vivo + gráfico só no release) fica como plano B se necessário
- Repositório git desde o início do desenvolvimento, mesmo local, para permitir migração suave entre ambientes

### 2.4 Validação de referência
Sistema **1,4-Dioxano / Metanol a 308,5 K** já testado contra dados de literatura (desvio significativo da idealidade — bom caso de teste para modelos de atividade). Serve de base para expandir a suíte de testes com exercícios de Koretsky e Smith/Van Ness/Abbott.

**Validações já realizadas** (ver log completo na seção 7 e prestação de contas na seção 5.1):
- **Van Laar**: modelo já implementado no `gemini.py` (junto com Margules 1P) desde antes da integração dos ambientes de desenvolvimento. Auditado pelo Claude Code contra dados reais de `thermo` para o sistema Dioxano/Metanol — bug de troca γ1↔γ2 identificado e corrigido; consistência confirmada nas bordas (P calculado batendo com os Psat puros)
- **Margules 1P**: implementado no `gemini.py` junto com o Van Laar, mas **ainda não submetido a auditoria/validação numérica específica** — pendente

**Pendente de implementação (não confundir com validado):**
- **Margules 2P (three-suffix)**: **ainda não implementado** no `gemini.py`. Existe apenas um **caso de teste de referência** (`teste_margules_2p_MEK_tolueno.py`), construído a partir de dados de uma planilha Excel (pacote XSEOS, sistema Metil-etil-cetona/Tolueno a 323,15 K), com a fórmula de referência já validada internamente (diferença inferior a 0,001 em todos os pontos) — esse teste aguarda a implementação real do modelo no `gemini.py` para servir de comparação

### 2.5 Protótipos de estudo e referências visuais

Durante o período de estudo aprofundado dos modelos de coeficiente de atividade (julho 2026), foram produzidos dois protótipos interativos em React/JavaScript — `margules-1-parametro.jsx` e `margules-2-parametros.jsx` — com o auxílio do Claude (chat), como ferramenta de apoio ao estudo e ilustração do tipo de interatividade pretendida para o app final.

**Características desses protótipos:**
- Slider para o(s) parâmetro(s) do modelo, com atualização em tempo real dos gráficos
- Gráfico de gᴱ/RT vs x1 e gráfico de γ (ou ln γ) vs x1, com alternância entre modo linear e logarítmico
- Guia de leitura pedagógico embutido, destacando pontos-chave a observar (simetria, comportamento nas bordas, diluição infinita)
- **Natureza explicitamente didática**: são ilustrações de estudo em JavaScript/React, não parte do código de produção do TCC — o app final continua em Python (Flet + thermo), com arquitetura própria

Esses protótipos, junto com uma imagem de referência de uma planilha Excel (pacote XSEOS, canal "Youtermo" no YouTube) mostrando o padrão de tabela + gráficos esperado pela interface, foram organizados no repositório na pasta `referencias/`, servindo de referência visual e de validação matemática para o Claude Code durante o desenvolvimento do `gemini.py`.

### 2.6 Comunicação com o orientador

Como parte do acompanhamento do desenvolvimento, os dois protótipos interativos (seção 2.5) foram compartilhados por e-mail com o orientador (Dr. Filipe Xavier Feitosa) durante o período de estudo, com as seguintes informações relevantes registradas na mensagem:
- Contexto: revisão de fundamentos dos modelos de Gᴱ durante as férias, antes de iniciar o desenvolvimento do app
- Transparência sobre o uso do Claude na geração das ilustrações interativas
- Ressalva explícita de que são ilustrações didáticas em JavaScript, distintas do app do TCC (que permanece em Python/thermo, com estrutura própria)
- Objetivo declarado: comunicar ao orientador o tipo de interação/experiência que se pretende alcançar no produto final

Esse e-mail serve como registro documentado e datado de acompanhamento do orientador ao longo do processo — relevante tanto para a prestação de contas de uso de IA (seção 5) quanto como evidência de comunicação contínua com a orientação.

---

## 3. Estado Atual do Código

Arquivo `fletando.py` — implementa apenas a primeira etapa:
- Tabela de input (P, x, y) com botões de adicionar/remover linha
- Sem cálculo, sem gráfico, sem sliders, sem seleção de modelo

---

## 4. Ambiente e Fluxo de Trabalho

### 4.1 Ferramentas
- **Edição atual:** Termux + Acode (edição manual, Termux só executava)
- **Planejado:** Claude Code assumindo edição + execução + auditoria de erros dentro do Termux, enquanto o código for simples
- **Migração planejada:** para desktop quando entrar a parte pesada (múltiplos modelos, suíte de testes, performance)
- **Status da assinatura:** ainda em avaliação (Claude Pro, ~mês que vem)

### 4.2 Por que Termux funciona para este projeto
- Flet é usado em modo web (`flet run --web`), sem necessidade de build nativo (que exigiria maturin e companhia — o gargalo real do Flet no Android)
- `thermo` nunca foi um problema de compilação nesse ambiente
- Papel do Claude Code é limitado a Bash + Read/Edit — não depende de recursos "pesados" (Remote Control, sandboxing) que são não-oficiais/instáveis no Termux

### 4.3 Diferença Windows vs. Termux para Claude Code
Windows tem suporte oficial da Anthropic (nativo ou via WSL). Termux não tem suporte oficial — qualquer uso ali é workaround da comunidade. Para o escopo deste projeto (bash simples + edição de arquivo), o risco é baixo, mas vale ter um plano B (ex: PC/notebook) caso apareçam bugs sem solução no ambiente Termux.

---

## 5. Prestação de Contas — Uso de IA no Desenvolvimento

Considerando que a banca incluirá um professor especialista em Python e uso de IA, o desenvolvimento seguirá estas práticas, documentadas continuamente (não reconstruídas ao final):

1. **Transparência total** sobre o uso do Claude Code como ferramenta de desenvolvimento no TCC, incluindo escopo do que foi delegado e o que foi decisão do autor
2. **Explicação exigida antes de aceitar código gerado** — nunca aprovar uma mudança sem entender o porquê da abordagem escolhida
3. **Registro de decisões de arquitetura**, não só do código final (por que Flet, por que essa separação cálculo/interface, por que vetorização, por que `on_change_end`)
4. **Validação numérica documentada** contra literatura (Koretsky, Smith/Van Ness) como evidência de correção, não apenas "o código rodou sem erro"
5. Pontos técnicos antecipados que a banca pode questionar:
   - Escolha de Flet vs. alternativas (Streamlit, Dash, Jupyter widgets)
   - Garantia de corretude dos cálculos do `thermo`
   - Decisões de performance
   - Estrutura/organização do projeto

### 5.1 Caso registrado: código pré-existente gerado por outra IA (`gemini.py`)

Durante a integração dos ambientes de desenvolvimento (julho 2026), foi descoberto no repositório um arquivo `gemini.py` — um módulo de cálculo de equilíbrio líquido-vapor (modelos Margules 1P e Van Laar, função `calculate_vle_isothermal`), produzido em um teste anterior com o Google Gemini Pro, **quase sem supervisão do autor na época da criação**.

**Critério de decisão adotado:** a origem do código (gerado por outra IA, sem supervisão prévia) não é, por si só, motivo para descarte — mas também não é motivo para uso direto sem processo. O código passou pelo seguinte tratamento antes de ser considerado parte legítima do projeto:

1. **Auditoria técnica solicitada ao Claude Code**, com foco explícito em corretude termodinâmica (não apenas qualidade de código): verificação das equações de Margules e Van Laar contra a literatura, verificação da Lei de Raoult modificada, e teste com dados reais via `thermo` para o sistema 1,4-Dioxano/Metanol a 308,5 K
2. **Um bug real foi encontrado e corrigido** durante essa auditoria: troca indevida entre os coeficientes de atividade γ1 e γ2 na implementação do modelo Van Laar — confirmado pela consistência das bordas do teste (P calculado batendo exatamente com os Psat puros de cada componente)
3. **Ressalva registrada pelo próprio processo de auditoria:** o teste validou a *implementação* (consistência matemática interna), não a *acurácia* dos parâmetros A12/A21 usados (que foram valores de exemplo, não os parâmetros reais do sistema) — pendente de busca de parâmetros reais em literatura para validação completa

**Princípio adotado para uso futuro de código de origem similar:** um código gerado por IA sem supervisão prévia pode ser incorporado ao projeto desde que (a) seja submetido a auditoria técnica documentada, (b) o autor seja capaz de explicar seu funcionamento após o processo, e (c) a origem e o processo de validação sejam registrados nesta prestação de contas — transformando uma origem potencialmente frágil em prática de revisão de código documentada, e não em ocultação.

**Pendência:** entendimento linha a linha do `gemini.py` pelo autor (com apoio do Claude Code explicando o código), de forma que o autor seja capaz de defender qualquer trecho perante a banca sem depender de memória de terceiros.

*(Este documento serve como registro inicial dessa prestação de contas — recomenda-se atualizá-lo conforme decisões técnicas forem tomadas ao longo do desenvolvimento.)*

---

## 6. Plano de Execução Temporal

**Prazo total:** 2026.2 (livre de apresentação) até defesa em junho de 2027.1

**Princípio-guia:** nenhum código novo depois de dezembro de 2026. Tudo após essa data é validação, escrita e polimento — não desenvolvimento sob pressão.

| Fase | Período | Foco |
|---|---|---|
| 0. Preparação | Jul–Ago 2026 | Decisões, setup, fundação |
| 1. Núcleo funcional | Ago–Out 2026 | Etapas 1→4 (tabela → gráfico → sliders → modelos) |
| 2. Validação e robustez | Out–Dez 2026 | Testes contra livros, empacotamento pro orientador |
| 3. Folga estratégica | Dez 2026–Fev 2027 | Buffer, revisão com orientador, início da escrita |
| 4. Escrita e fechamento | Mar–Mai 2027 | TCC escrito, seção de uso de IA, ajustes finos |
| 5. Reta final | Jun 2027 | Ensaios, ajustes críticos, defesa |

### Fase 0 — Preparação (Jul–Ago 2026)
- Decidir sobre assinatura do Claude Code
- Criar repositório git (local, com possibilidade de remoto futuro)
- Estruturar pastas do projeto (`calculos/`, `interface/`, `testes/`)
- Iniciar o documento de prestação de contas como arquivo vivo

### Fase 1 — Núcleo funcional (Ago–Out 2026)
- Etapa 2: simulação gráfica com os dados da tabela
- Etapa 3: sliders com `on_change_end`
- Etapa 4: seleção de modelo (generalização NRTL → Van Laar/Wilson/Margules/UNIFAC)
- **Meta:** aplicação funcionalmente completa (mesmo que visualmente crua) até outubro

### Fase 2 — Validação e robustez (Out–Dez 2026)
- Suíte de testes contra exercícios do Koretsky e Smith/Van Ness
- Tratamento de erros de input, pensando no uso em sala de aula
- Decisão de empacotamento final (.exe vs. script local vs. web hospedado)
- **Meta:** versão estável o suficiente para "segurar uma aula" até dezembro

### Fase 3 — Folga estratégica (Dez 2026–Fev 2027)
- Buffer proposital (coincide com recesso acadêmico)
- Revisão com o orientador testando a ferramenta na prática
- Ajustes finos baseados nesse feedback
- Início da escrita de seções independentes de código fechado (revisão bibliográfica, fundamentação teórica)

### Fase 4 — Escrita e fechamento (Mar–Mai 2027)
- Redação completa do TCC (metodologia, resultados, seção de prestação de contas sobre uso de IA)
- Últimos ajustes de UI/UX baseados em uso real
- Entrega da prévia (confirmar prazo oficial junto à coordenação)

### Fase 5 — Reta final (Jun 2027)
- Ensaios de apresentação e slides
- Apenas ajustes críticos — sem novas features
- Defesa pública

---

## 7. Pontos em Aberto (decidir ao longo do caminho)
- Assinatura do Claude Code (Pro) — avaliação em andamento
- Formato de empacotamento final: executável nativo vs. web hospedado vs. script local — decisão adiada para a Fase 2
- Hospedagem gratuita (se optado por web): opções identificadas incluem Render e PythonAnywhere, com ressalva de cold-start em planos gratuitos — inadequado para demonstração ao vivo sem mitigação
- Confirmação de prazos oficiais da coordenação (prévia, depósito, defesa) para 2027.1, já que os prazos anteriores encontrados nos slides eram de outro semestre

### 7.1 Roteiro de testes de ambiente para o Claude Code
A ser executado logo após a ativação da assinatura Pro, aproveitando o período de férias da faculdade (julho 2026) como janela livre para essa validação prática, antes do início da Fase 1 (núcleo funcional).

**Termux (nativo, com glibc-runner ou proot-Ubuntu)**
- Instalação sem erro?
- `flet run --web` funciona em conjunto com o Claude Code rodando?
- Sessão de trabalho típica (editar + rodar + corrigir erro) — fluida ou trava?
- Sem sandbox de SO (não suportado oficialmente) — só a camada de permissões do próprio Claude Code protege

**Replit** (autor já é usuário intermediário, com fluxo PC-celular já estabelecido)
- Instalação no shell — funciona de primeira?
- Comportamento em sessão longa com o app em foreground vs. background — limitação já conhecida (Replit interrompe processos em segundo plano no app Android), a confirmar como se manifesta especificamente com o Claude Code
- Consumo dos ~1.200 minutos/mês do tier gratuito numa sessão de trabalho real
- Free tier exige projeto público — compatível com o plano de repositório open source

**Desktop (Windows, se houver acesso)**
- Baseline "oficial" — suporte nativo pleno, sandbox de SO disponível (via WSL2)
- Referência de comparação para medir a fricção dos demais ambientes

**Critério de decisão:** não necessariamente qual ambiente é tecnicamente superior (desktop tende a vencer nisso por padrão), mas qual equilibra melhor a praticidade do dia a dia do autor com a fricção tolerável — em linha com a divisão de fases já definida (ambiente leve/móvel na Fase 1, migração para desktop na Fase 2, quando o trabalho fica mais intenso).

### 7.2 Log de testes de instalação (julho 2026)

Testes realizados sem assinatura ativa — validam apenas se a *instalação* do Claude Code completa sem erro em cada ambiente (login/uso real ainda não testado).

**✅ Replit — sucesso direto**
- Ambiente já vinha com Node.js v20.20.0 e npm 10.8.2 prontos
- `npm install -g @anthropic-ai/claude-code` completou sem nenhum erro ou aviso
- `claude --version` retornou a versão instalada normalmente
- Nenhum workaround necessário — funcionou de primeira, como esperado por ser um container Linux genuíno

**❌ Termux nativo (puro, sem camada extra) — falhou**
- Node.js v26.4.0 e npm 11.18.0 já disponíveis
- `npm install -g @anthropic-ai/claude-code` completou, mas com aviso `allow-scripts` bloqueando o script de pós-instalação (`postinstall: node install.cjs`)
- Reinstalação com `--allow-scripts=@anthropic-ai/claude-code` resolveu o aviso, mas `claude --version` retornou erro: binário nativo não instalado
- Rodar o `install.cjs` manualmente revelou a causa raiz: **"Native binaries for linux-arm64-android are not available on this release channel"** — a Anthropic distribui binários para `linux-arm64` (glibc) e `linux-arm64-musl`, mas não para a variante Android/Bionic que o Termux usa nativamente
- **Diagnóstico:** barreira de distribuição de binários, não erro de configuração — confirma a limitação teórica discutida antes dos testes

**❌ Termux + glibc-runner — tentativa abandonada**
- Instalação do `glibc-repo` e `glibc-runner` via `pkg` completou sem erro
- `grun node [...]/install.cjs` retornou erro de sintaxe ("incorrect flag or binary to run")
- Consulta ao `grun --help` revelou que a ferramenta espera um binário glibc já compilado como alvo, não um comando a interpretar diretamente
- Tentativa de usar `grun --shell` para abrir um shell glibc não produziu ambiente claramente distinto (comando `node --version` dentro do "shell" retornou a mesma versão do Node nativo do Termux, sugerindo que o shell glibc não estava de fato ativo ou configurado)
- **Diagnóstico:** ferramenta pouco documentada para este caso de uso específico; abandonada por incerteza, não por confirmação definitiva de incompatibilidade
- Pacotes desinstalados posteriormente (`pkg uninstall glibc-runner glibc-repo -y --allow-remove-essential`, necessário por serem marcados como pacotes essenciais) antes de prosseguir para a alternativa seguinte

**✅ Termux + proot-Ubuntu — sucesso**
- Instalação do `proot-distro` via `pkg` completou com um erro cosmético não-bloqueante (`FileNotFoundError: python3.14` durante etapa de otimização de bytecode pós-instalação) — não impediu o funcionamento da ferramenta
- `proot-distro install ubuntu` — download do rootfs completo; travou momentaneamente na etapa "Fetching manifest" (comunicação com o registro de containers), resolvido tentando novamente sem trocar de rede
- `proot-distro login ubuntu` — login no ambiente Ubuntu emulado, sucesso
- Node.js instalado dentro do Ubuntu via `apt install -y nodejs npm` (v22.22.1 / npm 9.2.0) — versões diferentes das do Termux nativo, mas irrelevante pois é ambiente isolado
- `npm install -g @anthropic-ai/claude-code` completou sem erros nem avisos de `allow-scripts`
- **`claude --version` retornou `2.1.215 (Claude Code)` — instalação 100% funcional**
- **Diagnóstico:** o ambiente Ubuntu emulado se identifica como `linux-arm64` (glibc) genuíno em todos os níveis do sistema, permitindo que o script de detecção de plataforma do Claude Code baixe o binário nativo correto sem obstáculo

**Resumo do log:**

| Ambiente | Resultado | Causa |
|---|---|---|
| Replit | ✅ Sucesso direto | Container Linux genuíno, sem necessidade de workaround |
| Termux nativo puro | ❌ Falhou | Sem binário distribuído para `linux-arm64-android` |
| Termux + glibc-runner | ❌ Abandonado | Ferramenta pouco documentada; não foi possível configurar um ambiente glibc funcional para este caso |
| Termux + proot-Ubuntu | ✅ Sucesso | Ambiente Linux completo e genuíno, sem as limitações de tradução parcial do glibc-runner |

**Pendente de decisão futura:** com dois ambientes agora comprovadamente funcionais para a instalação (Replit e Termux+proot-Ubuntu), falta testar a experiência de uso real (login, edição, execução, auditoria de erros) em ambos assim que a assinatura Pro for ativada, antes de escolher qual adotar como ambiente principal de desenvolvimento móvel.

### 7.3 Log de autenticação e configuração (assinatura Pro ativada)

Com a assinatura Claude Pro ativa ("Habemus Pro"), o roteiro de testes de uso real foi concluído com sucesso nos dois ambientes validados na instalação.

**✅ Replit — autenticação e configuração completas**
- Tela inicial de escolha de tema (Dark mode) confirmada sem problemas
- Login selecionado via método 1 (conta com assinatura Pro/Max/Team/Enterprise)
- **Obstáculo encontrado:** o terminal do Replit não abre o navegador automaticamente (ambiente cloud sem acesso à tela do dispositivo) — a URL de autenticação OAuth precisou ser copiada manualmente
- **Obstáculo secundário:** a cópia manual do texto quebrado em múltiplas linhas no terminal mobile inseriu espaços indevidos no meio da URL (ex: "client_id" virou "client id"), corrompendo o link e gerando erro "Parâmetro client_id ausente" no navegador
- **Resolução:** uso do atalho `c` (copiar) oferecido pelo próprio prompt do Claude Code, que copia a URL corretamente para a área de transferência sem o problema de concatenação manual; girar o celular para modo paisagem também ajudou a visualizar a URL com menos quebras de linha
- Login concluído após colar a URL corrigida no navegador (Samsung Internet) e colar o código de autorização retornado de volta no terminal
- Configuração de idioma aplicada via `~/.claude/settings.json` com `{"language": "portuguese"}` — confirmada com resposta em português na primeira conversa de teste

**✅ Termux + proot-Ubuntu — autenticação e configuração completas**
- Mesmo fluxo do Replit: login dentro do ambiente Ubuntu emulado (`proot-distro login ubuntu` → `claude`)
- Tela de tema, aviso de segurança e escolha de método de login (opção 1) idênticas ao Replit
- Login concluído sem repetição do obstáculo de corrupção de URL (não relatado como problema desta vez)
- Configuração de idioma aplicada com o mesmo comando/arquivo `~/.claude/settings.json`, confirmada com sucesso

**Resumo atualizado da tabela de ambientes:**

| Ambiente | Instalação | Login/Autenticação | Config. idioma PT-BR |
|---|---|---|---|
| Replit | ✅ | ✅ (com obstáculo de URL resolvido) | ✅ |
| Termux + proot-Ubuntu | ✅ | ✅ | ✅ |
| Termux nativo puro | ❌ | — | — |
| Termux + glibc-runner | ❌ (abandonado) | — | — |

**Nota para prestação de contas (seção 5):** o obstáculo de cópia de URL no Replit é um bom exemplo de troubleshooting documentável — ilustra domínio técnico do autor sobre peculiaridades de ambientes não convencionais (terminal mobile, quebra de linha, atalhos de CLI), reforçando a narrativa de uso dirigido e compreendido da ferramenta, não apenas seguir passos cegamente.

**Próximo passo em aberto:** testar o Claude Code de fato trabalhando sobre o código do projeto (`fletando.py`) — leitura, edição e execução — em um dos dois ambientes validados, como primeiro uso prático real.
