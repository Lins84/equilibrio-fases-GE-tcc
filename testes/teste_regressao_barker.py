"""
Caso de teste de validação para regress_params_barker (calculos/gemini.py).

Método: gera dados "experimentais" sintéticos a partir de parâmetros
conhecidos via calculate_vle_isothermal, amostra alguns pontos (P, x1, y1)
dessa curva, e verifica se regress_params_barker recupera os mesmos
parâmetros usados para gerar os dados. Sem ruído nos dados — a regressão
deve recuperar os parâmetros com erro desprezível (validação da mecânica
do ajuste, não de robustez a ruído experimental real).

Cobre os três casos distintos de REGRESSAO_MODELOS: parâmetros livres
simples (Margules 1P), um parâmetro extra fixo por convenção (NRTL,
alpha12) e parâmetros extras fixos vindos de dados estruturais (UNIQUAC,
r/q via grupos UNIFAC).
"""

import numpy as np

from calculos.gemini import (
    calculate_vle_isothermal,
    regress_params_barker,
    unifac_groups_from_name,
    uniquac_rq_from_groups,
)

TOLERANCIA_RELATIVA = 0.01  # 1% de erro relativo, dados sintéticos sem ruído


def amostrar_pontos(component1_id, component2_id, T_C, model_name, params, x1_amostra):
    """Gera a curva completa via calculate_vle_isothermal e extrai os
    pontos (P_kPa, x1, y1) mais próximos dos x1 pedidos em x1_amostra."""
    resultado = calculate_vle_isothermal(component1_id, component2_id, T_C, model_name, params)
    x1_malha = np.array(resultado["x1"])
    pontos = []
    for x1 in x1_amostra:
        idx = int(np.argmin(np.abs(x1_malha - x1)))
        pontos.append((resultado["P_kPa"][idx], resultado["x1"][idx], resultado["y1"][idx]))
    return pontos


def verificar_recuperacao(nome_caso, params_verdadeiros, params_regredidos):
    todos_ok = True
    for chave, valor_certo in params_verdadeiros.items():
        if chave not in params_regredidos:
            continue
        valor_obtido = params_regredidos[chave]
        erro_relativo = abs(valor_obtido - valor_certo) / (abs(valor_certo) + 1e-9)
        status = "OK" if erro_relativo < TOLERANCIA_RELATIVA else "FALHA"
        if status == "FALHA":
            todos_ok = False
        print(f"  [{nome_caso}] {chave}: verdadeiro={valor_certo:.6g} regredido={valor_obtido:.6g} -> {status}")
    return todos_ok


