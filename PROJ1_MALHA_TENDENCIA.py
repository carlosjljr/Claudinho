# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - CONVERGENCIA DE MALHA: TENSAO DE VON MISES
# =====================================================================
# Cole este arquivo inteiro em UMA celula do Colab e rode.
#
# A tendencia NAO e uma reta: e o modelo de convergencia de malha,
#     s(h) = s0 - C * h^p
# do qual saem os dois numeros que vao para o texto -- s0, o valor
# extrapolado para malha infinitamente refinada, e p, a ordem observada
# de convergencia. Uma reta extrapolaria para um valor sem significado
# fisico em h = 0.
#
# A curva ajustada e desenhada apenas entre o menor e o maior elemento
# ensaiado; s0 aparece so na tabela impressa.
# =====================================================================
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# ---------------------------------------------------------------------
# DADOS
# ---------------------------------------------------------------------
ARESTA = [2.0, 1.8, 1.6, 1.4, 1.2, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]

SERIES = {
    "Tetraédrico de ordem um": [
        8.5937, 9.4742, 10.033, 10.995, 13.213, 15.272, 17.202, 15.692,
        17.396, 19.480, 21.301, 21.449, 25.511],
    "Tetraédrico de ordem dois": [
        18.002, 19.184, 19.139, 20.190, 22.695, 22.230, 23.625, 23.239,
        24.006, 24.814, 26.700, 27.127, 28.756],
    "Hexaédrico de ordem um": [
        19.684, 19.109, 20.307, 19.105, 21.945, 24.032, 22.535, 23.777,
        24.247, 24.721, 25.941, 28.283, np.nan],
    "Hexaédrico de ordem dois": [
        22.759, 23.548, 21.724, 20.565, 26.100, 22.873, 29.565, 24.690,
        24.440, 25.293, 26.666, np.nan, np.nan],
}

ARQUIVO = "grafico_tensao_tendencia.png"
ROTULO_Y = "Tensão (Von Mises) [MPa]"
SIMBOLO = "σ"
UNIDADE = "MPa"
PASSO_Y = 1.0        # uma linha de grade por MPa
PASSO_Y_MENOR = 0.5

EXPOENTES = np.arange(0.2, 3.001, 0.02)   # faixa de p varrida no ajuste


# ---------------------------------------------------------------------
# AJUSTE
# ---------------------------------------------------------------------
def ajustar(h, y):
    """Ajusta y = y0 - C*h^p e devolve (funcao, parametros).

    Para p fixo o modelo e LINEAR em (y0, C), entao em vez de um
    otimizador nao linear -- instavel com dados ruidosos como estes --
    varre-se p numa grade e resolve-se minimos quadrados para cada um.
    Sem scipy e muito mais estavel.
    """
    valido = np.isfinite(h) & np.isfinite(y)
    h, y = np.asarray(h, float)[valido], np.asarray(y, float)[valido]
    if h.size < 3:
        return None, {}

    melhor = None
    for p in EXPOENTES:
        base = np.column_stack((np.ones_like(h), -(h ** p)))
        (y0, c), *_ = np.linalg.lstsq(base, y, rcond=None)
        erro = np.sum((y - (y0 - c * h ** p)) ** 2)
        if melhor is None or erro < melhor[0]:
            melhor = (erro, y0, c, p)

    erro, y0, c, p = melhor
    total = np.sum((y - y.mean()) ** 2)
    r2 = float(1.0 - erro / total) if total > 0 else np.nan
    # p encostado na borda da grade significa que o ajuste queria um
    # expoente fora dela: o modelo nao descreve a serie e y0 vira
    # extrapolacao sem sentido fisico.
    no_limite = bool(p <= EXPOENTES[0] + 1e-9 or p >= EXPOENTES[-1] - 1e-9)
    return (lambda x: y0 - c * x ** p), {"y0": float(y0), "p": float(p),
                                         "r2": r2, "p_no_limite": no_limite}


def pontos_fora(y, fator=6.0, iteracoes=3):
    """Indices que destoam dos VIZINHOS, nao de um ajuste global.

    Um ponto muito fora puxa o proprio ajuste e faz os vizinhos
    parecerem errados tambem. Cada ponto e comparado com a media dos
    dois vizinhos, e a escala de referencia e o passo tipico da serie,
    entao o criterio se adapta a series justas e a series espalhadas.
    """
    marcados = []
    trabalho = np.array(y, dtype=float)
    for _ in range(iteracoes):
        indices = np.flatnonzero(np.isfinite(trabalho))
        if indices.size < 5:
            break
        valores = trabalho[indices]
        passos = np.abs(np.diff(valores))
        escala = 1.4826 * np.median(np.abs(passos - np.median(passos)))
        if not np.isfinite(escala) or escala <= 0:
            break
        desvio = np.zeros_like(valores)
        desvio[1:-1] = valores[1:-1] - 0.5 * (valores[:-2] + valores[2:])
        if not np.any(np.abs(desvio) > fator * escala):
            break
        pior = int(np.argmax(np.abs(desvio)))
        marcados.append(int(indices[pior]))
        trabalho[indices[pior]] = np.nan
    return sorted(marcados)


