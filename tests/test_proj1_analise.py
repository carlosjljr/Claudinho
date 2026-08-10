# -*- coding: utf-8 -*-
"""Validacao das funcoes de analise com dados sinteticos.

Nao exige Google Colab nem acesso as planilhas: gera um ensaio com
parametros conhecidos e verifica se o pipeline recupera esses parametros.

Rodar com:  python tests/test_proj1_analise.py
"""

import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from proj1_analise import (  # noqa: E402
    Config,
    Ensaio,
    ajustar_circulo,
    ajustar_centro_raio_fixo,
    algarismos_significativos,
    angulo_desenrolado,
    curva_desejada_ensaio,
    detectar_inicio,
    estimar_centro,
    extrair_txy,
    grade_comum,
    metricas_globais,
    metricas_por_degrau,
    passo_da_categoria,
    preparar_ensaio,
    raio_nominal,
    resolucao_angular,
    trajetoria_desejada,
    varredura_estimada,
)

# O Tracker exporta em notacao cientifica com 3 algarismos significativos
# ("3,07E+02"), entao os dados chegam quantizados. Varios testes usam
# esta funcao para reproduzir fielmente essa perda de precisao.
quantizar = np.vectorize(lambda v: float(f"{v:.2E}"))

from dados_sinteticos import gerar_ensaio  # noqa: E402

FALHAS = []


def verificar(condicao, mensagem):
    if condicao:
        print(f"  ok   {mensagem}")
    else:
        print(f"  FALHA {mensagem}")
        FALHAS.append(mensagem)


def montar(cfg, planilha="PROJ 1_PE01", categoria="I_S1_P10", repeticao=1, **kwargs):
    t, x, y = gerar_ensaio(passo=passo_da_categoria(categoria), **kwargs)
    ensaio = Ensaio(
        planilha=planilha,
        categoria=categoria,
        repeticao=repeticao,
        t=t,
        x=x,
        y=y,
        passo=passo_da_categoria(categoria),
    )
    return preparar_ensaio(ensaio, cfg)


# ---------------------------------------------------------------------
print("\n[1] Leitura e conversao de texto pt-BR")
linhas = [
    ["massa_A", "", ""],
    ["t", "x", "y"],
    ["0,00E+00", "3,07E+02", "5,03E+00"],
    ["3,33E-02", "3,07E+02", "5,03E+00"],
    ["6,67E-02", "3,06E+02", "5,10E+00"],
    ["", "", ""],
]
t, x, y = extrair_txy(linhas)
verificar(t.size == 3, f"cabecalho e linha vazia descartados (n={t.size})")
verificar(np.isclose(t[1], 0.0333), f"tempo convertido: {t[1]}")
verificar(np.isclose(x[0], 307.0), f"x convertido: {x[0]}")
verificar(np.isclose(y[0], 5.03), f"y convertido: {y[0]}")

# ---------------------------------------------------------------------
print("\n[2] Metadados extraidos do nome da categoria")
verificar(passo_da_categoria("I_S1_P02") == 2.0, "I_S1_P02 -> passo 2 graus")
verificar(passo_da_categoria("I_S2_P10") == 10.0, "I_S2_P10 -> passo 10 graus")
cfg = Config(mostrar_figuras=False)
verificar(
    np.isclose(raio_nominal(cfg, "PROJ 1_PE01", "I_S1_P02"), 146.58 + 159.74),
    "S1 usa AB+BC como raio nominal",
)
verificar(
    np.isclose(raio_nominal(cfg, "PROJ 1_PE01", "I_S2_P02"), 167.25),
    "S2 usa apenas BC como raio nominal",
)

# ---------------------------------------------------------------------
print("\n[3] Ajuste de circunferencia")
angulos = np.deg2rad(np.linspace(10, 120, 200))
xc_v, yc_v, r_v = 150.0, -80.0, 205.0
xa = xc_v + r_v * np.cos(angulos)
ya = yc_v + r_v * np.sin(angulos)
xc, yc, raio = ajustar_circulo(xa, ya)
verificar(
    np.allclose([xc, yc, raio], [xc_v, yc_v, r_v], atol=1e-6),
    f"centro/raio recuperados: ({xc:.3f}, {yc:.3f}), R={raio:.3f}",
)

