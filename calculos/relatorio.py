"""Relatório em HTML do VLE Interativo (pedido do orientador, formato escolhido
pelo autor em 2026-10-21).

Módulo puro: não importa Flet nem `thermo`. Recebe os números já calculados e
devolve um arquivo HTML único, com estilo e gráficos (SVG) embutidos — sem
biblioteca nova e sem arquivo externo —, que abre em qualquer navegador e que o
aluno imprime como PDF por lá. O relatório **não classifica o ajuste como bom ou
ruim** (o orientador declinou o veredito em 2026-10-20: a crítica cabe a quem
lê).

Contrato de `gerar_relatorio_html(dados)`:

    gerado_em   str            data e hora já formatadas
    comp1/comp2 str            identificadores digitados no card "Sistema"
    T_C         float          temperatura em °C
    modelo      str            nome do modelo Gᴱ (chave de MODELS_GE)
    parametros  [(rótulo, valor)]   parâmetros numéricos do modelo
    origem_rotulo / origem_detalhe  selo de origem do parâmetro (str ou None)
    pontos      [(P kPa, x1, y1)]   tabela experimental (pode ser vazia)
    fonte_dados str | None     fonte, se a tabela ainda é um exemplo embutido
    curva       dict           saída de `calculate_vle_isothermal` na malha padrão
    comparacao  dict | None    saída de `erros_comparacao`
    ln_gamma_exp [(x1, ln γ1, ln γ2)]   ln γ da tabela (método indireto)
    avisos      [str]          avisos do app (fase líquida instável, T crítica…)
"""

import html
import math

# Mesmas cores dos gráficos do app (azul = líquido, laranja = vapor, verde e
# roxo = ln γ₁ e ln γ₂): a cor identifica a fase/componente e o estilo
# identifica a origem (marcador cheio = tabela, linha = modelo, marcador
# vazado = modelo nos x₁ da tabela).
COR_LIQUIDO = "#1976d2"
COR_VAPOR = "#e65100"
COR_GAMMA1 = "#388e3c"
COR_GAMMA2 = "#8e24aa"


def erros_comparacao(pontos, resultado):
    """ΔP e Δy do modelo contra a tabela — a mesma conta do botão "Comparar".

    `pontos` = [(P kPa, x1, y1)] da tabela; `resultado` = saída de
    `calculate_vle_isothermal(..., x1_values=<x1 da tabela>)`. Devolve:

    - `n`: pontos que entram no erro;
    - `dp_rms_pct`: ΔP relativo (%), RMS; `dy_rms`: Δy absoluto, RMS (duas
      grandezas separadas, decisão de 2026-09-27);
    - `pior_dp`, `pior_dy`: (maior desvio, x₁ onde ocorre); o de pressão é
      fração (multiplique por 100 para %);
    - `linhas`: por ponto, (x1, P_exp, P_calc, ΔP %, y_exp, y_calc, Δy).
    """
    calc_por_x1 = dict(zip(resultado["x1"], zip(resultado["P_kPa"], resultado["y1"])))
    soma_dp_rel2 = 0.0
    soma_dy_abs2 = 0.0
    pior_dp = (0.0, None)
    pior_dy = (0.0, None)
    linhas = []
    for p_exp, x1, y_exp in pontos:
        p_calc, y_calc = calc_por_x1[x1]
        desvio_p = abs(p_calc - p_exp) / p_exp
        desvio_y = abs(y_calc - y_exp)
        soma_dp_rel2 += desvio_p ** 2
        soma_dy_abs2 += desvio_y ** 2
        if pior_dp[1] is None or desvio_p > pior_dp[0]:
            pior_dp = (desvio_p, x1)
        if pior_dy[1] is None or desvio_y > pior_dy[0]:
            pior_dy = (desvio_y, x1)
        linhas.append((x1, p_exp, p_calc, desvio_p * 100, y_exp, y_calc, desvio_y))
    n = len(pontos)
    return {
        "n": n,
        "dp_rms_pct": math.sqrt(soma_dp_rel2 / n) * 100,
        "dy_rms": math.sqrt(soma_dy_abs2 / n),
        "pior_dp": pior_dp,
        "pior_dy": pior_dy,
        "linhas": linhas,
    }


# ---------------------------------------------------------------------------
# Gráficos em SVG
# ---------------------------------------------------------------------------

