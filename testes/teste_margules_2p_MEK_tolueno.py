"""
Conferência SECUNDÁRIA do `model_margules_2p` contra uma planilha, sistema
Metil-etil-cetona (1) / Tolueno (2) a 323,15 K.

Fonte: planilha Excel do pacote XSEOS (canal "Youtermo", YouTube). Procedência
sem rastreio e só três casas decimais: serve para pegar erro grosseiro, não
como validação do modelo. A validação do modelo está em
`teste_margules_2p_primeiros_principios.py` (definição termodinâmica) e
`teste_margules_2p_nist_ln_gamma.py` (dado experimental com fonte).

Correção de 2026-10-08: até então este teste comparava a planilha com uma CÓPIA
da fórmula escrita aqui dentro (`_margules_2p_referencia`), e nunca chamava o
`model_margules_2p` do `calculos/gemini.py`. Agora a comparação principal é
com o modelo real, depois de converter A/B para A12/A21; a cópia ficou só para
conferir a conversão.

Modelo (forma A/B de Smith/Van Ness/Abbott, usada na planilha):
    g^E = xa*xb*[A + B*(xa - xb)]
    RT*ln(gamma_a) = (A + 3B)*xb^2 - 4B*xb^3
    RT*ln(gamma_b) = (A - 3B)*xa^2 + 4B*xa^3
Forma do app (adimensional): A12 = (A - B)/RT e A21 = (A + B)/RT.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_margules_2p_MEK_tolueno.py
"""

import sys

import numpy as np

from calculos.gemini import model_margules_2p

R = 8.314  # J/(mol.K)
T = 323.15  # K
A = 765.70069
B = -233.74021

# Dados de referência: (x1, ln_gamma1, ln_gamma2)
DADOS_REFERENCIA = [
    (0.00, 0.372, 0.000),
    (0.10, 0.273, 0.005),
    (0.20, 0.194, 0.019),
    (0.30, 0.131, 0.040),
    (0.40, 0.084, 0.065),
    (0.50, 0.050, 0.093),
    (0.60, 0.026, 0.121),
    (0.70, 0.012, 0.148),
    (0.80, 0.004, 0.171),
    (0.90, 0.001, 0.189),
    (1.00, 0.000, 0.198),
]


def comparar_com_implementacao(funcao_margules_2p):
    """
    Compara os valores de referência (DADOS_REFERENCIA) com os calculados
    por `funcao_margules_2p`, e imprime uma tabela com a diferença absoluta.

    Args:
        funcao_margules_2p: função com assinatura (x1, A, B, R, T) -> (ln_gamma1, ln_gamma2)
    """
    cabecalho = (
        f"{'x1':>6} | {'ln_g1_ref':>10} | {'ln_g1_calc':>11} | {'dif_g1':>8} | "
        f"{'ln_g2_ref':>10} | {'ln_g2_calc':>11} | {'dif_g2':>8}"
    )
    print(cabecalho)
    print("-" * len(cabecalho))

    for x1, ln_g1_ref, ln_g2_ref in DADOS_REFERENCIA:
        ln_g1_calc, ln_g2_calc = funcao_margules_2p(x1, A, B, R, T)
        dif_g1 = abs(ln_g1_calc - ln_g1_ref)
        dif_g2 = abs(ln_g2_calc - ln_g2_ref)

        print(
            f"{x1:6.2f} | {ln_g1_ref:10.3f} | {ln_g1_calc:11.5f} | {dif_g1:8.5f} | "
            f"{ln_g2_ref:10.3f} | {ln_g2_calc:11.5f} | {dif_g2:8.5f}"
        )


def _margules_2p_referencia(x1, A, B, R, T):
    """Implementação de referência da fórmula Margules 2P (three-suffix)."""
    xa = x1
    xb = 1 - x1

    RT_ln_gamma_a = (A + 3 * B) * xb**2 - 4 * B * xb**3
    RT_ln_gamma_b = (A - 3 * B) * xa**2 + 4 * B * xa**3

    ln_gamma1 = RT_ln_gamma_a / (R * T)
    ln_gamma2 = RT_ln_gamma_b / (R * T)
    return ln_gamma1, ln_gamma2


def _gemini_margules_2p(x1, A, B, R, T):
    """`model_margules_2p` do app, com A/B (J/mol) convertidos para A12/A21."""
    RT = R * T
    g1, g2 = model_margules_2p(x1, {"A12": (A - B) / RT, "A21": (A + B) / RT})
    return float(np.log(g1)), float(np.log(g2))


if __name__ == "__main__":
    tolerancia = 0.001  # a planilha traz 3 casas decimais
    falhas = []

    print("1) model_margules_2p (calculos/gemini.py) contra a planilha:\n")
    comparar_com_implementacao(_gemini_margules_2p)
    for x1, ln_g1_ref, ln_g2_ref in DADOS_REFERENCIA:
        ln_g1, ln_g2 = _gemini_margules_2p(x1, A, B, R, T)
        if abs(ln_g1 - ln_g1_ref) >= tolerancia or abs(ln_g2 - ln_g2_ref) >= tolerancia:
            falhas.append(f"modelo do app em x1={x1}")

    print("\n2) Conversão A/B -> A12/A21 (cópia da fórmula da planilha contra o app, x1 de 0 a 1):")
    maior = 0.0
    for x1 in np.linspace(0.0, 1.0, 101):
        ref = _margules_2p_referencia(x1, A, B, R, T)
        app = _gemini_margules_2p(x1, A, B, R, T)
        maior = max(maior, abs(ref[0] - app[0]), abs(ref[1] - app[1]))
    print(f"   diferença máxima: {maior:.1e}")
    if maior > 1e-12:
        falhas.append(f"conversão A/B diferente do app: {maior:.2e}")

    print()
    if falhas:
        print(f"FALHA: {falhas}")
        sys.exit(1)
    print(f"OK: modelo do app dentro de {tolerancia} da planilha e conversão A/B exata.")
