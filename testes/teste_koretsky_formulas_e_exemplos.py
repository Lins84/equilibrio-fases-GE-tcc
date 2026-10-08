"""
Modelos de Gᴱ e motor de cálculo contra o livro de Koretsky (2026-10-08).

Fonte: Koretsky, M. D. *Engineering and Chemical Thermodynamics*, 2ª ed.
Hoboken: Wiley, 2013. Páginas citadas são as impressas. A `thermo` não tem
Margules nem Van Laar; este teste dá aos dois (e confere os demais) uma fonte
citável que não depende da própria `thermo` nem de dado sintético do projeto.

A. FÓRMULAS. As equações da Tabela 7.2 (p. 438) e da Tabela 7.4 (p. 442),
   transcritas aqui na notação do livro (componentes a e b, A e B em J/mol,
   RT·ln γ), são comparadas com `MODELS_GE` em 101 composições, para vários
   conjuntos de parâmetros. A conversão para o app é a de sempre:
   A₁₂ = (A − B)/RT e A₂₁ = (A + B)/RT (Margules 3 sufixos); Margules 1 sufixo
   A_app = A/RT; Van Laar A₁₂ = A/RT e A₂₁ = B/RT. A transcrição da Tabela 7.4
   (UNIQUAC com q′) é por sua vez conferida com o Exemplo 7.12 do livro.

B. EXEMPLOS 8.9 a 8.11 (pp. 491-495): dados P-x-y de benzeno/ciclo-hexano a
   10 °C (Tabela E8.9A, p. 492, que o livro atribui à coletânea DECHEMA de
   Gmehling et al.) e as respostas publicadas — Tabela E8.9B (P_calc e γ com
   A = 1401 J/mol) e os valores de A e B ajustados. Confere o cálculo direto do
   app e a regressão de Barker contra esses números.

C. EXEMPLO 8.5 (pp. 476-477): etanol/água a 70 °C, Margules de 3 sufixos com
   A = 3590 e B = −1180 J/mol, ponto de orvalho com y₁ = 0,48: o livro obtém
   x₁ = 0,12 e P = 0,55 bar (experimental 0,13 e 0,57 bar).

D. PROBLEMA 7.70 (p. 464): acetona/clorofórmio a 35,17 °C, UNIQUAC com os
   parâmetros do livro (q′ = q, então o `model_uniquac` vale direto); o livro
   reporta P = 261,9 torr e y₁ = 0,143 medidos para x₁ = 0,20.

E. UNIQUAC com q′ (2026-10-08): o `model_uniquac` aceita q′ opcional (qp1/qp2) e
   reproduz a Tabela 7.4 no Exemplo 7.12 e nos Problemas 7.68 e 7.69, em toda a
   faixa de x₁ (erro ~1e-13); no 7.68 o γ₁ com q′ (2,235) fica a 2,8 % do medido
   (2,30), contra 8 % sem q′ (2,49).

Observações de honestidade:
  * O Exemplo 7.12 (p. 442) imprime a₂₁ = −1380,3, mas o próprio exemplo usa
    τ₂₁ = 0,014, que só sai com a₂₁ = +1380,3; o teste usa o sinal que o
    cálculo do livro implica (erro tipográfico do livro).
  * O UNIQUAC da UI usa q (sem q′), como o ChemSep/thermo; o livro usa q′ para
    álcoois e água nos Problemas 7.68 e 7.69, onde as respostas diferem. Desde
    2026-10-08 o `model_uniquac` aceita q′ (qp1/qp2, opcionais; bloco E confere com
    a Tabela 7.4), mas a UI NÃO o liga: com os a₁₂/a₂₁ do banco ChemSep, q′ piora o
    ajuste aos dados NIST (ver CLAUDE.md).
  * As tolerâncias dos blocos B a D foram fixadas depois de medir (valor medido
    ao lado de cada constante): verificação de sanidade, não calibração —
    nada no motor foi ajustado a esses números.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_koretsky_formulas_e_exemplos.py
"""

import numpy as np
from scipy.optimize import brentq
from thermo import Chemical

from calculos.gemini import MODELS_GE, calculate_vle_isothermal, regress_params_barker

R = 8.314                      # J/(mol·K), valor usado pelo livro
X1 = np.linspace(0.0, 1.0, 101)
X1_INT = X1[1:-1]              # UNIQUAC tem 0/0 em x = 0 e 1 (tratado só no app)
TOL_FORMULA = 1e-10

