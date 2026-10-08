import csv
import dataclasses
import io
import math
import re
import textwrap
from pathlib import Path

import flet as ft
import flet_charts as fch

from calculos.gemini import (
    MODELOS_COM_BANCO_IPDB,
    MODELS_GE,
    REGRESSAO_MODELOS,
    buscar_parametros_banco,
    calculate_vle_isothermal,
    detectar_instabilidade_liquida,
    ln_gamma_experimental,
    montar_parametros_automaticos,
    regress_params_barker,
    uniquac_fonte_rq,
)

# Selo de origem do parâmetro (seção 2.8 do mapeamento): cor de fundo, cor
# do texto e rótulo por tipo de origem. "preditivo" cobre o UNIFAC (sem
# parâmetro de interação ajustável por par — grupos apenas).
ORIGENS_SELO = {
    "fornecido": (ft.Colors.BLUE_GREY_100, ft.Colors.BLUE_GREY_900, "Fornecido"),
    "banco": (ft.Colors.GREEN_100, ft.Colors.GREEN_900, "Banco de dados"),
    "calculado": (ft.Colors.ORANGE_100, "#7A3300", "Calculado"),
    "calculado_poucos_pontos": (ft.Colors.RED_100, ft.Colors.RED_900, "Calculado (poucos pontos)"),
    "preditivo": (ft.Colors.PURPLE_100, ft.Colors.PURPLE_900, "Preditivo"),
    # UNIQUAC com a₁₂/a₂₁ do banco mas r/q pelos grupos UNIFAC (o ChemSep não
    # tem r/q para o par): variante de menor confiança, mesmo padrão e mesmas
    # cores do "Calculado". 2026-10-06.
    "banco_rq_unifac": (ft.Colors.ORANGE_100, "#7A3300", "Banco, r/q via UNIFAC"),
}

# Sliders por modelo — nome do parâmetro (chave esperada por MODELS_GE em
# calculos/gemini.py), rótulo exibido, faixa e valor inicial. Só cobre os
# modelos cujos parâmetros são números de interação livres, fornecidos
# manualmente. UNIQUAC e UNIFAC não entram aqui — seus parâmetros são
# resolvidos automaticamente a partir dos componentes escolhidos, via
# montar_parametros_automaticos (grupos UNIFAC clássicos no UNIFAC; r/q do
# ChemSep e banco IPDB no UNIQUAC), sem slider manual.
# Faixa do slider é só recorte de exploração, não limite físico. Van Laar
# (A₁₂, A₂₁) e NRTL (τ₁₂, τ₂₁) vão a ±3 (2026-10-07): ajustados ao dado do
# NIST (Cristino 2013) saem A₁₂ = 2,06 (150 °C) e τ₂₁ = 2,49, fora de ±2.
# Margules 1P e 2P também vão a ±3 (2026-10-07, pedido do autor): o exemplo
# metanol/dimetilbuteno a 70 °C ajusta A = 2,25 (1P) e A₁₂ = 2,26, A₂₁ = 2,25 (2P).
PARAM_SLIDERS = {
    "Margules (1-P)": [
        {"chave": "A", "rotulo": "A", "min": -3.0, "max": 3.0, "inicial": 0.5},
    ],
    "Margules (2-P)": [
        {"chave": "A12", "rotulo": "A₁₂", "min": -3.0, "max": 3.0, "inicial": 0.6},
        {"chave": "A21", "rotulo": "A₂₁", "min": -3.0, "max": 3.0, "inicial": 0.3},
    ],
    "Van Laar": [
        {"chave": "A12", "rotulo": "A₁₂", "min": -3.0, "max": 3.0, "inicial": 0.6},
        {"chave": "A21", "rotulo": "A₂₁", "min": -3.0, "max": 3.0, "inicial": 0.4},
    ],
    "Wilson": [
        {"chave": "L12", "rotulo": "Λ₁₂", "min": 0.01, "max": 3.0, "inicial": 0.8},
        {"chave": "L21", "rotulo": "Λ₂₁", "min": 0.01, "max": 3.0, "inicial": 0.6},
    ],
    "NRTL": [
        {"chave": "tau12", "rotulo": "τ₁₂", "min": -3.0, "max": 3.0, "inicial": 0.3},
        {"chave": "tau21", "rotulo": "τ₂₁", "min": -3.0, "max": 3.0, "inicial": 0.3},
        {"chave": "alpha12", "rotulo": "α₁₂", "min": 0.2, "max": 0.47, "inicial": 0.3},
    ],
}


# Paleta dos gráficos (item 4 da lista de estética, 2026-10-03, opção A do
# autor): a COR identifica a fase, o ESTILO identifica a origem do dado —
# marcador cheio = tabela (experimental), linha contínua = modelo, marcador
# vazado = modelo calculado nos x1 da tabela ("Comparar", só no P-x-y desde
# 2026-10-08). Azul/laranja é o
# par que melhor se distingue em daltonismo, e o vermelho fica livre para o
# que ele já significa no app (erro, exclusão). No gráfico de ln γ a
# distinção é por componente (outra grandeza), com par de cores próprio.
COR_LIQUIDO = ft.Colors.BLUE_700
COR_VAPOR = ft.Colors.ORANGE_900
COR_GAMMA1 = ft.Colors.GREEN_700
COR_GAMMA2 = ft.Colors.PURPLE_600


def limites_redondos(vmin: float, vmax: float, alvo: int = 7) -> tuple[float, float, float]:
    """Limites e passo "redondos" para um eixo, a partir do intervalo dos
    dados: devolve (inicio, fim, passo) com o passo em 1, 2, 2.5 ou 5 vezes
    uma potência de 10, e inicio/fim múltiplos do passo, com cerca de `alvo`
    intervalos. Sem isso o eixo ia de, por ex., 27.1 a 76.1 e o gráfico
    desenhava esses dois extremos por cima dos marcadores regulares (30, 70):
    "6.4" colado no "10", "-0.05" quebrando sobre o "0.00" (item 8 da lista
    de estética, 2026-10-03). Com os limites sobre múltiplos do passo, o
    rótulo dos extremos coincide com um marcador regular e deixa de colidir."""
    # Intervalo praticamente constante (ex.: ln γ com A ≈ 1e-16, o "zero" do
    # slider, que sai com ruído de ponto flutuante em vez de 0 exato): o passo
    # calculado cairia abaixo de 5e-11 e `round(passo, 10)` o transformava em
    # 0 — o Flet então estourava "label_spacing cannot be 0" (relatado pelo
    # autor ao mexer no slider do Margules 1P, 2026-10-03). Tratado como
    # constante, do mesmo jeito que `gerar_grafico` já trata o caso exato
    # (vmin == vmax): abre ±1 em volta.
    escala = max(1.0, abs(vmin), abs(vmax))
    if vmax - vmin < 1e-6 * escala:
        vmin, vmax = vmin - 1, vmax + 1
    amplitude = vmax - vmin
    bruto = amplitude / alvo
    potencia = 10 ** math.floor(math.log10(bruto))
    passo = next(m * potencia for m in (1, 2, 2.5, 5, 10) if bruto <= m * potencia)
    inicio = math.floor(vmin / passo) * passo
    fim = math.ceil(vmax / passo) * passo
    return round(inicio, 10), round(fim, 10), round(passo, 10)


def margem_extremos(inicio: float, fim: float, passo: float) -> tuple[float, float]:
    """Limites de eixo ligeiramente abertos (0,2% do passo, invisível no
    gráfico) para que os marcadores exatos do primeiro e do último rótulo
    caiam DENTRO do intervalo, mesmo com o ruído de ponto flutuante de
    `inicio + k * passo` (ver `eixo_vertical`)."""
    folga = passo * 0.002
    return inicio - folga, fim + folga


def casas_do_passo(passo: float) -> int:
    """Casas decimais necessárias para escrever o passo do eixo sem perdê-lo
    (0,1 → 1; 0,25 → 2; 10 → 0)."""
    for casas in range(7):
        if abs(round(passo, casas) - passo) < 1e-9:
            return casas
    return 6


def rotulos_eixo(min_y: float, max_y: float, passo: float) -> list[fch.ChartAxisLabel]:
    """Rótulos explícitos do eixo vertical, nos múltiplos exatos do passo
    dentro de [min_y, max_y] (os limites já trazem a folga de
    `margem_extremos`, que não muda quais múltiplos entram).

    Por que explícitos (2026-10-06): o Flet gera os marcadores somando o passo
    a cada volta, e o ruído de ponto flutuante faz o zero sair como -2e-16 —
    escrito como "-0.00" no ln γ quando o eixo passa por zero vindo de
    valores negativos. Calculando cada valor como `k * passo` e escrevendo o
    zero como "0", o rótulo fica certo qualquer que seja o ruído."""
    casas = casas_do_passo(passo)
    k_ini = math.ceil(min_y / passo - 1e-9)
    k_fim = math.floor(max_y / passo + 1e-9)
    rotulos = []
    for k in range(k_ini, k_fim + 1):
        valor = round(k * passo, 10)
        texto = "0" if k == 0 else f"{valor:.{casas}f}"
        rotulos.append(fch.ChartAxisLabel(value=valor, label=ft.Text(texto, size=14)))
    return rotulos


def eixo_vertical(
    titulo: str,
    passo: float,
    largura_rotulo: int = 40,
    min_y: float | None = None,
    max_y: float | None = None,
) -> fch.ChartAxis:
    """Eixo vertical dos gráficos, com o passo fixo vindo de
    `limites_redondos`. Criado NOVO a cada `gerar_grafico` em vez de mutar o
    `label_spacing` do eixo existente — este app não muta propriedade de
    controle já criado.

    `min_y`/`max_y` (os limites do gráfico): quando informados, os rótulos
    são escritos por `rotulos_eixo` (ver o motivo lá); sem eles, o Flet gera
    os rótulos automáticos.

    `show_min`/`show_max` desligados: os rótulos dos extremos saem da
    própria escala regular (os limites de `limites_redondos` são múltiplos do
    passo — e `margem_extremos` abre uma folga mínima para o marcador do
    extremo não ser descartado por ruído de ponto flutuante). Com os dois
    ligados o extremo era desenhado duas vezes, uma por cima da outra: o
    último marcador do ln γ sai como 0.6000000000000001, diferente do
    máximo 0.6, e o "0.60" do topo aparecia em negrito.
    `largura_rotulo`: o ln γ tem rótulos negativos de 5 caracteres ("-0.10"),
    que quebravam em duas linhas ("-0.1" / "0") na coluna padrão de 40px."""
    rotulos = (
        rotulos_eixo(min_y, max_y, passo)
        if min_y is not None and max_y is not None
        else []
    )
    return fch.ChartAxis(
        label_size=largura_rotulo,
        label_spacing=passo,
        labels=rotulos,
        show_min=False,
        show_max=False,
        title=ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD),
        title_size=22,
    )


def marcador_vazado(forma: str, cor) -> fch.ChartPointShape:
    """Marcador só com contorno (sem preenchimento) — o calculado nos pontos
    da tabela, para ser lido contra o marcador cheio do dado experimental.
    `forma`: "quadrado" (líquido) ou "circulo" (vapor e ln γ), as mesmas
    formas dos marcadores cheios."""
    if forma == "quadrado":
        return fch.ChartSquarePoint(
            size=8, color=ft.Colors.TRANSPARENT, stroke_color=cor, stroke_width=2
        )
    return fch.ChartCirclePoint(
        radius=4.5, color=ft.Colors.TRANSPARENT, stroke_color=cor, stroke_width=2
    )


def formatar_parametro(valor: float) -> str:
    """Texto do campo de valor de um parâmetro (4 algarismos significativos,
    sem rótulo — o rótulo fica no próprio campo)."""
    return f"{valor:.4g}"


def parse_ponto(p_str: str, x_str: str, y_str: str) -> tuple[float, float, float]:
    """Converte as 3 strings de uma linha da tabela em (P, x1, y1) float.
    Levanta ValueError se algum campo estiver vazio ou não for numérico."""
    return float(p_str), float(x_str), float(y_str)


