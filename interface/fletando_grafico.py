import csv
import io
import math

import flet as ft
import flet_charts as fch

from calculos.gemini import (
    MODELS_GE,
    calculate_vle_isothermal,
    montar_parametros_automaticos,
)

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


# Função principal que constrói a interface
def main(page: ft.Page):
    # Configuração básica da página
    page.title = "Fletando - Gráfico Dinâmico"
    page.padding = 20
    # Sem isso, conteúdo mais alto que a janela fica simplesmente
    # inacessível — sem scroll nem aviso, só dá pra ver diminuindo o zoom
    # do navegador até tudo caber de uma vez. Passou despercebido com um
    # gráfico só; com o segundo gráfico (ln γ vs x1) ficou grave.
    page.scroll = ft.ScrollMode.AUTO

    # Variável de largura para manter tudo alinhado
    largura_coluna = 60

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
                border=ft.InputBorder.NONE,
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
        bottom_axis=fch.ChartAxis(label_size=32),
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

    legenda = ft.Row(
        controls=[
            chip_legenda(ft.Colors.BLUE, "líquido — tabela (x)"),
            chip_legenda(ft.Colors.RED, "vapor — tabela (y)"),
            chip_legenda(ft.Colors.GREEN, "líquido — modelo"),
            chip_legenda(ft.Colors.ORANGE, "vapor — modelo"),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
        wrap=True,
        visible=False,
    )

    # 4b. Segundo gráfico: ln γ vs x1 (seção 2.2 do mapeamento) — só a curva
    # calculada pelo modelo (não dá para obter γ direto dos pontos brutos
    # da tabela sem inverter a Lei de Raoult, o que é o método indireto de
    # regressão já descartado na seção 2.8; fica reservado para quando essa
    # regressão existir).
    chart_gamma = fch.LineChart(
        data_series=[],
        min_x=0,
        max_x=1,
        min_y=0,
        max_y=1,
        expand=True,
        left_axis=fch.ChartAxis(label_size=40),
        bottom_axis=fch.ChartAxis(label_size=32),
        visible=False,
    )

    legenda_gamma = ft.Row(
        controls=[
            chip_legenda(ft.Colors.GREEN, "ln γ1 — modelo"),
            chip_legenda(ft.Colors.ORANGE, "ln γ2 — modelo"),
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

    # 5. Dropdown de seleção do modelo Gᴱ — troca o modelo e já recalcula
    # a curva (gerar_grafico) com os parâmetros do novo modelo.
    modelo_selecionado = {"nome": next(iter(MODELS_GE))}

    def selecionar_modelo(e):
        modelo_selecionado["nome"] = e.control.value
        construir_sliders(modelo_selecionado["nome"])
        gerar_grafico()

    dropdown_modelo = ft.Dropdown(
        label="Modelo Gᴱ",
        value=modelo_selecionado["nome"],
        options=[ft.dropdown.Option(nome) for nome in MODELS_GE],
        on_select=selecionar_modelo,
        width=220,
    )

    # 5b. Seletores de componente (nome/sinônimo/CAS — resolvidos pelo
    # thermo.Chemical dentro de calculate_vle_isothermal) e temperatura do
    # sistema. Recalculam a curva ao sair do campo (on_blur/on_submit) —
    # não a cada tecla, para não repetir Chemical() com nome incompleto.
    campo_componente1 = ft.TextField(
        label="Componente 1", value="ethanol", width=180,
        on_blur=gerar_grafico, on_submit=gerar_grafico,
    )
    campo_componente2 = ft.TextField(
        label="Componente 2", value="water", width=180,
        on_blur=gerar_grafico, on_submit=gerar_grafico,
    )
    campo_temperatura = ft.TextField(
        label="Temperatura (°C)",
        value="70",
        width=150,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_blur=gerar_grafico,
        on_submit=gerar_grafico,
    )
    linha_sistema = ft.Row(
        controls=[campo_componente1, campo_componente2, campo_temperatura],
        spacing=12,
    )

    # 6. Sliders dos parâmetros do modelo escolhido — guardam os valores
    # atuais em parametros_atuais; soltar o slider (on_change_end) já
    # recalcula a curva via gerar_grafico.
    parametros_atuais = {}
    sliders_area = ft.Column(spacing=2)

    def construir_sliders(nome_modelo):
        sliders_area.controls.clear()
        parametros_atuais.clear()

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
            return

        for spec in specs:
            parametros_atuais[spec["chave"]] = spec["inicial"]
            valor_texto = ft.Text(f"{spec['rotulo']} = {spec['inicial']:.3g}", width=110)

            def on_change(e, spec=spec, valor_texto=valor_texto):
                valor_texto.value = f"{spec['rotulo']} = {e.control.value:.3g}"
                page.update()

            def on_change_end(e, spec=spec):
                parametros_atuais[spec["chave"]] = e.control.value
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

    construir_sliders(modelo_selecionado["nome"])

    # Adiciona a tabela, os botões, o gráfico e as mensagens à página
    page.add(
        dropdown_modelo,
        linha_sistema,
        sliders_area,
        dt,
        linha_botoes_tabela,
        botao_gerar_grafico,
        mensagem_status,
        legenda,
        ft.Container(content=chart, height=300),
        legenda_gamma,
        ft.Container(content=chart_gamma, height=300),
    )

    gerar_grafico()


# Execução no Replit
if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
