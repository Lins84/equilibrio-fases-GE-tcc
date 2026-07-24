"""
Testes da lógica pura de leitura da tabela P/x/y (Etapa 2 — gráfico a
partir dos dados brutos da tabela, sem cálculo de modelo).

`parse_ponto` e `pontos_para_series` não dependem de `flet`/`flet_charts`,
então este teste roda com `python3 testes/teste_parse_ponto_tabela.py` sem
precisar instalar nada além da lib padrão.
"""

from fletando import parse_ponto, pontos_para_series


def teste_parse_ponto_valores_validos():
    assert parse_ponto("101.3", "0.5", "0.7") == (101.3, 0.5, 0.7)
    assert parse_ponto("101,3".replace(",", "."), "0", "1") == (101.3, 0.0, 1.0)
    assert parse_ponto("-5", "0.1", "0.2") == (-5.0, 0.1, 0.2)
    print("OK: parse_ponto aceita valores numéricos válidos.")


def teste_parse_ponto_valores_invalidos():
    casos_invalidos = [
        ("", "0.5", "0.7"),      # P vazio
        ("101.3", "", "0.7"),    # x vazio
        ("101.3", "0.5", ""),    # y vazio
        ("abc", "0.5", "0.7"),   # P não numérico
        ("101.3", "x1", "0.7"),  # x não numérico
    ]
    for p_str, x_str, y_str in casos_invalidos:
        try:
            parse_ponto(p_str, x_str, y_str)
            raise AssertionError(f"Esperava ValueError para {(p_str, x_str, y_str)!r}")
        except ValueError:
            pass
    print("OK: parse_ponto levanta ValueError para campos vazios/não numéricos.")


def teste_pontos_para_series():
    pontos = [
        (101.3, 0.0, 0.0),
        (95.0, 0.5, 0.7),
        (80.0, 1.0, 1.0),
    ]
    liquido, vapor = pontos_para_series(pontos)

    assert liquido == [(0.0, 101.3), (0.5, 95.0), (1.0, 80.0)]
    assert vapor == [(0.0, 101.3), (0.7, 95.0), (1.0, 80.0)]
    print("OK: pontos_para_series monta as séries líquido/vapor corretamente.")


def teste_pontos_para_series_ordena_por_composicao():
    # Pontos fora de ordem na tabela devem sair ordenados por composição.
    pontos = [
        (80.0, 1.0, 1.0),
        (101.3, 0.0, 0.0),
        (95.0, 0.5, 0.7),
    ]
    liquido, vapor = pontos_para_series(pontos)

    assert [x for x, _ in liquido] == [0.0, 0.5, 1.0]
    assert [y for y, _ in vapor] == [0.0, 0.7, 1.0]
    print("OK: pontos_para_series ordena as séries pela composição.")


if __name__ == "__main__":
    teste_parse_ponto_valores_validos()
    teste_parse_ponto_valores_invalidos()
    teste_pontos_para_series()
    teste_pontos_para_series_ordena_por_composicao()
    print("\nTodos os testes passaram.")
