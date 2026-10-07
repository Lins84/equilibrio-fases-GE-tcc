"""
Testes da leitura de pontos P/x/y por texto colado e por CSV
(botão "Importar dados", 2026-10-06). Lógica pura, mas vive em
`interface/fletando_grafico.py`, então exige flet instalado.

Roda a partir da raiz: `PYTHONPATH=. .venv/bin/python testes/teste_importar_texto.py`
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "interface"))

from fletando_grafico import (
    EXEMPLOS_NIST,
    carregar_exemplo_nist,
    importar_pontos_csv,
    importar_pontos_texto,
)

ESPERADO = [(12.33, 0.0, 0.0), (16.51, 0.01, 0.091)]


def teste_formatos_aceitos():
    casos = {
        "espaco": "12.33 0.0 0.0\n16.51 0.01 0.091",
        "espaco_virgula_decimal": "12,33 0,0 0,0\n16,51 0,01 0,091",
        "tab_excel": "12,33\t0,0\t0,0\n16,51\t0,01\t0,091",
        "ponto_e_virgula": "12,33;0,0;0,0\n16,51;0,01;0,091",
        "virgula": "12.33,0.0,0.0\n16.51,0.01,0.091",
        "linhas_em_branco": "\n12.33 0.0 0.0\n\n16.51 0.01 0.091\n\n",
    }
    for nome, texto in casos.items():
        pontos, ignoradas = importar_pontos_texto(texto)
        assert pontos == ESPERADO and ignoradas == 0, (nome, pontos, ignoradas)
    print("OK: separadores e decimal com vírgula.")


def teste_cabecalho():
    pontos, _ = importar_pontos_texto("P,x,y\n12.33,0.0,0.0\n16.51,0.01,0.091")
    assert pontos == ESPERADO
    # Cabeçalho em outra ordem reordena as colunas.
    pontos, _ = importar_pontos_texto("y x P\n0.0 0.0 12.33\n0.091 0.01 16.51")
    assert pontos == ESPERADO
    print("OK: cabeçalho opcional, em qualquer ordem.")


def teste_erros():
    for ruim in ("", "   \n  ", "a b c\n1 2 3"):
        try:
            importar_pontos_texto(ruim)
        except ValueError:
            continue
        raise AssertionError(f"deveria falhar: {ruim!r}")
    pontos, ignoradas = importar_pontos_texto("12.33 0.0 0.0\nabc 1 2\n5 6\n16.51 0.01 0.091")
    assert pontos == ESPERADO and ignoradas == 2, (pontos, ignoradas)
    print("OK: erros de cabeçalho e linhas inválidas contadas.")


def teste_csv():
    pontos, ignoradas = importar_pontos_csv("P,x,y\n12.33,0.0,0.0\n16.51,0.01,0.091\n")
    assert pontos == ESPERADO and ignoradas == 0, (pontos, ignoradas)
    print("OK: leitura de CSV.")


def teste_exemplos_nist():
    esperado = {
        "etanol/água, 90 °C": 12,
        "etanol/água, 108 °C": 26,
        "metanol/dimetilbuteno, 70 °C": 22,
        "clorofórmio/MEK, 30 °C": 22,
    }
    assert {ex["rotulo"] for ex in EXEMPLOS_NIST} == set(esperado), "lista de exemplos mudou"
    for ex in EXEMPLOS_NIST:
        pontos = carregar_exemplo_nist(ex)
        assert len(pontos) == esperado[ex["rotulo"]], (ex["rotulo"], len(pontos))
        assert all(0 <= x <= 1 and 0 <= y <= 1 and P > 0 for P, x, y in pontos)
        assert [p[1] for p in pontos] == sorted(p[1] for p in pontos)
        assert ex["componente1"] and ex["componente2"] and ex["fonte"] and ex["nota"]
    assert carregar_exemplo_nist({**EXEMPLOS_NIST[0], "T_K": 999.9}) == []
    print("OK: exemplos NIST carregam (12, 26, 22 e 22 pontos), ordenados por x.")


if __name__ == "__main__":
    teste_formatos_aceitos()
    teste_cabecalho()
    teste_erros()
    teste_csv()
    teste_exemplos_nist()
    print("Todos os testes passaram.")
