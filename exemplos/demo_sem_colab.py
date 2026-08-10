# -*- coding: utf-8 -*-
"""Demonstracao do pipeline com dados sinteticos, sem Colab.

Gera um ensaio parecido com os do PROJ 1 (angulo de repouso diferente de
zero, escada de degraus, tres repeticoes) e produz:

  1. a comparacao entre o metodo antigo e o novo no plano X-Y;
  2. a comparacao no dominio do tempo;
  3. as figuras finais do pipeline.

Uso:  python exemplos/demo_sem_colab.py [pasta_de_saida]
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests"))

from proj1_analise import (  # noqa: E402
    Config,
    Ensaio,
    configurar_estilo,
    configurar_log,
    curva_desejada_ensaio,
    plot_angulo,
    plot_media_desvio,
    plot_xy,
    preparar_ensaio,
    trajetoria_desejada,
)
from dados_sinteticos import gerar_ensaio  # noqa: E402

SAIDA = sys.argv[1] if len(sys.argv) > 1 else "figuras_demo"

PASSO = 10.0
THETA0 = 11.9  # angulo de repouso do braco na filmagem
RAIO = 306.32  # AB + BC
AB, BC = 146.58, 159.74

cfg = Config(mostrar_figuras=False, formatos_figura=("png",))
configurar_log()
configurar_estilo(cfg)
os.makedirs(SAIDA, exist_ok=True)

# --- tres repeticoes com instantes de comando diferentes -------------
ensaios = []
for i, (t_cmd, dur, semente) in enumerate(
    ((1.8, 13.0, 11), (0.6, 12.4, 22), (2.7, 14.1, 33)), start=1
):
    t, x, y = gerar_ensaio(
        passo=PASSO,
        theta0=THETA0,
        raio=RAIO,
        t_comando=t_cmd,
        duracao=dur,
        semente=semente,
        ruido=0.05,
    )
    ensaios.append(
        preparar_ensaio(
            Ensaio("PROJ 1_PE01", "I_S1_P10", i, t, x, y, passo=PASSO), cfg
        )
    )

ref = ensaios[0]
print(f"centro estimado: {ref.centro}  raio: {ref.raio:.2f} mm ({ref.origem_centro})")
print(f"repouso: {ref.theta0:.2f} graus | comando na amostra {ref.indice_comando}")

# =====================================================================
# 1. Plano X-Y: por que as curvas nao se encontravam
# =====================================================================
# Cenario extra: origem do Tracker deslocada da junta (acontece quando o
# eixo do video nao e marcado exatamente sobre o eixo do servo).
DESLOCAMENTO = (18.0, -25.0)
t_d, x_d, y_d = gerar_ensaio(
    passo=PASSO, theta0=THETA0, raio=RAIO, centro=DESLOCAMENTO, t_comando=1.8, semente=44
)
ensaio_deslocado = preparar_ensaio(
    Ensaio("PROJ 1_PE01", "I_S1_P10", 1, t_d, x_d, y_d, passo=PASSO), cfg
)

fig, (antigo, novo) = plt.subplots(1, 2, figsize=(11.5, 4.8))

# --- metodo antigo: rampa linear 0->180 graus, arco centrado em (0,0)
# com raio nominal e SEM o angulo de repouso.
tempos = ref.t - ref.t[0]
rampa = (tempos / tempos[-1]) * 180.0
x_antigo = (AB + BC) * np.cos(np.deg2rad(rampa))
y_antigo = (AB + BC) * np.sin(np.deg2rad(rampa))

antigo.plot(ref.x, ref.y, color="tab:blue", label="Medido (origem na junta)")
antigo.plot(
    ensaio_deslocado.x,
    ensaio_deslocado.y,
    color="tab:orange",
    label="Medido (origem deslocada)",
)
antigo.plot(x_antigo, y_antigo, "k--", linewidth=1.8, label="Desejada: rampa 0–180°")
antigo.plot(ref.x[0], ref.y[0], "o", color="tab:blue", markersize=6)
antigo.plot(ensaio_deslocado.x[0], ensaio_deslocado.y[0], "o", color="tab:orange", markersize=6)
antigo.plot(x_antigo[0], y_antigo[0], "ks", markersize=6)
antigo.annotate(
    "desejada parte de 0°\ne varre 180°",
    xy=(x_antigo[0], y_antigo[0]),
    xytext=(-40, 60),
    textcoords="offset points",
    fontsize=8,
    arrowprops=dict(arrowstyle="->", linewidth=0.8),
)
antigo.annotate(
    f"ensaio parte de {THETA0:.0f}°",
    xy=(ref.x[0], ref.y[0]),
    xytext=(-120, -35),
    textcoords="offset points",
    fontsize=8,
    arrowprops=dict(arrowstyle="->", linewidth=0.8),
)
antigo.set_title("Antes: origens, raios e faixas angulares diferentes")
antigo.set_xlabel("X (mm)")
antigo.set_ylabel("Y (mm)")
antigo.legend(loc="lower left", fontsize=8)
antigo.set_aspect("equal", adjustable="datalim")

# --- metodo novo: mesmo centro, mesmo raio, mesma faixa angular
for e, cor, rotulo in (
    (ref, "tab:blue", "Medido (origem na junta)"),
    (ensaio_deslocado, "tab:orange", "Medido (origem deslocada)"),
):
    novo.plot(e.x - e.centro[0], e.y - e.centro[1], color=cor, label=rotulo)
_, x_des, y_des = curva_desejada_ensaio(ref, cfg)
novo.plot(
    x_des - ref.centro[0],
    y_des - ref.centro[1],
    "k--",
    linewidth=1.8,
    label="Desejada: escada sobre o mesmo arco",
)
novo.plot(0, 0, "k+", markersize=10)
novo.set_title("Depois: mesmo centro, raio e referencia angular")
novo.set_xlabel("X (mm) — origem na junta")
novo.set_ylabel("Y (mm) — origem na junta")
novo.legend(loc="lower left", fontsize=8)
novo.set_aspect("equal", adjustable="datalim")

fig.tight_layout()
fig.savefig(os.path.join(SAIDA, "comparacao_xy.png"), dpi=200)
plt.close(fig)
print(
    "centro recuperado no caso deslocado: "
    f"{tuple(round(v, 2) for v in ensaio_deslocado.centro)} "
    f"(real {DESLOCAMENTO}) via {ensaio_deslocado.origem_centro}"
)

# =====================================================================
# 2. Dominio do tempo: rampa linear x escada de degraus
# =====================================================================
fig, (antigo, novo) = plt.subplots(1, 2, figsize=(11.5, 4.3), sharey=True)

for e in ensaios:
    indices = np.arange(e.t.size)
    antigo.plot(indices, e.theta, label=f"Experimento {e.repeticao}")
antigo.plot(
    np.arange(tempos.size),
    rampa,
    "k--",
    linewidth=1.8,
    label="Desejada (rampa 0–180)",
)
antigo.set_title("Antes: eixo em amostras, rampa linear, sem alinhar")
antigo.set_xlabel("Amostras (indice)")
antigo.set_ylabel("Angulo (graus)")
antigo.legend(loc="upper left")

for e in ensaios:
    recorte = e.tau >= -0.2
    novo.plot(e.tau[recorte], e.theta_rel[recorte], label=f"Experimento {e.repeticao}")
tau_cmd = np.linspace(-0.2, max(e.tau[-1] for e in ensaios), 3000)
novo.plot(
    tau_cmd,
    trajetoria_desejada(tau_cmd, PASSO, cfg),
    "k--",
    linewidth=1.8,
    label="Comando (escada de 10°/s)",
)
novo.set_title("Depois: tempo desde o comando, escada de degraus")
novo.set_xlabel("Tempo desde o comando (s)")
novo.set_ylabel("Deslocamento angular (graus)")
novo.legend(loc="upper left")

fig.tight_layout()
fig.savefig(os.path.join(SAIDA, "comparacao_angulo.png"), dpi=200)
plt.close(fig)

# =====================================================================
# 3. Figuras finais do pipeline
# =====================================================================
plot_xy(ensaios, cfg, SAIDA)
plot_angulo(ensaios, cfg, SAIDA)
plot_angulo(ensaios, cfg, SAIDA, zoom=cfg.zoom_segundos)
plot_media_desvio(ensaios, cfg, SAIDA)

print(f"Figuras geradas em: {os.path.abspath(SAIDA)}")
for arquivo in sorted(os.listdir(SAIDA)):
    print(f"  - {arquivo}")
