# -*- coding: utf-8 -*-
"""PROJ 1 - CTG/UFPE - Analise das trajetorias dos servos.

Le os dados exportados do Tracker (t, x, y) armazenados em planilhas do
Google Sheets, estima o centro de rotacao de cada ensaio, converte a
posicao do efetuador em angulo, alinha as repeticoes pelo instante do
comando, compara com a trajetoria desejada (escada de degraus) e gera
graficos e metricas de desempenho.

O modulo roda no Google Colab (leitura das planilhas) mas as funcoes de
analise nao dependem do Colab: podem ser importadas e testadas
isoladamente com arrays numpy.

Uso no Colab:

    !git clone <repo> && cd Claudinho
    from proj1_analise import Config, executar
    resultados = executar(Config())
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

logger = logging.getLogger("proj1")

# As dependencias do Colab sao opcionais: sem elas o modulo continua
# importavel para testes locais e para reprocessar dados em cache.
try:  # pragma: no cover - depende do ambiente
    from google.colab import auth as _colab_auth, drive as _colab_drive
    from google.auth import default as _credenciais_padrao
    import gspread

    EM_COLAB = True
except Exception:  # pragma: no cover
    EM_COLAB = False


# =====================================================================
# PARTE 1 - CONFIGURACAO
# =====================================================================


@dataclass
class Config:
    """Parametros do processamento. Altere aqui, nao no meio do codigo."""

    # --- Fontes de dados -------------------------------------------------
    pasta_drive: str = "/content/drive/MyDrive/CTG_UFPE/PROJETOS/PROJ 1"
    subpasta_resultados: str = "RESULTADOS"
    subpasta_cache: str = "CACHE_DADOS"
    planilhas: Tuple[str, ...] = (
        "PROJ 1_PE01",
        "PROJ 1_PE10",
        "PROJ 1_PE11",
        "PROJ 1_PE12",
    )
    categorias: Tuple[str, ...] = (
        "I_S1_P02",
        "I_S1_P05",
        "I_S1_P10",
        "I_S2_P02",
        "I_S2_P05",
        "I_S2_P10",
    )
    n_repeticoes: int = 3
    usar_cache: bool = True

    # --- Modelo do ensaio ------------------------------------------------
    periodo_degrau_s: float = 1.0  # um degrau a cada 1 s
    angulo_max_graus: float = 180.0  # saturacao do servo
    passo_padrao_graus: float = 2.0  # usado se o nome nao tiver "Pxx"

    # --- Deteccao do inicio do movimento ---------------------------------
    fracao_tolerancia_plato: float = 0.15  # do passo, define o fim do plato
    tolerancia_plato_min_graus: float = 0.10
    n_confirmacoes: int = 3  # amostras seguidas fora do plato

    # --- Estimativa do centro de rotacao ---------------------------------
    tolerancia_raio_nominal: float = 0.25  # 25% de desvio aceitos
    dispersao_radial_max: float = 0.05  # 5% de std(r)/mean(r)
    varredura_minima_ajuste_livre: float = 90.0  # graus
    preferencia_origem: float = 1.2  # empate ate 20% pior fica com a origem

    # --- Metricas --------------------------------------------------------
    fracao_janela_regime: float = 0.30  # ultimos 30% do degrau = regime
    banda_acomodacao: float = 0.05  # +-5% do passo

    # --- Graficos --------------------------------------------------------
    fig_tamanho: Tuple[float, float] = (7.0, 4.5)
    fig_dpi: int = 300
    formatos_figura: Tuple[str, ...] = ("png", "pdf")
    zoom_segundos: float = 3.0
    margem_pre_comando_s: float = 0.2
    mostrar_figuras: bool = True

    # --- Geometria nominal dos elos (mm, medida na filmagem em t=0) ------
    # Serve apenas para validar o raio estimado a partir dos dados.
    elos: Dict[str, Dict[str, Dict[str, float]]] = field(
        default_factory=lambda: {
            "PROJ 1_PE01": {
                "I_S1_P02": {"AB": 146.58, "BC": 159.74},
                "I_S1_P05": {"AB": 145.56, "BC": 158.43},
                "I_S1_P10": {"AB": 146.74, "BC": 158.53},
                "I_S2_P02": {"BC": 167.25},
                "I_S2_P05": {"BC": 167.19},
                "I_S2_P10": {"BC": 167.18},
            },
            "PROJ 1_PE10": {
                "I_S1_P02": {"AB": 118.59, "BC": 113.00},
                "I_S1_P05": {"AB": 120.61, "BC": 118.34},
                "I_S1_P10": {"AB": 120.24, "BC": 118.08},
                "I_S2_P02": {"BC": 111.27},
                "I_S2_P05": {"BC": 110.91},
                "I_S2_P10": {"BC": 111.06},
            },
            "PROJ 1_PE11": {
                "I_S1_P02": {"AB": 118.59, "BC": 113.00},
                "I_S1_P05": {"AB": 120.61, "BC": 118.34},
                "I_S1_P10": {"AB": 120.24, "BC": 118.08},
                "I_S2_P02": {"BC": 111.27},
                "I_S2_P05": {"BC": 110.91},
                "I_S2_P10": {"BC": 111.06},
            },
            "PROJ 1_PE12": {
                "I_S1_P02": {"AB": 118.59, "BC": 113.00},
                "I_S1_P05": {"AB": 120.61, "BC": 118.34},
                "I_S1_P10": {"AB": 120.24, "BC": 118.08},
                "I_S2_P02": {"BC": 111.27},
                "I_S2_P05": {"BC": 110.91},
                "I_S2_P10": {"BC": 111.06},
            },
        }
    )

    @property
    def pasta_resultados(self) -> str:
        return os.path.join(self.pasta_drive, self.subpasta_resultados)

    @property
    def pasta_cache(self) -> str:
        return os.path.join(self.pasta_drive, self.subpasta_cache)


def configurar_log(nivel: int = logging.INFO) -> None:
    # force=True porque o Colab ja configura o logging na inicializacao e,
    # sem isso, basicConfig vira no-op e nada aparece.
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    logger.setLevel(nivel)


def configurar_estilo(cfg: Config) -> None:
    """Estilo unico para todas as figuras (padrao de artigo)."""
    matplotlib.rcParams.update(
        {
            "figure.figsize": cfg.fig_tamanho,
            "figure.dpi": 110,
            "savefig.dpi": cfg.fig_dpi,
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
            "legend.framealpha": 0.9,
        }
    )


# =====================================================================
# PARTE 2 - MODELO DO ENSAIO
# =====================================================================


def passo_da_categoria(categoria: str, padrao: float = 2.0) -> float:
    """Extrai o passo em graus do nome da categoria ("I_S1_P05" -> 5.0)."""
    achado = re.search(r"P(\d+)", categoria)
    return float(int(achado.group(1))) if achado else float(padrao)


def usa_dois_elos(categoria: str) -> bool:
    """S1 gira o conjunto todo (AB+BC); S2 gira apenas o elo BC."""
    return "S1" in categoria


def raio_nominal(cfg: Config, planilha: str, categoria: str) -> Optional[float]:
    params = cfg.elos.get(planilha, {}).get(categoria)
    if not params:
        return None
    if usa_dois_elos(categoria):
        if "AB" not in params or "BC" not in params:
            return None
        return float(params["AB"]) + float(params["BC"])
    if "BC" not in params:
        return None
    return float(params["BC"])


@dataclass
class Ensaio:
    """Uma repeticao de um ensaio, ja com as grandezas derivadas."""

    planilha: str
    categoria: str
    repeticao: int
    t: np.ndarray  # tempo bruto do Tracker (s)
    x: np.ndarray  # posicao do efetuador (mm)
    y: np.ndarray

    passo: float = np.nan
    centro: Tuple[float, float] = (0.0, 0.0)
    raio: float = np.nan
    origem_centro: str = ""
    theta: np.ndarray = field(default_factory=lambda: np.empty(0))  # graus
    theta0: float = np.nan  # angulo do repouso (graus)
    tau: np.ndarray = field(default_factory=lambda: np.empty(0))  # t - t_cmd
    sentido: int = 1
    indice_comando: int = 0
    resolucao_angular_graus: float = np.nan
    resolucao_angular_max_graus: float = np.nan
    algarismos_significativos: int = 0

    @property
    def rotulo(self) -> str:
        return f"{self.planilha} | {self.categoria} | rep {self.repeticao}"

    @property
    def theta_rel(self) -> np.ndarray:
        """Angulo medido em relacao ao repouso, ja com o sentido corrigido."""
        return self.sentido * (self.theta - self.theta0)

    @property
    def dt(self) -> float:
        return float(np.median(np.diff(self.t))) if self.t.size > 1 else np.nan


# =====================================================================
# PARTE 3 - LEITURA DAS PLANILHAS (uma chamada em lote por planilha)
# =====================================================================


def _com_retry(funcao, *args, tentativas: int = 5, **kwargs):
    """Repete a chamada com espera exponencial em erros de quota/rede."""
    espera = 2.0
    for tentativa in range(1, tentativas + 1):
        try:
            return funcao(*args, **kwargs)
        except Exception as erro:  # gspread.APIError, ConnectionError, ...
            resposta = getattr(erro, "response", None)
            codigo = getattr(resposta, "status_code", None)
            recuperavel = codigo in (429, 500, 502, 503, 504) or codigo is None
            if not recuperavel or tentativa == tentativas:
                raise
            logger.warning(
                "Falha na API (%s). Nova tentativa em %.0fs [%d/%d].",
                codigo or type(erro).__name__,
                espera,
                tentativa,
                tentativas,
            )
            time.sleep(espera)
            espera *= 2
    raise RuntimeError("inalcancavel")


def autenticar_colab():  # pragma: no cover - exige Colab
    """Autentica, monta o Drive e devolve o cliente gspread."""
    if not EM_COLAB:
        raise RuntimeError("Sem Google Colab: use o cache local de dados.")
    _colab_auth.authenticate_user()
    credenciais, _ = _credenciais_padrao()
    cliente = gspread.authorize(credenciais)
    _colab_drive.mount("/content/drive")
    return cliente


def _para_float(valores: Sequence[str]) -> np.ndarray:
    """Converte texto pt-BR ("3,07E+02") em float, sem estourar excecao."""
    serie = pd.Series(list(valores), dtype="object").astype(str).str.strip()
    tem_ponto_e_virgula = serie.str.contains(".", regex=False) & serie.str.contains(
        ",", regex=False
    )
    serie = serie.mask(tem_ponto_e_virgula, serie.str.replace(".", "", regex=False))
    serie = serie.str.replace(",", ".", regex=False)
    return pd.to_numeric(serie, errors="coerce").to_numpy(dtype=float)


def extrair_txy(linhas: Sequence[Sequence[str]]) -> Tuple[np.ndarray, ...]:
    """Converte a matriz de strings da aba em (t, x, y) numericos.

    O cabecalho e descartado automaticamente: qualquer linha que nao
    tenha os tres campos numericos e removida.
    """
    if not linhas:
        return np.empty(0), np.empty(0), np.empty(0)
    tabela = [(list(linha) + ["", "", ""])[:3] for linha in linhas]
    t = _para_float([linha[0] for linha in tabela])
    x = _para_float([linha[1] for linha in tabela])
    y = _para_float([linha[2] for linha in tabela])
    valido = np.isfinite(t) & np.isfinite(x) & np.isfinite(y)
    descartadas = int((~valido).sum())
    if descartadas:
        logger.debug("%d linha(s) nao numerica(s) descartada(s).", descartadas)
    return t[valido], x[valido], y[valido]


def abas_esperadas(cfg: Config) -> List[str]:
    return [
        f"{categoria}_{i}"
        for categoria in cfg.categorias
        for i in range(1, cfg.n_repeticoes + 1)
    ]


def ler_planilha(planilha, abas: Sequence[str]) -> Dict[str, List[List[str]]]:
    """Le varias abas em UMA chamada (values_batch_get) quando possivel."""
    existentes = {ws.title for ws in _com_retry(planilha.worksheets)}
    alvo = [aba for aba in abas if aba in existentes]
    faltando = [aba for aba in abas if aba not in existentes]
    if faltando:
        logger.warning("Abas ausentes em %s: %s", planilha.title, ", ".join(faltando))
    if not alvo:
        return {}

    if hasattr(planilha, "values_batch_get"):
        faixas = [f"'{aba}'!A:C" for aba in alvo]
        resposta = _com_retry(planilha.values_batch_get, faixas)
        blocos = resposta.get("valueRanges", [])
        if len(blocos) != len(alvo):
            raise RuntimeError(
                f"Resposta inconsistente do Sheets: {len(blocos)} faixas para "
                f"{len(alvo)} abas pedidas."
            )
        return {aba: bloco.get("values", []) for aba, bloco in zip(alvo, blocos)}

    # gspread antigo: uma chamada por aba (mais lento, mesmo resultado).
    return {
        aba: _com_retry(planilha.worksheet(aba).get_all_values) for aba in alvo
    }


def _caminho_cache(cfg: Config, planilha: str, aba: str) -> str:
    seguro = f"{planilha}__{aba}".replace(" ", "_").replace("/", "-")
    return os.path.join(cfg.pasta_cache, f"{seguro}.csv")


def carregar_ensaios(cfg: Config, cliente=None) -> List[Ensaio]:
    """Devolve todos os ensaios brutos, usando cache em disco quando houver."""
    ensaios: List[Ensaio] = []
    if cfg.usar_cache:
        os.makedirs(cfg.pasta_cache, exist_ok=True)

    for nome_planilha in cfg.planilhas:
        abas = abas_esperadas(cfg)
        em_cache = {
            aba: _caminho_cache(cfg, nome_planilha, aba)
            for aba in abas
            if cfg.usar_cache and os.path.exists(_caminho_cache(cfg, nome_planilha, aba))
        }
        faltantes = [aba for aba in abas if aba not in em_cache]

        brutos: Dict[str, List[List[str]]] = {}
        if faltantes:
            if cliente is None:
                raise RuntimeError(
                    f"Sem cache para {nome_planilha} e sem cliente gspread. "
                    "Rode no Colab ou preencha a pasta de cache."
                )
            planilha = _com_retry(cliente.open, nome_planilha)
            logger.info("Lendo %s (%d abas)...", nome_planilha, len(faltantes))
            brutos = ler_planilha(planilha, faltantes)

        for aba in abas:
            categoria, _, sufixo = aba.rpartition("_")
            repeticao = int(sufixo)
            if aba in em_cache:
                tabela = pd.read_csv(em_cache[aba])
                t = tabela["t"].to_numpy(float)
                x = tabela["x"].to_numpy(float)
                y = tabela["y"].to_numpy(float)
            elif aba in brutos:
                t, x, y = extrair_txy(brutos[aba])
                if cfg.usar_cache and t.size:
                    pd.DataFrame({"t": t, "x": x, "y": y}).to_csv(
                        _caminho_cache(cfg, nome_planilha, aba), index=False
                    )
            else:
                continue

            if t.size < 5:
                logger.warning("Aba %s/%s com poucos dados; ignorada.", nome_planilha, aba)
                continue

            ensaios.append(
                Ensaio(
                    planilha=nome_planilha,
                    categoria=categoria,
                    repeticao=repeticao,
                    t=t,
                    x=x,
                    y=y,
                    passo=passo_da_categoria(categoria, cfg.passo_padrao_graus),
                )
            )
    logger.info("Ensaios carregados: %d", len(ensaios))
    return ensaios


# =====================================================================
# PARTE 4 - GEOMETRIA: CENTRO DE ROTACAO E ANGULO
# =====================================================================


def ajustar_circulo(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """Ajuste algebrico de circunferencia (Kasa). Devolve (xc, yc, R)."""
    if x.size < 3:
        return np.nan, np.nan, np.nan
    matriz = np.column_stack((x, y, np.ones(x.size)))
    termo = x**2 + y**2
    solucao, *_ = np.linalg.lstsq(matriz, termo, rcond=None)
    xc = float(solucao[0] / 2.0)
    yc = float(solucao[1] / 2.0)
    sob_raiz = solucao[2] + xc**2 + yc**2
    raio = float(np.sqrt(sob_raiz)) if sob_raiz > 0 else np.nan
    return xc, yc, raio


def ajustar_centro_raio_fixo(
    x: np.ndarray,
    y: np.ndarray,
    raio: float,
    centro_inicial: Tuple[float, float] = (0.0, 0.0),
    iteracoes: int = 200,
    tol: float = 1e-10,
) -> Tuple[float, float]:
    """Ajusta so o centro, com o raio fixado no valor nominal.

    Com o raio conhecido sobram apenas dois parametros, e o problema
    deixa de ser mal condicionado em arcos curtos — situacao em que o
    ajuste livre de circunferencia erra grosseiramente (num arco de 10 graus
    ele chega a deslocar o centro em dezenas de milimetros).

    Itera c <- media(p_i - R * versor(p_i - c)), que e o passo de
    Gauss-Newton desse problema.
    """
    cx, cy = centro_inicial
    for _ in range(iteracoes):
        dx, dy = x - cx, y - cy
        norma = np.hypot(dx, dy)
        norma = np.where(norma > 0, norma, 1e-12)
        cx_novo = float(np.mean(x - raio * dx / norma))
        cy_novo = float(np.mean(y - raio * dy / norma))
        convergiu = abs(cx_novo - cx) < tol and abs(cy_novo - cy) < tol
        cx, cy = cx_novo, cy_novo
        if convergiu:
            break
    return cx, cy


def _estatisticas_radiais(
    x: np.ndarray, y: np.ndarray, centro: Tuple[float, float]
) -> Tuple[float, float]:
    """Devolve (raio medio, desvio dos raios em mm) em torno de um centro."""
    raios = np.hypot(x - centro[0], y - centro[1])
    media = float(np.mean(raios))
    if not np.isfinite(media) or media <= 0:
        return np.nan, np.inf
    return media, float(np.std(raios))


def varredura_estimada(x: np.ndarray, y: np.ndarray, raio: float) -> float:
    """Angulo central varrido (graus), estimado sem conhecer o centro.

    Usa a maior corda entre os pontos: corda = 2*R*sen(varredura/2).
    Satura em 180 graus, o que basta para decidir se o ajuste livre de
    circunferencia e confiavel.
    """
    if not np.isfinite(raio) or raio <= 0 or x.size < 2:
        return np.nan
    passo = max(1, x.size // 200)
    px, py = x[::passo], y[::passo]
    distancias = np.hypot(px[:, None] - px[None, :], py[:, None] - py[None, :])
    corda = float(distancias.max())
    return float(2.0 * np.degrees(np.arcsin(np.clip(corda / (2.0 * raio), 0.0, 1.0))))


def estimar_centro(
    x: np.ndarray,
    y: np.ndarray,
    cfg: Config,
    raio_esperado: Optional[float] = None,
) -> Tuple[Tuple[float, float], float, str]:
    """Determina o centro de rotacao do ensaio.

    Avalia ate tres hipoteses e fica com a que deixa os pontos mais
    proximos de uma circunferencia (menor desvio dos raios):

      1. **origem** — a origem do Tracker ja e a junta (caso desta base);
      2. **raio fixo** — ajusta o centro com o raio travado no nominal;
         confiavel mesmo em arcos curtos;
      3. **ajuste livre** — circunferencia de tres parametros; so entra
         quando a varredura passa de `varredura_minima_ajuste_livre`,
         porque abaixo disso ele e mal condicionado. E a unica hipotese
         que mede o raio de forma independente, util para validar AB+BC.

    Empates vao para a origem, para nao trocar um centro fisicamente
    significativo por um deslocamento de decimos de milimetro.

    Devolve ((xc, yc), raio, origem_da_estimativa).
    """
    candidatos: List[Tuple[str, Tuple[float, float]]] = [("origem", (0.0, 0.0))]

    if raio_esperado is not None and raio_esperado > 0:
        candidatos.append(
            ("raio fixo", ajustar_centro_raio_fixo(x, y, raio_esperado))
        )

    xc, yc, raio_livre = ajustar_circulo(x, y)
    if np.isfinite(xc) and np.isfinite(yc) and np.isfinite(raio_livre):
        referencia = raio_esperado if raio_esperado else raio_livre
        varredura = varredura_estimada(x, y, referencia)
        if np.isfinite(varredura) and varredura >= cfg.varredura_minima_ajuste_livre:
            candidatos.append(("ajuste livre", (xc, yc)))
        else:
            logger.debug(
                "Ajuste livre descartado: varredura de apenas %.0f graus.", varredura
            )

    avaliados = []
    for nome, centro in candidatos:
        raio, desvio = _estatisticas_radiais(x, y, centro)
        if not np.isfinite(raio):
            continue
        if raio_esperado is not None:
            if abs(raio - raio_esperado) / raio_esperado > cfg.tolerancia_raio_nominal:
                continue
        avaliados.append((desvio, nome, centro, raio))

    if not avaliados:
        raio, desvio = _estatisticas_radiais(x, y, (0.0, 0.0))
        logger.warning(
            "Nenhum centro compativel com o raio nominal (%.1f mm); usando a "
            "origem do Tracker (raio medido %.1f mm). Confira AB/BC em "
            "Config.elos e a calibracao do video.",
            raio_esperado if raio_esperado else float("nan"),
            raio,
        )
        return (0.0, 0.0), raio, "origem (sem validacao)"

    desvio, nome, centro, raio = min(avaliados, key=lambda item: item[0])

    # Occam: se a origem explica quase tao bem, fica com ela.
    origem = next((item for item in avaliados if item[1] == "origem"), None)
    if origem is not None and origem[0] <= cfg.preferencia_origem * desvio:
        desvio, nome, centro, raio = origem

    if raio > 0 and desvio / raio > cfg.dispersao_radial_max:
        logger.warning(
            "Pontos pouco circulares (desvio de %.2f mm em raio de %.1f mm) "
            "com centro '%s': confira a calibracao do Tracker.",
            desvio,
            raio,
            nome,
        )
    return centro, raio, nome


def angulo_desenrolado(
    x: np.ndarray, y: np.ndarray, centro: Tuple[float, float]
) -> np.ndarray:
    """Angulo do efetuador em graus, sem saltos de +-180."""
    return np.degrees(np.unwrap(np.arctan2(y - centro[1], x - centro[0])))


def algarismos_significativos(valores: np.ndarray, maximo: int = 12) -> int:
    """Com quantos algarismos significativos os dados foram gravados.

    O Tracker exporta em notacao cientifica com poucas casas ("3,07E+02"),
    e essa quantizacao vira erro angular: perto de x = 307 mm um passo de
    1 mm equivale a ~0,19 graus. Detectar isso permite declarar a
    resolucao real da medida no artigo.
    """
    amostra = valores[np.isfinite(valores) & (valores != 0.0)]
    if amostra.size == 0:
        return maximo
    passo = max(1, amostra.size // 400)
    digitos = []
    for valor in np.abs(amostra[::passo]):
        expoente = int(np.floor(np.log10(valor)))
        for n in range(1, maximo + 1):
            quantum = 10.0 ** (expoente - n + 1)
            if abs(valor / quantum - round(valor / quantum)) < 1e-6:
                digitos.append(n)
                break
        else:
            digitos.append(maximo)
    return int(np.median(digitos))


def _quantum(valores: np.ndarray, digitos: int) -> np.ndarray:
    """Menor incremento representavel em cada amostra."""
    modulo = np.abs(valores)
    expoente = np.where(modulo > 0, np.floor(np.log10(np.where(modulo > 0, modulo, 1.0))), 0.0)
    return np.where(modulo > 0, 10.0 ** (expoente - digitos + 1), 0.0)


def resolucao_angular(
    x: np.ndarray, y: np.ndarray, centro: Tuple[float, float]
) -> Tuple[float, float, int]:
    """Incerteza angular (graus) imposta pelo arredondamento dos dados.

    Propaga o quantum de x e y para theta = atan2(y - yc, x - xc):
        dtheta = sqrt((dy*qx)^2 + (dx*qy)^2) / r^2
    Devolve (mediana, maximo, algarismos significativos detectados).
    """
    digitos = min(algarismos_significativos(x), algarismos_significativos(y))
    dx = x - centro[0]
    dy = y - centro[1]
    r2 = dx**2 + dy**2
    valido = r2 > 0
    if not np.any(valido):
        return np.nan, np.nan, digitos
    incerteza = np.degrees(
        np.hypot(dy[valido] * _quantum(x, digitos)[valido],
                 dx[valido] * _quantum(y, digitos)[valido])
        / r2[valido]
    )
    return float(np.median(incerteza)), float(np.max(incerteza)), digitos


def detectar_inicio(
    theta: np.ndarray, passo: float, cfg: Config
) -> Tuple[int, float]:
    """Acha o instante do comando e o angulo de repouso.

    O criterio e o fim do plato inicial: antes do comando o braco esta
    parado, entao theta permanece dentro de uma faixa estreita em torno da
    primeira amostra. Exige N amostras seguidas fora da faixa para nao
    disparar com um unico ponto ruidoso.

    Devolve (indice do ultimo ponto parado, angulo de repouso em graus).
    """
    if theta.size == 0:
        return 0, np.nan

    tolerancia = max(
        cfg.fracao_tolerancia_plato * abs(passo), cfg.tolerancia_plato_min_graus
    )
    fora = np.abs(theta - theta[0]) > tolerancia

    n_conf = max(1, min(cfg.n_confirmacoes, theta.size))
    janelas = np.convolve(fora.astype(int), np.ones(n_conf, dtype=int), mode="valid")
    confirmadas = np.flatnonzero(janelas == n_conf)

    if confirmadas.size == 0:
        logger.warning("Movimento nao detectado; alinhando pela primeira amostra.")
        return 0, float(np.median(theta[: min(10, theta.size)]))

    inicio_movimento = int(confirmadas[0])
    indice_comando = max(inicio_movimento - 1, 0)
    repouso = float(np.median(theta[: max(indice_comando + 1, 1)]))
    return indice_comando, repouso


def preparar_ensaio(ensaio: Ensaio, cfg: Config) -> Ensaio:
    """Preenche centro, raio, angulo, repouso, sentido e tempo relativo."""
    esperado = raio_nominal(cfg, ensaio.planilha, ensaio.categoria)
    centro, raio, origem = estimar_centro(ensaio.x, ensaio.y, cfg, esperado)
    theta = angulo_desenrolado(ensaio.x, ensaio.y, centro)
    indice_comando, repouso = detectar_inicio(theta, ensaio.passo, cfg)

    # Sentido positivo = sentido em que o experimento efetivamente girou.
    cauda = theta[max(int(0.9 * theta.size), indice_comando + 1) :]
    deslocamento = float(np.median(cauda)) - repouso if cauda.size else 0.0
    sentido = -1 if deslocamento < 0 else 1

    ensaio.centro = centro
    ensaio.raio = raio
    ensaio.origem_centro = origem
    ensaio.theta = theta
    ensaio.theta0 = repouso
    ensaio.indice_comando = indice_comando
    ensaio.sentido = sentido
    ensaio.tau = ensaio.t - ensaio.t[indice_comando]

    if esperado is not None and np.isfinite(raio):
        desvio = 100 * abs(raio - esperado) / esperado
        if desvio > 10:
            logger.warning(
                "%s: raio medido %.1f mm x nominal %.1f mm (%.0f%% de desvio).",
                ensaio.rotulo,
                raio,
                esperado,
                desvio,
            )

    mediana, maximo, digitos = resolucao_angular(ensaio.x, ensaio.y, centro)
    ensaio.resolucao_angular_graus = mediana
    ensaio.resolucao_angular_max_graus = maximo
    ensaio.algarismos_significativos = digitos
    if np.isfinite(maximo) and maximo > 0.10 * abs(ensaio.passo):
        logger.warning(
            "%s: dados gravados com %d algarismos significativos; a "
            "quantizacao sozinha ja da ate %.2f graus de incerteza "
            "(%.0f%% do passo de %.0f graus).",
            ensaio.rotulo,
            digitos,
            maximo,
            100 * maximo / abs(ensaio.passo),
            ensaio.passo,
        )
    return ensaio


# =====================================================================
# PARTE 5 - TRAJETORIA DESEJADA E CINEMATICA DIRETA
# =====================================================================


def trajetoria_desejada(
    tau: np.ndarray, passo: float, cfg: Config, sentido: int = 1
) -> np.ndarray:
    """Escada de degraus: um degrau de `passo` graus a cada `periodo`.

    Em tau < 0 o comando e zero; o primeiro degrau ocorre em tau = 0 e os
    seguintes a cada `periodo_degrau_s`, saturando em `angulo_max_graus`.
    Devolve o angulo comandado RELATIVO ao repouso, em graus.
    """
    n_degraus = np.floor(tau / cfg.periodo_degrau_s) + 1.0
    comando = np.clip(n_degraus, 0.0, None) * abs(passo)
    comando = np.minimum(comando, cfg.angulo_max_graus)
    comando[tau < 0] = 0.0
    return sentido * comando


def cinematica_direta(
    angulo_absoluto_graus: np.ndarray,
    raio: float,
    centro: Tuple[float, float] = (0.0, 0.0),
) -> Tuple[np.ndarray, np.ndarray]:
    """Converte angulo em posicao (x, y) NO MESMO referencial dos dados.

    E este o ponto que fazia as curvas medida e desejada nao se
    sobreporem: a desejada precisa nascer no mesmo centro e com o mesmo
    raio da medida, e nao em (0, 0) com raio AB+BC nominal.
    """
    radianos = np.deg2rad(angulo_absoluto_graus)
    return centro[0] + raio * np.cos(radianos), centro[1] + raio * np.sin(radianos)


def curva_desejada_ensaio(
    ensaio: Ensaio, cfg: Config
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(comando relativo, x desejado, y desejado) sobre o tau do ensaio."""
    comando_rel = trajetoria_desejada(ensaio.tau, ensaio.passo, cfg, sentido=1)
    absoluto = ensaio.theta0 + ensaio.sentido * comando_rel
    x_des, y_des = cinematica_direta(absoluto, ensaio.raio, ensaio.centro)
    return comando_rel, x_des, y_des


