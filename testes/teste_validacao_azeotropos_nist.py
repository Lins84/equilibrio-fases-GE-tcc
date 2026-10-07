"""
Validação do motor de cálculo contra dois sistemas com azeótropo, de dado
experimental com fonte citável (2026-10-07). Complementa
`teste_validacao_nist_etanol_agua.py` (que valida os modelos do banco IPDB)
cobrindo o que aquele não cobre:

  * azeótropo de pressão MÁXIMA (mínimo ponto de ebulição, desvio positivo):
    metanol + 2,3-dimetil-2-buteno, Feng, Dong e Li, Fluid Phase Equilib. 309
    (2011) 201-205, doi:10.1016/j.fluid.2011.07.014 — 4 isotermas, 70-100 °C;
  * azeótropo de pressão MÍNIMA (máximo ponto de ebulição, desvio NEGATIVO):
    clorofórmio + 2-butanona, Clara, Marigliano e Solimo, J. Chem. Eng. Data
    51 (2006) 1473-1478, doi:10.1021/je060150a — 30 °C.

Dados do NIST/TRC ThermoML Archive (doi:10.18434/mds2-2422), públicos,
extraídos pelo TRC e NÃO avaliados criticamente — fonte e ressalvas no
cabeçalho de cada CSV em `referencias/`. Nenhum dos dois pares tem parâmetros
no IPDB, então a única via é a regressão de Barker (o caso de uso original
dela: par sem banco).

Verifica:
  1. P medido nos componentes puros bate com a Psat do `thermo` (sanidade
     do dado e da Psat);
  2. o azeótropo existe no dado e é do tipo esperado (cruzamento de y − x;
     P extremo no interior);
  3. a regressão de Barker converge nos modelos regressáveis, sem parâmetro
     preso no limite, com resíduo pequeno, e reproduz P e y;
  4. o azeótropo previsto pelo modelo ajustado existe, é do tipo certo e cai
     perto do experimental (tolerância por sistema, abaixo);
  5. no desvio negativo (clorofórmio/MEK), Van Laar fica com A₁₂ e A₂₁ < 0
     — caso real que exigiu o chute inicial extra (CLAUDE.md, 2026-10-06).

As tolerâncias foram fixadas depois de medir (valor medido indicado ao lado
de cada constante): são verificação de sanidade, não calibração — nada no
motor foi ajustado a esses números.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_validacao_azeotropos_nist.py
"""

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from thermo import Chemical

from calculos.gemini import (
    REGRESSAO_MODELOS,
    calculate_vle_isothermal,
    regress_params_barker,
)

REF = Path(__file__).resolve().parent.parent / "referencias"

SISTEMAS = [
    {
        "nome": "metanol + 2,3-dimetil-2-buteno",
        "csv": REF / "nist_thermoml_feng2011_metanol_dimetilbuteno_isotermas.csv",
        "col": "metanol",
        "comp1": "methanol",
        "comp2": "2,3-dimethyl-2-butene",
        "n_isotermas": 4,
        "n_pontos": 85,
        "tipo": "max",   # pressão máxima no interior
        "tol_psat_puros": 0.5,    # % ; medido: até 0,33 %
        "tol_azeotropo_x": 0.03,  # |x_az modelo − x_az exp|; medido: até 0,015
    },
    {
        "nome": "clorofórmio + 2-butanona",
        "csv": REF / "nist_thermoml_clara2006_cloroformio_mek_303K.csv",
        "col": "cloroformio",
        "comp1": "chloroform",
        "comp2": "2-butanone",
        "n_isotermas": 1,
        "n_pontos": 22,
        "tipo": "min",   # pressão mínima no interior
        "tol_psat_puros": 4.0,    # % ; medido: 0,4 % (CHCl3) e 3,2 % (MEK) — dado do MEK 3 % acima da Psat
        "tol_azeotropo_x": 0.10,  # a região do mínimo é quase plana; medido: 0,045-0,050 (modelo em x1 ≈ 0,14-0,15 contra 0,191)
    },
]

MODELOS = ("Margules (2-P)", "Van Laar", "Wilson", "NRTL")
TOL_BARKER_DP, TOL_BARKER_DY = 3.5, 0.040  # % e fração molar (RMS); pior medido: 2,0 % e 0,0245
TOL_RESIDUO_BARKER = 0.035                 # pior medido: 0,0213


def ler(sistema):
    por_T = defaultdict(list)
    with open(sistema["csv"], encoding="utf-8") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            por_T[float(r["T_K"])].append(
                (float(r["P_kPa"]), float(r["x_" + sistema["col"]]), float(r["y_" + sistema["col"]]))
            )
    return {T: sorted(v, key=lambda p: p[1]) for T, v in por_T.items()}


def azeotropo_experimental(pts):
    """x1 onde y − x troca de sinal (interpolação linear entre os dois pontos
    vizinhos) e o P máximo/mínimo do interior; None se não houver cruzamento."""
    x = np.array([p[1] for p in pts]); y = np.array([p[2] for p in pts])
    d = y - x
    for i in range(1, len(d) - 1):  # fora dos extremos, onde y − x é 0 por construção
        if d[i] == 0:               # ponto medido exatamente sobre o azeótropo (ex.: 363,15 K, x1 = 0,612)
            return x[i]
        if d[i] * d[i + 1] < 0:
            return x[i] + (x[i + 1] - x[i]) * d[i] / (d[i] - d[i + 1])
    return None


