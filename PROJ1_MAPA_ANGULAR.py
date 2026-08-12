# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - MAPA ANGULAR: erro de posicao e repetibilidade dos atuadores
# =====================================================================
# Cole numa celula do Colab e rode. Nao depende dos outros modulos.
#
# Malha 5x5 de posicoes comandadas (0, 45, 90, 135, 180 graus em cada
# atuador). Para cada combinacao mede-se o angulo efetivo dos dois
# atuadores; a cinematica direta converte em posicao do efetuador e o
# erro cartesiano sai da distancia ate o alvo.
# =====================================================================
import os
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ALVOS = (0.0, 45.0, 90.0, 135.0, 180.0)

# Comprimentos de PROJETO dos elos (mm). Ver o aviso de consistencia no
# fim do arquivo: eles nao batem com o raio medido na filmagem.
PROTOTIPOS = {
    "PE01": {
        "L": (114.14, 109.50),
        "theta1": [0.0] * 5 + [53.9] * 5 + [93.6] * 5 + [135.5] * 5 + [181.3] * 5,
        "theta2": [-5.9, 38.4, 82.4, 123.6, 164.9,
                   -5.4, 41.0, 84.3, 122.6, 163.5,
                   -4.0, 41.9, 83.9, 121.9, 163.8,
                   -2.4, 42.9, 83.3, 119.9, 163.6,
                   -2.9, 42.1, 81.0, 119.2, 163.4],
    },
    "PE02": {
        "L": (108.15, 104.16),
        "theta1": [0.0] * 5 + [47.5] * 5 + [88.5] * 5 + [129.1] * 5 + [174.5] * 5,
        "theta2": [-0.3, 44.7, 87.1, 122.1, 164.8,
                   -0.8, 47.4, 86.8, 122.9, 164.5,
                    1.6, 45.9, 87.5, 122.6, 166.0,
                    0.5, 45.9, 84.9, 120.8, 165.7,
                    0.9, 47.1, 87.8, 124.9, 166.7],
    },
}

# Raio do efetuador medido na FILMAGEM (AB+BC das abas I_S1_*), para o
# teste de consistencia. Deixe None para pular a verificacao.
RAIO_FILMAGEM = {"PE01": 306.32, "PE02": 231.59}

PASTA_SAIDA = "/content/drive/MyDrive/CTG_UFPE/PROJETOS/PROJ 1/RESULTADOS"
FORMATOS = ("png", "pdf")
FIG_TAMANHO = (7.0, 4.5)
MOSTRAR_FIGURAS = True

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
    "legend.fontsize": 9, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.grid": True, "grid.linestyle": "--", "grid.linewidth": 0.4,
    "grid.alpha": 0.6, "lines.linewidth": 1.3,
})


def garantir_drive_mapa():
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


def malha_comandada():
    """Devolve (theta1_desejado, theta2_desejado) da malha 5x5."""
    t1 = np.repeat(ALVOS, len(ALVOS)).astype(float)
    t2 = np.tile(ALVOS, len(ALVOS)).astype(float)
    return t1, t2


def cinematica_direta(theta1, theta2, L1, L2):
    """Posicao do efetuador. theta2 e medido a partir da perpendicular."""
    a, b = np.deg2rad(theta1), np.deg2rad(theta2)
    x = L1 * np.cos(a) + L2 * np.cos(a + b - np.pi / 2)
    y = L1 * np.sin(a) + L2 * np.sin(a + b - np.pi / 2)
    return x, y


