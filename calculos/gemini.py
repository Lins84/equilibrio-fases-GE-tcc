import glob
import hashlib
import os
import warnings
import xml.etree.ElementTree as ET
from functools import lru_cache

import chemicals
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
    (1,2):   86.02,  (2,1):  -35.36,
    (1,3):   61.13,  (3,1):  -11.12,
    (1,4):   76.50,  (4,1):  -69.70,
    (1,5):  986.50,  (5,1):  156.40,
    (1,6):  697.20,  (6,1):   16.51,
    (1,7): 1318.00,  (7,1):  300.00,
    (1,8): 1333.00,  (8,1):  275.80,
    (1,9):  476.40,  (9,1):   26.76,
    (1,10): 677.00,  (10,1): 505.70,
    (1,11): 232.10,  (11,1): 114.80,
    (1,12): 507.00,  (12,1): 329.30,
    (1,13): 251.50,  (13,1):  83.36,
    (2,3):   38.81,  (3,2):    3.446,
    (2,5):  524.10,  (5,2):  457.00,
    (2,6):  787.60,  (6,2):  -12.52,
    (2,7):  270.60,  (7,2):  496.10,
    (2,9):  182.60,  (9,2):   42.92,
    (3,5):  636.10,  (5,3):   89.60,
    (3,6):  637.35,  (6,3):  -50.00,
    (3,7):  903.80,  (7,3):  362.30,
    (4,5):  803.20,  (5,4):   25.82,
    (5,6): -137.10,  (6,5):  249.10,
    (5,7):  353.50,  (7,5): -229.10,
    (5,8): -259.70,  (8,5): -451.60,
    (5,9):   84.00,  (9,5):  164.50,
    (5,10): -203.60, (10,5): 529.00,
    (5,11): 101.10,  (11,5): 245.40,
    (5,13):  28.06,  (13,5): 237.70,
    (6,7): -180.95,  (7,6):  289.60,
    (7,9): -195.40,  (9,7):  472.50,
    (7,13): 540.50,  (13,7): -314.70,
    (9,11): -213.70, (11,9): 372.20,
    (9,13): -103.60, (13,9): 191.10,
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
        return (np.log(Phii / xi) + z / 2 * qi_ * np.log(thi / Phii)
                + li_ - Phii / xi * (x1 * l1 + x2 * l2))

    if x1 == 0:
        # Limite x1->0 (componente 2 puro): Phi1/x1 -> r1/r2 evita a
        # indeterminação 0/0 que ocorreria calculando lnγC diretamente.
        lnγ1_C = np.log(r1 / r2) + z / 2 * q1 * np.log(q1 * r2 / (q2 * r1)) + l1 - (r1 / r2) * l2
        lnγ2_C = 0.0
    elif x2 == 0:
        lnγ1_C = 0.0
        lnγ2_C = np.log(r2 / r1) + z / 2 * q2 * np.log(q2 * r1 / (q1 * r2)) + l2 - (r2 / r1) * l1
    else:
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
                Theta[m] * tau(m, k) / sum(Theta[n] * tau(m, n) for n in all_subs)
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