def azeotropo_modelo(comp1, comp2, T_C, modelo, params):
    """Mesmo critério, sobre a malha de 101 pontos do próprio motor."""
    r = calculate_vle_isothermal(comp1, comp2, T_C, modelo, params)
    x = np.array(r["x1"]); d = np.array(r["y1"]) - x
    for i in range(1, len(d) - 2):  # fora dos extremos, onde y − x é 0 por construção
        if d[i] * d[i + 1] < 0:
            return x[i] + (x[i + 1] - x[i]) * d[i] / (d[i] - d[i + 1])
    return None


def deltas(sistema, modelo, params, T_C, pts):
    x = np.array([p[1] for p in pts]); P = np.array([p[0] for p in pts]); y = np.array([p[2] for p in pts])
    r = calculate_vle_isothermal(sistema["comp1"], sistema["comp2"], T_C, modelo, params, x1_values=x)
    dP = 100 * np.sqrt(np.mean(((np.array(r["P_kPa"]) - P) / P) ** 2))
    dy = np.sqrt(np.mean((np.array(r["y1"]) - y) ** 2))
    return dP, dy


def main():
    falhas = []
    for s in SISTEMAS:
        dados = ler(s)
        assert len(dados) == s["n_isotermas"] and sum(len(v) for v in dados.values()) == s["n_pontos"], \
            f"CSV de referência alterado: {s['nome']}"
        print(f"\n=== {s['nome']} ===")
        for T_K, pts in sorted(dados.items()):
            T_C = T_K - 273.15
            print(f"T = {T_K} K ({T_C:.2f} °C), {len(pts)} pontos")

            # 1. P dos puros contra Psat do thermo.
            for rotulo, comp, p_exp in ((s["comp2"], s["comp2"], pts[0][0]), (s["comp1"], s["comp1"], pts[-1][0])):
                psat = Chemical(comp, T=T_K).Psat / 1000.0
                erro = 100 * abs(p_exp - psat) / psat
                ok = erro < s["tol_psat_puros"]
                print(f"  puro {rotulo:22s} P exp={p_exp:7.2f}  Psat={psat:7.2f}  erro={erro:4.2f}%  {'OK' if ok else 'FALHA'}")
                if not ok:
                    falhas.append((s["nome"], T_K, "psat_puro", rotulo, erro))

            # 2. Azeótropo no dado.
            assert pts[0][1] == 0.0 and pts[-1][1] == 1.0, "o dado deveria ter os dois puros"
            x_az = azeotropo_experimental(pts)
            P_int = [p[0] for p in pts[1:-1]]
            extremo = max(P_int) if s["tipo"] == "max" else min(P_int)
            puros = (pts[0][0], pts[-1][0])
            tipo_ok = extremo > max(puros) if s["tipo"] == "max" else extremo < min(puros)
            ok = x_az is not None and tipo_ok
            print(f"  azeótropo exp: x1≈{x_az:.3f}, P {'máx' if s['tipo']=='max' else 'mín'} interior={extremo:.2f}  {'OK' if ok else 'FALHA'}")
            if not ok:
                falhas.append((s["nome"], T_K, "azeotropo_exp"))
                continue

            # 3-5. Regressão de Barker e azeótropo do modelo ajustado.
            for modelo in MODELOS:
                kw = {"params_fixos": {"alpha12": 0.3}} if modelo == "NRTL" else {}
                rr = regress_params_barker(modelo, s["comp1"], s["comp2"], T_C, pts, **kw)
                params = dict(rr["params"])
                dP, dy = deltas(s, modelo, params, T_C, pts)
                lo, hi = REGRESSAO_MODELOS[modelo]["limites"]
                no_limite = [k for k, a, b in zip(REGRESSAO_MODELOS[modelo]["livres"], lo, hi)
                             if abs(params[k] - a) < 1e-3 * (1 + abs(a)) or abs(params[k] - b) < 1e-3 * (1 + abs(b))]
                ok = (rr["sucesso"] and not no_limite and rr["residual_rms"] < TOL_RESIDUO_BARKER
                      and dP < TOL_BARKER_DP and dy < TOL_BARKER_DY)
                x_mod = azeotropo_modelo(s["comp1"], s["comp2"], T_C, modelo, params)
                ok_az = x_mod is not None and abs(x_mod - x_az) < s["tol_azeotropo_x"]
                txt_az = f"{x_mod:.3f}" if x_mod is not None else "ausente"
                print(f"  Barker {modelo:14s} ΔP={dP:5.2f}%  Δy={dy:.4f}  rms={rr['residual_rms']:.4f}  "
                      f"{'OK' if ok else 'FALHA'} | azeótropo x1={txt_az} (dx={abs(x_mod - x_az) if x_mod is not None else float('nan'):.3f}) {'OK' if ok_az else 'FALHA'}")
                if not ok:
                    falhas.append((s["nome"], T_K, modelo, "barker", dP, dy))
                if not ok_az:
                    falhas.append((s["nome"], T_K, modelo, "azeotropo_modelo", x_mod, x_az))
                if modelo == "Van Laar" and s["tipo"] == "min":
                    neg = params["A12"] < 0 and params["A21"] < 0
                    print(f"    Van Laar desvio negativo: A12={params['A12']:.3f} A21={params['A21']:.3f}  {'OK' if neg else 'FALHA'}")
                    if not neg:
                        falhas.append((s["nome"], T_K, "van_laar_sinal", params))

    print()
    if falhas:
        print(f"FALHA: {len(falhas)} caso(s) fora da tolerância: {falhas}")
        raise SystemExit(1)
    print("OK: regressão de Barker e azeótropo validados contra dado NIST/ThermoML nos dois sistemas.")


if __name__ == "__main__":
    main()
