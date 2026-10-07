"""Aviso de ajuste suspeito da regressão de Barker (2026-10-07, opção (a)).

`regress_params_barker` devolve `no_limite` (parâmetros a menos de 1 % de um
limite da busca) e `sucesso`; a UI transforma isso em texto com
`aviso_ajuste_regressao`. Verifica que:
- dados sem relação com o par encostam parâmetros no limite e geram aviso;
- os quatro exemplos NIST do app, em todos os modelos com slider, NÃO geram aviso
  (nenhum falso positivo);
- `sucesso` falso gera aviso mesmo sem parâmetro no limite;
- sem problema, o aviso é None.

Rodar da raiz: PYTHONPATH=. .venv/bin/python testes/teste_aviso_regressao.py
"""
import importlib.util
import random
import sys
from pathlib import Path

from calculos.gemini import regress_params_barker

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "interface"))
spec = importlib.util.spec_from_file_location("fg", RAIZ / "interface" / "fletando_grafico.py")
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

MODELOS = ["Margules (1-P)", "Margules (2-P)", "Van Laar", "Wilson", "NRTL"]
falhas = []


def conferir(ok, msg):
    print(("OK: " if ok else "FALHOU: ") + msg)
    if not ok:
        falhas.append(msg)


def rotulos(modelo):
    return {s["chave"]: (None, None, s["rotulo"]) for s in fg.PARAM_SLIDERS[modelo]}


def regredir(modelo, c1, c2, T_C, pontos):
    fixos = {"alpha12": 0.3} if modelo == "NRTL" else {}
    return regress_params_barker(modelo, c1, c2, T_C, pontos, params_fixos=fixos)


# 1) dados sem relação com o par (mesma semente do achado de 2026-10-07)
random.seed(1)
ruido = [(30 + random.random() * 40, i / 9, random.random()) for i in range(10)]
for modelo, chave, rotulo in [("Van Laar", "A21", "A₂₁"), ("Wilson", "L12", "Λ₁₂")]:
    res = regredir(modelo, "ethanol", "water", 70.0, ruido)
    chaves = [p["chave"] for p in res["no_limite"]]
    aviso = fg.aviso_ajuste_regressao(res, rotulos(modelo))
    conferir(chave in chaves, f"{modelo}: {chave} marcado no limite com dados sem relação ({chaves}).")
    conferir(aviso is not None and rotulo in aviso and "limite da busca" in aviso,
             f"{modelo}: aviso cita {rotulo} e o limite da busca.")

# 2) exemplos reais: nenhum falso positivo
for ex in fg.EXEMPLOS_NIST:
    pontos = fg.carregar_exemplo_nist(ex)
    T_C = ex["T_K"] - 273.15
    for modelo in MODELOS:
        res = regredir(modelo, ex["componente1"], ex["componente2"], T_C, pontos)
        aviso = fg.aviso_ajuste_regressao(res, rotulos(modelo))
        conferir(aviso is None and res["sucesso"],
                 f"{ex['rotulo']} / {modelo}: sem aviso (no_limite={res['no_limite']}, sucesso={res['sucesso']}).")

# 3) otimizador que não convergiu
sintetico = {"params": {}, "no_limite": [], "sucesso": False}
aviso = fg.aviso_ajuste_regressao(sintetico, {})
conferir(aviso is not None and "não convergiu" in aviso, "sucesso falso gera aviso de não convergência.")

# 4) sem problema
conferir(fg.aviso_ajuste_regressao({"no_limite": [], "sucesso": True}, {}) is None,
         "sem parâmetro no limite e com convergência, o aviso é None.")

if falhas:
    print(f"\n{len(falhas)} falha(s).")
    sys.exit(1)
print("\nTodos os testes passaram.")
