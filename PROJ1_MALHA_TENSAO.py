# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - CONVERGENCIA DE MALHA: von Mises nos pontos de prova
# =====================================================================
# Cole numa celula do Colab e rode. Nao depende dos outros modulos.
#
# Solido = com gravidade; tracejado = sem gravidade.
# Alem da figura, roda a analise de convergencia: um estudo de malha so
# justifica a malha adotada se a tensao PARAR de mudar com o refino.
# =====================================================================
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Modelos de elementos finitos, na mesma nomenclatura dos protótipos.
MODELOS = {
    "PE01": "(a) PE01 — modelo simplificado",
    "PE02": "(b) PE02 — configuração final",
}

ELEMENTOS = np.array([0.2, 0.4, 0.8, 1.0, 1.5])   # milhoes de elementos
FAIXA_ADOTADA = (0.7, 0.9)                        # malha escolhida
LIMITE_CONVERGENCIA = 5.0                         # % de variacao aceita

DADOS = {
    ("PE01", "com gravidade"): {
        "ENG 1": [19.593, 34.305, 30.590, 41.674, 46.414],
        "ENG 2": [39.035, 26.362, 32.050, 34.209, 34.339],
        "POT 1": [61.961, 115.390, 74.867, 109.560, 160.120],
        "POT 2": [124.040, 95.886, 17.024, 71.411, 99.586],
    },
    ("PE01", "sem gravidade"): {
        "ENG 1": [18.705, 24.235, 20.665, 21.556, 33.037],
        "ENG 2": [20.664, 25.456, 31.147, 37.697, 28.234],
        "POT 1": [59.017, 110.560, 71.225, 105.530, 159.450],
        "POT 2": [89.519, 71.908, 23.485, 91.556, 143.450],
    },
    ("PE02", "com gravidade"): {
        "ENG 1": [21.335, 21.435, 28.325, 28.277, 38.338],
        "ENG 2": [33.003, 28.083, 31.020, 34.671, 34.031],
        "POT 1": [36.400, 25.670, 35.133, 33.606, 21.692],
        "POT 2": [121.240, 36.767, 114.550, 97.281, 145.230],
    },
    ("PE02", "sem gravidade"): {
        "ENG 1": [20.620, 20.714, 27.261, 26.865, 36.095],
        "ENG 2": [31.449, 27.110, 29.392, 32.622, 32.093],
        "POT 1": [33.319, 26.164, 30.679, 35.443, 20.943],
        "POT 2": [117.700, 31.508, 112.830, 89.020, 116.010],
    },
}

CORES = {"ENG 1": "#1f4e9c", "ENG 2": "#3fa7d6",
         "POT 1": "#2e7d32", "POT 2": "#c77d00"}
MARCAS = {"ENG 1": "o", "ENG 2": "s", "POT 1": "^", "POT 2": "D"}

PASTA_SAIDA = "/content/drive/MyDrive/CTG_UFPE/PROJETOS/PROJ 1/RESULTADOS"
FORMATOS = ("png", "pdf")
MOSTRAR_FIGURAS = True

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.size": 11, "axes.titlesize": 11, "axes.labelsize": 11,
    "legend.fontsize": 9, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.grid": True, "grid.linestyle": "--", "grid.linewidth": 0.4,
    "grid.alpha": 0.6,
})


def garantir_drive_malha():
    """Monta o Drive se estiver no Colab e ainda nao estiver montado.

    Assim a ordem das celulas nao importa: este modulo pode rodar antes
    ou depois do de trajetoria.
    """
    if not PASTA_SAIDA.startswith("/content/drive"):
        return
    try:
        from google.colab import drive
    except ImportError:
        return
    if not os.path.isdir("/content/drive/MyDrive"):
        drive.mount("/content/drive")


def tabela_convergencia():
    """Variacao percentual da tensao a cada refino de malha.

    Um ponto so pode ser reportado como convergido se a variacao entre
    as duas malhas mais finas ficar abaixo de LIMITE_CONVERGENCIA.
    """
    linhas = []
    for (modelo, condicao), pontos in DADOS.items():
        for ponto, valores in pontos.items():
            serie = np.asarray(valores, float)
            variacao = 100.0 * np.abs(np.diff(serie)) / np.abs(serie[:-1])
            linhas.append({
                "modelo": modelo,
                "condicao": condicao,
                "ponto": ponto,
                "tensao_malha_adotada_MPa": float(
                    serie[int(np.argmin(np.abs(ELEMENTOS - np.mean(FAIXA_ADOTADA))))]),
                "tensao_malha_fina_MPa": float(serie[-1]),
                "variacao_ultimo_refino_pct": float(variacao[-1]),
                "variacao_maxima_pct": float(variacao.max()),
                "monotonico": bool(np.all(np.diff(serie) > 0)
                                   or np.all(np.diff(serie) < 0)),
                "convergido": bool(variacao[-1] < LIMITE_CONVERGENCIA),
            })
    return pd.DataFrame(linhas)


def salvar_figura_malha(fig, nome):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    for formato in FORMATOS:
        fig.savefig(os.path.join(PASTA_SAIDA, f"{nome}.{formato}"), format=formato)
    if MOSTRAR_FIGURAS:
        plt.show()
    plt.close(fig)


