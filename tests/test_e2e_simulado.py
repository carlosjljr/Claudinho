# -*- coding: utf-8 -*-
"""Teste ponta a ponta de `executar()` com um cliente gspread simulado.

Cobre o que os testes unitarios nao alcancam: leitura em lote, descarte
de abas fora da analise, cache em disco, geracao das figuras e
exportacao das metricas. Os dados sao formatados exatamente como o
Tracker exporta ("3,07E+02", tres algarismos significativos), entao o
teste tambem verifica que a quantizacao nao introduz vies nas metricas.

Rodar com:  python tests/test_e2e_simulado.py
"""

import os
import shutil
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dados_sinteticos import gerar_ensaio  # noqa: E402
from proj1_analise import Config, executar, passo_da_categoria  # noqa: E402

FALHAS = []


def verificar(condicao, mensagem):
    if condicao:
        print(f"  ok   {mensagem}")
    else:
        print(f"  FALHA {mensagem}")
        FALHAS.append(mensagem)


PLANILHAS = ("PROJ 1_PE01", "PROJ 1_PE10")
CATEGORIAS = ("I_S1_P10", "I_S2_P05")
RAIOS = {
    ("PROJ 1_PE01", "I_S1_P10"): 146.74 + 158.53,
    ("PROJ 1_PE01", "I_S2_P05"): 167.19,
    ("PROJ 1_PE10", "I_S1_P10"): 120.24 + 118.08,
    ("PROJ 1_PE10", "I_S2_P05"): 110.91,
}
CHAMADAS = {"open": 0, "worksheets": 0, "batch": 0}


def formatar(valor):
    """Reproduz o formato do Tracker exportado em pt-BR."""
    return f"{valor:.2E}".replace(".", ",")


class Aba:
    def __init__(self, title):
        self.title = title


class PlanilhaFalsa:
    def __init__(self, title):
        self.title = title
        self.tabelas = {}
        for categoria in CATEGORIAS:
            for repeticao in (1, 2, 3):
                t, x, y = gerar_ensaio(
                    passo=passo_da_categoria(categoria),
                    theta0=11.9 + 3 * repeticao,
                    raio=RAIOS[(title, categoria)],
                    t_comando=0.5 + 0.7 * repeticao,
                    duracao=9.0 + 0.5 * repeticao,
                    sentido=-1 if "S2" in categoria else 1,
                    ruido=0.05,
                    semente=repeticao + 10 * len(categoria) + len(title),
                )
                linhas = [["massa_A", "", ""], ["t", "x", "y"]]
                linhas += [
                    [formatar(a), formatar(b), formatar(c)] for a, b, c in zip(t, x, y)
                ]
                linhas.append([""])  # linha curta, como o Sheets devolve
                self.tabelas[f"{categoria}_{repeticao}"] = linhas
        # aba que existe na planilha mas nao esta na analise
        self.tabelas["III_D1000_1"] = [["massa_A", "", ""], ["t", "x", "y"]]

    def worksheets(self):
        CHAMADAS["worksheets"] += 1
        return [Aba(nome) for nome in self.tabelas]

    def values_batch_get(self, ranges):
        CHAMADAS["batch"] += 1
        blocos = []
        for faixa in ranges:
            nome = faixa.split("!")[0].strip("'")
            blocos.append({"range": faixa, "values": self.tabelas[nome]})
        return {"valueRanges": blocos}


class ClienteFalso:
    def open(self, nome):
        CHAMADAS["open"] += 1
        if nome not in PLANILHAS:
            raise KeyError(nome)
        return PlanilhaFalsa(nome)


base = tempfile.mkdtemp(prefix="proj1_e2e_")
try:
    cfg = Config(
        pasta_drive=base,
        planilhas=PLANILHAS,
        categorias=CATEGORIAS,
        mostrar_figuras=False,
        formatos_figura=("png",),
    )

    print("\n[1] Execucao completa")
    resultado = executar(cfg, cliente=ClienteFalso())
    verificar(
        len(resultado["ensaios"]) == 12,
        f"12 ensaios carregados ({len(resultado['ensaios'])})",
    )
    total = sum(CHAMADAS.values())
    verificar(
        total == 3 * len(PLANILHAS),
        f"{total} chamadas a API para {len(PLANILHAS)} planilhas x 6 abas "
        f"({CHAMADAS})",
    )

    print("\n[2] Geometria recuperada dos dados quantizados")
    for ensaio in resultado["ensaios"]:
        esperado = RAIOS[(ensaio.planilha, ensaio.categoria)]
        desvio = abs(ensaio.raio - esperado)
        if desvio > 1.0:
            verificar(False, f"{ensaio.rotulo}: raio {ensaio.raio:.2f} x {esperado:.2f}")
            break
    else:
        verificar(True, "raio de todos os 12 ensaios dentro de 1 mm do nominal")
    verificar(
        all(e.algarismos_significativos == 3 for e in resultado["ensaios"]),
        "quantizacao de 3 algarismos significativos detectada em todos",
    )

    print("\n[3] Metricas sem vies")
    metricas = resultado["metricas_por_degrau"]
    erro_max = metricas["erro_graus"].abs().max()
    verificar(erro_max < 0.3, f"erro de regime maximo: {erro_max:.3f} graus")
    sobressinal = metricas["sobressinal_percentual"].mean()
    verificar(
        3.0 < sobressinal < 12.0,
        f"sobressinal medio coerente com o gerador: {sobressinal:.1f}%",
    )
    for (planilha, categoria), grupo in metricas.groupby(["planilha", "categoria"]):
        inclinacao = np.polyfit(grupo["degrau"], grupo["erro_graus"], 1)[0]
        if abs(inclinacao) > 0.03:
            verificar(
                False, f"{planilha}/{categoria}: erro deriva {inclinacao:+.4f}°/degrau"
            )
            break
    else:
        verificar(True, "nenhum grupo acumula erro degrau a degrau")

    print("\n[4] Saidas geradas")
    pastas = ("TRAJETORIA_XY", "ANGULO_TEMPO", "ANGULO_ZOOM", "MEDIA_DESVIO")
    for pasta in pastas:
        caminho = os.path.join(cfg.pasta_resultados, pasta)
        n = len(os.listdir(caminho)) if os.path.isdir(caminho) else 0
        verificar(n == 4, f"{pasta}: {n} figuras (4 grupos)")
    for arquivo in (
        "metricas_por_degrau.csv",
        "metricas_por_ensaio.csv",
        "resumo_por_categoria.csv",
    ):
        verificar(
            os.path.exists(os.path.join(cfg.pasta_resultados, arquivo)),
            f"{arquivo} exportado",
        )

    print("\n[5] Cache dispensa a API")
    CHAMADAS.update({"open": 0, "worksheets": 0, "batch": 0})
    segunda = executar(cfg, cliente=None)
    verificar(sum(CHAMADAS.values()) == 0, "segunda execucao nao chamou a API")
    verificar(
        len(segunda["ensaios"]) == len(resultado["ensaios"]),
        "mesma quantidade de ensaios vinda do cache",
    )
    verificar(
        np.allclose(
            segunda["metricas_por_degrau"]["erro_graus"],
            resultado["metricas_por_degrau"]["erro_graus"],
        ),
        "metricas identicas as da primeira execucao",
    )
finally:
    shutil.rmtree(base, ignore_errors=True)

print()
if FALHAS:
    print(f"{len(FALHAS)} verificacao(oes) falharam:")
    for item in FALHAS:
        print(f"  - {item}")
    sys.exit(1)
print("Todas as verificacoes passaram.")