def model_nrtl(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando NRTL.

    Parâmetros esperados em params:
        tau12, tau21 : parâmetros de interação adimensionais (τij = bij / T_K)
        alpha12      : parâmetro de não-aleatoriedade (α12 = α21 no NRTL clássico)
    """
    tau12, tau21 = params['tau12'], params['tau21']
    alpha12 = params['alpha12']
    x2 = 1 - x1

    G12 = np.exp(-alpha12 * tau12)
    G21 = np.exp(-alpha12 * tau21)

    denom1 = x1 + x2 * G21
    denom2 = x2 + x1 * G12

    lngamma1 = x2**2 * (tau21 * (G21 / denom1)**2 + tau12 * G12 / denom2**2)
    lngamma2 = x1**2 * (tau12 * (G12 / denom2)**2 + tau21 * G21 / denom1**2)
    return np.exp(lngamma1), np.exp(lngamma2)


def nrtl_params_from_ipdb(cas1, cas2, T_K):
    """Busca bij/αij na tabela 'ChemSep NRTL' do thermo.interaction_parameters.IPDB
    e retorna os parâmetros já prontos para model_nrtl (τij = bij / T_K).

    Levanta ValueError se o par não tiver dado nessa tabela — sem essa
    checagem, o IPDB devolve silenciosamente bij/αij = 0 para pares
    ausentes (nenhuma exceção), o que produziria uma curva de aparência
    plausível mas sem nenhum parâmetro real por trás."""
    from thermo.interaction_parameters import IPDB

    if not IPDB.has_ip_specific('ChemSep NRTL', [cas1, cas2], 'bij'):
        raise ValueError(
            f"par ({cas1}, {cas2}) sem parâmetros NRTL na tabela ChemSep do IPDB"
        )

    bij = IPDB.get_ip_asymmetric_matrix('ChemSep NRTL', [cas1, cas2], 'bij')
    alphaij = IPDB.get_ip_asymmetric_matrix('ChemSep NRTL', [cas1, cas2], 'alphaij')

    return {
        'tau12': bij[0][1] / T_K,
        'tau21': bij[1][0] / T_K,
        'alpha12': alphaij[0][1],
    }


def wilson_params_from_ipdb(cas1, cas2, T_K):
    """Busca aij/bij na tabela 'ChemSep Wilson' do IPDB e retorna Λ12/Λ21
    prontos para model_wilson. Nessa tabela, ln(Λij) = aij + bij/T_K
    diretamente (o termo aij já embute ln(Vj/Vi); ver docstring de
    thermo.wilson.Wilson) — sem precisar buscar volume molar à parte.
    Mesmo cuidado de nrtl_params_from_ipdb: levanta ValueError se o par
    não tiver dado nessa tabela, em vez de deixar o IPDB devolver 0
    silenciosamente."""
    from thermo.interaction_parameters import IPDB

    if not IPDB.has_ip_specific('ChemSep Wilson', [cas1, cas2], 'bij'):
        raise ValueError(
            f"par ({cas1}, {cas2}) sem parâmetros Wilson na tabela ChemSep do IPDB"
        )

    aij = IPDB.get_ip_asymmetric_matrix('ChemSep Wilson', [cas1, cas2], 'aij')
    bij = IPDB.get_ip_asymmetric_matrix('ChemSep Wilson', [cas1, cas2], 'bij')

    return {
        'L12': np.exp(aij[0][1] + bij[0][1] / T_K),
        'L21': np.exp(aij[1][0] + bij[1][0] / T_K),
    }


# Modelos com tabela de parâmetros de interação binária real no IPDB/ChemSep
# (item 2 de "Próximos passos" do CLAUDE.md — dar ao usuário a opção de
# buscar em vez de digitar manualmente). Margules e Van Laar ficam de fora:
# não há tabela deles no IPDB (Van Laar é modelo antigo, pouco usado em
# bancos modernos; Margules nem chega a ser um modelo de banco de dados).
MODELOS_COM_BANCO_IPDB = {"NRTL", "Wilson"}


def buscar_parametros_banco(model_name, component1_id, component2_id, T_K):
    """Resolve os componentes (nome/sinônimo/CAS) para CAS via thermo.Chemical
    e busca os parâmetros de interação binária real no banco IPDB/ChemSep,
    para os modelos que têm tabela lá (MODELOS_COM_BANCO_IPDB). Levanta
    ValueError para modelo sem tabela no IPDB, ou par ausente na tabela do
    modelo pedido (repassado de nrtl_params_from_ipdb/wilson_params_from_ipdb)."""
    if model_name not in MODELOS_COM_BANCO_IPDB:
        raise ValueError(f"modelo '{model_name}' não tem tabela de parâmetros no banco IPDB")

    cas1 = Chemical(component1_id).CAS
    cas2 = Chemical(component2_id).CAS

    if model_name == "NRTL":
        return nrtl_params_from_ipdb(cas1, cas2, T_K)
    return wilson_params_from_ipdb(cas1, cas2, T_K)


def unifac_groups_from_name(component_id):
    """Resolve um componente (nome/sinônimo/CAS) para seus grupos UNIFAC
    clássicos ({subgrupo: nº de ocorrências}), via thermo (banco de
    fragmentação DDBST). Levanta ValueError se a fragmentação não estiver
    disponível nesse banco, ou se usar algum subgrupo fora da tabela
    UNIFAC_SUBGROUPS implementada neste projeto (cobertura parcial — ver
    seção 2.7 do mapeamento)."""
    from thermo.unifac import UNIFAC_group_assignment_DDBST

    cas = Chemical(component_id).CAS
    grupos = UNIFAC_group_assignment_DDBST(cas, 'UNIFAC')
    if not grupos:
        raise ValueError(
            f"fragmentação UNIFAC não disponível para '{component_id}' (CAS {cas})"
        )

    faltando = sorted(k for k in grupos if k not in UNIFAC_SUBGROUPS)
    if faltando:
        raise ValueError(
            f"'{component_id}' usa subgrupo(s) UNIFAC fora da tabela "
            f"implementada neste projeto: {faltando}"
        )
    return grupos


def uniquac_rq_from_groups(groups):
    """Soma R/Q dos subgrupos UNIFAC (mesma tabela UNIFAC_SUBGROUPS) para
    obter os parâmetros estruturais r, q de um componente para o UNIQUAC —
    a decomposição em grupos é a mesma usada no UNIFAC (Abrams/Prausnitz:
    r_i = Σ ν_k·R_k, q_i = Σ ν_k·Q_k)."""
    r = sum(nu * UNIFAC_SUBGROUPS[k][1] for k, nu in groups.items())
    q = sum(nu * UNIFAC_SUBGROUPS[k][2] for k, nu in groups.items())
    return r, q


def _caminho_xml_chemsep():
    """Caminho do XML de compostos puros do ChemSep dentro do pacote
    `chemicals`, ou None se não houver. Procura por padrão de nome
    (`Misc/ChemSep*.xml`, o mais recente por ordem alfabética) em vez de fixar
    `ChemSep8.32.xml`, porque o número da versão do ChemSep está no nome do
    arquivo e muda se o pacote for atualizado."""
    candidatos = sorted(glob.glob(os.path.join(os.path.dirname(chemicals.__file__), "Misc", "ChemSep*.xml")))
    return candidatos[-1] if candidatos else None


# Alerta de atualização do XML interno do ChemSep (2026-10-07, pedido do
# autor). O UNIQUAC usa r/q desse XML, que é dado empacotado no `chemicals`
# (não é interface dele): uma atualização do pacote pode renomeá-lo, movê-lo ou
# mudar valores sem aviso. Estes são os valores com que o UNIQUAC foi validado
# (testes/teste_banco_ipdb.py contra `thermo.UNIQUAC`). Se algum diferir,
# `verificar_xml_chemsep` devolve o alerta, `_tabela_rq_chemsep` o emite como
# `RuntimeWarning` ao carregar o arquivo e `testes/teste_xml_chemsep.py` falha.
# Depois de revalidar o UNIQUAC com o pacote novo, atualize as três constantes.
CHEMICALS_VERSAO_VALIDADA = "1.5.2"
CHEMSEP_XML_NOME_VALIDADO = "ChemSep8.32.xml"
CHEMSEP_XML_SHA256_VALIDADO = "78b3e0c6408ff35f3b75fb71a1fdd70bb8e967d8996b49452a4a9fa2dd567c76"


def verificar_xml_chemsep():
    """Lista de alertas (texto) se o `chemicals` ou o XML do ChemSep não forem
    os validados para o UNIQUAC; lista vazia se tudo bate."""
    alertas = []
    if chemicals.__version__ != CHEMICALS_VERSAO_VALIDADA:
        alertas.append(
            f"a versão do pacote `chemicals` mudou ({CHEMICALS_VERSAO_VALIDADA} validada, "
            f"{chemicals.__version__} instalada); ela pode ter alterado o XML do ChemSep"
        )
    caminho = _caminho_xml_chemsep()
    if caminho is None:
        alertas.append(
            "o XML do ChemSep não foi encontrado no `chemicals`; o UNIQUAC usará os r/q dos grupos UNIFAC"
        )
        return alertas
    if os.path.basename(caminho) != CHEMSEP_XML_NOME_VALIDADO:
        alertas.append(
            f"o XML do ChemSep mudou de nome ({CHEMSEP_XML_NOME_VALIDADO} validado, "
            f"{os.path.basename(caminho)} encontrado)"
        )
    try:
        with open(caminho, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        alertas.append("o XML do ChemSep não pôde ser lido para conferência")
    else:
        if sha != CHEMSEP_XML_SHA256_VALIDADO:
            alertas.append("o conteúdo do XML do ChemSep mudou em relação ao validado (r/q podem ter mudado)")
    return alertas


@lru_cache(maxsize=1)
def _tabela_rq_chemsep():
    """Lê UMA vez o banco de compostos puros do ChemSep que acompanha o pacote
    `chemicals` (Misc/ChemSep*.xml, licença Artistic 2.0) e devolve
    {CAS: (r, q)} do UNIQUAC — 429 dos 431 compostos têm os dois valores.

    Arquivo ausente ou ilegível (ex.: uma versão futura do `chemicals` que o
    mova ou remova — ele não é usado pelo código do pacote, só empacotado)
    devolve tabela vazia: `montar_parametros_automaticos` então cai nos grupos
    UNIFAC, em vez de o UNIQUAC inteiro falhar."""
    # Alerta (uma vez, por causa do cache): o XML é dado interno do `chemicals`.
    for alerta in verificar_xml_chemsep():
        warnings.warn(
            f"UNIQUAC: {alerta}. Revalidar o UNIQUAC (testes/teste_banco_ipdb.py) e, se estiver "
            "correto, atualizar as constantes *_VALIDADO em calculos/gemini.py.",
            RuntimeWarning,
            stacklevel=2,
        )
    caminho = _caminho_xml_chemsep()
    if caminho is None:
        return {}
    tabela = {}
    try:
        raiz = ET.parse(caminho).getroot()
    except (OSError, ET.ParseError):
        return {}
    for composto in raiz.iter("compound"):
        cas = composto.find("CAS")
        r = composto.find("UniquacR")
        q = composto.find("UniquacQ")
        if cas is not None and r is not None and q is not None:
            try:
                tabela[cas.get("value")] = (float(r.get("value")), float(q.get("value")))
            except (TypeError, ValueError):
                continue
    return tabela


def uniquac_rq_from_chemsep(cas):
    """(r, q) do UNIQUAC para o composto de CAS dado, no banco do ChemSep, ou
    None se ele não constar ali. São os r/q com que os parâmetros de interação
    da tabela 'ChemSep UNIQUAC' do IPDB foram ajustados — usá-los junto com
    esses parâmetros é o par consistente (ex.: etanol 2,11/1,97; água
    0,92/1,40; os do UNIFAC dão 2,5755/2,588 para o etanol)."""
    return _tabela_rq_chemsep().get(cas)


def uniquac_params_from_ipdb(cas1, cas2):
    """Busca bij (K) na tabela 'ChemSep UNIQUAC' do IPDB e retorna os
    parâmetros de interação a12/a21 prontos para model_uniquac (r1/q1/r2/q2
    vêm de uniquac_rq_from_chemsep ou, na falta, de uniquac_rq_from_groups; T_K é injetado por
    calculate_vle_isothermal). Levanta ValueError se o par não tiver dado
    nessa tabela (mesmo cuidado de nrtl_params_from_ipdb — o IPDB não
    avisa sozinho)."""
    from thermo.interaction_parameters import IPDB

    if not IPDB.has_ip_specific('ChemSep UNIQUAC', [cas1, cas2], 'bij'):
        raise ValueError(
            f"par ({cas1}, {cas2}) sem parâmetros UNIQUAC na tabela ChemSep do IPDB"
        )

    # Sinal (corrigido em 2026-10-06): o IPDB guarda bij = -A_ij/R e o `thermo`
    # usa tau = exp(+bij/T) (ver o Exemplo 3 da docstring de
    # `thermo.uniquac.UNIQUAC`). O `model_uniquac` usa a convenção clássica
    # tau = exp(-a/T); logo a = -bij. Passar `bij` direto como `a` invertia o
    # sinal de tau e o UNIQUAC saía com γ < 1 (ln γ negativo) para o par
    # etanol/água, que tem desvio positivo forte da idealidade.
    bij = IPDB.get_ip_asymmetric_matrix('ChemSep UNIQUAC', [cas1, cas2], 'bij')
    return {'a12': -bij[0][1], 'a21': -bij[1][0]}


def _uniquac_rq_do_par(component1_id, component2_id):
    """((r1, q1), (r2, q2), fonte) do UNIQUAC para o par. `fonte` é "chemsep"
    ou "unifac".

    r/q do ChemSep (2026-10-06, decisão do autor), quando os DOIS componentes
    constam lá — são os r/q com que os a12/a21 do banco foram ajustados.
    Senão, cai para os grupos UNIFAC (decisão de 2026-09-27), nos dois, para
    não misturar fontes dentro do par."""
    rq1 = uniquac_rq_from_chemsep(Chemical(component1_id).CAS)
    rq2 = uniquac_rq_from_chemsep(Chemical(component2_id).CAS)
    if rq1 is not None and rq2 is not None:
        return rq1, rq2, "chemsep"
    return (
        uniquac_rq_from_groups(unifac_groups_from_name(component1_id)),
        uniquac_rq_from_groups(unifac_groups_from_name(component2_id)),
        "unifac",
    )


def uniquac_fonte_rq(component1_id, component2_id):
    """De onde vêm os r/q do UNIQUAC para este par: "chemsep" ou "unifac".
    Usada pela UI para o selo de origem dizer a fonte que de fato valeu."""
    return _uniquac_rq_do_par(component1_id, component2_id)[2]


def montar_parametros_automaticos(model_name, component1_id, component2_id):
    """Resolve automaticamente os parâmetros de um modelo Gᴱ a partir dos
    componentes escolhidos, para os modelos cuja origem hoje é banco de
    dados/preditiva (seção 2.8 do mapeamento) — sem entrada manual na UI:

    - UNIFAC: grupos de cada componente (preditivo, sem IPDB).
    - UNIQUAC: r/q do ChemSep (ou, se faltar, via grupos UNIFAC) + a12/a21 via IPDB.

    Não cobre Margules/Van Laar/Wilson/NRTL — esses seguem com parâmetro
    fornecido manualmente (sliders) na UI. Levanta ValueError com mensagem
    clara quando a fonte não cobre o componente/par pedido."""
    if model_name == "UNIFAC":
        return {
            "groups1": unifac_groups_from_name(component1_id),
            "groups2": unifac_groups_from_name(component2_id),
        }

    if model_name == "UNIQUAC":
        (r1, q1), (r2, q2), _ = _uniquac_rq_do_par(component1_id, component2_id)
        cas1 = Chemical(component1_id).CAS
        cas2 = Chemical(component2_id).CAS
        return {
            "r1": r1, "q1": q1, "r2": r2, "q2": q2,
            **uniquac_params_from_ipdb(cas1, cas2),
        }

    raise ValueError(f"modelo '{model_name}' não tem resolução automática de parâmetros")


def model_wilson(x1, params):
    """Calcula os coeficientes de atividade (gamma) usando Wilson."""
    L12, L21 = params['L12'], params['L21']
    x2 = 1 - x1

    if x1 == 0:
        return np.exp(1 - L21 - np.log(L12)), 1.0
    if x2 == 0:
        return 1.0, np.exp(1 - L12 - np.log(L21))

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
    "NRTL": model_nrtl,
    "UNIQUAC": model_uniquac,
    "UNIFAC": model_unifac,
}

# --- Calculadora Principal de Equilíbrio ---

def calculate_vle_isothermal(component1_id, component2_id, T_C, model_name, model_params, x1_values=None):
    """
    Calcula os diagramas Pxy e yx para um sistema binário a uma dada temperatura.

    Args:
        component1_id (str): ID do componente 1 (ex: 'ethanol').
        component2_id (str): ID do componente 2 (ex: 'water').
        T_C (float): Temperatura em Celsius.
        model_name (str): O nome do modelo Gᴱ a ser usado (chave do dicionário MODELS_GE).
        model_params (dict): Um dicionário com os parâmetros do modelo (ex: {'A': 1.6}).
        x1_values (list[float], opcional): composições de líquido específicas
            a calcular, em vez da malha genérica de 101 pontos — usado pela
            comparação calculado-vs-experimental (item 4 do roadmap), que
            precisa do modelo avaliado exatamente nos x1 digitados na
            tabela, não numa malha que não coincide com eles.

    Returns:
        dict: Um dicionário com as listas de resultados: 'P_kPa', 'x1', 'y1',
            'gamma1', 'gamma2' (coeficientes de atividade, mesma malha de x1).
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
    x1_array = np.linspace(0, 1, 101) if x1_values is None else np.array(x1_values)

    P_list_Pa = []
    y1_list = []
    gamma1_list = []
    gamma2_list = []

    params_com_T = {**model_params, 'T_K': T_K}

    for x1 in x1_array:
        # 1. Calcular os coeficientes de atividade para a composição x1
        gamma1, gamma2 = model_function(x1, params_com_T)
        gamma1_list.append(gamma1)
        gamma2_list.append(gamma2)

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
        'y1': [float(y) for y in y1_list],
        'gamma1': [float(g) for g in gamma1_list],
        'gamma2': [float(g) for g in gamma2_list],
    }


