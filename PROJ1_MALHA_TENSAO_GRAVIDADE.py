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
#     traco    -> gravidade (com = continuo, sem = tracejado)
#     marcador -> modelo (MEE03 circulo, MEE10 quadrado)
#
# Os dados do MEE03 sao os do poster ("a tensao nos acoplamentos do
# MEE03 vai de 19,6 a 46,4 MPa"); os do MEE10, os da "Versao Final"
# ("fica entre 21,3 e 38,3 MPa"). As series do comando rotulado
# "VER 10" nao batem com nenhum dos dois -- sao de uma versao
# intermediaria -- e por isso ficaram de fora.
# =====================================================================
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# DADOS - tensao de Von Mises [MPa]
# ---------------------------------------------------------------------
ELEMENTOS = [0.2, 0.4, 0.8, 1.0, 1.5]        # milhoes de elementos

# Acoplamentos das engrenagens (antigos ENG 1 e ENG 2)
SG = {
    ("MEE03", "sem gravidade"): {
        "SG 1": [18.705, 24.235, 20.665, 21.556, 33.037],
        "SG 2": [20.664, 25.456, 31.147, 37.697, 28.234],
    },
    ("MEE03", "com gravidade"): {
        "SG 1": [19.593, 34.305, 30.590, 41.674, 46.414],
        "SG 2": [39.035, 26.362, 32.050, 34.209, 34.339],
    },
    ("MEE10", "sem gravidade"): {
        "SG 1": [20.620, 20.714, 27.261, 26.865, 36.095],
        "SG 2": [31.449, 27.110, 29.392, 32.622, 32.093],
    },
    ("MEE10", "com gravidade"): {
        "SG 1": [21.335, 21.435, 28.325, 28.277, 38.338],
        "SG 2": [33.003, 28.083, 31.020, 34.671, 34.031],
    },
}

# Pre-cargas nos potenciometros
POT = {
    ("MEE03", "sem gravidade"): {
        "POT 1": [59.017, 110.560, 71.225, 105.530, 159.450],
        "POT 2": [89.519, 71.908, 23.485, 91.556, 143.450],
    },
    ("MEE03", "com gravidade"): {
        "POT 1": [61.961, 115.390, 74.867, 109.560, 160.120],
        "POT 2": [124.040, 95.886, 17.024, 71.411, 99.586],
    },
    ("MEE10", "sem gravidade"): {
        "POT 1": [33.319, 26.164, 30.679, 35.443, 20.943],
        "POT 2": [117.700, 31.508, 112.830, 89.020, 116.010],
    },
    ("MEE10", "com gravidade"): {
        "POT 1": [36.400, 25.670, 35.133, 33.606, 21.692],
        "POT 2": [121.240, 36.767, 114.550, 97.281, 145.230],
    },
}

FIGURAS = [
    (SG,  ("SG 1", "SG 2"),   "grafico_tensao_sg.png"),
    (POT, ("POT 1", "POT 2"), "grafico_tensao_pot.png"),
]

ROTULO_Y = "Tensão equivalente de Von Mises [MPa]"
MODELOS = ("MEE03", "MEE10")
CORES = ("#000000", "0.45")                  # ponto 1, ponto 2
TRACOS = {"com gravidade": "-", "sem gravidade": "--"}
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

    print("\n  Acréscimo da gravidade, malha a malha:")
    for modelo in MODELOS:
        for ponto in pontos:
            com = np.asarray(dados[(modelo, "com gravidade")][ponto], float)
            sem = np.asarray(dados[(modelo, "sem gravidade")][ponto], float)
            efeito = 100.0 * (com - sem) / sem
            print(f"    {modelo} {ponto}: de {efeito.min():+.1f}% a "
                  f"{efeito.max():+.1f}%")


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
