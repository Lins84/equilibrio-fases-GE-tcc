"""
Testes da leitura de pontos P/x/y por texto colado e do exemplo embutido
(botão "Importar dados", 2026-10-06). Lógica pura, mas vive em
`interface/fletando_grafico.py`, então exige flet instalado.

Roda a partir da raiz: `PYTHONPATH=. .venv/bin/python testes/teste_importar_texto.py`
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "interface"))

from fletando_grafico import (
    EXEMPLOS_CSV,
    PASTA_EXEMPLOS,
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


def teste_exemplos_existem_e_leem():
    assert EXEMPLOS_CSV
    for rotulo, arquivo in EXEMPLOS_CSV.items():
        texto = (PASTA_EXEMPLOS / arquivo).read_text(encoding="utf-8")
        pontos, ignoradas = importar_pontos_csv(texto)
        assert len(pontos) == 14 and ignoradas == 0, (rotulo, len(pontos), ignoradas)
    print("OK: exemplos embutidos carregam.")


if __name__ == "__main__":
    teste_formatos_aceitos()
    teste_cabecalho()
    teste_erros()
    teste_exemplos_existem_e_leem()
    print("Todos os testes passaram.")
