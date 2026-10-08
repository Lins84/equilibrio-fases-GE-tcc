"""ln γ experimental da tabela, para o gráfico de ln γ (2026-10-08).

`ln_gamma_experimental` calcula, pelo método indireto (Raoult modificada,
γᵢ = yᵢ·P/(xᵢ·Pᵢˢᵃᵗ), Psat da thermo), o ln γ de cada ponto da tabela com
0,10 ≤ x₁ ≤ 0,90 (faixa decidida pelo autor). Verifica:

  1. contra a implementação independente do teste do Margules 2-P
     (`teste_margules_2p_nist_ln_gamma.ln_gamma_experimental`, escrita à parte), nas
     10 isotermas NIST: mesmos pontos e mesmos valores;
  2. ida e volta: dados gerados por um modelo (NRTL do banco, etanol/água) devolvem
     o ln γ do próprio modelo, com erro < 1e-9;
  3. a faixa: x₁ = 0,10 e 0,90 entram; 0,05 e 0,95 não; a saída vem ordenada;
  4. pontos fora do domínio (P ≤ 0, y₁ em 0 ou 1) são ignorados, sem erro;

A parte da tela (marcadores cheios no gráfico, coluna "Tabela" na legenda) foi
verificada por captura de tela, não por este script.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_ln_gamma_experimental.py
"""
import math
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "testes"))

from calculos.gemini import (  # noqa: E402
    LN_GAMMA_EXP_X_MAX,
    LN_GAMMA_EXP_X_MIN,
    buscar_parametros_banco,
    calculate_vle_isothermal,
    ln_gamma_experimental,
)
import teste_margules_2p_nist_ln_gamma as ref  # noqa: E402

falhas = []


def conferir(ok, msg):
    print(("OK: " if ok else "FALHOU: ") + msg)
    if not ok:
        falhas.append(msg)


conferir((LN_GAMMA_EXP_X_MIN, LN_GAMMA_EXP_X_MAX) == (0.10, 0.90), "faixa padrão 0,10 a 0,90.")

# 1. contra a implementação independente, nas 10 isotermas NIST
for nome, caminho, coluna, c1, c2, _n in ref.SISTEMAS:
    for T_K, pts in sorted(ref.ler(caminho, coluna).items()):
        novo = ln_gamma_experimental(pts, c1, c2, T_K - 273.15)
        velho = ref.ln_gamma_experimental(pts, c1, c2, T_K)
        ok = len(novo) == len(velho) and len(novo) >= 4
        if ok:
            novo_ord = np.array(novo)
            # ordem lexicográfica nos dois: o clorofórmio/MEK tem dois pontos em x₁ = 0,252
            velho_ord = np.array(sorted(map(tuple, velho)))
            ok = np.abs(novo_ord - velho_ord).max() < 1e-9
        conferir(ok, f"{nome}, {T_K} K: {len(novo)} pontos, iguais à implementação independente.")

# 2. ida e volta com o NRTL do banco
params = buscar_parametros_banco("NRTL", "ethanol", "water", 343.15)
xs = [0.02, 0.10, 0.25, 0.4, 0.5, 0.65, 0.8, 0.90, 0.97]
r = calculate_vle_isothermal("ethanol", "water", 70.0, "NRTL", params, x1_values=xs)
pts = list(zip(r["P_kPa"], r["x1"], r["y1"]))
exp = ln_gamma_experimental(pts, "ethanol", "water", 70.0)
esperado = [(x, math.log(a), math.log(b)) for x, a, b in zip(r["x1"], r["gamma1"], r["gamma2"]) if 0.10 <= x <= 0.90]
e = max(abs(a - b) for t, u in zip(exp, esperado) for a, b in zip(t, u))
conferir(len(exp) == len(esperado) == 7 and e < 1e-9, f"ida e volta com o NRTL: erro máx {e:.1e}, {len(exp)} pontos.")

# 3. faixa e ordem
conferir([round(x, 2) for x, _, _ in exp] == [0.10, 0.25, 0.4, 0.5, 0.65, 0.8, 0.9],
         "só 0,10 ≤ x₁ ≤ 0,90 (0,02 e 0,97 fora; 0,10 e 0,90 dentro), em ordem.")
exp_inv = ln_gamma_experimental(pts[::-1], "ethanol", "water", 70.0)
conferir(exp_inv == exp, "a ordem da tabela não importa: a saída sai ordenada por x₁.")

# 4. pontos fora do domínio
ruins = [(-1.0, 0.5, 0.5), (50.0, 0.5, 0.0), (50.0, 0.5, 1.0), (0.0, 0.5, 0.5), (50.0, 0.5, 0.6)]
saida = ln_gamma_experimental(ruins, "ethanol", "water", 70.0)
conferir(len(saida) == 1, "P ≤ 0 e y₁ = 0 ou 1 são ignorados sem erro (sobra o ponto válido).")
conferir(ln_gamma_experimental([], "ethanol", "water", 70.0) == [], "tabela vazia devolve lista vazia.")

if falhas:
    print(f"\n{len(falhas)} falha(s).")
    sys.exit(1)
print("\nTodos os testes passaram.")