falhas = []


def confere(ok, texto):
    print(f"  {'OK   ' if ok else 'FALHA'} {texto}")
    if not ok:
        falhas.append(texto)


# --------------------------------------------------------------------------
# A. Fórmulas do livro (notação a = componente 1, b = componente 2)
# --------------------------------------------------------------------------

def livro_margules_2sufixos(xa, A, T):
    xb = 1 - xa
    return A * xb**2 / (R * T), A * xa**2 / (R * T)                      # (7.55), (7.56)


def livro_margules_3sufixos_AB(xa, A, B, T):
    xb = 1 - xa
    return (((A + 3 * B) * xb**2 - 4 * B * xb**3) / (R * T),             # (7.59)
            ((A - 3 * B) * xa**2 + 4 * B * xa**3) / (R * T))             # (7.60)


def livro_margules_3sufixos_Aab_Aba(xa, Aab, Aba, T):
    xb = 1 - xa                                                          # Tabela 7.2, linha "or"
    return (xb**2 * (Aab + 2 * (Aba - Aab) * xa) / (R * T),
            xa**2 * (Aba + 2 * (Aab - Aba) * xb) / (R * T))


def livro_van_laar(xa, A, B, T):
    xb = 1 - xa                                                          # Tabela 7.2
    d = A * xa + B * xb
    return A * (B * xb / d)**2 / (R * T), B * (A * xa / d)**2 / (R * T)


def livro_wilson(xa, Lab, Lba):
    xb = 1 - xa                                                          # Tabela 7.2
    t = Lba / (xb + Lba * xa) - Lab / (xa + Lab * xb)
    return -(np.log(xa + Lab * xb) + xb * t), -(np.log(xb + Lba * xa) - xa * t)


def livro_nrtl(xa, tab, tba, alfa):
    xb = 1 - xa                                                          # Tabela 7.2
    Gab, Gba = np.exp(-alfa * tab), np.exp(-alfa * tba)
    return (xb**2 * (tba * Gba**2 / (xa + xb * Gba)**2 + tab * Gab / (xb + xa * Gab)**2),
            xa**2 * (tab * Gab**2 / (xb + xa * Gab)**2 + tba * Gba / (xa + xb * Gba)**2))


def livro_uniquac(xa, ra, qa, qpa, rb, qb, qpb, a_ab, a_ba, T):
    """Tabela 7.4 (p. 442), com q′ na parte residual, z = 10."""
    xb = 1 - xa
    z = 10
    t_ab, t_ba = np.exp(-a_ab / T), np.exp(-a_ba / T)
    Pa = xa * ra / (xa * ra + xb * rb); Pb = 1 - Pa
    ta = xa * qa / (xa * qa + xb * qb); tb = 1 - ta
    pa = xa * qpa / (xa * qpa + xb * qpb); pb = 1 - pa
    la = z / 2 * (ra - qa) - (ra - 1); lb = z / 2 * (rb - qb) - (rb - 1)
    ca = np.log(Pa / xa) + z / 2 * qa * np.log(ta / Pa) + la - Pa / xa * (xa * la + xb * lb)
    cb = np.log(Pb / xb) + z / 2 * qb * np.log(tb / Pb) + lb - Pb / xb * (xa * la + xb * lb)
    ra_ = -qpa * np.log(pa + pb * t_ba) + pb * qpa * (t_ba / (pa + pb * t_ba) - t_ab / (pa * t_ab + pb))
    rb_ = -qpb * np.log(pa * t_ab + pb) + pa * qpb * (t_ab / (pa * t_ab + pb) - t_ba / (pa + pb * t_ba))
    return np.exp(ca + ra_), np.exp(cb + rb_)


def ln_app(modelo, params, xs):
    """(ln γ₁, ln γ₂) do app em cada x₁ de `xs` (os modelos recebem x₁ escalar)."""
    g = np.array([MODELS_GE[modelo](float(x), params) for x in xs])
    return np.log(g[:, 0]), np.log(g[:, 1])


def erro_max(par_app, par_livro):
    return max(np.abs(par_app[0] - par_livro[0]).max(), np.abs(par_app[1] - par_livro[1]).max())


