# -*- coding: utf-8 -*-
"""Testa PROJ1_COLAB.py com um cliente do Sheets simulado."""
import os, shutil, sys, tempfile
import matplotlib; matplotlib.use("Agg")
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO); sys.path.insert(0, os.path.join(REPO, "tests"))
from dados_sinteticos import gerar_ensaio

import PROJ1_COLAB as P

BASE = tempfile.mkdtemp(prefix="colab_")
P.PASTA_DRIVE = BASE
P.PASTA_RESULTADOS = os.path.join(BASE, "RESULTADOS")
P.PASTA_CACHE = os.path.join(BASE, "CACHE_DADOS")
P.MOSTRAR_FIGURAS = False
P.FORMATOS = ("png",)

RAIOS = {}
for proto, cats in P.ELOS.items():
    for cat, params in cats.items():
        RAIOS[(proto, cat)] = (params.get("AB", 0.0) if "S1" in cat else 0.0) + params["BC"]

CHAMADAS = {"open": 0, "worksheets": 0, "batch": 0}
fmt = lambda v: v   # UNFORMATTED_VALUE devolve numero, nao texto


class Aba:
    def __init__(self, t): self.title = t


class Planilha:
    def __init__(self, arquivo):
        proto = next(k for k, v in P.PLANILHAS.items() if v == arquivo)
        self.title = arquivo
        self.tabelas = {}
        for cat in P.CATEGORIAS:
            for rep in (1, 2, 3):
                t, x, y = gerar_ensaio(
                    passo=P.passo_da_categoria(cat),
                    theta0=11.9 + 3 * rep,
                    raio=RAIOS[(proto, cat)],
                    t_comando=0.5 + 0.7 * rep,
                    duracao=12.0 + 0.5 * rep,
                    sentido=-1 if "S2" in cat else 1,
                    ruido=0.05, semente=rep + len(cat) + len(proto),
                )
                linhas = [["massa_A", "", ""], ["t", "x", "y"]]
                linhas += [[fmt(a), fmt(b), fmt(c)] for a, b, c in zip(t, x, y)]
                linhas.append([""])
                self.tabelas[f"{cat}_{rep}"] = linhas
        self.tabelas["ABA_FORA_DA_ANALISE_1"] = [["massa_A", "", ""], ["t", "x", "y"]]

    def worksheets(self):
        CHAMADAS["worksheets"] += 1
        return [Aba(n) for n in self.tabelas]

    def values_batch_get(self, ranges, params=None):
        CHAMADAS["batch"] += 1
        # Sem UNFORMATTED_VALUE a API devolveria o texto formatado com 3
        # algarismos significativos, que era a origem da quantizacao.
        assert (params or {}).get("valueRenderOption") == "UNFORMATTED_VALUE", \
            "a leitura precisa pedir valores nao formatados"
        return {"valueRanges": [
            {"values": self.tabelas[f.split("!")[0].strip("'")]} for f in ranges]}


class Cliente:
    def open(self, nome):
        CHAMADAS["open"] += 1
        if nome not in P.PLANILHAS.values():
            raise KeyError(nome)
        return Planilha(nome)


try:
    res = P.executar_trajetoria(cliente=Cliente())

    print("\n=== VERIFICACOES ===")
    falhas = []
    def check(cond, msg):
        print(("  ok   " if cond else "  FALHA ") + msg)
        if not cond: falhas.append(msg)

    check(len(res["ensaios"]) == 36, f"36 ensaios (2 prototipos x 6 cat x 3) -> {len(res['ensaios'])}")
    check(sum(CHAMADAS.values()) == 6, f"6 chamadas a API {CHAMADAS}")
    protos = sorted({e["prototipo"] for e in res["ensaios"]})
    check(protos == ["PE01", "PE02"], f"so PE01 e PE02: {protos}")

    md = res["metricas_por_degrau"]
    p10 = md[md.categoria.str.endswith("P10")]
    check(p10["tempo_assentamento_s"].notna().all(), "degraus de 10 graus acomodaram (faixa acima da resolucao)")
    check(md["erro_regime_graus"].abs().max() < 0.5, f"erro de regime max {md['erro_regime_graus'].abs().max():.3f} deg")

    r = res["resumo_por_categoria"]
    t01 = r[r.prototipo=="PE01"]["t_assentamento_medio_s"].mean()
    t02 = r[r.prototipo=="PE02"]["t_assentamento_medio_s"].mean()
    check(np.isfinite(t01) and np.isfinite(t02),
          f"tempo de assentamento medio por prototipo: PE01={1000*t01:.0f} ms, PE02={1000*t02:.0f} ms")

    check("ganho_servo" in r.columns and r["ganho_servo"].notna().all(),
          f"ganho do servo estimado por categoria: "
          f"{r['ganho_servo'].min():.3f}-{r['ganho_servo'].max():.3f}")

    pe = res["metricas_por_ensaio"]
    check({"t_assentamento_medio_s","t_assentamento_desvio_s","t_assentamento_max_s",
           "degraus_sem_assentar"}.issubset(pe.columns), "colunas de assentamento por repeticao")

    print("\n=== ARQUIVOS ===")
    for raiz, _, arqs in sorted(os.walk(P.PASTA_RESULTADOS)):
        rel = os.path.relpath(raiz, P.PASTA_RESULTADOS)
        if arqs: print(f"  {rel}: {len(arqs)} arquivos")

    print("\n=== DETECCAO DE CADENCIA E FAIXA DE ACOMODACAO ===")
    # A cadencia sai dos proprios dados, sem supor PERIODO_DEGRAU_S.
    erros_cadencia = []
    for e in res["ensaios"]:
        inst = P.instantes_dos_degraus(e["tau"], e["theta_rel"], e["passo"])
        if inst.size >= 2:
            erros_cadencia.append(abs(np.median(np.diff(inst)) - P.PERIODO_DEGRAU_S))
    check(len(erros_cadencia) == len(res["ensaios"]),
          f"cadencia detectada em {len(erros_cadencia)}/{len(res['ensaios'])} ensaios")
    check(max(erros_cadencia) < 0.06,
          f"cadencia medida bate com 1,0 s (erro max {max(erros_cadencia):.3f} s)")

    check(P.instantes_dos_degraus(np.arange(0, 3, 1/30), np.zeros(90), 10.0).size == 0,
          "serie sem movimento devolve vazio em vez de levantar excecao")

    P.BANDA_MODO = "passo"
    faixa_passo = P.largura_da_faixa(10.0, 100.0)
    P.BANDA_MODO = "valor_final"
    faixa_final = P.largura_da_faixa(10.0, 100.0)
    P.BANDA_MODO = "passo"
    check(faixa_passo == 0.5 and faixa_final == 5.0,
          f"modos de faixa: passo=±{faixa_passo}deg, valor_final=±{faixa_final}deg")

    # 2a execucao usando cache
    CHAMADAS.update({"open":0,"worksheets":0,"batch":0})
    P.executar_trajetoria(cliente=None)
    check(sum(CHAMADAS.values()) == 0, "2a execucao nao chamou a API (cache)")

    print()
    sys.exit(1 if falhas else 0)
finally:
    shutil.rmtree(BASE, ignore_errors=True)
