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