def figura_malha():
    fig, eixos = plt.subplots(1, len(MODELOS), figsize=(11.0, 4.4), sharey=True)
    eixos = np.atleast_1d(eixos)

    for eixo, (modelo, titulo) in zip(eixos, MODELOS.items()):
        eixo.axvspan(*FAIXA_ADOTADA, color="0.88", zorder=0)
        for ponto in CORES:
            eixo.plot(ELEMENTOS, DADOS[(modelo, "com gravidade")][ponto],
                      MARCAS[ponto] + "-", color=CORES[ponto], ms=4.5, lw=1.4,
                      label=ponto)
            eixo.plot(ELEMENTOS, DADOS[(modelo, "sem gravidade")][ponto],
                      MARCAS[ponto] + "--", color=CORES[ponto], ms=3.5, lw=1.0,
                      alpha=0.75)
        eixo.set_xticks(ELEMENTOS)
        eixo.set_xticklabels([f"{v:.1f}" for v in ELEMENTOS])
        eixo.set_xlabel("Número de elementos [$\\times 10^6$]")
        eixo.set_title(titulo)
    eixos[0].set_ylabel("Tensão equivalente de von Mises [MPa]")

    # Marca os pontos que nao convergiram: sem isso a figura sugere que
    # a malha adotada vale para todos os pontos, o que nao e o caso.
    convergencia = tabela_convergencia()
    for eixo, modelo in zip(eixos, MODELOS):
        falhos = convergencia[(convergencia["modelo"] == modelo)
                              & (convergencia["condicao"] == "com gravidade")
                              & (~convergencia["convergido"])]["ponto"].tolist()
        if falhos:
            eixo.text(0.02, 0.97, "não convergiu: " + ", ".join(falhos),
                      transform=eixo.transAxes, fontsize=7.5, va="top",
                      bbox=dict(boxstyle="round", facecolor="#ffe9e9",
                                edgecolor="#c00", alpha=0.9, lw=0.6))

    marcadores = [plt.Line2D([], [], color=CORES[p], marker=MARCAS[p],
                             linestyle="-", ms=4.5, label=p) for p in CORES]
    marcadores += [
        plt.Line2D([], [], color="0.35", linestyle="-", label="com gravidade"),
        plt.Line2D([], [], color="0.35", linestyle="--", label="sem gravidade"),
        plt.Rectangle((0, 0), 1, 1, color="0.88", label="malha adotada"),
    ]
    fig.legend(handles=marcadores, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, -0.14))
    fig.tight_layout()
    salvar_figura_malha(fig, "malha_tensao_von_mises")


def figura_convergencia(convergencia):
    """Variacao percentual a cada refino: o que justifica a malha."""
    fig, eixos = plt.subplots(1, len(MODELOS), figsize=(11.0, 4.0), sharey=True)
    eixos = np.atleast_1d(eixos)
    passos = [f"{ELEMENTOS[i]:.1f}→{ELEMENTOS[i+1]:.1f}"
              for i in range(len(ELEMENTOS) - 1)]

    for eixo, modelo in zip(eixos, MODELOS):
        for ponto in CORES:
            serie = np.asarray(DADOS[(modelo, "com gravidade")][ponto], float)
            variacao = 100.0 * np.abs(np.diff(serie)) / np.abs(serie[:-1])
            eixo.plot(passos, variacao, MARCAS[ponto] + "-",
                      color=CORES[ponto], ms=4.5, lw=1.4, label=ponto)
        eixo.axhline(LIMITE_CONVERGENCIA, color="k", linestyle=":", lw=1.2)
        eixo.text(0.02, LIMITE_CONVERGENCIA, f" {LIMITE_CONVERGENCIA:.0f}%",
                  va="bottom", fontsize=8, transform=eixo.get_yaxis_transform())
        eixo.set_yscale("log")
        eixo.set_xlabel("Refino [$\\times 10^6$ elementos]")
        eixo.set_title(MODELOS[modelo])
        eixo.tick_params(axis="x", rotation=30)
    eixos[0].set_ylabel("Variação da tensão (%)")
    eixos[-1].legend(loc="best", ncol=2)
    fig.tight_layout()
    salvar_figura_malha(fig, "malha_convergencia")


def executar_malha():
    garantir_drive_malha()
    convergencia = tabela_convergencia()

    print("=== CONVERGENCIA DE MALHA (com gravidade) ===")
    vista = convergencia[convergencia["condicao"] == "com gravidade"]
    print(vista[["modelo", "ponto", "tensao_malha_adotada_MPa",
                 "tensao_malha_fina_MPa", "variacao_ultimo_refino_pct",
                 "variacao_maxima_pct", "monotonico", "convergido"]]
          .round(2).to_string(index=False))

    nao_convergiram = convergencia[~convergencia["convergido"]]
    if not nao_convergiram.empty:
        print(f"\n! {len(nao_convergiram)} série(s) NÃO convergiram "
              f"(variação > {LIMITE_CONVERGENCIA:.0f}% no último refino):")
        for _, linha in nao_convergiram.iterrows():
            print(f"    {linha['modelo']:6s} {linha['ponto']:6s} "
                  f"{linha['condicao']:14s} -> {linha['variacao_ultimo_refino_pct']:6.1f}%")
        print("  Nesses pontos a tensão ainda depende da malha, então o valor"
              "\n  absoluto não pode ser reportado como resultado. Tensão que"
              "\n  não converge com o refino costuma indicar singularidade"
              "\n  geométrica (canto vivo) — nesse caso vale reportar a tensão"
              "\n  a uma distância definida do canto, ou adicionar o raio de"
              "\n  concordância real da peça ao modelo.")

    figura_malha()
    figura_convergencia(convergencia)

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    convergencia.to_csv(os.path.join(PASTA_SAIDA, "malha_convergencia.csv"),
                        index=False, sep=";", decimal=",")
    print(f"\nConcluído. Resultados em {PASTA_SAIDA}")
    return convergencia


if __name__ == "__main__":
    CONVERGENCIA = executar_malha()
