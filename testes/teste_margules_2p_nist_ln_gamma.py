"""
Margules 2-P contra ln γ "experimental" de dado NIST/ThermoML (2026-10-08).

Complementa `teste_margules_2p_primeiros_principios.py` (que valida a FÓRMULA
pela definição termodinâmica) olhando o modelo contra dado real: nas 10
isotermas dos três sistemas com fonte citável em `referencias/` (etanol/água,
Cristino 2013; metanol/2,3-dimetil-2-buteno, Feng 2011; clorofórmio/2-butanona,
Clara 2006), calcula o ln γ experimental pelo método INDIRETO (inverte a Raoult
modificada nos pontos (P, x₁, y₁) medidos, com a mesma Psat da `thermo` que o
app usa):

    γ₁ = y₁·P / (x₁·P₁ˢᵃᵗ),   γ₂ = y₂·P / (x₂·P₂ˢᵃᵗ)

e confere o Margules 2-P ajustado pelo app (regressão de Barker) contra ele.
É um método diferente do usado pelo ajuste (Barker minimiza P e y, não γ), de
modo que o resultado não é circular.

Importante — o que este teste NÃO prova: um dado real mostra que o modelo
descreve o sistema (adequação), não que a fórmula está certa; isso é papel do
teste de primeiros princípios. Aqui o dado também sofre da amplificação de ruído
que levou o projeto a preferir Barker (seção 2.8 do mapeamento), então só os
pontos com 0,10 ≤ x₁ ≤ 0,90 entram na comparação.

Verifica, por isoterma:
  1. o sinal de A₁₂ e A₂₁ ajustados é o do desvio medido (ln γ experimental
     médio positivo ou negativo, por componente);
  2. o ln γ do Margules 2-P ajustado reproduz o ln γ experimental (RMS no
     interior, abaixo de uma tolerância medida);
  3. estimador independente — a linearização clássica do Margules 2-P,
     Gᴱ/(RT·x₁x₂) = A₁₂·x₂ + A₂₁·x₁ (mínimos quadrados lineares sobre o ln γ
     experimental) — dá A₁₂ e A₂₁ próximos dos da regressão de Barker.

Para contexto, imprime o mesmo RMS de ln γ do Van Laar e do Wilson (não entram
nos critérios). As tolerâncias foram fixadas depois de medir (valor medido ao
lado de cada constante): verificação de sanidade, não calibração — nada no
motor foi ajustado a esses números.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_margules_2p_nist_ln_gamma.py
"""

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from thermo import Chemical

from calculos.gemini import MODELS_GE, regress_params_barker

REF = Path(__file__).resolve().parent.parent / "referencias"

SISTEMAS = [
    ("etanol + água", REF / "nist_thermoml_cristino2013_etanol_agua_isotermas.csv",
     "etanol", "ethanol", "water", 5),
    ("metanol + 2,3-dimetil-2-buteno", REF / "nist_thermoml_feng2011_metanol_dimetilbuteno_isotermas.csv",
     "metanol", "methanol", "2,3-dimethyl-2-butene", 4),
    ("clorofórmio + 2-butanona", REF / "nist_thermoml_clara2006_cloroformio_mek_303K.csv",
     "cloroformio", "chloroform", "2-butanone", 1),
]

X_MIN, X_MAX = 0.10, 0.90
TOL_RMS_LN_GAMMA = 0.080   # pior medido: 0,065 (metanol/dimetilbuteno a 100 °C)
TOL_PARAM_LINEAR = 0.50    # |A_barker − A_linearizado|; pior medido: 0,42 (mesmo caso). Folgada de propósito: a linearização usa só 0,1 ≤ x₁ ≤ 0,9 e extrapola às pontas


def ler(csv_path, coluna):
    por_T = defaultdict(list)
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            por_T[float(r["T_K"])].append(
                (float(r["P_kPa"]), float(r["x_" + coluna]), float(r["y_" + coluna]))
            )
    return {T: sorted(v, key=lambda p: p[1]) for T, v in por_T.items()}


def ln_gamma_experimental(pts, comp1, comp2, T_K):
    """(x1, ln γ₁, ln γ₂) nos pontos do interior, pelo método indireto."""
    psat1 = Chemical(comp1, T=T_K).Psat / 1000.0
    psat2 = Chemical(comp2, T=T_K).Psat / 1000.0
    saida = []
    for P, x1, y1 in pts:
        if not (X_MIN <= x1 <= X_MAX):
            continue
        g1 = y1 * P / (x1 * psat1)
        g2 = (1 - y1) * P / ((1 - x1) * psat2)
        saida.append((x1, np.log(g1), np.log(g2)))
    return np.array(saida)


