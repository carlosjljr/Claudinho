# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - CONVERGENCIA DE MALHA: Von Mises nos pontos de prova
# =====================================================================
# Cole numa celula do Colab e rode. Nao depende dos outros modulos.
#
# Um unico grafico com os dois modelos. Tres canais visuais, um por
# fator, porque sao 8 series (2 modelos x 2 servos x 2 condicoes):
#   cor       -> servo   (Servo 1 preto, Servo 2 cinza)
#   traco     -> gravidade (sem = continuo, com = tracejado)
#   marcador  -> modelo  (MEE03 circulo, MEE10 quadrado)
# =====================================================================
import os
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MODELOS = ("MEE03", "MEE10")

ELEMENTOS = np.array([0.2, 0.4, 0.8, 1.0, 1.5])   # milhoes de elementos
# Malha escolhida. Nao e desenhada na figura; segue em uso para
# preencher a coluna tensao_malha_adotada_MPa da tabela.
FAIXA_ADOTADA = (0.7, 0.9)
LIMITE_CONVERGENCIA = 5.0                         # % de variacao aceita

# ATENCAO: as series antes se chamavam ENG 1 e ENG 2 (pontos de
# engaste). Foram renomeadas para Servo 1 e Servo 2 conforme pedido --
# confira se a correspondencia esta correta antes de publicar.
DADOS = {
    ("MEE03", "com gravidade"): {
        "Servo 1": [19.593, 34.305, 30.590, 41.674, 46.414],
        "Servo 2": [39.035, 26.362, 32.050, 34.209, 34.339],
    },
    ("MEE03", "sem gravidade"): {
        "Servo 1": [18.705, 24.235, 20.665, 21.556, 33.037],
        "Servo 2": [20.664, 25.456, 31.147, 37.697, 28.234],
    },
    ("MEE10", "com gravidade"): {
        "Servo 1": [21.335, 21.435, 28.325, 28.277, 38.338],
        "Servo 2": [33.003, 28.083, 31.020, 34.671, 34.031],
    },
    ("MEE10", "sem gravidade"): {
        "Servo 1": [20.620, 20.714, 27.261, 26.865, 36.095],
        "Servo 2": [31.449, 27.110, 29.392, 32.622, 32.093],
    },
}

# --- Codificacao visual ----------------------------------------------
# Troque "0.45" por "tab:red" se preferir o vermelho ao cinza.
CORES = {"Servo 1": "#000000", "Servo 2": "0.45"}
ESTILO_GRAVIDADE = {"sem gravidade": "-", "com gravidade": "--"}
MARCAS = {"MEE03": "o", "MEE10": "s"}

PASTA_SAIDA = "/content/drive/MyDrive/CTG_UFPE/PROJETOS/PROJ 1/RESULTADOS"
FORMATOS = ("png", "pdf")
FIG_TAMANHO = (7.5, 5.0)
MOSTRAR_FIGURAS = True

# Fontes. O rotulo do eixo Y ja estava grande o bastante, entao ficou
# menor que os demais de proposito.
FONTE_EIXO_Y = 14
FONTE_EIXO_X = 17
FONTE_MARCAS = 15
FONTE_LEGENDA = 15

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.size": FONTE_MARCAS,
    "axes.titlesize": FONTE_EIXO_X,
    "axes.labelsize": FONTE_EIXO_X,
    "legend.fontsize": FONTE_LEGENDA,
    "xtick.labelsize": FONTE_MARCAS,
    "ytick.labelsize": FONTE_MARCAS,
    "axes.grid": True, "grid.linestyle": "--", "grid.linewidth": 0.4,
    "grid.alpha": 0.6,
})