def _passo_redondo(intervalo, alvo=6):
    """Passo 1, 2, 2,5 ou 5 × 10^k que dá cerca de `alvo` intervalos."""
    bruto = intervalo / alvo
    expoente = math.floor(math.log10(bruto))
    fracao = bruto / 10 ** expoente
    for m in (1, 2, 2.5, 5, 10):
        if fracao <= m:
            return m * 10 ** expoente
    return 10 * 10 ** expoente


def _casas(passo):
    texto = f"{passo:.10f}".rstrip("0")
    return len(texto.split(".")[1]) if "." in texto else 0


def _rotulo(valor, casas):
    # "-0" e "0.0" viram "0"; o resto tem o mínimo de casas do passo.
    if abs(valor) < 10 ** (-casas - 3):
        return "0"
    return f"{valor:.{casas}f}"


def _limites_y(valores):
    vmin, vmax = min(valores), max(valores)
    if vmax - vmin < 1e-6 * max(1.0, abs(vmax), abs(vmin)):
        vmin, vmax = vmin - 1, vmax + 1
    margem = 0.05 * (vmax - vmin)
    passo = _passo_redondo(vmax - vmin + 2 * margem)
    inicio = math.floor((vmin - margem) / passo) * passo
    fim = math.ceil((vmax + margem) / passo) * passo
    return inicio, fim, passo


def _glifo(tipo, cor, x, y, r=4.5):
    """Marcador SVG: 'quadrado', 'circulo', ou os mesmos com sufixo '_vazado'."""
    vazado = tipo.endswith("_vazado")
    base = tipo.replace("_vazado", "")
    preenchimento = "#fff" if vazado else cor
    atributos = f'fill="{preenchimento}" stroke="{cor}" stroke-width="1.6"'
    if base == "quadrado":
        return (
            f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r:.1f}" '
            f'height="{2 * r:.1f}" {atributos}/>'
        )
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" {atributos}/>'


def svg_grafico(titulo_x, titulo_y, series, largura=560, altura=360):
    """Gráfico de linhas/marcadores em SVG, eixo x de 0 a 1.

    `series` = lista de dicts {"tipo": "linha" | "quadrado" | "circulo" |
    "quadrado_vazado" | "circulo_vazado", "cor": str, "pontos": [(x, y)]}.
    Séries sem pontos são ignoradas. Devolve a tag <svg> como string.
    """
    series = [s for s in series if s["pontos"]]
    esquerda, direita, topo, base = 66, 16, 14, 50
    larg_plot = largura - esquerda - direita
    alt_plot = altura - topo - base
    ys = [y for s in series for _, y in s["pontos"]] or [0.0, 1.0]
    y_ini, y_fim, passo_y = _limites_y(ys)

    def px(x):
        return esquerda + x * larg_plot

    def py(y):
        return topo + (y_fim - y) / (y_fim - y_ini) * alt_plot

    partes = [
        f'<svg viewBox="0 0 {largura} {altura}" width="100%" role="img" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="12">'
    ]
    casas_y = _casas(passo_y)
    n_y = int(round((y_fim - y_ini) / passo_y))
    for k in range(n_y + 1):
        valor = y_ini + k * passo_y
        y = py(valor)
        partes.append(
            f'<line x1="{esquerda}" y1="{y:.1f}" x2="{largura - direita}" '
            f'y2="{y:.1f}" stroke="#e0e0e0"/>'
        )
        partes.append(
            f'<text x="{esquerda - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="#333">{_rotulo(valor, casas_y)}</text>'
        )
    for k in range(6):
        x_val = k / 5
        x = px(x_val)
        partes.append(
            f'<line x1="{x:.1f}" y1="{topo}" x2="{x:.1f}" y2="{topo + alt_plot}" '
            f'stroke="#eeeeee"/>'
        )
        partes.append(
            f'<text x="{x:.1f}" y="{topo + alt_plot + 16}" text-anchor="middle" '
            f'fill="#333">{_rotulo(x_val, 1)}</text>'
        )
    partes.append(
        f'<rect x="{esquerda}" y="{topo}" width="{larg_plot}" height="{alt_plot}" '
        f'fill="none" stroke="#9e9e9e"/>'
    )
    for s in series:
        if s["tipo"] == "linha":
            caminho = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in s["pontos"])
            partes.append(
                f'<polyline points="{caminho}" fill="none" stroke="{s["cor"]}" '
                f'stroke-width="2.2" stroke-linejoin="round"/>'
            )
    for s in series:
        if s["tipo"] != "linha":
            for x, y in s["pontos"]:
                partes.append(_glifo(s["tipo"], s["cor"], px(x), py(y)))
    partes.append(
        f'<text x="{esquerda + larg_plot / 2:.1f}" y="{altura - 8}" '
        f'text-anchor="middle" fill="#222" font-size="13">{html.escape(titulo_x)}</text>'
    )
    partes.append(
        f'<text transform="translate(15 {topo + alt_plot / 2:.1f}) rotate(-90)" '
        f'text-anchor="middle" fill="#222" font-size="13">{html.escape(titulo_y)}</text>'
    )
    partes.append("</svg>")
    return "".join(partes)


