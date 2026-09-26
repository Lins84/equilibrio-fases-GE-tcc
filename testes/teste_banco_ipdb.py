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

from calculos.gemini import buscar_parametros_banco, model_wilson

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
        print("OK: busca de parâmetros no banco IPDB validada (Wilson novo, NRTL já existente).")
    else:
        print("FALHA: um ou mais casos não passaram — ver detalhes acima.")


if __name__ == "__main__":
    main()
