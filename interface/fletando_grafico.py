import csv
import io
import math
import re
import textwrap

import flet as ft
import flet_charts as fch

from calculos.gemini import (
    MODELOS_COM_BANCO_IPDB,
    MODELS_GE,
    buscar_parametros_banco,
    calculate_vle_isothermal,
    montar_parametros_automaticos,
    regress_params_barker,
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
}

# Sliders por modelo — nome do parâmetro (chave esperada por MODELS_GE em
# calculos/gemini.py), rótulo exibido, faixa e valor inicial. Só cobre os
# modelos cujos parâmetros são números de interação livres, fornecidos
# manualmente. UNIQUAC e UNIFAC não entram aqui — seus parâmetros são
# resolvidos automaticamente a partir dos componentes escolhidos, via
# montar_parametros_automaticos (grupos UNIFAC clássicos + banco IPDB para
# o UNIQUAC), sem slider manual.
PARAM_SLIDERS = {
    "Margules (1-P)": [
        {"chave": "A", "rotulo": "A", "min": -2.0, "max": 2.0, "inicial": 0.5},
    ],
    "Margules (2-P)": [
        {"chave": "A12", "rotulo": "A₁₂", "min": -2.0, "max": 2.0, "inicial": 0.6},
        {"chave": "A21", "rotulo": "A₂₁", "min": -2.0, "max": 2.0, "inicial": 0.3},
    ],
    "Van Laar": [
        {"chave": "A12", "rotulo": "A₁₂", "min": -2.0, "max": 2.0, "inicial": 0.6},
        {"chave": "A21", "rotulo": "A₂₁", "min": -2.0, "max": 2.0, "inicial": 0.4},
    ],
    "Wilson": [
        {"chave": "L12", "rotulo": "Λ₁₂", "min": 0.01, "max": 3.0, "inicial": 0.8},
        {"chave": "L21", "rotulo": "Λ₂₁", "min": 0.01, "max": 3.0, "inicial": 0.6},
    ],
    "NRTL": [
        {"chave": "tau12", "rotulo": "τ₁₂", "min": -2.0, "max": 2.0, "inicial": 0.3},
        {"chave": "tau21", "rotulo": "τ₂₁", "min": -2.0, "max": 2.0, "inicial": 0.3},
        {"chave": "alpha12", "rotulo": "α₁₂", "min": 0.2, "max": 0.47, "inicial": 0.3},
    ],
}


# Paleta dos gráficos (item 4 da lista de estética, 2026-10-03, opção A do
# autor): a COR identifica a fase, o ESTILO identifica a origem do dado —
# marcador cheio = tabela (experimental), linha contínua = modelo, marcador
# vazado = modelo calculado nos x1 da tabela ("Comparar"). Azul/laranja é o
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
    amplitude = max(vmax - vmin, 1e-12)
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