def bloco_a():
    print("A. Fórmulas do livro (Tabelas 7.2 e 7.4) contra MODELS_GE")
    T = 323.15
    RT = R * T
    # Margules 1 sufixo
    for A in (-1500.0, 0.0, 1401.0, 3000.0):
        e = erro_max(ln_app("Margules (1-P)", {"A": A / RT}, X1), livro_margules_2sufixos(X1, A, T))
        confere(e < TOL_FORMULA, f"Margules 1-P, A = {A:7.1f} J/mol: erro máx {e:.1e}")
    # Margules 3 sufixos: forma (A, B), forma (A_ab, A_ba) e app têm de coincidir
    for A, B in ((1397.0, 69.0), (3590.0, -1180.0), (-800.0, 500.0), (2000.0, 3000.0)):
        p = {"A12": (A - B) / RT, "A21": (A + B) / RT}
        ap = ln_app("Margules (2-P)", p, X1)
        e1 = erro_max(ap, livro_margules_3sufixos_AB(X1, A, B, T))
        e2 = erro_max(ap, livro_margules_3sufixos_Aab_Aba(X1, A - B, A + B, T))
        confere(max(e1, e2) < TOL_FORMULA,
                f"Margules 2-P, A = {A:7.1f}, B = {B:7.1f}: erro máx {e1:.1e} (forma A,B) e {e2:.1e} (forma A_ab,A_ba)")
    # Van Laar (inclui o par do Problema 7.66, p. 463: 3000 e 5040 J/mol)
    for A, B in ((3000.0, 5040.0), (1500.0, 600.0), (-1200.0, -700.0)):
        e = erro_max(ln_app("Van Laar", {"A12": A / RT, "A21": B / RT}, X1), livro_van_laar(X1, A, B, T))
        confere(e < TOL_FORMULA, f"Van Laar, A = {A:7.1f}, B = {B:7.1f}: erro máx {e:.1e}")
    # Wilson (inclui o par do Problema 7.71, p. 464: 1,216 e 0,617)
    for Lab, Lba in ((0.8083, 0.6432), (1.216, 0.617), (0.2, 1.8)):
        e = erro_max(ln_app("Wilson", {"L12": Lab, "L21": Lba}, X1), livro_wilson(X1, Lab, Lba))
        confere(e < TOL_FORMULA, f"Wilson, Λab = {Lab}, Λba = {Lba}: erro máx {e:.1e}")
    # NRTL
    for tab, tba, al in ((0.5, 1.2, 0.3), (-0.3, 0.9, 0.47), (1.5, 0.2, 0.2)):
        e = erro_max(ln_app("NRTL", {"tau12": tab, "tau21": tba, "alpha12": al}, X1),
                     livro_nrtl(X1, tab, tba, al))
        confere(e < TOL_FORMULA, f"NRTL, τab = {tab}, τba = {tba}, α = {al}: erro máx {e:.1e}")
    # UNIQUAC com q' = q (o app não usa q'); só no interior (0/0 nas pontas)
    casos = (("acetona/clorofórmio (Prob. 7.70)", 2.57, 2.34, 2.70, 2.34, -171.71, 93.93, 308.32),
             ("etanol/n-heptano com q'=q", 2.11, 1.97, 5.17, 4.40, -105.23, 1380.3, 323.15))
    for nome, ra, qa, rb, qb, a12, a21, TT in casos:
        p = dict(r1=ra, q1=qa, r2=rb, q2=qb, a12=a12, a21=a21, T_K=TT)
        g = np.array([MODELS_GE["UNIQUAC"](float(x), p) for x in X1_INT])
        gl = np.array([livro_uniquac(x, ra, qa, qa, rb, qb, qb, a12, a21, TT) for x in X1_INT])
        e = np.abs(np.log(g) - np.log(gl)).max()
        confere(e < TOL_FORMULA, f"UNIQUAC (Tabela 7.4), {nome}: erro máx {e:.1e}")
    # Auto-teste da transcrição da Tabela 7.4: o Exemplo 7.12 (p. 443) com q' reproduz o livro
    g1, g2 = livro_uniquac(0.3022, 2.11, 1.97, 0.92, 5.17, 4.40, 4.40, -105.23, 1380.3, 323.15)
    confere(abs(g1 - 2.67) < 0.01 and abs(g2 - 1.32) < 0.01,
            f"Exemplo 7.12 (com q'): γ₁ = {g1:.3f}, γ₂ = {g2:.3f} (livro: 2,67 e 1,32; a₂₁ = +1380,3, ver nota)")


