"""Teste manual: diagrama P-x-y do sistema dioxano(1)/metanol(2) a 70 C,
usando o modelo NRTL com parametros reais do thermo.interaction_parameters.IPDB
(via gemini.nrtl_params_from_ipdb), renderizado com flet_charts.

Combina gemini.py (calculo) + o padrao de grafico de fletando_grafico.py,
sem alterar nenhum dos dois arquivos do projeto.
"""
import flet as ft
import flet_charts as fch

from calculos.gemini import calculate_vle_isothermal, nrtl_params_from_ipdb

CAS_DIOXANO = "123-91-1"
CAS_METANOL = "67-56-1"
T_C = 70.0


def main(page: ft.Page):
    page.title = "Teste NRTL - Dioxano/Metanol (dados reais IPDB)"
    page.padding = 20

    params = nrtl_params_from_ipdb(CAS_DIOXANO, CAS_METANOL, T_C + 273.15)
    resultado = calculate_vle_isothermal(
        "1,4-dioxane", "methanol", T_C, "NRTL", params
    )

    liquido = list(zip(resultado["x1"], resultado["P_kPa"]))
    vapor = list(zip(resultado["y1"], resultado["P_kPa"]))

    min_p, max_p = min(resultado["P_kPa"]), max(resultado["P_kPa"])
    margem = (max_p - min_p) * 0.1

    chart = fch.LineChart(
        data_series=[
            fch.LineChartData(
                color=ft.Colors.BLUE,
                stroke_width=3,
                points=[fch.LineChartDataPoint(x, p) for x, p in liquido],
            ),
            fch.LineChartData(
                color=ft.Colors.RED,
                stroke_width=3,
                points=[fch.LineChartDataPoint(y, p) for y, p in vapor],
            ),
        ],
        min_x=0,
        max_x=1,
        min_y=min_p - margem,
        max_y=max_p + margem,
        expand=True,
        left_axis=fch.ChartAxis(label_size=40),
        bottom_axis=fch.ChartAxis(label_size=32),
    )

    legenda = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(width=12, height=12, bgcolor=ft.Colors.BLUE, border_radius=6),
                    ft.Text("líquido (x1 dioxano)"),
                ],
                tight=True,
            ),
            ft.Row(
                controls=[
                    ft.Container(width=12, height=12, bgcolor=ft.Colors.RED, border_radius=6),
                    ft.Text("vapor (y1 dioxano)"),
                ],
                tight=True,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
    )

    titulo = ft.Text(
        f"1,4-Dioxano (1) / Metanol (2) — NRTL, T = {T_C} °C — params via thermo IPDB",
        size=18,
        weight=ft.FontWeight.BOLD,
    )
    params_txt = ft.Text(
        f"τ12={params['tau12']:.4f}  τ21={params['tau21']:.4f}  α12={params['alpha12']:.4f}  "
        f"|  P: {min_p:.1f}–{max_p:.1f} kPa",
        size=12,
        color=ft.Colors.GREY_600,
    )

    page.add(
        titulo,
        params_txt,
        ft.Container(content=chart, height=400),
        legenda,
    )


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
