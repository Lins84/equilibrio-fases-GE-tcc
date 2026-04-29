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

def model_van_laar(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando Van Laar."""
    A12, A21 = params['A12'], params['A21']
    x2 = 1 - x1

    # Prevenção de divisão por zero nos extremos
    if x1 == 0: return 1.0, np.exp(A21)
    if x2 == 0: return np.exp(A12), 1.0

    lngamma1 = A12 * (A21 * x2 / (A12 * x1 + A21 * x2))**2
    lngamma2 = A21 * (A12 * x1 / (A12 * x1 + A21 * x2))**2
    return np.exp(lngamma1), np.exp(lngamma2)

# Adicione outros modelos (Wilson, NRTL, UNIQUAC) aqui como funções separadas...
# def model_wilson(x1, params): ...

# Dicionário para selecionar o modelo facilmente
MODELS_GE = {
    "Margules (1-P)": model_margules_1p,
    "Van Laar": model_van_laar,
    # "Wilson": model_wilson,
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

    for x1 in x1_array:
        # 1. Calcular os coeficientes de atividade para a composição x1
        gamma1, gamma2 = model_function(x1, model_params)

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

