import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import flet as ft


def gerar_grafico() -> bytes:
    x_list = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    y_xp1 = list(range(0, 11))
    y_yp1 = [1 - x for x in x_list]

    fig, ax = plt.subplots()
    ax.plot(x_list, y_xp1, color="blue", label="xp1")
    ax.plot(x_list, y_yp1, color="red", label="yp1")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend()
    ax.grid(True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def main(page: ft.Page):
    page.title = "Charts"
    img_data = gerar_grafico()
    page.add(ft.Image(src=img_data, expand=True, fit=ft.BoxFit.CONTAIN))


ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
