"""
Validação do motor de cálculo contra dado experimental com fonte citável
(2026-10-06). Substitui, como evidência, o CSV de etanol/água a 50 °C sem
fonte que foi removido (ver CLAUDE.md, "Decisões de engenharia do aluno").

Dado: Cristino et al., Fluid Phase Equilib. 341 (2013) 48-53,
doi:10.1016/j.fluid.2012.12.014, via NIST/TRC ThermoML Archive
(doi:10.18434/mds2-2422) — ver cabeçalho de
referencias/nist_thermoml_cristino2013_etanol_agua_isotermas.csv.
Limites: faixa de x1 incompleta e T alta (90-150 °C); dados não avaliados
criticamente pelo NIST/TRC.

Verifica, por isoterma:
  1. modelos com parâmetros do banco IPDB (sem ajuste aos dados) reproduzem
     os pontos dentro de ΔP e Δy toleráveis;
  2. a regressão de Barker converge para todos os modelos regressáveis, sem
     parâmetro preso no limite, com resíduo pequeno.
As tolerâncias foram fixadas depois de medir (folga de 1,5x a 2x sobre o
pior caso, indicado ao lado de cada constante): são verificação de sanidade,
não calibração — nada no motor foi ajustado a esses números.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_validacao_nist_etanol_agua.py
"""

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from calculos.gemini import (
    REGRESSAO_MODELOS,
    buscar_parametros_banco,
    calculate_vle_isothermal,
    montar_parametros_automaticos,
    regress_params_barker,
)

CSV = Path(__file__).resolve().parent.parent / "referencias" / "nist_thermoml_cristino2013_etanol_agua_isotermas.csv"

TOL_IPDB_DP, TOL_IPDB_DY = 7.0, 0.06      # % e fração molar (RMS); pior medido: 4,7 % e 0,038
TOL_BARKER_DP, TOL_BARKER_DY = 5.0, 0.04  # pior medido: 2,9 % e 0,018
QPRIME_ETANOL, QPRIME_AGUA = 0.92, 1.00   # q′ do ChemSep/Koretsky (UniquacQP do XML do ChemSep)
TOL_RESIDUO_BARKER = 0.04                  # pior medido: 0,023


def ler():
    por_T = defaultdict(list)
    with open(CSV, encoding="utf-8") as f:
        linhas = (l for l in f if not l.startswith("#"))
        for r in csv.DictReader(linhas):
            por_T[float(r["T_K"])].append((float(r["P_kPa"]), float(r["x_etanol"]), float(r["y_etanol"])))
    return {T: sorted(v, key=lambda p: p[1]) for T, v in por_T.items()}


def deltas(modelo, params, T_C, pts):
    x = np.array([p[1] for p in pts]); P = np.array([p[0] for p in pts]); y = np.array([p[2] for p in pts])
    r = calculate_vle_isothermal("ethanol", "water", T_C, modelo, params, x1_values=x)
    dP = 100 * np.sqrt(np.mean(((np.array(r["P_kPa"]) - P) / P) ** 2))
    dy = np.sqrt(np.mean((np.array(r["y1"]) - y) ** 2))
    return dP, dy


def main():
    dados = ler()
    assert len(dados) == 5 and sum(len(v) for v in dados.values()) == 76, "CSV de referência alterado"
    rq = montar_parametros_automaticos("UNIQUAC", "ethanol", "water")
    fixos_uniquac = {k: rq[k] for k in ("r1", "q1", "r2", "q2")}
    falhas = []

    for T_K, pts in sorted(dados.items()):
        T_C = T_K - 273.15
        print(f"\nT = {T_K} K ({T_C:.2f} °C), {len(pts)} pontos")
        for modelo in ("NRTL", "Wilson", "UNIQUAC", "UNIFAC"):
            params = (buscar_parametros_banco(modelo, "ethanol", "water", T_K)
                      if modelo in ("NRTL", "Wilson")
                      else montar_parametros_automaticos(modelo, "ethanol", "water"))
            dP, dy = deltas(modelo, params, T_C, pts)
            ok = dP < TOL_IPDB_DP and dy < TOL_IPDB_DY
            print(f"  banco/predito {modelo:8s} ΔP={dP:5.2f}%  Δy={dy:.4f}  {'OK' if ok else 'FALHA'}")
            if not ok:
                falhas.append((T_K, modelo, "banco", dP, dy))
        # q′ (Anderson e Prausnitz) com os a₁₂/a₂₁ do ChemSep: NÃO deve ser usado. Esses
        # parâmetros foram ajustados com q; trocar por q′ só na parte residual piora o ajuste
        # (medido: ΔP 4,0–5,0 % contra 1,3–3,5 % com q). Registra a razão de a UI não ligar q′.
        pq = dict(rq, qp1=QPRIME_ETANOL, qp2=QPRIME_AGUA)
        dP_q = deltas("UNIQUAC", rq, T_C, pts)[0]
        dP_qp = deltas("UNIQUAC", pq, T_C, pts)[0]
        ok = dP_qp > dP_q
        print(f"  UNIQUAC com q′ (não usar) ΔP={dP_qp:5.2f}% contra {dP_q:5.2f}% com q  {'OK' if ok else 'FALHA'}")
        if not ok:
            falhas.append((T_K, "UNIQUAC", "q′ não piorou", dP_qp, dP_q))
        for modelo, kw in (("Margules (2-P)", {}), ("Van Laar", {}), ("Wilson", {}),
                           ("NRTL", {"params_fixos": {"alpha12": 0.3}}),
                           ("UNIQUAC", {"params_fixos": fixos_uniquac})):
            rr = regress_params_barker(modelo, "ethanol", "water", T_C, pts, **kw)
            params = dict(rr["params"])
            dP, dy = deltas(modelo, params, T_C, pts)
            lo, hi = REGRESSAO_MODELOS[modelo]["limites"]
            no_limite = [k for k, a, b in zip(REGRESSAO_MODELOS[modelo]["livres"], lo, hi)
                         if abs(params[k] - a) < 1e-3 * (1 + abs(a)) or abs(params[k] - b) < 1e-3 * (1 + abs(b))]
            ok = (rr["sucesso"] and not no_limite and rr["residual_rms"] < TOL_RESIDUO_BARKER
                  and dP < TOL_BARKER_DP and dy < TOL_BARKER_DY)
            print(f"  Barker {modelo:14s} ΔP={dP:5.2f}%  Δy={dy:.4f}  rms={rr['residual_rms']:.4f}  {'OK' if ok else 'FALHA'}")
            if not ok:
                falhas.append((T_K, modelo, "barker", dP, dy))

    print()
    if falhas:
        print(f"FALHA: {len(falhas)} caso(s) fora da tolerância: {falhas}")
        raise SystemExit(1)
    print("OK: modelos do banco e regressão de Barker validados contra dado NIST/ThermoML (Cristino 2013).")


if __name__ == "__main__":
    main()