# =====================================================================
# PARTE 6 - METRICAS DE DESEMPENHO
# =====================================================================


def _cruzamento(tau: np.ndarray, sinal: np.ndarray, nivel: float) -> float:
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
    fracao = (nivel - y0) / (y1 - y0)
    return float(tau[i - 1] + fracao * (tau[i] - tau[i - 1]))


def metricas_por_degrau(ensaio: Ensaio, cfg: Config) -> pd.DataFrame:
    """Erro de regime, sobressinal, tempo de subida e de acomodacao."""
    passo = abs(ensaio.passo)
    periodo = cfg.periodo_degrau_s
    resposta = ensaio.theta_rel  # ja com sentido corrigido, 0 no repouso
    tau = ensaio.tau

    n_max = int(np.floor(cfg.angulo_max_graus / passo))
    duracao = float(tau[-1]) if tau.size else 0.0
    n_degraus = min(n_max, int(np.floor(duracao / periodo)))

    linhas = []
    for k in range(n_degraus):
        inicio, fim = k * periodo, (k + 1) * periodo
        janela = (tau >= inicio) & (tau < fim)
        if janela.sum() < 3:
            continue

        tau_j = tau[janela]
        resp_j = resposta[janela]
        alvo = (k + 1) * passo
        valor_inicial = k * passo

        limite_regime = fim - cfg.fracao_janela_regime * periodo
        regime = resp_j[tau_j >= limite_regime]
        valor_regime = float(np.mean(regime)) if regime.size else np.nan

        pico = float(np.max(resp_j))
        sobressinal = 100.0 * (pico - alvo) / passo

        t10 = _cruzamento(tau_j, resp_j, valor_inicial + 0.1 * passo)
        t90 = _cruzamento(tau_j, resp_j, valor_inicial + 0.9 * passo)
        tempo_subida = t90 - t10 if np.isfinite(t10) and np.isfinite(t90) else np.nan

        banda = cfg.banda_acomodacao * passo
        fora_da_banda = np.flatnonzero(np.abs(resp_j - alvo) > banda)
        tempo_acomodacao = (
            float(tau_j[fora_da_banda[-1]] - inicio) if fora_da_banda.size else 0.0
        )

        linhas.append(
            {
                "planilha": ensaio.planilha,
                "categoria": ensaio.categoria,
                "repeticao": ensaio.repeticao,
                "degrau": k + 1,
                "alvo_graus": alvo,
                "regime_graus": valor_regime,
                "erro_graus": valor_regime - alvo,
                "erro_percentual": 100.0 * (valor_regime - alvo) / alvo,
                "sobressinal_percentual": sobressinal,
                "tempo_subida_s": tempo_subida,
                "tempo_acomodacao_s": tempo_acomodacao,
            }
        )
    return pd.DataFrame(linhas)


