import flet as ft


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

    # Adiciona a tabela e o botão inferior à página
    page.add(dt, botao_adicionar)


# Execução no Replit
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=5000)
