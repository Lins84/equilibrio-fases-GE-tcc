import flet as ft


def main(page: ft.Page):
    page.title = "Fletando"
    
    tf = ft.TextField("oi",
                     border= ft.border.all(1),
                     whidth= 80,
                     height = 40,
                     padding = 4) 
    
    page.add(ft.Row(3*[tf]))


ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