def _legenda(itens):
    """Legenda em HTML: itens = [(tipo, cor, texto)]."""
    celulas = []
    for tipo, cor, texto in itens:
        if tipo == "linha":
            glifo = (
                f'<svg width="26" height="12"><line x1="1" y1="6" x2="25" y2="6" '
                f'stroke="{cor}" stroke-width="2.2"/></svg>'
            )
        else:
            glifo = f'<svg width="14" height="14">{_glifo(tipo, cor, 7, 7, 4.5)}</svg>'
        celulas.append(f'<span class="leg">{glifo} {html.escape(texto)}</span>')
    return '<div class="legenda">' + "".join(celulas) + "</div>"


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

def _num(valor, casas=4):
    return f"{valor:.{casas}f}"


def _tabela(cabecalhos, linhas, classe=""):
    cab = "".join(f"<th>{c}</th>" for c in cabecalhos)
    corpo = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in linha) + "</tr>" for linha in linhas
    )
    return f'<table class="{classe}"><thead><tr>{cab}</tr></thead><tbody>{corpo}</tbody></table>'


_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; color: #1b1b1b; background: #fff;
       margin: 0 auto; max-width: 860px; padding: 24px 16px 40px; line-height: 1.45; }
header { background: #1976d2; color: #fff; border-radius: 12px; padding: 16px 20px; }
header h1 { margin: 0 0 4px; font-size: 22px; }
header p { margin: 0; font-size: 14px; opacity: .95; }
h2 { color: #1565c0; font-size: 17px; margin: 26px 0 8px; border-bottom: 2px solid #bbdefb;
     padding-bottom: 3px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; margin: 6px 0; }
th, td { border: 1px solid #bbdefb; padding: 5px 8px; text-align: right; }
th { background: #e3f2fd; color: #0d47a1; }
table.chave td:first-child, table.chave th:first-child { text-align: left; }
table.chave td:first-child { background: #f5f9ff; font-weight: bold; width: 34%; }
.nota { font-size: 13px; color: #424242; }
.aviso { background: #fff3e0; border-left: 4px solid #e65100; color: #7a3300;
         padding: 8px 12px; margin: 8px 0; font-size: 14px; border-radius: 4px; }
.selo { display: inline-block; background: #eceff1; color: #263238; border-radius: 10px;
        padding: 1px 9px; font-weight: bold; font-size: 14px; }
.legenda { font-size: 13px; margin: 2px 0 10px; }
.leg { display: inline-block; margin-right: 16px; white-space: nowrap; }
.leg svg { vertical-align: middle; }
.grafico { margin: 8px 0 4px; }
footer { margin-top: 30px; font-size: 12px; color: #616161; border-top: 1px solid #e0e0e0;
         padding-top: 8px; }
@media print {
  body { max-width: none; padding: 0; }
  header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  h2 { break-after: avoid; }
  table, .bloco, .aviso { break-inside: avoid; }
}
@page { size: A4; margin: 14mm; }
"""


def gerar_relatorio_html(dados):
    """Monta o relatório (string HTML completa) a partir de `dados` (ver o
    contrato no início do módulo). Todo texto vindo do usuário é escapado."""
    e = html.escape
    comp1, comp2 = e(str(dados["comp1"])), e(str(dados["comp2"]))
    modelo = e(str(dados["modelo"]))
    T_C = dados["T_C"]
    curva = dados["curva"]
    pontos = dados.get("pontos") or []
    comparacao = dados.get("comparacao")
    ln_exp = dados.get("ln_gamma_exp") or []

    corpo = []

    # 1. Sistema e hipóteses
    corpo.append("<h2>Sistema</h2>")
    corpo.append(_tabela(
        ["Item", "Valor"],
        [
            ["Componente 1", comp1],
            ["Componente 2", comp2],
            ["Temperatura", f"{T_C:g} °C"],
            ["Modelo de Gᴱ", modelo],
        ],
        classe="chave",
    ))
    corpo.append(
        '<p class="nota">Equilíbrio líquido-vapor isotérmico pela Lei de Raoult '
        "modificada (vapor ideal, uma só fase líquida); pressões de vapor dos "
        "componentes puros pela biblioteca <i>thermo</i>. Pressão em kPa; x₁ e y₁ "
        "são frações molares do componente 1.</p>"
    )

    # 2. Parâmetros e origem
    corpo.append("<h2>Parâmetros do modelo</h2>")
    parametros = dados.get("parametros") or []
    if parametros:
        corpo.append(_tabela(
            ["Parâmetro", "Valor"],
            [[e(str(r)), _num(v)] for r, v in parametros],
            classe="chave",
        ))
    if dados.get("origem_rotulo"):
        corpo.append(
            f'<p>Origem: <span class="selo">{e(dados["origem_rotulo"])}</span></p>'
        )
    if dados.get("origem_detalhe"):
        corpo.append(f'<p class="nota">{e(dados["origem_detalhe"])}</p>')

    # 3. Dados experimentais
    corpo.append("<h2>Dados experimentais</h2>")
    if pontos:
        corpo.append(_tabela(
            ["#", "P (kPa)", "x₁", "y₁"],
            [[i + 1, _num(p, 3), _num(x), _num(y)] for i, (p, x, y) in enumerate(pontos)],
        ))
        if dados.get("fonte_dados"):
            corpo.append(f'<p class="nota">Fonte: {e(dados["fonte_dados"])}.</p>')
    else:
        corpo.append('<p class="nota">Nenhum ponto experimental na tabela.</p>')

    # 4. Comparação calculado × experimental
    if comparacao:
        pior_dp, x_dp = comparacao["pior_dp"]
        pior_dy, x_dy = comparacao["pior_dy"]
        corpo.append("<h2>Comparação entre o modelo e a tabela</h2>")
        corpo.append(_tabela(
            ["Medida", "Valor"],
            [
                ["Pontos usados", comparacao["n"]],
                ["ΔP relativo (RMS)", f"{comparacao['dp_rms_pct']:.2f} %"],
                ["Δy absoluto (RMS)", _num(comparacao["dy_rms"])],
                ["Maior desvio de pressão", f"{pior_dp * 100:.2f} % em x₁ = {x_dp:g}"],
                ["Maior desvio de y₁", f"{_num(pior_dy)} em x₁ = {x_dy:g}"],
            ],
            classe="chave",
        ))
        corpo.append(_tabela(
            ["x₁", "P exp. (kPa)", "P calc. (kPa)", "ΔP (%)", "y₁ exp.", "y₁ calc.", "Δy"],
            [
                [f"{x:g}", _num(pe, 3), _num(pc, 3), f"{dp:.2f}", _num(ye), _num(yc), _num(dy)]
                for x, pe, pc, dp, ye, yc, dy in comparacao["linhas"]
            ],
        ))
        corpo.append(
            '<p class="nota">ΔP é relativo (em %) e Δy é absoluto, ambos como raiz '
            "da média dos quadrados, reportados separados porque medem partes "
            "diferentes da física. Este relatório não classifica o ajuste como bom "
            "ou ruim: a análise crítica cabe a quem o lê.</p>"
        )

    # 5. Gráficos
    corpo.append('<section class="bloco"><h2>Diagrama P-x-y</h2>')
    liquido_exp = [(x, p) for p, x, _ in pontos]
    vapor_exp = [(y, p) for p, _, y in pontos]
    liquido_calc = sorted(zip(curva["x1"], curva["P_kPa"]))
    vapor_calc = sorted(zip(curva["y1"], curva["P_kPa"]))
    series_pxy = [
        {"tipo": "linha", "cor": COR_LIQUIDO, "pontos": liquido_calc},
        {"tipo": "linha", "cor": COR_VAPOR, "pontos": vapor_calc},
        {"tipo": "quadrado", "cor": COR_LIQUIDO, "pontos": liquido_exp},
        {"tipo": "circulo", "cor": COR_VAPOR, "pontos": vapor_exp},
    ]
    itens = [
        ("linha", COR_LIQUIDO, "Líquido, modelo"),
        ("linha", COR_VAPOR, "Vapor, modelo"),
    ]
    if pontos:
        itens += [
            ("quadrado", COR_LIQUIDO, "Líquido, tabela"),
            ("circulo", COR_VAPOR, "Vapor, tabela"),
        ]
    if comparacao:
        xs = sorted({x for _, x, _ in pontos})
        # linha = (x1, P_exp, P_calc, ΔP %, y_exp, y_calc, Δy) → (P_calc, y_calc)
        calc = {linha[0]: (linha[2], linha[5]) for linha in comparacao["linhas"]}
        series_pxy += [
            {"tipo": "quadrado_vazado", "cor": COR_LIQUIDO,
             "pontos": [(x, calc[x][0]) for x in xs]},
            {"tipo": "circulo_vazado", "cor": COR_VAPOR,
             "pontos": [(calc[x][1], calc[x][0]) for x in xs]},
        ]
        itens += [
            ("quadrado_vazado", COR_LIQUIDO, "Líquido, modelo nos x₁ da tabela"),
            ("circulo_vazado", COR_VAPOR, "Vapor, modelo nos x₁ da tabela"),
        ]
    corpo.append(_legenda(itens))
    corpo.append(
        '<div class="grafico">'
        + svg_grafico("x₁, y₁ (fração molar)", "P (kPa)", series_pxy)
        + "</div></section>"
    )

    corpo.append('<section class="bloco"><h2>Coeficientes de atividade (ln γ)</h2>')
    ln1 = [math.log(g) for g in curva["gamma1"]]
    ln2 = [math.log(g) for g in curva["gamma2"]]
    series_gamma = [
        {"tipo": "linha", "cor": COR_GAMMA1, "pontos": list(zip(curva["x1"], ln1))},
        {"tipo": "linha", "cor": COR_GAMMA2, "pontos": list(zip(curva["x1"], ln2))},
        {"tipo": "circulo", "cor": COR_GAMMA1, "pontos": [(x, g1) for x, g1, _ in ln_exp]},
        {"tipo": "circulo", "cor": COR_GAMMA2, "pontos": [(x, g2) for x, _, g2 in ln_exp]},
    ]
    itens_g = [
        ("linha", COR_GAMMA1, "ln γ₁, modelo"),
        ("linha", COR_GAMMA2, "ln γ₂, modelo"),
    ]
    if ln_exp:
        itens_g += [
            ("circulo", COR_GAMMA1, "ln γ₁, tabela"),
            ("circulo", COR_GAMMA2, "ln γ₂, tabela"),
        ]
    corpo.append(_legenda(itens_g))
    corpo.append(
        '<div class="grafico">'
        + svg_grafico("x₁ (fração molar)", "ln γ", series_gamma)
        + "</div>"
    )
    if ln_exp:
        corpo.append(
            '<p class="nota">ln γ da tabela: método indireto, γᵢ = yᵢ·P/(xᵢ·Pᵢˢᵃᵗ), '
            "só para 0,10 ≤ x₁ ≤ 0,90 (nas pontas o erro de medida é amplificado).</p>"
        )
    corpo.append("</section>")

    # 6. Avisos
    avisos = dados.get("avisos") or []
    if avisos:
        corpo.append("<h2>Avisos do aplicativo</h2>")
        corpo.extend(f'<div class="aviso">{e(a)}</div>' for a in avisos)

    return (
        '<!DOCTYPE html>\n<html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Relatório VLE — {comp1}/{comp2} a {T_C:g} °C</title>"
        f"<style>{_CSS}</style></head><body>"
        "<header><h1>Relatório — VLE Interativo</h1>"
        "<p>Equilíbrio líquido-vapor com modelos de Gᴱ · "
        f'{e(str(dados["gerado_em"]))}</p></header>'
        + "".join(corpo)
        + "<footer>Gerado pelo VLE Interativo (TCC de Engenharia Química, UFC). "
        "Os dados experimentais são os digitados ou importados pelo usuário; "
        "pressões de vapor da biblioteca thermo; parâmetros de interação conforme "
        "a origem indicada acima.</footer></body></html>"
    )
