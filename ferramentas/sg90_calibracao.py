# -*- coding: utf-8 -*-
# =====================================================================
# SG90 - da varredura medida para a calibracao
# =====================================================================
# Entrada: um CSV com uma linha por parada da varredura, com as colunas
#     largura_us    largura do pulso enviada pelo Arduino
#     sentido       "sobe" ou "desce"
#     angulo_graus  angulo MEDIDO do braco (Tracker, medidor de angulo
#                   ou transferidor)
# O arquivo que o sketch imprime ja tem as duas primeiras colunas; a
# terceira e preenchida com a medicao do video.
#
# Saida: a faixa util, a zona morta, a histerese e as duas constantes
# que voltam para o sketch -- us = usEmZeroGrau + usPorGrau * graus.
#
# Rodar:  python sg90_calibracao.py varredura.csv
# =====================================================================
import os
import sys

import numpy as np
import pandas as pd

# Variacao angular minima, em graus, para considerar que o braco de
# fato andou entre duas larguras vizinhas. Abaixo disso a diferenca e
# ruido de medicao.
LIMIAR_MOVIMENTO = 0.25

# Fracao da inclinacao media abaixo da qual o trecho e considerado
# saturado (o braco bateu no batente e nao responde mais ao pulso).
FRACAO_SATURACAO = 0.25


def ler(caminho):
    """Le o CSV aceitando ; ou , e decimal com virgula."""
    tabela = pd.read_csv(caminho, sep=None, engine="python",
                         comment="#", decimal=",")
    if tabela.shape[1] == 1:          # decimal era ponto
        tabela = pd.read_csv(caminho, sep=None, engine="python", comment="#")
    faltando = {"largura_us", "angulo_graus"} - set(tabela.columns)
    if faltando:
        raise SystemExit(
            f"Faltam colunas no arquivo: {', '.join(sorted(faltando))}.\n"
            f"Encontradas: {', '.join(tabela.columns)}")
    if "sentido" not in tabela:
        tabela["sentido"] = "sobe"
    return tabela.dropna(subset=["largura_us", "angulo_graus"])


def curva_media(tabela):
    """Uma leitura por largura de pulso.

    A varredura passa duas vezes por cada largura (subindo e descendo).
    Deixar as duas na mesma serie cria pontos com o mesmo x, e a
    derivada numerica usada para achar o batente divide por zero. A
    media das duas desloca a curva pela metade da histerese, que e uma
    constante: nao muda a inclinacao, que e o que o ajuste procura.
    """
    media = (tabela.groupby("largura_us")["angulo_graus"]
             .mean().sort_index())
    return media.index.to_numpy(float), media.to_numpy(float)


def faixa_util(largura, angulo):
    """Trecho em que o servo ainda responde ao pulso.

    Nas pontas o braco encosta no batente: o pulso continua mudando e o
    angulo nao. Incluir esse trecho no ajuste achata a reta e subestima
    o ganho, entao ele e cortado antes.
    """
    ordem = np.argsort(largura)
    largura, angulo = largura[ordem], angulo[ordem]
    if largura.size < 5:
        return largura, angulo, (float(largura.min()), float(largura.max()))

    inclinacao = np.gradient(angulo, largura)
    referencia = np.median(np.abs(inclinacao))
    responde = np.abs(inclinacao) > FRACAO_SATURACAO * referencia
    indices = np.flatnonzero(responde)
    if indices.size < 3:
        return largura, angulo, (float(largura.min()), float(largura.max()))
    corte = slice(int(indices[0]), int(indices[-1]) + 1)
    return (largura[corte], angulo[corte],
            (float(largura[corte][0]), float(largura[corte][-1])))


def zona_morta(largura, angulo):
    """Quanto o pulso precisa mudar para o braco sair do lugar, em us.

    Medida como o intervalo tipico ENTRE movimentos sucessivos, e nao
    como o trecho parado: amostrando de 5 em 5 us um servo que anda de
    10 em 10, o trecho parado mede 5 us e o intervalo entre movimentos
    mede 10 -- e e o segundo que diz qual passo vale a pena comandar.
    """
    ordem = np.argsort(largura)
    largura, angulo = largura[ordem], angulo[ordem]
    andou = np.abs(np.diff(angulo)) >= LIMIAR_MOVIMENTO
    movimentos = int(np.count_nonzero(andou))
    if movimentos < 3:
        return 0.0
    # Largura varrida dividida pelo numero de movimentos. A mediana dos
    # intervalos parece mais natural, mas a amostragem raramente cai em
    # fase com os degraus do servo e os intervalos saem alternados
    # (5, 15, 5, 15...), o que desloca a mediana para uma das pontas.
    return float((largura[-1] - largura[0]) / movimentos)


