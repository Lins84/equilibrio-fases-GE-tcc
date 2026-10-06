"""
Caso de teste de validação para wilson_params_from_ipdb e
buscar_parametros_banco (calculos/gemini.py) — item 2 de "Próximos
passos" do CLAUDE.md: expor busca de parâmetros reais no banco
IPDB/ChemSep para NRTL e Wilson, como opção ao lado do valor manual.

nrtl_params_from_ipdb já tinha esse cuidado (evitar o zero silencioso do
IPDB para pares ausentes); este teste cobre o par novo (Wilson) e o
adaptador comum buscar_parametros_banco.

Referência para Wilson: exemplo da própria docstring de thermo.wilson.Wilson
(etanol/água a 70 °C, x1=0.252) — gammas esperados [1.957, 1.160].
"""

import numpy as np
from thermo import UNIQUAC

from calculos.gemini import (
    buscar_parametros_banco,
    model_uniquac,
    model_wilson,
    uniquac_params_from_ipdb,
)

TOLERANCIA_ABSOLUTA = 0.001


def main():
    todos_ok = True

    T_K = 273.15 + 70.0
    params = buscar_parametros_banco("Wilson", "ethanol", "water", T_K)
    g1, g2 = model_wilson(0.252, params)
    g1_ref, g2_ref = 1.957, 1.160
    ok = abs(g1 - g1_ref) < TOLERANCIA_ABSOLUTA and abs(g2 - g2_ref) < TOLERANCIA_ABSOLUTA
    print(f"  [Wilson via banco] gamma1={g1:.4f} (ref {g1_ref}), gamma2={g2:.4f} (ref {g2_ref}) -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok

    # NRTL via buscar_parametros_banco continua funcionando (mesmo adaptador
    # de nomes -> CAS usado para Wilson).
    params_nrtl = buscar_parametros_banco("NRTL", "1,4-dioxane", "methanol", T_K)
    ok = all(chave in params_nrtl for chave in ("tau12", "tau21", "alpha12"))
    print(f"  [NRTL via banco] chaves esperadas presentes -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok

    # UNIQUAC via banco (adicionado em 2026-10-06, depois de um bug de sinal em
    # uniquac_params_from_ipdb: o app dava gamma < 1 para etanol/agua).
    # Referencia: Exemplo 3 da docstring de thermo.uniquac.UNIQUAC (etanol/agua,
    # 70 C, x1=0.252, r/q do UNIQUAC original) -> [1.977454, 1.139770]; e a
    # classe UNIQUAC do thermo em toda a faixa de x1 com os mesmos r/q.
    T_K_uq = 343.15
    cas = ["64-17-5", "7732-18-5"]
    ip = uniquac_params_from_ipdb(*cas)
    params_uq = {**ip, "r1": 2.11, "q1": 1.97, "r2": 0.92, "q2": 1.4, "T_K": T_K_uq}
    from thermo.interaction_parameters import IPDB
    tau_bs = IPDB.get_ip_asymmetric_matrix("ChemSep UNIQUAC", cas, "bij")
    g1, g2 = model_uniquac(0.252, params_uq)
    g1_ref, g2_ref = 1.977454, 1.139770
    ok = abs(g1 - g1_ref) < TOLERANCIA_ABSOLUTA and abs(g2 - g2_ref) < TOLERANCIA_ABSOLUTA
    print(f"  [UNIQUAC via banco] gamma1={g1:.4f} (ref {g1_ref}), gamma2={g2:.4f} (ref {g2_ref}) -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok

    erro_max = 0.0
    for x1 in np.linspace(0.0, 1.0, 101):
        if x1 in (0.0, 1.0):
            continue  # a classe do thermo nao aceita x exato 0/1 sem tratamento
        ref = UNIQUAC(T=T_K_uq, xs=[x1, 1 - x1], rs=[2.11, 0.92], qs=[1.97, 1.4], tau_bs=tau_bs).gammas()
        g = model_uniquac(x1, params_uq)
        erro_max = max(erro_max, abs(g[0] - ref[0]), abs(g[1] - ref[1]))
    ok = erro_max < 1e-9
    print(f"  [UNIQUAC via banco] erro maximo contra thermo.UNIQUAC em x1 de 0.01 a 0.99 = {erro_max:.2e} -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok

    # Casos de erro esperados.
    try:
        buscar_parametros_banco("Van Laar", "ethanol", "water", T_K)
        print("  [erro esperado] FALHA: Van Laar não tem tabela no IPDB, deveria rejeitar")
        todos_ok = False
    except ValueError:
        print("  [erro esperado] OK: modelo sem tabela no IPDB é rejeitado")

    try:
        buscar_parametros_banco("Wilson", "helium", "xenon", T_K)
        print("  [erro esperado] FALHA: par ausente na tabela, deveria rejeitar")
        todos_ok = False
    except ValueError:
        print("  [erro esperado] OK: par ausente na tabela Wilson é rejeitado")

    print()
    if todos_ok:
        print("OK: busca de parâmetros no banco IPDB validada (Wilson, NRTL e UNIQUAC).")
    else:
        print("FALHA: um ou mais casos não passaram — ver detalhes acima.")


if __name__ == "__main__":
    main()
