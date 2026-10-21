"""Tabelas 13.3, 13.4 e 13.5 de Smith, Van Ness, Abbott e Swihart (2026-10-21).

Smith, J. M.; Van Ness, H. C.; Abbott, M. M.; Swihart, M. T. Introduction to Chemical
Engineering Thermodynamics, 8ª ed., McGraw-Hill Education, 2018, cap. 13, seção 13.5.
Dados de ELV isotérmico (P, x1, y1) transcritos pelo autor do projeto a partir das páginas
do livro (pp. 474, 477 e 480), conferidos linha a linha na imagem; as pressões de vapor
dos puros (P1sat e P2sat) são as impressas no livro. Os dados são de fonte da literatura
reproduzidos no livro; aqui servem só de conferência, com a citação acima (mesmo
tratamento da Tabela E8.9A do Koretsky em `teste_koretsky_formulas_e_exemplos.py`).

  Tabela 13.3, p. 474: metiletilcetona(1)/tolueno(2), 50 °C — Margules 2-P publicado:
      GE/(x1 x2 RT) = 0,198 x1 + 0,372 x2.
  Tabela 13.4, p. 477: clorofórmio(1)/1,4-dioxano(2), 50 °C — A12 = −0,72 e A21 = −1,27.
  Tabela 13.5, p. 480: dietilcetona(1)/n-hexano(2), 65 °C — reta GE/(x1 x2 RT) = 0,70 x1 +
      1,35 x2 e, pelo método de Barker (p. 481), A21 = 0,596 e A12 = 1,153.

O que cada bloco confere:
  1. Os dados batem com a Eq. 13.24 (γi* = yi P / (xi Pi^sat)): ln γ1*, ln γ2* e
     GE/(x1 x2 RT)* recalculados a partir de P, x1, y1 reproduzem as colunas da tabela
     dentro do arredondamento (3 casas). Isso confere a transcrição e a equação.
  2. Os parâmetros publicados pela reta de GE/(x1 x2 RT) são reproduzidos por mínimos
     quadrados lineares nessa coluna (o livro "desenha" a reta, então a tolerância é
     folgada na Tabela 13.4).
  3. O modelo do app (Margules 2-P) com esses parâmetros e a P^sat do livro reproduz P e y.
  4. Teste de consistência de resíduos (Eq. 13.59): média de |δ ln(γ1/γ2)| na Tabela
     13.5 ≈ 0,15, o valor que o livro dá (p. 481; limiares do livro: 0,03 = alta
     consistência, 0,10 = provavelmente aceitável).
  5. Barker só em P (Tabela 13.5): reproduz A12 = 1,153 e A21 = 0,596 aproximadamente.
     **O livro não informa a função-objetivo** (diz só "as close as possible to the
     measured values", p. 481): com Σ(δP)² sai A12 = 1,154 e A21 = 0,567; com Σ(δP/P)²,
     1,129 e 0,599; nenhuma das duas reproduz os dois números ao mesmo tempo (a superfície
     é achatada: o RMS de P é ≈ 1,4 % nos dois casos).
  6. O `regress_params_barker` do app minimiza P (relativo) e y juntos, com a Psat da
     `thermo`; dá A12 = 1,08 e A21 = 0,65 na Tabela 13.5, na mesma ordem de grandeza do
     livro, mas não igual — diferença esperada, registrada aqui.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_smith_van_ness_tabelas_13.py
"""

import sys

import numpy as np
from scipy.optimize import least_squares

from calculos.gemini import MODELS_GE, regress_params_barker

todos_ok = True


def conferir(descricao, condicao, detalhe=""):
    global todos_ok
    print(f"  [{descricao}] {detalhe}-> {'OK' if condicao else 'FALHA'}")
    todos_ok &= bool(condicao)


