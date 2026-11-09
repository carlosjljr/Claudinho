# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - MALHA x GRAVIDADE: TENSAO DE VON MISES
#          duas figuras -- pontos do SG e pontos do potenciometro
# =====================================================================
# Cole este arquivo inteiro em UMA celula do Colab e rode.
#
# Mesma codificacao visual da figura do artigo, tres canais para nao
# precisar de uma entrada de legenda por curva:
#     cor      -> ponto de medicao (1 preto, 2 cinza)
#     traco    -> gravidade (sem = continuo, com = tracejado)
#     marcador -> modelo (MEE03 circulo, MEE10 quadrado)
#
# ATENCAO: so ha dados de tensao do MEE10 (as series que estavam como
# "VER 10"). Os campos do MEE03 estao vazios; e so preencher com as
# cinco leituras que a figura passa a mostrar os circulos tambem.
# =====================================================================
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# DADOS - tensao de Von Mises [MPa]
# ---------------------------------------------------------------------
ELEMENTOS = [0.2, 0.4, 0.8, 1.0, 1.5]        # milhoes de elementos

# Pontos do SG (antigos ENG 1 e ENG 2)
SG = {
    ("MEE03", "sem gravidade"): {"SG 1": None, "SG 2": None},
    ("MEE03", "com gravidade"): {"SG 1": None, "SG 2": None},
    ("MEE10", "sem gravidade"): {
        "SG 1": [27.387, 33.240, 42.276, 39.454, 67.500],
        "SG 2": [42.562, 45.992, 48.320, 45.291, 67.262],
    },
    ("MEE10", "com gravidade"): {
        "SG 1": [28.737, 34.772, 39.596, 39.995, 76.055],
        "SG 2": [41.688, 41.297, 45.495, 45.822, 70.231],
    },
}

# Pontos do potenciometro
POT = {
    ("MEE03", "sem gravidade"): {"POT 1": None, "POT 2": None},
    ("MEE03", "com gravidade"): {"POT 1": None, "POT 2": None},
    ("MEE10", "sem gravidade"): {
        "POT 1": [12.418, 8.6097, 22.686, 10.043, 27.075],
        "POT 2": [6.0130, 10.239, 11.401, 11.768, 7.7621],
    },
    ("MEE10", "com gravidade"): {
        "POT 1": [10.197, 15.554, 12.373, 12.966, 14.560],
        "POT 2": [9.2122, 7.5657, 7.0929, 8.1407, 8.9756],
    },
}

FIGURAS = [
    (SG,  ("SG 1", "SG 2"),   "grafico_tensao_sg.png"),
    (POT, ("POT 1", "POT 2"), "grafico_tensao_pot.png"),
]

ROTULO_Y = "Tensão equivalente de Von Mises [MPa]"
MODELOS = ("MEE03", "MEE10")
CORES = ("#000000", "0.45")                  # ponto 1, ponto 2
TRACOS = {"sem gravidade": "-", "com gravidade": "--"}
MARCAS = {"MEE03": "o", "MEE10": "s"}

# O rotulo do eixo Y ja e grande o bastante, entao fica menor que o
# resto de proposito.
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 400, "savefig.bbox": "tight",
    "font.size": 15, "axes.labelsize": 17, "legend.fontsize": 15,
    "xtick.labelsize": 15, "ytick.labelsize": 15,
    "axes.grid": True, "grid.linestyle": "--", "grid.linewidth": 0.4,
    "grid.alpha": 0.6,
})


def grafico(dados, pontos, arquivo):
    """Uma figura com os dois modelos, os dois pontos e as duas condicoes."""
    h = np.asarray(ELEMENTOS, float)
    cores = dict(zip(pontos, CORES))
    fig, eixo = plt.subplots(figsize=(7.5, 5.0), layout="constrained")
    presentes = []

    for modelo in MODELOS:
        for condicao, traco in TRACOS.items():
            for ponto in pontos:
                valores = dados[(modelo, condicao)][ponto]
                if valores is None:          # serie ainda sem dados
                    continue
                eixo.plot(h, valores, marker=MARCAS[modelo], linestyle=traco,
                          color=cores[ponto], ms=6, lw=1.5,
                          markerfacecolor="none", markeredgewidth=1.4)
                presentes.append(modelo)

    eixo.set_xticks(h)
    eixo.set_xticklabels([f"{v:.1f}" for v in h])
    eixo.set_xlabel("Número de elementos [$\\times 10^6$]")
    eixo.set_ylabel(ROTULO_Y, fontsize=14)

    # Legenda em tres blocos, um por canal visual: explica todas as
    # curvas sem listar uma entrada para cada.
    def alca(**kwargs):
        base = dict(color="0.2", linestyle="-", marker="None", lw=1.5)
        base.update(kwargs)
        return plt.Line2D([], [], **base)

    alcas = [alca(color=cores[p], label=p) for p in pontos]
    alcas += [alca(linestyle=t, label=c) for c, t in TRACOS.items()]
    alcas += [alca(linestyle="None", marker=MARCAS[m], ms=6,
                   markerfacecolor="none", markeredgewidth=1.4, label=m)
              for m in MODELOS if m in presentes]
    eixo.legend(handles=alcas, loc="upper center", bbox_to_anchor=(0.5, -0.16),
                ncol=3, frameon=False, handlelength=2.2, columnspacing=1.6)

    fig.savefig(arquivo)
    plt.close(fig)
    return arquivo


def tabela(dados, pontos, titulo):
    """Variacao percentual a cada refino, para o texto do artigo."""
    print(f"\n=== {titulo}: VARIAÇÃO A CADA REFINO ===")
    print(f"{'série':<30} {'σ malha fina':>13} {'último refino':>14} "
          f"{'máxima':>8}")
    for modelo in MODELOS:
        for condicao in TRACOS:
            for ponto in pontos:
                valores = dados[(modelo, condicao)][ponto]
                if valores is None:
                    continue
                serie = np.asarray(valores, float)
                variacao = 100.0 * np.abs(np.diff(serie)) / np.abs(serie[:-1])
                print(f"{modelo + ' ' + ponto + ' ' + condicao:<30} "
                      f"{serie[-1]:10.2f} MPa {variacao[-1]:12.1f}% "
                      f"{variacao.max():7.1f}%")
    print("  Variação alta no último refino significa que a tensão ainda "
          "depende da\n  malha naquele ponto, então o valor absoluto não "
          "pode ser reportado.")


# ---------------------------------------------------------------------
if __name__ == "__main__":
    for dados, pontos, arquivo in FIGURAS:
        grafico(dados, pontos, arquivo)
        tabela(dados, pontos, pontos[0].split()[0])

    try:
        from IPython.display import Image, display
        for _, _, arquivo in FIGURAS:
            display(Image(filename=arquivo))
    except ImportError:
        pass
