import numpy as np
from thermo.chemical import Chemical

# --- Modelos de Coeficiente de Atividade (Gᴱ) ---

def model_margules_1p(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando Margules de 1 parâmetro."""
    A = params['A']
    x2 = 1 - x1
    lngamma1 = A * x2**2
    lngamma2 = A * x1**2
    return np.exp(lngamma1), np.exp(lngamma2)

def model_margules_2p(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando Margules de 2 parâmetros."""
    A12, A21 = params['A12'], params['A21']
    x2 = 1 - x1
    lngamma1 = x2**2 * (A12 + 2 * (A21 - A12) * x1)
    lngamma2 = x1**2 * (A21 + 2 * (A12 - A21) * x2)
    return np.exp(lngamma1), np.exp(lngamma2)

def model_van_laar(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando Van Laar."""
    A12, A21 = params['A12'], params['A21']
    x2 = 1 - x1

    # Prevenção de divisão por zero nos extremos
    if x1 == 0: return np.exp(A12), 1.0
    if x2 == 0: return 1.0, np.exp(A21)

    lngamma1 = A12 * (A21 * x2 / (A12 * x1 + A21 * x2))**2
    lngamma2 = A21 * (A12 * x1 / (A12 * x1 + A21 * x2))**2
    return np.exp(lngamma1), np.exp(lngamma2)

def model_uniquac(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando UNIQUAC.

    Parâmetros esperados em params:
        r1, q1  : parâmetros estruturais do componente 1
        r2, q2  : parâmetros estruturais do componente 2
        a12, a21: parâmetros de interação (em K)  →  τij = exp(-aij / T_K)
        T_K     : temperatura em Kelvin (adicionado automaticamente pelo calculador)
    """
    r1, q1 = params['r1'], params['q1']
    r2, q2 = params['r2'], params['q2']
    a12, a21 = params['a12'], params['a21']
    T_K = params['T_K']
    x2 = 1 - x1
    z = 10

    tau12 = np.exp(-a12 / T_K)
    tau21 = np.exp(-a21 / T_K)

    # Frações de segmento (Φ) e de área (θ)
    denom_r = x1 * r1 + x2 * r2
    denom_q = x1 * q1 + x2 * q2
    Phi1 = x1 * r1 / denom_r
    Phi2 = x2 * r2 / denom_r
    th1 = x1 * q1 / denom_q
    th2 = x2 * q2 / denom_q

    l1 = z / 2 * (r1 - q1) - (r1 - 1)
    l2 = z / 2 * (r2 - q2) - (r2 - 1)

    # Parte combinatorial
    def lnγ_C(xi, Phii, thi, li, Phi1_, Phi2_, l1_, l2_, x1_, x2_):
        return (np.log(Phii / xi) + z / 2 * params[f'q{1 if xi==x1_ else 2}'] *
                np.log(thi / Phii) + li - Phii / xi * (x1_ * l1_ + x2_ * l2_))

    if x1 == 0:
        lnγ1_C = np.log(r1 / r2) + 1 - r1 / r2 - z / 2 * q1 * (np.log(r1 * q2 / (r2 * q1)) + 1 - r1 * q2 / (r2 * q1))
        lnγ2_C = 0.0
    elif x2 == 0:
        lnγ1_C = 0.0
        lngamma2_C_val = np.log(r2 / r1) + 1 - r2 / r1 - z / 2 * q2 * (np.log(r2 * q1 / (r1 * q2)) + 1 - r2 * q1 / (r1 * q2))
    else:
        lnγ1_C = (np.log(Phi1 / x1) + z / 2 * q1 * np.log(th1 / Phi1)
                  + l1 - Phi1 / x1 * (x1 * l1 + x2 * l2))
        lnγ2_C = (np.log(Phi2 / x2) + z / 2 * q2 * np.log(th2 / Phi2)
                  + l2 - Phi2 / x2 * (x1 * l1 + x2 * l2))

    # Parte residual
    S1 = th1 + th2 * tau21
    S2 = th2 + th1 * tau12
    lnγ1_R = q1 * (1 - np.log(S1) - th1 / S1 - th2 * tau12 / S2)
    lnγ2_R = q2 * (1 - np.log(S2) - th2 / S2 - th1 * tau21 / S1)

    if x1 == 0:
        return np.exp(lnγ1_C + lnγ1_R), 1.0
    if x2 == 0:
        return 1.0, np.exp(lngamma2_C_val + lnγ2_R)
    return np.exp(lnγ1_C + lnγ1_R), np.exp(lnγ2_C + lnγ2_R)

# ---------------------------------------------------------------------------
# Tabelas UNIFAC (Fredenslund et al., 1977 + revisões Gmehling)
# ---------------------------------------------------------------------------

# Subgrupos: {id: (grupo_principal, R, Q, nome)}
UNIFAC_SUBGROUPS = {
    # Grupo 1 – CH2
    1:  (1, 0.9011, 0.8480, "CH3"),
    2:  (1, 0.6744, 0.5400, "CH2"),
    3:  (1, 0.4469, 0.2280, "CH"),
    4:  (1, 0.2195, 0.0000, "C"),
    # Grupo 2 – C=C
    5:  (2, 1.3454, 1.1760, "CH2=CH"),
    6:  (2, 1.1167, 0.8670, "CH=CH"),
    7:  (2, 1.1173, 0.9880, "CH2=C"),
    8:  (2, 0.8886, 0.6760, "CH=C"),
    # Grupo 3 – ACH (aromático)
    9:  (3, 0.5313, 0.4000, "ACH"),
    10: (3, 0.3652, 0.1200, "AC"),
    # Grupo 4 – ACCH2
    11: (4, 1.2663, 0.9680, "ACCH3"),
    12: (4, 1.0396, 0.6600, "ACCH2"),
    13: (4, 0.8121, 0.3480, "ACCH"),
    # Grupo 5 – OH
    14: (5, 1.0000, 1.2000, "OH"),
    # Grupo 6 – CH3OH
    15: (6, 1.4311, 1.4320, "CH3OH"),
    # Grupo 7 – H2O
    16: (7, 0.9200, 1.4000, "H2O"),
    # Grupo 8 – ACOH
    17: (8, 0.8952, 0.6800, "ACOH"),
    # Grupo 9 – CH2CO
    18: (9, 1.6724, 1.4880, "CH3CO"),
    19: (9, 1.4457, 1.1800, "CH2CO"),
    # Grupo 10 – CHO
    20: (10, 0.9980, 0.9480, "CHO"),
    # Grupo 11 – CCOO (éster)
    21: (11, 1.9031, 1.7280, "CH3COO"),
    22: (11, 1.6764, 1.4200, "CH2COO"),
    # Grupo 12 – HCOO
    23: (12, 1.2420, 1.1880, "HCOO"),
    # Grupo 13 – CH2O (éter)
    24: (13, 1.1450, 1.0880, "CH3O"),
    25: (13, 0.9183, 0.7800, "CH2O"),
    26: (13, 0.6908, 0.4680, "CHO"),
    27: (13, 0.9183, 1.1000, "THF"),
}

# Parâmetros de interação amn entre grupos principais (a_mn ≠ a_nm)
# Formato: {(m, n): amn}  — amn = 0 quando m == n (não necessário guardar)
_A = {
    (1,2):  86.02,  (2,1):  -35.36,
    (1,3):  61.13,  (3,1):  -11.12,
    (1,4):  76.50,  (4,1):  -69.70,
    (1,5): 986.50,  (5,1):  156.40,
    (1,6): 697.20,  (6,1):  300.90,
    (1,7): 1318.0,  (7,1):  -14.09,
    (1,8): 1333.0,  (8,1): -247.00,
    (1,9): 476.40,  (9,1):   26.76,
    (1,10): 677.0,  (10,1):  505.70,
    (1,11): 232.1,  (11,1):  114.80,
    (1,12): 507.0,  (12,1):  529.00,
    (1,13): 251.5,  (13,1):   83.36,
    (2,3):  38.81,  (3,2):  -13.89,
    (2,5): 693.90,  (5,2):  -4.460,
    (2,6): 357.50,  (6,2):  202.50,
    (2,7): 1140.0,  (7,2):  -4.460,
    (2,9): 524.10,  (9,2):   -52.1,
    (3,5): 4000.0,  (5,3): -259.70,
    (3,6): -259.7,  (6,3):  -246.0,
    (3,7):  634.2,  (7,3):  -13.89,
    (4,5): 5695.0,  (5,4): -246.00,
    (5,6):  -40.0,  (6,5):   128.0,
    (5,7):  353.5,  (7,5):  -229.1,
    (5,8):  -64.7,  (8,5):   167.0,
    (5,9):  -195.4, (9,5):  -103.6,
    (5,10): -400.0, (10,5):  -118.1,
    (5,11): 245.4,  (11,5):  -151.0,
    (5,13): 251.5,  (13,5):   28.06,
    (6,7):  -137.1, (7,6):   353.50,
    (7,9):  -195.4, (9,7):   -116.0,
    (7,13): -116.0, (13,7):  -330.4,
    (9,11):  372.2, (11,9):  -213.7,
    (9,13): -103.6, (13,9):  140.80,
}

def _amn(m, n):
    """Retorna o parâmetro de interação amn; 0 se m==n ou não tabelado."""
    if m == n:
        return 0.0
    return _A.get((m, n), 0.0)

def model_unifac(x1, params):
    """Calcula os coeficientes de atividade usando UNIFAC.

    Parâmetros esperados em params:
        groups1: dict {subgroup_id: nu}  — grupos e contagens do componente 1
        groups2: dict {subgroup_id: nu}  — grupos e contagens do componente 2
        T_K    : temperatura em Kelvin (adicionado automaticamente pelo calculador)
    """
    g1 = params['groups1']
    g2 = params['groups2']
    T_K = params['T_K']
    x2 = 1 - x1

    # --- r e q de cada componente ---
    def rq(groups):
        r = sum(nu * UNIFAC_SUBGROUPS[k][1] for k, nu in groups.items())
        q = sum(nu * UNIFAC_SUBGROUPS[k][2] for k, nu in groups.items())
        return r, q

    r1, q1 = rq(g1)
    r2, q2 = rq(g2)

    # --- Parte Combinatorial (Staverman-Guggenheim) ---
    z = 10
    denom_r = x1 * r1 + x2 * r2
    denom_q = x1 * q1 + x2 * q2
    Phi1, Phi2 = x1 * r1 / denom_r, x2 * r2 / denom_r
    th1,  th2  = x1 * q1 / denom_q, x2 * q2 / denom_q
    l1 = z / 2 * (r1 - q1) - (r1 - 1)
    l2 = z / 2 * (r2 - q2) - (r2 - 1)

    def lnγC(xi, Phii, thi, qi_, li_):
        if xi == 0:
            return 0.0
        return (np.log(Phii / xi) + z / 2 * qi_ * np.log(thi / Phii)
                + li_ - Phii / xi * (x1 * l1 + x2 * l2))

    lnγ1_C = lnγC(x1, Phi1, th1, q1, l1)
    lnγ2_C = lnγC(x2, Phi2, th2, q2, l2)

    # --- Parte Residual ---
    # Coletar todos os subgrupos presentes e seus grupos principais
    all_subs = set(g1.keys()) | set(g2.keys())
    main_groups = {k: UNIFAC_SUBGROUPS[k][0] for k in all_subs}
    Qk = {k: UNIFAC_SUBGROUPS[k][2] for k in all_subs}

    def group_activity_coeff(groups_i, x_frac_mixture):
        """Calcula ln(Γk) para uma composição dada (mistura ou puro i)."""
        # Fração molar de grupos na mistura
        total_nu = {}
        for comp_g, xi in x_frac_mixture:
            for k, nu in comp_g.items():
                total_nu[k] = total_nu.get(k, 0) + xi * nu

        sum_nu = sum(total_nu.values())
        X = {k: v / sum_nu for k, v in total_nu.items()}

        # θm por grupo principal (usando Qk médio ponderado por subgrupo)
        sum_XQ = sum(X[k] * Qk[k] for k in all_subs)
        Theta = {k: X[k] * Qk[k] / sum_XQ for k in all_subs}

        # τmk entre grupos principais
        def tau(k_sub, m_sub):
            mk = main_groups[k_sub]
            mm = main_groups[m_sub]
            return np.exp(-_amn(mm, mk) / T_K)

        lnGamma = {}
        for k in all_subs:
            s1 = sum(Theta[m] * tau(k, m) for m in all_subs)
            s2 = sum(
                Theta[m] * tau(m, k) / sum(Theta[n] * tau(n, m) for n in all_subs)
                for m in all_subs
            )
            lnGamma[k] = Qk[k] * (1 - np.log(max(s1, 1e-300)) - s2)
        return lnGamma

    # Γk na mistura
    lnGamma_mix = group_activity_coeff(None, [(g1, x1), (g2, x2)])

    # Γk^(i) no componente puro (xi → 1)
    lnGamma_pure1 = group_activity_coeff(None, [(g1, 1.0), (g2, 0.0)])
    lnGamma_pure2 = group_activity_coeff(None, [(g1, 0.0), (g2, 1.0)])

    def lnγR(groups_i, lnGamma_pure_i):
        return sum(
            nu * (lnGamma_mix[k] - lnGamma_pure_i[k])
            for k, nu in groups_i.items()
        )

    lnγ1_R = lnγR(g1, lnGamma_pure1)
    lnγ2_R = lnγR(g2, lnGamma_pure2)

    return np.exp(lnγ1_C + lnγ1_R), np.exp(lnγ2_C + lnγ2_R)

def model_wilson(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando Wilson."""
    L12, L21 = params['L12'], params['L21']
    x2 = 1 - x1

    if x1 == 0:
        return 1.0, np.exp(1 - L21 - np.log(L21))
    if x2 == 0:
        return np.exp(1 - L12 - np.log(L12)), 1.0

    a = x1 + L12 * x2
    b = x2 + L21 * x1
    lngamma1 = -np.log(a) + x2 * (L12 / a - L21 / b)
    lngamma2 = -np.log(b) - x1 * (L12 / a - L21 / b)
    return np.exp(lngamma1), np.exp(lngamma2)

# Dicionário para selecionar o modelo facilmente
MODELS_GE = {
    "Margules (1-P)": model_margules_1p,
    "Margules (2-P)": model_margules_2p,
    "Van Laar": model_van_laar,
    "Wilson": model_wilson,
    "UNIQUAC": model_uniquac,
    "UNIFAC": model_unifac,
}

# --- Calculadora Principal de Equilíbrio ---

def calculate_vle_isothermal(component1_id, component2_id, T_C, model_name, model_params):
    """
    Calcula os diagramas Pxy e yx para um sistema binário a uma dada temperatura.

    Args:
        component1_id (str): ID do componente 1 (ex: 'ethanol').
        component2_id (str): ID do componente 2 (ex: 'water').
        T_C (float): Temperatura em Celsius.
        model_name (str): O nome do modelo Gᴱ a ser usado (chave do dicionário MODELS_GE).
        model_params (dict): Um dicionário com os parâmetros do modelo (ex: {'A': 1.6}).

    Returns:
        dict: Um dicionário com as listas de resultados: 'P_kPa', 'x1', 'y1'.
    """
    T_K = T_C + 273.15  # Converter para Kelvin

    # Obter objetos Chemical da biblioteca thermo
    comp1 = Chemical(component1_id, T=T_K)
    comp2 = Chemical(component2_id, T=T_K)

    # Pressão de saturação (em Pa) na temperatura do sistema
    P1_sat_Pa = comp1.Psat
    P2_sat_Pa = comp2.Psat

    # Selecionar a função do modelo Gᴱ
    model_function = MODELS_GE.get(model_name)
    if not model_function:
        raise ValueError("Modelo Gᴱ não reconhecido.")

    # Geração dos pontos de composição do líquido
    x1_array = np.linspace(0, 1, 101)

    P_list_Pa = []
    y1_list = []

    params_com_T = {**model_params, 'T_K': T_K}

    for x1 in x1_array:
        # 1. Calcular os coeficientes de atividade para a composição x1
        gamma1, gamma2 = model_function(x1, params_com_T)

        # 2. Calcular a pressão total (Lei de Raoult Modificada)
        P_Pa = x1 * gamma1 * P1_sat_Pa + (1 - x1) * gamma2 * P2_sat_Pa
        P_list_Pa.append(P_Pa)

        # 3. Calcular a composição do vapor
        y1 = (x1 * gamma1 * P1_sat_Pa) / P_Pa
        y1_list.append(y1)

    # Converter para unidades mais convenientes e retornar
    return {
        'P_kPa': [p / 1000 for p in P_list_Pa],
        'x1': [float(x) for x in x1_array], # Converte de numpy.float64 para float
        'y1': [float(y) for y in y1_list]
    }

