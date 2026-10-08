"""
Van Laar e Margules 1-P contra ln γ "experimental" de dado NIST/ThermoML
(2026-10-08).

A `thermo` não tem Van Laar nem Margules, então estes dois modelos não têm
oráculo de biblioteca. Esta validação usa o que o projeto tem de oficializado:
as 10 isotermas NIST/TRC ThermoML em `referencias/` (etanol/água, Cristino
2013; metanol/2,3-dimetil-2-buteno, Feng 2011; clorofórmio/2-butanona, Clara
2006) — o mesmo conjunto e o mesmo método de `teste_margules_2p_nist_ln_gamma.py`
(ln γ experimental pelo método INDIRETO, γᵢ = yᵢ·P/(xᵢ·Pᵢˢᵃᵗ), só no interior
0,10 ≤ x₁ ≤ 0,90, Psat da `thermo`). O ajuste do app é por Barker (minimiza P e
y), então a comparação com o ln γ não é circular.

Verifica, por isoterma:
  1. o sinal dos parâmetros ajustados é o do desvio medido;
  2. o RMS de ln γ do modelo ajustado (Barker) contra o ln γ experimental fica
     abaixo de uma tolerância medida;
  3. estimador linear INDEPENDENTE do Barker, a partir do ln γ experimental:
       Van Laar:    x₁x₂·RT/Gᴱ = x₁/A₂₁ + x₂/A₁₂   (reta em x₁)
       Margules 1P: Gᴱ/(RT·x₁x₂) = A               (constante; usa a média)
     com Gᴱ/RT = x₁ ln γ₁ + x₂ ln γ₂ medido. Os parâmetros do Barker ficam
     próximos dos do estimador (tolerância medida).

O que este teste NÃO prova: dado real mostra que o modelo DESCREVE o sistema
(adequação), não que a fórmula está escrita certa — isso é papel de um teste
por primeiros princípios (definição termodinâmica), que o Margules 2-P já tem
em `teste_margules_2p_primeiros_principios.py`. O Margules 1-P, por ter um
parâmetro só, é simétrico: descreve mal sistemas assimétricos, e isso aparece
aqui como RMS maior (limite do modelo, não bug).

As tolerâncias foram fixadas depois de medir (valor medido ao lado de cada
constante): verificação de sanidade, não calibração — nada no motor foi
ajustado a esses números.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_van_laar_margules_1p_nist_ln_gamma.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calculos.gemini import regress_params_barker  # noqa: E402
from teste_margules_2p_nist_ln_gamma import (  # noqa: E402
    SISTEMAS,
    ler,
    ln_gamma_experimental,
    rms_ln_gamma,
)

TOL_RMS_VAN_LAAR = 0.080     # pior medido: 0,065 (metanol/dimetilbuteno a 100 °C)
TOL_RMS_MARGULES_1P = 0.150  # pior medido: 0,119 (etanol/água a 90 °C; sistema assimétrico, 1 parâmetro só)
TOL_PARAM_VAN_LAAR = 0.50    # |Barker − linearizado|; pior medido: 0,41. Folgada: a reta usa só 0,1 ≤ x₁ ≤ 0,9 e extrapola às pontas, e 1/intercepto amplifica o ruído
TOL_PARAM_MARGULES_1P = 0.35 # |A_Barker − média de Gᴱ/(RT·x₁x₂)|; pior medido: 0,28


def g_excesso_medido(exp):
    """Gᴱ/RT medido nos pontos do interior, e x₁, x₂."""
    x1 = exp[:, 0]
    x2 = 1 - x1
    return x1, x2, x1 * exp[:, 1] + x2 * exp[:, 2]


def estimador_van_laar(exp):
    """A₁₂, A₂₁ por reta de x₁x₂/(Gᴱ/RT) contra x₁: intercepto em x₁=0 é 1/A₁₂,
    em x₁=1 é 1/A₂₁."""
    x1, x2, g = g_excesso_medido(exp)
    y = x1 * x2 / g
    inclinacao, intercepto = np.polyfit(x1, y, 1)
    return 1.0 / intercepto, 1.0 / (intercepto + inclinacao)


def estimador_margules_1p(exp):
    x1, x2, g = g_excesso_medido(exp)
    return float(np.mean(g / (x1 * x2)))


def main():
    falhas = []
    piores = {"vl_rms": 0.0, "m1_rms": 0.0, "vl_dif": 0.0, "m1_dif": 0.0}
    for nome, caminho, coluna, comp1, comp2, n_isotermas in SISTEMAS:
        dados = ler(caminho, coluna)
        assert len(dados) == n_isotermas, f"CSV de referência alterado: {nome}"
        print(f"\n=== {nome} ===")
        for T_K, pts in sorted(dados.items()):
            T_C = T_K - 273.15
            exp = ln_gamma_experimental(pts, comp1, comp2, T_K)
            assert len(exp) >= 4, f"pontos insuficientes no interior: {nome} {T_K} K"
            sinal_exp = (np.sign(exp[:, 1].mean()), np.sign(exp[:, 2].mean()))

            # --- Van Laar ---
            rv = regress_params_barker("Van Laar", comp1, comp2, T_C, pts)
            pv = rv["params"]
            rms_v = rms_ln_gamma("Van Laar", pv, exp)
            A12_l, A21_l = estimador_van_laar(exp)
            dif_v = max(abs(pv["A12"] - A12_l), abs(pv["A21"] - A21_l))
            sinal_v = (np.sign(pv["A12"]), np.sign(pv["A21"]))
            ok_v = (sinal_v == sinal_exp and rms_v < TOL_RMS_VAN_LAAR and dif_v < TOL_PARAM_VAN_LAAR
                    and rv["sucesso"] and not rv["no_limite"])

            # --- Margules 1-P ---
            rm = regress_params_barker("Margules (1-P)", comp1, comp2, T_C, pts)
            pm = rm["params"]
            rms_m = rms_ln_gamma("Margules (1-P)", pm, exp)
            A_l = estimador_margules_1p(exp)
            dif_m = abs(pm["A"] - A_l)
            sinal_m = np.sign(pm["A"])
            ok_m = (sinal_m == sinal_exp[0] == sinal_exp[1] and rms_m < TOL_RMS_MARGULES_1P
                    and dif_m < TOL_PARAM_MARGULES_1P and rm["sucesso"] and not rm["no_limite"])

            piores["vl_rms"] = max(piores["vl_rms"], rms_v)
            piores["m1_rms"] = max(piores["m1_rms"], rms_m)
            piores["vl_dif"] = max(piores["vl_dif"], dif_v)
            piores["m1_dif"] = max(piores["m1_dif"], dif_m)
            print(f"  T={T_K:6.2f} K  n_int={len(exp):2d} | "
                  f"VanLaar Barker A12={pv['A12']:6.3f} A21={pv['A21']:6.3f} "
                  f"linear A12={A12_l:6.3f} A21={A21_l:6.3f} (dif {dif_v:.3f}) RMS={rms_v:.3f} "
                  f"{'OK' if ok_v else 'FALHA'} | "
                  f"Margules1P Barker A={pm['A']:6.3f} linear A={A_l:6.3f} (dif {dif_m:.3f}) RMS={rms_m:.3f} "
                  f"{'OK' if ok_m else 'FALHA'}")
            if not ok_v:
                falhas.append((nome, T_K, "Van Laar"))
            if not ok_m:
                falhas.append((nome, T_K, "Margules (1-P)"))

    print(f"\npior RMS de ln γ — Van Laar: {piores['vl_rms']:.3f}; Margules 1-P: {piores['m1_rms']:.3f}")
    print(f"pior diferença Barker × linear — Van Laar: {piores['vl_dif']:.3f}; Margules 1-P: {piores['m1_dif']:.3f}")
    if falhas:
        print(f"FALHA: {falhas}")
        raise SystemExit(1)
    print("OK: Van Laar e Margules 1-P ajustados reproduzem o ln γ experimental nas 10 isotermas NIST.")


if __name__ == "__main__":
    main()
