# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - MALHA x GRAVIDADE: DEFORMACAO TOTAL
# =====================================================================
# Cole este arquivo inteiro em UMA celula do Colab e rode.
#
# Mesma codificacao visual da figura de tensao:
#     cor + marcador -> modelo (MEE03 preto/circulo, MEE10 cinza/quadrado)
#     traco          -> gravidade (sem = continuo, com = tracejado)
#
# As series antes chamadas "Primária" e "Final" sao o MEE03 e o MEE10.
# A serie "Central" foi descartada, conforme pedido.
# =====================================================================
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# DADOS - deformacao total [mm]
# ---------------------------------------------------------------------
ELEMENTOS = [0.2, 0.4, 0.8, 1.0, 1.5]        # milhoes de elementos

DEFORMACAO = {
    ("MEE03", "sem gravidade"): [4.4105, 5.1237, 4.8736, 4.9944, 4.9952],
    ("MEE03", "com gravidade"): [4.7456, 5.4779, 5.2337, 5.3518, 5.3536],
    ("MEE10", "sem gravidade"): [5.5175, 5.2692, 5.1151, 5.2310, 5.2143],
    ("MEE10", "com gravidade"): [5.9964, 5.7072, 5.5146, 5.6373, 5.6008],
}

ARQUIVO = "grafico_deformacao_gravidade.png"
ROTULO_Y = "Deformação total [mm]"
MODELOS = ("MEE03", "MEE10")
CORES = {"MEE03": "#000000", "MEE10": "0.45"}
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


def grafico(arquivo):
    """Os dois modelos, com e sem gravidade, num unico grafico."""
    h = np.asarray(ELEMENTOS, float)
    fig, eixo = plt.subplots(figsize=(7.5, 5.0), layout="constrained")

    for modelo in MODELOS:
        for condicao, traco in TRACOS.items():
            eixo.plot(h, DEFORMACAO[(modelo, condicao)],
                      marker=MARCAS[modelo], linestyle=traco,
                      color=CORES[modelo], ms=6, lw=1.5,
                      markerfacecolor="none", markeredgewidth=1.4)

    eixo.set_xticks(h)
    eixo.set_xticklabels([f"{v:.1f}" for v in h])
    eixo.set_xlabel("Número de elementos [$\\times 10^6$]")
    eixo.set_ylabel(ROTULO_Y, fontsize=14)

    # Legenda em dois blocos, um por canal visual.
    def alca(**kwargs):
        base = dict(color="0.2", linestyle="-", marker="None", lw=1.5)
        base.update(kwargs)
        return plt.Line2D([], [], **base)

    alcas = [alca(color=CORES[m], marker=MARCAS[m], ms=6,
                  markerfacecolor="none", markeredgewidth=1.4, label=m)
             for m in MODELOS]
    alcas += [alca(linestyle=t, label=c) for c, t in TRACOS.items()]
    eixo.legend(handles=alcas, loc="upper center", bbox_to_anchor=(0.5, -0.16),
                ncol=2, frameon=False, handlelength=2.2, columnspacing=1.6)

    fig.savefig(arquivo)
    plt.close(fig)
    return arquivo


def tabela():
    """Efeito da gravidade e estabilidade com o refino, para o texto."""
    print("\n=== DEFORMAÇÃO TOTAL ===")
    print(f"{'série':<26} {'malha fina':>11} {'último refino':>14} "
          f"{'máxima':>8}")
    for modelo in MODELOS:
        for condicao in TRACOS:
            serie = np.asarray(DEFORMACAO[(modelo, condicao)], float)
            variacao = 100.0 * np.abs(np.diff(serie)) / np.abs(serie[:-1])
            print(f"{modelo + ' ' + condicao:<26} {serie[-1]:8.4f} mm "
                  f"{variacao[-1]:12.1f}% {variacao.max():7.1f}%")

    print("\n  Efeito da gravidade na malha mais fina:")
    for modelo in MODELOS:
        com = DEFORMACAO[(modelo, "com gravidade")][-1]
        sem = DEFORMACAO[(modelo, "sem gravidade")][-1]
        print(f"    {modelo}: {com - sem:+.4f} mm "
              f"({100.0 * (com - sem) / sem:+.1f}%)")


# ---------------------------------------------------------------------
if __name__ == "__main__":
    grafico(ARQUIVO)
    tabela()

    try:
        from IPython.display import Image, display
        display(Image(filename=ARQUIVO))
    except ImportError:
        pass