def analisar(nome, dados):
    """Tabela ponto a ponto com erro angular e cartesiano."""
    L1, L2 = dados["L"]
    t1_d, t2_d = malha_comandada()
    t1_m = np.asarray(dados["theta1"], float)
    t2_m = np.asarray(dados["theta2"], float)
    if t1_m.size != t1_d.size or t2_m.size != t2_d.size:
        raise ValueError(
            f"{nome}: esperados {t1_d.size} pontos, recebidos "
            f"{t1_m.size} (theta1) e {t2_m.size} (theta2)."
        )

    x_d, y_d = cinematica_direta(t1_d, t2_d, L1, L2)
    x_m, y_m = cinematica_direta(t1_m, t2_m, L1, L2)
    return pd.DataFrame({
        "prototipo": nome,
        "theta1_alvo": t1_d, "theta2_alvo": t2_d,
        "theta1_medido": t1_m, "theta2_medido": t2_m,
        "erro_theta1": t1_m - t1_d, "erro_theta2": t2_m - t2_d,
        "x_alvo": x_d, "y_alvo": y_d, "x_medido": x_m, "y_medido": y_m,
        "erro_cartesiano_mm": np.hypot(x_m - x_d, y_m - y_d),
    })


def repetibilidade(tabela):
    """Desvio de theta2 para cada alvo, entre as configuracoes de theta1.

    Cada alvo de theta2 e visitado 5 vezes (uma por nivel de theta1); a
    dispersao entre essas 5 leituras e a repetibilidade do atuador 2.
    """
    return (tabela.groupby(["prototipo", "theta2_alvo"])
            .agg(theta2_medio=("theta2_medido", "mean"),
                 theta2_desvio=("theta2_medido", "std"),
                 erro_medio=("erro_theta2", "mean"),
                 n=("theta2_medido", "count"))
            .reset_index())


def ganho_e_offset(tabela):
    """Separa o erro em ganho e offset: medido = ganho*comandado + offset.

    Um erro que cresce com o alvo (e o caso destes dados) nao e
    dispersao: e ganho diferente de 1, tipicamente calibracao da largura
    de pulso do servo. Isso e corrigivel por software, enquanto um erro
    aleatorio nao seria -- por isso vale separar os dois no artigo.
    """
    linhas = []
    for nome, bloco in tabela.groupby("prototipo"):
        for atuador in (1, 2):
            alvo = bloco[f"theta{atuador}_alvo"].to_numpy(float)
            medido = bloco[f"theta{atuador}_medido"].to_numpy(float)
            ganho, offset = np.polyfit(alvo, medido, 1)
            residuo = medido - (ganho * alvo + offset)
            linhas.append({
                "prototipo": nome,
                "atuador": atuador,
                "ganho": ganho,
                "offset_graus": offset,
                "residuo_rms_graus": float(np.sqrt(np.mean(residuo**2))),
                "residuo_max_graus": float(np.max(np.abs(residuo))),
            })
    return pd.DataFrame(linhas)


def resumir(tabela):
    return (tabela.groupby("prototipo")
            .agg(erro_abs_medio_theta1=("erro_theta1", lambda s: s.abs().mean()),
                 erro_abs_medio_theta2=("erro_theta2", lambda s: s.abs().mean()),
                 erro_abs_max_theta2=("erro_theta2", lambda s: s.abs().max()),
                 erro_cartesiano_medio_mm=("erro_cartesiano_mm", "mean"),
                 erro_cartesiano_max_mm=("erro_cartesiano_mm", "max"))
            .reset_index())


def _num(valor, casas):
    """Numero em formato pt-BR (virgula decimal), pronto para o texto."""
    if not np.isfinite(valor):
        return "—"
    return f"{valor:.{casas}f}".replace(".", ",")


