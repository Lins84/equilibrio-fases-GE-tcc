"""Margules e Van Laar contra as equações de Smith, Van Ness e Abbott (2026-10-21).

Segunda fonte de livro para as fórmulas que a `thermo` não tem. Smith, J. M.;
Van Ness, H. C.; Abbott, M. M.; Swihart, M. T. Introduction to Chemical Engineering
Thermodynamics, 8ª ed., McGraw-Hill Education, 2018, cap. 13, seção 13.4:

  Margules 1-P (caso A0 da expansão de Redlich/Kister, p. 470):
    (13.37) ln γ1 = A0 x2²          (13.38) ln γ2 = A0 x1²
  Margules 2-P (p. 470):
    (13.39) GE/RT = (A21 x1 + A12 x2) x1 x2
    (13.40) ln γ1 = x2² [A12 + 2 (A21 − A12) x1]
    (13.41) ln γ2 = x1² [A21 + 2 (A12 − A21) x2]
    com A0 + A1 = A21 e A0 − A1 = A12; ln γ1∞ = A12 e ln γ2∞ = A21.
  Van Laar (pp. 470-471):
    (13.42) GE/(x1 x2 RT) = A'12 A'21 / (A'12 x1 + A'21 x2)
    (13.43) ln γ1 = A'12 (1 + A'12 x1 / (A'21 x2))^−2
    (13.44) ln γ2 = A'21 (1 + A'21 x2 / (A'12 x1))^−2
    com ln γ1∞ = A'12 e ln γ2∞ = A'21.
  Estabilidade da fase líquida (Eq. 12.5 e Exemplo 15.4, p. 597): para
    GE/RT = A x1 x2, a mistura é estável em toda a faixa se e só se A < 2.

As equações foram transcritas à parte (não importadas do app) e comparadas com
`MODELS_GE` em 101 composições, extremos inclusos (nos extremos, pelos limites
analíticos que o próprio livro dá: ln γ1∞, ln γ2∞ e ln γ = 0 no componente puro).
Os parâmetros do app (A, A12, A21) são adimensionais, como os do livro nessa seção.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_smith_van_ness_formulas.py
"""

import sys

import numpy as np

from calculos.gemini import MODELS_GE, detectar_instabilidade_liquida

todos_ok = True


def conferir(descricao, condicao, detalhe=""):
    global todos_ok
    print(f"  [{descricao}] {detalhe}-> {'OK' if condicao else 'FALHA'}")
    todos_ok &= bool(condicao)


def modelo(nome, params, x1):
    # ponto a ponto: o Van Laar do app trata os extremos com `if x1 == 0`, só escalar
    pares = [MODELS_GE[nome](float(x), params) for x in np.atleast_1d(x1)]
    return np.log([p[0] for p in pares]), np.log([p[1] for p in pares])


X1 = np.linspace(0.0, 1.0, 101)
X1_INT = X1[1:-1]


# ---- transcrição do livro -------------------------------------------------------

def livro_margules_1p(x1, A0):
    x2 = 1 - x1
    return A0 * x2**2, A0 * x1**2  # (13.37), (13.38)


def livro_margules_2p(x1, A12, A21):
    x2 = 1 - x1
    ln1 = x2**2 * (A12 + 2 * (A21 - A12) * x1)  # (13.40)
    ln2 = x1**2 * (A21 + 2 * (A12 - A21) * x2)  # (13.41)
    return ln1, ln2


def livro_ge_margules_2p(x1, A12, A21):
    x2 = 1 - x1
    return (A21 * x1 + A12 * x2) * x1 * x2  # (13.39)


def livro_van_laar(x1, A12, A21):
    x2 = 1 - x1
    ln1 = A12 * (1 + A12 * x1 / (A21 * x2)) ** -2  # (13.43)
    ln2 = A21 * (1 + A21 * x2 / (A12 * x1)) ** -2  # (13.44)
    return ln1, ln2


def livro_ge_van_laar(x1, A12, A21):
    x2 = 1 - x1
    return A12 * A21 * x1 * x2 / (A12 * x1 + A21 * x2)  # (13.42) vezes x1 x2


print("== Margules 1-P: Eqs. 13.37 e 13.38 ==")
for A0 in (-1.2, -0.3, 0.5, 1.2, 2.25):
    l1, l2 = livro_margules_1p(X1, A0)
    m1, m2 = modelo("Margules (1-P)", {"A": A0}, X1)
    erro = max(np.max(np.abs(l1 - m1)), np.max(np.abs(l2 - m2)))
    conferir(f"A0 = {A0}", erro < 1e-12, f"erro máx. {erro:.1e} ")

