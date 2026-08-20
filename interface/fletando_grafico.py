import flet as ft
import flet_charts as fch


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


# Função principal que constrói a interface
def main(page: ft.Page):
    # Configuração básica da página
    page.title = "Fletando - Gráfico Dinâmico"
    page.padding = 20

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

    # 2. Função geradora de linhas
    def adicionar_linha(e):
        # Função para criar as caixas de texto padronizadas
        def criar_campo():
            return ft.TextField(
                value="",
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
            ft.DataCell(criar_campo()),
            ft.DataCell(criar_campo()),
            ft.DataCell(criar_campo()),
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

    legenda = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(width=12, height=12, bgcolor=ft.Colors.BLUE, border_radius=6),
                    ft.Text("líquido (x)"),
                ],
                tight=True,
            ),
            ft.Row(
                controls=[
                    ft.Container(width=12, height=12, bgcolor=ft.Colors.RED, border_radius=6),
                    ft.Text("vapor (y)"),
                ],
                tight=True,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
        visible=False,
    )

    def gerar_grafico(e):
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

        if not pontos_validos:
            chart.visible = False
            legenda.visible = False
            mensagem_status.value = (
                "Adicione ao menos um ponto válido (P, x, y preenchidos "
                "com números) para gerar o gráfico."
            )
            mensagem_status.color = ft.Colors.RED
            page.update()
            return

        liquido, vapor = pontos_para_series(pontos_validos)
        chart.data_series = [
            fch.LineChartData(
                color=ft.Colors.BLUE,
                stroke_width=3,
                points=[fch.LineChartDataPoint(x, p) for x, p in liquido],
            ),
            fch.LineChartData(
                color=ft.Colors.RED,
                stroke_width=3,
                points=[fch.LineChartDataPoint(x, p) for x, p in vapor],
            ),
        ]

        valores_P = [p for _, p in liquido] + [p for _, p in vapor]
        min_y, max_y = min(valores_P), max(valores_P)
        if min_y == max_y:
            min_y, max_y = min_y - 1, max_y + 1
        margem = (max_y - min_y) * 0.1
        chart.min_y = min_y - margem
        chart.max_y = max_y + margem
        chart.visible = True
        legenda.visible = True

        if linhas_ignoradas:
            mensagem_status.value = f"{linhas_ignoradas} linha(s) ignorada(s) por dado inválido."
            mensagem_status.color = ft.Colors.ORANGE
        else:
            mensagem_status.value = ""

        page.update()

    botao_gerar_grafico = ft.Button(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.SHOW_CHART), ft.Text("Gerar Gráfico")],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=gerar_grafico,
    )

    # Adiciona a tabela, os botões, o gráfico e as mensagens à página
    page.add(
        dt,
        botao_adicionar,
        botao_gerar_grafico,
        mensagem_status,
        legenda,
        ft.Container(content=chart, height=300),
    )


# Execução no Replit
if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