def rms_ln_gamma(modelo, params, exp):
    # os modelos do app recebem x₁ escalar (Van Laar e Wilson tratam os limites com `if`)
    ln = np.array([np.log(MODELS_GE[modelo](float(x), params)) for x in exp[:, 0]])
    res = np.concatenate([ln[:, 0] - exp[:, 1], ln[:, 1] - exp[:, 2]])
    return float(np.sqrt(np.mean(res**2)))


def linearizacao(exp):
    """A₁₂, A₂₁ por mínimos quadrados lineares de Gᴱ/(RT·x₁x₂) contra x₁."""
    x1 = exp[:, 0]
    y = (x1 * exp[:, 1] + (1 - x1) * exp[:, 2]) / (x1 * (1 - x1))
    inclinacao, intercepto = np.polyfit(x1, y, 1)
    A12 = intercepto                  # em x₁ = 0: Gᴱ/(RT·x₁x₂) = A₁₂
    A21 = intercepto + inclinacao     # em x₁ = 1: = A₂₁
    return A12, A21


def main():
    falhas = []
    maior_rms = maior_dif = 0.0
    for nome, caminho, coluna, comp1, comp2, n_isotermas in SISTEMAS:
        dados = ler(caminho, coluna)
        assert len(dados) == n_isotermas, f"CSV de referência alterado: {nome}"
        print(f"\n=== {nome} ===")
        for T_K, pts in sorted(dados.items()):
            T_C = T_K - 273.15
            exp = ln_gamma_experimental(pts, comp1, comp2, T_K)
            assert len(exp) >= 4, f"pontos insuficientes no interior: {nome} {T_K} K"

            rr = regress_params_barker("Margules (2-P)", comp1, comp2, T_C, pts)
            p = rr["params"]
            rms = rms_ln_gamma("Margules (2-P)", p, exp)
            A12_l, A21_l = linearizacao(exp)
            dif = max(abs(p["A12"] - A12_l), abs(p["A21"] - A21_l))
            maior_rms, maior_dif = max(maior_rms, rms), max(maior_dif, dif)

            # contexto: outros modelos de 2 parâmetros contra o mesmo ln γ experimental
            contexto = {}
            for outro in ("Van Laar", "Wilson"):
                ro = regress_params_barker(outro, comp1, comp2, T_C, pts)
                contexto[outro] = rms_ln_gamma(outro, ro["params"], exp)

            sinal_exp = (np.sign(exp[:, 1].mean()), np.sign(exp[:, 2].mean()))
            sinal_mod = (np.sign(p["A12"]), np.sign(p["A21"]))
            ok_sinal = sinal_exp == sinal_mod
            ok_rms = rms < TOL_RMS_LN_GAMMA
            ok_lin = dif < TOL_PARAM_LINEAR
            ok = ok_sinal and ok_rms and ok_lin and rr["sucesso"] and not rr["no_limite"]
            print(f"  T={T_K:6.2f} K  n_int={len(exp):2d}  Barker A12={p['A12']:6.3f} A21={p['A21']:6.3f} | "
                  f"linearizado A12={A12_l:6.3f} A21={A21_l:6.3f} (dif {dif:.3f}) | "
                  f"RMS lnγ: Margules2P={rms:.3f} VanLaar={contexto['Van Laar']:.3f} Wilson={contexto['Wilson']:.3f} | "
                  f"sinal {'ok' if ok_sinal else 'ERRADO'}  {'OK' if ok else 'FALHA'}")
            if not ok:
                falhas.append((nome, T_K, dict(sinal=ok_sinal, rms=rms, dif=dif, sucesso=rr["sucesso"],
                                              no_limite=rr["no_limite"])))

    print(f"\npior RMS de ln γ do Margules 2-P: {maior_rms:.3f} (tolerância {TOL_RMS_LN_GAMMA})")
    print(f"pior diferença Barker × linearização: {maior_dif:.3f} (tolerância {TOL_PARAM_LINEAR})")
    if falhas:
        print(f"FALHA: {falhas}")
        raise SystemExit(1)
    print("OK: Margules 2-P ajustado reproduz o ln γ experimental nas 10 isotermas NIST.")


if __name__ == "__main__":
    main()