def tabela_para_o_texto(tabela, repet):
    """Tabela pronta para colar no artigo, com theta1 e theta2.

    Uma linha por posicao comandada. O atuador 1 tem UMA leitura por
    alvo (o angulo e o mesmo em todo o bloco), entao nao ha desvio; o
    atuador 2 e visitado 5 vezes, uma por configuracao do atuador 1, e
    o desvio entre essas leituras vai entre parenteses. A ultima linha
    traz o erro absoluto medio de cada coluna.
    """
    nomes = list(PROTOTIPOS)
    colunas = ["Alvo [°]"]
    for nome in nomes:
        colunas += [f"Atuador 1 – {nome} [°]", f"Atuador 2 – {nome} [°] (dp)"]

    linhas = []
    for alvo in ALVOS:
        linha = {"Alvo [°]": _num(alvo, 0)}
        for nome in nomes:
            bloco = tabela[(tabela["prototipo"] == nome)
                           & (tabela["theta1_alvo"] == alvo)]
            medido1 = float(bloco["theta1_medido"].iloc[0])
            leitura = repet[(repet["prototipo"] == nome)
                            & (repet["theta2_alvo"] == alvo)].iloc[0]
            linha[f"Atuador 1 – {nome} [°]"] = _num(medido1, 1)
            linha[f"Atuador 2 – {nome} [°] (dp)"] = (
                f"{_num(leitura['theta2_medio'], 2)} "
                f"({_num(leitura['theta2_desvio'], 2)})")
        linhas.append(linha)

    rodape = {"Alvo [°]": "|erro| médio"}
    for nome in nomes:
        bloco = tabela[tabela["prototipo"] == nome]
        rodape[f"Atuador 1 – {nome} [°]"] = _num(bloco["erro_theta1"].abs().mean(), 2)
        rodape[f"Atuador 2 – {nome} [°] (dp)"] = _num(bloco["erro_theta2"].abs().mean(), 2)
    linhas.append(rodape)

    return pd.DataFrame(linhas, columns=colunas)


def salvar_figura_mapa(fig, nome, tentativas=3):
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


def figura_erro_angular(tabela, repet):
    """Erro do atuador 2 por alvo, com a dispersao entre repeticoes."""
    fig, (esq, dir_) = plt.subplots(1, 2, figsize=(11.0, 4.2))

    for nome in tabela["prototipo"].unique():
        bloco = repet[repet["prototipo"] == nome]
        esq.errorbar(bloco["theta2_alvo"], bloco["erro_medio"],
                     yerr=bloco["theta2_desvio"], marker="o", capsize=3,
                     markersize=5, label=nome)
    esq.axhline(0.0, color="k", linewidth=0.8)
    esq.set_xlabel("Posição comandada do atuador 2 (graus)")
    esq.set_ylabel("Erro médio (graus)")
    esq.set_title("(a) Erro e repetibilidade do atuador 2")
    esq.set_xticks(ALVOS)
    esq.legend(loc="best")

    for nome in tabela["prototipo"].unique():
        bloco = tabela[tabela["prototipo"] == nome]
        dir_.plot(bloco["theta2_alvo"], bloco["erro_cartesiano_mm"], "o",
                  markersize=4, alpha=0.75, label=nome)
    dir_.set_xlabel("Posição comandada do atuador 2 (graus)")
    dir_.set_ylabel("Erro cartesiano (mm)")
    dir_.set_title("(b) Erro de posição do efetuador")
    dir_.set_xticks(ALVOS)
    dir_.legend(loc="best")

    fig.tight_layout()
    salvar_figura_mapa(fig, "mapa_angular_erro")


def figura_espaco_trabalho(tabela):
    """Alvos x posicoes medidas no plano, um painel por protótipo."""
    nomes = list(tabela["prototipo"].unique())
    fig, eixos = plt.subplots(1, len(nomes), figsize=(5.5 * len(nomes), 4.6),
                              squeeze=False)
    for eixo, nome in zip(eixos[0], nomes):
        bloco = tabela[tabela["prototipo"] == nome]
        eixo.plot(bloco["x_alvo"], bloco["y_alvo"], "s", markersize=6,
                  markerfacecolor="none", label="Alvo")
        eixo.plot(bloco["x_medido"], bloco["y_medido"], "o", markersize=4,
                  label="Medido")
        for _, linha in bloco.iterrows():
            eixo.plot([linha["x_alvo"], linha["x_medido"]],
                      [linha["y_alvo"], linha["y_medido"]],
                      "-", color="0.5", linewidth=0.6)
        eixo.plot(0, 0, "k+", markersize=10)
        eixo.set_aspect("equal", adjustable="datalim")
        eixo.set_xlabel("X (mm)")
        eixo.set_ylabel("Y (mm)")
        eixo.set_title(f"{nome} — malha 5×5")
        eixo.legend(loc="best")
    fig.tight_layout()
    salvar_figura_mapa(fig, "mapa_angular_espaco_trabalho")