print("== Margules 2-P: Eqs. 13.39 a 13.41 e definição dos parâmetros ==")
for A12, A21 in ((1.35, 0.70), (0.372, 0.198), (-0.72, -1.27), (2.26, 2.25), (1.2, -0.4)):
    l1, l2 = livro_margules_2p(X1, A12, A21)
    m1, m2 = modelo("Margules (2-P)", {"A12": A12, "A21": A21}, X1)
    erro = max(np.max(np.abs(l1 - m1)), np.max(np.abs(l2 - m2)))
    conferir(f"A12 = {A12}, A21 = {A21}", erro < 1e-12, f"erro máx. {erro:.1e} ")
    # GE/RT = x1 ln γ1 + x2 ln γ2 (Koretsky, Eq. 7.49) deve dar a Eq. 13.39
    ge_app = X1 * m1 + (1 - X1) * m2
    erro_ge = np.max(np.abs(ge_app - livro_ge_margules_2p(X1, A12, A21)))
    conferir("  GE/RT = Σ xi ln γi igual à Eq. 13.39", erro_ge < 1e-12, f"erro máx. {erro_ge:.1e} ")
    conferir(
        "  diluição infinita: ln γ1(0) = A12 e ln γ2(1) = A21",
        abs(m1[0] - A12) < 1e-12 and abs(m2[-1] - A21) < 1e-12,
    )
    # A0 + A1 = A21 e A0 − A1 = A12 -> A0 = (A12 + A21)/2, A1 = (A21 − A12)/2
    A0, A1 = (A12 + A21) / 2, (A21 - A12) / 2
    Y = A0 + A1 * (2 * X1 - 1)  # Y = GE/(x1 x2 RT) pela expansão de Redlich/Kister
    erro_y = np.max(np.abs(X1[1:-1] * (1 - X1[1:-1]) * Y[1:-1] - ge_app[1:-1]))
    conferir("  expansão de Redlich/Kister (A0, A1) igual à Eq. 13.39", erro_y < 1e-12, f"erro máx. {erro_y:.1e} ")

print("== Van Laar: Eqs. 13.42 a 13.44 (só pares de mesmo sinal, como no teste do Koretsky) ==")
for A12, A21 in ((1.35, 0.70), (2.06, 1.2), (0.5, 0.5), (-0.97, -1.33), (1.772, 0.9042)):
    l1, l2 = livro_van_laar(X1_INT, A12, A21)
    m1, m2 = modelo("Van Laar", {"A12": A12, "A21": A21}, X1_INT)
    erro = max(np.max(np.abs(l1 - m1)), np.max(np.abs(l2 - m2)))
    conferir(f"A'12 = {A12}, A'21 = {A21}: interior", erro < 1e-12, f"erro máx. {erro:.1e} ")
    # extremos: limites que o livro dá (ln γ∞ = A') e ln γ = 0 no componente puro
    e1, e2 = modelo("Van Laar", {"A12": A12, "A21": A21}, np.array([0.0, 1.0]))
    conferir(
        "  extremos (ln γ1∞ = A'12, ln γ2∞ = A'21, puros = 0)",
        abs(e1[0] - A12) < 1e-12 and abs(e2[0]) < 1e-12 and abs(e1[1]) < 1e-12 and abs(e2[1] - A21) < 1e-12,
    )
    ge_app = X1_INT * m1 + (1 - X1_INT) * m2
    erro_ge = np.max(np.abs(ge_app - livro_ge_van_laar(X1_INT, A12, A21)))
    conferir("  GE/RT = Σ xi ln γi igual à Eq. 13.42", erro_ge < 1e-12, f"erro máx. {erro_ge:.1e} ")

print("== Auto-teste: o teste reprova um Van Laar com γ1 e γ2 trocados ==")
l1, l2 = livro_van_laar(X1_INT, 1.35, 0.70)
m1, m2 = modelo("Van Laar", {"A12": 1.35, "A21": 0.70}, X1_INT)
conferir("reprova a troca", np.max(np.abs(l1 - m2)) > 1e-3, f"(erro com troca {np.max(np.abs(l1 - m2)):.2f}) ")

print("== Estabilidade (Eq. 12.5; Exemplo 15.4: A < 2 estável, A > 2 duas fases) ==")
for A, esperado in ((1.9, False), (2.0, False), (2.1, True), (2.25, True)):
    r = modelo("Margules (1-P)", {"A": A}, X1)
    g1 = np.exp(r[0])
    faixa = detectar_instabilidade_liquida(list(X1), list(g1))
    conferir(f"A = {A}", (faixa is not None) == esperado, f"faixa instável: {faixa} ")

print()
if todos_ok:
    print("OK: Margules e Van Laar conferem com as equações de Smith, Van Ness e Abbott.")
else:
    print("FALHA: veja as linhas acima.")
    sys.exit(1)
