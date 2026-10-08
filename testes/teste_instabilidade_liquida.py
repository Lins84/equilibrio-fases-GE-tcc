"""Aviso de instabilidade da fase líquida (2026-10-08).

Uma fase líquida só é estável se d ln(x₁γ₁)/dx₁ > 0. `detectar_instabilidade_liquida`
aplica essa condição à malha de `calculate_vle_isothermal`, e a UI usa
`aviso_instabilidade_liquida` para avisar quando o modelo prevê duas fases
líquidas — nesse trecho o diagrama de Raoult modificada (uma só fase) não vale.

Verifica:
  1. Margules 1-P: a condição se reduz a A/RT > 2 (derivada de 1/(x₁x₂) − 2A/RT,
     mínimo 4 − 2A/RT em x₁ = 0,5) — sem aviso em A = 2,0 e abaixo; com aviso em
     A = 2,01 e acima, em torno de x₁ = 0,5, e a faixa cresce com A (a faixa
     exata é 1/(x₁x₂) = 2A; a malha de 101 pontos erra por até ~0,015);
  2. sem falso positivo: os modelos do banco para etanol/água (miscível em tudo)
     e os ajustes de Barker às 10 isotermas NIST de etanol/água e clorofórmio/MEK
     não geram aviso. Metanol/dimetilbuteno é o caso que avisa de propósito:
     Margules, Van Laar e NRTL ajustados chegam a A/RT ≈ 2,2 e o modelo prevê
     separação de fases (o Wilson não), embora o dado seja de fase única;
  3. sistema que se separa de fato (1-butanol/água, UNIFAC e UNIQUAC) gera aviso;
  4. NRTL com τ grandes e Van Laar com A₁₂ e A₂₁ grandes geram aviso;
  5. malha curta ou vazia não dá erro.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_instabilidade_liquida.py
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

from calculos.gemini import (
    buscar_parametros_banco,
    calculate_vle_isothermal,
    detectar_instabilidade_liquida,
    montar_parametros_automaticos,
)

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "interface"))
spec = importlib.util.spec_from_file_location("fg", RAIZ / "interface" / "fletando_grafico.py")
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

falhas = []


def conferir(ok, msg):
    print(("OK: " if ok else "FALHOU: ") + msg)
    if not ok:
        falhas.append(msg)


def faixa(c1, c2, T_C, modelo, params):
    r = calculate_vle_isothermal(c1, c2, T_C, modelo, params)
    return detectar_instabilidade_liquida(r["x1"], r["gamma1"]), r


# 1. Margules 1-P: limiar A = 2 e faixa
for A in (0.0, 1.0, 1.9, 2.0):
    f, _ = faixa("ethanol", "water", 70.0, "Margules (1-P)", {"A": A})
    conferir(f is None, f"Margules 1-P, A = {A}: sem aviso.")
for A in (2.01, 2.5, 3.0, 4.0):
    f, _ = faixa("ethanol", "water", 70.0, "Margules (1-P)", {"A": A})
    ok = f is not None and f[0] < 0.5 < f[1]
    if ok and A >= 2.5:
        # spinodal exata: x₁x₂ = 1/(2A) → x₁ = (1 ± sqrt(1 − 2/A))/2
        raiz = np.sqrt(1 - 2 / A)
        ok = abs(f[0] - (1 - raiz) / 2) < 0.02 and abs(f[1] - (1 + raiz) / 2) < 0.02
    conferir(ok, f"Margules 1-P, A = {A}: aviso em torno de x₁ = 0,5 ({f}).")
larg = [(f[1] - f[0]) for f in (faixa("ethanol", "water", 70.0, "Margules (1-P)", {"A": a})[0] for a in (2.5, 3.0, 4.0))]
conferir(larg[0] < larg[1] < larg[2], "a faixa instável cresce com A.")

# 2. sem falso positivo (etanol/água é miscível em tudo)
for modelo in ("NRTL", "Wilson"):
    p = buscar_parametros_banco(modelo, "ethanol", "water", 343.15)
    f, _ = faixa("ethanol", "water", 70.0, modelo, p)
    conferir(f is None, f"{modelo} do banco, etanol/água a 70 °C: sem aviso.")
for modelo in ("UNIQUAC", "UNIFAC"):
    p = montar_parametros_automaticos(modelo, "ethanol", "water")
    f, _ = faixa("ethanol", "water", 70.0, modelo, p)
    conferir(f is None, f"{modelo}, etanol/água a 70 °C: sem aviso.")
for modelo, p in (("Margules (2-P)", {"A12": 1.9, "A21": 1.0}), ("Van Laar", {"A12": 1.9, "A21": 1.0}),
                  ("Wilson", {"L12": 0.2, "L21": 0.3})):
    f, _ = faixa("ethanol", "water", 70.0, modelo, p)
    conferir(f is None, f"{modelo} {p}: sem aviso (Wilson nem prevê separação de fases).")
# modelos ajustados por Barker aos 10 isotermas NIST: etanol/água e clorofórmio/MEK sem aviso;
# metanol/dimetilbuteno (desvio positivo forte, A/RT ≈ 2,2): Margules, Van Laar e NRTL
# cruzam o limite de estabilidade e DEVEM avisar (é o que o modelo prevê); o Wilson não prevê
# separação de fases e não avisa. Medido em 2026-10-08.
sys.path.insert(0, str(RAIZ / "testes"))
from teste_margules_2p_nist_ln_gamma import SISTEMAS, ler  # noqa: E402
from calculos.gemini import regress_params_barker  # noqa: E402

for nome, caminho, coluna, c1, c2, _n in SISTEMAS:
    for T_K, pts in sorted(ler(caminho, coluna).items()):
        avisam = []
        for modelo, kw in (("Margules (1-P)", {}), ("Margules (2-P)", {}), ("Van Laar", {}),
                           ("Wilson", {}), ("NRTL", {"params_fixos": {"alpha12": 0.3}})):
            rr = regress_params_barker(modelo, c1, c2, T_K - 273.15, pts, **kw)
            f, _ = faixa(c1, c2, T_K - 273.15, modelo, rr["params"])
            if f is not None:
                avisam.append(modelo)
        esperado = ["Margules (1-P)", "Margules (2-P)", "Van Laar", "NRTL"] if c2 == "2,3-dimethyl-2-butene" else []
        conferir(avisam == esperado, f"{nome}, {T_K} K, ajustes de Barker: avisam {avisam} (esperado {esperado}).")

# 3. sistema que se separa de fato
for modelo in ("UNIFAC", "UNIQUAC"):
    p = montar_parametros_automaticos(modelo, "1-butanol", "water")
    f, _ = faixa("1-butanol", "water", 60.0, modelo, p)
    conferir(f is not None, f"1-butanol/água a 60 °C, {modelo}: aviso ({f}).")

# 4. NRTL e Van Laar com interação forte
f, _ = faixa("ethanol", "water", 70.0, "NRTL", {"tau12": 2.5, "tau21": 2.5, "alpha12": 0.3})
conferir(f is not None, f"NRTL τ = 2,5: aviso ({f}).")
f, _ = faixa("ethanol", "water", 70.0, "Van Laar", {"A12": 2.5, "A21": 1.5})
conferir(f is not None, f"Van Laar 2,5/1,5: aviso ({f}).")

# texto da UI
r = calculate_vle_isothermal("ethanol", "water", 70.0, "Margules (1-P)", {"A": 3.0})
av = fg.aviso_instabilidade_liquida(r["x1"], r["gamma1"])
conferir(av is not None and "duas fases líquidas" in av and "0,2" in av and "0,7" in av and "não vale" in av,
         f"texto do aviso na UI: {av}")
r = calculate_vle_isothermal("ethanol", "water", 70.0, "Margules (1-P)", {"A": 1.0})
conferir(fg.aviso_instabilidade_liquida(r["x1"], r["gamma1"]) is None, "UI sem aviso para A = 1.")

# 5. malha curta ou vazia
conferir(detectar_instabilidade_liquida([], []) is None and detectar_instabilidade_liquida([0.3, 0.5], [1.1, 1.2]) is None,
         "malha vazia ou curta não dá erro.")

if falhas:
    print(f"\n{len(falhas)} falha(s).")
    sys.exit(1)
print("\nTodos os testes passaram.")
