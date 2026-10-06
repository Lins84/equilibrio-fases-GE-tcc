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
    montar_parametros_automaticos,
    uniquac_params_from_ipdb,
    uniquac_rq_from_chemsep,
)
import calculos.gemini as gemini

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

    # r/q do ChemSep (2026-10-06): etanol/agua devem sair com os valores
    # originais do UNIQUAC e reproduzir de ponta a ponta (montar_parametros_
    # automaticos -> model_uniquac) a referencia do thermo.
    ok = uniquac_rq_from_chemsep("64-17-5") == (2.11, 1.97) and uniquac_rq_from_chemsep("7732-18-5") == (0.92, 1.4)
    print(f"  [r/q ChemSep] etanol (2.11, 1.97) e agua (0.92, 1.4) -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok

    auto = montar_parametros_automaticos("UNIQUAC", "ethanol", "water")
    g1, g2 = model_uniquac(0.252, {**auto, "T_K": T_K_uq})
    ok = abs(g1 - g1_ref) < TOLERANCIA_ABSOLUTA and abs(g2 - g2_ref) < TOLERANCIA_ABSOLUTA
    print(f"  [UNIQUAC automatico] gamma1={g1:.4f} (ref {g1_ref}), gamma2={g2:.4f} (ref {g2_ref}) -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok

    # Sem r/q no ChemSep, cai para os grupos UNIFAC nos dois componentes.
    original = gemini.uniquac_rq_from_chemsep
    gemini.uniquac_rq_from_chemsep = lambda cas: None
    try:
        sem = montar_parametros_automaticos("UNIQUAC", "ethanol", "water")
    finally:
        gemini.uniquac_rq_from_chemsep = original
    ok = abs(sem["r1"] - 2.5755) < 1e-9 and abs(sem["q1"] - 2.588) < 1e-9
    print(f"  [UNIQUAC sem r/q ChemSep] volta para grupos UNIFAC (r1={sem['r1']}) -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok

    # Arquivo do ChemSep ausente (ex.: versao futura do chemicals que o mova):
    # o UNIQUAC nao pode quebrar, deve cair nos grupos UNIFAC.
    original_caminho = gemini._caminho_xml_chemsep
    gemini._caminho_xml_chemsep = lambda: "/caminho/que/nao/existe.xml"
    gemini._tabela_rq_chemsep.cache_clear()
    try:
        ausente = montar_parametros_automaticos("UNIQUAC", "ethanol", "water")
        ok = abs(ausente["r1"] - 2.5755) < 1e-9
    except Exception as exc:
        ok = False
        print(f"    excecao inesperada: {type(exc).__name__}: {exc}")
    finally:
        gemini._caminho_xml_chemsep = original_caminho
        gemini._tabela_rq_chemsep.cache_clear()
    print(f"  [UNIQUAC com XML ChemSep ausente] cai nos grupos UNIFAC sem quebrar -> {'OK' if ok else 'FALHA'}")
    todos_ok &= ok
    ok = uniquac_rq_from_chemsep("64-17-5") == (2.11, 1.97)
    print(f"  [r/q ChemSep] tabela volta ao normal depois do teste -> {'OK' if ok else 'FALHA'}")
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