def metricas_globais(ensaio: Ensaio, cfg: Config) -> Dict[str, float]:
    """RMSE e erro maximo em relacao ao comando, para tau >= 0."""
    comando = trajetoria_desejada(ensaio.tau, ensaio.passo, cfg, sentido=1)
    valido = ensaio.tau >= 0
    erro = ensaio.theta_rel[valido] - comando[valido]

    resumo = {
        "planilha": ensaio.planilha,
        "categoria": ensaio.categoria,
        "repeticao": ensaio.repeticao,
        "duracao_s": float(ensaio.tau[-1]) if ensaio.tau.size else np.nan,
        "taxa_amostragem_hz": 1.0 / ensaio.dt if np.isfinite(ensaio.dt) else np.nan,
        "raio_mm": ensaio.raio,
        "centro_x_mm": ensaio.centro[0],
        "centro_y_mm": ensaio.centro[1],
        "angulo_repouso_graus": ensaio.theta0,
        "origem_centro": ensaio.origem_centro,
        "sentido": ensaio.sentido,
        "algarismos_significativos": ensaio.algarismos_significativos,
        "resolucao_angular_graus": ensaio.resolucao_angular_graus,
        "resolucao_angular_max_graus": ensaio.resolucao_angular_max_graus,
        "rmse_graus": np.nan,
        "erro_abs_max_graus": np.nan,
    }
    if erro.size:
        resumo["rmse_graus"] = float(np.sqrt(np.mean(erro**2)))
        resumo["erro_abs_max_graus"] = float(np.max(np.abs(erro)))
    return resumo