# (P_kPa, x1, y1, ln γ1*, ln γ2*, GE/(x1 x2 RT)*) — só as linhas internas (0 < x1 < 1)
T13_3 = {
    "P1sat": 36.09, "P2sat": 12.30,
    "linhas": [
        (15.51, 0.0895, 0.2716, 0.266, 0.009, 0.389),
        (18.61, 0.1981, 0.4565, 0.172, 0.025, 0.342),
        (21.63, 0.3193, 0.5934, 0.108, 0.049, 0.312),
        (24.01, 0.4232, 0.6815, 0.069, 0.075, 0.297),
        (25.92, 0.5119, 0.7440, 0.043, 0.100, 0.283),
        (27.96, 0.6096, 0.8050, 0.023, 0.127, 0.267),
        (30.12, 0.7135, 0.8639, 0.010, 0.151, 0.248),
        (31.75, 0.7934, 0.9048, 0.003, 0.173, 0.234),
        (34.15, 0.9102, 0.9590, -0.003, 0.237, 0.227),
    ],
}
T13_4 = {
    "P1sat": 69.36, "P2sat": 15.79,
    "linhas": [
        (17.51, 0.0932, 0.1794, -0.722, 0.004, -0.758),
        (18.15, 0.1248, 0.2383, -0.694, -0.000, -0.790),
        (19.30, 0.1757, 0.3302, -0.648, -0.007, -0.825),
        (19.89, 0.2000, 0.3691, -0.636, -0.007, -0.828),
        (21.37, 0.2626, 0.4628, -0.611, -0.014, -0.882),
        (24.95, 0.3615, 0.6184, -0.486, -0.057, -0.919),
        (29.82, 0.4750, 0.7552, -0.380, -0.127, -0.992),
        (34.80, 0.5555, 0.8378, -0.279, -0.218, -1.019),
        (42.10, 0.6718, 0.9137, -0.192, -0.355, -1.113),
        (60.38, 0.8780, 0.9860, -0.023, -0.824, -1.124),
        (65.39, 0.9398, 0.9945, -0.002, -0.972, -1.074),
    ],
}
T13_5 = {
    "P1sat": 29.00, "P2sat": 90.15,
    "linhas": [
        (91.78, 0.063, 0.049, 0.901, 0.033, 1.481),
        (88.01, 0.248, 0.131, 0.472, 0.121, 1.114),
        (81.67, 0.372, 0.182, 0.321, 0.166, 0.955),
        (78.89, 0.443, 0.215, 0.278, 0.210, 0.972),
        (76.82, 0.508, 0.248, 0.257, 0.264, 1.043),
        (73.39, 0.561, 0.268, 0.190, 0.306, 0.977),
        (66.45, 0.640, 0.316, 0.123, 0.337, 0.869),
        (62.95, 0.702, 0.368, 0.129, 0.393, 0.993),
        (57.70, 0.763, 0.412, 0.072, 0.462, 0.909),
        (50.16, 0.834, 0.490, 0.016, 0.536, 0.740),
        (45.70, 0.874, 0.570, 0.027, 0.548, 0.844),
    ],
}

# nome, tabela, (A12, A21) publicados pela reta, componentes (thermo) e T
CASOS = [
    ("Tabela 13.3 (MEK/tolueno, 50 °C)", T13_3, (0.372, 0.198), ("2-butanone", "toluene", 50.0), 0.02),
    ("Tabela 13.4 (clorofórmio/dioxano, 50 °C)", T13_4, (-0.72, -1.27), ("chloroform", "1,4-dioxane", 50.0), 0.10),
    ("Tabela 13.5 (dietilcetona/hexano, 65 °C)", T13_5, (1.35, 0.70), ("3-pentanone", "hexane", 65.0), 0.01),
]


def colunas(tab):
    a = np.array(tab["linhas"])
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]


def margules_2p(x1, A12, A21):
    pares = [MODELS_GE["Margules (2-P)"](float(x), {"A12": A12, "A21": A21}) for x in x1]
    return np.log([p[0] for p in pares]), np.log([p[1] for p in pares])


def p_e_y(tab, x1, A12, A21):
    """P e y1 pela Lei de Raoult modificada (Eqs. 13.57 e 13.58) com a Psat do livro."""
    l1, l2 = margules_2p(x1, A12, A21)
    a, b = x1 * np.exp(l1) * tab["P1sat"], (1 - x1) * np.exp(l2) * tab["P2sat"]
    return a + b, a / (a + b)


resultados = {}
for nome, tab, (A12_liv, A21_liv), (c1, c2, T_C), tol_reta in CASOS:
    print(f"== {nome} ==")
    P, x1, y1, l1_tab, l2_tab, Y_tab = colunas(tab)

    # 1. dados contra a Eq. 13.24
    l1 = np.log(y1 * P / (x1 * tab["P1sat"]))
    l2 = np.log((1 - y1) * P / ((1 - x1) * tab["P2sat"]))
    Y = (x1 * l1 + (1 - x1) * l2) / (x1 * (1 - x1))
    e_l = max(np.max(np.abs(l1 - l1_tab)), np.max(np.abs(l2 - l2_tab)))
    e_y = np.max(np.abs(Y - Y_tab))
    conferir("ln γ1*, ln γ2* da tabela = Eq. 13.24", e_l <= 0.0006, f"erro máx. {e_l:.4f} (tabela com 3 casas) ")
    conferir("GE/(x1x2RT)* da tabela = Σ xi ln γi*/(x1x2)", e_y <= 0.001, f"erro máx. {e_y:.4f} ")

    # 2. reta de GE/(x1 x2 RT) por mínimos quadrados lineares
    A = np.vstack([x1, 1 - x1]).T
    A21_ls, A12_ls = np.linalg.lstsq(A, Y_tab, rcond=None)[0]
    conferir(
        "reta de GE/(x1x2RT)* dá os parâmetros do livro",
        abs(A12_ls - A12_liv) <= tol_reta and abs(A21_ls - A21_liv) <= tol_reta,
        f"(A12 = {A12_ls:.3f} contra {A12_liv}; A21 = {A21_ls:.3f} contra {A21_liv}) ",
    )

    # 3. modelo do app com os parâmetros do livro
    Pc, yc = p_e_y(tab, x1, A12_liv, A21_liv)
    rms_P = 100 * np.sqrt(np.mean(((Pc - P) / P) ** 2))
    rms_y = np.sqrt(np.mean((yc - y1) ** 2))
    print(f"     modelo com os parâmetros do livro: ΔP = {rms_P:.2f} % e Δy = {rms_y:.4f}")
    resultados[nome] = (rms_P, rms_y)

    # 4. resíduo de consistência (Eq. 13.59 pela correlação)
    g1, g2 = margules_2p(x1, A12_liv, A21_liv)
    d = (l1 - l2) - (g1 - g2)
    media_d = float(np.mean(np.abs(d)))
    print(f"     média de |δ ln(γ1/γ2)| = {media_d:.3f}")
    resultados[nome] += (media_d,)