# ---------------------------------------------------------------------
print("\n[4] Escolha do centro de rotacao")
t, x, y = gerar_ensaio(centro=(0.0, 0.0), raio=306.32)
centro, raio, origem = estimar_centro(x, y, cfg, raio_esperado=306.32)
verificar(
    np.hypot(*centro) < 1.0 and abs(raio - 306.32) < 0.5,
    f"origem do Tracker reconhecida como junta: centro={centro}, R={raio:.2f} ({origem})",
)

t2, x2, y2 = gerar_ensaio(centro=(150.0, -80.0), raio=205.0)
centro2, raio2, origem2 = estimar_centro(x2, y2, cfg, raio_esperado=205.0)
verificar(
    np.hypot(centro2[0] - 150.0, centro2[1] + 80.0) < 1.0 and abs(raio2 - 205.0) < 0.5,
    f"centro deslocado recuperado pelo ajuste: {tuple(round(v, 2) for v in centro2)} ({origem2})",
)

# arco curto: o ajuste livre e mal condicionado e deve ser rejeitado
t3, x3, y3 = gerar_ensaio(passo=2.0, duracao=5.0, centro=(0.0, 0.0), raio=306.32)
centro3, raio3, origem3 = estimar_centro(x3, y3, cfg, raio_esperado=306.32)
verificar(
    np.hypot(*centro3) < 1.0,
    f"arco curto nao gera centro absurdo: {tuple(round(v, 2) for v in centro3)} ({origem3})",
)

# ---------------------------------------------------------------------
print("\n[4b] Quantizacao dos dados (3 algarismos significativos)")
t, x, y = gerar_ensaio(raio=306.32, ruido=0.0)
verificar(
    algarismos_significativos(quantizar(x)) == 3,
    "detecta 3 algarismos significativos nos dados exportados",
)
verificar(
    algarismos_significativos(x) >= 10,
    f"detecta precisao total quando ela existe ({algarismos_significativos(x)} digitos)",
)
mediana, maximo, digitos = resolucao_angular(quantizar(x), quantizar(y), (0.0, 0.0))
erro_real = np.abs(
    angulo_desenrolado(quantizar(x), quantizar(y), (0.0, 0.0))
    - angulo_desenrolado(x, y, (0.0, 0.0))
).max()
verificar(
    erro_real <= maximo,
    f"formula limita o erro real: real={erro_real:.3f}° <= estimado={maximo:.3f}°",
)
verificar(
    0.05 < maximo < 0.5,
    f"incerteza por quantizacao em R=306 mm: {maximo:.3f}° (mediana {mediana:.3f}°)",
)

# ---------------------------------------------------------------------
print("\n[4c] Ajuste de centro com raio fixo em arcos curtos")
verificar(
    abs(varredura_estimada(x, y, 306.32) - 120.0) < 3.0,
    f"varredura estimada sem conhecer o centro: {varredura_estimada(x, y, 306.32):.1f}°",
)
for span in (10.0, 20.0, 40.0):
    angulos = np.deg2rad(np.linspace(11.9, 11.9 + span, int(span * 6) + 10))
    xa = quantizar(110.91 * np.cos(angulos))
    ya = quantizar(110.91 * np.sin(angulos))
    livre = ajustar_circulo(xa, ya)
    fixo = ajustar_centro_raio_fixo(xa, ya, 110.91)
    verificar(
        np.hypot(*fixo) < 0.3,
        f"arco de {span:.0f}°: raio fixo erra {np.hypot(*fixo):.3f} mm "
        f"(ajuste livre erraria {np.hypot(livre[0], livre[1]):.1f} mm)",
    )
    centro_esc, _, origem_esc = estimar_centro(xa, ya, cfg, raio_esperado=110.91)
    verificar(
        np.hypot(*centro_esc) < 0.3,
        f"arco de {span:.0f}°: pipeline escolhe '{origem_esc}' e erra "
        f"{np.hypot(*centro_esc):.3f} mm",
    )