def grade_comum(
    ensaios: Sequence[Ensaio], cfg: Config
) -> Tuple[np.ndarray, np.ndarray]:
    """Reamostra as repeticoes num eixo tau unico e devolve (tau, matriz).

    Necessario porque as repeticoes tem duracoes diferentes: interpolar e
    correto, repetir o ultimo valor ate igualar o comprimento (como fazia
    a versao anterior) inventa um patamar que nao existiu.
    """
    if not ensaios:
        return np.empty(0), np.empty((0, 0))
    tau_min = max(float(e.tau[0]) for e in ensaios)
    tau_max = min(float(e.tau[-1]) for e in ensaios)
    if tau_max <= tau_min:
        return np.empty(0), np.empty((0, 0))
    passo_tempo = float(np.median([e.dt for e in ensaios]))
    grade = np.arange(tau_min, tau_max, passo_tempo)
    matriz = np.column_stack(
        [np.interp(grade, e.tau, e.theta_rel) for e in ensaios]
    )
    return grade, matriz


# =====================================================================
# PARTE 7 - GRAFICOS
# =====================================================================


def _salvar(fig, cfg: Config, pasta: str, nome: str) -> None:
    os.makedirs(pasta, exist_ok=True)
    for formato in cfg.formatos_figura:
        fig.savefig(os.path.join(pasta, f"{nome}.{formato}"), format=formato)
    if cfg.mostrar_figuras:
        plt.show()
    plt.close(fig)


