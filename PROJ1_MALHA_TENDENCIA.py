# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - CONVERGENCIA DE MALHA POR TAMANHO DE ELEMENTO
#          com linha de tendencia por curva
# =====================================================================
# Cole numa celula do Colab e rode.
#
# A tendencia padrao NAO e uma reta: e o modelo de convergencia de
# malha, sigma(h) = sigma0 - C * h^p, que e o que descreve uma solucao
# de elementos finitos quando o elemento encolhe. Dele saem dois numeros
# que valem no artigo:
#     sigma0 -> tensao extrapolada para malha infinitamente refinada
#     p      -> ordem observada de convergencia
# Uma reta ajustada a sigma(h) extrapolaria para um valor sem
# significado fisico em h = 0.
# =====================================================================
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MultipleLocator

# ---------------------------------------------------------------------
# AJUSTE DA TENDENCIA
# ---------------------------------------------------------------------
EXPOENTES = np.arange(0.2, 3.001, 0.02)   # faixa de p varrida no ajuste


def ajustar_divergente(h, sigma):
    """Ajusta sigma = A * h^(-lambda): tensao SEM valor limite.

    E o comportamento de uma singularidade geometrica (canto vivo), em
    que a solucao exata da elasticidade e infinita no ponto e nenhum
    elemento, de qualquer ordem, estabiliza. Serve para comparar com o
    modelo convergente: se os dois ajustam igualmente bem, o estudo de
    malha nao tem alcance para distinguir um caso do outro.
    """
    valido = np.isfinite(h) & np.isfinite(sigma)
    h, sigma = np.asarray(h, float)[valido], np.asarray(sigma, float)[valido]
    if h.size < 3 or np.any(h <= 0) or np.any(sigma <= 0):
        return {}
    a, b = np.polyfit(np.log(h), np.log(sigma), 1)
    previsto = np.exp(b) * h ** a
    total = np.sum((sigma - sigma.mean()) ** 2)
    r2 = float(1.0 - np.sum((sigma - previsto) ** 2) / total) if total > 0 else np.nan
    return {"lambda": float(-a), "A": float(np.exp(b)), "r2": r2}


