import flet as ft

def main(page: ft.Page):
    page.title = "Fletando"
    page.add(ft.TextField(label='Oiew!'))

ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000, no_cdn=True)