def _nome_base(planilha: str, categoria: str) -> str:
    return f"{planilha.replace(' ', '_')}_{categoria}"


def plot_xy(ensaios: Sequence[Ensaio], cfg: Config, pasta: str) -> None:
    """Trajetoria no plano, no referencial da junta, com o arco desejado."""
    ref = ensaios[0]
    fig, eixo = plt.subplots(figsize=cfg.fig_tamanho)

    for ensaio in ensaios:
        eixo.plot(
            ensaio.x - ensaio.centro[0],
            ensaio.y - ensaio.centro[1],
            label=f"Experimento {ensaio.repeticao}",
        )

    _, x_des, y_des = curva_desejada_ensaio(ref, cfg)
    eixo.plot(
        x_des - ref.centro[0],
        y_des - ref.centro[1],
        "k--",
        linewidth=1.8,
        label="Trajetoria desejada",
    )
    eixo.plot(0, 0, "k+", markersize=9)

    eixo.set_xlabel("X (mm) — origem na junta")
    eixo.set_ylabel("Y (mm) — origem na junta")
    eixo.set_title(f"{ref.planilha} — {ref.categoria}")
    eixo.legend(loc="best")
    eixo.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    _salvar(fig, cfg, pasta, f"xy_{_nome_base(ref.planilha, ref.categoria)}")


