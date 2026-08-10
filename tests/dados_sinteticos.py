# -*- coding: utf-8 -*-
"""Gerador de ensaios sinteticos com parametros conhecidos.

Serve para validar o pipeline sem depender do Colab nem das planilhas:
como o angulo de repouso, o instante do comando, o passo e o centro de
rotacao sao escolhidos aqui, da para conferir se a analise os recupera.
"""

import numpy as np


def resposta_degrau(tau, tempo_degrau, amplitude, wn=28.0, zeta=0.65):
    """Resposta de 2a ordem subamortecida a um degrau em `tempo_degrau`."""
    dt = np.clip(tau - tempo_degrau, 0.0, None)
    wd = wn * np.sqrt(1.0 - zeta**2)
    envelope = np.exp(-zeta * wn * dt)
    oscilacao = np.cos(wd * dt) + (zeta / np.sqrt(1 - zeta**2)) * np.sin(wd * dt)
    saida = amplitude * (1.0 - envelope * oscilacao)
    return np.where(tau >= tempo_degrau, saida, 0.0)


def gerar_ensaio(
    passo=10.0,
    theta0=11.9,
    centro=(0.0, 0.0),
    raio=306.32,
    t_comando=2.0,
    duracao=14.0,
    fps=30.0,
    sentido=1,
    ruido=0.02,
    semente=0,
    n_degraus=None,
):
    """Cria (t, x, y) de um ensaio com escada de degraus conhecida.

    A sequencia comandada e a mesma em todas as repeticoes (o servo
    executa o programa inteiro); o que muda entre elas e o instante do
    comando e o trecho de video gravado.
    """
    rng = np.random.default_rng(semente)
    t = np.arange(0.0, duracao, 1.0 / fps)
    tau = t - t_comando

    if n_degraus is None:
        n_degraus = int(180.0 / passo)

    angulo = np.zeros_like(t)
    for k in range(n_degraus):
        angulo += resposta_degrau(tau, k * 1.0, passo)

    angulo_total = theta0 + sentido * angulo
    angulo_total += rng.normal(0.0, ruido, angulo_total.size)

    radianos = np.deg2rad(angulo_total)
    x = centro[0] + raio * np.cos(radianos)
    y = centro[1] + raio * np.sin(radianos)
    return t, x, y