def eixo_vertical(titulo: str, passo: float, largura_rotulo: int = 40) -> fch.ChartAxis:
    """Eixo vertical dos gráficos, com o passo fixo vindo de
    `limites_redondos`. Criado NOVO a cada `gerar_grafico` em vez de mutar o
    `label_spacing` do eixo existente — este app não muta propriedade de
    controle já criado.

    `show_min`/`show_max` desligados: os rótulos dos extremos saem da
    própria escala regular (os limites de `limites_redondos` são múltiplos do
    passo — e `margem_extremos` abre uma folga mínima para o marcador do
    extremo não ser descartado por ruído de ponto flutuante). Com os dois
    ligados o extremo era desenhado duas vezes, uma por cima da outra: o
    último marcador do ln γ sai como 0.6000000000000001, diferente do
    máximo 0.6, e o "0.60" do topo aparecia em negrito.
    `largura_rotulo`: o ln γ tem rótulos negativos de 5 caracteres ("-0.10"),
    que quebravam em duas linhas ("-0.1" / "0") na coluna padrão de 40px."""
    return fch.ChartAxis(
        label_size=largura_rotulo,
        label_spacing=passo,
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


def ponto_grafico(
    x: float, y: float, nome_x: str, nome_y: str, unidade_y: str = ""
) -> fch.LineChartDataPoint:
    """Ponto de série dos gráficos, com o tooltip (ao passar o cursor)
    mostrando os dois valores, nomeados e formatados por `formatar_valor`
    — em duas linhas, ex.: "x1 = 0.3500" e "P = 45.23 kPa". Sem o nome,
    o valor solto do tooltip padrão não diz de que eixo é; sem o x, não
    diz onde está."""
    sufixo = f" {unidade_y}" if unidade_y else ""
    texto = (
        f"{nome_x} = {formatar_valor(x)}\n"
        f"{nome_y} = {formatar_valor(y)}{sufixo}"
    )
    # `text_align` padrão do Flet é CENTER: as duas linhas saíam centradas
    # uma em relação à outra. START alinha o início das duas à esquerda.
    return fch.LineChartDataPoint(
        x,
        y,
        tooltip=fch.LineChartDataPointTooltip(
            text=texto, text_align=ft.TextAlign.START
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

    # Ícone ⓘ tocável (não só hover) — o `tooltip` nativo do Flet depende de
    # hover ou long-press, e o usuário final deste app usa celular (sem
    # mouse); um toque simples no ícone não abria nada de forma confiável.
    # Em vez de tooltip, o ícone abre um diálogo com a explicação — mesmo
    # gesto (toque) em qualquer dispositivo. `obter_texto` é uma função sem
    # argumentos (não uma string fixa) para cobrir os casos em que a
    # explicação muda em tempo real (ex.: origem do parâmetro).
    def icone_info(obter_texto, titulo="Sobre este valor", destaque=False):
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
                    title=ft.Text(titulo),
                    content=ft.Text(texto_quebrado),
                    actions=[ft.TextButton("Ok", on_click=lambda e: page.pop_dialog())],
                )
            )

        # `destaque=True` (selo de origem do parâmetro, pedido do autor,
        # 2026-10-03): ícone cheio, um pouco maior, em azul-celeste. Os ⓘ do
        # ΔP/Δy ficam no estilo discreto de antes.
        if destaque:
            return ft.IconButton(
                icon=ft.Icons.INFO,
                icon_size=18,
                icon_color=ft.Colors.LIGHT_BLUE_600,
                padding=0,
                on_click=abrir,
            )
        return ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            icon_size=16,
            padding=0,
            on_click=abrir,
        )

    # Agrupamento visual em cards (2026-09-28, passada de estética) — antes,
    # tudo (sistema, sliders, tabela, botões, gráficos) ficava solto em
    # sequência, sem hierarquia visual entre seções que fazem coisas
    # diferentes. Cada card leva um título curto — mesma ideia de
    # "dashboards financeiros" já citada como inspiração do selo de origem
    # (seção 2.8 do mapeamento), aplicada agora ao layout inteiro.
    def cartao(titulo, *controles, expand=False, extra_titulo=None):
        # `extra_titulo` (opcional) — um controle extra ao lado do título,
        # no cabeçalho do card, em vez de só mais um item na lista debaixo.
        # Usado pelo botão "Comparar" no card "Dados experimentais" (pedido
        # do autor, 2026-09-28): fica junto do título, não lá embaixo perto
        # de "Gerar Gráfico".
        cabecalho = ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD)
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
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
            )
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[cabecalho, *controles],
                    spacing=ESPACO_PEQUENO,
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
    dt = ft.DataTable(
        column_spacing=16,
        horizontal_margin=8,
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
                    size=14,
                )
            ),
            ft.DataColumn(
                label=ft.Text("x₁", width=largura_coluna, text_align=ft.TextAlign.CENTER)
            ),
            ft.DataColumn(
                label=ft.Text("y₁", width=largura_coluna, text_align=ft.TextAlign.CENTER)
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

        # Função para criar as caixas de texto padronizadas
        def criar_campo(valor_inicial):
            return ft.TextField(
                value=valor_inicial,
                width=largura_coluna,
                text_align=ft.TextAlign.CENTER,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=filtrar_numero,
                border=ft.NoInputBorder(),
                # Sem isso, "Comparar"/"Limpar Tabela" só reavaliavam se
                # havia dado válido quando "Gerar Gráfico" era clicado —
                # digitar direto na tabela não acendia nem apagava os
                # botões (relatado pelo autor, 2026-09-28). `atualizar_
                # estado_botoes_tabela` é leve (só recalcula os dois
                # `.disabled`, não redesenha o gráfico inteiro a cada
                # tecla) e é definida mais abaixo — resolvida por closure
                # só quando o campo de verdade perde o foco.
                on_blur=lambda e: atualizar_estado_botoes_tabela(),
            )

        # Prepara a nova linha
        nova_linha = ft.DataRow(cells=[])

        # Função específica para excluir esta linha
        def excluir_esta_linha(e):
            dt.rows.remove(nova_linha)
            page.update()

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

    async def importar_csv(e):
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
            pontos, ignoradas_csv = importar_pontos_csv(texto)
        except (ValueError, UnicodeDecodeError) as exc:
            mensagem_status.value = f"Falha ao importar CSV: {exc}."
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return

        if not pontos:
            mensagem_status.value = "Nenhum ponto válido encontrado no CSV."
            mensagem_status.color = ft.Colors.RED_800
            page.update()
            return

        dt.rows.clear()
        for ponto in pontos:
            adicionar_linha(valores=ponto, atualizar=False)

        aviso = f" {ignoradas_csv} linha(s) do CSV ignorada(s) por dado inválido." if ignoradas_csv else ""
        gerar_grafico(mensagem_extra=f"{len(pontos)} ponto(s) importado(s) do CSV.{aviso}")

    botao_importar_csv = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.UPLOAD_FILE), ft.Text("Importar CSV")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=importar_csv,
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

    # Ícone só (não botão com texto) — pedido do autor, 2026-09-28: precisa
    # caber ao lado de "Comparar" no cabeçalho do card, sem disputar espaço
    # com o título. "Delete sweep" (vassoura+lixo) é o ícone Material
    # padrão pra "limpar tudo", autoexplicativo mesmo sem o rótulo de texto.
    botao_limpar_tabela = ft.IconButton(
        icon=ft.Icons.DELETE_SWEEP,
        tooltip="Limpar Tabela",
        on_click=limpar_tabela,
    )

    linha_botoes_tabela = ft.Row(controls=[botao_adicionar, botao_importar_csv], wrap=True)

    # Reavaliação leve de "Comparar"/"Limpar Tabela" ao editar a tabela
    # diretamente (ver criar_campo, on_blur) — só checa se existe ao menos
    # um ponto válido, sem recalcular o modelo nem redesenhar os gráficos
    # (isso só acontece em "Gerar Gráfico"). `botao_comparar` é definido
    # mais abaixo; resolvido por closure, sem problema (mesmo padrão já
    # usado em `importar_csv`/`gerar_grafico`).
    def tabela_tem_ponto_valido():
        for linha in dt.rows:
            p_field, x_field, y_field = (linha.cells[i].content for i in range(3))
            try:
                parse_ponto(p_field.value, x_field.value, y_field.value)
                return True
            except ValueError:
                continue
        return False

    def atualizar_estado_botoes_tabela():
        tem_dado = tabela_tem_ponto_valido()
        botao_comparar.disabled = not tem_dado
        botao_limpar_tabela.disabled = not tem_dado
        page.update()

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
    # mudou). Uma coluna por gráfico (P-x-y e ln γ) — γ1/γ2 do modelo
    # avaliados exatamente nos x1 da tabela, junto com "Comparar".
    coluna_comparativo_pxy = coluna_legenda(
        "comparativo",
        [glifo_legenda(COR_LIQUIDO, "quadrado_vazado"), glifo_legenda(COR_VAPOR, "circulo_vazado")],
        84,
    )
    coluna_comparativo_pxy.visible = False
    coluna_comparativo_gamma = coluna_legenda(
        "comparativo",
        [glifo_legenda(COR_GAMMA1, "circulo_vazado"), glifo_legenda(COR_GAMMA2, "circulo_vazado")],
        84,
    )
    coluna_comparativo_gamma.visible = False

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

    legenda = ft.Row(
        controls=[
            coluna_legenda(
                "",
                [ft.Text("líquido", size=14), ft.Text("vapor", size=14)],
                56,
            ),
            coluna_legenda(
                "tabela",
                [glifo_legenda(COR_LIQUIDO, "quadrado"), glifo_legenda(COR_VAPOR, "circulo")],
                60,
            ),
            coluna_legenda(
                "modelo",
                [glifo_legenda(COR_LIQUIDO, "linha"), glifo_legenda(COR_VAPOR, "linha")],
                60,
            ),
            coluna_comparativo_pxy,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=4,
        visible=False,
    )

    # 4b. Segundo gráfico: ln γ vs x1 (seção 2.2 do mapeamento) — a curva do
    # modelo na malha genérica de 101 pontos, mais (via "Comparar", igual ao
    # gráfico 1) o próprio modelo avaliado exatamente nos x1 da tabela. Não
    # tem γ "experimental": γ1/γ2 sempre vêm da fórmula do modelo Gᴱ, nunca
    # de inverter a Lei de Raoult a partir de P/y medidos (método indireto
    # de regressão descartado na seção 2.8) — a diferença entre as duas
    # curvas aqui é só a malha de x1 usada, não a origem do γ.
    chart_gamma = fch.LineChart(
        data_series=[],
        min_x=0,
        max_x=1,
        min_y=0,
        max_y=1,
        expand=True,
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

    legenda_gamma = ft.Row(
        controls=[
            coluna_legenda(
                "",
                [ft.Text("ln γ₁", size=14), ft.Text("ln γ₂", size=14)],
                56,
            ),
            coluna_legenda(
                "modelo",
                [glifo_legenda(COR_GAMMA1, "linha"), glifo_legenda(COR_GAMMA2, "linha")],
                60,
            ),
            coluna_comparativo_gamma,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=4,
        visible=False,
    )

    # Ponta a ponta: pontos digitados na tabela (discretos, sem interpolação —
    # decisão de 2026-08-19) + curva calculada por calculate_vle_isothermal
    # com o modelo/parâmetros/componentes/temperatura escolhidos, no mesmo
    # gráfico. Para Margules/Van Laar/Wilson/NRTL os parâmetros vêm dos
    # sliders (parametros_atuais); para UNIQUAC/UNIFAC vêm de
    # montar_parametros_automaticos, resolvido a partir dos componentes.
    def gerar_grafico(e=None, mensagem_extra=None, atualizar_pagina=True):
        pontos_validos = []
        linhas_ignoradas = 0
        for linha in dt.rows:
            p_field, x_field, y_field = (linha.cells[i].content for i in range(3))
            try:
                pontos_validos.append(
                    parse_ponto(p_field.value, x_field.value, y_field.value)
                )
            except ValueError:
                # Linha com os 3 campos vazios é só espaço reservado da
                # tabela (ela nasce com NUM_LINHAS_INICIAIS linhas em
                # branco), não "dado inválido": não entra na contagem do
                # aviso. Antes, a tabela vazia no carregamento já mostrava
                # "10 linha(s) ... ignorada(s)" (achado nos prints,
                # 2026-10-01).
                if any((campo.value or "").strip() for campo in (p_field, x_field, y_field)):
                    linhas_ignoradas += 1

        # "Comparar" só faz sentido havendo dado experimental de verdade na
        # tabela para comparar contra — desabilitado sem isso (item 4 do
        # roadmap). Reconstruir o gráfico do zero também descarta qualquer
        # comparação calculada antes, pra não sobrar uma curva comparativa
        # desatualizada em relação ao modelo/tabela atual.
        botao_comparar.disabled = not pontos_validos
        # "Limpar Tabela" fica apagado sem dado nenhum pra apagar — mesmo
        # critério do "Comparar" (pontos_validos), pedido do autor,
        # 2026-09-28. O clique apaga qualquer dado presente, digitado à mão
        # ou importado via CSV — `limpar_tabela` não distingue a origem.
        botao_limpar_tabela.disabled = not pontos_validos
        coluna_comparativo_pxy.visible = False
        coluna_comparativo_gamma.visible = False
        linha_erro_comparativo.visible = False

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
                points=[ponto_grafico(x, p, "x₁", "P", "kPa") for x, p in liquido],
            ))
            series.append(fch.LineChartData(
                color=COR_VAPOR,
                stroke_width=0,
                point=fch.ChartCirclePoint(radius=4.5, color=COR_VAPOR, stroke_width=0),
                points=[ponto_grafico(x, p, "y₁", "P", "kPa") for x, p in vapor],
            ))
            valores_P += [p for _, p in liquido] + [p for _, p in vapor]

        erro_modelo = None
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
            modelo_ok = True
        except Exception as exc:
            erro_modelo = str(exc)

        if not series:
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
        chart.left_axis = eixo_vertical("P (kPa)", passo_y)
        chart.visible = True
        legenda.visible = True

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
            chart_gamma.left_axis = eixo_vertical("ln γ", passo_g, largura_rotulo=52)
            chart_gamma.visible = True
            legenda_gamma.visible = True
        else:
            chart_gamma.visible = False
            legenda_gamma.visible = False

        mensagens = []
        if mensagem_extra:
            mensagens.append(mensagem_extra)
        if linhas_ignoradas:
            mensagens.append(f"{linhas_ignoradas} linha(s) da tabela ignorada(s) por dado inválido.")
        if erro_modelo:
            mensagens.append(f"Curva do modelo não calculada: {erro_modelo}.")
        mensagem_status.value = " ".join(mensagens)
        mensagem_status.color = "#9A3B00" if mensagens else ""

        # `atualizar_pagina=False` só na carga inicial da página (ver
        # montar_layout/main) — junta o que seria 2 `page.update()`
        # seguidos (um daqui, um do montar_layout) num só, evitando
        # disparar duas atualizações em sequência rápida logo na
        # inicialização (suspeito do bug intermitente relatado pelo
        # autor, 2026-09-28 — a página já chegava quebrada, sem precisar
        # de nenhuma interação).
        if atualizar_pagina:
            page.update()

    botao_gerar_grafico = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.SHOW_CHART), ft.Text("Gerar Gráfico")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=gerar_grafico,
    )

    # 4c. Comparação calculado-vs-experimental (item 4 do roadmap) — só a
    # parte visual por enquanto (autorizado em 2026-09-27: "implementar o
    # botão para visualizar... e depois adicionar a parte do erro"). Avalia
    # o modelo exatamente nos x1 da tabela (não na malha genérica de 101
    # pontos usada por gerar_grafico), pra sobrepor calculado e experimental
    # no mesmo gráfico. O número de erro em si (métrica ainda não definida
    # — depende de orientação do Dr. Filipe) fica para depois.
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

        liquido_comp = sorted(zip(resultado["x1"], resultado["P_kPa"]))
        vapor_comp = sorted(zip(resultado["y1"], resultado["P_kPa"]))

        chart.data_series = chart.data_series + [
            fch.LineChartData(
                color=COR_LIQUIDO,
                stroke_width=0,
                point=marcador_vazado("quadrado", COR_LIQUIDO),
                points=[ponto_grafico(x, p, "x₁", "P", "kPa") for x, p in liquido_comp],
            ),
            fch.LineChartData(
                color=COR_VAPOR,
                stroke_width=0,
                point=marcador_vazado("circulo", COR_VAPOR),
                points=[ponto_grafico(y, p, "y₁", "P", "kPa") for y, p in vapor_comp],
            ),
        ]
        coluna_comparativo_pxy.visible = True

        ln_gamma1_comp = sorted(zip(resultado["x1"], (math.log(g) for g in resultado["gamma1"])))
        ln_gamma2_comp = sorted(zip(resultado["x1"], (math.log(g) for g in resultado["gamma2"])))
        chart_gamma.data_series = chart_gamma.data_series + [
            fch.LineChartData(
                color=COR_GAMMA1,
                stroke_width=0,
                point=marcador_vazado("circulo", COR_GAMMA1),
                points=[ponto_grafico(x, g, "x₁", "ln γ₁") for x, g in ln_gamma1_comp],
            ),
            fch.LineChartData(
                color=COR_GAMMA2,
                stroke_width=0,
                point=marcador_vazado("circulo", COR_GAMMA2),
                points=[ponto_grafico(x, g, "x₁", "ln γ₂") for x, g in ln_gamma2_comp],
            ),
        ]
        coluna_comparativo_gamma.visible = True
        chart_gamma.visible = True
        legenda_gamma.visible = True

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
        for p_exp, x1, y_exp in pontos_validos:
            P_calc, y_calc = calc_por_x1[x1]
            soma_dp_rel2 += ((P_calc - p_exp) / p_exp) ** 2
            soma_dy_abs2 += (y_calc - y_exp) ** 2
        dp_rms_pct = math.sqrt(soma_dp_rel2 / len(pontos_validos)) * 100
        dy_rms = math.sqrt(soma_dy_abs2 / len(pontos_validos))

        texto_dp_comparativo.value = f"ΔP = {dp_rms_pct:.2f}% (RMS)"
        texto_dy_comparativo.value = f"Δy = {dy_rms:.4f} (RMS)"
        linha_erro_comparativo.visible = True

        mensagem_status.value = f"Comparação calculada em {len(x1_lista)} ponto(s) da tabela."
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
    LARGURA_CAMPO_SISTEMA = 190

    dropdown_modelo = ft.Dropdown(
        # "Gᴱ" (small capital E) some fontes/navegadores não têm o glifo —
        # visto em sessão real no Samsung Browser (2026-09-27): o rótulo
        # aparecia cortado como só "Modelo G". Texto simples renderiza
        # em qualquer fonte.
        label="Modelo GE",
        value=modelo_selecionado["nome"],
        options=[ft.dropdown.Option(nome) for nome in MODELS_GE],
        on_select=selecionar_modelo,
        width=LARGURA_CAMPO_SISTEMA,
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
        text_align=ft.TextAlign.CENTER,
        on_blur=gerar_grafico, on_submit=gerar_grafico,
    )
    campo_componente2 = ft.TextField(
        label="Componente 2", value="water", width=LARGURA_CAMPO_SISTEMA,
        text_align=ft.TextAlign.CENTER,
        on_blur=gerar_grafico, on_submit=gerar_grafico,
    )
    campo_temperatura = ft.TextField(
        label="Temperatura (°C)",
        value="70",
        width=LARGURA_CAMPO_SISTEMA,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_blur=gerar_grafico,
        on_submit=gerar_grafico,
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
    # Guarda também o `tipo` (não só o `texto`), necessário pra restaurar o
    # selo certo ao desfazer (ver empilhar_historico/desfazer, abaixo).
    detalhe_selo_origem = {"tipo": None, "texto": ""}
    icone_selo_origem = icone_info(
        lambda: detalhe_selo_origem["texto"],
        titulo="Origem deste parâmetro",
        destaque=True,
    )
    selo_origem = ft.Row(
        controls=[chip_selo_origem, icone_selo_origem],
        spacing=4,
        visible=False,
    )

    def atualizar_selo_origem(tipo, detalhe):
        bg, fg, rotulo = ORIGENS_SELO[tipo]
        chip_selo_origem.bgcolor = bg
        texto_selo_origem.value = rotulo
        texto_selo_origem.color = fg
        detalhe_selo_origem["tipo"] = tipo
        detalhe_selo_origem["texto"] = detalhe
        selo_origem.visible = True

    # Desfazer (2026-09-28, pedido do autor: "cliquei no Barker e me
    # arrependi") — histórico dos últimos MAX_HISTORICO_PARAMETROS estados
    # dos parâmetros do modelo (valores dos sliders + selo de origem),
    # empilhado só antes de "Buscar do Banco" e "Calcular por Regressão
    # (Barker)" — as duas ações que sobrescrevem todos os sliders de uma vez
    # sem o usuário ter digitado nada diretamente. Arrastar um slider
    # manualmente não empilha: é o próprio usuário no controle, diferente de
    # um valor que veio de fora. Aumentado de 2 para 5 a pedido do autor
    # (2026-09-28) — mudança de uma linha, já que o histórico é uma lista
    # genérica, não variáveis fixas por passo.
    MAX_HISTORICO_PARAMETROS = 5
    historico_parametros = []

    def empilhar_historico():
        if not parametros_atuais:
            return
        historico_parametros.append({
            "parametros": dict(parametros_atuais),
            "tipo_origem": detalhe_selo_origem["tipo"],
            "detalhe_origem": detalhe_selo_origem["texto"],
        })
        del historico_parametros[:-MAX_HISTORICO_PARAMETROS]
        botao_desfazer.disabled = False

    def desfazer(e=None):
        if not historico_parametros:
            return
        estado = historico_parametros.pop()
        for chave, valor in estado["parametros"].items():
            if chave not in sliders_por_chave:
                continue
            slider, valor_texto, rotulo = sliders_por_chave[chave]
            slider.value = max(slider.min, min(slider.max, valor))
            valor_texto.value = f"{rotulo} = {valor:.3g}"
            parametros_atuais[chave] = valor
        if estado["tipo_origem"] is not None:
            atualizar_selo_origem(estado["tipo_origem"], estado["detalhe_origem"])
        botao_desfazer.disabled = not historico_parametros
        gerar_grafico(mensagem_extra="Última alteração de parâmetros desfeita.")

    botao_desfazer = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.UNDO), ft.Text("Desfazer")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=desfazer,
        disabled=True,
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

    def construir_sliders(nome_modelo):
        sliders_area.controls.clear()
        parametros_atuais.clear()
        sliders_por_chave.clear()
        # Histórico não atravessa troca de modelo — os parâmetros de um
        # modelo diferente não têm relação com os do anterior.
        historico_parametros.clear()
        botao_desfazer.disabled = True

        botao_buscar_banco.visible = nome_modelo in MODELOS_COM_BANCO_IPDB
        botao_regressao.visible = nome_modelo in PARAM_SLIDERS
        botao_desfazer.visible = nome_modelo in PARAM_SLIDERS
        nota_alpha_fixo.visible = (nome_modelo == "NRTL")

        specs = PARAM_SLIDERS.get(nome_modelo)
        if not specs:
            sliders_area.controls.append(
                ft.Text(
                    "Este modelo resolve os parâmetros automaticamente a "
                    "partir dos componentes escolhidos (grupos UNIFAC "
                    "clássicos e, para UNIQUAC, o banco de interação "
                    "binária IPDB/ChemSep) — sem sliders manuais por "
                    "enquanto.",
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
                    "r/q estruturais via grupos UNIFAC; a₁₂/a₂₁ do banco "
                    "IPDB/ChemSep (tabela 'ChemSep UNIQUAC') para o par "
                    "de componentes escolhido.",
                )
            return

        for spec in specs:
            parametros_atuais[spec["chave"]] = spec["inicial"]
            valor_texto = ft.Text(f"{spec['rotulo']} = {spec['inicial']:.3g}", width=110)

            def on_change(e, spec=spec, valor_texto=valor_texto):
                valor_texto.value = f"{spec['rotulo']} = {e.control.value:.3g}"
                page.update()

            def on_change_end(e, spec=spec):
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
                key=ft.ValueKey(f"slider_{chave_unica}"),
            )
            sliders_area.controls.append(
                ft.Row([valor_texto, slider], key=ft.ValueKey(f"linha_{chave_unica}"))
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

        empilhar_historico()
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
            valor_texto.value = f"{rotulo} = {valor:.3g}"
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

        empilhar_historico()
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
            valor_texto.value = f"{rotulo} = {valor:.3g}"
            parametros_atuais[chave] = valor

        poucos_pontos = resultado["graus_liberdade"] == 1
        aviso_gl = (
            " — poucos pontos (grau de liberdade mínimo), confiança baixa"
            if poucos_pontos else ""
        )
        atualizar_selo_origem(
            "calculado_poucos_pontos" if poucos_pontos else "calculado",
            f"Regressão de Barker a partir de {resultado['n_pontos']} "
            f"ponto(s) da tabela (grau de liberdade = "
            f"{resultado['graus_liberdade']}), resíduo RMS = "
            f"{resultado['residual_rms']:.4g}.",
        )
        gerar_grafico(
            mensagem_extra=(
                f"Parâmetros calculados por regressão (Barker) a partir de "
                f"{resultado['n_pontos']} ponto(s) da tabela{aviso_gl}."
            )
        )

    botao_regressao = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.FUNCTIONS), ft.Text("Calcular por Regressão (Barker)")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=calcular_por_regressao,
    )

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
            "Sistema", linha_componentes, linha_modelo_temperatura, expand=expand
        )

    def construir_card_parametros(expand=False):
        return cartao(
            "Parâmetros do modelo",
            sliders_area,
            selo_origem,
            nota_alpha_fixo,
            ft.Row(controls=[botao_buscar_banco, botao_regressao, botao_desfazer], wrap=True),
            expand=expand,
        )

    def construir_card_dados(expand=False):
        # Revertido (2026-09-28): embrulhar `dt` num Column/Row com altura
        # fixa e scroll (tentativa de caber tudo em 100% de zoom) quebrava
        # a renderização do ícone de excluir — sobrava só um traço
        # vermelho (parecendo "i"), e piorou pra sumir de vez ao adicionar
        # o scroll horizontal também. `dt` volta a ser filho direto do
        # card, sem wrapper; a altura extra das 10 linhas soma na página
        # (rolagem normal do navegador/`page.scroll` já cobre isso), em
        # vez de arriscar quebrar o DataTable de novo.
        return cartao(
            "Dados experimentais",
            dt,
            linha_botoes_tabela,
            botao_gerar_grafico,
            mensagem_status,
            linha_erro_comparativo,
            expand=expand,
            extra_titulo=ft.Row(controls=[botao_comparar, botao_limpar_tabela], spacing=4),
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

    def construir_grafico_p_xy(altura, expand=False):
        return cartao(
            "Diagrama P-x-y",
            ft.Container(content=legenda, height=ALTURA_LEGENDA, alignment=ft.Alignment.CENTER),
            ft.Container(content=chart, height=altura),
            expand=expand,
        )

    def construir_grafico_gamma(altura, expand=False):
        return cartao(
            "Coeficientes de atividade (ln γ)",
            ft.Container(content=legenda_gamma, height=ALTURA_LEGENDA, alignment=ft.Alignment.CENTER),
            ft.Container(content=chart_gamma, height=altura),
            expand=expand,
        )

    # Guarda o modo atual ("mobile"/"desktop") para só reconstruir o layout
    # quando ele realmente muda — não a cada pixel de resize. Sem isso, abrir
    # o seletor de arquivo nativo (botão "Importar CSV") no celular dispara
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
                        controls=[credito_app, botao_modo],
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
                    ft.Row(
                        controls=[credito_app, botao_modo],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
                    ft.Container(content=construir_card_dados(), width=420),
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    construir_grafico_p_xy(altura=320, expand=True),
                                    construir_grafico_gamma(altura=320, expand=True),
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