def plot_angulo(
    ensaios: Sequence[Ensaio],
    cfg: Config,
    pasta: str,
    zoom: Optional[float] = None,
) -> None:
    """Angulo relativo x tempo, com a escada de comando sobreposta."""
    ref = ensaios[0]
    fig, eixo = plt.subplots(figsize=cfg.fig_tamanho)

    limite = zoom if zoom else max(float(e.tau[-1]) for e in ensaios)
    valores = []
    for ensaio in ensaios:
        recorte = (ensaio.tau >= -cfg.margem_pre_comando_s) & (ensaio.tau <= limite)
        eixo.plot(
            ensaio.tau[recorte],
            ensaio.theta_rel[recorte],
            label=f"Experimento {ensaio.repeticao}",
        )
        valores.append(ensaio.theta_rel[recorte])

    tau_cmd = np.linspace(-cfg.margem_pre_comando_s, limite, 2000)
    comando = trajetoria_desejada(tau_cmd, ref.passo, cfg, sentido=1)
    eixo.plot(tau_cmd, comando, "k--", linewidth=1.8, label="Comando (desejado)")

    # Limita o eixo aos dados medidos: se um degrau do comando cai
    # exatamente na borda do recorte, o salto vertical nao deve esticar
    # a escala inteira.
    medidos = np.concatenate(valores) if valores else np.empty(0)
    if medidos.size:
        minimo, maximo = float(np.min(medidos)), float(np.max(medidos))
        folga = 0.08 * max(maximo - minimo, abs(ref.passo))
        eixo.set_ylim(minimo - folga, maximo + folga)

    eixo.set_xlabel("Tempo desde o comando (s)")
    eixo.set_ylabel("Deslocamento angular (graus)")
    sufixo = f" — zoom 0–{limite:g} s" if zoom else ""
    eixo.set_title(f"{ref.planilha} — {ref.categoria}{sufixo}")
    eixo.legend(loc="upper left")
    fig.tight_layout()
    nome = "angulo_zoom_" if zoom else "angulo_"
    _salvar(fig, cfg, pasta, nome + _nome_base(ref.planilha, ref.categoria))