def main():
    todos_ok = True

    # Caso 1: Margules (1-P) — 1 parâmetro livre, sem params_fixos.
    params_verdadeiros = {"A": 0.7}
    pontos = amostrar_pontos("ethanol", "water", 70.0, "Margules (1-P)", params_verdadeiros, [0.1, 0.3, 0.5, 0.7, 0.9])
    resultado = regress_params_barker("Margules (1-P)", "ethanol", "water", 70.0, pontos)
    todos_ok &= verificar_recuperacao("Margules (1-P)", params_verdadeiros, resultado["params"])
    assert resultado["sucesso"], "otimizador não convergiu para Margules (1-P)"

    # Caso 2: NRTL — alpha12 fixado por convenção (não é ajustado).
    params_verdadeiros = {"tau12": 0.3, "tau21": 0.4, "alpha12": 0.3}
    pontos = amostrar_pontos(
        "1,4-dioxane", "methanol", 70.0, "NRTL", params_verdadeiros, [0.1, 0.3, 0.5, 0.7, 0.9]
    )
    resultado = regress_params_barker(
        "NRTL", "1,4-dioxane", "methanol", 70.0, pontos, params_fixos={"alpha12": 0.3}
    )
    todos_ok &= verificar_recuperacao("NRTL", params_verdadeiros, resultado["params"])
    assert resultado["sucesso"], "otimizador não convergiu para NRTL"

    # Caso 3: UNIQUAC — r1/q1/r2/q2 vêm dos grupos UNIFAC (estruturais,
    # fixos), só a12/a21 são ajustados.
    grupos1 = unifac_groups_from_name("1,4-dioxane")
    grupos2 = unifac_groups_from_name("methanol")
    r1, q1 = uniquac_rq_from_groups(grupos1)
    r2, q2 = uniquac_rq_from_groups(grupos2)
    params_verdadeiros = {"a12": -227.0, "a21": 9.6, "r1": r1, "q1": q1, "r2": r2, "q2": q2}
    pontos = amostrar_pontos(
        "1,4-dioxane", "methanol", 70.0, "UNIQUAC", params_verdadeiros, [0.1, 0.3, 0.5, 0.7, 0.9]
    )
    resultado = regress_params_barker(
        "UNIQUAC", "1,4-dioxane", "methanol", 70.0, pontos,
        params_fixos={"r1": r1, "q1": q1, "r2": r2, "q2": q2},
    )
    todos_ok &= verificar_recuperacao("UNIQUAC", params_verdadeiros, resultado["params"])
    assert resultado["sucesso"], "otimizador não convergiu para UNIQUAC"

    # Casos 4-8 (2026-10-06): modelos que não tinham teste de recuperação
    # (Margules 2P, Van Laar, Wilson), com desvio positivo e NEGATIVO da
    # idealidade. O Van Laar com A12, A21 < 0 falhava no chute inicial
    # positivo (convergia para solução espúria, ou ficava no limite).
    x1_amostra = [0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95]
    casos_extra = [
        ("Margules (2-P) +", "Margules (2-P)", {"A12": 1.6, "A21": 0.7}),
        ("Margules (2-P) -", "Margules (2-P)", {"A12": -0.8, "A21": -0.4}),
        ("Van Laar +", "Van Laar", {"A12": 1.7, "A21": 0.8}),
        ("Van Laar -", "Van Laar", {"A12": -0.8, "A21": -0.5}),
        ("Van Laar - (assimétrico)", "Van Laar", {"A12": -0.3, "A21": -1.5}),
        ("Wilson +", "Wilson", {"L12": 0.18, "L21": 0.95}),
        ("Wilson -", "Wilson", {"L12": 1.6, "L21": 1.4}),
    ]
    for rotulo, modelo, params_verdadeiros in casos_extra:
        for c1, c2, T in (("ethanol", "water", 80.0), ("acetone", "chloroform", 50.0)):
            pontos = amostrar_pontos(c1, c2, T, modelo, params_verdadeiros, x1_amostra)
            resultado = regress_params_barker(modelo, c1, c2, T, pontos)
            todos_ok &= verificar_recuperacao(f"{rotulo} {c1}/{c2}", params_verdadeiros, resultado["params"])
            assert resultado["sucesso"], f"otimizador não convergiu para {rotulo} {c1}/{c2}"

    # Casos de erro esperados (seção 2.8 do mapeamento).
    try:
        regress_params_barker("Margules (2-P)", "ethanol", "water", 70.0, [(50.0, 0.2, 0.4), (60.0, 0.5, 0.6)])
        print("  [erro esperado] FALHA: deveria ter rejeitado poucos pontos")
        todos_ok = False
    except ValueError:
        print("  [erro esperado] OK: rejeita corretamente menos pontos que o mínimo")

    try:
        regress_params_barker(
            "NRTL", "ethanol", "water", 70.0, [(50.0, 0.2, 0.4), (60.0, 0.5, 0.6), (55.0, 0.8, 0.7)]
        )
        print("  [erro esperado] FALHA: deveria exigir alpha12 em params_fixos")
        todos_ok = False
    except ValueError:
        print("  [erro esperado] OK: exige alpha12 em params_fixos para NRTL")

    try:
        regress_params_barker(
            "UNIFAC", "ethanol", "water", 70.0, [(50.0, 0.2, 0.4), (60.0, 0.5, 0.6), (55.0, 0.8, 0.7)]
        )
        print("  [erro esperado] FALHA: UNIFAC não deveria suportar regressão")
        todos_ok = False
    except ValueError:
        print("  [erro esperado] OK: UNIFAC (preditivo) rejeita regressão")

    print()
    if todos_ok:
        print(f"OK: todos os parâmetros recuperados com erro relativo abaixo de {TOLERANCIA_RELATIVA:.0%}.")
    else:
        print("FALHA: um ou mais casos não passaram — ver detalhes acima.")


if __name__ == "__main__":
    main()
