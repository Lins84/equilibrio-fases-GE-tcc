"""Teste de regressão de `limites_redondos` (interface/fletando_grafico.py).

Bug de 2026-10-03: mexendo no slider do Margules 1P, o "zero" do slider sai
como A ≈ 1e-16 (ruído de ponto flutuante), o ln γ fica praticamente constante
e o passo do eixo vertical, arredondado a 10 casas, virava 0 — o Flet
estourava "label_spacing cannot be 0". Aqui: o passo é sempre positivo, em
intervalos degenerados e ao varrer o slider inteiro.

Rodar a partir da raiz: `uv run python testes/teste_limites_redondos.py`
(precisa de `flet` e das dependências do projeto instaladas).
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "interface"))

import numpy as np

from calculos.gemini import MODELS_GE
from fletando_grafico import limites_redondos


def teste_passo_positivo_em_intervalos_degenerados():
    casos = [
        (0.0, 0.0),
        (-1e-17, 2e-17),
        (1e-16, 1e-16),
        (1e-12, 1e-12 + 1e-14),
        (70.0, 70.0 + 1e-13),
        (0.0, 1e-9),
    ]
    for vmin, vmax in casos:
        inicio, fim, passo = limites_redondos(vmin, vmax)
        assert passo > 0, f"passo <= 0 para {(vmin, vmax)}: {(inicio, fim, passo)}"
        assert inicio <= vmin and fim >= vmax, f"limites não cobrem {(vmin, vmax)}"
    print("OK: passo sempre positivo em intervalos degenerados.")


def teste_intervalos_normais_nao_mudaram():
    assert limites_redondos(27.1, 76.1) == (20, 80, 10)
    assert limites_redondos(-0.05, 0.55) == (-0.1, 0.6, 0.1)
    print("OK: intervalos normais seguem com os mesmos limites e passo.")


def teste_varredura_do_slider_margules_1p():
    x1 = np.linspace(0, 1, 101)
    for A in np.linspace(-3, 3, 61):
        g1, g2 = MODELS_GE["Margules (1-P)"](x1, {"A": float(A)})
        ln_g = np.concatenate([np.log(g1), np.log(g2)])
        margem = (ln_g.max() - ln_g.min()) * 0.05
        _, _, passo = limites_redondos(ln_g.min() - margem, ln_g.max() + margem)
        assert passo > 0, f"passo <= 0 com A = {A}"
    print("OK: varredura de A (-3 a 3) sempre gera passo positivo.")


if __name__ == "__main__":
    teste_passo_positivo_em_intervalos_degenerados()
    teste_intervalos_normais_nao_mudaram()
    teste_varredura_do_slider_margules_1p()
    print("\nTodos os testes passaram.")