def pontos_para_series(
    pontos: list[tuple[float, float, float]],
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """A partir de pontos (P, x1, y1) já validados, monta as duas séries do
    diagrama P-x-y (sem nenhum cálculo de modelo — só os dados brutos da
    tabela): pares (x1, P) para a fase líquida e (y1, P) para a vapor,
    cada série ordenada pela composição."""
    liquido = sorted(((x1, P) for P, x1, y1 in pontos), key=lambda par: par[0])
    vapor = sorted(((y1, P) for P, x1, y1 in pontos), key=lambda par: par[0])
    return liquido, vapor


def formatar_valor(valor: float, algarismos: int = 4) -> str:
    """Formata um número para o tooltip dos gráficos com `algarismos`
    significativos (4 por padrão), sem notação científica. O tooltip
    padrão do Flet mostra o float inteiro (ex.: 45.234871620938), com
    algarismos que não significam nada num valor calculado/digitado.
    Valores praticamente nulos (ruído de ponto flutuante, ex.: ln γ de
    1e-17 no limite de componente puro) saem como "0"."""
    if not math.isfinite(valor):
        return str(valor)
    if abs(valor) < 1e-9:
        return "0"
    casas =algarismos - 1 - math.floor(math.log10(abs(valor)))
    return f"{round(valor, casas):.{max(casas, 0)}f}"


# Fundo do balão do tooltip dos gráficos (ver `ponto_grafico`): o azul claro
# do cabeçalho da tabela, semitransparente (pedido do autor, 2026-10-03) para
# o gráfico aparecer por trás do balão. A moldura `BLUE_200` continua opaca e
# delimita o balão.
OPACIDADE_TOOLTIP = 0.70
TOOLTIP_FUNDO = ft.Colors.with_opacity(OPACIDADE_TOOLTIP, ft.Colors.BLUE_50)


def novo_tooltip() -> fch.LineChartTooltip:
    """Balão do tooltip dos gráficos. Uma função (e não um objeto único)
    porque o gráfico do card e o do diálogo "Ampliar" precisam cada um do
    seu — o app não reaproveita controle entre dois pais."""
    return fch.LineChartTooltip(
        bgcolor=TOOLTIP_FUNDO,
        border_side=ft.BorderSide(1.5, ft.Colors.BLUE_200),
        # Mantém o balão dentro da área do gráfico: sem isso, perto do
        # topo ele subia além do card e a primeira linha era cortada.
        fit_inside_horizontally=True,
        fit_inside_vertically=True,
    )


def clonar_series(series: list) -> list:
    """Cópia das séries de um gráfico, para o gráfico do diálogo "Ampliar".
    `dataclasses.replace` gera controles novos, com identificador próprio (um
    `deepcopy` copiava o identificador interno, e dois controles com o mesmo
    id confundem o cliente); os pontos precisam ser copiados um a um, porque
    o `replace` da série é raso e dividiria a lista com o original. Os
    marcadores (`point`) e os tooltips não são controles, podem ser
    compartilhados."""
    return [
        dataclasses.replace(
            serie, points=[dataclasses.replace(p) for p in serie.points]
        )
        for serie in series
    ]


def ponto_grafico(
    x: float,
    y: float,
    nome_x: str,
    nome_y: str,
    unidade_y: str = "",
    negrito: bool = True,
) -> fch.LineChartDataPoint:
    """Ponto de série dos gráficos, com o tooltip (ao passar o cursor)
    mostrando os dois valores, nomeados e formatados por `formatar_valor`
    — em duas linhas, ex.: "x1 = 0.3500" e "P = 45.23 kPa". Sem o nome,
    o valor solto do tooltip padrão não diz de que eixo é; sem o x, não
    diz onde está.

    `negrito=False` deixa o texto do balão em peso normal; o padrão é
    negrito. Regra nos dois gráficos: só a curva do modelo sai em negrito;
    os pontos da tabela (experimentais) e os marcadores vazados (comparativo,
    o modelo calculado nos x1 da tabela) saem em peso normal."""
    sufixo = f" {unidade_y}" if unidade_y else ""
    texto = (
        f"{nome_x} = {formatar_valor(x)}\n"
        f"{nome_y} = {formatar_valor(y)}{sufixo}"
    )
    # Cor do texto: sem `color` no `text_style`, o Flet pinta o balão com a
    # cor da própria série (azul no líquido, laranja no vapor) — escolha do
    # autor (2026-10-03), que mostra a que fase cada linha pertence. Sobre
    # o fundo BLUE_50 o contraste é ~4,0:1 (azul) e ~3,3:1 (laranja), abaixo
    # dos 4,5:1 recomendados; sobre o fundo cinza-azulado padrão do Flet era
    # bem pior (por isso o fundo foi trocado).
    # Um estilo só para o balão inteiro, de propósito: rótulo em negrito e
    # número normal exigiria `text_spans`, que no Flet 1.0.0 faz o balão
    # sumir (o cliente lê os trechos como controles, não como dados); o
    # negrito em letras Unicode (𝐱, 𝐏) sai em fonte serifada de fallback.
    # `text_align` padrão do Flet é CENTER: as duas linhas saíam centradas
    # uma em relação à outra. START alinha o início das duas à esquerda.
    return fch.LineChartDataPoint(
        x,
        y,
        tooltip=fch.LineChartDataPointTooltip(
            text=texto,
            text_align=ft.TextAlign.START,
            text_style=ft.TextStyle(
                size=14,
                weight=ft.FontWeight.BOLD if negrito else ft.FontWeight.W_400,
            ),
        ),
    )


def importar_pontos_csv(
    texto_csv: str,
) -> tuple[list[tuple[float, float, float]], int]:
    """Lê um CSV com colunas P, x, y (cabeçalho, nomes case-insensitive,
    em qualquer ordem) e retorna (pontos válidos, nº de linhas ignoradas).
    Levanta ValueError se o cabeçalho não tiver as três colunas esperadas."""
    leitor = csv.DictReader(io.StringIO(texto_csv))
    if not leitor.fieldnames:
        raise ValueError("arquivo CSV vazio ou sem linha de cabeçalho")

    coluna_de = {(nome or "").strip().lower(): nome for nome in leitor.fieldnames}
    faltando = [c for c in ("p", "x", "y") if c not in coluna_de]
    if faltando:
        raise ValueError(
            "cabeçalho do CSV precisa ter as colunas P, x, y "
            f"(faltando: {', '.join(faltando).upper()})"
        )

    pontos = []
    ignoradas = 0
    for linha in leitor:
        try:
            pontos.append(parse_ponto(
                linha[coluna_de["p"]], linha[coluna_de["x"]], linha[coluna_de["y"]]
            ))
        except (ValueError, TypeError):
            ignoradas += 1
    return pontos, ignoradas


def _separar_linha(linha: str) -> list[str]:
    """Divide uma linha de texto colado em campos. Aceita ponto e vírgula,
    tabulação (colagem do Excel), espaços ou vírgula como separador; com
    ponto e vírgula, tabulação ou espaços, a vírgula é lida como decimal."""
    if ";" in linha:
        return [c.strip().replace(",", ".") for c in linha.split(";")]
    if "\t" in linha:
        return [c.strip().replace(",", ".") for c in linha.split("\t")]
    por_espaco = linha.split()
    if len(por_espaco) == 3:
        return [c.replace(",", ".") for c in por_espaco]
    return [c.strip() for c in linha.split(",")]


def importar_pontos_texto(
    texto: str,
) -> tuple[list[tuple[float, float, float]], int]:
    """Lê pontos (P, x, y) de um texto colado — uma linha por ponto, na
    ordem P, x, y. A primeira linha pode ser um cabeçalho (P, x, y em
    qualquer ordem, como no CSV); sem cabeçalho, vale a ordem P, x, y.
    Retorna (pontos válidos, nº de linhas ignoradas). Levanta ValueError se
    o texto estiver vazio ou o cabeçalho não tiver as colunas P, x, y."""
    linhas = [l for l in texto.splitlines() if l.strip()]
    if not linhas:
        raise ValueError("nenhum texto para importar")

    ordem = (0, 1, 2)
    campos = _separar_linha(linhas[0])
    try:
        [float(c) for c in campos]
    except ValueError:
        # Primeira linha não numérica: é cabeçalho.
        nomes = [c.lower() for c in campos]
        if sorted(nomes) != ["p", "x", "y"]:
            raise ValueError(
                "cabeçalho precisa ter as colunas P, x, y, ou não ter "
                "cabeçalho nenhum (ordem P, x, y)"
            )
        ordem = (nomes.index("p"), nomes.index("x"), nomes.index("y"))
        linhas = linhas[1:]

    pontos = []
    ignoradas = 0
    for linha in linhas:
        campos = _separar_linha(linha)
        try:
            pontos.append(parse_ponto(*(campos[i] for i in ordem)))
        except (ValueError, TypeError, IndexError):
            ignoradas += 1
    return pontos, ignoradas


# Exemplos do botão "Importar dados" (2026-10-07): isotermas de dado
# experimental com fonte citável, obtidas do NIST/TRC ThermoML Archive
# (doi:10.18434/mds2-2422, dados públicos; extraídos pelo TRC, não avaliados
# criticamente). Os CSVs ficam em referencias/ com a fonte no cabeçalho. Ao
# carregar, o exemplo também ajusta componentes e temperatura da tela, porque
# o dado só faz sentido a essa T. Para acrescentar um exemplo, basta uma linha
# em EXEMPLOS_NIST (x e y do CSV são do componente 1). O campo "limitacoes"
# (2026-10-07, pedido do autor) alimenta o "?" de cada exemplo no diálogo
# "Exemplos"; é redação do assistente a partir de fatos medidos, a revisar.
PASTA_REFERENCIAS = Path(__file__).resolve().parent.parent / "referencias"
_CSV_ETANOL_AGUA = PASTA_REFERENCIAS / "nist_thermoml_cristino2013_etanol_agua_isotermas.csv"
_FONTE_ETANOL_AGUA = "Cristino et al., Fluid Phase Equilib. 341 (2013) 48-53, via NIST ThermoML"
EXEMPLOS_NIST = [
    {
        "rotulo": "etanol/água, 90 °C",
        "arquivo": _CSV_ETANOL_AGUA, "coluna": "etanol", "T_K": 363.3,
        "componente1": "ethanol", "componente2": "water",
        "fonte": _FONTE_ETANOL_AGUA,
        "nota": "faixa de x₁ incompleta, T elevada",
        "limitacoes": (
            "# Origem do dado\nNIST/TRC ThermoML (dados públicos), extraídos pelo TRC e não avaliados criticamente.\n\n# Faixa de x₁ incompleta\nHá 12 pontos, com x₁ de 0,16 a 0,997: nada abaixo de 0,16 e um vão de 0,79 a 0,997. Os dois componentes puros não foram medidos. O teste da área (consistência termodinâmica) não é conclusivo sobre uma faixa parcial.\n\n# Temperatura e pressão elevadas\nIsoterma de 90 °C, P de 126 a 159 kPa (acima de 1 atm). O app supõe fase vapor ideal (Raoult modificada); em pressão alta essa hipótese é menos boa, e a temperatura fica bem acima das de aula.\n\n# O que funciona\nNRTL, Wilson e UNIQUAC (parâmetros do banco) e UNIFAC reproduzem o dado sem nenhum ajuste: Wilson ΔP 0,5 % e Δy 0,024; UNIFAC 0,9 % e 0,021; NRTL 1,1 % e 0,029; UNIQUAC 1,3 % e 0,030. A regressão de Barker também converge."
        ),
    },
    {
        "rotulo": "etanol/água, 108 °C",
        "arquivo": _CSV_ETANOL_AGUA, "coluna": "etanol", "T_K": 381.4,
        "componente1": "ethanol", "componente2": "water",
        "fonte": _FONTE_ETANOL_AGUA,
        "nota": "faixa de x₁ incompleta, T elevada",
        "limitacoes": (
            "# Origem do dado\nNIST/TRC ThermoML (dados públicos), extraídos pelo TRC e não avaliados criticamente.\n\n# Faixa de x₁ incompleta\nHá 26 pontos, com x₁ de 0,017 a 0,997: um vão de 0,79 a 0,997. Os dois componentes puros não foram medidos. O teste da área (consistência termodinâmica) não é conclusivo sobre uma faixa parcial.\n\n# Temperatura e pressão elevadas\nIsoterma de 108 °C, P de 156 a 295 kPa (quase 3 atm). O app supõe fase vapor ideal (Raoult modificada); em pressão alta essa hipótese é menos boa, e a temperatura fica bem acima das de aula.\n\n# O que funciona\nNRTL, Wilson e UNIQUAC (parâmetros do banco) e UNIFAC reproduzem o dado sem nenhum ajuste: Wilson ΔP 0,8 % e Δy 0,017; NRTL 1,4 % e 0,022; UNIQUAC 1,6 % e 0,022; UNIFAC 2,3 % e 0,020. A regressão de Barker também converge."
        ),
    },
    {
        "rotulo": "metanol/dimetilbuteno, 70 °C",
        "arquivo": PASTA_REFERENCIAS / "nist_thermoml_feng2011_metanol_dimetilbuteno_isotermas.csv",
        "coluna": "metanol", "T_K": 343.15,
        "componente1": "methanol", "componente2": "2,3-dimethyl-2-butene",
        "fonte": "Feng, Dong e Li, Fluid Phase Equilib. 309 (2011) 201-205, via NIST ThermoML",
        "nota": "azeótropo de pressão máxima em x₁ ≈ 0,58 (mínimo ponto de ebulição)",
        "limitacoes": (
            "# Origem do dado\nNIST/TRC ThermoML (dados públicos), extraídos pelo TRC e não avaliados criticamente.\n\n# Só a regressão se aplica\nO par não tem parâmetros no banco (NRTL e Wilson) e o 2,3-dimetil-2-buteno não está na tabela de grupos UNIFAC, então UNIQUAC e UNIFAC não funcionam e \"Buscar do Banco\" não encontra o par. Use \"Calcular por Regressão (Barker)\" ou digite os parâmetros.\n\n# Pressão\nP de 91 a 191 kPa (acima de 1 atm em boa parte da faixa); o app supõe fase vapor ideal.\n\n# Aviso de duas fases líquidas\nMargules, Van Laar e NRTL ajustados por Barker a este dado chegam a desvios positivos tão fortes (A/RT ≈ 2,2 no Margules 1-P) que o modelo prevê separação em duas fases líquidas para x₁ entre cerca de 0,34 e 0,67 (Margules e Van Laar), e o app mostra um aviso laranja. O dado é de fase única e o ajuste reproduz P e y bem; o aviso diz que o modelo, extrapolado, prevê uma separação que o dado não mostra. O Wilson não prevê separação de fases e não avisa.\n\n# O que funciona\nO dado cobre x₁ de 0 a 1 com os dois puros medidos (P dentro de 0,1 % da pressão de vapor do thermo) e passa no teste da área (D ≈ 4 %). Depois de ajustados por Barker, os modelos erram ΔP em 1 a 2 % e Δy em 0,011 a 0,025, e reproduzem o azeótropo de pressão máxima a menos de 0,015 em x₁ (experimental 0,575; Wilson 0,579).\n\n# Cosmético\nO campo \"Componente 2\" mostra o nome cortado; o valor está inteiro."
        ),
    },
    {
        "rotulo": "clorofórmio/MEK, 30 °C",
        "arquivo": PASTA_REFERENCIAS / "nist_thermoml_clara2006_cloroformio_mek_303K.csv",
        "coluna": "cloroformio", "T_K": 303.15,
        "componente1": "chloroform", "componente2": "2-butanone",
        "fonte": "Clara, Marigliano e Solimo, J. Chem. Eng. Data 51 (2006) 1473-1478, via NIST ThermoML",
        "nota": "desvio negativo, azeótropo de pressão mínima em x₁ ≈ 0,19 (máximo ponto de ebulição)",
        "limitacoes": (
            "# Origem do dado\nNIST/TRC ThermoML (dados públicos), extraídos pelo TRC e não avaliados criticamente.\n\n# Só a regressão se aplica\nO par não tem parâmetros no banco (NRTL, Wilson e UNIQUAC) e o clorofórmio não está na tabela de grupos UNIFAC, então \"Buscar do Banco\", UNIQUAC e UNIFAC não funcionam. Use \"Calcular por Regressão (Barker)\" ou digite os parâmetros.\n\n# Azeótropo: o modelo não acerta a composição\nO modelo ajustado reproduz a existência e o tipo do azeótropo de pressão mínima e a pressão (≈ 15 kPa), mas o coloca em x₁ ≈ 0,14 a 0,15, contra 0,19 do dado: a região é quase plana e a composição é pouco determinada.\n\n# Pontos do dado\nA pressão medida da 2-butanona pura (15,74 kPa) fica 3,2 % acima da pressão de vapor do thermo (15,25 kPa), o que desloca um pouco o erro ΔP. Há dois pontos em x₁ = 0,252, então a mensagem após \"Comparar\" conta 21 composições distintas (o erro usa os 22 pontos).\n\n# O que funciona\nO dado cobre x₁ de 0 a 1 e passa no teste da área (D ≈ 3 %). Por Barker, ΔP fica em 1,5 a 1,6 % e Δy em 0,008 a 0,009; o Van Laar sai com A₁₂ e A₂₁ negativos (−0,97 e −1,33), como se espera de um desvio negativo."
        ),
    },
]


# Botão "Ajuda" (2026-10-07, pedido do autor): manual rápido / tira-dúvidas,
# navegável por tópicos. Por ora só o sumário — `conteudo=None` mostra "em
# breve"; para escrever um tópico basta trocar o None por um texto. Os tópicos
# seguem os cards da tela: o "?" de cada card abre o tópico dele (campo `id`,
# usado por `cartao(..., ajuda=id)`). Lista proposta pelo assistente e
# aprovada em linhas gerais pelo autor ("vamos seguir sua recomendação");
# os títulos exatos seguem a confirmar.
AJUDA_TOPICOS = [
    {
        "id": "primeiros_passos",
        "titulo": "Primeiros passos (3 etapas)",
        # Rascunho do assistente (2026-10-07), a revisar pelo autor.
        "conteudo": (
            "Em 3 etapas, usando um exemplo pronto:\n\n"
            "# 1. Carregue dados\n"
            "No card \"Dados experimentais\", toque em \"Exemplos\" e escolha um. "
            "O app preenche a tabela, os componentes e a temperatura e já desenha "
            "os dois gráficos.\n\n"
            "# 2. Ajuste o modelo\n"
            "No card \"Sistema\", escolha o modelo de Gᴱ. No card \"Parâmetros do "
            "modelo\", arraste o slider ou digite o valor do parâmetro e veja a "
            "curva mudar. O selo ao lado do título diz de onde veio o valor "
            "(Fornecido, Banco de dados ou Calculado).\n\n"
            "# 3. Compare com o experimental\n"
            "Toque em \"Comparar\": o app calcula o modelo nos pontos da tabela "
            "(marcadores vazados) e mostra o desvio em P (ΔP, em %) e em y₁ (Δy). "
            "Para o app buscar o parâmetro que melhor ajusta os dados, toque em "
            "\"Calcular por Regressão (Barker)\".\n\n"
            "Com os seus próprios dados: digite P (em kPa), x₁ e y₁ na tabela "
            "ou use \"Importar dados\"; informe os componentes (nome em inglês, "
            "como ethanol e water, ou número CAS) e a temperatura em °C. Os "
            "pontos digitados entram nos gráficos quando você sai do campo."
        ),
    },
    {
        "id": "dados",
        "titulo": "Dados experimentais: digitar, importar e exemplos",
        # Rascunho do assistente (2026-10-07), a revisar pelo autor.
        "conteudo": (
            "A tabela guarda os pontos experimentais de um sistema a "
            "temperatura constante: P (em kPa) e as frações molares x₁ (no "
            "líquido) e y₁ (no vapor) do componente 1.\n\n"
            "# Digitar na tabela\n"
            "Preencha P, x₁ e y₁ de cada linha, usando ponto como separador "
            "decimal (a vírgula não é aceita na tabela). \"Adicionar Novo "
            "Ponto\" cria uma linha; a lixeira vermelha exclui a linha. Linhas "
            "incompletas (com algum campo vazio) ficam de fora até serem "
            "preenchidas; as que têm os três campos mas com número inválido "
            "são ignoradas, com aviso. Os gráficos se atualizam sozinhos "
            "quando você sai de um campo (ou aperta Enter) e o conteúdo da "
            "tabela mudou.\n\n"
            "# Importar dados\n"
            "\"Importar dados\" substitui o conteúdo da tabela e já desenha os "
            "gráficos. Há duas formas:\n"
            "• Arquivo CSV do dispositivo: precisa de cabeçalho com as colunas "
            "P, x e y (maiúsculas ou minúsculas, em qualquer ordem).\n"
            "• Colar texto: uma linha por ponto, na ordem P, x₁, y₁, separados "
            "por espaço, tabulação, ponto e vírgula ou vírgula. Com espaço, "
            "tabulação ou ponto e vírgula, a vírgula vale como decimal (útil "
            "para colar direto do Excel). A primeira linha pode ser um "
            "cabeçalho P, x, y em qualquer ordem.\n"
            "Linhas inválidas são ignoradas e contadas na mensagem.\n\n"
            "# Exemplos\n"
            "\"Exemplos\" carrega dado experimental real (NIST/ThermoML); a "
            "mensagem mostra a fonte. Além da tabela, ele preenche os "
            "componentes e a temperatura, porque cada conjunto só vale à "
            "temperatura em que foi medido. Hoje são quatro: etanol/água a 90 "
            "e a 108 °C, metanol/2,3-dimetil-2-buteno a 70 °C e "
            "clorofórmio/2-butanona (MEK) a 30 °C.\n\n"
            "# Limpar dados\n"
            "\"Limpar dados\" esvazia a tabela inteira (volta a 10 linhas em "
            "branco). Fica apagado quando não há nenhum ponto válido.\n\n"
            "# Atenção às unidades\n"
            "Digite a pressão em kPa. Em outra unidade (mmHg, bar) o app não "
            "avisa, e o erro ΔP da comparação perde o sentido."
        ),
    },
    {
        "id": "sistema",
        "titulo": "Sistema: componentes, temperatura e modelo Gᴱ",
        # Rascunho do assistente (2026-10-07), a revisar pelo autor. Fatos
        # conferidos rodando o motor: nomes aceitos pelo thermo, aviso de T na
        # crítica, mensagens de erro e o que NÃO é reiniciado ao trocar
        # componentes/temperatura (parâmetros e tabela; o selo volta a Fornecido).
        "conteudo": (
            "Este card define o sistema binário que o app calcula. Os gráficos "
            "são refeitos quando você sai de um campo ou aperta Enter; no "
            "modelo, assim que você escolhe.\n\n"
            "# Componentes\n"
            "Digite o nome em inglês (ethanol, water, methanol, acetone) ou o "
            "número CAS (64-17-5). Maiúsculas não importam. Nomes em português "
            "costumam falhar: \"acetona\", \"benzeno\" e \"água\" (com acento) "
            "não são reconhecidos, enquanto \"etanol\", \"metanol\" e \"agua\" "
            "funcionam por coincidência. Na dúvida, use inglês ou CAS.\n\n"
            "O Componente 1 é o dono dos índices 1: x₁ e y₁ da tabela e dos "
            "gráficos, e os parâmetros A₁₂, τ₁₂ etc. Trocar a ordem dos "
            "componentes inverte o diagrama. Se o nome não for reconhecido, a "
            "mensagem \"Curva do modelo não calculada\" aparece no card "
            "\"Dados experimentais\". Dois componentes iguais não dão erro, mas "
            "o resultado não tem sentido.\n\n"
            "# Temperatura\n"
            "Em °C, com ponto como separador decimal (70.5; \"70,5\" dá erro). "
            "O cálculo é isotérmico: existe uma única temperatura, e ela deve "
            "ser a mesma em que os dados da tabela foram medidos, senão a "
            "comparação não vale. Os exemplos já preenchem a temperatura certa.\n\n"
            "Mantenha a temperatura abaixo da temperatura crítica dos dois "
            "componentes (etanol 241,6 °C; água 373,9 °C). Na crítica ou acima "
            "dela a pressão de vapor deixa de ter sentido: etanol/água a 300 °C "
            "daria pressões acima da pressão crítica do etanol (6268 kPa). O app "
            "ainda calcula, mas mostra um aviso laranja no card \"Dados "
            "experimentais\" dizendo qual componente passou da crítica.\n\n"
            "# Modelo Gᴱ\n"
            "Margules 1-P, Margules 2-P, Van Laar, Wilson e NRTL têm parâmetros "
            "que você ajusta no card \"Parâmetros do modelo\". UNIQUAC e UNIFAC "
            "não têm slider: calculam os parâmetros sozinhos a partir dos "
            "componentes. Isso só funciona se o par estiver nos dados do app — "
            "o UNIQUAC precisa de a₁₂/a₂₁ no banco para o par, e o UNIFAC precisa "
            "que os dois componentes tenham seus grupos na tabela do projeto. "
            "Se faltar, aparece uma mensagem de erro; use outro modelo.\n\n"
            "Trocar de modelo volta os parâmetros aos valores iniciais. Para "
            "saber quando usar cada modelo, veja o tópico \"Modelos de Gᴱ\".\n\n"
            "# Ao trocar componentes ou temperatura\n"
            "Os valores dos parâmetros e os pontos da tabela ficam como "
            "estavam. Se os parâmetros vieram do banco ou da regressão para o "
            "sistema anterior, o selo de origem volta a \"Fornecido\" e o ⓘ "
            "explica que os valores são do sistema anterior — refaça a busca no "
            "banco ou a regressão para o novo sistema."
        ),
    },
    {
        "id": "parametros",
        "titulo": "Parâmetros do modelo: slider, valor digitado, selo de origem, banco e regressão",
        # Rascunho do assistente (2026-10-07), a revisar pelo autor. Fatos
        # conferidos nas fórmulas de gemini.py (A₁₂/A₂₁ = ln γ à diluição
        # infinita; Λ = 1 e τ = 0 dão solução ideal), nos limites da regressão
        # (REGRESSAO_MODELOS), nas mensagens de erro reais e num teste com
        # dados sem relação com o par (resíduo ≈ 0,4 e parâmetro no limite).
        "conteudo": (
            "Este card controla os números que dão forma à curva do modelo. "
            "O selo ao lado do título diz de onde veio o valor atual.\n\n"
            "# O que cada parâmetro é\n"
            "Margules 1-P: um só parâmetro, A. Com A = 0 a solução é ideal; "
            "A > 0 dá desvio positivo da idealidade (γ > 1) e A < 0, desvio "
            "negativo (γ < 1).\n\n"
            "Margules 2-P e Van Laar: A₁₂ e A₂₁ são os valores de ln γ₁ e "
            "ln γ₂ à diluição infinita (quando x₁ tende a 0 e quando x₂ tende a "
            "0).\n\n"
            "Wilson: Λ₁₂ e Λ₂₁, sempre maiores que zero; com os dois iguais a 1 "
            "a solução é ideal.\n\n"
            "NRTL: τ₁₂, τ₂₁ e α₁₂; com τ₁₂ = τ₂₁ = 0 a solução é ideal. O α₁₂ "
            "não é ajustado pela regressão (fica fixo, 0,3 de início). O "
            "tópico \"Modelos de Gᴱ\" diz quando usar cada um.\n\n"
            "# Mudar o valor à mão\n"
            "Arraste o slider: o campo ao lado acompanha e o gráfico é "
            "redesenhado quando você solta. Ou digite no campo e confirme com "
            "Enter ou saindo do campo (a vírgula decimal vale). Valor que não "
            "é número volta ao anterior com um aviso vermelho; Λ₁₂ e Λ₂₁ têm "
            "de ser maiores que zero.\n\n"
            "A faixa do slider é só um recorte para explorar: A, A₁₂, A₂₁, τ₁₂ e "
            "τ₂₁ vão de −3 a 3; Λ, de 0,01 a 3; α₁₂, de 0,2 a 0,47. Um valor "
            "digitado, vindo do banco ou da regressão pode ficar fora dela: o "
            "botão do slider vai para a ponta, mas o cálculo usa o valor real.\n\n"
            "# O selo de origem\n"
            "Fornecido: valor inicial do app, ou arrastado ou digitado por você. "
            "Banco de dados: veio do botão \"Buscar do Banco\" (ou é o UNIQUAC, "
            "que sempre usa o banco). Calculado: veio da regressão. Calculado "
            "(poucos pontos): regressão com o número mínimo de pontos, confiança "
            "baixa. Preditivo: UNIFAC, sem parâmetro por par. Banco, r/q via "
            "UNIFAC: UNIQUAC cujos r/q não estavam no banco. Toque no ⓘ para ver "
            "o detalhe (tabela do banco usada, número de pontos e resíduo da "
            "regressão).\n\n"
            "Mexer à mão em qualquer parâmetro (menos o α₁₂), ou trocar "
            "componentes ou temperatura, devolve o selo a \"Fornecido\".\n\n"
            "# Buscar do Banco (IPDB)\n"
            "Só existe para NRTL e Wilson: Margules e Van Laar não têm tabela no "
            "banco. Usa os componentes e a temperatura do card \"Sistema\" e "
            "preenche todos os parâmetros do modelo (no NRTL, inclusive o α₁₂ "
            "do banco). Se o par não está na tabela, aparece \"Busca no banco "
            "não realizada\" com o motivo — é o caso de metanol/"
            "dimetilbuteno e clorofórmio/MEK dos exemplos.\n\n"
            "# Calcular por Regressão (Barker)\n"
            "Ajusta os parâmetros aos pontos da tabela, comparando a pressão e "
            "a composição do vapor calculadas com as medidas. Serve para pares "
            "sem parâmetros no banco. Só acende com pontos válidos suficientes: "
            "2 para Margules 1-P e 3 para os demais; tocar no botão apagado "
            "explica. Não existe para UNIQUAC e UNIFAC. Usa a temperatura do "
            "card \"Sistema\", que deve ser a dos dados.\n\n"
            "O resíduo RMS, no ⓘ do selo, resume o ajuste (ΔP relativo e Δy "
            "juntos, sem unidade). Nos exemplos NIST ele ficou entre 0,007 e "
            "0,023; num teste com dados sem relação com o par saiu cerca de 0,4.\n\n"
            "O app mostra um aviso laranja neste card quando o parâmetro termina "
            "a menos de 1 % de um limite da busca (±5 no Margules, Van Laar e "
            "NRTL; 0,0001 e 10 no Wilson) ou quando o otimizador não converge: "
            "quase sempre é sinal de que o modelo não descreve os dados ou de "
            "que há erro de digitação. O aviso não cobre tudo — um resíduo alto "
            "com os parâmetros dentro dos limites passa sem aviso. Confira "
            "sempre com \"Comparar\".\n\n"
            "# UNIQUAC e UNIFAC\n"
            "Não têm slider: os parâmetros saem sozinhos dos componentes, e os "
            "botões de banco e regressão não aparecem."
        ),
    },
    {
        "id": "comparar",
        "titulo": "Comparar calculado e experimental (ΔP e Δy)",
        # Rascunho do assistente (2026-10-07), a revisar pelo autor. Fatos
        # conferidos em `calcular_comparativo` e rodando o app: a comparação
        # SOME ao mudar qualquer parâmetro (gerar_grafico a limpa) e é preciso
        # clicar de novo; valores de referência vêm das validações NIST.
        "conteudo": (
            "A comparação responde à pergunta: o quanto o modelo, com os "
            "parâmetros de agora, erra os pontos da tabela?\n\n"
            "# Como usar\n"
            "O botão \"Comparar\", no card \"Parâmetros do modelo\", só acende "
            "com pelo menos um ponto válido na tabela (tocar nele apagado "
            "explica). Vale para todos os modelos, inclusive UNIQUAC e UNIFAC. "
            "Ao clicar, o app calcula o modelo exatamente nos x₁ da tabela, e não "
            "na malha de 101 pontos da curva.\n\n"
            "# Como ler os gráficos\n"
            "No diagrama P-x-y aparecem marcadores vazados (a coluna "
            "\"Comparativo\" da legenda): o modelo calculado nos x₁ da tabela, "
            "com a mesma cor e forma da fase (quadrado: líquido; círculo: vapor). "
            "A distância entre um marcador cheio (dado da tabela) e o vazado do "
            "mesmo ponto é o erro. O gráfico de ln γ não muda com \"Comparar\": "
            "os pontos da tabela já aparecem nele sem precisar clicar (veja o "
            "tópico do ln γ).\n\n"
            "# O que são ΔP e Δy\n"
            "ΔP é o erro relativo da pressão, em %, em relação à pressão medida. "
            "Δy é o erro absoluto da fração molar do vapor (sem unidade; 0,02 é "
            "2 pontos percentuais). Os dois são RMS: tira-se a raiz da média dos "
            "quadrados dos erros de todos os pontos, o que pesa mais os erros "
            "grandes que uma média simples. Ficam separados porque cada um mede "
            "uma coisa — a pressão reflete o desvio da idealidade como um todo; "
            "a composição do vapor é mais sensível ao erro em cada componente. "
            "O ΔP é relativo porque a pressão nunca chega perto de zero; o Δy é "
            "absoluto porque y passa por 0 e 1 nas bordas, onde um erro "
            "relativo explodiria.\n\n"
            "# Valores de referência\n"
            "Nos exemplos NIST do app: modelos do banco de dados sem nenhum ajuste "
            "no etanol/água, ΔP entre 0,5 e 2,3 % e Δy entre 0,017 e 0,030; "
            "modelos ajustados por regressão de Barker, ΔP de 1 a 2 % e Δy de "
            "0,008 a 0,025. É a ordem de grandeza de um bom ajuste com dado "
            "confiável, não um critério de aprovação: o dado também tem erro.\n\n"
            "# Cuidados\n"
            "A comparação some quando deixa de valer: ao mexer em qualquer "
            "parâmetro, trocar de modelo, mudar o sistema, importar dados, e "
            "também ao editar ou excluir um ponto da tabela. Os marcadores "
            "vazados, o ΔP e o Δy desaparecem e é preciso clicar em "
            "\"Comparar\" de novo. Isso evita mostrar um erro que já não "
            "vale.\n\n"
            "Um ΔP de dezenas de % quase sempre indica entrada errada, e não "
            "modelo ruim: confira se P está em kPa, se a temperatura é a dos "
            "dados e se os componentes estão na ordem certa (x₁ e y₁ são do "
            "Componente 1).\n\n"
            "Todos os pontos pesam igual, inclusive os repetidos. Depois de "
            "\"Comparar\", a mensagem do card \"Dados experimentais\" diz com "
            "quantos pontos o erro foi calculado e onde (em que x₁) estão o "
            "maior desvio de pressão e o maior desvio de y₁ — é por aí que "
            "vale começar a procurar um ponto digitado errado ou a região em "
            "que o modelo falha."
        ),
    },
    {
        "id": "pxy",
        "titulo": "Diagrama P-x-y",
        # Rascunho do assistente (2026-10-07), a revisar pelo autor. Fatos
        # conferidos no código (`gerar_grafico`, `ponto_grafico`, lupa) e nos
        # exemplos NIST (azeótropos); leitura do diagrama é termodinâmica
        # padrão.
        "conteudo": (
            "O diagrama mostra o equilíbrio líquido-vapor do sistema a uma "
            "temperatura fixa: a pressão P (kPa, eixo vertical) contra a "
            "fração molar do Componente 1 (eixo horizontal).\n\n"
            "# O que está desenhado\n"
            "Curva azul (\"Líquido\"): a pressão de bolha, P contra x₁, a fração "
            "molar no líquido. Curva laranja (\"Vapor\"): a pressão de orvalho, P "
            "contra y₁, a fração molar no vapor. As duas dividem o mesmo eixo "
            "horizontal, por isso ele se chama \"x₁, y₁\".\n\n"
            "Os marcadores cheios são os pontos da tabela: quadrado azul, o "
            "líquido (x₁, P); círculo laranja, o vapor (y₁, P). Cada ponto "
            "experimental gera os dois, na mesma altura. Os marcadores vazados "
            "aparecem depois de \"Comparar\" (veja o tópico dele).\n\n"
            "# Como ler\n"
            "Acima da curva azul o sistema é só líquido; abaixo da laranja, só "
            "vapor; entre as duas, líquido e vapor coexistem. Uma linha "
            "horizontal na altura de uma pressão liga a composição do líquido "
            "(onde ela cruza a curva azul) à do vapor em equilíbrio com ele (onde "
            "cruza a laranja).\n\n"
            "Nos extremos, x₁ = 0 e x₁ = 1, as duas curvas se encontram: são as "
            "pressões de vapor dos componentes puros à temperatura escolhida. Se "
            "os pontos medidos nas pontas não caem sobre esse encontro, confira a "
            "temperatura e os componentes.\n\n"
            "# Azeótropo\n"
            "Quando as curvas se tocam no meio, com tangente horizontal, líquido "
            "e vapor têm a mesma composição: é um azeótropo. Pode ser de pressão "
            "máxima (as curvas formam um arco para cima; desvio positivo da "
            "idealidade), como o metanol/dimetilbuteno a 70 °C, em x₁ ≈ 0,58, ou "
            "de pressão mínima (arco para baixo; desvio negativo), como o "
            "clorofórmio/MEK a 30 °C, em x₁ ≈ 0,19. Ver o azeótropo no modelo e "
            "nos pontos é um bom teste de que o modelo capta o desvio. Os "
            "azeótropos de pressão máxima são mais comuns que os de pressão "
            "mínima (Koretsky, seção 8.1).\n\n"
            "# Cálculo\n"
            "As curvas vêm da lei de Raoult modificada: P = x₁γ₁P₁ˢᵃᵗ + x₂γ₂P₂ˢᵃᵗ e "
            "y₁ = x₁γ₁P₁ˢᵃᵗ/P, com γ do modelo de Gᴱ escolhido e as pressões de "
            "vapor da thermo. O vapor é tratado como ideal. Vale para uma única "
            "temperatura.\n\n"
            "# Detalhes da tela\n"
            "O gráfico é redesenhado sozinho ao mexer em parâmetro, modelo ou "
            "sistema e quando você edita a tabela (ao sair do campo ou apertar "
            "Enter). Sem pontos válidos, só as curvas do modelo "
            "aparecem; se o modelo falhar, aparecem só os pontos e a mensagem "
            "\"Curva do modelo não calculada\". O eixo vertical se ajusta para "
            "caber dados e curvas.\n\n"
            "Passando o cursor sobre um ponto, o balão mostra "
            "x₁ (ou y₁) e P. Os valores calculados pelo modelo saem em negrito; "
            "os da tabela, em peso normal.\n\n"
            "No computador, a lupa ao lado do título abre o gráfico ampliado, tal "
            "como está no momento do clique: para refletir mudanças, feche e "
            "abra de novo."
        ),
    },
    {
        "id": "gamma",
        "titulo": "Coeficientes de atividade (ln γ)",
        # Rascunho do assistente (2026-10-08), a revisar pelo autor; revisado no
        # mesmo dia a pedido do autor (sem números de um par específico, Gibbs-
        # Duhem com a condição em que vale, e o que os círculos vazados mostram
        # neste gráfico). Fatos conferidos rodando o motor (valores nas pontas,
        # Gibbs-Duhem, simetria do Margules 1-P, relação do azeótropo) e lendo
        # `gerar_grafico`/`ponto_grafico`.
        "conteudo": (
            "O gráfico mostra, para o modelo escolhido, o logaritmo natural do "
            "coeficiente de atividade de cada componente (ln γ₁ e ln γ₂, eixo "
            "vertical) contra x₁, a fração molar do Componente 1 no líquido.\n\n"
            "# O que ln γ diz\n"
            "O coeficiente de atividade γ mede o desvio do líquido em relação à "
            "solução ideal (γ = 1, ln γ = 0). ln γ > 0: o componente \"escapa\" "
            "mais do líquido do que o ideal (desvio positivo, pressão acima da "
            "de Raoult). ln γ < 0: escapa menos (desvio negativo). A curva "
            "verde é a de γ₁ e a roxa, a de γ₂ (as cores da legenda).\n\n"
            "# Como ler as curvas\n"
            "Cada componente puro é ideal: ln γ₁ = 0 em x₁ = 1 e ln γ₂ = 0 em "
            "x₁ = 0. O valor na ponta oposta é o da diluição infinita: ln γ₁ em "
            "x₁ = 0 (o componente 1 muito diluído no 2) e ln γ₂ em x₁ = 1. "
            "Costuma ser onde o desvio de cada curva é maior.\n\n"
            "As duas curvas estão ligadas pela equação de Gibbs-Duhem, que a "
            "temperatura constante (e sem considerar o efeito da pressão sobre "
            "γ, como o app faz) se escreve x₁·d ln γ₁/dx₁ + x₂·d ln γ₂/dx₁ = 0. "
            "Na prática: as inclinações das duas curvas têm sinais opostos (ou "
            "são ambas nulas), isto é, quando uma sobe a outra desce. Os modelos "
            "do app saem de uma energia de Gibbs em excesso, então obedecem a "
            "isso por construção (Koretsky, Eqs. 7.42 e 7.43); já em dados "
            "experimentais a mesma equação é a base dos testes de consistência "
            "termodinâmica, como o teste da área (Koretsky, Eq. 7.50). O livro "
            "deduz a equação a T e P constantes; em dados isotérmicos a "
            "dependência de γ com a pressão costuma ser pequena, e o teste pode "
            "ser aplicado direto (p. 428).\n\n"
            "No Margules 1-P as duas curvas são uma o espelho da outra em torno "
            "de x₁ = 0,5, e o parâmetro A é o valor de ln γ nas pontas. Desvio "
            "positivo dá curvas acima de zero; desvio negativo (A < 0), abaixo.\n\n"
            "# Relação com o P-x-y e o azeótropo\n"
            "O ln γ é o que dá forma ao diagrama P-x-y: sem desvio (ln γ = 0) as "
            "curvas do diagrama seriam as de Raoult. Num azeótropo, x₁ = y₁ e "
            "portanto γ₁P₁ˢᵃᵗ = γ₂P₂ˢᵃᵗ, ou seja, ln γ₁ − ln γ₂ = ln(P₂ˢᵃᵗ/P₁ˢᵃᵗ) "
            "(Koretsky, Eqs. 8.17 a 8.20). "
            "Dá para conferir lendo as duas curvas no x₁ do azeótropo e as "
            "pressões de vapor dos puros nas pontas do P-x-y.\n\n"
            "# Detalhes da tela\n"
            "As curvas são o que o modelo prevê, calculado em 101 valores de x₁.\n\n"
            "Os marcadores cheios (coluna \"Tabela\" da legenda) são o ln γ "
            "\"experimental\" dos pontos da tabela. A tabela traz P e y₁, não γ; o "
            "app calcula γ de cada componente pela lei de Raoult modificada, "
            "γᵢ = yᵢ·P/(xᵢ·Pᵢˢᵃᵗ), com a pressão de vapor da thermo na "
            "temperatura do card \"Sistema\" (vapor ideal). São valores derivados "
            "dos dados, não medidos. Só aparecem os pontos com x₁ entre 0,10 e "
            "0,90: perto dos extremos a divisão por um x pequeno amplifica o erro "
            "de P e de y₁, e o ponto deixa de ser confiável. A distância entre "
            "um marcador e a curva mostra onde o modelo se afasta do dado, e o "
            "erro de pressão aparece ampliado (dividido pela fração molar). "
            "Esses marcadores seguem a tabela: mudam quando ela é editada, e não "
            "dependem de \"Comparar\". Para os números do erro, use ΔP e Δy.\n\n"
            "Passando o cursor sobre um ponto, o balão mostra x₁ e o ln γ do "
            "componente. O eixo vertical se ajusta aos valores (o zero aparece "
            "como \"0\"). Com UNIQUAC e UNIFAC o gráfico aparece normalmente, "
            "com os parâmetros automáticos. No computador, a lupa ao lado do "
            "título abre o gráfico ampliado, tal como está no momento do clique."
        ),
    },
    {
        "id": "modelos",
        "titulo": "Modelos de Gᴱ e quando usar cada um",
        # Rascunho do assistente (2026-10-08), a revisar pelo autor, a partir do
        # Koretsky (2ª ed., 2013), cap. 7 (pp. 425-442) e dos fatos do projeto. O
        # roteiro "Qual usar" é síntese do assistente sobre as descrições do livro
        # (o livro só dá a estatística de p. 437). O limite A/RT > 2 do Margules 1-P
        # é derivado: d²(gᴱ/RT)/dx₁² = 1/(x₁x₂) − 2A/RT, mínimo 4 − 2A/RT em x₁ = 0,5.
        "conteudo": (
            "Um modelo de Gᴱ é uma expressão para a energia de Gibbs em excesso da "
            "mistura líquida, gᴱ, em função da composição. Dela saem os "
            "coeficientes de atividade de todos os componentes: RT ln γᵢ é a "
            "grandeza parcial molar de gᴱ, e gᴱ = RT·Σ xᵢ ln γᵢ (Koretsky, Eqs. "
            "7.48 e 7.49). Como todos os γ saem de uma só expressão, eles já "
            "respeitam a equação de Gibbs-Duhem. Os parâmetros são ajustados a "
            "dados experimentais e dependem da temperatura: valem para a "
            "temperatura dos dados.\n\n"
            "# Margules 1-P (dois sufixos)\n"
            "gᴱ = A·x₁x₂. Um parâmetro só, e o modelo é simétrico: as curvas de ln "
            "γ₁ e ln γ₂ são uma o espelho da outra em torno de x₁ = 0,5. Serve para "
            "misturas de moléculas parecidas em tamanho e em tipo de interação. O A "
            "compara a interação entre moléculas diferentes com a média das "
            "interações entre moléculas iguais: A > 0 quando as diferentes se "
            "atraem menos (γ > 1) e A < 0 quando se atraem mais (γ < 1) (Koretsky, "
            "Exemplo 7.9). Se A/RT passa de 2, o modelo passa a prever que a "
            "mistura se separa em duas fases líquidas (ver o tópico \"Limitações\").\n\n"
            "# Margules 2-P (três sufixos) e Van Laar\n"
            "Dois parâmetros, A₁₂ e A₂₁, que são o ln γ de cada componente à "
            "diluição infinita. Descrevem misturas assimétricas, em que as duas "
            "curvas de ln γ são diferentes. Com A₁₂ = A₂₁ os dois se reduzem ao "
            "Margules 1-P. No Van Laar os dois parâmetros precisam ter o mesmo "
            "sinal e o modelo não representa extremos de ln γ (Koretsky, p. 439); o "
            "Margules 2-P não tem essa restrição.\n\n"
            "# Wilson\n"
            "Dois parâmetros, Λ₁₂ e Λ₂₁, que precisam ser positivos. Funciona bem "
            "em misturas de substâncias polares com apolares, como álcoois e "
            "alcanos, e em misturas de hidrocarbonetos, e se estende bem a vários "
            "componentes. Não descreve mistura que se separa em duas fases líquidas "
            "(Koretsky, p. 439). Tem tabela no banco (botão \"Buscar do Banco\").\n\n"
            "# NRTL\n"
            "Três parâmetros: τ₁₂ e τ₂₁, de natureza energética, e α₁₂, ligado ao "
            "ordenamento local das moléculas. Lida com desvios grandes da "
            "idealidade, inclusive misturas parcialmente miscíveis e de orgânicos "
            "com água (Koretsky, p. 441). No app, a regressão não ajusta o α₁₂ (ele "
            "fica fixo); com \"Buscar do Banco\" ele vem do banco. Tem tabela no "
            "banco.\n\n"
            "# UNIQUAC\n"
            "Divide gᴱ em uma parte combinatorial, que depende do tamanho e da "
            "forma das moléculas (parâmetros r e q de cada componente puro), e uma "
            "parte residual, energética, com dois parâmetros de interação (a₁₂ e "
            "a₂₁, em K). Funciona para muitos pares de substâncias polares e "
            "apolares, inclusive parcialmente miscíveis (Koretsky, p. 441). No app "
            "não há slider: r, q, a₁₂ e a₂₁ saem do banco ChemSep (com r e q dos "
            "grupos UNIFAC se faltarem). O app usa q na parte residual, como o "
            "ChemSep; o Koretsky usa um q′ modificado para álcoois e água, e por "
            "isso resultados de exercícios do livro com esses compostos podem "
            "diferir.\n\n"
            "# UNIFAC\n"
            "Preditivo: divide cada molécula em grupos funcionais e calcula os γ a "
            "partir de parâmetros de interação entre os grupos, sem precisar de "
            "dado do par (Koretsky, p. 442). É útil quando não há dado nem "
            "parâmetro de banco, mas tende a ser menos preciso que um modelo "
            "ajustado ao par, e só vale para moléculas cujos grupos estão na tabela "
            "do app. Não tem slider nem regressão.\n\n"
            "# Qual usar\n"
            "Não existe um modelo melhor para tudo. Numa comparação com 3563 pares "
            "da coletânea DECHEMA, o Wilson foi o de melhor ajuste em só 30 % dos "
            "casos, e cada um dos modelos assimétricos foi o melhor em pelo menos "
            "467 sistemas (Koretsky, p. 437). Um roteiro, a adaptar a cada caso:\n"
            "• moléculas parecidas, poucos pontos: Margules 1-P;\n"
            "• desvio assimétrico: Margules 2-P ou Van Laar;\n"
            "• polar com apolar (álcool com hidrocarboneto, por exemplo): Wilson, "
            "NRTL ou UNIQUAC;\n"
            "• suspeita de duas fases líquidas: NRTL ou UNIQUAC, não o Wilson;\n"
            "• sem dado nem parâmetro do par: UNIFAC.\n"
            "Mais parâmetros ajustam melhor, mas pedem mais pontos (a regressão "
            "exige o número de parâmetros mais um). A melhor forma de escolher é "
            "testar: troque o modelo, ajuste, use \"Comparar\" e olhe ΔP e Δy.\n\n"
            "# Como os modelos foram conferidos\n"
            "As equações foram escritas no código do projeto. Margules 1-P, "
            "Margules 2-P, Van Laar, Wilson, NRTL e UNIQUAC foram conferidas contra "
            "as equações do Koretsky (Tabelas 7.2 e 7.4), e Wilson, NRTL, UNIQUAC e "
            "UNIFAC, contra a thermo. Um exemplo resolvido do livro "
            "(benzeno/ciclo-hexano a 10 °C, Exemplos 8.9 a 8.11) é reproduzido pelo "
            "app, no cálculo direto e na regressão. Detalhes em \"Sobre\"."
        ),
    },
    {
        "id": "limitacoes",
        "titulo": "Limitações e cuidados (isotérmico, unidades, gás ideal)",
        # Rascunho do assistente (2026-10-08), a revisar pelo autor. Fatos do
        # app conferidos no código; citações do Koretsky (2ª ed., 2013) lidas no
        # livro; Antoine e Tb medidos em testes/teste_psat_koretsky_apendice_a.py.
        "conteudo": (
            "O VLE Interativo é uma ferramenta de ensino e parte de hipóteses "
            "simplificadoras. Conhecê-las evita tirar do gráfico uma conclusão que "
            "o cálculo não sustenta.\n\n"
            "# Só isotérmico\n"
            "Todo o cálculo é a uma temperatura constante, a do card \"Sistema\": a "
            "pressão varia ao longo da curva. Os pontos da tabela devem ser todos "
            "dessa temperatura, e o app não confere isso. Diagramas isobáricos "
            "(T-x-y) não existem no app. Os parâmetros de um modelo valem para a "
            "temperatura em que foram obtidos: gᴱ e os γ mudam com a temperatura "
            "(Koretsky, seção 7.4, Eqs. 7.75 e 7.81), e usar parâmetros de outra "
            "temperatura só dá uma aproximação.\n\n"
            "# Gás ideal e lei de Raoult modificada\n"
            "O app calcula P = Σ xᵢγᵢPᵢˢᵃᵗ e yᵢ = xᵢγᵢPᵢˢᵃᵗ/P (Koretsky, Eqs. 8.10 "
            "a 8.16). Isso supõe vapor de gás ideal e fugacidade do líquido puro "
            "igual à pressão de saturação, sem correção de Poynting nem "
            "coeficientes de fugacidade. Vale a pressões baixas ou moderadas. A "
            "pressões altas, ou com substâncias que se associam no vapor, o vapor "
            "deixa de ser ideal e o cálculo se afasta do real; o livro trata esse "
            "caso com uma equação de estado (Exemplo 8.6). O app avisa quando a "
            "temperatura chega à crítica de algum componente, mas só avisa: bem "
            "antes disso o vapor ideal já é uma aproximação pior.\n\n"
            "# Uma só fase líquida\n"
            "O app supõe que o líquido é uma única fase em qualquer composição e não "
            "calcula equilíbrio líquido-líquido. Se os parâmetros dão desvio positivo "
            "forte (no Margules 1-P, A/RT acima de 2), o modelo prevê separação em "
            "duas fases líquidas (Koretsky, seção 7.4), e a curva calculada na região "
            "instável não corresponde a um equilíbrio real. O app testa isso: quando "
            "o modelo prevê a separação, aparece um aviso laranja com a faixa de x₁ "
            "afetada. Por exemplo, o ajuste do Margules 1-P ao exemplo de "
            "metanol/dimetilbuteno a 70 °C dá A/RT = 2,25 e dispara o aviso.\n\n"
            "# Dados e unidades\n"
            "A pressão da tabela é em kPa e o app não confere a unidade: outra "
            "unidade dá ΔP sem sentido, sem aviso. x₁ e y₁ são frações molares do "
            "Componente 1. O app também não faz teste de consistência termodinâmica "
            "nos dados. Um teste simples é o da área (Koretsky, Eq. 7.50): o "
            "gráfico de ln(γ₁/γ₂) contra x₁, calculado dos dados, deve ter áreas "
            "acima e abaixo do zero aproximadamente iguais. O app não o calcula.\n\n"
            "# Pressão de vapor e componentes\n"
            "As pressões de vapor vêm da thermo, que escolhe a correlação de cada "
            "substância. Conferidas contra a equação de Antoine do Apêndice A do "
            "Koretsky (11 compostos), a diferença ficou abaixo de 1,5 % na maioria "
            "e chegou ao máximo de 3,1 % (acetona, na ponta fria da faixa da "
            "Antoine do livro); no ponto de ebulição normal, a thermo reproduz "
            "101,325 kPa com erro menor que 0,05 %. Os componentes precisam ser "
            "reconhecidos pela thermo (nome em inglês ou CAS), e UNIQUAC e UNIFAC "
            "só funcionam para pares com dados no app.\n\n"
            "# O que o app não faz\n"
            "Equilíbrio líquido-líquido e sólido-líquido, misturas com mais de dois "
            "componentes, gases dissolvidos (lei de Henry) e diagramas T-x-y a "
            "pressão constante."
        ),
    },
    {
        "id": "sobre",
        "titulo": "Sobre: autor, fontes e créditos",
        # Pedido do autor (2026-10-07). Redação do assistente, a revisar pelo
        # autor. Versões e licenças conferidas nos metadados dos pacotes
        # instalados e no uv.lock; fontes dos dados conforme referencias/ e o
        # mapeamento. Tópico sem "?" de card: só no sumário do botão Ajuda.
        "conteudo": (
            "# Autor\n"
            "Leonardo de Sousa Lins, graduando em Engenharia Química na "
            "Universidade Federal do Ceará (UFC). O VLE Interativo foi "
            "desenvolvido como Trabalho de Conclusão de Curso, para o ensino do "
            "equilíbrio líquido-vapor com modelos de Gᴱ.\n\n"
            "# Linguagem e bibliotecas\n"
            "Python (Python Software Foundation): a linguagem de todo o app.\n\n"
            "Flet 1.0 e flet-charts 1.0, de Appveyor Systems Inc. e dos "
            "colaboradores do Flet (licença Apache 2.0; flet.dev): a interface e os "
            "gráficos.\n\n"
            "thermo 0.6.1 e chemicals 1.5.2, de Caleb Bell (licença MIT; "
            "github.com/CalebBell/thermo): reconhecimento dos componentes por nome "
            "ou CAS, pressão de vapor e acesso aos bancos de parâmetros.\n\n"
            "NumPy e SciPy, das comunidades que os mantêm: cálculo numérico e, no "
            "SciPy, o ajuste da regressão de Barker.\n\n"
            "As equações dos modelos de Gᴱ (Margules, Van Laar, Wilson, NRTL, "
            "UNIQUAC e UNIFAC) foram escritas no código do projeto. Wilson, "
            "NRTL, UNIQUAC e UNIFAC foram conferidas contra as implementações "
            "da thermo; Margules, Van Laar, Wilson, NRTL e UNIQUAC, também "
            "contra as equações do livro de Koretsky (abaixo). O Margules e o "
            "Van Laar, que a thermo não tem, foram conferidos ainda pela "
            "definição termodinâmica (energia de Gibbs em excesso) e contra os "
            "dados NIST abaixo.\n\n"
            "# Fontes dos parâmetros\n"
            "NRTL, Wilson e UNIQUAC: parâmetros de interação, e r/q do UNIQUAC, do "
            "banco ChemSep, de Harry Kooijman e Ross Taylor (Artistic License 2.0), "
            "distribuído com a thermo e a chemicals.\n\n"
            "UNIFAC: grupos e parâmetros do método original (Fredenslund, Jones e "
            "Prausnitz), conforme as tabelas da thermo.\n\n"
            "Regressão: técnica de redução de dados de equilíbrio líquido-vapor "
            "(método de Barker) descrita em Smith, Van Ness e Abbott.\n\n"
            "# Livro de referência\n"
            "Koretsky, M. D. Engineering and Chemical Thermodynamics, 2ª ed. "
            "Hoboken: Wiley, 2013. Referência das equações dos modelos "
            "(Tabelas 7.2 e 7.4), da equação de Gibbs-Duhem (Eqs. 6.19, 7.42 e "
            "7.43), do teste da área (Eq. 7.50), da lei de Raoult modificada e "
            "dos azeótropos (cap. 8). Dele vêm também conferências do app: "
            "exemplos e problemas resolvidos (Exemplos 8.5 e 8.9 a 8.11; "
            "Problema 7.70, com os dados de benzeno/ciclo-hexano a 10 °C que o "
            "livro atribui à coletânea DECHEMA de Gmehling et al.) e as "
            "equações de Antoine e as constantes do Apêndice A, contra as quais "
            "se conferiram as pressões de vapor da thermo.\n\n"
            "# Fontes dos dados experimentais\n"
            "Os exemplos vêm do NIST/TRC ThermoML Archive (doi:10.18434/mds2-2422; "
            "Riccardi et al., J. Comput. Chem. 43, 879, 2022), dados públicos "
            "extraídos pelo TRC e não avaliados criticamente. Artigos de origem:\n"
            "• Etanol/água: Cristino et al., Fluid Phase Equilib. 341 (2013) "
            "48-53, doi:10.1016/j.fluid.2012.12.014.\n"
            "• Metanol/2,3-dimetil-2-buteno: Feng, Dong e Li, Fluid Phase Equilib. "
            "309 (2011) 201-205, doi:10.1016/j.fluid.2011.07.014.\n"
            "• Clorofórmio/2-butanona: Clara, Marigliano e Solimo, J. Chem. Eng. "
            "Data 51 (2006) 1473-1478, doi:10.1021/je060150a.\n\n"
            "Como conferência secundária do Margules 2-P, usou-se também uma "
            "planilha do pacote XSEOS (canal Youtermo, no YouTube), de "
            "procedência não rastreada e com três casas decimais.\n\n"
            "# Licenças\n"
            "Cada biblioteca e cada base de dados mantém a licença e os direitos "
            "dos seus autores; os créditos acima são deles.\n\n"
            "# Contato: sugestões e feedback\n"
            "Sugestões de implementações futuras e feedback de quem usou o app são "
            "bem-vindos: leolins22@gmail.com"
        ),
    },
]


def carregar_exemplo_nist(exemplo: dict) -> list[tuple[float, float, float]]:
    """Pontos (P kPa, x1, y1) da isoterma do exemplo (`T_K`, em K) no CSV dele.
    x1 e y1 são do componente 1. Ignora as linhas de comentário (#)."""
    pontos = []
    with open(exemplo["arquivo"], encoding="utf-8") as f:
        for linha in csv.DictReader(l for l in f if not l.startswith("#")):
            if abs(float(linha["T_K"]) - exemplo["T_K"]) < 1e-6:
                pontos.append((
                    float(linha["P_kPa"]),
                    float(linha["x_" + exemplo["coluna"]]),
                    float(linha["y_" + exemplo["coluna"]]),
                ))
    return sorted(pontos, key=lambda p: p[1])


def aviso_ajuste_regressao(resultado, rotulos_por_chave):
    """Texto de aviso laranja se a regressão de Barker terminou suspeita, ou
    None: parâmetro a menos de 1 % de um limite da busca (`no_limite`) ou
    otimizador que não convergiu (`sucesso` falso). `rotulos_por_chave` mapeia a
    chave do parâmetro a uma tupla cujo último item é o rótulo exibido (como
    `sliders_por_chave`). Pedido do autor em 2026-10-07 (opção (a)); o resíduo
    alto sem parâmetro no limite não é coberto."""
    problemas = []
    if resultado.get("no_limite"):
        itens = ", ".join(
            f"{rotulos_por_chave[p['chave']][-1] if p['chave'] in rotulos_por_chave else p['chave']}"
            f" = {formatar_valor(p['valor'])} (limite da busca: {p['limite']:g})"
            for p in resultado["no_limite"]
        )
        problemas.append(f"terminou com parâmetro no limite da busca — {itens}")
    if resultado.get("sucesso") is False:
        problemas.append("o otimizador não convergiu")
    if not problemas:
        return None
    return (
        "Atenção: a regressão " + " e ".join(problemas) + ". O modelo "
        "provavelmente não descreve estes dados, ou há erro de digitação na "
        "tabela. Confira com \"Comparar\" antes de usar este ajuste."
    )


def aviso_instabilidade_liquida(x1, gamma1):
    """Texto de aviso se o modelo prevê duas fases líquidas (fase líquida única
    instável) em algum trecho de x₁, ou None. `x1` e `gamma1` são as listas de
    `calculate_vle_isothermal` na malha padrão. O diagrama P-x-y de Raoult
    modificada supõe uma só fase líquida, então não vale nesse trecho — pedido
    de aviso do autor em 2026-10-08 ("se o custo for baixo, implemente")."""
    faixa = detectar_instabilidade_liquida(x1, gamma1)
    if faixa is None:
        return None
    ini, fim = (f"{v:.2f}".replace(".", ",") for v in faixa)
    return (
        "Atenção: com estes parâmetros o modelo prevê duas fases líquidas "
        f"(fase líquida instável) para x₁ entre cerca de {ini} e {fim}. O "
        "diagrama P-x-y calculado supõe uma só fase líquida, então não vale "
        "nessa faixa. Se o sistema real é miscível em tudo, isso indica que o "
        "modelo ou os parâmetros não descrevem bem essa região."
    )


def aviso_temperatura_critica(comp1, comp2, T_C, tcs_C):
    """Texto de aviso se T_C chega à temperatura crítica de algum componente
    (`tcs_C` = [Tc1, Tc2] em °C, como devolve `calculate_vle_isothermal`), ou
    None. Acima da crítica a pressão de vapor extrapolada não tem sentido físico
    e o cálculo não dá erro — o autor pediu o aviso em 2026-10-07."""
    acima = [
        (nome, tc) for nome, tc in zip((comp1, comp2), tcs_C)
        if tc is not None and T_C >= tc
    ]
    if not acima:
        return None
    detalhe = "; ".join(f"{nome}: {tc:.1f} °C".replace(".", ",") for nome, tc in acima)
    return (
        f"Atenção: a temperatura ({T_C:g} °C) está na ou acima da temperatura "
        f"crítica de um componente ({detalhe}). Nesse caso a pressão de vapor "
        "não tem sentido físico e o diagrama não é confiável."
    )


# Escala de espaçamento única para o app inteiro (2026-09-28, passada de
# estética) — evita valores soltos espalhados sem critério; cada uso abaixo
# escolhe um destes três. 4/8/12 (espremido pra caber no zoom) ficou feio e
# mal espaçado (relatado pelo autor) — a causa real do desktop não caber em
# 100% de zoom era os dois gráficos empilhados ocupando espaço vertical
# demais, não o padding dos cards. Resolvido colocando os gráficos lado a
# lado no desktop (ver construir_grafico_p_xy/gamma), o que permite devolver
# um espaçamento confortável de novo.
ESPACO_PEQUENO = 6
ESPACO_MEDIO = 12
ESPACO_GRANDE = 20


# Função principal que constrói a interface
def main(page: ft.Page):
    # Configuração básica da página
    page.title = "VLE Interativo"
    page.padding = ESPACO_GRANDE
    # Sem isso, conteúdo mais alto que a janela fica simplesmente
    # inacessível — sem scroll nem aviso, só dá pra ver diminuindo o zoom
    # do navegador até tudo caber de uma vez. Passou despercebido com um
    # gráfico só; com o segundo gráfico (ln γ vs x1) ficou grave.
    page.scroll = ft.ScrollMode.AUTO
    # Tema claro fixo, não o padrão do sistema/navegador (2026-09-28) — o
    # usuário final é o orientador, projetando em sala de aula (seção 1.4
    # do mapeamento: "fontes grandes, alto contraste"); um app que muda de
    # claro pra escuro sozinho conforme o SO de quem abre é imprevisível
    # nesse cenário, e o tema escuro anterior (herdado do navegador) saiu
    # visivelmente mais escuro/baixo contraste num teste real em monitor.
    page.theme_mode = ft.ThemeMode.LIGHT
    # `body_medium` em 16 (padrão 14), item 6 da estética (2026-10-03): é o
    # estilo que o gráfico usa para os números da escala dos eixos, que
    # ficavam em ~12px — os textos que o público mais precisa ler de longe
    # em projeção. Com a escala maior, os rótulos do eixo x de 0,1 em 0,1
    # se encostavam no celular ("0.10.20.3…" a 360px), então o passo do
    # eixo x passou a 0,2 nos dois gráficos (os dois eixos são criados uma
    # vez, não dá para variar por modo sem mutar o eixo).
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE_700,
        text_theme=ft.TextTheme(body_medium=ft.TextStyle(size=16)),
    )

    # Variável de largura para manter tudo alinhado
    largura_coluna = 60

    # Estilo dos botões do card "Dados experimentais" (2026-10-03, a pedido
    # do autor, a critério do assistente). Secundários: fundo azul bem claro,
    # texto e ícone azul-escuro, contorno azul e cantos de 12px (a mesma
    # família das caixas do card Sistema). O mapa de estados é por
    # `ft.ControlState` para o botão apagado (Comparar sem dado) ficar cinza em
    # vez de azul. O estilo é definido na criação do botão, nunca mutado
    # depois. (O estilo "primário", azul cheio, era do "Gerar Gráfico", retirado
    # em 2026-10-08.)
    def estilo_botao():
        return ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: ft.Colors.BLUE_50,
                ft.ControlState.DISABLED: ft.Colors.GREY_100,
            },
            color={
                ft.ControlState.DEFAULT: ft.Colors.BLUE_800,
                ft.ControlState.DISABLED: ft.Colors.GREY_600,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1.5, ft.Colors.BLUE_200),
                ft.ControlState.DISABLED: ft.BorderSide(1.5, ft.Colors.GREY_300),
            },
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding(14, 10, 14, 10),
        )

    # Ícone ⓘ tocável (não só hover) — o `tooltip` nativo do Flet depende de
    # hover ou long-press, e o usuário final deste app usa celular (sem
    # mouse); um toque simples no ícone não abria nada de forma confiável.
    # Em vez de tooltip, o ícone abre um diálogo com a explicação — mesmo
    # gesto (toque) em qualquer dispositivo. `obter_texto` é uma função sem
    # argumentos (não uma string fixa) para cobrir os casos em que a
    # explicação muda em tempo real (ex.: origem do parâmetro).
    def icone_info(obter_texto, titulo="Sobre este valor"):
        def abrir(e):
            # Quebra de linha manual via textwrap, não `width` no
            # Container/Text — as duas tentativas anteriores (width no
            # Text, depois Container(width=320) em volta dele) não
            # bastaram pra impedir o texto de vazar pras laterais dentro
            # do AlertDialog (autor confirmou nas duas vezes, 2026-09-28).
            # Inserindo as quebras de linha (`\n`) no próprio texto, a
            # largura de cada linha fica garantida independente de como o
            # AlertDialog calcula a largura do conteúdo.
            texto_quebrado = "\n".join(textwrap.wrap(obter_texto(), width=42))
            page.show_dialog(
                ft.AlertDialog(
                    # Cabeçalho e corpo em cores diferentes, da paleta do app
                    # (pedido do autor, 2026-10-03): título em azul escuro
                    # (a cor da faixa e da nota do α₁₂), texto em verde-azulado
                    # escuro (a cor do texto da nota). Ambos > 4,5:1 no fundo
                    # do diálogo.
                    title=ft.Text(
                        titulo,
                        color=ft.Colors.BLUE_800,
                        weight=ft.FontWeight.BOLD,
                    ),
                    content=ft.Text(texto_quebrado, color=ft.Colors.TEAL_900),
                    actions=[ft.TextButton("Ok", on_click=lambda e: page.pop_dialog())],
                )
            )

        # Todos os ⓘ do app (selo de origem, ΔP e Δy) usam o mesmo estilo
        # (pedido do autor, 2026-10-03): ícone cheio, 18px, azul-celeste.
        return ft.IconButton(
            icon=ft.Icons.INFO,
            icon_size=18,
            icon_color=ft.Colors.LIGHT_BLUE_600,
            padding=0,
            on_click=abrir,
        )

    # Agrupamento visual em cards (2026-09-28, passada de estética) — antes,
    # tudo (sistema, sliders, tabela, botões, gráficos) ficava solto em
    # sequência, sem hierarquia visual entre seções que fazem coisas
    # diferentes. Cada card leva um título curto — mesma ideia de
    # "dashboards financeiros" já citada como inspiração do selo de origem
    # (seção 2.8 do mapeamento), aplicada agora ao layout inteiro.
    def cartao(
        titulo,
        *controles,
        expand=False,
        extra_titulo=None,
        centralizar=False,
        extra_junto=False,
        ajuda=None,
    ):
        # `extra_titulo` (opcional) — um controle extra ao lado do título,
        # no cabeçalho do card, em vez de só mais um item na lista debaixo.
        # Usado pelo botão "Comparar" no card "Dados experimentais" (pedido
        # do autor, 2026-09-28): fica junto do título, não lá embaixo.
        # `extra_junto` (2026-10-07): o extra fica logo depois do texto do
        # título (usado pelo selo de origem no card "Parâmetros do modelo"),
        # em vez de empurrado para a ponta direita.
        # Estilo (2026-10-03): título em azul-escuro, como os rótulos das
        # caixas do card Sistema.
        cabecalho = ft.Text(
            titulo, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800
        )
        # `ajuda` (2026-10-07): id de um tópico de AJUDA_TOPICOS; põe o "?" logo
        # depois do título, abrindo o tópico daquele card. O ícone é criado
        # novo a cada montagem (o app não muta controle já criado).
        if ajuda is not None:
            cabecalho = ft.Row(
                controls=[cabecalho, icone_ajuda_card(ajuda)],
                spacing=2,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        if centralizar and extra_titulo is None:
            # Num Column centralizado o título viria no meio; a Row ocupa a
            # largura toda e mantém o título à esquerda.
            cabecalho = ft.Row(controls=[cabecalho])
        if extra_titulo is not None:
            # `wrap=True` — sem isso, título + extra_titulo (ex.: "Dados
            # experimentais" + botão "Comparar" + ícone "Limpar Tabela")
            # não cabiam numa linha só no celular, e o Flutter quebrava o
            # layout inteiro com um erro de overflow (relatado pelo autor
            # como uma "tarja" cobrindo a tela, 2026-09-28) — mesma classe
            # de bug já corrigida antes em linha_componentes e nas linhas de
            # botões.
            cabecalho = ft.Row(
                controls=[cabecalho, extra_titulo],
                alignment=(
                    ft.MainAxisAlignment.START
                    if extra_junto
                    else ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
            )
        # Estilo (2026-10-03): todos os cards com fundo branco, moldura
        # azul-clara de 1,5px e cantos de 12px, sem sombra — a mesma
        # linguagem das caixas, da tabela e dos botões.
        return ft.Card(
            bgcolor=ft.Colors.WHITE,
            elevation=0,
            shape=ft.RoundedRectangleBorder(
                radius=12, side=ft.BorderSide(1.5, ft.Colors.BLUE_200)
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[cabecalho, *controles],
                    spacing=ESPACO_PEQUENO,
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.CENTER
                        if centralizar
                        else ft.CrossAxisAlignment.START
                    ),
                ),
                padding=ESPACO_MEDIO,
            ),
            expand=expand,
        )

    # 1. Criação da Tabela Vazia
    #
    # `column_spacing`/`horizontal_margin` apertados (2026-10-01): com os
    # padrões do Material (56 entre colunas, 24 nas bordas), a tabela pedia
    # ~440px de largura — sendo quase metade disso só espaço vazio, já que o
    # conteúdo (3 campos de 60 + a lixeira) soma ~228. No celular o card
    # oferece ~296px úteis, então a quarta coluna, a da lixeira, ficava fora
    # da tela: em 360 e 390px de largura NENHUM ícone de excluir aparecia, e
    # não havia rolagem horizontal pra alcançá-lo — ou seja, não dava pra
    # excluir um ponto individual pelo celular, que é o dispositivo principal
    # de uso. Medido por varredura de larguras com captura de tela.
    # Valor único para os dois modos de layout, de propósito: ajustar isso
    # conforme desktop/mobile significaria mutar propriedade de controle já
    # criado, que foi exatamente o gatilho do bug de renderização de
    # 2026-09-28 (ver montar_layout).
    # Estilo (2026-10-03): cabeçalho azul claro com texto azul-escuro em
    # negrito, linhas brancas separadas por filete azul e moldura de cantos
    # arredondados. `dt` continua filho direto da Column do card, sem
    # contêiner em volta (embrulhá-lo quebrou a renderização em 2026-09-28).
    dt = ft.DataTable(
        column_spacing=16,
        horizontal_margin=8,
        heading_row_color=ft.Colors.BLUE_50,
        data_row_color=ft.Colors.WHITE,
        border=ft.Border.all(1.5, ft.Colors.BLUE_200),
        border_radius=12,
        horizontal_lines=ft.BorderSide(1, ft.Colors.BLUE_100),
        # Unidade no cabeçalho de P (2026-10-01): o motor trabalha em kPa
        # (`calculate_vle_isothermal` devolve `P_kPa`) e `calcular_comparativo`
        # divide P calculado por P experimental direto — digitar mmHg ou bar
        # produzia um ΔP sem sentido e uma curva do modelo em escala
        # diferente dos pontos, sem nenhum aviso. x1/y1 em vez de x/y para
        # casar com a notação do resto do app e do cálculo.
        # Sem subscrito Unicode ("x₁") de propósito: o projeto já perdeu um
        # rótulo por glifo ausente em navegador de celular ("Gᴱ" saiu cortado
        # no Samsung Browser, 2026-09-27 — ver dropdown_modelo).
        columns=[
            ft.DataColumn(
                label=ft.Text(
                    "P (kPa)", width=largura_coluna, text_align=ft.TextAlign.CENTER,
                    size=14, color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD,
                )
            ),
            ft.DataColumn(
                label=ft.Text(
                    "x₁", width=largura_coluna, text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD,
                )
            ),
            ft.DataColumn(
                label=ft.Text(
                    "y₁", width=largura_coluna, text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD,
                )
            ),
            ft.DataColumn(label=ft.Text("", width=40)),  # Coluna vazia para a lixeira
        ],
        rows=[],  # Inicia sem linhas
    )

    # 2. Função geradora de linhas — `valores`, se informado, é (P, x, y) já
    # validado (usado pela importação de CSV) para pré-preencher a linha.
    def adicionar_linha(e=None, valores=None, atualizar=True):
        textos_iniciais = [str(v) for v in valores] if valores else ["", "", ""]

        # Bloqueia caractere não numérico ao digitar (não só o teclado
        # virtual do `keyboard_type=NUMBER`, que não impede letras de
        # verdade com teclado físico). Revertido de `ft.InputFilter`
        # (2026-09-28): esse controle quebrou a renderização no celular —
        # tudo depois do primeiro card virava uma área cinza (erro de
        # widget do Flutter), provável problema de serialização da regex
        # nessa versão do Flet. Filtro em Python puro (`on_change`
        # reescrevendo o valor) evita depender desse controle.
        def filtrar_numero(e):
            valor_filtrado = re.sub(r"[^0-9.\-]", "", e.control.value or "")
            if valor_filtrado != e.control.value:
                e.control.value = valor_filtrado
                e.control.update()
            # Editar a tabela invalida a comparação já mostrada (2026-10-07,
            # opção (a) do autor): o ΔP/Δy e os marcadores vazados eram da
            # tabela de antes.
            invalidar_comparacao()

        # Função para criar as caixas de texto padronizadas
        def criar_campo(valor_inicial):
            return ft.TextField(
                value=valor_inicial,
                width=largura_coluna,
                text_align=ft.TextAlign.CENTER,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=filtrar_numero,
                border=ft.NoInputBorder(),
                # Estilo (2026-10-03): fundo transparente (um branco opaco
                # cobria o filete entre as linhas) que vira azul claro ao
                # focar, cantos arredondados, texto escuro de peso médio.
                filled=True,
                fill_color=ft.Colors.TRANSPARENT,
                focused_bgcolor=ft.Colors.BLUE_50,
                border_radius=8,
                text_style=ft.TextStyle(
                    color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_500
                ),
                cursor_color=ft.Colors.BLUE_700,
                # Sem preenchimento lateral: com `filled`, o padrão do Material
                # (12px de cada lado) cortava "0.935" nos 60px da coluna.
                content_padding=ft.Padding(0, 8, 0, 8),
                # Ao sair do campo (ou Enter): reavalia os botões e, se o
                # conteúdo da tabela mudou, redesenha os gráficos (ver
                # `ao_sair_do_campo`, definida mais abaixo — resolvida por
                # closure só quando o evento acontece).
                # `lambda`: `ao_sair_do_campo` ainda não existe quando as linhas
                # iniciais são criadas; o nome só é resolvido no evento.
                on_blur=lambda e: ao_sair_do_campo(e),
                on_submit=lambda e: ao_sair_do_campo(e),
            )

        # Prepara a nova linha
        nova_linha = ft.DataRow(cells=[])

        # Função específica para excluir esta linha
        def excluir_esta_linha(e):
            dt.rows.remove(nova_linha)
            invalidar_comparacao()
            # Redesenha se o conteúdo mudou (ou só reavalia os botões, se a
            # linha excluída estava em branco) e já faz o page.update().
            ao_sair_do_campo()

        # O botão da lixeira permanece o mesmo (ft.IconButton suporta ícones nativamente)
        botao_excluir = ft.IconButton(
            icon=ft.Icons.DELETE,
            icon_color="red",
            tooltip="Excluir ponto",
            on_click=excluir_esta_linha,
        )

        # Preenche a linha com as células de texto e o botão de exclusão
        nova_linha.cells = [
            ft.DataCell(criar_campo(textos_iniciais[0])),
            ft.DataCell(criar_campo(textos_iniciais[1])),
            ft.DataCell(criar_campo(textos_iniciais[2])),
            ft.DataCell(botao_excluir),
        ]

        # Adiciona a linha à tabela e atualiza a interface — `atualizar`
        # pode ser desligado por quem chama em lote (criação inicial,
        # importação de CSV), pra mandar só UM `page.update()` no final em
        # vez de um por linha. Um `page.update()` por linha, disparado em
        # sequência rápida, é o suspeito principal de um bug intermitente
        # (pré-existente, não introduzido hoje) em que o Flutter no
        # celular quebra a renderização logo na carga da página — o
        # próprio autor confirmou que o problema já aparece "de fábrica",
        # sem precisar de nenhuma interação (2026-09-28).
        dt.rows.append(nova_linha)
        if atualizar:
            page.update()

    # Cria NUM_LINHAS_INICIAIS linhas em branco automaticamente (antes era
    # só 1, aumentado pra 10 a pedido do autor, 2026-09-28: menos cliques em
    # "Adicionar Novo Ponto" pra digitar um conjunto de dados típico). Extraí
    # numa função porque "Limpar Tabela" (abaixo) precisa recriar o mesmo
    # estado inicial. `atualizar=False` — só um `page.update()` no final,
    # feito por quem chama esta função (o carregamento inicial da página e
    # o "Limpar Tabela" já mandam sua própria atualização completa depois).
    NUM_LINHAS_INICIAIS = 10

    def criar_linhas_iniciais():
        for _ in range(NUM_LINHAS_INICIAIS):
            adicionar_linha(None, atualizar=False)

    criar_linhas_iniciais()

    # 3. CORREÇÃO DA DEPRECIAÇÃO: Construindo um botão moderno com ft.Button
    # Em vez de text= e icon=, colocamos uma ft.Row dentro do content=
    botao_adicionar = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.ADD), ft.Text("Adicionar Novo Ponto")],
            tight=True,  # Faz a linha ocupar apenas o espaço do texto e ícone
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=adicionar_linha,
        style=estilo_botao(),
    )

    # 3b. Importação via CSV (colunas P, x, y) — substitui os pontos da
    # tabela pelos do arquivo. Ficam editáveis depois de importados, como
    # os digitados manualmente (decisão em aberto na seção 2.2 do
    # mapeamento; assim ficou mais simples, sem um segundo modo travado).
    # O seletor é criado NO CLIQUE (2026-10-03), não na inicialização: criado
    # no início, o Flet o registra no navegador por uma mensagem avulsa,
    # enviada antes de a tela existir e nunca reenviada — se o navegador a
    # perde (visto no Chrome/Windows, sempre na primeira sessão do servidor,
    # FilePicker(112)), o clique estoura "Timeout waiting for invoke method
    # listener" e só o F5 conserta. Criado no clique, o navegador já está
    # carregado. É o padrão do Flet 1.0 (`ft.FilePicker().pick_files(...)`).

    # Aplica à tabela os pontos vindos de qualquer das três origens (arquivo,
    # exemplo, texto colado): substitui as linhas, redesenha e avisa.
    # `rotulo` diz a origem na mensagem de status.
    def aplicar_importacao(pontos, ignoradas, rotulo):
        if not pontos:
            mensagem_status.value = f"Nenhum ponto válido encontrado ({rotulo})."
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return

        dt.rows.clear()
        for ponto in pontos:
            adicionar_linha(valores=ponto, atualizar=False)

        aviso = f" {ignoradas} linha(s) ignorada(s) por dado inválido." if ignoradas else ""
        gerar_grafico(mensagem_extra=f"{len(pontos)} ponto(s) importado(s) ({rotulo}).{aviso}")

    def falha_importacao(exc):
        mensagem_status.value = f"Falha ao importar: {exc}."
        mensagem_status.color = ft.Colors.RED_800
        page.update()

    def importar_exemplo(exemplo):
        def acao(e):
            page.pop_dialog()
            try:
                pontos = carregar_exemplo_nist(exemplo)
            except (OSError, ValueError, KeyError) as exc:
                falha_importacao(exc)
                return
            # Só `.value` muda (regra do app: não mutar layout de controle criado).
            campo_componente1.value = exemplo["componente1"]
            campo_componente2.value = exemplo["componente2"]
            campo_temperatura.value = f"{exemplo['T_K'] - 273.15:.2f}"
            aplicar_importacao(
                pontos, 0,
                f"exemplo {exemplo['rotulo']}. Fonte: {exemplo['fonte']}; "
                f"{exemplo['nota']}",
            )

        return acao

    async def importar_arquivo(e):
        page.pop_dialog()
        try:
            arquivos = await ft.FilePicker().pick_files(
                dialog_title="Selecionar CSV (colunas P, x, y)",
                allowed_extensions=["csv"],
                with_data=True,
            )
        except (RuntimeError, TimeoutError):
            # O navegador não respondeu ao pedido de abrir o seletor (ver o
            # comentário acima). Segunda proteção: sem este except, o Flet
            # mostra a tela de erro da aplicação.
            mensagem_status.value = (
                "Não foi possível abrir o seletor de arquivos (o navegador "
                "não respondeu). Recarregue a página (F5) e tente de novo."
            )
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return
        if not arquivos:
            return  # usuário cancelou a seleção

        try:
            texto = arquivos[0].bytes.decode("utf-8")
            pontos, ignoradas = importar_pontos_csv(texto)
        except (ValueError, UnicodeDecodeError) as exc:
            falha_importacao(exc)
            return
        aplicar_importacao(pontos, ignoradas, "arquivo CSV")

    def abrir_colar_texto(e):
        page.pop_dialog()
        campo = ft.TextField(
            multiline=True,
            width=largura_dialogo(),
            min_lines=6,
            max_lines=10,
            hint_text="P  x  y\n(uma linha por ponto)",
            border_color=ft.Colors.BLUE_200,
            focused_border_color=ft.Colors.BLUE_700,
            border_radius=12,
            text_size=14,
        )
        erro = ft.Text("", color=ft.Colors.RED_800, size=14)

        def confirmar(e):
            try:
                pontos, ignoradas = importar_pontos_texto(campo.value or "")
            except ValueError as exc:
                erro.value = f"{exc}."
                page.update()
                return
            if not pontos:
                erro.value = "Nenhuma linha válida (esperado: P, x, y numéricos)."
                page.update()
                return
            page.pop_dialog()
            aplicar_importacao(pontos, ignoradas, "texto colado")

        page.show_dialog(
            ft.AlertDialog(
                bgcolor=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(
                    radius=12, side=ft.BorderSide(1.5, ft.Colors.BLUE_200)
                ),
                title=ft.Text(
                    "Colar texto", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800
                ),
                content=ft.Container(
                    width=largura_dialogo(),
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Uma linha por ponto, na ordem P (kPa), x\u2081, "
                                "y\u2081. Separador: espaço, tab, ; ou vírgula. "
                                "O cabeçalho é opcional.",
                                size=14,
                                color=ft.Colors.TEAL_900,
                            ),
                            campo,
                            erro,
                        ],
                        tight=True,
                        spacing=ESPACO_PEQUENO,
                    ),
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton("Importar", on_click=confirmar),
                ],
            )
        )

    def largura_dialogo():
        # No celular o diálogo tem margem lateral; 420px é o teto no desktop.
        return max(220, min(420, (page.width or 420) - 120))

    def opcao_dialogo(icone, texto, ao_clicar, largura=None):
        return ft.Button(
            content=ft.Row(
                controls=[ft.Icon(icone), ft.Text(texto, expand=True)],
                alignment=ft.MainAxisAlignment.START,
            ),
            on_click=ao_clicar,
            style=estilo_botao(),
            width=largura or largura_dialogo(),
        )

    def mostrar_dialogo_opcoes(titulo, opcoes):
        page.show_dialog(
            ft.AlertDialog(
                bgcolor=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(
                    radius=12, side=ft.BorderSide(1.5, ft.Colors.BLUE_200)
                ),
                title=ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                content=ft.Column(controls=opcoes, tight=True, spacing=ESPACO_MEDIO),
                actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog())],
            )
        )

    def abrir_importar(e):
        mostrar_dialogo_opcoes("Importar dados", [
            opcao_dialogo(ft.Icons.UPLOAD_FILE, "Arquivo CSV do dispositivo", importar_arquivo),
            opcao_dialogo(ft.Icons.CONTENT_PASTE, "Colar texto", abrir_colar_texto),
        ])

    # Botão "Exemplos" (2026-10-07, pedido do autor): os exemplos embutidos saíram
    # do diálogo "Importar dados" e ganharam botão próprio, ao lado dele.
    # O "?" de cada exemplo abre as limitações dele (2026-10-07, pedido do autor).
    def abrir_exemplos(e):
        def linha_exemplo(ex):
            return ft.Row(
                controls=[
                    opcao_dialogo(
                        ft.Icons.SCIENCE, ex["rotulo"], importar_exemplo(ex),
                        largura=largura_dialogo() - 44,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.HELP_OUTLINE,
                        icon_size=20,
                        icon_color=ft.Colors.BLUE_700,
                        padding=2,
                        tooltip="Limitações deste exemplo",
                        on_click=abrir_limitacoes_exemplo(ex),
                    ),
                ],
                spacing=4,
            )

        mostrar_dialogo_opcoes("Exemplos", [linha_exemplo(ex) for ex in EXEMPLOS_NIST])

    def abrir_limitacoes_exemplo(ex):
        def ao_clicar(e):
            page.pop_dialog()
            page.show_dialog(
                estilo_dialogo_ajuda(
                    "Limitações: " + ex["rotulo"],
                    ft.Container(width=largura_dialogo(), content=corpo_ajuda(ex["limitacoes"])),
                    [
                        ft.TextButton("Voltar aos exemplos", on_click=lambda e: (page.pop_dialog(), abrir_exemplos(e))),
                        ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog()),
                    ],
                    rolavel=True,
                )
            )
        return ao_clicar

    # Ajuda: lista de tópicos -> página do tópico, cada uma um diálogo novo
    # (a regra do app é não mutar controle já criado; mesmo padrão de "Colar
    # texto"). "Voltar" reabre a lista.
    def estilo_dialogo_ajuda(titulo, conteudo, acoes, rolavel=False):
        return ft.AlertDialog(
            scrollable=rolavel,
            bgcolor=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(
                radius=12, side=ft.BorderSide(1.5, ft.Colors.BLUE_200)
            ),
            title=ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
            content=conteudo,
            actions=acoes,
        )

    def corpo_ajuda(conteudo):
        # Texto do tópico em parágrafos (separados por linha em branco). Uma
        # linha que começa com "# " é um subtítulo: sai em negrito azul.
        if conteudo is None:
            return ft.Text("Conteúdo em breve.", size=14, color=ft.Colors.GREY_800, italic=True)
        blocos = []
        for paragrafo in conteudo.split("\n\n"):
            linhas = paragrafo.split("\n")
            if linhas[0].startswith("# "):
                blocos.append(
                    ft.Text(linhas[0][2:], size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)
                )
                linhas = linhas[1:]
            if linhas:
                blocos.append(ft.Text("\n".join(linhas), size=14, color=ft.Colors.TEAL_900))
        return ft.Column(controls=blocos, spacing=ESPACO_PEQUENO, tight=True)

    def mostrar_topico_ajuda(topico):
        page.show_dialog(
            estilo_dialogo_ajuda(
                topico["titulo"],
                ft.Container(width=largura_dialogo(), content=corpo_ajuda(topico["conteudo"])),
                [
                    ft.TextButton("Todos os tópicos", on_click=voltar_aos_topicos),
                    ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog()),
                ],
                rolavel=True,
            )
        )

    def abrir_topico_ajuda(topico):
        # Da lista de tópicos: fecha a lista e abre o tópico.
        def ao_clicar(e):
            page.pop_dialog()
            mostrar_topico_ajuda(topico)
        return ao_clicar

    def icone_ajuda_card(id_topico):
        # "?" no cabeçalho de um card: abre direto o tópico daquele card (sem
        # lista aberta por baixo); "Todos os tópicos" leva ao sumário.
        topico = next(t for t in AJUDA_TOPICOS if t["id"] == id_topico)
        return ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            icon_size=20,
            icon_color=ft.Colors.BLUE_700,
            padding=2,
            tooltip="Ajuda sobre este card",
            on_click=lambda e: mostrar_topico_ajuda(topico),
        )

    def mostrar_lista_ajuda():
        # Sem espaço sobrando quando a lista é curta; rola quando não cabe.
        altura = max(220, min(520, int((page.height or 700) * 0.6), 42 * len(AJUDA_TOPICOS) + 12))
        lista = ft.Column(
            controls=[
                opcao_dialogo(ft.Icons.ARTICLE_OUTLINED, t["titulo"], abrir_topico_ajuda(t))
                for t in AJUDA_TOPICOS
            ],
            spacing=ESPACO_PEQUENO,
            scroll=ft.ScrollMode.AUTO,
        )
        page.show_dialog(
            estilo_dialogo_ajuda(
                "Ajuda",
                ft.Container(width=largura_dialogo(), height=altura, content=lista),
                [ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog())],
            )
        )

    def abrir_ajuda(e):
        mostrar_lista_ajuda()

    def voltar_aos_topicos(e):
        page.pop_dialog()
        mostrar_lista_ajuda()

    botao_importar_csv = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.UPLOAD_FILE), ft.Text("Importar dados")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=abrir_importar,
        style=estilo_botao(),
    )

    botao_exemplos = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.SCIENCE), ft.Text("Exemplos")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=abrir_exemplos,
        style=estilo_botao(),
    )

    # 3c. Limpar tabela (2026-09-28, pedido do autor) — descarta todas as
    # linhas atuais (digitadas ou importadas) e volta ao estado inicial
    # (NUM_LINHAS_INICIAIS linhas em branco), sem precisar excluir linha por
    # linha manualmente.
    def limpar_tabela(e=None):
        dt.rows.clear()
        criar_linhas_iniciais()
        gerar_grafico(
            mensagem_extra=f"Tabela limpa — {NUM_LINHAS_INICIAIS} linha(s) em branco restaurada(s)."
        )

    # Botão com ícone e rótulo "Limpar dados" (2026-10-07, pedido do autor;
    # antes era só o ícone, a pedido dele em 2026-09-28 para caber ao lado do
    # "Comparar" no cabeçalho — o "Comparar" saiu dali para o card de
    # parâmetros, então sobrou espaço). Mesmo estilo dos demais botões
    # secundários. "Delete sweep" (vassoura+lixo) é o ícone Material padrão
    # para "limpar tudo".
    botao_limpar_tabela = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.DELETE_SWEEP), ft.Text("Limpar dados")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=limpar_tabela,
        style=estilo_botao(),
    )

    linha_botoes_tabela = ft.Row(
        controls=[botao_adicionar, botao_importar_csv, botao_exemplos], wrap=True
    )

    # Reavaliação leve de "Comparar"/"Limpar dados"/"Regressão" quando o
    # conteúdo da tabela não mudou (ver `ao_sair_do_campo`): só checa se
    # existe ponto válido, sem recalcular o modelo nem redesenhar os
    # gráficos. `botao_comparar` é definido
    # mais abaixo; resolvido por closure, sem problema (mesmo padrão já
    # usado em `aplicar_importacao`/`gerar_grafico`).
    # Dica ao tocar num botão apagado (2026-10-07, pedido do autor): botão
    # desabilitado não dispara `on_click`, então cada um vai dentro de um
    # GestureDetector (`caixa_*`, criados mais abaixo) cujo `on_tap` explica por
    # que está apagado. Botões de parâmetros mostram no `aviso_parametro` (dentro
    # do card, em laranja — vermelho é só erro); o "Limpar dados", na mensagem de
    # status do card "Dados experimentais". `dica_ativa["lugar"]` lembra onde
    # há dica para apagá-la quando o estado muda.
    COR_DICA = "#9A3B00"
    dica_ativa = {"lugar": None, "texto": ""}

    def esconder_dica():
        if dica_ativa["lugar"] == "parametros":
            aviso_parametro.visible = False
        elif dica_ativa["lugar"] == "status":
            # Só apaga se a mensagem ainda é a dica (outra ação pode já ter
            # escrito por cima).
            if mensagem_status.value == dica_ativa["texto"]:
                mensagem_status.value = ""
        dica_ativa["lugar"] = None

    def mostrar_dica(texto, lugar="parametros"):
        esconder_dica()
        if lugar == "parametros":
            aviso_parametro.value = texto
            aviso_parametro.color = COR_DICA
            aviso_parametro.visible = True
        else:
            mensagem_status.value = texto
            mensagem_status.color = COR_DICA
        dica_ativa["lugar"] = lugar
        dica_ativa["texto"] = texto
        page.update()

    def contar_pontos_validos():
        n = 0
        for linha in dt.rows:
            p_field, x_field, y_field = (linha.cells[i].content for i in range(3))
            try:
                parse_ponto(p_field.value, x_field.value, y_field.value)
                n += 1
            except ValueError:
                continue
        return n

    # "Calcular por Regressão" só acende quando a regressão pode rodar: o
    # modelo tem parâmetro ajustável (REGRESSAO_MODELOS — fora UNIFAC) e a
    # tabela tem o mínimo de pontos válidos (nº de parâmetros livres + 1,
    # seção 2.8 / decisão de 2026-09-13; o mesmo piso que `regress_params_
    # barker` exige). Pedido do autor, 2026-10-07: acesos só quando aplicável,
    # como o "Comparar".
    def regressao_aplicavel(n_pontos):
        nome = modelo_selecionado["nome"]
        # Na UI a regressão vale só para os modelos com slider (não UNIQUAC).
        spec = REGRESSAO_MODELOS.get(nome) if nome in PARAM_SLIDERS else None
        return spec is not None and n_pontos >= len(spec["livres"]) + 1

    def atualizar_habilitacao_botoes(n_pontos):
        # Uma dica de "por que está apagado" (ver `mostrar_dica`) fica velha
        # assim que a tabela muda — some junto com a reavaliação.
        if dica_ativa["lugar"] is not None:
            esconder_dica()
        botao_comparar.disabled = n_pontos == 0
        botao_limpar_tabela.disabled = n_pontos == 0
        botao_regressao.disabled = not regressao_aplicavel(n_pontos)

    def atualizar_estado_botoes_tabela():
        atualizar_habilitacao_botoes(contar_pontos_validos())
        page.update()

    # Redesenho automático (2026-10-08, pedido do autor: retirar o botão "Gerar
    # Gráfico" e automatizar). Os pontos da tabela entram nos gráficos quando o
    # campo perde o foco (ou Enter) **e o conteúdo da tabela mudou** desde o
    # último desenho: só entrar e sair de um campo não redesenha nem apaga a
    # comparação. A cada tecla só o `invalidar_comparacao` roda (barato). Ao
    # excluir uma linha, importar, limpar e trocar modelo/parâmetros o gráfico
    # já era redesenhado; agora também ao editar a tabela.
    ultima_assinatura = {"v": ()}
    comparacao_escondida = {"v": False}

    def assinatura_tabela():
        # Linhas com algum campo preenchido, na ordem; linhas em branco não
        # contam (adicionar/excluir linha em branco não muda o desenho).
        linhas = []
        for linha in dt.rows:
            campos = tuple((linha.cells[i].content.value or "").strip() for i in range(3))
            if any(campos):
                linhas.append(campos)
        return tuple(linhas)

    def ao_sair_do_campo(e=None):
        if assinatura_tabela() == ultima_assinatura["v"]:
            atualizar_estado_botoes_tabela()
            return
        esconder_dica()
        extra = None
        if comparacao_escondida["v"]:
            comparacao_escondida["v"] = False
            extra = (
                "Tabela editada: a comparação foi escondida. Clique em "
                "\"Comparar\" de novo."
            )
        gerar_grafico(mensagem_extra=extra)

    # 4. Gráfico P-x-y a partir dos dados brutos da tabela (Etapa 2 — sem
    # nenhum cálculo de modelo; só visualiza o que o usuário digitou).
    mensagem_status = ft.Text(value="", color=ft.Colors.RED_800)

    chart = fch.LineChart(
        data_series=[],
        min_x=0,
        max_x=1,
        min_y=0,
        max_y=1,
        expand=True,
        tooltip=novo_tooltip(),
        # Rótulos de eixo (2026-10-01): até aqui os dois gráficos mostravam
        # só números soltos, sem dizer o que era cada eixo — num material
        # didático, exatamente o que o aluno não decifra sozinho. O eixo
        # horizontal carrega as duas composições, porque a curva do líquido
        # é plotada contra x1 e a do vapor contra y1 no mesmo eixo.
        left_axis=fch.ChartAxis(
            label_size=40,
            title=ft.Text("P (kPa)", size=14, weight=ft.FontWeight.BOLD),
            title_size=22,
        ),
        # label_spacing fixa o intervalo entre marcações (0.2 em 0..1 = 6; era 0.1 = 11
        # rótulos). Sem isso, o eixo calculava um intervalo tão miúdo que
        # os rótulos apareciam repetidos e o gráfico pedia mais largura do
        # que cabia na tela (obrigando a diminuir o zoom do navegador).
        bottom_axis=fch.ChartAxis(
            label_size=32,
            label_spacing=0.2,
            title=ft.Text("x₁, y₁ (fração molar)", size=14, weight=ft.FontWeight.BOLD),
            title_size=22,
        ),
        visible=False,
    )

    # Legenda em GRADE (item 7 da lista de estética, opção B do autor,
    # 2026-10-03): linhas = a fase (ou o componente, no ln γ), colunas = a
    # origem do dado (tabela, modelo, comparativo). O símbolo de cada coluna é
    # o mesmo em todas as linhas — a grade ensina a regra "cor = fase, estilo
    # = origem" em vez de repeti-la em seis rótulos longos. Tem sempre
    # três linhas (cabeçalho + 2), em qualquer largura: a legenda de chips
    # que quebrava linha estourava a altura fixa e cobria o topo do eixo.
    # Larguras de coluna fixas, somando ~270px para caber no card do celular.
    ALTURA_CELULA_LEGENDA = 22

    def glifo_legenda(cor, forma):
        # O símbolo espelha o desenho da série: "circulo" e "quadrado"
        # (marcador cheio = tabela), "linha" (curva do modelo) e as variantes
        # "_vazado" (modelo calculado nos pontos da tabela, via "Comparar").
        if forma == "linha":
            return ft.Container(width=22, height=3, bgcolor=cor, border_radius=1)
        vazado = forma.endswith("_vazado")
        return ft.Container(
            width=12, height=12,
            bgcolor=None if vazado else cor,
            border=ft.Border.all(2, cor) if vazado else None,
            border_radius=2 if forma.startswith("quadrado") else 6,
        )

    def celula_legenda(controle):
        return ft.Container(
            content=controle, height=ALTURA_CELULA_LEGENDA, alignment=ft.Alignment.CENTER
        )

    def coluna_legenda(cabecalho, itens, largura):
        return ft.Column(
            controls=[
                celula_legenda(ft.Text(cabecalho, size=14, color=ft.Colors.BLUE_GREY_700)),
                *[celula_legenda(item) for item in itens],
            ],
            spacing=2,
            width=largura,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # Colunas da comparação calculado-vs-experimental (item 4 do roadmap):
    # só aparecem depois de "Comparar" ser clicado, e são escondidas de novo
    # sempre que gerar_grafico() reconstrói o gráfico do zero (modelo/tabela
    # mudou). Só o P-x-y tem coluna "Comparativo": no ln γ os marcadores
    # vazados caíam sobre a curva do modelo e não diziam nada (não há ln γ
    # experimental para comparar); retirados em 2026-10-08, pedido do autor.
    # Funções (e não objetos únicos) porque o diálogo "Ampliar" monta uma
    # legenda própria — um controle não pode ter dois pais.
    def nova_coluna_comparativo_pxy():
        return coluna_legenda(
            "Comparativo",
            [glifo_legenda(COR_LIQUIDO, "quadrado_vazado"), glifo_legenda(COR_VAPOR, "circulo_vazado")],
            84,
        )

    coluna_comparativo_pxy = nova_coluna_comparativo_pxy()
    coluna_comparativo_pxy.visible = False

    # Resultado numérico da comparação (ΔP/Δy, seção "Próximos passos" item
    # 4 do CLAUDE.md) — mesmo padrão selo+ícone ⓘ já usado para a origem do
    # parâmetro: valor sempre visível, explicação do que cada Δ significa
    # só aparece ao tocar no ícone (diálogo — ver icone_info), sem poluir a
    # tela com texto fixo.
    texto_dp_comparativo = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    icone_dp_comparativo = icone_info(
        lambda: (
            "ΔP (RMS): erro relativo médio entre a pressão calculada pelo "
            "modelo e a pressão experimental digitada, ponto a ponto."
        ),
        titulo="O que é ΔP?",
    )
    texto_dy_comparativo = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    icone_dy_comparativo = icone_info(
        lambda: (
            "Δy (RMS): erro absoluto médio entre a fração molar de vapor "
            "(y) calculada pelo modelo e a experimental digitada, ponto a "
            "ponto."
        ),
        titulo="O que é Δy?",
    )
    linha_erro_comparativo = ft.Row(
        controls=[
            ft.Row([texto_dp_comparativo, icone_dp_comparativo], spacing=4, tight=True),
            ft.Row([texto_dy_comparativo, icone_dy_comparativo], spacing=4, tight=True),
        ],
        spacing=20,
        # `wrap=True`: no celular (~296px úteis) "ΔP = 90.41% (RMS) ⓘ" e
        # "Δy = 0.0704 (RMS) ⓘ" juntos passavam da borda direita do card;
        # com a quebra, o segundo vai para a linha de baixo.
        wrap=True,
        run_spacing=4,
        visible=False,
    )

    def montar_legenda_pxy(coluna_comparativo):
        return ft.Row(
            controls=[
                coluna_legenda(
                    "",
                    [ft.Text("Líquido", size=14), ft.Text("Vapor", size=14)],
                    56,
                ),
                coluna_legenda(
                    "Tabela",
                    [glifo_legenda(COR_LIQUIDO, "quadrado"), glifo_legenda(COR_VAPOR, "circulo")],
                    60,
                ),
                coluna_legenda(
                    "Modelo",
                    [glifo_legenda(COR_LIQUIDO, "linha"), glifo_legenda(COR_VAPOR, "linha")],
                    60,
                ),
                coluna_comparativo,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4,
        )

    legenda = montar_legenda_pxy(coluna_comparativo_pxy)
    legenda.visible = False

    # 4b. Segundo gráfico: ln γ vs x1 (seção 2.2 do mapeamento) — a curva do
    # modelo na malha genérica de 101 pontos e, desde 2026-10-08 (pedido do
    # autor, faixa 0,10 a 0,90), o ln γ "experimental" dos pontos da tabela
    # como marcadores cheios, pelo método indireto (`ln_gamma_experimental`).
    # O método indireto continua descartado para a REGRESSÃO (seção 2.8: usa
    # Barker); aqui é só exibição, por isso a faixa restrita. "Comparar" não
    # mexe neste gráfico.
    chart_gamma = fch.LineChart(
        data_series=[],
        min_x=0,
        max_x=1,
        min_y=0,
        max_y=1,
        expand=True,
        tooltip=novo_tooltip(),
        left_axis=fch.ChartAxis(
            label_size=40,
            title=ft.Text("ln γ", size=14, weight=ft.FontWeight.BOLD),
            title_size=22,
        ),
        bottom_axis=fch.ChartAxis(
            label_size=32,
            label_spacing=0.2,
            title=ft.Text("x₁ (fração molar)", size=14, weight=ft.FontWeight.BOLD),
            title_size=22,
        ),
        visible=False,
    )

    def montar_legenda_gamma():
        return ft.Row(
            controls=[
                coluna_legenda(
                    "",
                    [ft.Text("ln γ₁", size=14), ft.Text("ln γ₂", size=14)],
                    56,
                ),
                coluna_legenda(
                    "Tabela",
                    [glifo_legenda(COR_GAMMA1, "circulo"), glifo_legenda(COR_GAMMA2, "circulo")],
                    60,
                ),
                coluna_legenda(
                    "Modelo",
                    [glifo_legenda(COR_GAMMA1, "linha"), glifo_legenda(COR_GAMMA2, "linha")],
                    60,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4,
        )

    legenda_gamma = montar_legenda_gamma()
    legenda_gamma.visible = False

    # Lupa do card (2026-10-03, opção A do autor, só no desktop): abre o
    # gráfico ampliado num diálogo. O Flet 1.0.0 não tem zoom/pan no gráfico
    # de linhas, então não é zoom de região — é o mesmo gráfico em tamanho
    # grande. O diálogo monta um gráfico NOVO (cópia das séries, mesmo
    # tooltip, eixos e legenda novos), porque um controle não pode estar em
    # dois lugares. Os botões são criados uma vez e reaproveitados entre as
    # montagens de layout (como `botao_comparar`); ficam apagados até haver
    # gráfico (`gerar_grafico` os acende).
    def ampliar_grafico(titulo, grafico, legenda_nova, titulo_eixo_x, titulo_eixo_y, largura_rotulo_y):
        largura = min((page.width or 1200) * 0.92, 1300)
        altura = min((page.height or 800) * 0.88, 820)
        # Reserva: título do diálogo + legenda (72) + folgas.
        altura_grafico = max(altura - 72 - 130, 260)
        grande = fch.LineChart(
            data_series=clonar_series(grafico.data_series),
            min_x=0,
            max_x=1,
            min_y=grafico.min_y,
            max_y=grafico.max_y,
            expand=True,
            tooltip=novo_tooltip(),
            left_axis=eixo_vertical(
                titulo_eixo_y,
                grafico.left_axis.label_spacing,
                largura_rotulo_y,
                grafico.min_y,
                grafico.max_y,
            ),
            # Mais largo = cabe o passo de 0,1 sem os rótulos se encostarem.
            bottom_axis=fch.ChartAxis(
                label_size=32,
                label_spacing=0.1,
                title=ft.Text(titulo_eixo_x, size=14, weight=ft.FontWeight.BOLD),
                title_size=22,
            ),
        )
        page.show_dialog(
            ft.AlertDialog(
                bgcolor=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(
                    radius=12, side=ft.BorderSide(1.5, ft.Colors.BLUE_200)
                ),
                title=ft.Row(
                    controls=[
                        ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=ft.Colors.BLUE_800,
                            tooltip="Fechar",
                            on_click=lambda e: page.pop_dialog(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                # Altura explícita: sem ela o diálogo ficava ~175px mais alto
                # que o conteúdo, com faixa branca embaixo.
                content=ft.Container(
                    width=largura,
                    height=72 + altura_grafico + ESPACO_PEQUENO,
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                content=legenda_nova,
                                height=72,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Container(content=grande, height=altura_grafico),
                        ],
                        spacing=ESPACO_PEQUENO,
                        tight=True,
                    ),
                ),
            )
        )

    def ampliar_pxy(e=None):
        coluna = nova_coluna_comparativo_pxy()
        coluna.visible = coluna_comparativo_pxy.visible
        ampliar_grafico(
            "Diagrama P-x-y", chart, montar_legenda_pxy(coluna),
            "x₁, y₁ (fração molar)", "P (kPa)", 40,
        )

    def ampliar_gamma(e=None):
        ampliar_grafico(
            "Coeficientes de atividade (ln γ)", chart_gamma, montar_legenda_gamma(),
            "x₁ (fração molar)", "ln γ", 52,
        )

    def nova_lupa(ao_clicar):
        return ft.IconButton(
            icon=ft.Icons.ZOOM_IN,
            icon_size=22,
            icon_color=ft.Colors.BLUE_800,
            padding=4,
            tooltip="Ampliar gráfico",
            on_click=ao_clicar,
            disabled=True,
        )

    botao_lupa_pxy = nova_lupa(ampliar_pxy)
    botao_lupa_gamma = nova_lupa(ampliar_gamma)

    # Ponta a ponta: pontos digitados na tabela (discretos, sem interpolação —
    # decisão de 2026-08-19) + curva calculada por calculate_vle_isothermal
    # com o modelo/parâmetros/componentes/temperatura escolhidos, no mesmo
    # gráfico. Para Margules/Van Laar/Wilson/NRTL os parâmetros vêm dos
    # sliders (parametros_atuais); para UNIQUAC/UNIFAC vêm de
    # montar_parametros_automaticos, resolvido a partir dos componentes.
    def gerar_grafico(e=None, mensagem_extra=None, atualizar_pagina=True):
        ultima_assinatura["v"] = assinatura_tabela()
        pontos_validos = []
        linhas_ignoradas = 0
        for linha in dt.rows:
            p_field, x_field, y_field = (linha.cells[i].content for i in range(3))
            try:
                pontos_validos.append(
                    parse_ponto(p_field.value, x_field.value, y_field.value)
                )
            except ValueError:
                # Só conta como "dado inválido" a linha com os 3 campos
                # preenchidos que não viram número (ex.: "-", "1.2.3"). Linha
                # em branco é espaço reservado da tabela (ela nasce com
                # NUM_LINHAS_INICIAIS linhas em branco; antes a tabela vazia
                # mostrava "10 linha(s) ... ignorada(s)", 2026-10-01) e linha
                # incompleta é um ponto ainda sendo digitado: desde que o
                # gráfico se atualiza ao sair de cada campo (2026-10-08), avisar
                # a cada Tab pelo meio de uma linha seria só ruído.
                if all((campo.value or "").strip() for campo in (p_field, x_field, y_field)):
                    linhas_ignoradas += 1

        # "Comparar" só faz sentido havendo dado experimental de verdade na
        # tabela para comparar contra — desabilitado sem isso (item 4 do
        # roadmap). Reconstruir o gráfico do zero também descarta qualquer
        # comparação calculada antes, pra não sobrar uma curva comparativa
        # desatualizada em relação ao modelo/tabela atual.
        botao_comparar.disabled = not pontos_validos
        botao_regressao.disabled = not regressao_aplicavel(len(pontos_validos))
        # "Limpar Tabela" fica apagado sem dado nenhum pra apagar — mesmo
        # critério do "Comparar" (pontos_validos), pedido do autor,
        # 2026-09-28. O clique apaga qualquer dado presente, digitado à mão
        # ou importado via CSV — `limpar_tabela` não distingue a origem.
        botao_limpar_tabela.disabled = not pontos_validos
        coluna_comparativo_pxy.visible = False
        linha_erro_comparativo.visible = False
        comparativo_ativo["ativo"] = False

        series = []
        series_gamma = []
        valores_P = []
        valores_gamma = []
        modelo_ok = False

        if pontos_validos:
            liquido, vapor = pontos_para_series(pontos_validos)
            # Dado experimental é ponto, modelo é linha (decisão de
            # 2026-08-19; forma escolhida pelo autor em 2026-10-03, opção C):
            # `stroke_width=0` esconde a linha e `point=` desenha só o
            # marcador. Formas diferentes (quadrado = líquido, círculo =
            # vapor) para as fases se distinguirem sem depender só da cor —
            # projeção em sala, impressão em preto e branco.
            series.append(fch.LineChartData(
                color=COR_LIQUIDO,
                stroke_width=0,
                point=fch.ChartSquarePoint(size=8, color=COR_LIQUIDO, stroke_width=0),
                points=[
                    ponto_grafico(x, p, "x₁", "P", "kPa", negrito=False)
                    for x, p in liquido
                ],
            ))
            series.append(fch.LineChartData(
                color=COR_VAPOR,
                stroke_width=0,
                point=fch.ChartCirclePoint(radius=4.5, color=COR_VAPOR, stroke_width=0),
                points=[
                    ponto_grafico(x, p, "y₁", "P", "kPa", negrito=False)
                    for x, p in vapor
                ],
            ))
            valores_P += [p for _, p in liquido] + [p for _, p in vapor]

        erro_modelo = None
        aviso_critica = None
        aviso_instabilidade = None
        revalidar_selo_ao_mudar_sistema()
        try:
            nome_modelo = modelo_selecionado["nome"]
            comp1 = campo_componente1.value.strip()
            comp2 = campo_componente2.value.strip()
            if nome_modelo in PARAM_SLIDERS:
                params_modelo = dict(parametros_atuais)
            else:
                params_modelo = montar_parametros_automaticos(nome_modelo, comp1, comp2)
                if nome_modelo == "UNIQUAC":
                    atualizar_selo_uniquac(comp1, comp2)

            T_C = float(campo_temperatura.value)
            resultado = calculate_vle_isothermal(
                comp1, comp2, T_C, nome_modelo, params_modelo,
            )
            liquido_calc = sorted(zip(resultado["x1"], resultado["P_kPa"]))
            vapor_calc = sorted(zip(resultado["y1"], resultado["P_kPa"]))
            series.append(fch.LineChartData(
                color=COR_LIQUIDO,
                stroke_width=2,
                points=[ponto_grafico(x, p, "x₁", "P", "kPa") for x, p in liquido_calc],
            ))
            series.append(fch.LineChartData(
                color=COR_VAPOR,
                stroke_width=2,
                points=[ponto_grafico(y, p, "y₁", "P", "kPa") for y, p in vapor_calc],
            ))
            valores_P += resultado["P_kPa"]

            ln_gamma1 = [math.log(g) for g in resultado["gamma1"]]
            ln_gamma2 = [math.log(g) for g in resultado["gamma2"]]
            series_gamma.append(fch.LineChartData(
                color=COR_GAMMA1,
                stroke_width=2,
                points=[ponto_grafico(x, g, "x₁", "ln γ₁") for x, g in zip(resultado["x1"], ln_gamma1)],
            ))
            series_gamma.append(fch.LineChartData(
                color=COR_GAMMA2,
                stroke_width=2,
                points=[ponto_grafico(x, g, "x₁", "ln γ₂") for x, g in zip(resultado["x1"], ln_gamma2)],
            ))
            valores_gamma += ln_gamma1 + ln_gamma2
            # ln γ "experimental" dos pontos da tabela (método indireto, só
            # 0,10 ≤ x₁ ≤ 0,90 — ver `ln_gamma_experimental`): marcadores
            # cheios, mesma regra do P-x-y (cheio = tabela). Depois das curvas
            # para ficarem por cima delas. Círculo nos dois componentes: aqui
            # quem distingue é a cor (γ₁ verde, γ₂ roxo), não a forma.
            if pontos_validos:
                exp_gamma = ln_gamma_experimental(pontos_validos, comp1, comp2, T_C)
                if exp_gamma:
                    series_gamma.append(fch.LineChartData(
                        color=COR_GAMMA1,
                        stroke_width=0,
                        point=fch.ChartCirclePoint(radius=4.5, color=COR_GAMMA1, stroke_width=0),
                        points=[ponto_grafico(x, g1, "x₁", "ln γ₁", negrito=False) for x, g1, _ in exp_gamma],
                    ))
                    series_gamma.append(fch.LineChartData(
                        color=COR_GAMMA2,
                        stroke_width=0,
                        point=fch.ChartCirclePoint(radius=4.5, color=COR_GAMMA2, stroke_width=0),
                        points=[ponto_grafico(x, g2, "x₁", "ln γ₂", negrito=False) for x, _, g2 in exp_gamma],
                    ))
                    valores_gamma += [g for _, g1, g2 in exp_gamma for g in (g1, g2)]
            modelo_ok = True
            aviso_critica = aviso_temperatura_critica(
                comp1, comp2, T_C, resultado.get("Tc_C", [])
            )
            aviso_instabilidade = aviso_instabilidade_liquida(
                resultado["x1"], resultado["gamma1"]
            )
        except Exception as exc:
            erro_modelo = str(exc)

        if not series:
            aviso_instabilidade_txt.visible = False
            chart.visible = False
            legenda.visible = False
            chart_gamma.visible = False
            legenda_gamma.visible = False
            motivo = (
                f" ({erro_modelo})" if erro_modelo else ""
            )
            prefixo = f"{mensagem_extra} " if mensagem_extra else ""
            mensagem_status.value = (
                f"{prefixo}Adicione ao menos um ponto válido na tabela, ou "
                f"corrija os campos de componente/temperatura{motivo}, para "
                "gerar o gráfico."
            )
            mensagem_status.color = ft.Colors.RED_800
            if atualizar_pagina:
                page.update()
            return

        chart.data_series = series
        min_y, max_y = min(valores_P), max(valores_P)
        if min_y == max_y:
            min_y, max_y = min_y - 1, max_y + 1
        margem = (max_y - min_y) * 0.05
        inicio_y, fim_y, passo_y = limites_redondos(min_y - margem, max_y + margem)
        chart.min_y, chart.max_y = margem_extremos(inicio_y, fim_y, passo_y)
        chart.left_axis = eixo_vertical("P (kPa)", passo_y, 40, chart.min_y, chart.max_y)
        chart.visible = True
        legenda.visible = True
        botao_lupa_pxy.disabled = False

        if modelo_ok:
            chart_gamma.data_series = series_gamma
            min_g, max_g = min(valores_gamma), max(valores_gamma)
            if min_g == max_g:
                min_g, max_g = min_g - 1, max_g + 1
            margem_g = (max_g - min_g) * 0.05
            inicio_g, fim_g, passo_g = limites_redondos(
                min_g - margem_g, max_g + margem_g
            )
            chart_gamma.min_y, chart_gamma.max_y = margem_extremos(inicio_g, fim_g, passo_g)
            chart_gamma.left_axis = eixo_vertical(
                "ln γ", passo_g, 52, chart_gamma.min_y, chart_gamma.max_y
            )
            chart_gamma.visible = True
            legenda_gamma.visible = True
            botao_lupa_gamma.disabled = False
        else:
            chart_gamma.visible = False
            legenda_gamma.visible = False
            botao_lupa_gamma.disabled = True

        mensagens = []
        if mensagem_extra:
            mensagens.append(mensagem_extra)
        if linhas_ignoradas:
            mensagens.append(f"{linhas_ignoradas} linha(s) da tabela ignorada(s) por dado inválido.")
        if erro_modelo:
            mensagens.append(f"Curva do modelo não calculada: {erro_modelo}.")
        if aviso_critica:
            mensagens.append(aviso_critica)
        mensagem_status.value = " ".join(mensagens)
        mensagem_status.color = "#9A3B00" if mensagens else ""
        aviso_instabilidade_txt.value = aviso_instabilidade or ""
        aviso_instabilidade_txt.visible = bool(aviso_instabilidade)

        # `atualizar_pagina=False` só na carga inicial da página (ver
        # montar_layout/main) — junta o que seria 2 `page.update()`
        # seguidos (um daqui, um do montar_layout) num só, evitando
        # disparar duas atualizações em sequência rápida logo na
        # inicialização (suspeito do bug intermitente relatado pelo
        # autor, 2026-09-28 — a página já chegava quebrada, sem precisar
        # de nenhuma interação).
        if atualizar_pagina:
            page.update()

    # 4c. Comparação calculado-vs-experimental (item 4 do roadmap) — só a
    # parte visual por enquanto (autorizado em 2026-09-27: "implementar o
    # botão para visualizar... e depois adicionar a parte do erro"). Avalia
    # o modelo exatamente nos x1 da tabela (não na malha genérica de 101
    # pontos usada por gerar_grafico), pra sobrepor calculado e experimental
    # no mesmo gráfico. O número de erro em si (métrica ainda não definida
    # — depende de orientação do Dr. Filipe) fica para depois.
    # A comparação mostrada vale para a tabela e os parâmetros do momento do
    # clique. Se a tabela é editada, ela é escondida (opção (a) do autor,
    # 2026-10-07; antes ficava na tela defasada). Remove as
    # 2 séries que `calcular_comparativo` acrescentou a cada gráfico, esconde as
    # colunas "Comparativo" das legendas e a linha ΔP/Δy. Só age se há
    # comparação (barato: roda a cada tecla).
    comparativo_ativo = {"ativo": False}

    def invalidar_comparacao():
        if not comparativo_ativo["ativo"]:
            return
        comparativo_ativo["ativo"] = False
        comparacao_escondida["v"] = True
        chart.data_series = chart.data_series[:-2]
        coluna_comparativo_pxy.visible = False
        linha_erro_comparativo.visible = False
        mensagem_status.value = (
            "Tabela editada: a comparação foi escondida. Clique em \"Comparar\" "
            "de novo."
        )
        mensagem_status.color = COR_DICA
        page.update()

    def calcular_comparativo(e=None):
        pontos_validos = []
        for linha in dt.rows:
            p_field, x_field, y_field = (linha.cells[i].content for i in range(3))
            try:
                pontos_validos.append(
                    parse_ponto(p_field.value, x_field.value, y_field.value)
                )
            except ValueError:
                pass

        if not pontos_validos:
            return  # botão deveria estar desabilitado; guarda defensiva

        x1_lista = sorted({x1 for _, x1, _ in pontos_validos})

        try:
            nome_modelo = modelo_selecionado["nome"]
            comp1 = campo_componente1.value.strip()
            comp2 = campo_componente2.value.strip()
            if nome_modelo in PARAM_SLIDERS:
                params_modelo = dict(parametros_atuais)
            else:
                params_modelo = montar_parametros_automaticos(nome_modelo, comp1, comp2)

            T_C = float(campo_temperatura.value)
            resultado = calculate_vle_isothermal(
                comp1, comp2, T_C, nome_modelo, params_modelo, x1_values=x1_lista,
            )
        except Exception as exc:
            mensagem_status.value = f"Comparação não calculada: {exc}."
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return

        # Clicar "Comparar" de novo não pode empilhar séries repetidas: tira a
        # comparação anterior antes de acrescentar a nova.
        if comparativo_ativo["ativo"]:
            chart.data_series = chart.data_series[:-2]
            comparativo_ativo["ativo"] = False

        liquido_comp = sorted(zip(resultado["x1"], resultado["P_kPa"]))
        vapor_comp = sorted(zip(resultado["y1"], resultado["P_kPa"]))

        chart.data_series = chart.data_series + [
            fch.LineChartData(
                color=COR_LIQUIDO,
                stroke_width=0,
                point=marcador_vazado("quadrado", COR_LIQUIDO),
                points=[ponto_grafico(x, p, "x₁", "P", "kPa", negrito=False) for x, p in liquido_comp],
            ),
            fch.LineChartData(
                color=COR_VAPOR,
                stroke_width=0,
                point=marcador_vazado("circulo", COR_VAPOR),
                points=[ponto_grafico(y, p, "y₁", "P", "kPa", negrito=False) for y, p in vapor_comp],
            ),
        ]
        coluna_comparativo_pxy.visible = True


        # Erro do ajuste: ΔP relativo (%) e Δy absoluto (fração molar),
        # cada um como RMS — mesma convenção de `regress_params_barker`
        # (resíduo ΔP relativo + Δy absoluto), mas reportados separados,
        # não combinados num resíduo só, porque cada um testa uma parte
        # diferente da física (P testa o desvio da idealidade como um
        # todo; y é mais sensível a erro em componente individual) e é
        # assim que ajuste de modelo Gᴱ é reportado na literatura (ex.:
        # compilações DECHEMA/Gmehling). ΔP em relativo é seguro (P nunca
        # passa perto de zero); Δy tem que ser absoluto, não relativo —
        # relativo em y sofreria a mesma amplificação de ruído perto das
        # bordas de composição (x1→0/1) que já descartou o método
        # indireto na seção 2.8. Autorizado pelo autor em 2026-09-27,
        # sem aguardar orientação do Dr. Filipe — decisão registrada e
        # justificada em CLAUDE.md.
        calc_por_x1 = dict(zip(resultado["x1"], zip(resultado["P_kPa"], resultado["y1"])))
        soma_dp_rel2 = 0.0
        soma_dy_abs2 = 0.0
        # Maior desvio de cada grandeza e em que x₁ ocorre (2026-10-08, pedido
        # do autor: mensagem "mais conclusiva"): diz onde o modelo mais se
        # afasta, o que o RMS sozinho esconde.
        pior_dp = (0.0, None)
        pior_dy = (0.0, None)
        for p_exp, x1, y_exp in pontos_validos:
            P_calc, y_calc = calc_por_x1[x1]
            desvio_p = abs(P_calc - p_exp) / p_exp
            desvio_y = abs(y_calc - y_exp)
            soma_dp_rel2 += desvio_p ** 2
            soma_dy_abs2 += desvio_y ** 2
            if pior_dp[1] is None or desvio_p > pior_dp[0]:
                pior_dp = (desvio_p, x1)
            if pior_dy[1] is None or desvio_y > pior_dy[0]:
                pior_dy = (desvio_y, x1)
        dp_rms_pct = math.sqrt(soma_dp_rel2 / len(pontos_validos)) * 100
        dy_rms = math.sqrt(soma_dy_abs2 / len(pontos_validos))

        texto_dp_comparativo.value = f"ΔP = {dp_rms_pct:.2f}% (RMS)"
        texto_dy_comparativo.value = f"Δy = {dy_rms:.4f} (RMS)"
        linha_erro_comparativo.visible = True
        comparativo_ativo["ativo"] = True

        mensagem_status.value = (
            f"Comparação feita com {len(pontos_validos)} ponto(s) da tabela. "
            f"Maior desvio de pressão: {pior_dp[0] * 100:.2f}% em x₁ = {pior_dp[1]:g}. "
            f"Maior desvio de y₁: {pior_dy[0]:.4f} em x₁ = {pior_dy[1]:g}."
        )
        mensagem_status.color = ""
        page.update()

    botao_comparar = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.COMPARE_ARROWS), ft.Text("Comparar")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=calcular_comparativo,
        disabled=True,
        style=estilo_botao(),
    )

    # 5. Dropdown de seleção do modelo Gᴱ — troca o modelo e já recalcula
    # a curva (gerar_grafico) com os parâmetros do novo modelo.
    modelo_selecionado = {"nome": next(iter(MODELS_GE))}

    def selecionar_modelo(e):
        modelo_selecionado["nome"] = e.control.value
        construir_sliders(modelo_selecionado["nome"])
        gerar_grafico()

    # Largura única dos 4 controles do card "Sistema" (dropdown de modelo,
    # dois componentes e temperatura) — ver a grade 2×2 logo abaixo.
    LARGURA_CAMPO_SISTEMA = 200

    # Estilo das caixas do card "Sistema" (pedido do autor, 2026-10-03: "está
    # muito simples"): fundo branco sobre o cartão cinza-azulado, borda azul
    # clara que fica azul forte e mais grossa ao focar, cantos arredondados,
    # rótulo em azul escuro negrito, texto escuro com peso médio e um ícone
    # azul na frente de cada campo. Só cores já usadas no app. Tudo definido
    # na criação — nada é alterado depois (regra de 2026-09-28).
    ESTILO_CAIXA_SISTEMA = dict(
        filled=True,
        fill_color=ft.Colors.WHITE,
        border_radius=12,
        border_width=1.5,
        border_color=ft.Colors.BLUE_200,
        focused_border_width=2.5,
        focused_border_color=ft.Colors.BLUE_700,
        label_style=ft.TextStyle(color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD),
        text_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_500),
        content_padding=ft.Padding(8, 14, 8, 14),
    )

    dropdown_modelo = ft.Dropdown(
        # "Gᴱ" (small capital E) some fontes/navegadores não têm o glifo —
        # visto em sessão real no Samsung Browser (2026-09-27): o rótulo
        # aparecia cortado como só "Modelo G". Texto simples renderiza
        # em qualquer fonte.
        label="Modelo GE",
        value=modelo_selecionado["nome"],
        # Texto exibido sem parênteses ("Margules 1-P"), só na tela: a chave
        # continua sendo o nome de MODELS_GE. Com os parênteses, "Margules
        # (1-P)" saía cortado no celular do autor (2026-10-06) por uns poucos
        # pixels entre o ícone e a seta; ajustar o recuo interno do campo não
        # teve efeito no Dropdown.
        options=[
            ft.dropdown.Option(key=nome, text=nome.replace(" (", " ").replace(")", ""))
            for nome in MODELS_GE
        ],
        on_select=selecionar_modelo,
        width=LARGURA_CAMPO_SISTEMA,
        leading_icon=ft.Icon(ft.Icons.FUNCTIONS, color=ft.Colors.BLUE_700),
        # 14px (os outros campos usam 16): com ícone na frente e seta atrás,
        # o nome "Margules (1-P)" não cabia nos 200px a 16px e era cortado.
        text_size=14,
        **ESTILO_CAIXA_SISTEMA,
    )

    # 5b. Seletores de componente (nome/sinônimo/CAS — resolvidos pelo
    # thermo.Chemical dentro de calculate_vle_isothermal) e temperatura do
    # sistema. Recalculam a curva ao sair do campo (on_blur/on_submit) —
    # não a cada tecla, para não repetir Chemical() com nome incompleto.
    # Largura fixa, sempre (a mesma nos dois modos — mutar `width` de
    # controle já criado foi o gatilho do bug de renderização de
    # 2026-09-28, ver montar_layout). Grade 2×2 (2026-10-03, pedido do
    # autor): com 220px, dois campos lado a lado (~452px) não cabiam no
    # card "Sistema" do desktop (~400-450px úteis, já que ele divide a
    # linha com "Parâmetros do modelo"), então cada um caía numa linha
    # própria — o dropdown à esquerda e os campos centralizados, num
    # degrau sem harmonia. Com 190px, dois campos + espaçamento (392px)
    # cabem; no celular, onde não cabem dois, `wrap=True` empilha um por
    # linha, agora todos alinhados à esquerda.
    campo_componente1 = ft.TextField(
        label="Componente 1", value="ethanol", width=LARGURA_CAMPO_SISTEMA,
        prefix_icon=ft.Icon(ft.Icons.SCIENCE, color=ft.Colors.BLUE_700),
        on_blur=gerar_grafico, on_submit=gerar_grafico,
        **ESTILO_CAIXA_SISTEMA,
    )
    campo_componente2 = ft.TextField(
        label="Componente 2", value="water", width=LARGURA_CAMPO_SISTEMA,
        prefix_icon=ft.Icon(ft.Icons.SCIENCE_OUTLINED, color=ft.Colors.BLUE_700),
        on_blur=gerar_grafico, on_submit=gerar_grafico,
        **ESTILO_CAIXA_SISTEMA,
    )
    campo_temperatura = ft.TextField(
        label="Temperatura (°C)",
        value="70",
        width=LARGURA_CAMPO_SISTEMA,
        prefix_icon=ft.Icon(ft.Icons.THERMOSTAT, color=ft.Colors.BLUE_700),
        keyboard_type=ft.KeyboardType.NUMBER,
        on_blur=gerar_grafico,
        on_submit=gerar_grafico,
        **ESTILO_CAIXA_SISTEMA,
    )
    # `wrap=True` (mesmo padrão já usado nas linhas de botões do app): sem
    # quebra, campos de largura fixa ultrapassavam a borda da tela de um
    # celular em retrato (~340-370px) — bug relatado pelo autor,
    # 2026-09-28. Duas linhas fixas: componentes em cima, modelo e
    # temperatura embaixo.
    linha_componentes = ft.Row(
        controls=[campo_componente1, campo_componente2],
        spacing=12,
        wrap=True,
    )
    linha_modelo_temperatura = ft.Row(
        controls=[dropdown_modelo, campo_temperatura],
        spacing=12,
        wrap=True,
    )

    # 6. Sliders dos parâmetros do modelo escolhido — guardam os valores
    # atuais em parametros_atuais; soltar o slider (on_change_end) já
    # recalcula a curva via gerar_grafico.
    parametros_atuais = {}
    sliders_area = ft.Column(spacing=2)
    # Guarda (slider, texto_valor, rótulo) por chave de parâmetro do modelo
    # atual, para o botão de regressão/busca no banco poder atualizar os
    # sliders depois de calcular — reconstruído a cada troca de modelo,
    # junto com os sliders.
    sliders_por_chave = {}

    # 6a. Selo de origem do parâmetro (seção 2.8 do mapeamento) — pequeno,
    # colorido, sempre visível junto dos sliders, com ícone ⓘ que mostra o
    # detalhe (o que foi assumido, de onde veio) num diálogo ao toque (ver
    # icone_info). Cobre o conjunto de parâmetros livres do modelo atual
    # como um todo: busca no banco e regressão atualizam todos de uma vez,
    # e mexer em qualquer slider manualmente já invalida a origem
    # "banco"/"calculado" anterior.
    texto_selo_origem = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    chip_selo_origem = ft.Container(
        content=texto_selo_origem,
        padding=ft.Padding(8, 2, 8, 2),
        border_radius=10,
    )
    # Estado mutável lido por icone_selo_origem no momento do toque — não dá
    # para fechar o texto no clique do ícone como nas explicações fixas
    # (ΔP/Δy) porque este detalhe muda em tempo real (atualizar_selo_origem).
    # Guarda também o `tipo` (não só o `texto`): `revalidar_selo_ao_mudar_
    # sistema` precisa saber de que origem era o selo.
    detalhe_selo_origem = {"tipo": None, "texto": ""}
    icone_selo_origem = icone_info(
        lambda: detalhe_selo_origem["texto"],
        titulo="Origem deste parâmetro",
    )
    selo_origem = ft.Row(
        controls=[chip_selo_origem, icone_selo_origem],
        spacing=4,
        # `tight` (definido na criação): sem ele a Row ocupa a largura toda e
        # o selo não fica colado ao título do card.
        tight=True,
        visible=False,
    )

    def chave_sistema():
        # Componentes (texto) e temperatura (número, para "70" == "70.0").
        try:
            T = float(campo_temperatura.value)
        except (TypeError, ValueError):
            T = (campo_temperatura.value or "").strip()
        return (campo_componente1.value.strip(), campo_componente2.value.strip(), T)

    # Sistema (componentes e T) em que o selo atual foi definido (2026-10-07):
    # valores de banco/regressão valem só para aquele sistema.
    sistema_do_selo = {"chave": None}

    def atualizar_selo_origem(tipo, detalhe):
        sistema_do_selo["chave"] = chave_sistema()
        bg, fg, rotulo = ORIGENS_SELO[tipo]
        chip_selo_origem.bgcolor = bg
        texto_selo_origem.value = rotulo
        texto_selo_origem.color = fg
        detalhe_selo_origem["tipo"] = tipo
        detalhe_selo_origem["texto"] = detalhe
        selo_origem.visible = True

    def revalidar_selo_ao_mudar_sistema():
        # Trocar componentes ou temperatura não recalcula os parâmetros. Se o
        # selo diz "Banco de dados"/"Calculado" para o sistema anterior, o
        # valor deixou de ter essa origem para o sistema atual: o selo volta a
        # "Fornecido" e o ⓘ explica (autor, 2026-10-07). Só modelos com slider;
        # UNIQUAC/UNIFAC recalculam a cada gráfico.
        if modelo_selecionado["nome"] not in PARAM_SLIDERS:
            return
        if detalhe_selo_origem["tipo"] not in ("banco", "calculado", "calculado_poucos_pontos"):
            return
        anterior = sistema_do_selo["chave"]
        if anterior is None or anterior == chave_sistema():
            return
        rotulo = ORIGENS_SELO[detalhe_selo_origem["tipo"]][2]
        c1, c2, T = anterior
        sufixo = f" a {T:g} °C" if isinstance(T, float) else ""
        atualizar_selo_origem(
            "fornecido",
            f"Estes valores vieram de \"{rotulo}\" para o sistema anterior "
            f"({c1}/{c2}{sufixo}) e não foram recalculados para o sistema "
            "atual. Refaça a busca no banco ou a regressão.",
        )

    def atualizar_selo_uniquac(comp1, comp2):
        """Selo do UNIQUAC dizendo de onde vieram os r/q do par atual (2026-10-06,
        pedido do autor). Chamado a cada cálculo, porque a fonte depende dos
        componentes escolhidos — não só do modelo."""
        banco = (
            "a₁₂/a₂₁ do banco IPDB/ChemSep (tabela 'ChemSep UNIQUAC') para "
            f"{comp1}/{comp2}."
        )
        if uniquac_fonte_rq(comp1, comp2) == "chemsep":
            atualizar_selo_origem(
                "banco",
                "r/q estruturais do banco ChemSep — os mesmos com que os "
                f"parâmetros de interação foram ajustados; {banco}",
            )
        else:
            atualizar_selo_origem(
                "banco_rq_unifac",
                "r/q estruturais calculados pelos grupos UNIFAC, porque o "
                "banco ChemSep não tem r/q para este par. Os parâmetros de "
                "interação foram ajustados com os r/q do ChemSep, então o "
                f"resultado pode se afastar do esperado; {banco}",
            )

    # Nota fixa do NRTL (requisito de UI da seção 2.8): α12 só é regredido
    # nunca — quando não vem do banco IPDB (que traz valor medido real),
    # fica fixado por convenção. Verdadeira nos dois casos, sem precisar
    # rastrear a origem de α12 separadamente do restante do selo.
    # `expand=True` no Text (não no Row) — sem isso, o texto não tinha
    # limite de largura e podia vazar pra fora do card "Parâmetros do
    # modelo" (mesma classe de bug do texto do ⓘ, 2026-09-28); com
    # `expand=True`, o texto ocupa só o espaço que sobra ao lado do ícone
    # e quebra linha dentro dele.
    # Ícone ⓘ e "α₁₂" em azul e texto em verde-azulado escuro itálico
    # (pedido do autor, 2026-10-03): a nota é um aviso científico que não
    # pode passar despercebido, então se destaca do cinza dos demais textos.
    # Todas as cores passam de 4,5:1 sobre o cartão.
    nota_alpha_fixo = ft.Row(
        controls=[
            ft.Icon(ft.Icons.INFO, size=18, color=ft.Colors.BLUE_700),
            ft.Text(
                spans=[
                    ft.TextSpan(
                        "α₁₂",
                        style=ft.TextStyle(
                            color=ft.Colors.BLUE_800,
                            weight=ft.FontWeight.BOLD,
                            italic=True,
                        ),
                    ),
                    ft.TextSpan(
                        ": quando não vier do banco IPDB, fica fixado por "
                        "convenção (não é ajustado pela regressão de Barker) — "
                        "valor de referência típico entre 0,2 e 0,47."
                    ),
                ],
                size=14,
                color=ft.Colors.TEAL_900,
                italic=True,
                expand=True,
            ),
        ],
        spacing=6,
        visible=False,
    )

    # Aviso de valor inválido digitado num campo de parâmetro (2026-10-06):
    # fica dentro do próprio card "Parâmetros do modelo", logo abaixo dos
    # campos — a mensagem de status geral mora no card "Dados experimentais",
    # que no celular (cards empilhados) fica longe, fora da vista. Criado uma
    # vez e reaproveitado entre montagens de layout (como `selo_origem`); só
    # `value` e `visible` mudam.
    aviso_parametro = ft.Text(
        "", color=ft.Colors.RED_800, size=14, visible=False
    )
    # Aviso de duas fases líquidas (2026-10-08): fica no card de parâmetros, perto
    # do que o causa (a mensagem de status mora no fim do card "Dados
    # experimentais", fora da tela quando a tabela é longa). Controle próprio,
    # criado uma vez e só `value`/`visible` mudam; `gerar_grafico` o atualiza a
    # cada cálculo (as dicas de botão apagado não o apagam).
    aviso_instabilidade_txt = ft.Text(
        "", color="#9A3B00", size=14, visible=False
    )

    def construir_sliders(nome_modelo):
        sliders_area.controls.clear()
        aviso_parametro.visible = False
        parametros_atuais.clear()
        sliders_por_chave.clear()

        botao_buscar_banco.visible = nome_modelo in MODELOS_COM_BANCO_IPDB
        caixa_regressao.visible = nome_modelo in PARAM_SLIDERS
        nota_alpha_fixo.visible = (nome_modelo == "NRTL")

        specs = PARAM_SLIDERS.get(nome_modelo)
        if not specs:
            sliders_area.controls.append(
                ft.Text(
                    "Este modelo resolve os parâmetros automaticamente a "
                    "partir dos componentes escolhidos (grupos UNIFAC "
                    "clássicos no UNIFAC; no UNIQUAC, r/q e interação "
                    "binária do banco ChemSep/IPDB) — sem sliders manuais "
                    "por enquanto.",
                    color=ft.Colors.GREY_800,
                    # `key` estável (2026-09-28) — sem identidade própria,
                    # trocar de modelo repetidamente/rápido no dropdown
                    # podia confundir a reconciliação de widgets do
                    # Flutter (bug intermitente e pré-existente,
                    # reproduzido pelo autor mesmo numa versão antiga do
                    # código — não é regressão de hoje). Um `key` único
                    # por modelo garante que o Flutter sempre trata isso
                    # como um widget novo, nunca reaproveita estado de um
                    # widget antigo por engano.
                    key=ft.ValueKey(f"sem_sliders_{nome_modelo}"),
                )
            )
            if nome_modelo == "UNIFAC":
                atualizar_selo_origem(
                    "preditivo",
                    "UNIFAC é preditivo: os parâmetros vêm só dos grupos "
                    "estruturais de cada componente, sem parâmetro de "
                    "interação ajustável por par.",
                )
            else:  # UNIQUAC
                atualizar_selo_origem(
                    "banco",
                    "r/q estruturais do banco ChemSep (ou, se faltarem, dos "
                    "grupos UNIFAC) e a₁₂/a₂₁ do banco IPDB/ChemSep. A fonte "
                    "que valeu para o par escolhido aparece aqui assim que o "
                    "gráfico é calculado.",
                )
            return

        for spec in specs:
            parametros_atuais[spec["chave"]] = spec["inicial"]
            # Campo de valor digitável (2026-10-06, pedido do autor): além de
            # arrastar o slider, dá para digitar o número exato. O rótulo do
            # parâmetro fica no próprio campo. Aceita vírgula decimal; valor
            # inválido volta ao anterior com aviso. O valor digitado não fica
            # preso ao intervalo do slider (que é só um recorte para
            # arrastar): só a posição do botão é limitada, como já acontece
            # com os valores vindos do banco e da regressão.
            def filtrar_valor(e):
                filtrado = re.sub(r"[^0-9.,\-]", "", e.control.value or "")
                if filtrado != e.control.value:
                    e.control.value = filtrado
                    e.control.update()

            def confirmar_valor(e, spec=spec):
                chave = spec["chave"]
                campo = e.control
                texto = (campo.value or "").strip().replace(",", ".")
                # Perder o foco sem editar não pode reescrever o valor: o
                # campo mostra 4 algarismos, e o parâmetro (ex.: vindo da
                # regressão) pode ter mais.
                if texto == formatar_parametro(parametros_atuais[chave]):
                    return
                try:
                    valor = float(texto)
                    if not math.isfinite(valor):
                        raise ValueError
                    if chave in ("L12", "L21") and valor <= 0:
                        raise ValueError
                except ValueError:
                    campo.value = formatar_parametro(parametros_atuais[chave])
                    exigencia = " maior que zero" if chave in ("L12", "L21") else ""
                    aviso_parametro.value = (
                        f"Valor inválido para {spec['rotulo']}: digite um "
                        f"número{exigencia}."
                    )
                    aviso_parametro.color = ft.Colors.RED_800
                    dica_ativa["lugar"] = None
                    aviso_parametro.visible = True
                    page.update()
                    return
                aviso_parametro.visible = False
                if valor == parametros_atuais[chave]:
                    page.update()
                    return
                parametros_atuais[chave] = valor
                slider_par = sliders_por_chave[chave][0]
                slider_par.value = max(slider_par.min, min(slider_par.max, valor))
                if chave != "alpha12":
                    atualizar_selo_origem(
                        "fornecido",
                        f"{spec['rotulo']} digitado manualmente pelo usuário.",
                    )
                gerar_grafico()

            valor_texto = ft.TextField(
                value=formatar_parametro(spec["inicial"]),
                label=spec["rotulo"],
                width=100,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=filtrar_valor,
                on_blur=confirmar_valor,
                on_submit=confirmar_valor,
                key=ft.ValueKey(f"valor_{nome_modelo}_{spec['chave']}"),
                **{**ESTILO_CAIXA_SISTEMA, "content_padding": ft.Padding(10, 10, 10, 10)},
            )

            def on_change(e, valor_texto=valor_texto):
                valor_texto.value = formatar_parametro(e.control.value)
                page.update()

            def on_change_end(e, spec=spec):
                aviso_parametro.visible = False
                parametros_atuais[spec["chave"]] = e.control.value
                if spec["chave"] != "alpha12":
                    atualizar_selo_origem(
                        "fornecido",
                        f"{spec['rotulo']} ajustado manualmente pelo "
                        "usuário via slider.",
                    )
                gerar_grafico()

            # `key` estável por modelo+parâmetro (não só `spec["chave"]"`,
            # que se repete entre modelos — ex.: "A12" existe em Margules
            # 2P e Van Laar) — mesmo motivo do `key` do texto "sem
            # sliders" acima: evita o Flutter reaproveitar por engano o
            # estado de um slider de um modelo anterior ao trocar rápido
            # no dropdown.
            chave_unica = f"{nome_modelo}_{spec['chave']}"
            slider = ft.Slider(
                min=spec["min"],
                max=spec["max"],
                value=spec["inicial"],
                on_change=on_change,
                on_change_end=on_change_end,
                expand=True,
                active_color=ft.Colors.BLUE_700,
                inactive_color=ft.Colors.BLUE_100,
                thumb_color=ft.Colors.BLUE_700,
                key=ft.ValueKey(f"slider_{chave_unica}"),
            )
            sliders_area.controls.append(
                ft.Row(
                    [valor_texto, slider],
                    spacing=ESPACO_PEQUENO,
                    key=ft.ValueKey(f"linha_{chave_unica}"),
                )
            )
            sliders_por_chave[spec["chave"]] = (slider, valor_texto, spec["rotulo"])

        atualizar_selo_origem(
            "fornecido",
            f"Valor inicial padrão do app para {nome_modelo}; ajustável "
            "manualmente pelos sliders, pela busca no banco IPDB (quando "
            "disponível) ou pela regressão de Barker a partir da tabela.",
        )

    # 6b. Busca de parâmetros reais no banco IPDB/ChemSep (item 2 de
    # "Próximos passos" do CLAUDE.md) — alternativa à digitação manual,
    # disponível só para os modelos com tabela lá (NRTL, Wilson;
    # MODELOS_COM_BANCO_IPDB). Visibilidade do botão é ajustada dentro de
    # construir_sliders a cada troca de modelo.
    def buscar_do_banco(e=None):
        nome_modelo = modelo_selecionado["nome"]
        comp1 = campo_componente1.value.strip()
        comp2 = campo_componente2.value.strip()
        try:
            T_C = float(campo_temperatura.value)
            params = buscar_parametros_banco(nome_modelo, comp1, comp2, T_C + 273.15)
        except Exception as exc:
            mensagem_status.value = f"Busca no banco não realizada: {exc}."
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return

        for chave, valor in params.items():
            if chave not in sliders_por_chave:
                continue
            slider, valor_texto, rotulo = sliders_por_chave[chave]
            # O banco (IPDB/ChemSep) pode devolver um valor fora do range de
            # exploração do slider (min/max são só um recorte manual para
            # arrastar, não um limite físico do parâmetro) — o Flet rejeita
            # slider.value fora de [min, max]. Só a posição visual é limitada;
            # o cálculo do gráfico usa o valor real, sem truncar.
            slider.value = max(slider.min, min(slider.max, valor))
            valor_texto.value = formatar_parametro(valor)
            parametros_atuais[chave] = valor

        atualizar_selo_origem(
            "banco",
            f"IPDB/ChemSep, tabela 'ChemSep {nome_modelo}', par "
            f"{comp1}/{comp2} a {T_C:.1f} °C.",
        )
        gerar_grafico(
            mensagem_extra=(
                f"Parâmetros de {nome_modelo} obtidos do banco IPDB/ChemSep "
                f"para {comp1}/{comp2}."
            )
        )

    botao_buscar_banco = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.STORAGE), ft.Text("Buscar do Banco (IPDB)")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=buscar_do_banco,
        style=estilo_botao(),
    )

    # 6c. Regressão de parâmetros pelo método de Barker (seção 2.8 do
    # mapeamento) — calcula os parâmetros livres do modelo escolhido a
    # partir dos pontos digitados na tabela, e atualiza os sliders com o
    # resultado (o próprio gerar_grafico já redesenha os gráficos em
    # seguida). Só cobre os modelos com slider manual (não UNIQUAC/UNIFAC
    # — UNIQUAC já resolve automaticamente via IPDB quando o par está no
    # banco; misturar isso com regressão fica para uma decisão futura).
    def calcular_por_regressao(e=None):
        nome_modelo = modelo_selecionado["nome"]
        if nome_modelo not in PARAM_SLIDERS:
            mensagem_status.value = (
                "Regressão por Barker só está disponível, por enquanto, "
                "para os modelos com slider manual (não UNIQUAC/UNIFAC)."
            )
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return

        pontos_validos = []
        for linha in dt.rows:
            p_field, x_field, y_field = (linha.cells[i].content for i in range(3))
            try:
                pontos_validos.append(
                    parse_ponto(p_field.value, x_field.value, y_field.value)
                )
            except ValueError:
                pass

        params_fixos = {}
        if nome_modelo == "NRTL":
            params_fixos["alpha12"] = parametros_atuais.get("alpha12", 0.3)

        try:
            comp1 = campo_componente1.value.strip()
            comp2 = campo_componente2.value.strip()
            T_C = float(campo_temperatura.value)
            resultado = regress_params_barker(
                nome_modelo, comp1, comp2, T_C, pontos_validos,
                params_fixos=params_fixos,
            )
        except Exception as exc:
            mensagem_status.value = f"Regressão não realizada: {exc}."
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return

        for chave, valor in resultado["params"].items():
            if chave not in sliders_por_chave:
                continue
            slider, valor_texto, rotulo = sliders_por_chave[chave]
            # A regressão de Barker não tem por que respeitar o range de
            # exploração do slider (min/max é só um recorte manual de UI,
            # não um limite físico do parâmetro) — o Flet rejeita
            # slider.value fora de [min, max]. Só a posição visual é
            # limitada; o cálculo do gráfico usa o valor regredido real.
            slider.value = max(slider.min, min(slider.max, valor))
            valor_texto.value = formatar_parametro(valor)
            parametros_atuais[chave] = valor

        poucos_pontos = resultado["graus_liberdade"] == 1
        aviso_gl = (
            " — poucos pontos (grau de liberdade mínimo), confiança baixa"
            if poucos_pontos else ""
        )
        aviso_ajuste = aviso_ajuste_regressao(resultado, sliders_por_chave)
        atualizar_selo_origem(
            "calculado_poucos_pontos" if poucos_pontos else "calculado",
            f"Regressão de Barker a partir de {resultado['n_pontos']} "
            f"ponto(s) da tabela (grau de liberdade = "
            f"{resultado['graus_liberdade']}), resíduo RMS = "
            f"{resultado['residual_rms']:.4g}."
            + (f" {aviso_ajuste}" if aviso_ajuste else ""),
        )
        gerar_grafico(
            mensagem_extra=(
                f"Parâmetros calculados por regressão (Barker) a partir de "
                f"{resultado['n_pontos']} ponto(s) da tabela{aviso_gl}."
            )
        )
        # Depois do gráfico: `gerar_grafico` reavalia os botões e apagaria a
        # dica. Aviso laranja dentro do card "Parâmetros do modelo".
        if aviso_ajuste:
            mostrar_dica(aviso_ajuste)

    botao_regressao = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.FUNCTIONS), ft.Text("Calcular por Regressão (Barker)")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=calcular_por_regressao,
        # Começa apagado; `atualizar_habilitacao_botoes` acende quando há
        # pontos suficientes para o modelo escolhido.
        disabled=True,
        style=estilo_botao(),
    )

    def dica_regressao():
        spec = REGRESSAO_MODELOS.get(modelo_selecionado["nome"])
        minimo = len(spec["livres"]) + 1
        mostrar_dica(
            f"A regressão precisa de pelo menos {minimo} pontos válidos na "
            f"tabela para {modelo_selecionado['nome']} (há "
            f"{contar_pontos_validos()}). Complete a tabela, importe dados ou "
            "use um exemplo."
        )

    def dica_comparar():
        mostrar_dica(
            "Para comparar, a tabela precisa ter ao menos um ponto "
            "experimental válido (P, x₁ e y₁ preenchidos)."
        )

    def dica_limpar():
        mostrar_dica("A tabela já está sem pontos válidos.", lugar="status")

    def caixa_com_dica(botao, dica):
        # Só explica quando o botão está de fato apagado; aceso, o clique é
        # do próprio botão.
        return ft.GestureDetector(
            content=botao,
            on_tap=lambda e: dica() if botao.disabled else None,
        )

    caixa_regressao = caixa_com_dica(botao_regressao, dica_regressao)
    caixa_comparar = caixa_com_dica(botao_comparar, dica_comparar)
    caixa_limpar = caixa_com_dica(botao_limpar_tabela, dica_limpar)

    construir_sliders(modelo_selecionado["nome"])

    # Layout adaptativo (2026-09-28) — implementa, enfim, o arranjo previsto
    # desde o rascunho original do autor e a seção 2.2 do mapeamento
    # ("tabela de dados à esquerda + dois gráficos sincronizados à
    # direita"), que a versão mobile-only nunca chegou a ter. Abaixo do
    # breakpoint (celular, tela estreita): tudo empilhado numa coluna só,
    # igual ao que já foi validado em sessão real. A partir do breakpoint
    # (PC, navegador em janela larga): tabela/controles à esquerda, os dois
    # gráficos à direita — reaproveitando os MESMOS objetos de controle
    # (dt, chart, sliders_area etc.), só reorganizados em containers
    # diferentes. `page.on_resize` reconstrói o layout ao vivo (ex.: girar
    # o celular, redimensionar a janela do navegador).
    LARGURA_BREAKPOINT_DESKTOP = 900

    # Um card por seção — antes viviam juntos numa única "coluna de
    # controles"; a partir de 2026-09-28 o desktop os espalha em posições
    # diferentes (Sistema e Parâmetros embaixo dos gráficos, Dados
    # experimentais isolado à esquerda), então cada um vira uma função
    # própria em vez de um bloco fixo.
    def construir_card_sistema(expand=False):
        return cartao(
            "Sistema", linha_componentes, linha_modelo_temperatura, expand=expand,
            ajuda="sistema",
        )

    def construir_card_parametros(expand=False):
        return cartao(
            "Parâmetros do modelo",
            sliders_area,
            aviso_parametro,
            aviso_instabilidade_txt,
            # "Comparar" (2026-10-07, pedido do autor: "colocar o botão comparar
            # junto com o card de parâmetros"): numa linha própria, sob os
            # sliders. O selo de origem foi para o cabeçalho do card
            # (`extra_titulo`, logo após o título). Comparar vale para todos os
            # modelos (UNIQUAC/UNIFAC inclusos), ao contrário da regressão, que
            # depende dos sliders.
            ft.Row(controls=[caixa_comparar], wrap=True),
            nota_alpha_fixo,
            ft.Row(controls=[botao_buscar_banco, caixa_regressao], wrap=True),
            # ΔP/Δy (2026-10-06, pedido do autor: "o erro agora no card de
            # parâmetros"): o erro do modelo fica junto dos parâmetros que o
            # produzem, em vez de no fim do card "Dados experimentais".
            linha_erro_comparativo,
            expand=expand,
            extra_titulo=selo_origem,
            extra_junto=True,
            ajuda="parametros",
        )

    def construir_card_dados(expand=False, centralizar=False):
        # Revertido (2026-09-28): embrulhar `dt` num Column/Row com altura
        # fixa e scroll (tentativa de caber tudo em 100% de zoom) quebrava
        # a renderização do ícone de excluir — sobrava só um traço
        # vermelho (parecendo "i"), e piorou pra sumir de vez ao adicionar
        # o scroll horizontal também. `dt` volta a ser filho direto do
        # card, sem wrapper; a altura extra das 10 linhas soma na página
        # (rolagem normal do navegador/`page.scroll` já cobre isso), em
        # vez de arriscar quebrar o DataTable de novo.
        # `centralizar` (2026-10-03, só no desktop): tabela e botões no meio do
        # card de 420px. No celular fica False e o card é idêntico ao de
        # antes. Em vez de mutar `linha_botoes_tabela` (criada uma vez), uma
        # Row nova com o alinhamento certo a cada montagem; as mensagens
        # voltam para a esquerda dentro de um Container.
        if centralizar:
            # A lixeira de limpar (que no celular fica no cabeçalho, ao lado
            # do título) vai para uma Row própria, centralizada, logo abaixo
            # do título. ("Comparar" mudou para o card de parâmetros.)
            acoes_topo = [
                ft.Row(
                    controls=[caixa_limpar],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            ]
            # Três botões não cabem numa linha nos ~420px do card: "Adicionar"
            # numa linha e "Importar dados" + "Exemplos" juntos na de baixo
            # (o mesmo arranjo que o celular já faz por quebra de linha).
            botoes = ft.Column(
                controls=[
                    ft.Row(controls=[botao_adicionar], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row(
                        controls=[botao_importar_csv, botao_exemplos],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=ESPACO_MEDIO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            mensagens = [
                ft.Container(content=mensagem_status, alignment=ft.Alignment.CENTER_LEFT),
            ]
        else:
            acoes_topo = []
            botoes = linha_botoes_tabela
            mensagens = [mensagem_status]
        return cartao(
            "Dados experimentais",
            *acoes_topo,
            dt,
            botoes,
            *mensagens,
            centralizar=centralizar,
            expand=expand,
            ajuda="dados",
            extra_titulo=(
                None
                if centralizar
                else ft.Row(controls=[caixa_limpar], spacing=4)
            ),
        )

    # Um card por gráfico (não mais um "Resultados" combinado) — no desktop
    # ficam lado a lado (ver montar_layout), cada um com `expand=True` pra
    # dividir a largura disponível ao meio.
    # Altura fixa pra área da legenda, igual nos dois cards (relatado pelo
    # autor, 2026-09-28: sem ela os cards saíam com tamanhos diferentes).
    # Como a legenda agora é uma grade de sempre três linhas (cabeçalho +
    # duas, ~70px — ver `coluna_legenda`), 72px comporta as duas legendas em
    # qualquer largura, sem espaço morto e sem cobrir o topo do eixo.
    ALTURA_LEGENDA = 72

    # `com_lupa` só no desktop (o celular não precisa do "Ampliar", pedido do
    # autor): no celular o card fica exatamente como antes.
    def construir_grafico_p_xy(altura, expand=False, com_lupa=False):
        return cartao(
            "Diagrama P-x-y",
            ft.Container(content=legenda, height=ALTURA_LEGENDA, alignment=ft.Alignment.CENTER),
            ft.Container(content=chart, height=altura),
            expand=expand,
            extra_titulo=botao_lupa_pxy if com_lupa else None,
            ajuda="pxy",
        )

    def construir_grafico_gamma(altura, expand=False, com_lupa=False):
        return cartao(
            "Coeficientes de atividade (ln γ)",
            ft.Container(content=legenda_gamma, height=ALTURA_LEGENDA, alignment=ft.Alignment.CENTER),
            ft.Container(content=chart_gamma, height=altura),
            expand=expand,
            extra_titulo=botao_lupa_gamma if com_lupa else None,
            ajuda="gamma",
        )

    # Guarda o modo atual ("mobile"/"desktop") para só reconstruir o layout
    # quando ele realmente muda — não a cada pixel de resize. Sem isso, abrir
    # o seletor de arquivo nativo (botão "Importar dados") no celular dispara
    # um evento de resize (mudança de viewport ao abrir aquele painel), que
    # reconstrói `page.controls` inteiro no meio da espera do
    # `FilePicker.pick_files()`, derruba o listener que ele aguardava, e
    # estoura em "TimeoutException... invoke method listener for
    # FilePicker.pick_files" (bug relatado pelo autor, 2026-09-28).
    modo_layout_atual = {"modo": None}

    # Modo escolhido à mão pelo botão de alternância (2026-10-01, pedido do
    # autor). `None` = decide pela largura da janela, como sempre foi. Depois
    # de um clique, a escolha do usuário manda, e redimensionar a janela não
    # a desfaz — alguém que pediu "ver como celular" num monitor largo não
    # quer o layout pulando de volta sozinho.
    modo_forcado = {"valor": None}

    def montar_layout(e=None):
        modo_automatico = (
            "desktop" if (page.width or 0) >= LARGURA_BREAKPOINT_DESKTOP else "mobile"
        )
        modo = modo_forcado["valor"] or modo_automatico
        if modo == modo_layout_atual["modo"]:
            return
        modo_layout_atual["modo"] = modo

        # Revertido em definitivo (2026-09-28): o toggle responsivo dos
        # campos de componente/temperatura (mutar `.width`/`.expand` de
        # controles já criados a cada chamada de `montar_layout`, inclusive
        # na primeiríssima carga da página) foi isolado, por eliminação
        # nesta mesma sessão, como o gatilho de um bug intermitente do
        # Flutter em que a página carregava mostrando só o dropdown de
        # modelo e uma área cinza no lugar do resto — reproduzível até com
        # o código de antes desse recurso, mas só quando esse trecho
        # específico estava ativo. Sem confirmação da causa raiz exata (é
        # comportamento interno do Flutter/Flet, não deste código), a
        # correção segura é não mutar mais essas propriedades depois de
        # criadas — os campos ficam sempre com largura fixa (220px),
        # perdendo o ajuste fino ao card "Sistema" mais estreito no
        # desktop (cosmético) em troca de não quebrar a renderização.

        # Espaço reservado antes do 1º controle: o rótulo flutuante de
        # dropdown_modelo colava na borda superior da tela e cortava pela
        # metade em landscape no celular (visto em sessão real,
        # 2026-09-27) — aumentar page.padding não teve nenhum efeito
        # visível, então em vez de padding é espaço de layout de verdade.
        # Inofensivo no desktop (só um respiro extra no topo).
        espaco_topo = ft.Container(height=24)

        # Botão de alternar modo de exibição (2026-10-01). Criado NOVO a cada
        # montagem, junto com os cards, em vez de ser um controle fixo que
        # tem ícone/rótulo trocados a cada clique — pelo mesmo motivo
        # registrado logo acima: este app não muta propriedade de controle já
        # criado. O `modo` da closure é o desta montagem, então o botão
        # sempre oferece o modo oposto ao que está na tela.
        def alternar_modo(e):
            modo_forcado["valor"] = "desktop" if modo == "mobile" else "mobile"
            montar_layout()

        botao_modo = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.DESKTOP_WINDOWS if modo == "mobile" else ft.Icons.PHONE_IPHONE,
                        size=16,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Text(
                        "Ver como computador" if modo == "mobile" else "Ver como celular",
                        size=14,
                        color=ft.Colors.WHITE,
                    ),
                ],
                tight=True,
                spacing=6,
            ),
            on_click=alternar_modo,
            # Fundo branco translúcido (pedido do autor, 2026-10-03): destaca
            # o botão da faixa azul sem competir com o título.
            style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE)),
        )

        # Botão "Ajuda" (2026-10-07): mesmo estilo do botão de modo, ao lado
        # dele; criado novo a cada montagem pelo mesmo motivo.
        botao_ajuda = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.HELP_OUTLINE, size=16, color=ft.Colors.WHITE),
                    ft.Text("Ajuda", size=14, color=ft.Colors.WHITE),
                ],
                tight=True,
                spacing=6,
            ),
            on_click=abrir_ajuda,
            style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE)),
        )
        botoes_cabecalho = ft.Row(
            controls=[botao_ajuda, botao_modo],
            spacing=ESPACO_PEQUENO,
            wrap=True,
            alignment=ft.MainAxisAlignment.END,
        )

        # Faixa de cabeçalho (item 5 da estética, 2026-10-03, opção H2 do
        # autor): nome, subtítulo e crédito, com o botão de modo dentro da
        # faixa. Montada nova a cada `montar_layout`, como o resto — sem
        # mutar controle já criado. No desktop o crédito e o botão ficam à
        # direita; no celular, abaixo do subtítulo, para o título caber.
        titulo_app = ft.Column(
            controls=[
                ft.Text(
                    "VLE Interativo",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                ft.Text(
                    "Equilíbrio líquido-vapor com modelos de Gᴱ",
                    size=14,
                    color=ft.Colors.WHITE,
                ),
            ],
            spacing=2,
        )
        credito_app = ft.Text("UFC", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        if modo == "desktop":
            interior_cabecalho = ft.Row(
                controls=[
                    ft.Container(content=titulo_app, expand=True),
                    ft.Column(
                        controls=[credito_app, botoes_cabecalho],
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            interior_cabecalho = ft.Column(
                controls=[
                    titulo_app,
                    # Crédito e os dois botões numa Row que quebra linha
                    # sozinha (a 360px o botão de modo desce para a de baixo).
                    ft.Row(
                        controls=[credito_app, botao_ajuda, botao_modo],
                        spacing=ESPACO_PEQUENO,
                        run_spacing=0,
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=ESPACO_PEQUENO,
            )
        linha_modo = ft.Container(
            content=interior_cabecalho,
            bgcolor=ft.Colors.BLUE_700,
            border_radius=12,
            padding=ft.Padding(16, 12, 16, 12),
        )

        if modo == "desktop":
            # Reorganizado a pedido do autor (2026-09-28): a tabela de
            # dados fica sozinha, isolada à esquerda (com mais linhas
            # visíveis de uma vez — ver adicionar_linha), e Sistema +
            # Parâmetros do modelo saem da esquerda e vão para uma segunda
            # fileira, lado a lado, embaixo dos dois gráficos.
            conteudo = ft.Row(
                controls=[
                    ft.Container(content=construir_card_dados(centralizar=True), width=420),
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    construir_grafico_p_xy(altura=320, expand=True, com_lupa=True),
                                    construir_grafico_gamma(altura=320, expand=True, com_lupa=True),
                                ],
                                spacing=ESPACO_GRANDE,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                            ft.Row(
                                controls=[
                                    construir_card_sistema(expand=True),
                                    construir_card_parametros(expand=True),
                                ],
                                spacing=ESPACO_GRANDE,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                        ],
                        spacing=ESPACO_GRANDE,
                        expand=True,
                    ),
                ],
                spacing=ESPACO_GRANDE,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        else:
            # Mobile continua empilhado na ordem original, validada em
            # sessão real — a reorganização acima é só pro desktop.
            conteudo = ft.Column(
                controls=[
                    construir_card_sistema(),
                    construir_card_parametros(),
                    construir_card_dados(),
                    construir_grafico_p_xy(altura=300),
                    construir_grafico_gamma(altura=300),
                ],
                spacing=ESPACO_MEDIO,
            )

            # Modo celular numa janela larga = o usuário pediu pra PREVER como
            # fica no telefone (botão acima). Sem limite de largura, os cards
            # esticariam pelos 1400px do monitor e a previsão não valeria
            # nada: sliders atravessando a tela, tabela perdida num canto.
            # A moldura só entra quando há janela sobrando — num telefone de
            # verdade a condição é falsa e o empilhamento fica exatamente como
            # estava, sem nenhuma mudança no que já foi validado em aparelho
            # real.
            LARGURA_SIMULACAO_CELULAR = 420
            if (page.width or 0) - 2 * ESPACO_GRANDE > LARGURA_SIMULACAO_CELULAR + 60:
                conteudo = ft.Row(
                    controls=[ft.Container(content=conteudo, width=LARGURA_SIMULACAO_CELULAR)],
                    alignment=ft.MainAxisAlignment.CENTER,
                )

        page.controls = [espaco_topo, linha_modo, conteudo]
        page.update()

    page.on_resize = montar_layout
    # `gerar_grafico` primeiro, sem sua própria `page.update()`, montando o
    # estado final dos controles (gráfico, mensagens, botões); só depois
    # `montar_layout()` monta a árvore e manda a ÚNICA atualização real da
    # carga inicial — em vez de duas seguidas (uma de cada função).
    gerar_grafico(atualizar_pagina=False)
    montar_layout()


# Execução no Replit
if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