# --------------------------------------------------------------------------
# B. Exemplos 8.9 a 8.11: benzeno (1) / ciclo-hexano (2) a 10 °C
# --------------------------------------------------------------------------

# Tabela E8.9A (p. 492): x1, y1, P [Pa]. Fonte do livro: Gmehling, Onken e Arlt,
# Vapor-Liquid Equilibrium Data Collection (DECHEMA, 1977-1980).
E89_X1 = [0, 0.0610, 0.2149, 0.3187, 0.4320, 0.5246, 0.6117, 0.7265, 0.8040, 0.8830, 0.8999, 1]
E89_Y1 = [0, 0.0953, 0.2710, 0.3600, 0.4453, 0.5106, 0.5735, 0.6626, 0.7312, 0.8200, 0.8382, 1]
E89_P = [6344, 6590, 6980, 7140, 7171, 7216, 7140, 6974, 6845, 6617, 6557, 6073]
# Tabela E8.9B (p. 493), A = 1401 J/mol: P_calc [Pa] e γ
E89_PCALC = [6344, 6595, 7001, 7141, 7203, 7195, 7139, 6986, 6821, 6586, 6525, 6073]
E89_G1 = [1.81, 1.69, 1.44, 1.32, 1.21, 1.14, 1.09, 1.05, 1.02, 1.01, 1.01, 1.00]
E89_G2 = [1.00, 1.00, 1.03, 1.06, 1.12, 1.18, 1.25, 1.37, 1.47, 1.59, 1.62, 1.81]

TOL_E89_P_PA = 4.0       # medido: até 2,5 Pa (o livro arredonda a 1 Pa e usa A = 1401 arredondado)
TOL_E89_GAMA = 0.006     # medido: até 0,004 (o livro dá 2 casas)
FAIXA_A_1P = (1390.0, 1430.0)   # livro: 1401 (P), 1399 (gᴱ), 1424 (γ); app (Barker): 1406
TOL_A12_A21 = 0.01       # em ln γ∞; medido: até 0,0038 contra A = 1397, B = 69 do livro
TOL_ERRO_DP, TOL_ERRO_DY = 0.5, 0.005   # % e fração molar; medido: 0,28 % e 0,0027


def bloco_b():
    print("\nB. Exemplos 8.9 a 8.11 (benzeno/ciclo-hexano, 10 °C)")
    T_K = 283.15
    RT = R * T_K
    x1 = np.array(E89_X1)
    # B1. cálculo direto com A = 1401 J/mol e as Psat dos pontos puros da própria tabela
    P1sat, P2sat = float(E89_P[-1]), float(E89_P[0])
    g = np.array([MODELS_GE["Margules (1-P)"](float(x), {"A": 1401.0 / RT}) for x in x1])
    Pc = x1 * g[:, 0] * P1sat + (1 - x1) * g[:, 1] * P2sat
    eP = np.abs(Pc - np.array(E89_PCALC)).max()
    eg = max(np.abs(g[:, 0] - E89_G1).max(), np.abs(g[:, 1] - E89_G2).max())
    confere(eP < TOL_E89_P_PA, f"P_calc (Tabela E8.9B): erro máx {eP:.1f} Pa (tolerância {TOL_E89_P_PA})")
    confere(eg < TOL_E89_GAMA, f"γ calculado (Tabela E8.9B): erro máx {eg:.4f} (tolerância {TOL_E89_GAMA})")
    # B2. Psat da thermo nos pontos puros (sanidade do dado e da Psat)
    for nome, p_livro in (("benzene", P1sat), ("cyclohexane", P2sat)):
        ps = Chemical(nome, T=T_K).Psat
        confere(abs(ps - p_livro) / p_livro < 0.002,
                f"Psat da thermo, {nome}: {ps:.0f} Pa contra {p_livro:.0f} Pa da tabela ({100 * (ps - p_livro) / p_livro:+.2f} %)")
    # B3. regressão de Barker contra os valores publicados
    pts = [(p / 1000.0, x, y) for p, x, y in zip(E89_P, E89_X1, E89_Y1)]
    r1 = regress_params_barker("Margules (1-P)", "benzene", "cyclohexane", 10.0, pts)
    A1 = r1["params"]["A"] * RT
    confere(r1["sucesso"] and FAIXA_A_1P[0] < A1 < FAIXA_A_1P[1],
            f"Barker, Margules 1-P: A = {A1:.0f} J/mol (livro: 1401, 1399 e 1424 conforme a função-objetivo)")
    r2 = regress_params_barker("Margules (2-P)", "benzene", "cyclohexane", 10.0, pts)
    A12, A21 = r2["params"]["A12"], r2["params"]["A21"]
    a12_l, a21_l = (1397.0 - 69.0) / RT, (1397.0 + 69.0) / RT       # Exemplo 8.10: A = 1397, B = 69
    confere(r2["sucesso"] and abs(A12 - a12_l) < TOL_A12_A21 and abs(A21 - a21_l) < TOL_A12_A21,
            f"Barker, Margules 2-P: A₁₂ = {A12:.4f}, A₂₁ = {A21:.4f} (livro: {a12_l:.4f} e {a21_l:.4f}, "
            f"de A = 1397 e B = 69; regressão linear do livro: A = 1402, B = 75,1)")
    for nome, modelo, rr in (("Margules 1-P", "Margules (1-P)", r1), ("Margules 2-P", "Margules (2-P)", r2)):
        rv = calculate_vle_isothermal("benzene", "cyclohexane", 10.0, modelo, rr["params"], x1_values=x1)
        dP = 100 * np.sqrt(np.mean(((np.array(rv["P_kPa"]) - np.array(E89_P) / 1000) / (np.array(E89_P) / 1000))**2))
        dy = np.sqrt(np.mean((np.array(rv["y1"]) - np.array(E89_Y1))**2))
        confere(dP < TOL_ERRO_DP and dy < TOL_ERRO_DY, f"{nome} ajustado: ΔP = {dP:.2f} %, Δy = {dy:.4f}")