# ---------------------------------------------------------------------
# FIGURA E TABELA
# ---------------------------------------------------------------------
def grafico(h, series, arquivo, rotulo_y, passo_y, passo_y_menor):
    """Desenha os pontos medidos e a tendencia de cada serie."""
    h = np.asarray(h, float)
    paleta = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    fig, eixo = plt.subplots(figsize=(10, 8), layout="constrained")
    finos = np.linspace(h.min(), h.max(), 300)
    ajustes = {}

    for indice, (rotulo, valores) in enumerate(series.items()):
        cor = paleta[indice % len(paleta)]
        y = np.asarray(valores, float)

        # O dado medido domina a leitura; a tendencia entra apagada
        # atras dele, como apoio visual e nao como protagonista.
        eixo.plot(h, y, marker="o", color=cor, lw=1.6, ms=8, zorder=3,
                  label=rotulo)

        # O ponto fora da curva sai do AJUSTE, mas continua desenhado,
        # circulado, para a figura nao esconder o dado original.
        fora = pontos_fora(y)
        ajuste = y.copy()
        if fora:
            eixo.plot(h[fora], y[fora], "o", ms=16, mfc="none", mec=cor,
                      mew=2.0, zorder=4)
            ajuste[fora] = np.nan

        funcao, parametros = ajustar(h, ajuste)
        if funcao is None:
            continue
        parametros["fora"] = [float(h[i]) for i in fora]
        ajustes[rotulo] = parametros
        eixo.plot(finos, funcao(finos), linestyle="--", color=cor, lw=3.0,
                  alpha=0.40, zorder=1)

    eixo.set_xlabel("Tamanho dos elementos [mm]", fontsize=17)
    eixo.set_ylabel(rotulo_y, fontsize=17)
    eixo.set_xticks(h)
    eixo.set_xticklabels([f"{v:.1f}" for v in h], fontsize=16)
    eixo.tick_params(axis="y", labelsize=16)

    # Poucos pontos no eixo Y deixam a leitura grosseira: o passo das
    # marcas e fixado para dar uma linha de grade por unidade.
    eixo.yaxis.set_major_locator(MultipleLocator(passo_y))
    eixo.yaxis.set_minor_locator(MultipleLocator(passo_y_menor))
    eixo.grid(True, which="major", linestyle="--", linewidth=0.5)
    eixo.grid(True, which="minor", axis="y", linestyle=":", linewidth=0.4,
              alpha=0.5)

    # Uma entrada generica explica o tracejado, em vez de repetir uma
    # entrada de tendencia por curva.
    alcas, rotulos = eixo.get_legend_handles_labels()
    alcas.append(plt.Line2D([], [], color="0.35", linestyle="--", lw=3.0,
                            alpha=0.40))
    rotulos.append("tendência ajustada")
    eixo.legend(alcas, rotulos, fontsize=16, loc="lower left", frameon=False)

    fig.savefig(arquivo, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return ajustes


def tabela(ajustes, simbolo, unidade):
    """Parametros do ajuste, prontos para o texto do artigo."""
    print(f"\n=== TENDÊNCIA AJUSTADA ({simbolo} = {simbolo}₀ - C·h^p) ===")
    cabecalho = f"{simbolo}₀ [{unidade}]"
    print(f"{'série':<30} {cabecalho:>12} {'p':>7} {'R²':>7}  leitura")
    for rotulo, par in ajustes.items():
        if par["p_no_limite"]:
            leitura = f"não estabilizou — {simbolo}₀ não citável"
        elif par["r2"] < 0.80:
            leitura = f"ajuste fraco — não cite {simbolo}₀"
        elif par["p"] < 0.5:
            leitura = "convergência muito lenta"
        else:
            leitura = "ok"
        print(f"{rotulo:<30} {par['y0']:12.4f} {par['p']:7.2f} "
              f"{par['r2']:7.3f}  {leitura}")
    print(f"  {simbolo}₀ = valor extrapolado para h → 0; "
          f"p = ordem observada de convergência.")
    for rotulo, par in ajustes.items():
        if par["fora"]:
            arestas = ", ".join(f"{v:.1f}" for v in par["fora"])
            print(f"  ponto fora da curva em {rotulo}: aresta {arestas} mm "
                  f"(excluído do ajuste)")


# ---------------------------------------------------------------------
if __name__ == "__main__":
    AJUSTES = grafico(ARESTA, SERIES, ARQUIVO, ROTULO_Y, PASSO_Y,
                      PASSO_Y_MENOR)
    tabela(AJUSTES, SIMBOLO, UNIDADE)

    try:
        from IPython.display import Image, display
        display(Image(filename=ARQUIVO))
    except ImportError:
        pass
