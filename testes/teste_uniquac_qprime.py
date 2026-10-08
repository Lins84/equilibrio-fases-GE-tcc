"""Opção "usar q′" do UNIQUAC (2026-10-08).

O q′ (q modificado de Anderson e Prausnitz, Koretsky Tabela 7.4) vem do XML do
ChemSep (`UniquacQP`). `uniquac_qprime_do_par` diz se a opção muda alguma coisa
para o par, e `montar_parametros_automaticos(..., usar_qprime=True)` acrescenta
`qp1`/`qp2` quando muda. Verifica:

  1. padrão desligado: sem `qp1`/`qp2`, parâmetros idênticos aos de antes;
  2. etanol/água: q′ = 0,92 e 1,00 (os valores do Koretsky, Exemplo 7.12 e Problema
     7.68), a opção "afeta" e o resultado do modelo difere do sem q′;
  3. acetona/clorofórmio (q′ = q): a opção não afeta, e ligá-la não muda o resultado;
  4. um componente afetado e outro não (etanol/benzeno): q′ do benzeno vale o próprio
     q (2,4 = 2,4 do Problema 7.69);
  5. r/q dos grupos UNIFAC (ChemSep sem r/q): a opção não se aplica;
  6. a UI conhece o selo "Banco, com q′";
  7. os parâmetros montados pela opção (r, q, q′, a₁₂, a₂₁ do ChemSep) reproduzem a fórmula
     da Tabela 7.4 do Koretsky, transcrita à parte em
     `teste_koretsky_formulas_e_exemplos.livro_uniquac` (confere a ligação, não um valor do livro).

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_uniquac_qprime.py
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

from calculos import gemini
from calculos.gemini import MODELS_GE, montar_parametros_automaticos, uniquac_qprime_do_par

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


def ln_gamma(params, x1=0.4, T=343.15):
    g = MODELS_GE["UNIQUAC"](x1, {**params, "T_K": T})
    return np.log(np.array(g))


# 1. padrão desligado
p0 = montar_parametros_automaticos("UNIQUAC", "ethanol", "water")
conferir("qp1" not in p0 and "qp2" not in p0, "padrão: sem qp1/qp2.")
conferir("qp1" not in montar_parametros_automaticos("UNIQUAC", "ethanol", "water", usar_qprime=False),
         "usar_qprime=False explícito: sem qp1/qp2.")

# 2. etanol/água
info = uniquac_qprime_do_par("ethanol", "water")
conferir(info["afeta"] and info["qp1"] == 0.92 and info["qp2"] == 1.0,
         f"etanol/água: q′ = {info['qp1']} e {info['qp2']} (Koretsky: 0,92 e 1,00), afeta.")
p1 = montar_parametros_automaticos("UNIQUAC", "ethanol", "water", usar_qprime=True)
conferir(p1.get("qp1") == 0.92 and p1.get("qp2") == 1.0, "com a opção: qp1 = 0,92 e qp2 = 1,00 nos parâmetros.")
conferir(all(p1[k] == p0[k] for k in p0), "os demais parâmetros (r, q, a₁₂, a₂₁) não mudam.")
d = np.abs(ln_gamma(p1) - ln_gamma(p0)).max()
conferir(d > 0.05, f"o resultado muda com q′ (ln γ difere em até {d:.2f}).")

# 3. par sem efeito
info = uniquac_qprime_do_par("acetone", "chloroform")
conferir(not info["afeta"] and info["motivo"], f"acetona/clorofórmio: não afeta ({info['motivo']}).")
pa = montar_parametros_automaticos("UNIQUAC", "acetone", "chloroform", usar_qprime=True)
conferir("qp1" not in pa, "acetona/clorofórmio com a opção ligada: sem qp1/qp2 (nada a mudar).")
pa0 = montar_parametros_automaticos("UNIQUAC", "acetone", "chloroform")
conferir(np.allclose(ln_gamma(pa), ln_gamma(pa0), rtol=0, atol=1e-14), "e o resultado é idêntico.")

# 4. um afetado e um não
info = uniquac_qprime_do_par("ethanol", "benzene")
conferir(info["afeta"] and info["qp1"] == 0.92 and info["qp2"] == 2.4,
         f"etanol/benzeno: q′ = {info['qp1']} e {info['qp2']} (Problema 7.69: 0,92 e 2,4).")

# 5. r/q pelos grupos UNIFAC: a opção não se aplica
original = gemini._tabela_rq_chemsep
gemini._tabela_rq_chemsep = lambda: {}
try:
    info = uniquac_qprime_do_par("ethanol", "water")
    pu = montar_parametros_automaticos("UNIQUAC", "ethanol", "water", usar_qprime=True)
finally:
    gemini._tabela_rq_chemsep = original
conferir(not info["afeta"] and "UNIFAC" in info["motivo"] and "qp1" not in pu,
         "sem r/q do ChemSep (grupos UNIFAC): a opção não se aplica e não acrescenta qp.")

# 6. selo
conferir("banco_qprime" in fg.ORIGENS_SELO and fg.ORIGENS_SELO["banco_qprime"][2] == "Banco, com q′",
         'a UI tem o selo "Banco, com q′".')

# 7. ida e volta contra a fórmula do livro (Tabela 7.4) com os parâmetros do banco
sys.path.insert(0, str(RAIZ / "testes"))
from teste_koretsky_formulas_e_exemplos import livro_uniquac  # noqa: E402

T = 343.15
for x in (0.1, 0.4, 0.8):
    app = np.exp(ln_gamma(p1, x, T))
    liv = livro_uniquac(x, p1["r1"], p1["q1"], p1["qp1"], p1["r2"], p1["q2"], p1["qp2"], p1["a12"], p1["a21"], T)
    e = np.abs(np.log(app) - np.log(np.array(liv))).max()
    conferir(e < 1e-10, f"x₁ = {x}: parâmetros montados pela opção reproduzem a Tabela 7.4 (erro {e:.1e}).")

if falhas:
    print(f"\n{len(falhas)} falha(s).")
    sys.exit(1)
print("\nTodos os testes passaram.")