# --- Regressão de parâmetros — método de Barker (direto) ---
# Decisão de 2026-09-13 (seção 2.8 do mapeamento): quando não há parâmetro
# fornecido pelo usuário nem em banco de dados, o modelo é ajustado por
# regressão não-linear contra o resíduo de P e y diretamente (não contra
# γ "experimental" invertido da Lei de Raoult — método indireto, descartado).
# Não se aplica ao UNIFAC (preditivo, sem parâmetro ajustável por par).

# Para cada modelo: parâmetros livres (ajustados pela regressão, nessa
# ordem), chute inicial, limites (min, max) por parâmetro, e quais chaves
# extra têm que vir prontas em params_fixos (não são ajustadas):
# - NRTL: alpha12 fixado por convenção (mau-condicionamento com 3
#   parâmetros e poucos pontos — mesma decisão do α12 fixo).
# - UNIQUAC: r1/q1/r2/q2 são estruturais (vêm do banco ChemSep via
#   uniquac_rq_from_chemsep ou, na falta, dos grupos UNIFAC da molécula via
#   uniquac_rq_from_groups; não são ajustáveis por regressão).
REGRESSAO_MODELOS = {
    "Margules (1-P)": {
        "livres": ["A"],
        "chute_inicial": [0.5],
        "limites": ([-5.0], [5.0]),
        "params_fixos_obrigatorios": [],
    },
    "Margules (2-P)": {
        "livres": ["A12", "A21"],
        "chute_inicial": [0.5, 0.3],
        "limites": ([-5.0, -5.0], [5.0, 5.0]),
        "params_fixos_obrigatorios": [],
    },
    "Van Laar": {
        "livres": ["A12", "A21"],
        "chute_inicial": [0.5, 0.3],
        # O Van Laar é singular quando A12 e A21 têm sinais opostos (denominador
        # A12·x1 + A21·x2 passa por zero), então só tem solução com A12·A21 > 0.
        # Do chute positivo, desvio NEGATIVO (A < 0) não converge: parte-se
        # também de um chute negativo e fica o de menor resíduo (2026-10-06).
        "chutes_extras": [[-0.5, -0.3]],
        "limites": ([-5.0, -5.0], [5.0, 5.0]),
        "params_fixos_obrigatorios": [],
    },
    "Wilson": {
        "livres": ["L12", "L21"],
        "chute_inicial": [0.8, 0.6],
        "limites": ([1e-4, 1e-4], [10.0, 10.0]),
        "params_fixos_obrigatorios": [],
    },
    "NRTL": {
        "livres": ["tau12", "tau21"],
        "chute_inicial": [0.3, 0.3],
        "limites": ([-5.0, -5.0], [5.0, 5.0]),
        "params_fixos_obrigatorios": ["alpha12"],
    },
    "UNIQUAC": {
        "livres": ["a12", "a21"],
        "chute_inicial": [0.0, 0.0],
        "limites": ([-3000.0, -3000.0], [3000.0, 3000.0]),
        "params_fixos_obrigatorios": ["r1", "q1", "r2", "q2"],
    },
}


