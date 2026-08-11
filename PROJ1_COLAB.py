# -*- coding: utf-8 -*-
# =====================================================================
# PROJ 1 - CTG/UFPE - ANALISE DAS TRAJETORIAS DOS SERVOS
# =====================================================================
# Cole este arquivo inteiro em UMA celula do Colab e rode.
# Nao precisa clonar repositorio nem importar nada de fora.
#
# Protótipos: PE01 e PE02 (PE02 = arquivo "PROJ 1_PE10" no Drive).
# =====================================================================

# ---------------------------------------------------------------------
# PARTE 1 - BIBLIOTECAS, AUTENTICACAO E CONFIGURACAO
# ---------------------------------------------------------------------
import os
import re
import time

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

try:
    from google.colab import auth as _auth, drive as _drive
    from google.auth import default as _credenciais_padrao
    import gspread

    EM_COLAB = True
except ImportError:
    EM_COLAB = False

# --- Rótulo do protótipo -> nome do arquivo no Google Drive ----------
# Se você renomear a planilha no Drive, mude só o lado direito.
PLANILHAS = {
    "PE01": "PROJ 1_PE01",
    "PE02": "PROJ 1_PE10",
}

CATEGORIAS = (
    "I_S1_P02", "I_S1_P05", "I_S1_P10",
    "I_S2_P02", "I_S2_P05", "I_S2_P10",
)
N_REPETICOES = 3

PASTA_DRIVE = "/content/drive/MyDrive/CTG_UFPE/PROJETOS/PROJ 1"
PASTA_RESULTADOS = os.path.join(PASTA_DRIVE, "RESULTADOS")
PASTA_CACHE = os.path.join(PASTA_DRIVE, "CACHE_DADOS")
USAR_CACHE = True          # 2a execucao nao chama a API do Sheets

# --- Modelo do ensaio ------------------------------------------------
PERIODO_DEGRAU_S = 1.0     # um degrau a cada 1 s (verificado nos dados)
ANGULO_MAX_GRAUS = 180.0   # saturacao do servo
FRACAO_JANELA_REGIME = 0.30

# Faixa de acomodacao. Dois modos:
#   "passo"        -> +-BANDA * amplitude do degrau (convencao de controle)
#   "valor_final"  -> +-BANDA * |valor final absoluto|
# O 2o modo alarga a faixa conforme o braco sobe (a 180 graus, 2% sao
# +-3,6 graus), o que encurta artificialmente o tempo de acomodacao nos
# degraus altos. Use "passo" para o artigo; "valor_final" so para
# comparar com resultados calculados na outra convencao.
BANDA_MODO = "passo"
BANDA_ACOMODACAO = 0.05

# --- Deteccao do inicio do movimento ---------------------------------
FRACAO_TOLERANCIA_PLATO = 0.15
TOLERANCIA_PLATO_MIN = 0.10   # graus
N_CONFIRMACOES = 3

# --- Estimativa do centro de rotacao ---------------------------------
VARREDURA_MINIMA_AJUSTE_LIVRE = 90.0   # graus
TOLERANCIA_RAIO_NOMINAL = 0.25
PREFERENCIA_ORIGEM = 1.2

# --- Comprimentos dos elos (mm, medidos na filmagem em t=0) ----------
# Usados apenas para VALIDAR o raio estimado dos dados.
ELOS = {
    "PE01": {
        "I_S1_P02": {"AB": 146.58, "BC": 159.74},
        "I_S1_P05": {"AB": 145.56, "BC": 158.43},
        "I_S1_P10": {"AB": 146.74, "BC": 158.53},
        "I_S2_P02": {"BC": 167.25},
        "I_S2_P05": {"BC": 167.19},
        "I_S2_P10": {"BC": 167.18},
    },
    "PE02": {
        "I_S1_P02": {"AB": 118.59, "BC": 113.00},
        "I_S1_P05": {"AB": 120.61, "BC": 118.34},
        "I_S1_P10": {"AB": 120.24, "BC": 118.08},
        "I_S2_P02": {"BC": 111.27},
        "I_S2_P05": {"BC": 110.91},
        "I_S2_P10": {"BC": 111.06},
    },
}

# --- Figuras ---------------------------------------------------------
FIG_TAMANHO = (7.0, 4.5)
FIG_DPI = 300
FORMATOS = ("png", "pdf")   # PDF e vetorial: e o que o CREEM aceita sem perda
ZOOM_SEGUNDOS = 3.0
MARGEM_PRE_COMANDO = 0.2
MOSTRAR_FIGURAS = True

matplotlib.rcParams.update({
    "figure.figsize": FIG_TAMANHO,
    "figure.dpi": 110,
    "savefig.dpi": FIG_DPI,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.grid": True,
    "grid.linestyle": "--",
    "grid.linewidth": 0.4,
    "grid.alpha": 0.6,
    "lines.linewidth": 1.3,
})


def autenticar():
    """Autentica, monta o Drive e devolve o cliente do gspread."""
    _auth.authenticate_user()
    credenciais, _ = _credenciais_padrao()
    cliente = gspread.authorize(credenciais)
    _drive.mount("/content/drive")
    return cliente


# ---------------------------------------------------------------------
# PARTE 2 - LEITURA DAS PLANILHAS (uma chamada em lote por planilha)
# ---------------------------------------------------------------------
def com_retry(funcao, *args, tentativas=5, **kwargs):
    """Repete a chamada com espera exponencial em erro de quota/rede."""
    espera = 2.0
    for tentativa in range(1, tentativas + 1):
        try:
            return funcao(*args, **kwargs)
        except Exception as erro:
            codigo = getattr(getattr(erro, "response", None), "status_code", None)
            if tentativa == tentativas or codigo not in (429, 500, 502, 503, 504, None):
                raise
            print(f"  ! API falhou ({codigo}); tentando de novo em {espera:.0f}s")
            time.sleep(espera)
            espera *= 2


