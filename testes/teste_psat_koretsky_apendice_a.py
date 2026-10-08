"""
Pressão de vapor e constantes críticas da `thermo` contra o Apêndice A do
Koretsky (2026-10-08).

Fonte: Koretsky, M. D. *Engineering and Chemical Thermodynamics*, 2ª ed.
Hoboken: Wiley, 2013, Tabela A.1.1, pp. 639-640. Equação de Antoine do livro:

    ln(Psat [bar]) = A − B / (T [K] + C)       (válida de Tmin a Tmax da linha)

O app obtém a Psat da `thermo`, que escolhe sozinha a correlação por substância
(`Chemical.Psat`). Esta é uma conferência cruzada, de fonte independente: nas
temperaturas dentro da faixa de validade da Antoine do livro, a Psat da `thermo`
precisa concordar com ela dentro de uma tolerância medida; fora da faixa o
livro não garante nada e o teste não olha. Também confere Tc, Pc e ω (o app usa
Tc no aviso de temperatura crítica).

Os compostos são os que o livro tem e interessam ao projeto (2-butanona,
2,3-dimetil-2-buteno e 1,4-dioxano não constam na tabela). Os números foram
lidos da imagem do livro; um dígito errado de transcrição apareceria aqui como
desvio grande.

As tolerâncias foram fixadas depois de medir (valor medido ao lado de cada
constante): verificação de sanidade, não calibração — nada no motor foi
ajustado a esses números.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_psat_koretsky_apendice_a.py
"""

import numpy as np
from thermo import Chemical

# nome na thermo: (Tc [K], Pc [bar], ω, A, B, C, Tmin [K], Tmax [K])
TABELA_A11 = {
    "methanol":    (512.6, 80.96, 0.559, 11.9673, 3626.55, -34.29, 257, 364),
    "ethanol":     (516.2, 63.83, 0.635, 12.2917, 3803.98, -41.68, 270, 369),
    "water":       (647.3, 220.48, 0.344, 11.6834, 3816.44, -46.13, 284, 441),
    "chloroform":  (536.4, 54.72, 0.216, 9.3530, 2696.79, -46.16, 260, 370),
    "acetone":     (508.1, 47.01, 0.309, 10.0311, 2940.46, -35.93, 241, 350),
    "benzene":     (562.1, 48.94, 0.212, 9.2806, 2788.51, -52.36, 280, 377),
    "toluene":     (591.7, 41.14, 0.257, 9.3935, 3096.52, -53.67, 280, 410),
    "cyclohexane": (553.4, 40.73, 0.213, 9.1325, 2766.63, -50.50, 280, 380),
    "pentane":     (469.6, 33.74, 0.251, 9.2131, 2477.07, -39.94, 220, 330),
    "hexane":      (507.4, 29.69, 0.296, 9.2164, 2697.55, -48.78, 245, 370),
    "heptane":     (540.2, 27.36, 0.351, 9.2535, 2911.32, -56.51, 270, 400),
}

TOL_PSAT_PCT = 3.5     # medido: até 3,08 % (acetona a 251 K) e 2,24 % (clorofórmio a 360 K), nas pontas da faixa.
#   Não é falha da thermo: no ponto de ebulição normal (P = 101,325 kPa, referência independente)
#   a thermo fica a ≤ 0,05 % e a Antoine de 3 parâmetros do livro erra até 1,8 % (clorofórmio).
TOL_PSAT_TB_PCT = 0.15  # Psat da thermo em Tb contra 101,325 kPa; medido: até 0,05 % (clorofórmio)
TOL_TC_PCT = 0.5       # medido: até 0,3 % (etanol)
TOL_PC_PCT = 3.0       # medido: até 2,7 % (clorofórmio)
TOL_OMEGA = 0.012      # medido: até 0,009 (tolueno)

falhas = []


def main():
    pior_psat = (0.0, "")
    print("Psat (thermo) contra a Antoine do livro, 5 temperaturas dentro de [Tmin + 10, Tmax − 10]:")
    for nome, (Tc, Pc, w, A, B, C, Tmin, Tmax) in TABELA_A11.items():
        dif = []
        for T in np.linspace(Tmin + 10, Tmax - 10, 5):
            ant = 100.0 * np.exp(A - B / (T + C))                # kPa
            th = Chemical(nome, T=T).Psat / 1000.0
            dif.append(100.0 * (th - ant) / ant)
        pior = max(dif, key=abs)
        if abs(pior) > abs(pior_psat[0]):
            pior_psat = (pior, nome)
        ok = abs(pior) < TOL_PSAT_PCT
        print(f"  {'OK   ' if ok else 'FALHA'} {nome:12s} {Tmin}-{Tmax} K: diferença de {min(dif):+.2f} a {max(dif):+.2f} %")
        if not ok:
            falhas.append(f"Psat de {nome}: {pior:+.2f} %")
    print(f"  pior: {pior_psat[0]:+.2f} % ({pior_psat[1]}); tolerância {TOL_PSAT_PCT} %")

    print("\nÂncora física: Psat da thermo na temperatura de ebulição normal (Tb) = 101,325 kPa:")
    for nome in TABELA_A11:
        c = Chemical(nome)
        d = 100 * (Chemical(nome, T=c.Tb).Psat / 1000.0 - 101.325) / 101.325
        ok = abs(d) < TOL_PSAT_TB_PCT
        print(f"  {'OK   ' if ok else 'FALHA'} {nome:12s} Tb = {c.Tb:7.2f} K: {d:+.3f} %")
        if not ok:
            falhas.append(f"Psat em Tb de {nome}: {d:+.3f} %")

    print("\nConstantes críticas e fator acêntrico (thermo contra livro):")
    for nome, (Tc, Pc, w, *_ ) in TABELA_A11.items():
        c = Chemical(nome)
        dTc = 100 * (c.Tc - Tc) / Tc
        dPc = 100 * (c.Pc / 1e5 - Pc) / Pc
        dw = c.omega - w
        ok = abs(dTc) < TOL_TC_PCT and abs(dPc) < TOL_PC_PCT and abs(dw) < TOL_OMEGA
        print(f"  {'OK   ' if ok else 'FALHA'} {nome:12s} Tc {dTc:+.2f} %   Pc {dPc:+.2f} %   ω {dw:+.3f}")
        if not ok:
            falhas.append(f"constantes de {nome}")

    print()
    if falhas:
        print(f"FALHA: {falhas}")
        raise SystemExit(1)
    print("OK: Psat e constantes críticas da thermo conferem com o Apêndice A do Koretsky.")


if __name__ == "__main__":
    main()
