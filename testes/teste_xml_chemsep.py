"""
Alerta de atualização do XML interno do ChemSep (2026-10-07).

O UNIQUAC usa os r/q do XML de compostos puros do ChemSep que vem empacotado
no `chemicals` (dado interno do pacote, não interface). Este teste falha, com o
motivo, se a versão do `chemicals` ou o XML (nome e conteúdo) forem diferentes
dos validados — ou seja, sempre que uma atualização de dependência puder ter
alterado os r/q. Também confere que o alerta de execução (RuntimeWarning em
`calculos.gemini`) dispara quando algo diverge.

Se falhar depois de uma atualização do `chemicals`/`thermo`: rode
`PYTHONPATH=. .venv/bin/python testes/teste_banco_ipdb.py` (o UNIQUAC contra o
`thermo.UNIQUAC`); estando correto, atualize as constantes *_VALIDADO em
`calculos/gemini.py`.

Roda a partir da raiz: PYTHONPATH=. .venv/bin/python testes/teste_xml_chemsep.py
"""

import warnings

from calculos import gemini


def teste_xml_como_validado():
    alertas = gemini.verificar_xml_chemsep()
    if alertas:
        print("ALERTA: o XML interno do ChemSep (r/q do UNIQUAC) pode ter mudado:")
        for a in alertas:
            print("  -", a)
        print("Revalidar o UNIQUAC (testes/teste_banco_ipdb.py) e atualizar as constantes "
              "*_VALIDADO em calculos/gemini.py.")
        raise SystemExit(1)
    print("OK: chemicals e XML do ChemSep iguais aos validados para o UNIQUAC.")


def teste_alerta_dispara(versao_falsa="0.0.0"):
    """Simula uma atualização do pacote e confere o alerta, sem tocar no arquivo."""
    original = gemini.CHEMICALS_VERSAO_VALIDADA
    gemini.CHEMICALS_VERSAO_VALIDADA = versao_falsa
    gemini._tabela_rq_chemsep.cache_clear()
    try:
        with warnings.catch_warnings(record=True) as capturados:
            warnings.simplefilter("always")
            tabela = gemini._tabela_rq_chemsep()
        assert any(issubclass(w.category, RuntimeWarning) and "chemicals" in str(w.message) for w in capturados), \
            "o alerta de atualização não disparou"
        assert tabela, "mesmo com alerta, a tabela de r/q deve continuar sendo carregada"
    finally:
        gemini.CHEMICALS_VERSAO_VALIDADA = original
        gemini._tabela_rq_chemsep.cache_clear()
    print("OK: o alerta dispara quando a versão do chemicals diverge (e o UNIQUAC segue funcionando).")


if __name__ == "__main__":
    teste_xml_como_validado()
    teste_alerta_dispara()
    print("Todos os testes passaram.")
