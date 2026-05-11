import flet as ft


def main(page: ft.Page):
    page.title = "Fletando"

    
    tf = ft.TextField("oi")
                      
    ct = ft.Container(
        content=tf,
        border=ft.Border.all(1),
        width=80,
        height=40,
        padding=4)
    
    page.add(ft.Row(3*[ct]))


ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