def plot_media_desvio(ensaios: Sequence[Ensaio], cfg: Config, pasta: str) -> None:
    """Media +- 1 desvio padrao das repeticoes, contra o comando."""
    ref = ensaios[0]
    grade, matriz = grade_comum(ensaios, cfg)
    if grade.size == 0:
        logger.warning("Sem sobreposicao temporal em %s/%s.", ref.planilha, ref.categoria)
        return

    media = matriz.mean(axis=1)
    desvio = matriz.std(axis=1, ddof=1) if matriz.shape[1] > 1 else np.zeros_like(media)
    comando = trajetoria_desejada(grade, ref.passo, cfg, sentido=1)

    fig, (sup, inf) = plt.subplots(
        2,
        1,
        figsize=(cfg.fig_tamanho[0], cfg.fig_tamanho[1] * 1.35),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.0]},
    )

    sup.plot(grade, media, label=f"Media de {matriz.shape[1]} ensaios")
    sup.fill_between(
        grade, media - desvio, media + desvio, alpha=0.30, label="± 1 desvio padrao"
    )
    sup.plot(grade, comando, "k--", linewidth=1.6, label="Comando")
    sup.set_ylabel("Deslocamento angular (graus)")
    sup.set_title(f"{ref.planilha} — {ref.categoria}")
    sup.legend(loc="upper left")

    inf.plot(grade, media - comando, color="tab:red")
    inf.axhline(0.0, color="k", linewidth=0.8)
    inf.set_xlabel("Tempo desde o comando (s)")
    inf.set_ylabel("Erro (graus)")
    fig.tight_layout()
    _salvar(fig, cfg, pasta, f"media_{_nome_base(ref.planilha, ref.categoria)}")