# ---------------------------------------------------------------------
print("\n[5] Deteccao do instante do comando")
for passo_teste, t_cmd in ((10.0, 2.0), (5.0, 1.5), (2.0, 3.0)):
    t, x, y = gerar_ensaio(passo=passo_teste, t_comando=t_cmd, theta0=11.9)
    theta = angulo_desenrolado(x, y, (0.0, 0.0))
    indice, repouso = detectar_inicio(theta, passo_teste, cfg)
    erro_ms = abs(t[indice] - t_cmd) * 1000
    verificar(
        erro_ms <= 100.0 and abs(repouso - 11.9) < 0.15,
        f"passo {passo_teste:>4}: comando em t={t[indice]:.3f}s "
        f"(alvo {t_cmd}s, erro {erro_ms:.0f} ms), repouso={repouso:.2f} graus",
    )

# ---------------------------------------------------------------------
print("\n[6] Trajetoria desejada (escada)")
tau = np.array([-0.5, -0.01, 0.0, 0.5, 0.999, 1.0, 2.5, 100.0])
comando = trajetoria_desejada(tau, 10.0, cfg)
esperado = [0.0, 0.0, 10.0, 10.0, 10.0, 20.0, 30.0, 180.0]
verificar(
    np.allclose(comando, esperado),
    f"degraus corretos e saturacao em 180 graus: {comando.tolist()}",
)

# ---------------------------------------------------------------------
print("\n[7] Sentido de rotacao negativo")
ensaio_neg = montar(cfg, sentido=-1, theta0=40.0)
verificar(ensaio_neg.sentido == -1, "sentido negativo detectado")
verificar(
    ensaio_neg.theta_rel[-1] > 0,
    f"resposta reexpressa como positiva: {ensaio_neg.theta_rel[-1]:.2f} graus",
)

# ---------------------------------------------------------------------
print("\n[8] Sobreposicao da curva desejada com a medida (X-Y)")
ensaio = montar(cfg)
_, x_des, y_des = curva_desejada_ensaio(ensaio, cfg)
distancia = np.hypot(ensaio.x - x_des, ensaio.y - y_des)
verificar(
    float(np.median(distancia)) < 1.0,
    f"medida e desejada no mesmo referencial (erro mediano {np.median(distancia):.2f} mm)",
)
raio_des = np.hypot(x_des - ensaio.centro[0], y_des - ensaio.centro[1])
verificar(
    np.allclose(raio_des, ensaio.raio),
    "arco desejado usa o raio medido, nao o nominal",
)

# ---------------------------------------------------------------------
print("\n[9] Metricas de desempenho")
metricas = metricas_por_degrau(ensaio, cfg)
verificar(len(metricas) >= 10, f"degraus avaliados: {len(metricas)}")
verificar(
    metricas["erro_graus"].abs().max() < 0.2,
    f"erro de regime proximo de zero (max {metricas['erro_graus'].abs().max():.3f} graus)",
)
verificar(
    np.allclose(metricas["alvo_graus"], np.arange(1, len(metricas) + 1) * 10.0),
    "alvo acumulado corretamente ao longo dos degraus",
)
sobressinal = metricas["sobressinal_percentual"].mean()
verificar(
    2.0 < sobressinal < 15.0,
    f"sobressinal coerente com zeta=0.65: {sobressinal:.1f}%",
)
subida = metricas["tempo_subida_s"].mean()
verificar(0.02 < subida < 0.20, f"tempo de subida 10-90%: {subida*1000:.0f} ms")

globais = metricas_globais(ensaio, cfg)
verificar(
    globais["rmse_graus"] < 2.5,
    f"RMSE contra o comando: {globais['rmse_graus']:.2f} graus",
)
verificar(
    abs(globais["taxa_amostragem_hz"] - 30.0) < 0.1,
    f"taxa de amostragem estimada: {globais['taxa_amostragem_hz']:.2f} Hz",
)