# --------------------------------------------------------------------------
# C. Exemplo 8.5: etanol (a) / água (b) a 70 °C, ponto de orvalho
# --------------------------------------------------------------------------

def bloco_c():
    print("\nC. Exemplo 8.5 (etanol/água a 70 °C, Margules de 3 sufixos)")
    T_K = 343.15
    RT = R * T_K
    A, B = 3590.0, -1180.0
    x = np.linspace(0.0, 1.0, 2001)
    r = calculate_vle_isothermal("ethanol", "water", 70.0, "Margules (2-P)",
                                 {"A12": (A - B) / RT, "A21": (A + B) / RT}, x1_values=x)
    P, y = np.array(r["P_kPa"]), np.array(r["y1"])
    i = np.where(np.diff(np.sign(y - 0.48)))[0][0]
    xs = brentq(lambda xx: np.interp(xx, x, y) - 0.48, x[i], x[i + 1])
    Ps_bar = np.interp(xs, x, P) / 100.0
    confere(abs(xs - 0.12) < 0.01, f"x₁ do ponto de orvalho (y₁ = 0,48): {xs:.3f} (livro: 0,12; experimental 0,13)")
    confere(abs(Ps_bar - 0.55) < 0.01, f"P do ponto de orvalho: {Ps_bar:.3f} bar (livro: 0,55; experimental 0,57)")


# --------------------------------------------------------------------------
# D. Problema 7.70: acetona (1) / clorofórmio (2) a 35,17 °C, UNIQUAC
# --------------------------------------------------------------------------

TOL_P_PROB770 = 3.0      # %; medido: +2,35 %
TOL_Y_PROB770 = 0.015    # medido: 0,0104


def bloco_d():
    print("\nD. Problema 7.70 (acetona/clorofórmio a 35,17 °C, UNIQUAC com parâmetros do livro)")
    T_K = 35.17 + 273.15
    x1 = 0.20
    P1 = Chemical("acetone", T=T_K).Psat / 1000.0
    P2 = Chemical("chloroform", T=T_K).Psat / 1000.0
    g1, g2 = MODELS_GE["UNIQUAC"](x1, dict(r1=2.57, q1=2.34, r2=2.70, q2=2.34, a12=-171.71, a21=93.93, T_K=T_K))
    P = x1 * g1 * P1 + (1 - x1) * g2 * P2
    y1 = x1 * g1 * P1 / P
    P_torr = P / 0.133322
    erro_P = 100 * (P_torr - 261.9) / 261.9
    confere(abs(erro_P) < TOL_P_PROB770, f"P = {P_torr:.1f} torr contra 261,9 medido ({erro_P:+.2f} %)")
    confere(abs(y1 - 0.143) < TOL_Y_PROB770, f"y₁ = {y1:.4f} contra 0,143 medido")


