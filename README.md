# PROJ 1 — CTG/UFPE — Análise de trajetória dos servos

Processamento dos dados de vídeo (Tracker) dos protótipos PE01, PE10,
PE11 e PE12: leitura das planilhas do Google Sheets, estimativa do
centro de rotação, cálculo do deslocamento angular, alinhamento das
repetições pelo instante do comando, comparação com a trajetória
desejada e geração de gráficos e métricas.

| arquivo | o que é |
|---|---|
| `proj1_analise.py` | pipeline completo (roda no Colab) |
| `REVISAO_METODO.md` | o que estava errado no script anterior e por quê |
| `tests/test_proj1_analise.py` | validação das funções com dados sintéticos |
| `tests/test_e2e_simulado.py` | pipeline inteiro contra um Sheets simulado |
| `exemplos/demo_sem_colab.py` | figuras "antes × depois", sem Colab |

## Uso no Colab

```python
!git clone https://github.com/carlosjljr/Claudinho.git
%cd Claudinho

from proj1_analise import Config, executar

cfg = Config()                 # ajuste aqui o que precisar
resultados = executar(cfg)     # autentica, lê, analisa, plota e exporta

resultados["metricas_por_degrau"].head()
resultados["resumo_por_categoria"]
```

`executar()` faz a autenticação e monta o Drive sozinho quando está no
Colab. As figuras vão para `RESULTADOS/` (PNG + PDF) e as métricas para
CSV com `;` e vírgula decimal, que abre direto no Excel em português.

### O que dá para ajustar em `Config`

```python
cfg = Config(
    planilhas=("PROJ 1_PE01", "PROJ 1_PE10"),   # subconjunto de protótipos
    categorias=("I_S1_P10", "I_S2_P10"),        # subconjunto de ensaios
    periodo_degrau_s=1.0,                       # cadência da escada
    angulo_max_graus=180.0,                     # saturação do servo
    zoom_segundos=3.0,                          # janela do gráfico com zoom
    fig_tamanho=(7.0, 4.5),                     # polegadas
    formatos_figura=("png", "pdf"),             # PDF é vetorial (artigo)
    mostrar_figuras=False,                      # não exibe, só salva
)
```

Os comprimentos dos elos ficam em `Config.elos` e são usados apenas para
**validar** o raio estimado dos dados — não entram no cálculo do ângulo.

### Cache

Na primeira execução os dados brutos são gravados em
`CACHE_DADOS/*.csv` no Drive. Nas execuções seguintes o script lê o
cache e **não toca na API do Sheets**, então dá para iterar nos
gráficos à vontade. Para forçar releitura, apague a pasta ou use
`Config(usar_cache=False)`.

## Rodando fora do Colab

As funções de análise não dependem do Colab:

```bash
python tests/test_proj1_analise.py      # verifica cada função isoladamente
python tests/test_e2e_simulado.py       # pipeline inteiro, Sheets simulado
python exemplos/demo_sem_colab.py       # gera figuras/ com o antes × depois
```

Requer apenas `numpy`, `pandas` e `matplotlib`.

## Atenção à precisão dos dados

Os dados exportados do Tracker chegam com **3 algarismos
significativos** (`3,07E+02`). Perto de x = 307 mm isso é 1 mm de
resolução, o que vira até 0,19° de incerteza angular — da mesma ordem
da ondulação que aparece no regime permanente. O script mede isso e
exporta em `metricas_por_ensaio.csv` (`algarismos_significativos`,
`resolucao_angular_graus`, `resolucao_angular_max_graus`), avisando no
log quando passa de 10% do passo comandado. Se essa ondulação for
discutida no artigo, vale reexportar do Tracker com mais casas.

## Saídas

```
RESULTADOS/
├── TRAJETORIA_XY/     trajetória no plano, com o arco desejado sobreposto
├── ANGULO_TEMPO/      Δθ × tempo desde o comando, com a escada comandada
├── ANGULO_ZOOM/       o mesmo, nos primeiros segundos
├── MEDIA_DESVIO/      média ± 1 desvio das repetições + painel de erro
├── metricas_por_degrau.csv    erro de regime, sobressinal, t_subida, t_acomodação
├── metricas_por_ensaio.csv    RMSE, raio e centro estimados, taxa de amostragem
└── resumo_por_categoria.csv   agregado por protótipo e categoria
```
