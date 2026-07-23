"""
Caso de teste de validação para o modelo Margules 2P (three-suffix),
sistema Metil-etil-cetona (1) / Tolueno (2) a 323,15 K.

Fonte: planilha Excel do pacote XSEOS (canal "Youtermo", YouTube).

Modelo (forma A/B de Smith/Van Ness/Abbott):
    g^E = xa*xb*[A + B*(xa - xb)]
    RT*ln(gamma_a) = (A + 3B)*xb^2 - 4B*xb^3
    RT*ln(gamma_b) = (A - 3B)*xa^2 + 4B*xa^3
"""

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


if __name__ == "__main__":
    print("Comparando implementação de referência com os dados de validação:\n")
    comparar_com_implementacao(_margules_2p_referencia)

    print("\nVerificando se todas as diferenças ficam abaixo de 0.001...")
    tolerancia = 0.001
    todas_ok = True
    for x1, ln_g1_ref, ln_g2_ref in DADOS_REFERENCIA:
        ln_g1_calc, ln_g2_calc = _margules_2p_referencia(x1, A, B, R, T)
        if abs(ln_g1_calc - ln_g1_ref) >= tolerancia or abs(ln_g2_calc - ln_g2_ref) >= tolerancia:
            todas_ok = False
            print(f"  FALHA em x1={x1}: diferença acima da tolerância.")

    if todas_ok:
        print(f"OK: todas as diferenças estão abaixo de {tolerancia}.")
    else:
        print("FALHA: uma ou mais diferenças excederam a tolerância.")
