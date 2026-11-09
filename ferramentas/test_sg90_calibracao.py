# -*- coding: utf-8 -*-
"""Confere a analise da varredura contra um SG90 simulado.

Gera uma varredura com faixa, zona morta e histerese CONHECIDAS e
verifica se a analise recupera cada uma delas. Sem isto nao ha como
saber se um numero estranho vindo do ensaio e do servo ou do programa.

Rodar com:  python test_sg90_calibracao.py
"""
import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sg90_calibracao import analisar, ler  # noqa: E402

# Verdade injetada
US_EM_0, US_EM_180 = 700.0, 2300.0
ZONA_MORTA, HISTERESE = 10.0, 1.2
US_POR_GRAU = (US_EM_180 - US_EM_0) / 180.0

FALHAS = []


def verificar(condicao, mensagem):
    print(("  ok   " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


def gerar(caminho, passo=5, ruido=0.05, semente=3):
    rng = np.random.default_rng(semente)
    linhas = []
    for sentido in ("sobe", "desce"):
        larguras = (np.arange(600, 2401, passo) if sentido == "sobe"
                    else np.arange(2400, 599, -passo))
        for us in larguras:
            efetivo = np.clip(float(us), US_EM_0, US_EM_180)   # batente
            degrau = US_EM_0 + ZONA_MORTA * np.round(
                (efetivo - US_EM_0) / ZONA_MORTA)              # zona morta
            angulo = (degrau - US_EM_0) / US_POR_GRAU
            if sentido == "desce":
                angulo += HISTERESE                            # folga
            linhas.append({"largura_us": us, "sentido": sentido,
                           "angulo_graus": round(angulo + rng.normal(0, ruido), 2)})
    pd.DataFrame(linhas).to_csv(caminho, sep=";", index=False)


with tempfile.TemporaryDirectory() as pasta:
    caminho = os.path.join(pasta, "varredura.csv")
    gerar(caminho)
    r = analisar(ler(caminho))

    print("\n[1] Faixa útil (o batente das pontas tem de ficar de fora)")
    inicio, fim = r["faixa_util_us"]
    verificar(abs(inicio - US_EM_0) <= 6, f"início {inicio:.0f} ≈ {US_EM_0:.0f} us")
    verificar(abs(fim - US_EM_180) <= 6, f"fim {fim:.0f} ≈ {US_EM_180:.0f} us")

    print("\n[2] Conversão graus -> microssegundos")
    erro = 100 * abs(r["us_por_grau"] / US_POR_GRAU - 1)
    verificar(erro < 0.5,
              f"{r['us_por_grau']:.4f} us/grau contra {US_POR_GRAU:.4f} "
              f"({erro:.2f}% de erro)")
    verificar(r["r2"] > 0.99, f"R² = {r['r2']:.4f}")
    # A media entre subir e descer desloca o zero em meia histerese, o
    # que em microssegundos da ~5 us: e esperado, nao e erro.
    desvio_zero = abs(r["us_em_zero_grau"] - US_EM_0)
    verificar(desvio_zero < 0.6 * HISTERESE * US_POR_GRAU + 2,
              f"0° em {r['us_em_zero_grau']:.1f} us "
              f"(meia histerese abaixo de {US_EM_0:.0f}, como esperado)")

    print("\n[3] Zona morta")
    verificar(abs(r["zona_morta_us"] - ZONA_MORTA) < 1.5,
              f"{r['zona_morta_us']:.1f} us contra {ZONA_MORTA:.1f}")

    print("\n[4] Histerese")
    hist = r["histerese"]
    verificar(hist is not None and abs(hist["media_graus"] - HISTERESE) < 0.15,
              f"{hist['media_graus']:.2f}° contra {HISTERESE:.2f}°")

print()
if FALHAS:
    print(f"{len(FALHAS)} verificação(ões) falharam.")
    sys.exit(1)
print("Todas as verificações passaram.")
