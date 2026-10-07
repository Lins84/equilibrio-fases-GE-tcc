"""Aviso de temperatura crítica (2026-10-07).

`calculate_vle_isothermal` devolve `Tc_C` (°C) dos dois componentes, e a UI usa
`aviso_temperatura_critica` para avisar quando T chega à crítica de algum
deles — acima dela a pressão de vapor extrapolada não tem sentido e o cálculo
não dá erro (etanol/água a 300 °C devolve P acima da pressão crítica do etanol).

Rodar da raiz: PYTHONPATH=. .venv/bin/python testes/teste_temperatura_critica.py
"""
import importlib.util
import sys
from pathlib import Path

from calculos.gemini import calculate_vle_isothermal

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "interface"))
spec = importlib.util.spec_from_file_location("fg", RAIZ / "interface" / "fletando_grafico.py")
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

falhas = []


def conferir(ok, msg):
    print(("OK: " if ok else "FALHOU: ") + msg)
    if not ok:
        falhas.append(msg)


r = calculate_vle_isothermal("ethanol", "water", 70.0, "Margules (1-P)", {"A": 1.0})
tc_etanol, tc_agua = r["Tc_C"]
conferir(abs(tc_etanol - 241.56) < 0.1 and abs(tc_agua - 373.95) < 0.1,
         f"Tc do etanol e da água em °C ({tc_etanol:.2f}; {tc_agua:.2f}).")

av = fg.aviso_temperatura_critica("ethanol", "water", 70.0, r["Tc_C"])
conferir(av is None, "sem aviso a 70 °C.")

av = fg.aviso_temperatura_critica("ethanol", "water", 300.0, r["Tc_C"])
conferir(av is not None and "ethanol" in av and "water" not in av,
         "aviso a 300 °C cita só o etanol (a água ainda está abaixo da crítica).")

av = fg.aviso_temperatura_critica("ethanol", "water", 400.0, r["Tc_C"])
conferir(av is not None and "ethanol" in av and "water" in av,
         "aviso a 400 °C cita os dois componentes.")

conferir(fg.aviso_temperatura_critica("a", "b", 500.0, [None, None]) is None,
         "Tc desconhecida (None) não gera aviso nem erro.")

if falhas:
    print(f"\n{len(falhas)} falha(s).")
    sys.exit(1)
print("\nTodos os testes passaram.")