# ---------------------------------------------------------------------
print("\n[10] Alinhamento entre repeticoes com duracoes diferentes")
repeticoes = [
    montar(cfg, repeticao=1, t_comando=2.0, duracao=14.0, semente=1),
    montar(cfg, repeticao=2, t_comando=0.4, duracao=12.0, semente=2),
    montar(cfg, repeticao=3, t_comando=3.1, duracao=15.0, semente=3),
]
grade, matriz = grade_comum(repeticoes, cfg)
verificar(grade.size > 100, f"grade comum construida: {grade.size} pontos")
verificar(matriz.shape[1] == 3, f"tres repeticoes interpoladas: {matriz.shape}")
dispersao = matriz.std(axis=1, ddof=1).max()
verificar(
    dispersao < 1.0,
    f"repeticoes coincidem apos o alinhamento (desvio max {dispersao:.3f} graus)",
)
comando = trajetoria_desejada(grade, 10.0, cfg)
erro_regime = np.abs(matriz.mean(axis=1) - comando)
verificar(
    float(np.median(erro_regime)) < 0.5,
    f"media das repeticoes segue o comando (erro mediano {np.median(erro_regime):.3f} graus)",
)

# ---------------------------------------------------------------------
print("\n[11] Robustez: movimento comecando na 2a amostra")
t, x, y = gerar_ensaio(t_comando=0.033, duracao=8.0)
ensaio_cedo = preparar_ensaio(
    Ensaio("PE_teste", "I_S1_P10", 1, t, x, y, passo=10.0), cfg
)
verificar(
    ensaio_cedo.indice_comando <= 2,
    f"comando detectado no indice {ensaio_cedo.indice_comando}",
)
verificar(
    abs(ensaio_cedo.theta0 - 11.9) < 0.5,
    f"repouso estimado com plato curto: {ensaio_cedo.theta0:.2f} graus",
)

# ---------------------------------------------------------------------
print("\n[12] Metricas nao se degradam com os dados quantizados")
# Ate a versao anterior o ajuste livre de circunferencia deslocava o
# centro em ~1,8 mm nesses dados e o erro de regime crescia degrau a
# degrau ate 1,3 graus. Com o raio fixo o vies desaparece.
t, x, y = gerar_ensaio(
    passo=5.0, theta0=11.9, raio=110.91, t_comando=1.9,
    duracao=10.0, sentido=-1, ruido=0.0,
)
ensaio_q = preparar_ensaio(
    Ensaio("PE_teste", "I_S2_P05", 1, t, quantizar(x), quantizar(y), passo=5.0),
    replace(cfg, elos={"PE_teste": {"I_S2_P05": {"BC": 110.91}}}),
)
erros = metricas_por_degrau(ensaio_q, cfg)["erro_graus"].to_numpy()
verificar(
    np.abs(erros).max() < 0.15,
    f"erro de regime sem vies acumulado: max {np.abs(erros).max():.3f}° "
    f"(era 1,3° com ajuste livre)",
)
inclinacao = np.polyfit(np.arange(erros.size), erros, 1)[0]
verificar(
    abs(inclinacao) < 0.02,
    f"erro nao cresce com o numero do degrau: {inclinacao:+.4f}°/degrau",
)

# ---------------------------------------------------------------------
print("\n[13] Robustez: ensaio sem movimento")
t = np.arange(0, 5, 1 / 30)
x = np.full_like(t, 306.32)
y = np.zeros_like(t)
parado = preparar_ensaio(Ensaio("PE_teste", "I_S1_P02", 1, t, x, y, passo=2.0), cfg)
verificar(parado.indice_comando == 0, "ensaio parado nao quebra o pipeline")
verificar(np.isfinite(parado.theta0), f"repouso definido: {parado.theta0:.2f} graus")

# ---------------------------------------------------------------------
print()
if FALHAS:
    print(f"{len(FALHAS)} verificacao(oes) falharam:")
    for item in FALHAS:
        print(f"  - {item}")
    sys.exit(1)
print("Todas as verificacoes passaram.")