def conferir_comprimentos():
    """Compara os elos de projeto com o raio medido na filmagem.

    O ponto rastreado descreve um arco de raio AB+BC. Se o raio medido
    no video nao bate com L1+L2 de projeto, algum dos dois esta errado
    -- e todo resultado em milimetros depende disso. Os angulos nao
    dependem da escala, entao a analise angular continua valida.
    """
    if not RAIO_FILMAGEM:
        return
    print("\n=== CONSISTENCIA: elos de projeto x raio medido na filmagem ===")
    for nome, dados in PROTOTIPOS.items():
        raio_video = RAIO_FILMAGEM.get(nome)
        if raio_video is None:
            continue
        projeto = sum(dados["L"])
        razao = raio_video / projeto
        alerta = "  <-- VERIFICAR" if abs(razao - 1.0) > 0.05 else ""
        print(f"  {nome}: projeto L1+L2 = {projeto:6.2f} mm | "
              f"filmagem = {raio_video:6.2f} mm | razão = {razao:.3f}{alerta}")
    print("  Os erros em mm desta análise usam os elos de PROJETO. "
          "Se a razão não for ~1, resolva a escala do vídeo antes de\n"
          "  publicar qualquer número em milímetros (os ângulos não são "
          "afetados pela escala).")


def executar_mapa_angular():
    garantir_drive_mapa()
    tabelas = [analisar(nome, dados) for nome, dados in PROTOTIPOS.items()]
    tabela = pd.concat(tabelas, ignore_index=True)
    repet = repetibilidade(tabela)
    resumo = resumir(tabela)

    tabela_texto = tabela_para_o_texto(tabela, repet)
    print("=== TABELA PARA O TEXTO ===")
    print(tabela_texto.to_string(index=False))
    print("  (dp) = desvio padrao entre as 5 leituras do atuador 2 em cada alvo;"
          "\n  o atuador 1 tem uma unica leitura por alvo, entao nao tem desvio.")

    print("\n=== RESUMO POR PROTOTIPO ===")
    print(resumo.round(2).to_string(index=False))

    print("\n=== REPETIBILIDADE DO ATUADOR 2 (5 leituras por alvo) ===")
    print(repet.round(2).to_string(index=False))
    for nome in tabela["prototipo"].unique():
        desvio = repet[repet["prototipo"] == nome]["theta2_desvio"].mean()
        print(f"  {nome}: desvio médio entre repetições = {desvio:.2f}°")

    ganhos = ganho_e_offset(tabela)
    print("\n=== ERRO SISTEMATICO: ganho e offset ===")
    print(ganhos.round(3).to_string(index=False))
    for _, linha in ganhos.iterrows():
        if abs(linha["ganho"] - 1.0) > 0.02:
            print(f"  ! {linha['prototipo']} atuador {int(linha['atuador'])}: "
                  f"entrega {100*linha['ganho']:.1f}% do comandado. O erro "
                  f"cresce com o alvo — é calibração, não dispersão, e o "
                  f"resíduo depois de corrigir cai para "
                  f"{linha['residuo_rms_graus']:.2f}° RMS.")

    figura_erro_angular(tabela, repet)
    figura_espaco_trabalho(tabela)
    conferir_comprimentos()

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    for nome_arq, dados in (("mapa_angular_TABELA_ARTIGO", tabela_texto),
                            ("mapa_angular_pontos", tabela),
                            ("mapa_angular_repetibilidade", repet),
                            ("mapa_angular_ganho_offset", ganhos),
                            ("mapa_angular_resumo", resumo)):
        dados.to_csv(os.path.join(PASTA_SAIDA, f"{nome_arq}.csv"),
                     index=False, sep=";", decimal=",")
    print(f"\nConcluído. Resultados em {PASTA_SAIDA}")
    return {"tabela_artigo": tabela_texto, "pontos": tabela,
            "repetibilidade": repet, "ganho_offset": ganhos, "resumo": resumo}


if __name__ == "__main__":
    RESULTADOS_MAPA = executar_mapa_angular()