def ajustar(largura, angulo):
    """angulo = a * largura + b, com R2."""
    a, b = np.polyfit(largura, angulo, 1)
    previsto = a * largura + b
    total = np.sum((angulo - angulo.mean()) ** 2)
    r2 = float(1 - np.sum((angulo - previsto) ** 2) / total) if total else np.nan
    return float(a), float(b), r2


def histerese(tabela):
    """Diferenca media de angulo entre subir e descer na mesma largura.

    E a folga da engrenagem. Entra no erro de posicao de quem comanda
    sempre num sentido so, e explica parte da dispersao entre
    repeticoes.
    """
    sentidos = set(tabela["sentido"].astype(str).str.lower())
    if not {"sobe", "desce"} <= sentidos:
        return None
    pivo = (tabela.assign(sentido=tabela["sentido"].str.lower())
            .pivot_table(index="largura_us", columns="sentido",
                         values="angulo_graus", aggfunc="mean")
            .dropna())
    if pivo.empty:
        return None
    diferenca = pivo["desce"] - pivo["sobe"]
    return {"media_graus": float(diferenca.mean()),
            "maxima_graus": float(diferenca.abs().max()),
            "n": int(diferenca.size)}


def analisar(tabela):
    largura, angulo = curva_media(tabela)
    util_l, util_a, faixa = faixa_util(largura, angulo)
    a, b, r2 = ajustar(util_l, util_a)

    # Inversao: us = (graus - b) / a. E esta a forma usada no sketch.
    us_por_grau = 1.0 / a
    us_em_zero = -b / a
    morta = zona_morta(util_l, util_a)
    return {
        "faixa_util_us": faixa,
        "graus_na_faixa": (float(a * faixa[0] + b), float(a * faixa[1] + b)),
        "graus_por_us": a,
        "r2": r2,
        "us_por_grau": us_por_grau,
        "us_em_zero_grau": us_em_zero,
        "us_em_180_graus": us_em_zero + 180.0 * us_por_grau,
        "zona_morta_us": morta,
        "resolucao_graus": abs(a) * morta,
        "histerese": histerese(tabela),
        "n_pontos": int(util_l.size),
    }


def imprimir(resultado):
    faixa = resultado["faixa_util_us"]
    graus = resultado["graus_na_faixa"]
    print("\n=== FAIXA UTIL ===")
    print(f"  pulso  : {faixa[0]:.0f} a {faixa[1]:.0f} us")
    print(f"  angulo : {graus[0]:.1f}° a {graus[1]:.1f}° "
          f"({abs(graus[1] - graus[0]):.1f}° de curso)")
    print(f"  ajuste : {resultado['graus_por_us']:.5f} °/us, "
          f"R² = {resultado['r2']:.4f}  ({resultado['n_pontos']} pontos)")

    print("\n=== RESOLUCAO ===")
    print(f"  zona morta        : {resultado['zona_morta_us']:.1f} us")
    print(f"  menor passo util  : {resultado['resolucao_graus']:.2f}°")
    print("  Comandar passos menores que isso nao move o braco: o pulso "
          "muda e o\n  servo ignora. E o piso da exatidao deste atuador.")

    hist = resultado["histerese"]
    if hist:
        print("\n=== HISTERESE (folga da engrenagem) ===")
        print(f"  media  : {hist['media_graus']:+.2f}°")
        print(f"  maxima : {hist['maxima_graus']:.2f}°  "
              f"({hist['n']} larguras medidas nos dois sentidos)")
        print("  Chegar sempre pelo mesmo lado elimina esta parcela do erro.")

    print("\n=== PARA COLAR NO SKETCH ===")
    print(f"  float usPorGrau   = {resultado['us_por_grau']:.4f};")
    print(f"  float usEmZeroGrau = {resultado['us_em_zero_grau']:.1f};")
    print(f"  // 0° -> {resultado['us_em_zero_grau']:.0f} us ; "
          f"180° -> {resultado['us_em_180_graus']:.0f} us")
    padrao_por_grau = (2400.0 - 544.0) / 180.0
    desvio = 100.0 * (resultado["us_por_grau"] / padrao_por_grau - 1.0)
    print(f"  O padrao da biblioteca Servo e {padrao_por_grau:.4f} us/grau "
          f"({desvio:+.1f}% de diferenca).")
    if abs(desvio) > 2.0:
        print("  Essa diferenca e exatamente o erro de ganho que aparece "
              "no mapa angular:\n  o braco entrega menos grau do que foi "
              "pedido porque a conversao\n  graus->us era a da biblioteca, "
              "nao a deste servo.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(f"uso: python {os.path.basename(__file__)} "
                         f"varredura.csv")
    imprimir(analisar(ler(sys.argv[1])))
