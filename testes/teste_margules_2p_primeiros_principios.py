"""
Validação do `model_margules_2p` por primeiros princípios (2026-10-08).

A `thermo` não tem Margules, e a planilha XSEOS (única fonte anterior) traz só
três casas decimais de procedência sem rastreio. Este teste não depende de
nenhuma das duas: parte da DEFINIÇÃO do modelo e da termodinâmica.

O Margules 2-P é definido pela energia de Gibbs em excesso

    Gᴱ/RT = x₁·x₂·(A₂₁·x₁ + A₁₂·x₂)

e os coeficientes de atividade são as grandezas parciais molares de Gᴱ/RT:

    ln γ₁ = ∂(n·Gᴱ/RT)/∂n₁  (T, P, n₂ constantes),  idem para ln γ₂.

Aqui a derivada é feita pela definição, em n₁ e n₂ independentes, por passo
complexo (exato até a precisão de máquina, sem erro de diferença finita) — um
caminho independente da fórmula fechada que está em `calculos/gemini.py`.

Verifica, em x₁ de 0 a 1 (101 pontos, extremos inclusos) e em vários pares
(A₁₂, A₂₁), inclusive de sinais opostos e negativos:

  1. ln γ do modelo = grandeza parcial molar de Gᴱ/RT (definição);
  2. identidade de Euler: x₁·ln γ₁ + x₂·ln γ₂ = Gᴱ/RT;
  3. Gibbs-Duhem a T constante: x₁·d ln γ₁/dx₁ + x₂·d ln γ₂/dx₁ = 0;
  4. limites: ln γ₁(x₁=0) = A₁₂ e ln γ₂(x₁=1) = A₂₁ (diluição infinita) e
     γ = 1 no componente puro;
  5. com A₁₂ = A₂₁ = A, o resultado é o do `model_margules_1p`;
  6. o próprio teste detecta um modelo errado (parâmetros trocados).

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_margules_2p_primeiros_principios.py
"""

import numpy as np

from calculos.gemini import model_margules_1p, model_margules_2p

H = 1e-30  # passo complexo
X1 = np.linspace(0.0, 1.0, 101)
PARES = [
    (1.0, 0.5),
    (0.372, 0.198),   # valores da planilha XSEOS (MEK/tolueno, 323,15 K)
    (-0.8, -0.4),     # desvio negativo
    (2.2, 0.3),       # assimétrico
    (1.5, -0.7),      # sinais opostos
    (0.0, 0.0),       # solução ideal
]
TOL = 1e-12


def g_excesso(n1, n2, A12, A21):
    """n·Gᴱ/RT em mols n₁, n₂ independentes (forma homogênea de grau 1)."""
    return n1 * n2 * (A21 * n1 + A12 * n2) / (n1 + n2) ** 2


def ln_gamma_definicao(x1, A12, A21):
    """ln γᵢ = ∂(n·Gᴱ/RT)/∂nᵢ pela definição, por passo complexo, com n = 1."""
    x2 = 1.0 - x1
    ln1 = np.imag(g_excesso(x1 + 1j * H, x2, A12, A21)) / H
    ln2 = np.imag(g_excesso(x1, x2 + 1j * H, A12, A21)) / H
    return ln1, ln2


def ln_gamma_modelo(x1, A12, A21):
    g1, g2 = model_margules_2p(x1, {"A12": A12, "A21": A21})
    return np.log(g1), np.log(g2)


def checar(modelo, A12, A21):
    """Devolve a lista de falhas (texto) de `modelo` para o par dado."""
    falhas = []
    x2 = 1.0 - X1

    ln1 = np.array([modelo(x, A12, A21)[0] for x in X1])
    ln2 = np.array([modelo(x, A12, A21)[1] for x in X1])
    ref1, ref2 = ln_gamma_definicao(X1, A12, A21)

    # 1. definição (grandeza parcial molar)
    e = max(np.abs(ln1 - ref1).max(), np.abs(ln2 - ref2).max())
    if e > TOL:
        falhas.append(f"definição: erro máx {e:.2e}")

    # 2. Euler
    g = X1 * x2 * (A21 * X1 + A12 * x2)
    e = np.abs(X1 * ln1 + x2 * ln2 - g).max()
    if e > TOL:
        falhas.append(f"Euler: erro máx {e:.2e}")

    # 3. Gibbs-Duhem: derivada de ln γ pelo próprio modelo (passo complexo)
    d1 = np.array([np.imag(modelo(x + 1j * H, A12, A21)[0]) / H for x in X1])
    d2 = np.array([np.imag(modelo(x + 1j * H, A12, A21)[1]) / H for x in X1])
    e = np.abs(X1 * d1 + x2 * d2).max()
    if e > 1e-10:
        falhas.append(f"Gibbs-Duhem: erro máx {e:.2e}")

    # 4. limites
    l1_0 = modelo(0.0, A12, A21)[0]
    l2_1 = modelo(1.0, A12, A21)[1]
    l1_1 = modelo(1.0, A12, A21)[0]
    l2_0 = modelo(0.0, A12, A21)[1]
    for nome, obtido, esperado in (("ln γ₁(x₁=0)", l1_0, A12), ("ln γ₂(x₁=1)", l2_1, A21),
                                   ("ln γ₁(x₁=1)", l1_1, 0.0), ("ln γ₂(x₁=0)", l2_0, 0.0)):
        if abs(obtido - esperado) > TOL:
            falhas.append(f"limite {nome}: {obtido} ≠ {esperado}")
    return falhas


def modelo_real(x, A12, A21):
    return ln_gamma_modelo(x, A12, A21)


def modelo_parametros_trocados(x, A12, A21):
    return ln_gamma_modelo(x, A21, A12)


def main():
    todas = []
    print("Margules 2-P contra a definição (grandeza parcial molar de Gᴱ/RT):")
    for A12, A21 in PARES:
        falhas = checar(modelo_real, A12, A21)
        print(f"  A12={A12:6.3f}  A21={A21:6.3f}  {'OK' if not falhas else 'FALHA ' + '; '.join(falhas)}")
        todas += [(A12, A21, f) for f in falhas]

    # 5. A12 = A21 reduz ao Margules 1-P
    for A in (-1.3, 0.0, 0.5, 2.4):
        g1, g2 = model_margules_2p(X1, {"A12": A, "A21": A})
        h1, h2 = model_margules_1p(X1, {"A": A})
        e = max(np.abs(g1 - h1).max(), np.abs(g2 - h2).max())
        ok = e < TOL
        print(f"  A12=A21={A:5.2f} contra Margules 1-P: erro máx {e:.1e}  {'OK' if ok else 'FALHA'}")
        if not ok:
            todas.append((A, A, f"1-P: erro máx {e:.2e}"))

    # 6. o teste precisa reprovar um modelo errado
    pega = all(checar(modelo_parametros_trocados, A12, A21) for A12, A21 in PARES if A12 != A21)
    print(f"  detecta modelo com A12 e A21 trocados: {'OK' if pega else 'FALHA'}")
    if not pega:
        todas.append(("auto-teste", "o teste não reprovou o modelo errado"))

    print()
    if todas:
        print(f"FALHA: {todas}")
        raise SystemExit(1)
    print("OK: model_margules_2p confere com a definição termodinâmica em toda a faixa de x₁.")


if __name__ == "__main__":
    main()