def garantir_drive_malha():
    """Monta o Drive se estiver no Colab e ainda nao estiver montado."""
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
    for (modelo, condicao), series in DADOS.items():
        for serie_nome, valores in series.items():
            serie = np.asarray(valores, float)
            variacao = 100.0 * np.abs(np.diff(serie)) / np.abs(serie[:-1])
            linhas.append({
                "modelo": modelo,
                "condicao": condicao,
                "serie": serie_nome,
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


def salvar_figura_malha(fig, nome, tentativas=3):
    """Salva a figura tolerando falha transitoria do Drive montado."""
    for formato in FORMATOS:
        caminho = os.path.join(PASTA_SAIDA, f"{nome}.{formato}")
        for tentativa in range(1, tentativas + 1):
            try:
                os.makedirs(PASTA_SAIDA, exist_ok=True)
                fig.savefig(caminho, format=formato)
                break
            except OSError as erro:
                if tentativa == tentativas:
                    print(f"  ! nao foi possivel salvar {os.path.basename(caminho)}"
                          f" ({type(erro).__name__}); seguindo adiante")
                else:
                    time.sleep(1.0)
    if MOSTRAR_FIGURAS:
        plt.show()
    plt.close(fig)


def figura_malha():
    """Os dois modelos num unico grafico."""
    fig, eixo = plt.subplots(figsize=FIG_TAMANHO, layout="constrained")

    for modelo in MODELOS:
        for condicao, traco in ESTILO_GRAVIDADE.items():
            for serie_nome, cor in CORES.items():
                eixo.plot(ELEMENTOS, DADOS[(modelo, condicao)][serie_nome],
                          marker=MARCAS[modelo], linestyle=traco, color=cor,
                          ms=6, lw=1.5, markerfacecolor="none", markeredgewidth=1.4)

    eixo.set_xticks(ELEMENTOS)
    eixo.set_xticklabels([f"{v:.1f}" for v in ELEMENTOS])
    eixo.set_xlabel("Número de elementos [$\\times 10^6$]", fontsize=FONTE_EIXO_X)
    eixo.set_ylabel("Tensão equivalente de Von Mises [MPa]", fontsize=FONTE_EIXO_Y)

    # Legenda em tres blocos, um por canal visual: 6 entradas explicam
    # as 8 curvas, em vez de listar uma entrada por curva.
    def linha(**kwargs):
        base = dict(color="0.2", linestyle="-", marker="None", lw=1.5)
        base.update(kwargs)
        return plt.Line2D([], [], **base)

    # Montada a partir dos dicionarios de configuracao: se voce remover
    # uma condicao de ESTILO_GRAVIDADE para deixar a figura mais limpa,
    # a legenda acompanha sozinha.
    marcadores = [linha(color=cor, label=nome) for nome, cor in CORES.items()]
    marcadores += [linha(linestyle=traco, label=nome)
                   for nome, traco in ESTILO_GRAVIDADE.items()]
    marcadores += [linha(linestyle="None", marker=MARCAS[modelo], ms=6,
                         markerfacecolor="none", markeredgewidth=1.4,
                         label=modelo) for modelo in MODELOS]
    eixo.legend(handles=marcadores, loc="upper center",
                bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False,
                handlelength=2.2, columnspacing=1.6)

    salvar_figura_malha(fig, "malha_tensao_von_mises")


def figura_convergencia(convergencia):
    """Variacao percentual a cada refino, tambem num grafico so."""
    fig, eixo = plt.subplots(figsize=FIG_TAMANHO, layout="constrained")
    passos = [f"{ELEMENTOS[i]:.1f}→{ELEMENTOS[i+1]:.1f}"
              for i in range(len(ELEMENTOS) - 1)]

    for modelo in MODELOS:
        for serie_nome, cor in CORES.items():
            serie = np.asarray(DADOS[(modelo, "com gravidade")][serie_nome], float)
            variacao = 100.0 * np.abs(np.diff(serie)) / np.abs(serie[:-1])
            eixo.plot(passos, variacao, marker=MARCAS[modelo], color=cor,
                      ms=6, lw=1.5, markerfacecolor="none", markeredgewidth=1.4,
                      label=f"{modelo} — {serie_nome}")

    eixo.axhline(LIMITE_CONVERGENCIA, color="k", linestyle=":", lw=1.4)
    eixo.text(0.01, LIMITE_CONVERGENCIA, f" {LIMITE_CONVERGENCIA:.0f}%",
              va="bottom", fontsize=FONTE_MARCAS,
              transform=eixo.get_yaxis_transform())
    eixo.set_yscale("log")
    eixo.set_xlabel("Refino [$\\times 10^6$ elementos]", fontsize=FONTE_EIXO_X)
    eixo.set_ylabel("Variação da tensão (%)", fontsize=FONTE_EIXO_Y)
    eixo.tick_params(axis="x", rotation=20)
    eixo.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2,
                frameon=False, handlelength=2.2)
    salvar_figura_malha(fig, "malha_convergencia")


def executar_malha():
    garantir_drive_malha()
    convergencia = tabela_convergencia()

    print("=== CONVERGENCIA DE MALHA (com gravidade) ===")
    vista = convergencia[convergencia["condicao"] == "com gravidade"]
    print(vista[["modelo", "serie", "tensao_malha_adotada_MPa",
                 "tensao_malha_fina_MPa", "variacao_ultimo_refino_pct",
                 "variacao_maxima_pct", "monotonico", "convergido"]]
          .round(2).to_string(index=False))

    nao_convergiram = convergencia[~convergencia["convergido"]]
    if not nao_convergiram.empty:
        print(f"\n! {len(nao_convergiram)} série(s) NÃO convergiram "
              f"(variação > {LIMITE_CONVERGENCIA:.0f}% no último refino):")
        for _, linha in nao_convergiram.iterrows():
            print(f"    {linha['modelo']:6s} {linha['serie']:8s} "
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