def passo_da_categoria(categoria):
    """"I_S1_P05" -> 5.0 graus. Evita passar o passo errado na chamada."""
    achado = re.search(r"P(\d+)", categoria)
    return float(int(achado.group(1))) if achado else 2.0


def usa_dois_elos(categoria):
    """S1 gira o conjunto (AB+BC); S2 gira so o elo BC."""
    return "S1" in categoria


def raio_nominal(prototipo, categoria):
    params = ELOS.get(prototipo, {}).get(categoria)
    if not params or "BC" not in params:
        return None
    if usa_dois_elos(categoria):
        return float(params["AB"]) + float(params["BC"]) if "AB" in params else None
    return float(params["BC"])


def para_float(valores):
    """Converte texto pt-BR ("3,07E+02") em float, sem estourar excecao."""
    serie = pd.Series(list(valores), dtype="object").astype(str).str.strip()
    ambos = (serie.str.contains(".", regex=False)
             & serie.str.contains(",", regex=False))
    serie = serie.mask(ambos, serie.str.replace(".", "", regex=False))
    serie = serie.str.replace(",", ".", regex=False)
    return pd.to_numeric(serie, errors="coerce").to_numpy(dtype=float)


def extrair_txy(linhas):
    """Matriz de strings da aba -> (t, x, y). Descarta cabecalho e lixo."""
    if not linhas:
        return np.empty(0), np.empty(0), np.empty(0)
    tabela = [(list(linha) + ["", "", ""])[:3] for linha in linhas]
    t = para_float([l[0] for l in tabela])
    x = para_float([l[1] for l in tabela])
    y = para_float([l[2] for l in tabela])
    ok = np.isfinite(t) & np.isfinite(x) & np.isfinite(y)
    return t[ok], x[ok], y[ok]


def caminho_cache(prototipo, aba):
    return os.path.join(PASTA_CACHE, f"{prototipo}__{aba}.csv")


def carregar_ensaios(cliente=None):
    """Le tudo e devolve uma lista de dicionarios, um por repeticao."""
    abas = [f"{c}_{i}" for c in CATEGORIAS for i in range(1, N_REPETICOES + 1)]
    if USAR_CACHE:
        os.makedirs(PASTA_CACHE, exist_ok=True)

    ensaios = []
    for prototipo, arquivo in PLANILHAS.items():
        faltantes = [a for a in abas
                     if not (USAR_CACHE and os.path.exists(caminho_cache(prototipo, a)))]
        brutos = {}
        if faltantes:
            if cliente is None:
                raise RuntimeError(
                    f"Sem cache para {prototipo} e sem cliente do Sheets. "
                    "Rode no Colab."
                )
            planilha = com_retry(cliente.open, arquivo)
            existentes = {ws.title for ws in com_retry(planilha.worksheets)}
            alvo = [a for a in faltantes if a in existentes]
            ausentes = [a for a in faltantes if a not in existentes]
            if ausentes:
                print(f"  ! {prototipo}: abas ausentes -> {', '.join(ausentes)}")
            if alvo:
                print(f"  Lendo {prototipo} ({arquivo}): {len(alvo)} abas de uma vez")
                resposta = com_retry(
                    planilha.values_batch_get, [f"'{a}'!A:C" for a in alvo]
                )
                blocos = resposta.get("valueRanges", [])
                brutos = {a: b.get("values", []) for a, b in zip(alvo, blocos)}

        for aba in abas:
            categoria, _, sufixo = aba.rpartition("_")
            if USAR_CACHE and os.path.exists(caminho_cache(prototipo, aba)):
                tabela = pd.read_csv(caminho_cache(prototipo, aba))
                t, x, y = (tabela[c].to_numpy(float) for c in ("t", "x", "y"))
            elif aba in brutos:
                t, x, y = extrair_txy(brutos[aba])
                if USAR_CACHE and t.size:
                    pd.DataFrame({"t": t, "x": x, "y": y}).to_csv(
                        caminho_cache(prototipo, aba), index=False)
            else:
                continue

            if t.size < 5:
                print(f"  ! {prototipo}/{aba}: dados insuficientes, ignorado")
                continue

            ensaios.append({
                "prototipo": prototipo,
                "categoria": categoria,
                "repeticao": int(sufixo),
                "t": t, "x": x, "y": y,
                "passo": passo_da_categoria(categoria),
            })
    return ensaios


# ---------------------------------------------------------------------
# PARTE 3 - GEOMETRIA: CENTRO DE ROTACAO E ANGULO
# ---------------------------------------------------------------------
def ajustar_circulo(x, y):
    """Ajuste algebrico de circunferencia (Kasa). Devolve (xc, yc, R)."""
    if x.size < 3:
        return np.nan, np.nan, np.nan
    solucao, *_ = np.linalg.lstsq(
        np.column_stack((x, y, np.ones(x.size))), x**2 + y**2, rcond=None)
    xc, yc = float(solucao[0] / 2), float(solucao[1] / 2)
    sob_raiz = solucao[2] + xc**2 + yc**2
    return xc, yc, float(np.sqrt(sob_raiz)) if sob_raiz > 0 else np.nan


def ajustar_centro_raio_fixo(x, y, raio, iteracoes=200, tol=1e-10):
    """Ajusta so o centro, com o raio travado no nominal.

    Com o raio conhecido sobram 2 parametros em vez de 3, e o problema
    deixa de ser mal condicionado em arco curto: num arco de 10 graus o
    ajuste livre chega a deslocar o centro em 89 mm, este erra 0,05 mm.
    """
    cx, cy = 0.0, 0.0
    for _ in range(iteracoes):
        dx, dy = x - cx, y - cy
        norma = np.hypot(dx, dy)
        norma = np.where(norma > 0, norma, 1e-12)
        novo_x = float(np.mean(x - raio * dx / norma))
        novo_y = float(np.mean(y - raio * dy / norma))
        parou = abs(novo_x - cx) < tol and abs(novo_y - cy) < tol
        cx, cy = novo_x, novo_y
        if parou:
            break
    return cx, cy