# limites do ajuste do modelo com os parâmetros do livro (medidos em 2026-10-21; guarda de regressão)
nomes = [c[0] for c in CASOS]
conferir("13.3: ΔP < 0,5 % e Δy < 0,005 com os parâmetros do livro",
         resultados[nomes[0]][0] < 0.5 and resultados[nomes[0]][1] < 0.005)
conferir("13.4: ΔP < 2 % e Δy < 0,015",
         resultados[nomes[1]][0] < 2.0 and resultados[nomes[1]][1] < 0.015)
conferir("13.5: ΔP < 6 % e Δy < 0,04 (a reta do livro ajusta mal P aqui)",
         resultados[nomes[2]][0] < 6.0 and resultados[nomes[2]][1] < 0.04)

print("== Teste de consistência (Eq. 13.59 e limiares da p. 480) ==")
conferir("13.5: média ≈ 0,15 (o livro diz 'about 0.15' e conclui que há erro significativo)",
         abs(resultados[nomes[2]][2] - 0.15) <= 0.02 and resultados[nomes[2]][2] > 0.10,
         f"({resultados[nomes[2]][2]:.3f}) ")
conferir("13.3: abaixo de 0,03 (alta consistência)", resultados[nomes[0]][2] < 0.03, f"({resultados[nomes[0]][2]:.3f}) ")
conferir("13.4: entre 0,03 e 0,10 (provavelmente aceitável)",
         0.03 <= resultados[nomes[1]][2] < 0.10, f"({resultados[nomes[1]][2]:.3f}) ")

print("== Barker só em P na Tabela 13.5 (livro: A21 = 0,596 e A12 = 1,153; função-objetivo não informada) ==")
P, x1, y1, *_ = colunas(T13_5)
BARKER_A12, BARKER_A21 = 1.153, 0.596


def ajustar_so_P(relativo):
    def res(v):
        Pc, _ = p_e_y(T13_5, x1, v[0], v[1])
        return (Pc - P) / (P if relativo else 1.0)
    return least_squares(res, [0.5, 0.3]).x


for rotulo, relativo in (("Σ(δP)²", False), ("Σ(δP/P)²", True)):
    A12, A21 = ajustar_so_P(relativo)
    conferir(
        f"{rotulo} reproduz o Barker do livro aproximadamente",
        abs(A12 - BARKER_A12) <= 0.03 and abs(A21 - BARKER_A21) <= 0.035,
        f"(A12 = {A12:.3f} contra {BARKER_A12}; A21 = {A21:.3f} contra {BARKER_A21}) ",
    )

print("== regress_params_barker do app (P relativo e y juntos, Psat da thermo), Tabela 13.5 ==")
r = regress_params_barker("Margules (2-P)", "3-pentanone", "hexane", 65.0, [(a, b, c) for a, b, c, *_ in T13_5["linhas"]])
A12_app, A21_app = float(r["params"]["A12"]), float(r["params"]["A21"])
conferir("o ajuste converge", r["sucesso"] and not r["no_limite"])
conferir(
    "mesma ordem de grandeza do Barker do livro, mas não igual (objetivo e Psat diferentes)",
    abs(A12_app - BARKER_A12) <= 0.15 and abs(A21_app - BARKER_A21) <= 0.15,
    f"(app: A12 = {A12_app:.3f}, A21 = {A21_app:.3f}; livro: {BARKER_A12} e {BARKER_A21}) ",
)

print()
if todos_ok:
    print("OK: tabelas 13.3, 13.4 e 13.5 conferidas.")
else:
    print("FALHA: veja as linhas acima.")
    sys.exit(1)
