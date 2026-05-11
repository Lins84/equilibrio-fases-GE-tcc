import flet as ft


def main(page: ft.Page):
    page.title = "Fletando"

    def celula():
        return ft.TextField(
            value="oi",
            text_size=12,
            border=ft.InputBorder.NONE,
            width=80,
            height=40,
        )

    ct = ft.Container(
        content=ft.Row([celula(), celula(), celula()], spacing=0),
        border=ft.Border.all(1, ft.Colors.GREY_400),
        padding=4,
    )

    page.add(ct)


ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