def estatisticas_radiais(x, y, centro):
    raios = np.hypot(x - centro[0], y - centro[1])
    media = float(np.mean(raios))
    if not np.isfinite(media) or media <= 0:
        return np.nan, np.inf
    return media, float(np.std(raios))


def varredura_estimada(x, y, raio):
    """Angulo central varrido (graus), estimado sem conhecer o centro."""
    if not np.isfinite(raio) or raio <= 0 or x.size < 2:
        return np.nan
    salto = max(1, x.size // 200)
    px, py = x[::salto], y[::salto]
    corda = float(np.hypot(px[:, None] - px[None, :],
                           py[:, None] - py[None, :]).max())
    return float(2 * np.degrees(np.arcsin(np.clip(corda / (2 * raio), 0, 1))))


def estimar_centro(x, y, raio_esperado=None):
    """Centro de rotacao do ensaio, por tres hipoteses concorrentes.

    1. origem  - a origem do Tracker ja e a junta (caso desta base);
    2. raio fixo - centro ajustado com o raio travado no nominal;
    3. ajuste livre - so quando a varredura passa de 90 graus, porque
       abaixo disso ele e mal condicionado. E a unica que mede o raio de
       forma independente, o que valida AB+BC.
    """
    candidatos = [("origem", (0.0, 0.0))]
    if raio_esperado:
        candidatos.append(
            ("raio fixo", ajustar_centro_raio_fixo(x, y, raio_esperado)))

    xc, yc, raio_livre = ajustar_circulo(x, y)
    if np.isfinite(xc) and np.isfinite(raio_livre):
        varredura = varredura_estimada(x, y, raio_esperado or raio_livre)
        if np.isfinite(varredura) and varredura >= VARREDURA_MINIMA_AJUSTE_LIVRE:
            candidatos.append(("ajuste livre", (xc, yc)))

    avaliados = []
    for nome, centro in candidatos:
        raio, desvio = estatisticas_radiais(x, y, centro)
        if not np.isfinite(raio):
            continue
        if raio_esperado and abs(raio - raio_esperado) / raio_esperado > TOLERANCIA_RAIO_NOMINAL:
            continue
        avaliados.append((desvio, nome, centro, raio))

    if not avaliados:
        raio, _ = estatisticas_radiais(x, y, (0.0, 0.0))
        print(f"  ! nenhum centro compativel com o raio nominal "
              f"({raio_esperado}); usando a origem (raio medido {raio:.1f} mm)")
        return (0.0, 0.0), raio, "origem (sem validacao)"

    desvio, nome, centro, raio = min(avaliados, key=lambda item: item[0])
    origem = next((i for i in avaliados if i[1] == "origem"), None)
    if origem and origem[0] <= PREFERENCIA_ORIGEM * desvio:
        desvio, nome, centro, raio = origem   # Occam: fica com a origem
    return centro, raio, nome


def angulo_desenrolado(x, y, centro):
    """Angulo em graus, sem saltos de +-180."""
    return np.degrees(np.unwrap(np.arctan2(y - centro[1], x - centro[0])))


def algarismos_significativos(valores, maximo=12):
    """Com quantos algarismos os dados foram gravados ("3,07E+02" -> 3)."""
    amostra = valores[np.isfinite(valores) & (valores != 0)]
    if amostra.size == 0:
        return maximo
    digitos = []
    for valor in np.abs(amostra[:: max(1, amostra.size // 400)]):
        expoente = int(np.floor(np.log10(valor)))
        for n in range(1, maximo + 1):
            quantum = 10.0 ** (expoente - n + 1)
            if abs(valor / quantum - round(valor / quantum)) < 1e-6:
                digitos.append(n)
                break
        else:
            digitos.append(maximo)
    return int(np.median(digitos))


def resolucao_angular(x, y, centro):
    """Incerteza angular (graus) que vem do arredondamento dos dados."""
    digitos = min(algarismos_significativos(x), algarismos_significativos(y))
    quantum = lambda v: np.where(
        np.abs(v) > 0,
        10.0 ** (np.floor(np.log10(np.where(np.abs(v) > 0, np.abs(v), 1.0)))
                 - digitos + 1),
        0.0)
    dx, dy = x - centro[0], y - centro[1]
    r2 = dx**2 + dy**2
    ok = r2 > 0
    if not np.any(ok):
        return np.nan, np.nan, digitos
    incerteza = np.degrees(
        np.hypot(dy[ok] * quantum(x)[ok], dx[ok] * quantum(y)[ok]) / r2[ok])
    return float(np.median(incerteza)), float(np.max(incerteza)), digitos


def detectar_inicio(theta, passo):
    """Instante do comando = fim do plato inicial.

    O criterio antigo (variacao de 4% em x E em y) nunca disparava:
    perto do eixo X um degrau de 2 graus muda x em apenas 0,12%.
    Aqui o limiar e em GRAUS, uma fracao do passo comandado, com
    confirmacao em N amostras para nao disparar num ponto ruidoso.
    """
    if theta.size == 0:
        return 0, np.nan
    tolerancia = max(FRACAO_TOLERANCIA_PLATO * abs(passo), TOLERANCIA_PLATO_MIN)
    fora = np.abs(theta - theta[0]) > tolerancia
    n_conf = max(1, min(N_CONFIRMACOES, theta.size))
    janelas = np.convolve(fora.astype(int), np.ones(n_conf, dtype=int), "valid")
    confirmadas = np.flatnonzero(janelas == n_conf)
    if confirmadas.size == 0:
        print("  ! movimento nao detectado; alinhando pela 1a amostra")
        return 0, float(np.median(theta[: min(10, theta.size)]))
    indice = max(int(confirmadas[0]) - 1, 0)
    return indice, float(np.median(theta[: indice + 1]))


def preparar(ensaio):
    """Preenche centro, raio, angulo, repouso, sentido e tempo relativo."""
    esperado = raio_nominal(ensaio["prototipo"], ensaio["categoria"])
    centro, raio, origem = estimar_centro(ensaio["x"], ensaio["y"], esperado)
    theta = angulo_desenrolado(ensaio["x"], ensaio["y"], centro)
    indice, repouso = detectar_inicio(theta, ensaio["passo"])

    cauda = theta[max(int(0.9 * theta.size), indice + 1):]
    deslocamento = (float(np.median(cauda)) - repouso) if cauda.size else 0.0
    sentido = -1 if deslocamento < 0 else 1

    mediana_res, max_res, digitos = resolucao_angular(
        ensaio["x"], ensaio["y"], centro)

    ensaio.update({
        "centro": centro, "raio": raio, "origem_centro": origem,
        "theta": theta, "theta0": repouso, "indice_comando": indice,
        "sentido": sentido,
        "tau": ensaio["t"] - ensaio["t"][indice],
        # Deslocamento angular relativo ao repouso, ja com o sentido
        # corrigido. E ESTA a grandeza que se compara com o comando --
        # comparar theta cru com uma curva que comeca em zero era o que
        # fazia as curvas nunca se encontrarem.
        "theta_rel": sentido * (theta - repouso),
        "dt": float(np.median(np.diff(ensaio["t"]))) if ensaio["t"].size > 1 else np.nan,
        "resolucao_angular": mediana_res,
        "resolucao_angular_max": max_res,
        "algarismos": digitos,
    })

    if esperado and np.isfinite(raio) and abs(raio - esperado) / esperado > 0.10:
        print(f"  ! {ensaio['prototipo']}/{ensaio['categoria']}_{ensaio['repeticao']}: "
              f"raio medido {raio:.1f} mm x nominal {esperado:.1f} mm")
    if np.isfinite(max_res) and max_res > 0.10 * abs(ensaio["passo"]):
        print(f"  ! {ensaio['prototipo']}/{ensaio['categoria']}_{ensaio['repeticao']}: "
              f"dados com {digitos} algarismos significativos -> ate {max_res:.2f} "
              f"graus so de quantizacao ({100*max_res/abs(ensaio['passo']):.0f}% do passo)")
    return ensaio


# ---------------------------------------------------------------------
# PARTE 4 - TRAJETORIA DESEJADA E CINEMATICA DIRETA
# ---------------------------------------------------------------------
def trajetoria_desejada(tau, passo):
    """Escada: um degrau de `passo` graus a cada PERIODO_DEGRAU_S.

    O ensaio e uma escada, nao uma rampa: nos graficos o braco salta o
    passo e estabiliza, e o degrau seguinte aparece 1 s depois.
    """
    n = np.clip(np.floor(tau / PERIODO_DEGRAU_S) + 1.0, 0.0, None)
    comando = np.minimum(n * abs(passo), ANGULO_MAX_GRAUS)
    comando[tau < 0] = 0.0
    return comando


JANELAS_CANDIDATAS = (0.10, 0.15, 0.20, 0.27, 0.35, 0.50)


def instantes_dos_degraus(tau, theta_rel, passo, fracao=0.5, janela_s=None):
    """Instantes dos degraus, escolhendo sozinho a melhor janela.

    A janela precisa cobrir a subida mas ficar bem abaixo da cadencia --
    e a cadencia e justamente o que se quer descobrir. Entao testam-se
    varias janelas e fica a que produz o espacamento mais regular
    (menor dispersao relativa), que e o que uma deteccao correta gera.
    """
    if janela_s is not None:
        return _instantes_com_janela(tau, theta_rel, passo, fracao, janela_s)

    melhor, melhor_score = np.empty(0), np.inf
    for candidata in JANELAS_CANDIDATAS:
        instantes = _instantes_com_janela(tau, theta_rel, passo, fracao, candidata)
        if instantes.size < 3:
            continue
        espacos = np.diff(instantes)
        media = float(np.mean(espacos))
        if media <= 0:
            continue
        score = float(np.std(espacos) / media)
        if score < melhor_score:
            melhor, melhor_score = instantes, score
    return melhor


def _instantes_com_janela(tau, theta_rel, passo, fracao, janela_s):
    """Instantes dos degraus tirados dos PROPRIOS dados.

    Nao depende de supor a cadencia. Compara theta[i+w] com theta[i]
    numa janela w que cobre a subida, em vez de quadros vizinhos: a
    30 fps o servo leva 3 a 4 quadros para vencer um degrau de 10 graus,
    entao a variacao POR QUADRO fica em ~3 graus e nunca ultrapassaria
    metade do passo. Dentro de cada grupo toma-se o quadro mais ingreme.

    O instante devolvido tem um deslocamento constante de meia subida;
    como so as DIFERENCAS entre eles sao usadas (a cadencia), isso se
    cancela.
    """
    if theta_rel.size < 4 or tau.size < 4:
        return np.empty(0)
    dt = float(np.median(np.diff(tau)))
    if not np.isfinite(dt) or dt <= 0:
        return np.empty(0)
    janela = max(1, int(round(janela_s / dt)))
    if theta_rel.size <= janela + 1:
        return np.empty(0)

    variacao = np.abs(theta_rel[janela:] - theta_rel[:-janela])
    indices = np.flatnonzero(variacao > fracao * abs(passo))
    if indices.size == 0:
        return np.empty(0)

    # Separar grupos exige um intervalo MENOR que a janela: com cadencia
    # curta o vao entre duas subidas fica abaixo de `janela` e os degraus
    # se fundiriam num grupo so. Dentro de um mesmo degrau a variacao
    # fica continuamente acima do limiar (50% do passo), entao um limite
    # pequeno nao parte um degrau em dois.
    separacao = max(2, janela // 2)
    cortes = np.flatnonzero(np.diff(indices) > separacao) + 1
    derivada = np.abs(np.diff(theta_rel))
    instantes = []
    for grupo in np.split(indices, cortes):
        if not grupo.size:
            continue
        inicio = int(grupo[0])
        fim = min(int(grupo[-1]) + janela, derivada.size)
        if fim <= inicio:
            continue
        instantes.append(tau[inicio + int(np.argmax(derivada[inicio:fim]))])
    return np.asarray(instantes)


def verificar_cadencia(grupo):
    """Compara a cadencia medida com PERIODO_DEGRAU_S."""
    periodos = []
    for ensaio in grupo:
        instantes = instantes_dos_degraus(
            ensaio["tau"], ensaio["theta_rel"], ensaio["passo"])
        if instantes.size >= 3:
            periodos.extend(np.diff(instantes).tolist())
    if len(periodos) < 2:
        return None
    medido = float(np.median(periodos))
    if abs(medido - PERIODO_DEGRAU_S) > 0.10:
        ref = grupo[0]
        print(f"  ! {ref['prototipo']}/{ref['categoria']}: cadência medida nos "
              f"dados = {medido:.3f} s, mas PERIODO_DEGRAU_S = "
              f"{PERIODO_DEGRAU_S:.3f} s. Ajuste a constante — a curva "
              f"desejada e todas as métricas dependem dela.")
    return medido


def largura_da_faixa(passo, alvo):
    """Meia-largura da faixa de acomodacao, conforme BANDA_MODO."""
    referencia = abs(passo) if BANDA_MODO == "passo" else abs(alvo)
    return BANDA_ACOMODACAO * referencia


def curva_desejada_xy(ensaio):
    """Curva desejada NO MESMO referencial dos dados medidos.

    Mesmo centro, mesmo raio e partindo do mesmo angulo de repouso --
    e por isso que agora ela cai em cima da medida.
    """
    comando = trajetoria_desejada(ensaio["tau"], ensaio["passo"])
    absoluto = ensaio["theta0"] + ensaio["sentido"] * comando
    radianos = np.deg2rad(absoluto)
    return (ensaio["centro"][0] + ensaio["raio"] * np.cos(radianos),
            ensaio["centro"][1] + ensaio["raio"] * np.sin(radianos))


# ---------------------------------------------------------------------
# PARTE 5 - METRICAS (inclui o TEMPO DE ACOMODACAO)
# ---------------------------------------------------------------------
def cruzamento(tau, sinal, nivel):
    """Primeiro instante em que `sinal` atinge `nivel` (interpolado)."""
    acima = np.flatnonzero(sinal >= nivel)
    if acima.size == 0:
        return np.nan
    i = int(acima[0])
    if i == 0:
        return float(tau[0])
    y0, y1 = sinal[i - 1], sinal[i]
    if y1 == y0:
        return float(tau[i])
    return float(tau[i - 1] + (nivel - y0) / (y1 - y0) * (tau[i] - tau[i - 1]))


def metricas_por_degrau(ensaio):
    """Erro de regime, sobressinal, tempo de subida e de ACOMODACAO."""
    passo = abs(ensaio["passo"])
    tau, resposta = ensaio["tau"], ensaio["theta_rel"]
    duracao = float(tau[-1]) if tau.size else 0.0
    n_degraus = min(int(ANGULO_MAX_GRAUS / passo),
                    int(np.floor(duracao / PERIODO_DEGRAU_S)))

    linhas = []
    for k in range(n_degraus):
        inicio, fim = k * PERIODO_DEGRAU_S, (k + 1) * PERIODO_DEGRAU_S
        janela = (tau >= inicio) & (tau < fim)
        if janela.sum() < 3:
            continue
        tau_j, resp_j = tau[janela], resposta[janela]
        alvo, base = (k + 1) * passo, k * passo

        regime = resp_j[tau_j >= fim - FRACAO_JANELA_REGIME * PERIODO_DEGRAU_S]
        valor_regime = float(np.mean(regime)) if regime.size else np.nan

        t10 = cruzamento(tau_j, resp_j, base + 0.10 * passo)
        t90 = cruzamento(tau_j, resp_j, base + 0.90 * passo)

        # TEMPO DE ACOMODACAO: instante em que a resposta ENTRA na faixa
        # de +-5% do passo e nao sai mais ate o proximo degrau.
        # NaN = o degrau acabou sem acomodar.
        banda = largura_da_faixa(passo, alvo)
        fora = np.flatnonzero(np.abs(resp_j - alvo) > banda)
        if fora.size == 0:
            t_acomodacao = 0.0
        elif fora[-1] + 1 < tau_j.size:
            t_acomodacao = float(tau_j[fora[-1] + 1] - inicio)
        else:
            t_acomodacao = np.nan

        pico = float(np.max(resp_j))
        linhas.append({
            "prototipo": ensaio["prototipo"],
            "categoria": ensaio["categoria"],
            "repeticao": ensaio["repeticao"],
            "degrau": k + 1,
            "alvo_graus": alvo,
            "regime_graus": valor_regime,
            "erro_graus": valor_regime - alvo,
            "sobressinal_graus": pico - alvo,
            "sobressinal_pct": 100.0 * (pico - alvo) / passo,
            "tempo_subida_s": t90 - t10 if np.isfinite(t10) and np.isfinite(t90) else np.nan,
            "tempo_acomodacao_s": t_acomodacao,
            "faixa_acomodacao_graus": banda,
        })
    return pd.DataFrame(linhas)


def metricas_do_ensaio(ensaio, por_degrau):
    """Uma linha por repeticao, com o tempo de acomodacao medio."""
    comando = trajetoria_desejada(ensaio["tau"], ensaio["passo"])
    depois = ensaio["tau"] >= 0
    erro = ensaio["theta_rel"][depois] - comando[depois]
    meu = por_degrau[
        (por_degrau["prototipo"] == ensaio["prototipo"])
        & (por_degrau["categoria"] == ensaio["categoria"])
        & (por_degrau["repeticao"] == ensaio["repeticao"])
    ]
    return {
        "prototipo": ensaio["prototipo"],
        "categoria": ensaio["categoria"],
        "repeticao": ensaio["repeticao"],
        "duracao_s": float(ensaio["tau"][-1]) if ensaio["tau"].size else np.nan,
        "taxa_amostragem_hz": 1.0 / ensaio["dt"] if np.isfinite(ensaio["dt"]) else np.nan,
        "raio_mm": ensaio["raio"],
        "centro_x_mm": ensaio["centro"][0],
        "centro_y_mm": ensaio["centro"][1],
        "origem_centro": ensaio["origem_centro"],
        "angulo_repouso_graus": ensaio["theta0"],
        "sentido": ensaio["sentido"],
        "algarismos_significativos": ensaio["algarismos"],
        "resolucao_angular_graus": ensaio["resolucao_angular"],
        "t_acomodacao_medio_s": meu["tempo_acomodacao_s"].mean(),
        "t_acomodacao_desvio_s": meu["tempo_acomodacao_s"].std(),
        "t_acomodacao_max_s": meu["tempo_acomodacao_s"].max(),
        "degraus_sem_acomodar": int(meu["tempo_acomodacao_s"].isna().sum()),
        "tempo_subida_medio_s": meu["tempo_subida_s"].mean(),
        "sobressinal_medio_pct": meu["sobressinal_pct"].mean(),
        "rmse_graus": float(np.sqrt(np.mean(erro**2))) if erro.size else np.nan,
    }


def grade_comum(grupo):
    """Reamostra as repeticoes num eixo tau unico (interpola, nao repete)."""
    tau_min = max(float(e["tau"][0]) for e in grupo)
    tau_max = min(float(e["tau"][-1]) for e in grupo)
    if tau_max <= tau_min:
        return np.empty(0), np.empty((0, 0))
    grade = np.arange(tau_min, tau_max, float(np.median([e["dt"] for e in grupo])))
    return grade, np.column_stack(
        [np.interp(grade, e["tau"], e["theta_rel"]) for e in grupo])


# ---------------------------------------------------------------------
# PARTE 6 - GRAFICOS
# ---------------------------------------------------------------------
def salvar_figura_traj(fig, subpasta, nome):
    pasta = os.path.join(PASTA_RESULTADOS, subpasta)
    os.makedirs(pasta, exist_ok=True)
    for formato in FORMATOS:
        fig.savefig(os.path.join(pasta, f"{nome}.{formato}"), format=formato)
    if MOSTRAR_FIGURAS:
        plt.show()
    plt.close(fig)


def texto_acomodacao(grupo, por_degrau):
    """Caixa com o tempo de acomodacao de cada repeticao e a media."""
    linhas, medias = [], []
    for ensaio in grupo:
        meu = por_degrau[
            (por_degrau["prototipo"] == ensaio["prototipo"])
            & (por_degrau["categoria"] == ensaio["categoria"])
            & (por_degrau["repeticao"] == ensaio["repeticao"])
        ]["tempo_acomodacao_s"]
        media = meu.mean()
        nao_acomodou = int(meu.isna().sum())
        if np.isfinite(media):
            medias.append(media)
            aviso = f"  ({nao_acomodou} degrau(s) sem acomodar)" if nao_acomodou else ""
            linhas.append(f"Exp {ensaio['repeticao']}: {1000*media:5.0f} ms"
                          f" ± {1000*meu.std():3.0f}{aviso}")
        else:
            linhas.append(f"Exp {ensaio['repeticao']}: nao acomodou")
    if medias:
        linhas.append(f"Média:  {1000*np.mean(medias):5.0f} ms"
                      f" ± {1000*np.std(medias):3.0f}")
    referencia = "do passo" if BANDA_MODO == "passo" else "do valor final"
    return (f"Tempo de acomodação (±{100*BANDA_ACOMODACAO:.0f}% {referencia})\n"
            + "\n".join(linhas))


def plot_xy(grupo, por_degrau):
    """Trajetoria no plano, no referencial da junta, com o arco desejado."""
    ref = grupo[0]
    fig, eixo = plt.subplots(figsize=FIG_TAMANHO)
    for ensaio in grupo:
        eixo.plot(ensaio["x"] - ensaio["centro"][0],
                  ensaio["y"] - ensaio["centro"][1],
                  label=f"Experimento {ensaio['repeticao']}")
    x_des, y_des = curva_desejada_xy(ref)
    eixo.plot(x_des - ref["centro"][0], y_des - ref["centro"][1],
              "k--", linewidth=1.8, label="Trajetória desejada")
    eixo.plot(0, 0, "k+", markersize=9)
    eixo.text(0.02, 0.02, texto_acomodacao(grupo, por_degrau),
              transform=eixo.transAxes, fontsize=7.5, va="bottom", ha="left",
              family="monospace",
              bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, lw=0.5))
    eixo.set_xlabel("X (mm) — origem na junta")
    eixo.set_ylabel("Y (mm) — origem na junta")
    eixo.set_title(f"{ref['prototipo']} — {ref['categoria']}")
    eixo.legend(loc="upper right")
    eixo.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    salvar_figura_traj(fig, "TRAJETORIA_XY", f"xy_{ref['prototipo']}_{ref['categoria']}")


def plot_angulo(grupo, por_degrau, zoom=None):
    """Angulo x tempo desde o comando, com a escada e o t. de acomodacao."""
    ref = grupo[0]
    fig, eixo = plt.subplots(figsize=FIG_TAMANHO)
    limite = zoom if zoom else max(float(e["tau"][-1]) for e in grupo)

    medidos = []
    for ensaio in grupo:
        corte = (ensaio["tau"] >= -MARGEM_PRE_COMANDO) & (ensaio["tau"] <= limite)
        eixo.plot(ensaio["tau"][corte], ensaio["theta_rel"][corte],
                  label=f"Experimento {ensaio['repeticao']}")
        medidos.append(ensaio["theta_rel"][corte])

    tau_cmd = np.linspace(-MARGEM_PRE_COMANDO, limite, 2000)
    eixo.plot(tau_cmd, trajetoria_desejada(tau_cmd, ref["passo"]),
              "k--", linewidth=1.8, label="Comando (desejado)")

    # faixa usada para medir o tempo de acomodacao
    passo = abs(ref["passo"])
    rotulo_faixa = f"Faixa de ±{100*BANDA_ACOMODACAO:.0f}% ({BANDA_MODO})"
    for k in range(int(np.ceil(limite / PERIODO_DEGRAU_S))):
        alvo = (k + 1) * passo
        if alvo > ANGULO_MAX_GRAUS:
            break
        banda = largura_da_faixa(passo, alvo)
        eixo.fill_between([k * PERIODO_DEGRAU_S, min((k + 1) * PERIODO_DEGRAU_S, limite)],
                          alvo - banda, alvo + banda,
                          color="0.6", alpha=0.25, linewidth=0,
                          label=rotulo_faixa if k == 0 else None)

    juntos = np.concatenate(medidos) if medidos else np.empty(0)
    if juntos.size:
        menor, maior = float(np.min(juntos)), float(np.max(juntos))
        folga = 0.08 * max(maior - menor, passo)
        eixo.set_ylim(menor - folga, maior + folga)

    eixo.text(0.98, 0.02, texto_acomodacao(grupo, por_degrau),
              transform=eixo.transAxes, fontsize=7.5, va="bottom", ha="right",
              family="monospace",
              bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, lw=0.5))
    eixo.set_xlabel("Tempo desde o comando (s)")
    eixo.set_ylabel("Deslocamento angular (graus)")
    sufixo = f" — zoom 0–{limite:g} s" if zoom else ""
    eixo.set_title(f"{ref['prototipo']} — {ref['categoria']}{sufixo}")
    eixo.legend(loc="upper left")
    fig.tight_layout()
    nome = ("angulo_zoom_" if zoom else "angulo_") + f"{ref['prototipo']}_{ref['categoria']}"
    salvar_figura_traj(fig, "ANGULO_ZOOM" if zoom else "ANGULO_TEMPO", nome)


def plot_media(grupo, por_degrau):
    """Media +- 1 desvio das repeticoes, com o erro num painel embaixo."""
    ref = grupo[0]
    grade, matriz = grade_comum(grupo)
    if grade.size == 0:
        print(f"  ! sem sobreposicao temporal em {ref['prototipo']}/{ref['categoria']}")
        return
    media = matriz.mean(axis=1)
    desvio = matriz.std(axis=1, ddof=1) if matriz.shape[1] > 1 else np.zeros_like(media)
    comando = trajetoria_desejada(grade, ref["passo"])

    fig, (sup, inf) = plt.subplots(
        2, 1, figsize=(FIG_TAMANHO[0], FIG_TAMANHO[1] * 1.35),
        sharex=True, gridspec_kw={"height_ratios": [2.2, 1.0]})
    sup.plot(grade, media, label=f"Média de {matriz.shape[1]} ensaios")
    sup.fill_between(grade, media - desvio, media + desvio, alpha=0.30,
                     label="± 1 desvio padrão")
    sup.plot(grade, comando, "k--", linewidth=1.6, label="Comando")
    sup.set_ylabel("Deslocamento angular (graus)")
    sup.set_title(f"{ref['prototipo']} — {ref['categoria']}")
    sup.legend(loc="upper left")
    inf.plot(grade, media - comando, color="tab:red")
    inf.axhline(0.0, color="k", linewidth=0.8)
    inf.set_xlabel("Tempo desde o comando (s)")
    inf.set_ylabel("Erro (graus)")
    fig.tight_layout()
    salvar_figura_traj(fig, "MEDIA_DESVIO", f"media_{ref['prototipo']}_{ref['categoria']}")


def plot_acomodacao(grupo, por_degrau):
    """Tempo de acomodacao degrau a degrau, por repeticao."""
    ref = grupo[0]
    fig, eixo = plt.subplots(figsize=FIG_TAMANHO)
    todos = []
    for ensaio in grupo:
        meu = por_degrau[
            (por_degrau["prototipo"] == ensaio["prototipo"])
            & (por_degrau["categoria"] == ensaio["categoria"])
            & (por_degrau["repeticao"] == ensaio["repeticao"])
        ]
        if meu.empty:
            continue
        eixo.plot(meu["degrau"], 1000 * meu["tempo_acomodacao_s"], "o-",
                  markersize=4, label=f"Experimento {ensaio['repeticao']}")
        todos.append(meu["tempo_acomodacao_s"].to_numpy())
    if todos:
        media = float(np.nanmean(np.concatenate(todos)))
        eixo.axhline(1000 * media, color="k", linestyle="--", linewidth=1.5,
                     label=f"Média: {1000*media:.0f} ms")
    eixo.set_xlabel("Degrau")
    eixo.set_ylabel("Tempo de acomodação (ms)")
    eixo.set_title(f"{ref['prototipo']} — {ref['categoria']} "
                   f"(±{100*BANDA_ACOMODACAO:.0f}% {BANDA_MODO})")
    eixo.legend(loc="best")
    fig.tight_layout()
    salvar_figura_traj(fig, "TEMPO_ACOMODACAO", f"acomodacao_{ref['prototipo']}_{ref['categoria']}")


def plot_comparacao_prototipos(resumo):
    """PE01 x PE02: tempo de acomodacao medio por categoria."""
    if resumo.empty:
        return
    tabela = resumo.pivot_table(index="categoria", columns="prototipo",
                                values="t_acomodacao_medio_s", aggfunc="mean")
    # O desvio entre degraus ja vem calculado no resumo; usar aggfunc="std"
    # aqui daria NaN, porque ha um unico valor por (categoria, prototipo).
    erros = resumo.pivot_table(index="categoria", columns="prototipo",
                               values="t_acomodacao_desvio_s", aggfunc="mean")
    erros = erros.reindex(index=tabela.index, columns=tabela.columns).fillna(0.0)
    fig, eixo = plt.subplots(figsize=(FIG_TAMANHO[0], FIG_TAMANHO[1]))
    posicoes = np.arange(len(tabela.index))
    largura = 0.8 / max(len(tabela.columns), 1)
    for i, coluna in enumerate(tabela.columns):
        eixo.bar(posicoes + i * largura, 1000 * tabela[coluna],
                 largura, yerr=1000 * erros[coluna],
                 capsize=3, label=coluna)
    eixo.set_xticks(posicoes + largura * (len(tabela.columns) - 1) / 2)
    eixo.set_xticklabels(tabela.index, rotation=30, ha="right")
    eixo.set_ylabel("Tempo de acomodação médio (ms)")
    eixo.set_title("Comparação entre protótipos (±5% do passo)")
    eixo.legend(loc="best")
    fig.tight_layout()
    salvar_figura_traj(fig, "TEMPO_ACOMODACAO", "comparacao_prototipos_acomodacao")


# ---------------------------------------------------------------------
# PARTE 7 - EXECUCAO
# ---------------------------------------------------------------------
def executar_trajetoria(cliente=None):
    if cliente is None and EM_COLAB:
        cliente = autenticar()

    print("PARTE 1/5 - Leitura das planilhas")
    ensaios = carregar_ensaios(cliente)
    print(f"  {len(ensaios)} ensaios carregados")

    print("PARTE 2/5 - Geometria, ângulo e alinhamento")
    for ensaio in ensaios:
        preparar(ensaio)

    print("PARTE 3/5 - Métricas")
    tabelas = [t for t in (metricas_por_degrau(e) for e in ensaios) if not t.empty]
    por_degrau = pd.concat(tabelas, ignore_index=True) if tabelas else pd.DataFrame()
    por_ensaio = pd.DataFrame([metricas_do_ensaio(e, por_degrau) for e in ensaios])

    # A faixa de acomodacao pode ser menor que a resolucao dos dados. Com
    # 3 algarismos significativos a incerteza chega a 0,25 graus; para o
    # passo de 2 graus a faixa de +-5% e +-0,1 grau. Nesse caso o tempo de
    # acomodacao NAO e mensuravel e nao deve ir para o artigo.
    avisados = set()
    for ensaio in ensaios:
        banda = largura_da_faixa(abs(ensaio["passo"]), abs(ensaio["passo"]))
        chave = (ensaio["prototipo"], ensaio["categoria"])
        if chave not in avisados and ensaio["resolucao_angular_max"] > banda:
            avisados.add(chave)
            print(f"  ! {chave[0]}/{chave[1]}: faixa de ±{banda:.2f}° é menor que a "
                  f"resolução dos dados (±{ensaio['resolucao_angular_max']:.2f}°). "
                  f"O tempo de acomodação desta categoria NÃO é confiável — "
                  f"reexporte do Tracker com mais casas decimais.")

    resumo = pd.DataFrame()
    if not por_degrau.empty:
        resumo = (por_degrau.groupby(["prototipo", "categoria"])
                  .agg(erro_medio_graus=("erro_graus", "mean"),
                       erro_desvio_graus=("erro_graus", "std"),
                       t_acomodacao_medio_s=("tempo_acomodacao_s", "mean"),
                       t_acomodacao_desvio_s=("tempo_acomodacao_s", "std"),
                       t_acomodacao_max_s=("tempo_acomodacao_s", "max"),
                       tempo_subida_medio_s=("tempo_subida_s", "mean"),
                       sobressinal_medio_pct=("sobressinal_pct", "mean"),
                       degraus=("degrau", "count"))
                  .reset_index())

    print("PARTE 4/5 - Gráficos")
    grupos = {}
    for ensaio in ensaios:
        grupos.setdefault((ensaio["prototipo"], ensaio["categoria"]), []).append(ensaio)
    for chave in sorted(grupos):
        grupo = sorted(grupos[chave], key=lambda e: e["repeticao"])
        print(f"  {chave[0]} / {chave[1]}")
        verificar_cadencia(grupo)
        plot_xy(grupo, por_degrau)
        plot_angulo(grupo, por_degrau)
        plot_angulo(grupo, por_degrau, zoom=ZOOM_SEGUNDOS)
        plot_media(grupo, por_degrau)
        plot_acomodacao(grupo, por_degrau)
    plot_comparacao_prototipos(resumo)

    print("PARTE 5/5 - Exportação")
    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    for nome, tabela in (("metricas_por_degrau", por_degrau),
                         ("metricas_por_ensaio", por_ensaio),
                         ("resumo_por_categoria", resumo)):
        if not tabela.empty:
            tabela.to_csv(os.path.join(PASTA_RESULTADOS, f"{nome}.csv"),
                          index=False, sep=";", decimal=",")
    print(f"Concluído. Resultados em {PASTA_RESULTADOS}")

    if not resumo.empty:
        print("\n=== TEMPO DE ACOMODAÇÃO (ms) ===")
        vista = resumo[["prototipo", "categoria",
                        "t_acomodacao_medio_s", "t_acomodacao_desvio_s",
                        "t_acomodacao_max_s"]].copy()
        for coluna in vista.columns[2:]:
            vista[coluna] = (1000 * vista[coluna]).round(0)
        vista.columns = ["Protótipo", "Categoria", "Média", "Desvio", "Máximo"]
        print(vista.to_string(index=False))

    return {"ensaios": ensaios, "metricas_por_degrau": por_degrau,
            "metricas_por_ensaio": por_ensaio, "resumo_por_categoria": resumo}


if EM_COLAB:
    RESULTADOS_TRAJETORIA = executar_trajetoria()