def regress_params_barker(
    model_name, component1_id, component2_id, T_C, pontos, params_fixos=None,
):
    """Ajusta os parâmetros livres de um modelo Gᴱ pelo método de Barker
    (direto): minimiza o resíduo de P e y calculados contra os pontos
    experimentais (P, x1, y1) digitados, via mínimos quadrados não-lineares
    (scipy.optimize.least_squares) — sem inverter a Lei de Raoult para
    obter γ "experimental" (método indireto, descartado na seção 2.8 do
    mapeamento).

    Args:
        model_name: chave de MODELS_GE/REGRESSAO_MODELOS.
        component1_id, component2_id: nome/sinônimo/CAS dos componentes
            (para obter Psat via thermo.Chemical, igual a
            calculate_vle_isothermal).
        T_C: temperatura do sistema em Celsius.
        pontos: lista de tuplas (P_kPa, x1, y1) experimentais.
        params_fixos: dict com os parâmetros que NÃO entram no ajuste
            (ex.: {'alpha12': 0.3} para NRTL; {'r1':..., 'q1':..., 'r2':...,
            'q2':...} para UNIQUAC — ver params_fixos_obrigatorios em
            REGRESSAO_MODELOS). Obrigatório quando o modelo exigir.

    Returns:
        dict: {
            'params': dict completo (livres ajustados + fixos, pronto para
                calculate_vle_isothermal),
            'n_pontos': nº de pontos usados,
            'graus_liberdade': n_pontos - nº de parâmetros livres,
            'residual_rms': raiz do erro quadrático médio do resíduo
                combinado (ΔP relativo e Δy absoluto, adimensional),
            'sucesso': bool — se o otimizador convergiu.
        }

    Levanta ValueError se o modelo não tiver regressão implementada
    (UNIFAC — preditivo, seção 2.7), se faltar algum params_fixos
    obrigatório, ou se houver menos pontos que o mínimo exigido (nº de
    parâmetros livres + 1 — seção 2.8: abaixo disso a regressão não tem
    grau de liberdade nenhum)."""
    from scipy.optimize import least_squares

    spec = REGRESSAO_MODELOS.get(model_name)
    if not spec:
        raise ValueError(
            f"modelo '{model_name}' não tem regressão de parâmetros implementada"
        )

    minimo_pontos = len(spec["livres"]) + 1
    if len(pontos) < minimo_pontos:
        raise ValueError(
            f"mínimo de {minimo_pontos} ponto(s) para regredir {model_name} "
            f"({len(spec['livres'])} parâmetro(s) livre(s) + 1) — foram "
            f"digitados {len(pontos)}"
        )

    params_fixos = dict(params_fixos or {})
    faltando = [k for k in spec["params_fixos_obrigatorios"] if k not in params_fixos]
    if faltando:
        raise ValueError(
            f"modelo '{model_name}' exige em params_fixos: {faltando}"
        )

    T_K = T_C + 273.15
    comp1 = Chemical(component1_id, T=T_K)
    comp2 = Chemical(component2_id, T=T_K)
    P1_sat_Pa = comp1.Psat
    P2_sat_Pa = comp2.Psat

    model_function = MODELS_GE[model_name]
    nomes_livres = spec["livres"]

    P_exp = np.array([p for p, x, y in pontos], dtype=float) * 1000.0  # kPa -> Pa
    x1_exp = np.array([x for p, x, y in pontos], dtype=float)
    y_exp = np.array([y for p, x, y in pontos], dtype=float)

    def calcular_P_y(valores_livres):
        params = {**params_fixos, **dict(zip(nomes_livres, valores_livres)), "T_K": T_K}
        P_calc = np.empty_like(x1_exp)
        y_calc = np.empty_like(x1_exp)
        for i, x1 in enumerate(x1_exp):
            gamma1, gamma2 = model_function(x1, params)
            P = x1 * gamma1 * P1_sat_Pa + (1 - x1) * gamma2 * P2_sat_Pa
            P_calc[i] = P
            y_calc[i] = (x1 * gamma1 * P1_sat_Pa) / P
        return P_calc, y_calc

    def residuos(valores_livres):
        P_calc, y_calc = calcular_P_y(valores_livres)
        # ΔP relativo (adimensional) e Δy absoluto (já em [0,1]) — a mesma
        # escala evita que P (em Pa, ordem de 1e4-1e5) domine o resíduo
        # sozinho frente a y.
        residuo_P = (P_calc - P_exp) / P_exp
        residuo_y = y_calc - y_exp
        return np.concatenate([residuo_P, residuo_y])

    resultado = None
    for chute in [spec["chute_inicial"], *spec.get("chutes_extras", [])]:
        try:
            tentativa = least_squares(residuos, x0=chute, bounds=spec["limites"])
        except ValueError:
            continue  # resíduo não finito já no chute (ex.: singularidade)
        if resultado is None or (tentativa.success, -tentativa.cost) > (
            resultado.success, -resultado.cost
        ):
            resultado = tentativa
    if resultado is None:
        raise ValueError(f"a regressão de {model_name} não convergiu de nenhum chute inicial")

    params_finais = {
        **params_fixos,
        **dict(zip(nomes_livres, resultado.x)),
    }

    return {
        "params": params_finais,
        "n_pontos": len(pontos),
        "graus_liberdade": len(pontos) - len(nomes_livres),
        "residual_rms": float(np.sqrt(np.mean(resultado.fun**2))),
        "sucesso": bool(resultado.success),
    }

