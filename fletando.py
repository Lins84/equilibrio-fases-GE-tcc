import flet as ft

def main(page: ft.Page):
   page.title = "Fletando"

   #def tabela (tf):
      # return
   
   dt=ft.DataTable(
      columns=[
         ft.DataColumn (label=ft.Text('oi'))
      ]

      
   )
   
   #tf = ft.TextField("oi")
   #ln =ft.Row(3*[tf])

   #linha = [ln]
   ct = ft.Container(
       content= dt,
    #   border= ft.Border.all(1),
                   # width= 80,
                   # height =40,
                    #padding =4
   )
   page.add(dt
   #   ft.Row([ct])
   )

ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)