# --------------------------------------------------------------------------
# E. UNIQUAC com q′ (2026-10-08): Exemplo 7.12 e Problemas 7.68 e 7.69
# --------------------------------------------------------------------------

# (nome, x1, T [K], r1, q1, q′1, r2, q2, q′2, a12, a21), todos do livro (p. 443 e pp. 463-464)
CASOS_QPRIME = (
    ("Exemplo 7.12 etanol/n-heptano", 0.3022, 323.15, 2.11, 1.97, 0.92, 5.17, 4.40, 4.40, -105.23, 1380.3),
    ("Problema 7.68 acetona/água", 0.30, 334.25, 2.57, 2.34, 2.34, 0.92, 1.40, 1.00, 530.99, -100.71),
    ("Problema 7.69 etanol/benzeno", 0.415, 318.15, 2.11, 1.97, 0.92, 3.19, 2.40, 2.40, -75.13, 242.53),
)
TOL_G_PROB768 = (0.05, 0.08)   # medido com q′: γ₁ 2,235 (−2,8 % de 2,30) e γ₂ 1,245 (−5,7 % de 1,32)


def bloco_e():
    print("E. UNIQUAC com q′ (parâmetro opcional qp1/qp2 do model_uniquac)")
    for nome, x1, T, r1, q1, qp1, r2, q2, qp2, a12, a21 in CASOS_QPRIME:
        base = dict(r1=r1, q1=q1, r2=r2, q2=q2, a12=a12, a21=a21, T_K=T)
        com = dict(base, qp1=qp1, qp2=qp2)
        # contra a Tabela 7.4 do livro, na faixa inteira (interior) e no ponto do problema
        g = np.array([MODELS_GE["UNIQUAC"](float(x), com) for x in X1_INT])
        gl = np.array([livro_uniquac(x, r1, q1, qp1, r2, q2, qp2, a12, a21, T) for x in X1_INT])
        e = np.abs(np.log(g) - np.log(gl)).max()
        confere(e < TOL_FORMULA, f"{nome}: app com q′ contra a Tabela 7.4, erro máx {e:.1e}")
        # sensibilidade: ignorar q′ tem de mudar o resultado quando q′ ≠ q
        if abs(qp1 - q1) + abs(qp2 - q2) > 0:
            g_sem = np.array([MODELS_GE["UNIQUAC"](float(x), base) for x in X1_INT])
            d = np.abs(np.log(g_sem) - np.log(g)).max()
            confere(d > 0.05, f"{nome}: com e sem q′ diferem (ln γ até {d:.2f}) — o teste enxerga q′")
        else:
            confere(np.allclose(MODELS_GE["UNIQUAC"](0.4, com), MODELS_GE["UNIQUAC"](0.4, base), rtol=0, atol=1e-14),
                    f"{nome}: q′ = q devolve o UNIQUAC original")
    # Problema 7.68: γ medidos (γ₁ = 2,30 e γ₂ = 1,32), x₁ = 0,30
    _, x1, T, r1, q1, qp1, r2, q2, qp2, a12, a21 = CASOS_QPRIME[1]
    base = dict(r1=r1, q1=q1, r2=r2, q2=q2, a12=a12, a21=a21, T_K=T)
    g1, g2 = MODELS_GE["UNIQUAC"](x1, dict(base, qp1=qp1, qp2=qp2))
    s1, s2 = MODELS_GE["UNIQUAC"](x1, base)
    confere(abs(g1 / 2.30 - 1) < TOL_G_PROB768[0] and abs(g2 / 1.32 - 1) < TOL_G_PROB768[1],
            f"Problema 7.68 com q′: γ₁ = {g1:.3f} e γ₂ = {g2:.3f} contra 2,30 e 1,32 medidos "
            f"(sem q′: {s1:.3f} e {s2:.3f})")


def main():
    bloco_a()
    bloco_b()
    bloco_c()
    bloco_d()
    bloco_e()
    print()
    if falhas:
        print(f"FALHA: {len(falhas)} verificação(ões) fora da tolerância:")
        for f in falhas:
            print("  -", f)
        raise SystemExit(1)
    print("OK: modelos e motor conferem com as fórmulas, exemplos e problemas do Koretsky.")


if __name__ == "__main__":
    main()
