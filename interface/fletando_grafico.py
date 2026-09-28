import csv
import io
import math

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
    "calculado": (ft.Colors.ORANGE_100, ft.Colors.ORANGE_900, "Calculado"),
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
        {"chave": "A12", "rotulo": "A12", "min": -2.0, "max": 2.0, "inicial": 0.6},
        {"chave": "A21", "rotulo": "A21", "min": -2.0, "max": 2.0, "inicial": 0.3},
    ],
    "Van Laar": [
        {"chave": "A12", "rotulo": "A12", "min": -2.0, "max": 2.0, "inicial": 0.6},
        {"chave": "A21", "rotulo": "A21", "min": -2.0, "max": 2.0, "inicial": 0.4},
    ],
    "Wilson": [
        {"chave": "L12", "rotulo": "Λ12", "min": 0.01, "max": 3.0, "inicial": 0.8},
        {"chave": "L21", "rotulo": "Λ21", "min": 0.01, "max": 3.0, "inicial": 0.6},
    ],
    "NRTL": [
        {"chave": "tau12", "rotulo": "τ12", "min": -2.0, "max": 2.0, "inicial": 0.3},
        {"chave": "tau21", "rotulo": "τ21", "min": -2.0, "max": 2.0, "inicial": 0.3},
        {"chave": "alpha12", "rotulo": "α12", "min": 0.2, "max": 0.47, "inicial": 0.3},
    ],
}


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
    page.title = "Fletando - Gráfico Dinâmico"
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
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_700)

    # Variável de largura para manter tudo alinhado
    largura_coluna = 60

    # Ícone ⓘ tocável (não só hover) — o `tooltip` nativo do Flet depende de
    # hover ou long-press, e o usuário final deste app usa celular (sem
    # mouse); um toque simples no ícone não abria nada de forma confiável.
    # Em vez de tooltip, o ícone abre um diálogo com a explicação — mesmo
    # gesto (toque) em qualquer dispositivo. `obter_texto` é uma função sem
    # argumentos (não uma string fixa) para cobrir os casos em que a
    # explicação muda em tempo real (ex.: origem do parâmetro).
    def icone_info(obter_texto, titulo="Sobre este valor"):
        def abrir(e):
            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text(titulo),
                    content=ft.Text(obter_texto()),
                    actions=[ft.TextButton("Ok", on_click=lambda e: page.pop_dialog())],
                )
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
    def cartao(titulo, *controles, expand=False):
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD),
                        *controles,
                    ],
                    spacing=ESPACO_PEQUENO,
                ),
                padding=ESPACO_MEDIO,
            ),
            expand=expand,
        )

    # 1. Criação da Tabela Vazia
    dt = ft.DataTable(
        columns=[
            ft.DataColumn(
                label=ft.Text("P", width=largura_coluna, text_align=ft.TextAlign.CENTER)
            ),
            ft.DataColumn(
                label=ft.Text("x", width=largura_coluna, text_align=ft.TextAlign.CENTER)
            ),
            ft.DataColumn(
                label=ft.Text("y", width=largura_coluna, text_align=ft.TextAlign.CENTER)
            ),
            ft.DataColumn(label=ft.Text("", width=40)),  # Coluna vazia para a lixeira
        ],
        rows=[],  # Inicia sem linhas
    )

    # 2. Função geradora de linhas — `valores`, se informado, é (P, x, y) já
    # validado (usado pela importação de CSV) para pré-preencher a linha.
    def adicionar_linha(e=None, valores=None):
        textos_iniciais = [str(v) for v in valores] if valores else ["", "", ""]

        # Função para criar as caixas de texto padronizadas
        def criar_campo(valor_inicial):
            return ft.TextField(
                value=valor_inicial,
                width=largura_coluna,
                text_align=ft.TextAlign.CENTER,
                keyboard_type=ft.KeyboardType.NUMBER,
                border=ft.NoInputBorder(),
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

        # Adiciona a linha à tabela e atualiza a interface
        dt.rows.append(nova_linha)
        page.update()

    # Cria a primeira linha em branco automaticamente
    adicionar_linha(None)

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
    seletor_arquivo = ft.FilePicker()
    page.services.append(seletor_arquivo)

    async def importar_csv(e):
        arquivos = await seletor_arquivo.pick_files(
            dialog_title="Selecionar CSV (colunas P, x, y)",
            allowed_extensions=["csv"],
            with_data=True,
        )
        if not arquivos:
            return  # usuário cancelou a seleção

        try:
            texto = arquivos[0].bytes.decode("utf-8")
            pontos, ignoradas_csv = importar_pontos_csv(texto)
        except (ValueError, UnicodeDecodeError) as exc:
            mensagem_status.value = f"Falha ao importar CSV: {exc}."
            mensagem_status.color = ft.Colors.RED
            page.update()
            return

        if not pontos:
            mensagem_status.value = "Nenhum ponto válido encontrado no CSV."
            mensagem_status.color = ft.Colors.RED
            page.update()
            return

        dt.rows.clear()
        for ponto in pontos:
            adicionar_linha(valores=ponto)

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
    linha_botoes_tabela = ft.Row(controls=[botao_adicionar, botao_importar_csv])

    # 4. Gráfico P-x-y a partir dos dados brutos da tabela (Etapa 2 — sem
    # nenhum cálculo de modelo; só visualiza o que o usuário digitou).
    mensagem_status = ft.Text(value="", color=ft.Colors.RED)

    chart = fch.LineChart(
        data_series=[],
        min_x=0,
        max_x=1,
        min_y=0,
        max_y=1,
        expand=True,
        left_axis=fch.ChartAxis(label_size=40),
        # label_spacing fixa o intervalo entre marcações (0.1 em 0..1 = 11
        # rótulos). Sem isso, o eixo calculava um intervalo tão miúdo que
        # os rótulos apareciam repetidos e o gráfico pedia mais largura do
        # que cabia na tela (obrigando a diminuir o zoom do navegador).
        bottom_axis=fch.ChartAxis(label_size=32, label_spacing=0.1),
        visible=False,
    )

    def chip_legenda(cor, texto):
        return ft.Row(
            controls=[
                ft.Container(width=12, height=12, bgcolor=cor, border_radius=6),
                ft.Text(texto),
            ],
            tight=True,
        )

    # Chips da comparação calculado-vs-experimental (item 4 do roadmap) —
    # controles próprios (não construídos por chip_legenda direto na lista)
    # porque precisam ligar/desligar sozinhos: só aparecem depois de
    # "Comparar" ser clicado, e são escondidos de novo sempre que
    # gerar_grafico() reconstrói o gráfico do zero (modelo/tabela mudou).
    chip_liquido_comparativo = chip_legenda(ft.Colors.PURPLE, "líquido — comparativo")
    chip_vapor_comparativo = chip_legenda(ft.Colors.CYAN, "vapor — comparativo")
    chip_liquido_comparativo.visible = False
    chip_vapor_comparativo.visible = False

    # Mesma ideia, para o gráfico de ln γ (4b) — γ1/γ2 do modelo avaliados
    # exatamente nos x1 da tabela, junto com "Comparar".
    chip_gamma1_comparativo = chip_legenda(ft.Colors.PURPLE, "ln γ1 — comparativo")
    chip_gamma2_comparativo = chip_legenda(ft.Colors.CYAN, "ln γ2 — comparativo")
    chip_gamma1_comparativo.visible = False
    chip_gamma2_comparativo.visible = False

    # Resultado numérico da comparação (ΔP/Δy, seção "Próximos passos" item
    # 4 do CLAUDE.md) — mesmo padrão selo+ícone ⓘ já usado para a origem do
    # parâmetro: valor sempre visível, explicação do que cada Δ significa
    # só aparece ao tocar no ícone (diálogo — ver icone_info), sem poluir a
    # tela com texto fixo.
    texto_dp_comparativo = ft.Text("", size=13, weight=ft.FontWeight.BOLD)
    icone_dp_comparativo = icone_info(
        lambda: (
            "ΔP (RMS): erro relativo médio entre a pressão calculada pelo "
            "modelo e a pressão experimental digitada, ponto a ponto."
        ),
        titulo="O que é ΔP?",
    )
    texto_dy_comparativo = ft.Text("", size=13, weight=ft.FontWeight.BOLD)
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
        visible=False,
    )

    legenda = ft.Row(
        controls=[
            chip_legenda(ft.Colors.BLUE, "líquido — tabela (x)"),
            chip_legenda(ft.Colors.RED, "vapor — tabela (y)"),
            chip_legenda(ft.Colors.GREEN, "líquido — modelo"),
            chip_legenda(ft.Colors.ORANGE, "vapor — modelo"),
            chip_liquido_comparativo,
            chip_vapor_comparativo,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
        wrap=True,
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
        left_axis=fch.ChartAxis(label_size=40),
        bottom_axis=fch.ChartAxis(label_size=32, label_spacing=0.1),
        visible=False,
    )

    legenda_gamma = ft.Row(
        controls=[
            chip_legenda(ft.Colors.GREEN, "ln γ1 — modelo"),
            chip_legenda(ft.Colors.ORANGE, "ln γ2 — modelo"),
            chip_gamma1_comparativo,
            chip_gamma2_comparativo,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
        wrap=True,
        visible=False,
    )

    # Ponta a ponta: pontos digitados na tabela (discretos, sem interpolação —
    # decisão de 2026-08-19) + curva calculada por calculate_vle_isothermal
    # com o modelo/parâmetros/componentes/temperatura escolhidos, no mesmo
    # gráfico. Para Margules/Van Laar/Wilson/NRTL os parâmetros vêm dos
    # sliders (parametros_atuais); para UNIQUAC/UNIFAC vêm de
    # montar_parametros_automaticos, resolvido a partir dos componentes.
    def gerar_grafico(e=None, mensagem_extra=None):
        pontos_validos = []
        linhas_ignoradas = 0
        for linha in dt.rows:
            p_field, x_field, y_field = (linha.cells[i].content for i in range(3))
            try:
                pontos_validos.append(
                    parse_ponto(p_field.value, x_field.value, y_field.value)
                )
            except ValueError:
                linhas_ignoradas += 1

        # "Comparar" só faz sentido havendo dado experimental de verdade na
        # tabela para comparar contra — desabilitado sem isso (item 4 do
        # roadmap). Reconstruir o gráfico do zero também descarta qualquer
        # comparação calculada antes, pra não sobrar uma curva comparativa
        # desatualizada em relação ao modelo/tabela atual.
        botao_comparar.disabled = not pontos_validos
        chip_liquido_comparativo.visible = False
        chip_vapor_comparativo.visible = False
        chip_gamma1_comparativo.visible = False
        chip_gamma2_comparativo.visible = False
        linha_erro_comparativo.visible = False

        series = []
        series_gamma = []
        valores_P = []
        valores_gamma = []
        modelo_ok = False

        if pontos_validos:
            liquido, vapor = pontos_para_series(pontos_validos)
            series.append(fch.LineChartData(
                color=ft.Colors.BLUE,
                stroke_width=3,
                points=[fch.LineChartDataPoint(x, p) for x, p in liquido],
            ))
            series.append(fch.LineChartData(
                color=ft.Colors.RED,
                stroke_width=3,
                points=[fch.LineChartDataPoint(x, p) for x, p in vapor],
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
                color=ft.Colors.GREEN,
                stroke_width=2,
                points=[fch.LineChartDataPoint(x, p) for x, p in liquido_calc],
            ))
            series.append(fch.LineChartData(
                color=ft.Colors.ORANGE,
                stroke_width=2,
                points=[fch.LineChartDataPoint(y, p) for y, p in vapor_calc],
            ))
            valores_P += resultado["P_kPa"]

            ln_gamma1 = [math.log(g) for g in resultado["gamma1"]]
            ln_gamma2 = [math.log(g) for g in resultado["gamma2"]]
            series_gamma.append(fch.LineChartData(
                color=ft.Colors.GREEN,
                stroke_width=2,
                points=[fch.LineChartDataPoint(x, g) for x, g in zip(resultado["x1"], ln_gamma1)],
            ))
            series_gamma.append(fch.LineChartData(
                color=ft.Colors.ORANGE,
                stroke_width=2,
                points=[fch.LineChartDataPoint(x, g) for x, g in zip(resultado["x1"], ln_gamma2)],
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
            mensagem_status.color = ft.Colors.RED
            page.update()
            return

        chart.data_series = series
        min_y, max_y = min(valores_P), max(valores_P)
        if min_y == max_y:
            min_y, max_y = min_y - 1, max_y + 1
        margem = (max_y - min_y) * 0.1
        chart.min_y = min_y - margem
        chart.max_y = max_y + margem
        chart.visible = True
        legenda.visible = True

        if modelo_ok:
            chart_gamma.data_series = series_gamma
            min_g, max_g = min(valores_gamma), max(valores_gamma)
            if min_g == max_g:
                min_g, max_g = min_g - 1, max_g + 1
            margem_g = (max_g - min_g) * 0.1
            chart_gamma.min_y = min_g - margem_g
            chart_gamma.max_y = max_g + margem_g
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
        mensagem_status.color = ft.Colors.ORANGE if mensagens else ""

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
            mensagem_status.color = ft.Colors.RED
            page.update()
            return

        liquido_comp = sorted(zip(resultado["x1"], resultado["P_kPa"]))
        vapor_comp = sorted(zip(resultado["y1"], resultado["P_kPa"]))

        chart.data_series = chart.data_series + [
            fch.LineChartData(
                color=ft.Colors.PURPLE,
                stroke_width=2,
                points=[fch.LineChartDataPoint(x, p) for x, p in liquido_comp],
            ),
            fch.LineChartData(
                color=ft.Colors.CYAN,
                stroke_width=2,
                points=[fch.LineChartDataPoint(y, p) for y, p in vapor_comp],
            ),
        ]
        chip_liquido_comparativo.visible = True
        chip_vapor_comparativo.visible = True

        ln_gamma1_comp = sorted(zip(resultado["x1"], (math.log(g) for g in resultado["gamma1"])))
        ln_gamma2_comp = sorted(zip(resultado["x1"], (math.log(g) for g in resultado["gamma2"])))
        chart_gamma.data_series = chart_gamma.data_series + [
            fch.LineChartData(
                color=ft.Colors.PURPLE,
                stroke_width=2,
                points=[fch.LineChartDataPoint(x, g) for x, g in ln_gamma1_comp],
            ),
            fch.LineChartData(
                color=ft.Colors.CYAN,
                stroke_width=2,
                points=[fch.LineChartDataPoint(x, g) for x, g in ln_gamma2_comp],
            ),
        ]
        chip_gamma1_comparativo.visible = True
        chip_gamma2_comparativo.visible = True
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

    dropdown_modelo = ft.Dropdown(
        # "Gᴱ" (small capital E) some fontes/navegadores não têm o glifo —
        # visto em sessão real no Samsung Browser (2026-09-27): o rótulo
        # aparecia cortado como só "Modelo G". Texto simples renderiza
        # em qualquer fonte.
        label="Modelo GE",
        value=modelo_selecionado["nome"],
        options=[ft.dropdown.Option(nome) for nome in MODELS_GE],
        on_select=selecionar_modelo,
        width=220,
    )

    # 5b. Seletores de componente (nome/sinônimo/CAS — resolvidos pelo
    # thermo.Chemical dentro de calculate_vle_isothermal) e temperatura do
    # sistema. Recalculam a curva ao sair do campo (on_blur/on_submit) —
    # não a cada tecla, para não repetir Chemical() com nome incompleto.
    # Largura (220) igual à do dropdown_modelo, por pedido do autor — mantém
    # os campos da "linha do sistema" visualmente alinhados com ele; texto
    # centralizado, mesmo padrão já usado nos campos da tabela.
    campo_componente1 = ft.TextField(
        label="Componente 1", value="ethanol", width=220,
        text_align=ft.TextAlign.CENTER,
        on_blur=gerar_grafico, on_submit=gerar_grafico,
    )
    campo_componente2 = ft.TextField(
        label="Componente 2", value="water", width=220,
        text_align=ft.TextAlign.CENTER,
        on_blur=gerar_grafico, on_submit=gerar_grafico,
    )
    campo_temperatura = ft.TextField(
        label="Temperatura (°C)",
        value="70",
        width=220,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_blur=gerar_grafico,
        on_submit=gerar_grafico,
    )
    # `wrap=True` (mesmo padrão já usado nas linhas de botões do app):
    # 3 campos de 220px + espaçamento somam mais que a área útil de um
    # celular em retrato (~340-370px) — sem quebra, os campos ultrapassavam
    # a borda da tela desde a primeira versão (bug relatado pelo autor,
    # 2026-09-28).
    # `expand=True` é o que faz o `alignment=CENTER` valer: sem ele, a Row só
    # ocupa a largura dos próprios campos (não a da página), e centralizar
    # dentro dela mesma não tem efeito nenhum.
    linha_sistema = ft.Row(
        controls=[campo_componente1, campo_componente2, campo_temperatura],
        spacing=12,
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True,
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
    texto_selo_origem = ft.Text("", size=12, weight=ft.FontWeight.BOLD)
    chip_selo_origem = ft.Container(
        content=texto_selo_origem,
        padding=ft.Padding(8, 2, 8, 2),
        border_radius=10,
    )
    # Estado mutável lido por icone_selo_origem no momento do toque — não dá
    # para fechar o texto no clique do ícone como nas explicações fixas
    # (ΔP/Δy) porque este detalhe muda em tempo real (atualizar_selo_origem).
    detalhe_selo_origem = {"texto": ""}
    icone_selo_origem = icone_info(
        lambda: detalhe_selo_origem["texto"], titulo="Origem deste parâmetro"
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
        detalhe_selo_origem["texto"] = detalhe
        selo_origem.visible = True

    # Nota fixa do NRTL (requisito de UI da seção 2.8): α12 só é regredido
    # nunca — quando não vem do banco IPDB (que traz valor medido real),
    # fica fixado por convenção. Verdadeira nos dois casos, sem precisar
    # rastrear a origem de α12 separadamente do restante do selo.
    nota_alpha_fixo = ft.Row(
        controls=[
            ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=ft.Colors.GREY_600),
            ft.Text(
                "α12: quando não vier do banco IPDB, fica fixado por "
                "convenção (não é ajustado pela regressão de Barker) — "
                "valor de referência típico entre 0,2 e 0,47.",
                size=11,
                color=ft.Colors.GREY_600,
                italic=True,
            ),
        ],
        spacing=4,
        visible=False,
    )

    def construir_sliders(nome_modelo):
        sliders_area.controls.clear()
        parametros_atuais.clear()
        sliders_por_chave.clear()

        botao_buscar_banco.visible = nome_modelo in MODELOS_COM_BANCO_IPDB
        botao_regressao.visible = nome_modelo in PARAM_SLIDERS
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
                    color=ft.Colors.GREY_600,
                    italic=True,
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
                    "r/q estruturais via grupos UNIFAC; a12/a21 do banco "
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

            slider = ft.Slider(
                min=spec["min"],
                max=spec["max"],
                value=spec["inicial"],
                on_change=on_change,
                on_change_end=on_change_end,
                expand=True,
            )
            sliders_area.controls.append(ft.Row([valor_texto, slider]))
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
            mensagem_status.color = ft.Colors.RED
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
            mensagem_status.color = ft.Colors.RED
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
            mensagem_status.color = ft.Colors.RED
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

    def construir_coluna_controles():
        return ft.Column(
            controls=[
                cartao("Sistema", dropdown_modelo, linha_sistema),
                cartao(
                    "Parâmetros do modelo",
                    sliders_area,
                    selo_origem,
                    nota_alpha_fixo,
                    ft.Row(controls=[botao_buscar_banco, botao_regressao], wrap=True),
                ),
                cartao(
                    "Dados experimentais",
                    dt,
                    linha_botoes_tabela,
                    ft.Row(controls=[botao_gerar_grafico, botao_comparar], wrap=True),
                    mensagem_status,
                    linha_erro_comparativo,
                ),
            ],
            spacing=ESPACO_MEDIO,
        )

    # Um card por gráfico (não mais um "Resultados" combinado) — no desktop
    # ficam lado a lado (ver montar_layout), cada um com `expand=True` pra
    # dividir a largura disponível ao meio.
    # Altura fixa pra área da legenda — a legenda do P-x-y tem mais chips
    # (4 a 6: tabela x/y + modelo + comparativo) que a do ln γ (2 a 4: só
    # modelo + comparativo), então quebra em duas linhas mais cedo que a
    # outra ao dividir a largura do desktop ao meio. Sem essa altura fixa,
    # os dois cards ficavam com tamanhos diferentes (relatado pelo autor,
    # 2026-09-28) — reservando espaço pra até duas linhas nos dois, os
    # cards saem sempre do mesmo tamanho, quebre a legenda ou não.
    ALTURA_LEGENDA = 64

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

    def montar_layout(e=None):
        modo = "desktop" if (page.width or 0) >= LARGURA_BREAKPOINT_DESKTOP else "mobile"
        if modo == modo_layout_atual["modo"]:
            return
        modo_layout_atual["modo"] = modo

        # Espaço reservado antes do 1º controle: o rótulo flutuante de
        # dropdown_modelo colava na borda superior da tela e cortava pela
        # metade em landscape no celular (visto em sessão real,
        # 2026-09-27) — aumentar page.padding não teve nenhum efeito
        # visível, então em vez de padding é espaço de layout de verdade.
        # Inofensivo no desktop (só um respiro extra no topo).
        espaco_topo = ft.Container(height=24)

        if modo == "desktop":
            # Gráficos lado a lado, não mais empilhados (autor relatou,
            # 2026-09-28: empilhados exigiam reduzir o zoom do navegador a
            # 75-90% pra caber tudo sem rolar, e espremer o padding dos
            # cards pra compensar só deixou tudo feio). Lado a lado usa a
            # largura do desktop em vez de brigar por altura, e permite
            # devolver um espaçamento confortável (ESPACO_* acima).
            conteudo = ft.Row(
                controls=[
                    ft.Container(content=construir_coluna_controles(), width=420),
                    ft.Row(
                        controls=[
                            construir_grafico_p_xy(altura=320, expand=True),
                            construir_grafico_gamma(altura=320, expand=True),
                        ],
                        spacing=ESPACO_GRANDE,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                spacing=ESPACO_GRANDE,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        else:
            conteudo = ft.Column(
                controls=[
                    construir_coluna_controles(),
                    construir_grafico_p_xy(altura=300),
                    construir_grafico_gamma(altura=300),
                ],
                spacing=ESPACO_MEDIO,
            )

        page.controls = [espaco_topo, conteudo]
        page.update()

    page.on_resize = montar_layout
    montar_layout()
    gerar_grafico()


# Execução no Replit
if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