# =====================================================================
# PARTE 8 - ORQUESTRACAO
# =====================================================================


def agrupar(ensaios: Sequence[Ensaio]) -> Dict[Tuple[str, str], List[Ensaio]]:
    grupos: Dict[Tuple[str, str], List[Ensaio]] = {}
    for ensaio in ensaios:
        grupos.setdefault((ensaio.planilha, ensaio.categoria), []).append(ensaio)
    for lista in grupos.values():
        lista.sort(key=lambda e: e.repeticao)
    return grupos


def executar(cfg: Optional[Config] = None, cliente=None) -> Dict[str, object]:
    """Roda o pipeline completo e devolve ensaios, metricas e resumo."""
    cfg = cfg or Config()
    configurar_log()
    configurar_estilo(cfg)

    if cliente is None and EM_COLAB:  # pragma: no cover
        cliente = autenticar_colab()

    logger.info("PARTE 1/5 — leitura das planilhas")
    ensaios = carregar_ensaios(cfg, cliente)

    logger.info("PARTE 2/5 — geometria, angulo e alinhamento")
    for ensaio in ensaios:
        preparar_ensaio(ensaio, cfg)

    logger.info("PARTE 3/5 — metricas")
    tabelas = [metricas_por_degrau(e, cfg) for e in ensaios]
    tabelas = [tabela for tabela in tabelas if not tabela.empty]
    por_degrau = (
        pd.concat(tabelas, ignore_index=True) if tabelas else pd.DataFrame()
    )
    resumo_ensaio = pd.DataFrame([metricas_globais(e, cfg) for e in ensaios])

    resumo = pd.DataFrame()
    if not por_degrau.empty:
        resumo = (
            por_degrau.groupby(["planilha", "categoria"])
            .agg(
                erro_medio_graus=("erro_graus", "mean"),
                erro_desvio_graus=("erro_graus", "std"),
                sobressinal_medio=("sobressinal_percentual", "mean"),
                tempo_subida_medio_s=("tempo_subida_s", "mean"),
                tempo_acomodacao_medio_s=("tempo_acomodacao_s", "mean"),
                degraus_avaliados=("degrau", "count"),
            )
            .reset_index()
        )

    logger.info("PARTE 4/5 — graficos")
    grupos = agrupar(ensaios)
    pastas = {
        "xy": os.path.join(cfg.pasta_resultados, "TRAJETORIA_XY"),
        "angulo": os.path.join(cfg.pasta_resultados, "ANGULO_TEMPO"),
        "zoom": os.path.join(cfg.pasta_resultados, "ANGULO_ZOOM"),
        "media": os.path.join(cfg.pasta_resultados, "MEDIA_DESVIO"),
    }
    for (planilha, categoria), lista in grupos.items():
        logger.info("Graficos de %s / %s", planilha, categoria)
        plot_xy(lista, cfg, pastas["xy"])
        plot_angulo(lista, cfg, pastas["angulo"])
        plot_angulo(lista, cfg, pastas["zoom"], zoom=cfg.zoom_segundos)
        plot_media_desvio(lista, cfg, pastas["media"])

    logger.info("PARTE 5/5 — exportacao")
    os.makedirs(cfg.pasta_resultados, exist_ok=True)
    for nome, tabela in (
        ("metricas_por_degrau", por_degrau),
        ("metricas_por_ensaio", resumo_ensaio),
        ("resumo_por_categoria", resumo),
    ):
        if not tabela.empty:
            tabela.to_csv(
                os.path.join(cfg.pasta_resultados, f"{nome}.csv"),
                index=False,
                decimal=",",
                sep=";",
            )
    logger.info("Concluido. Resultados em %s", cfg.pasta_resultados)

    return {
        "ensaios": ensaios,
        "metricas_por_degrau": por_degrau,
        "metricas_por_ensaio": resumo_ensaio,
        "resumo_por_categoria": resumo,
    }


if __name__ == "__main__":  # pragma: no cover
    executar()
