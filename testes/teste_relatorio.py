"""Relatório em HTML (calculos/relatorio.py) — pedido do orientador, 2026-10-21.

Confere, sem abrir a interface:
- `erros_comparacao` dá os mesmos números do botão "Comparar" nos dois exemplos
  NIST registrados no CLAUDE.md (metanol/dimetilbuteno 70 °C: ΔP 31,78 % e Δy
  0,1530; etanol/água 108 °C: ΔP 14,19 % e Δy 0,0658, Margules 1-P com A = 0,5);
- o HTML sai bem formado, com os números esperados e sem "NaN";
- texto vindo do usuário é escapado (nada de tag solta);
- o relatório não faz veredito (o orientador declinou o "bom/ruim");
- os casos sem tabela e sem comparação funcionam.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_relatorio.py
"""

import sys
import xml.dom.minidom
from html.parser import HTMLParser

sys.path.insert(0, "interface")

from calculos.gemini import calculate_vle_isothermal, ln_gamma_experimental
from calculos.relatorio import (
    _limites_y,
    erros_comparacao,
    gerar_relatorio_html,
    svg_grafico,
)
import fletando_grafico as ui

todos_ok = True


def conferir(descricao, condicao, detalhe=""):
    global todos_ok
    print(f"  [{descricao}] {detalhe}-> {'OK' if condicao else 'FALHA'}")
    todos_ok &= bool(condicao)


def exemplo(rotulo_parcial):
    for ex in ui.EXEMPLOS_NIST:
        if rotulo_parcial in ex["rotulo"]:
            return ex
    raise KeyError(rotulo_parcial)


def montar_dados(ex, modelo, params, comp1=None, comp2=None, com_pontos=True):
    comp1 = comp1 or ex["componente1"]
    comp2 = comp2 or ex["componente2"]
    T_C = ex["T_K"] - 273.15
    pontos = ui.carregar_exemplo_nist(ex) if com_pontos else []
    curva = calculate_vle_isothermal(comp1, comp2, T_C, modelo, params)
    comparacao = None
    if pontos:
        x1_lista = sorted({x for _, x, _ in pontos})
        comp = calculate_vle_isothermal(comp1, comp2, T_C, modelo, params, x1_values=x1_lista)
        comparacao = erros_comparacao(pontos, comp)
    return {
        "gerado_em": "21/10/2026 10:00",
        "comp1": comp1, "comp2": comp2, "T_C": T_C, "modelo": modelo,
        "parametros": [("A", params["A"])] if "A" in params else [],
        "origem_rotulo": "Fornecido", "origem_detalhe": "Valor digitado.",
        "pontos": pontos,
        "fonte_dados": ex["fonte"] if pontos else None,
        "curva": curva,
        "comparacao": comparacao,
        "ln_gamma_exp": ln_gamma_experimental(pontos, comp1, comp2, T_C) if pontos else [],
        "avisos": [],
    }


class Verificador(HTMLParser):
    """Conta tags abertas e fechadas (só as que precisam de par)."""

    SEM_PAR = {"meta", "br", "line", "rect", "circle", "path", "polyline", "input", "hr"}

    def __init__(self):
        super().__init__()
        self.pilha = []
        self.erro = None

    def handle_starttag(self, tag, attrs):
        if tag not in self.SEM_PAR:
            self.pilha.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.SEM_PAR:
            return
        if not self.pilha or self.pilha[-1] != tag:
            self.erro = f"</{tag}> sem par (pilha: {self.pilha[-3:]})"
        else:
            self.pilha.pop()


def main():
    print("== erros_comparacao contra os números registrados do app ==")
    casos = [
        ("metanol/dimetilbuteno", 31.78, 0.1530),
        ("etanol/água, 108", 14.19, 0.0658),
    ]
    for rotulo, dp_ref, dy_ref in casos:
        ex = exemplo(rotulo)
        dados = montar_dados(ex, "Margules (1-P)", {"A": 0.5})
        c = dados["comparacao"]
        conferir(
            rotulo,
            abs(c["dp_rms_pct"] - dp_ref) < 0.006 and abs(c["dy_rms"] - dy_ref) < 0.00006,
            f"ΔP = {c['dp_rms_pct']:.2f} % (ref {dp_ref}), Δy = {c['dy_rms']:.4f} (ref {dy_ref}) ",
        )
        conferir(
            rotulo + " — pontos",
            c["n"] == len(dados["pontos"]) == len(c["linhas"]),
            f"n = {c['n']} ",
        )

    print("== HTML completo (metanol/dimetilbuteno, Margules 1-P) ==")
    ex = exemplo("metanol/dimetilbuteno")
    dados = montar_dados(ex, "Margules (1-P)", {"A": 0.5})
    dados["avisos"] = ["Atenção: teste de aviso & <b>negrito</b>."]
    texto = gerar_relatorio_html(dados)
    v = Verificador()
    v.feed(texto)
    conferir("tags bem formadas", v.erro is None and not v.pilha, f"{v.erro or ''}")
    conferir("sem NaN/inf", "nan" not in texto.lower().replace("fonte", "") and "inf" not in texto.split("<style>")[0] .lower().replace("information", ""))
    conferir("ΔP e Δy no texto", "31.78 %" in texto and "0.1530" in texto)
    conferir("fonte citada", "Feng, Dong e Li" in texto)
    conferir("aviso escapado", "&lt;b&gt;negrito&lt;/b&gt;" in texto and "<b>negrito</b>" not in texto)
    conferir("sem veredito", all(p not in texto.lower() for p in ("bom ajuste", "ajuste ruim", "ajuste bom", "aprovado")))
    conferir("dois gráficos SVG", texto.count("<svg viewBox") == 2)
    for i, trecho in enumerate(texto.split("<svg viewBox")[1:], start=1):
        svg = "<svg viewBox" + trecho.split("</svg>")[0] + "</svg>"
        try:
            xml.dom.minidom.parseString(svg)
            ok = True
        except Exception as exc:
            ok = False
            print("     erro no SVG:", exc)
        conferir(f"SVG {i} é XML válido", ok)

    print("== escape do que o usuário digita ==")
    dados2 = montar_dados(ex, "Margules (1-P)", {"A": 0.5})
    dados2["comp1"] = '<script>alert("x")</script>'
    texto2 = gerar_relatorio_html(dados2)
    conferir("componente escapado", "<script>alert" not in texto2 and "&lt;script&gt;" in texto2)

    print("== sem tabela e sem comparação ==")
    dados3 = montar_dados(ex, "Margules (1-P)", {"A": 0.5}, com_pontos=False)
    texto3 = gerar_relatorio_html(dados3)
    v = Verificador()
    v.feed(texto3)
    conferir("tags bem formadas", v.erro is None and not v.pilha)
    conferir("diz que não há pontos", "Nenhum ponto experimental" in texto3)
    conferir("sem seção de comparação", "Comparação entre o modelo" not in texto3)

    print("== gráfico com valores constantes não quebra ==")
    ini, fim, passo = _limites_y([5.0, 5.0, 5.0])
    conferir("limites", fim > ini and passo > 0, f"({ini}, {fim}, passo {passo}) ")
    svg = svg_grafico("x", "y", [{"tipo": "linha", "cor": "#000", "pontos": [(0, 5), (1, 5)]}])
    xml.dom.minidom.parseString(svg)
    conferir("SVG constante", True)

    print()
    if todos_ok:
        print("OK: relatório em HTML validado.")
    else:
        print("FALHA: veja as linhas acima.")
        sys.exit(1)


main()
