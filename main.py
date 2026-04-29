import flet as ft
# A biblioteca 'thermo' não está sendo usada, pode ser removida.
# import thermo as th 

def main(page: ft.Page):
  page.title = "Charts"
  P_list = [0,1,2,3,4,5,6,7,8,9,10]
  x_list = [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
  # Esta é uma forma mais 'pythônica' de criar y_list
  y_list = [1 - x for x in x_list] 
  
  points_xp1=[]
  points_yp1=[]
  
  # O loop pode ser simplificado
  for i, p_val in enumerate(P_list):
    points_xp1.append(ft.LineChartDataPoint(x_list[i], p_val))
    points_yp1.append(ft.LineChartDataPoint(y_list[i], p_val))

  # --- MUDANÇA PRINCIPAL AQUI ---
  # 1. Defina uma lista com menos labels para evitar sobreposição.
  bottom_axis_labels = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

  lines = ft.LineChart(
    data_series=[
      ft.LineChartData(
        data_points=points_xp1,
        color=ft.Colors.BLUE, # Adicionar cores ajuda a diferenciar as linhas
      ),
      ft.LineChartData(
        data_points=points_yp1,
        color=ft.Colors.RED,
      )
    ],
    # expand=True, # Adicione isso se quiser que o gráfico ocupe o espaço disponível
    bottom_axis=ft.ChartAxis(
        # 2. Use a nova lista de labels.
        #    Usei f-string para formatar o número com uma casa decimal (ex: "0.0").
        labels=[
            ft.ChartAxisLabel(
                value=val, 
                label=ft.Text(f"{val:.1f}", size=12)
            ) for val in bottom_axis_labels
        ],
        # 3. É uma boa prática definir um tamanho para a área dos labels.
        labels_size=40 
    ),
    left_axis=ft.ChartAxis(
        labels=[
            ft.ChartAxisLabel(value=i, label=ft.Text(i, size=12)) for i in range(0, 11, 2)
        ],
        labels_size=30
    ),
  )

  page.add(lines)

if __name__ == "__main__":
  ft.app(target=main, view=ft.AppView.WEB_BROWSER)

