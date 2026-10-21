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
  Exemplo 13.1 (pp. 457-460, metanol(1)/acetato de metila(2), Margules 1-P com
    A = 2,771 − 0,00523 T e Antoine do livro, kPa e K): bolha e orvalho em P e T e
    azeótropo, com as respostas publicadas (a a e), pela Lei de Raoult modificada
    (Eq. 13.19) e pelo `model_margules_1p` do app. A pressão de vapor é a do livro,
    não a da `thermo`, para o teste só depender das equações.

As equações foram transcritas à parte (não importadas do app) e comparadas com
`MODELS_GE` em 101 composições, extremos inclusos (nos extremos, pelos limites
analíticos que o próprio livro dá: ln γ1∞, ln γ2∞ e ln γ = 0 no componente puro).
Os parâmetros do app (A, A12, A21) são adimensionais, como os do livro nessa seção.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_smith_van_ness_formulas.py
"""

import sys

import numpy as np
from scipy.optimize import brentq

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

print("== Exemplo 13.1 do livro (metanol/acetato de metila, Margules 1-P, Raoult modificada) ==")


def psat_13_1(T):
    p1 = np.exp(16.59158 - 3643.31 / (T - 33.424))
    p2 = np.exp(14.25326 - 2665.54 / (T - 53.424))
    return p1, p2


def A_13_1(T):
    return 2.771 - 0.00523 * T


def gammas_13_1(x1, T):
    return MODELS_GE["Margules (1-P)"](x1, {"A": A_13_1(T)})


def p_bolha(x1, T):  # Eq. 13.20
    p1, p2 = psat_13_1(T)
    g1, g2 = gammas_13_1(x1, T)
    return x1 * g1 * p1 + (1 - x1) * g2 * p2


def y1_bolha(x1, T):  # Eq. 13.19
    p1, _ = psat_13_1(T)
    return x1 * gammas_13_1(x1, T)[0] * p1 / p_bolha(x1, T)


def x1_orvalho(y1, T):
    return brentq(lambda x: y1_bolha(x, T) - y1, 1e-9, 1 - 1e-9)


def perto(valor, ref, tol):
    return abs(valor - ref) <= tol


T = 318.15
p1, p2 = psat_13_1(T)
x1 = 0.25
g1, g2 = gammas_13_1(x1, T)
print("  (a) T = 318,15 K, x1 = 0,25")
conferir("Psat 44,51 e 65,64 kPa", perto(p1, 44.51, 0.005) and perto(p2, 65.64, 0.005), f"({p1:.2f}; {p2:.2f}) ")
conferir("A = 1,107", perto(A_13_1(T), 1.107, 0.0005))
conferir("γ1 = 1,864 e γ2 = 1,072", perto(g1, 1.864, 0.0005) and perto(g2, 1.072, 0.0005), f"({g1:.4f}; {g2:.4f}) ")
conferir("P = 73,50 kPa", perto(p_bolha(x1, T), 73.50, 0.01), f"({p_bolha(x1, T):.3f}) ")
conferir("y1 = 0,282", perto(y1_bolha(x1, T), 0.282, 0.0005), f"({y1_bolha(x1, T):.4f}) ")

print("  (b) T = 318,15 K, y1 = 0,60 (orvalho em P)")
x1 = x1_orvalho(0.60, T)
g1, g2 = gammas_13_1(x1, T)
conferir("x1 = 0,8169", perto(x1, 0.8169, 0.0002), f"({x1:.4f}) ")
conferir("γ1 = 1,0378 e γ2 = 2,0935", perto(g1, 1.0378, 0.0002) and perto(g2, 2.0935, 0.0002), f"({g1:.4f}; {g2:.4f}) ")
# o texto extraído do livro dá P = 62,59 kPa, mas x1·γ1·P1sat/P só fecha em 0,60 com P = 62,89
# (62,59 daria y1 = 0,603); provável 62,89 ou erro de leitura da extração: conferir no exemplar.
P_b = p_bolha(x1, T)
conferir("P coerente com y1 = 0,60 (Eq. 13.19)", perto(x1 * g1 * p1 / P_b, 0.60, 1e-9), f"(P = {P_b:.2f} kPa; extração do livro: 62,59 — conferir no impresso) ")

print("  (c) P = 101,33 kPa, x1 = 0,85 (bolha em T)")
Tc = brentq(lambda t: p_bolha(0.85, t) - 101.33, 300, 360)
p1, p2 = psat_13_1(Tc)
g1, g2 = gammas_13_1(0.85, Tc)
conferir("T = 331,20 K", perto(Tc, 331.20, 0.01), f"({Tc:.3f}) ")
conferir("Psat 77,99 e 105,35 kPa", perto(p1, 77.99, 0.01) and perto(p2, 105.35, 0.01), f"({p1:.2f}; {p2:.2f}) ")
conferir("A = 1,0388", perto(A_13_1(Tc), 1.0388, 0.0001))
conferir("γ1 = 1,0236 e γ2 = 2,1182", perto(g1, 1.0236, 0.0002) and perto(g2, 2.1182, 0.0002), f"({g1:.4f}; {g2:.4f}) ")
conferir("y1 = 0,670", perto(y1_bolha(0.85, Tc), 0.670, 0.0005), f"({y1_bolha(0.85, Tc):.4f}) ")

print("  (d) P = 101,33 kPa, y1 = 0,40 (orvalho em T)")
Td = brentq(lambda t: p_bolha(x1_orvalho(0.40, t), t) - 101.33, 300, 360)
x1 = x1_orvalho(0.40, Td)
p1, p2 = psat_13_1(Td)
g1, g2 = gammas_13_1(x1, Td)
conferir("T = 326,70 K", perto(Td, 326.70, 0.01), f"({Td:.3f}) ")
conferir("Psat 64,63 e 89,94 kPa", perto(p1, 64.63, 0.01) and perto(p2, 89.94, 0.01), f"({p1:.2f}; {p2:.2f}) ")
conferir("A = 1,0624", perto(A_13_1(Td), 1.0624, 0.0001))
conferir("γ1 = 1,3628 e γ2 = 1,2523", perto(g1, 1.3628, 0.0002) and perto(g2, 1.2523, 0.0002), f"({g1:.4f}; {g2:.4f}) ")
conferir("x1 = 0,4602", perto(x1, 0.4602, 0.0002), f"({x1:.4f}) ")

print("  (e) azeótropo a 318,15 K")
p1, p2 = psat_13_1(T)
A = A_13_1(T)
x_az = (1 - np.log(p2 / p1) / A) / 2  # γ1/γ2 = P2sat/P1sat com ln γ1 − ln γ2 = A (1 − 2 x1)
g1, g2 = gammas_13_1(x_az, T)
conferir("γ1/γ2 = P2sat/P1sat = 1,4747", perto(g1 / g2, 1.4747, 0.0005), f"({g1 / g2:.4f}) ")
conferir("x1 = y1 = 0,325", perto(x_az, 0.325, 0.0005) and perto(y1_bolha(x_az, T), x_az, 1e-9), f"({x_az:.4f}) ")
conferir("γ1 = 1,657 e P = 73,76 kPa", perto(g1, 1.657, 0.0005) and perto(p_bolha(x_az, T), 73.76, 0.01), f"({g1:.4f}; {p_bolha(x_az, T):.3f}) ")
g1_inf = gammas_13_1(0.0, T)[0]
g2_inf = gammas_13_1(1.0, T)[1]
conferir("α12 = 2,052 (x1 = 0) e 0,224 (x1 = 1)", perto(g1_inf * p1 / p2, 2.052, 0.001) and perto(p1 / (g2_inf * p2), 0.224, 0.001), f"({g1_inf * p1 / p2:.4f}; {p1 / (g2_inf * p2):.4f}) ")

print()
if todos_ok:
    print("OK: Margules e Van Laar conferem com as equações de Smith, Van Ness e Abbott.")
else:
    print("FALHA: veja as linhas acima.")
    sys.exit(1)
