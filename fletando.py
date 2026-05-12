import flet as ft


def main(page: ft.Page):
    page.title = "Fletando"

    def celula(valor=""):
        return ft.Container(
            content=ft.TextField(
                value=valor,
                text_size=12,
                border=ft.InputBorder.NONE,
                height=32,
                content_padding=ft.padding.symmetric(horizontal=6, vertical=0),
            ),
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_600),
                bottom=ft.BorderSide(1, ft.Colors.GREY_600),
                left=ft.BorderSide(1, ft.Colors.GREY_600),
                right=ft.BorderSide(0),
            ),
            width=100,
            height=32,
        )

    ultima_celula = ft.Container(
        content=ft.TextField(
            value="",
            text_size=12,
            border=ft.InputBorder.NONE,
            height=32,
            content_padding=ft.padding.symmetric(horizontal=6, vertical=0),
        ),
        border=ft.Border.all(1, ft.Colors.GREY_600),
        width=100,
        height=32,
    )

    page.add(ft.Row([celula(), celula(), ultima_celula], spacing=0))


ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
