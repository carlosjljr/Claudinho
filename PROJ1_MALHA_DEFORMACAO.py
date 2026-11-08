# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - CONVERGENCIA DE MALHA: DEFORMAÇÃO TOTAL NO EXTREMO LIVRE
# =====================================================================
# Cole este arquivo inteiro em UMA celula do Colab e rode.
# Autocontido: nao depende de nenhum outro modulo.
#
# Deformacao total no extremo livre em funcao do comprimento de aresta,
# para as quatro formulacoes de elemento, com a tendencia de cada curva.
#
# A tendencia NAO e uma reta: e o modelo de convergencia de malha,
#     u(h) = u0 - C * h^p
# do qual saem dois numeros publicaveis -- u0, o deslocamento
# extrapolado para malha infinitamente refinada, e p, a ordem observada
# de convergencia. Diferente da tensao, o deslocamento e uma grandeza
# integral e nao sofre de singularidade geometrica: aqui as quatro
# formulacoes convergem de fato.
#
# ATENCAO AOS DADOS: o ponto de 1,8 mm das duas series de ordem dois
# destoa em +0,5875 mm nas DUAS, valor identico ate a quarta casa. Duas
# formulacoes independentes nao erram a mesma quantidade: e erro de
# transcricao, nao resultado. O script o detecta, tira do ajuste e o
# desenha circulado. Corrija na planilha e ele deixa de ser marcado.
# =====================================================================
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MultipleLocator

EXPOENTES = np.arange(0.2, 3.001, 0.02)   # faixa de p varrida no ajuste


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
                         rotulo_y="Deformação total [mm]",
                         simbolo="σ", ignorar_fora_da_curva=False,
                         passo_y=None, passo_y_menor=None,
                         limitar_aos_dados=False):
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
        inicio = 0.0 if (confiavel and not limitar_aos_dados) else h.min()
        finos = np.linspace(inicio, h.max(), 300)
        if modelo_tendencia == "log":
            finos = finos[finos > 0]
        eixo.plot(finos, funcao(finos), linestyle="--", color=cor,
                  lw=3.0, alpha=0.40, zorder=1)

        if (mostrar_assintota and confiavel and not limitar_aos_dados
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



# ---------------------------------------------------------------------
# DADOS — Tabela 2: deformação total no extremo livre [mm]
# ---------------------------------------------------------------------
COMPRIMENTO_ARESTA = [2.0, 1.8, 1.6, 1.4, 1.2, 1.0, 0.9, 0.8, 0.7, 0.6,
                      0.5, 0.4, 0.3]

DEFORMACAO = {
    "Tetraédrico de ordem um": [
        2.4930, 2.5322, 2.6161, 2.7320, 2.8160, 2.9418, 2.9722, 3.0300,
        3.0594, 3.1031, 3.1377, 3.1671, 3.1902],
    "Tetraédrico de ordem dois": [
        3.2034, 3.7939, 3.2095, 3.2125, 3.2149, 3.2171, 3.2181, 3.2192,
        3.2201, 3.2207, 3.2213, 3.2219, np.nan],
    #           ^^^^^^ suspeito: esperado ~3,2064
    "Hexaédrico de ordem um": [
        2.7942, 2.8630, 3.0110, 3.0319, 3.1216, 3.1539, 3.1514, 3.1724,
        3.1795, 3.1951, 3.2017, 3.2083, 3.2152],
    "Hexaédrico de ordem dois": [
        3.2108, 3.7980, 3.2103, 3.2141, 3.2157, 3.2181, 3.2184, 3.2202,
        3.2203, 3.2206, 3.2214, 3.2219, 3.2222],
    #           ^^^^^^ suspeito: esperado ~3,2106
}

ARQUIVO_SAIDA = "grafico_deformacao_tendencia.png"
# None = escala automatica, com TODOS os pontos dentro do quadro
# (inclusive os dois de 1,8 mm). Para dar zoom no trecho convergido,
# use (2.45, 3.30).
ESCALA_Y = None
PASSO_Y = 0.1          # uma linha de grade a cada 0,1 mm
PASSO_Y_MENOR = 0.05


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
                leitura = f"não estabilizou — {simbolo}₀ não citável"
            elif r2 < 0.80:
                leitura = f"ajuste fraco — não cite {simbolo}₀"
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
                  f"grandeza ainda sobe quando o\n    elemento encolhe, em vez "
                  f"de estabilizar. A tendência serve para mostrar\n    essa "
                  f"direção, mas {simbolo}₀ NÃO pode ser citado como valor "
                  f"convergida.\n    É o comportamento típico de "
                  f"singularidade geométrica (canto vivo).")
    else:
        print(f"{'série':<30} {'a':>10} {'b':>10} {'R²':>7}")
        for rotulo, par in ajustes.items():
            print(f"{rotulo:<30} {par['a']:10.3f} {par['b']:10.3f} "
                  f"{par.get('r2', np.nan):7.3f}")


# ---------------------------------------------------------------------
if __name__ == "__main__":
    ajustes = gerar_grafico_tensao(
        COMPRIMENTO_ARESTA, DEFORMACAO, ARQUIVO_SAIDA,
        escala_y=ESCALA_Y, passo_y=PASSO_Y, passo_y_menor=PASSO_Y_MENOR,
        limitar_aos_dados=True,
        rotulo_y="Deformação total [mm]",
        simbolo="u",
        ignorar_fora_da_curva=True,
    )
    imprimir_ajustes(ajustes, "potencia", unidade="mm", simbolo="u")

    for serie, parametros in ajustes.items():
        if parametros.get("fora_da_curva"):
            arestas = ", ".join(f"{v:.1f}" for v in parametros["fora_da_curva"])
            print(f"  ponto fora da curva em {serie}: aresta {arestas} mm "
                  f"(excluído do ajuste, desenhado circulado)")

    try:
        from IPython.display import Image, display
        display(Image(filename=ARQUIVO_SAIDA))
    except ImportError:
        pass