def detectar_fora_da_curva(h, y, modelo="potencia", fator=6.0, iteracoes=3):
    """Indices que destoam dos VIZINHOS, nao de um ajuste global.

    Comparar com a curva ajustada nao funciona aqui: um ponto muito
    fora puxa o proprio ajuste e faz os vizinhos parecerem errados
    tambem. Cada ponto e comparado com a media dos dois vizinhos, e a
    escala de referencia e o passo tipico da serie (desvio absoluto
    mediano das diferencas consecutivas). Assim o criterio se adapta
    sozinho a series justas e a series espalhadas.
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

        # desvio de cada ponto interno em relacao aos vizinhos
        desvio = np.full(valores.shape, 0.0)
        desvio[1:-1] = valores[1:-1] - 0.5 * (valores[:-2] + valores[2:])
        excesso = np.abs(desvio) / (fator * escala)
        if not np.any(excesso > 1.0):
            break
        pior = int(np.argmax(excesso))
        marcados.append(int(indices[pior]))
        trabalho[indices[pior]] = np.nan
    return sorted(marcados)


def ajustar_tendencia(h, sigma, modelo="potencia"):
    """Ajusta a tendencia de sigma(h) e devolve a funcao e os parametros.

    "potencia" (padrao): sigma = sigma0 - C*h^p. Para p fixo o modelo e
    LINEAR em (sigma0, C), entao em vez de um otimizador nao linear --
    instavel com dados ruidosos como estes -- varre-se p numa grade e
    resolve-se minimos quadrados para cada um, ficando com o melhor.
    Sem dependencia de scipy e muito mais estavel.

    "linear": sigma = a*h + b.
    "log":    sigma = a*ln(h) + b.

    Devolve (funcao_da_tendencia, parametros_dict).
    """
    valido = np.isfinite(h) & np.isfinite(sigma)
    h, sigma = np.asarray(h, float)[valido], np.asarray(sigma, float)[valido]
    if h.size < 3:
        return None, {}

    def r2(previsto):
        residuo = np.sum((sigma - previsto) ** 2)
        total = np.sum((sigma - sigma.mean()) ** 2)
        return float(1.0 - residuo / total) if total > 0 else np.nan

    if modelo == "linear":
        a, b = np.polyfit(h, sigma, 1)
        funcao = lambda x: a * x + b
        return funcao, {"a": a, "b": b, "sigma0": b, "r2": r2(funcao(h))}

    if modelo == "log":
        a, b = np.polyfit(np.log(h), sigma, 1)
        funcao = lambda x: a * np.log(x) + b
        return funcao, {"a": a, "b": b, "sigma0": np.nan, "r2": r2(funcao(h))}

    melhor = None
    for p in EXPOENTES:
        base = np.column_stack((np.ones_like(h), -(h ** p)))
        (sigma0, c), *_ = np.linalg.lstsq(base, sigma, rcond=None)
        erro = np.sum((sigma - (sigma0 - c * h ** p)) ** 2)
        if melhor is None or erro < melhor[0]:
            melhor = (erro, sigma0, c, p)

    _, sigma0, c, p = melhor
    funcao = lambda x: sigma0 - c * x ** p
    # p encostado na borda da grade significa que o ajuste queria um
    # expoente fora dela: o modelo de convergencia nao descreve a serie,
    # e sigma0 vira extrapolacao sem sentido fisico.
    no_limite = bool(p <= EXPOENTES[0] + 1e-9 or p >= EXPOENTES[-1] - 1e-9)
    return funcao, {"sigma0": float(sigma0), "C": float(c), "p": float(p),
                    "r2": r2(funcao(h)), "p_no_limite": no_limite}


# ---------------------------------------------------------------------
# FIGURA
# ---------------------------------------------------------------------
def gerar_grafico_tensao(tamanhos_malha, dados_series, caminho_saida,
                         dpi=300, escala_y=None, modelo_tendencia="potencia",
                         mostrar_tendencia=True, mostrar_assintota=True,
                         inverter_eixo_x=False, cores=None,
                         rotulo_y="Tensão (Von Mises) [MPa]",
                         simbolo="σ", ignorar_fora_da_curva=False,
                         passo_y=None, passo_y_menor=None,
                         limitar_aos_dados=False,
                         extrapolar_tendencia=True):
    """Tensao x tamanho do elemento, com a tendencia de cada curva.

    mostrar_assintota: marca sigma0 (o valor para h -> 0) com um traco
    horizontal fino, que e justamente o resultado que o estudo de malha
    procura.
    inverter_eixo_x: coloca o refino crescendo para a direita.
    """
    h = np.asarray(tamanhos_malha, float)
    paleta = cores or plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, eixo = plt.subplots(figsize=(10, 8), layout="constrained")
    ajustes, assintotas_desenhadas = {}, []

    for indice, (rotulo, valores) in enumerate(dados_series.items()):
        cor = paleta[indice % len(paleta)]
        sigma = np.asarray(valores, float)

        # O dado medido domina a leitura; a tendencia entra apagada
        # atras dele, como apoio visual e nao como protagonista.
        eixo.plot(h, sigma, marker="o", linestyle="-", color=cor,
                  lw=1.6, alpha=1.0, ms=8, zorder=3, label=rotulo)

        if not mostrar_tendencia:
            continue

        # Um unico ponto muito fora arrasta o ajuste inteiro. Quando
        # pedido, ele sai do AJUSTE mas continua desenhado, circulado,
        # para a figura nao esconder o dado original.
        sigma_ajuste = sigma.copy()
        fora = detectar_fora_da_curva(h, sigma, modelo_tendencia)
        if fora and ignorar_fora_da_curva:
            eixo.plot(h[fora], sigma[fora], "o", ms=16, mfc="none",
                      mec=cor, mew=2.0, zorder=4)
            sigma_ajuste[fora] = np.nan
        funcao, parametros = ajustar_tendencia(h, sigma_ajuste, modelo_tendencia)
        if fora:
            parametros["fora_da_curva"] = [float(h[i]) for i in fora]
        if funcao is None:
            continue
        ajustes[rotulo] = parametros

        # So se estende a tendencia ate h = 0 quando o ajuste merece
        # confianca. Extrapolar uma serie que nao converge joga a curva
        # para fora da escala e sugere um valor que nao existe.
        confiavel = (modelo_tendencia == "potencia"
                     and not parametros.get("p_no_limite")
                     and parametros.get("r2", 0) >= 0.80)
        estende = confiavel and extrapolar_tendencia and not limitar_aos_dados
        inicio = 0.0 if estende else h.min()
        finos = np.linspace(inicio, h.max(), 300)
        if modelo_tendencia == "log":
            finos = finos[finos > 0]
        eixo.plot(finos, funcao(finos), linestyle="--", color=cor,
                  lw=3.0, alpha=0.40, zorder=1)

        if (mostrar_assintota and estende
                and np.isfinite(parametros.get("sigma0", np.nan))):
            eixo.axhline(parametros["sigma0"], color=cor, linestyle=":",
                         lw=1.0, alpha=0.6)
            assintotas_desenhadas.append(rotulo)

    eixo.set_xlabel("Tamanho dos elementos [mm]", fontsize=17)
    eixo.set_ylabel(rotulo_y, fontsize=17)
    eixo.set_xticks(h)
    eixo.set_xticklabels([f"{v:.1f}" for v in h], fontsize=16)
    eixo.tick_params(axis="y", labelsize=16)
    if escala_y is not None:
        eixo.set_ylim(escala_y)
    elif limitar_aos_dados:
        # Enquadra exatamente o que foi medido: sem margem automatica
        # nem trecho de tendencia alem do ultimo ponto.
        todos = np.concatenate([np.asarray(v, float)
                                for v in dados_series.values()])
        todos = todos[np.isfinite(todos)]
        if todos.size:
            folga = 0.02 * (todos.max() - todos.min())
            eixo.set_ylim(todos.min() - folga, todos.max() + folga)
    if limitar_aos_dados:
        eixo.set_xlim(h.min(), h.max())
    if inverter_eixo_x:
        eixo.invert_xaxis()

    # Poucos pontos no eixo Y deixam a leitura grosseira: o passo das
    # marcas e fixado aqui para dar uma linha de grade por unidade.
    if passo_y:
        eixo.yaxis.set_major_locator(MultipleLocator(passo_y))
        if passo_y_menor:
            eixo.yaxis.set_minor_locator(MultipleLocator(passo_y_menor))
        else:
            eixo.yaxis.set_minor_locator(AutoMinorLocator(2))
    eixo.grid(True, which="major", linestyle="--", linewidth=0.5)
    eixo.grid(True, which="minor", axis="y", linestyle=":", linewidth=0.4,
              alpha=0.5)

    # Uma entrada generica explica o tracejado, em vez de repetir uma
    # entrada de tendencia por curva.
    alcas, rotulos = eixo.get_legend_handles_labels()
    if mostrar_tendencia:
        alcas.append(plt.Line2D([], [], color="0.35", linestyle="--",
                                lw=3.0, alpha=0.40))
        rotulos.append("tendência ajustada")
        if assintotas_desenhadas:
            alcas.append(plt.Line2D([], [], color="0.35", linestyle=":", lw=1.0))
            rotulos.append(f"${simbolo}_0$ (malha infinita)")
    eixo.legend(alcas, rotulos, fontsize=16, loc="lower left", frameon=False)

    fig.savefig(caminho_saida, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return ajustes


def comparar_modelos(tamanhos, dados_series):
    """Convergente x divergente: o estudo distingue os dois casos?"""
    h = np.asarray(tamanhos, float)
    print("\n=== O ESTUDO DISTINGUE CONVERGÊNCIA DE SINGULARIDADE? ===")
    print(f"{'série':<30} {'R² converge':>12} {'R² diverge':>11} {'λ':>6}  conclusão")
    for rotulo, valores in dados_series.items():
        sigma = np.asarray(valores, float)
        _, conv = ajustar_tendencia(h, sigma, "potencia")
        div = ajustar_divergente(h, sigma)
        if not conv or not div:
            continue
        diferenca = conv.get("r2", 0) - div.get("r2", 0)
        if abs(diferenca) < 0.05:
            conclusao = "empate — dado não decide"
        elif diferenca > 0:
            conclusao = "converge melhor"
        else:
            conclusao = "diverge melhor"
        print(f"{rotulo:<30} {conv.get('r2', np.nan):12.3f} "
              f"{div.get('r2', np.nan):11.3f} {div.get('lambda', np.nan):6.3f}"
              f"  {conclusao}")
    print("  Empate significa que a faixa de malhas ensaiada é curta demais "
          "para\n  separar uma tensão que converge devagar de uma que não "
          "converge.\n  Nos dois casos o pico de tensão não pode ser "
          "reportado como convergido.")


def imprimir_ajustes(ajustes, modelo="potencia", unidade="MPa", simbolo="σ"):
    """Tabela dos parametros, para ir ao texto do artigo."""
    if not ajustes:
        return
    print(f"\n=== TENDÊNCIA AJUSTADA (modelo: {modelo}) ===")
    if modelo == "potencia":
        cabecalho = f"{simbolo}₀ [{unidade}]"
        print(f"{'série':<30} {cabecalho:>12} {'p':>7} {'R²':>7}  leitura")
        for rotulo, par in ajustes.items():
            r2 = par.get("r2", np.nan)
            if par.get("p_no_limite"):
                leitura = "não estabilizou — σ₀ não citável"
            elif r2 < 0.80:
                leitura = "ajuste fraco — não cite σ₀"
            elif par.get("p", 0) < 0.5:
                leitura = "convergência muito lenta"
            else:
                leitura = "ok"
            print(f"{rotulo:<30} {par['sigma0']:12.4f} {par['p']:7.2f} "
                  f"{r2:7.3f}  {leitura}")
        print(f"  {simbolo}₀ = valor extrapolado para h → 0; "
              f"p = ordem observada de convergência.")
        pinados = [r for r, p in ajustes.items() if p.get("p_no_limite")]
        if pinados:
            print(f"  ! {len(pinados)} série(s) com p na borda da grade: a "
                  f"tensão ainda sobe quando o\n    elemento encolhe, em vez "
                  f"de estabilizar. A tendência serve para mostrar\n    essa "
                  f"direção, mas σ₀ NÃO pode ser citado como tensão "
                  f"convergida.\n    É o comportamento típico de "
                  f"singularidade geométrica (canto vivo).")
    else:
        print(f"{'série':<30} {'a':>10} {'b':>10} {'R²':>7}")
        for rotulo, par in ajustes.items():
            print(f"{rotulo:<30} {par['a']:10.3f} {par['b']:10.3f} "
                  f"{par.get('r2', np.nan):7.3f}")


# ---------------------------------------------------------------------
if __name__ == "__main__":
    tamanhos = [2.0, 1.8, 1.6, 1.4, 1.2, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    series = {
        "Tetraédrico de ordem um":   [8.5937, 9.4742, 10.033, 10.995, 13.213,
                                      15.272, 17.202, 15.692, 17.396, 19.480,
                                      21.301, 21.449, 25.511],
        "Tetraédrico de ordem dois": [18.0020, 19.1840, 19.139, 20.190, 22.695,
                                      22.230, 23.625, 23.239, 24.006, 24.814,
                                      26.700, 27.127, 28.756],
        "Hexaédrico de ordem um":    [19.6840, 19.1090, 20.307, 19.105, 21.945,
                                      24.032, 22.535, 23.777, 24.247, 24.721,
                                      25.941, 28.283, np.nan],
        "Hexaédrico de ordem dois":  [22.7590, 23.5480, 21.724, 20.565, 26.100,
                                      22.873, 29.565, 24.690, 24.440, 25.293,
                                      26.666, np.nan, np.nan],
    }

    ajustes = gerar_grafico_tensao(
        tamanhos, series, "grafico_tensao_tendencia.png",
        escala_y=None, passo_y=1.0, passo_y_menor=0.5,
        modelo_tendencia="potencia",
    )
    imprimir_ajustes(ajustes, "potencia")
    comparar_modelos(tamanhos, series)

    try:
        from IPython.display import Image, display
        display(Image(filename="grafico_tensao_tendencia.png"))
    except ImportError:
        pass
