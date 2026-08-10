# Revisão do script de análise — PROJ 1 (CREEM)

Revisão do código de processamento dos dados do Tracker: erros que
impedem a execução ou distorcem o resultado, problemas de método e
otimizações. As conclusões abaixo se apoiam nos dois scripts enviados,
na saída de execução e nos gráficos de ângulo (PE01 I_S1_P10, PE01
I_S2_P10, PE10 I_S1_P05).

---

## 1. Por que os gráficos combinados não fecham

Esse é o sintoma principal e tem **três causas somadas**, todas no
mesmo ponto: a curva medida e a curva desejada estão em referenciais
diferentes.

### 1.1 O ângulo de repouso não é subtraído

O ângulo experimental é calculado como `atan2(y, x)` no referencial do
Tracker, e a curva desejada começa em 0°. Mas o braço **não** começa em
0°: nos seus próprios gráficos ele parte de 11,9° (PE01 I_S1_P10), de
15,85° (PE10 I_S1_P05) e de 18,3° (PE01 I_S2_P10). Enquanto esse offset
θ₀ não for removido, as duas curvas nunca coincidem — a diferença entre
elas é dominada pela pose inicial, não pelo desempenho do servo.

**Correção:** comparar o *deslocamento* angular Δθ = θ − θ₀ com o
comando, ou somar θ₀ ao comando. O script usa a primeira forma.

### 1.2 A curva desejada varre um arco que o ensaio não percorre

`cinematica_direta` gera a curva desejada num círculo de raio AB+BC
centrado em (0, 0), varrendo 0→180°. Os dados medidos estão no
referencial do Tracker e varrem θ₀ → θ₀ + N·passo. Mesmo quando a
origem do vídeo coincide com a junta, os dois arcos cobrem faixas
diferentes e têm raios diferentes (nominal × medido).

**Correção:** a curva desejada tem de nascer no **mesmo centro**, com o
**mesmo raio** e a partir do **mesmo ângulo inicial** dos dados. O
centro é estimado dos próprios pontos (ajuste de circunferência) e
validado contra AB+BC.

### 1.3 A referência desejada está errada no tempo

Na versão reduzida, `gera_trajetoria_desejada` virou uma rampa linear de
0 a 180° proporcional à duração do vídeo. O ensaio não é uma rampa: é
uma **escada de degraus**. Isso está visível nos gráficos que você
enviou — em I_S1_P10 o braço salta ~10° e estabiliza; em I_S1_P05 salta
~5°; e no I_S2_P10 aparece o segundo degrau de ~10° por volta da amostra
32, ou seja, ≈1,07 s a 30 fps. É exatamente o modelo que a versão longa
já usava (passo P a cada 1 s), e ele está certo.

Comparar um degrau com uma rampa produz um "erro" que mede a diferença
entre dois modelos, não o desempenho do servo.

**Correção:** voltar à escada, `trajetoria_desejada()`, com saturação em
180°.

---

## 2. Erros que quebram ou distorcem o resultado

| # | Onde | Problema | Efeito |
|---|------|----------|--------|
| 1 | PARTE 4 (v. longa) | `PLANILHA_PE01/PE10/PE11` nunca são criadas — o dicionário chama-se `planilhas` | `NameError`, o script para |
| 2 | `alinhar_matrizes_por_variacao` | Exige variação ≥ 4% **em X e em Y ao mesmo tempo** | O alinhamento nunca dispara (ver 2.1) |
| 3 | `calcular_media_tempos` (v. longa) | `if v is not None` não filtra `NaN` | Média vira `NaN` |
| 4 | `montar_matrizes` | v. longa corta no menor comprimento; v. reduzida repete o último valor | Descarta o fim do ensaio mais longo / inventa um patamar que não foi medido |
| 5 | `gera_trajetoria_desejada` (v. longa) | `inicio_segundos=0.1` fixo, mas o corte deixa o início em `pontos_anteriores/fps` = 0,167 s | Degraus deslocados ~67 ms |
| 6 | PARTES 10 e 11 (v. reduzida) | Eixo X em índice de amostra e curva desejada removida | Repetições de durações diferentes deixam de ser comparáveis |
| 7 | `plotar_zoom_angulos` (v. longa) | Índices tirados do vetor de tempo aplicados às matrizes X/Y | Funciona por coincidência (mesmo número de linhas) |
| 8 | `converter_para_float` | `except:` nu | Engole `KeyboardInterrupt` e `MemoryError` |
| 9 | PARTE 8 (v. reduzida) | Bloco inteiro duplicado, função redefinida | Ruído; risco de editar a cópia errada |
| 10 | PARTE 3 | `dados_experimentos` é montado e nunca usado | 72 leituras completas da API jogadas fora |
| 11 | Todas as plotagens | `plt.show()` em laço sem `plt.close()` | ~96 figuras a 300 dpi acumuladas na memória |
| 12 | Sem `np.unwrap` no ângulo | Saltos de ±180° em `atan2` | Descontinuidades artificiais se o ensaio cruzar o eixo |

### 2.1 O alinhamento nunca funcionou — demonstração numérica

O critério é

```python
if var_x >= limiar and var_y >= limiar:   # limiar = 0,04
```

Tome a primeira linha real de `I_S1_P02_1` (PE01): x = 307,00 e
y = 5,03 mm, ou seja θ₀ = 0,94° e R = 307,04 mm. Aplicando os degraus:

| passo | x (mm) | var. x | y (mm) | var. y | critério `and` |
|---|---|---|---|---|---|
| 2° | 307,00 → 306,64 | **0,12 %** | 5,03 → 15,74 | 213 % | não dispara |
| 5° | 307,00 → 305,39 | **0,52 %** | 5,03 → 31,77 | 532 % | não dispara |
| 10° | 307,00 → 301,46 | **1,80 %** | 5,03 → 58,26 | 1058 % | não dispara |

A variação em x fica sempre abaixo dos 4 % exigidos, então a condição
`and` é falsa em todos os passos. Resultado: `idx_var` permanece 0 e
**nenhum recorte é feito** — as três repetições continuam desalinhadas,
que é exatamente o que aparece nos seus gráficos de zoom (no PE01
I_S2_P10 o experimento 1 começa a subir na amostra 0, o experimento 2 na
amostra 4 e o experimento 3 na amostra 1).

O problema de fundo é usar variação percentual de coordenadas
cartesianas para detectar um evento **angular**. Perto do eixo X, y é
pequeno e qualquer ruído dá centenas de por cento; x quase não muda.

**Correção:** detectar o início sobre o próprio ângulo, com limiar em
graus (uma fração do passo comandado) e confirmação em N amostras
seguidas para não disparar com um ponto ruidoso.

---

## 3. Método recomendado

O pipeline reescrito segue esta sequência. Cada etapa é verificável e
rende número para o artigo.

### 3.1 Centro de rotação estimado dos dados

Para o servo 1 o efetuador descreve um arco em torno da junta A; para o
servo 2, em torno de B. Em vez de supor que a origem do Tracker é a
junta, o centro é obtido por ajuste algébrico de circunferência (Kåsa) e
comparado com a origem; escolhe-se o que der menor dispersão radial,
descartando resultados cujo raio se afaste mais de 25% do nominal
(AB+BC para S1, BC para S2).

Duas vantagens:

- **vira resultado do artigo**: o raio ajustado é uma medida
  independente do comprimento do elo. Nos seus dados a origem já está
  praticamente sobre a junta — a primeira amostra de `I_S1_P02_1` dá
  R = 307,04 mm contra AB+BC = 146,58 + 159,74 = 306,32 mm, **0,24 % de
  desvio**, o que valida a calibração do vídeo;
- **detecta erro de calibração**: se a origem do Tracker for marcada
  fora do eixo do servo, o ajuste corrige e o log avisa.

### 3.2 Deslocamento angular e tempo desde o comando

- θ(t) = atan2(y − y_c, x − x_c), com `np.unwrap`;
- θ₀ = mediana do platô inicial;
- Δθ = θ − θ₀, com o sinal ajustado para que o movimento seja positivo
  (o sentido de rotação no referencial do vídeo depende de como o eixo
  Y foi orientado no Tracker);
- τ = t − t_comando.

Com (τ, Δθ) todas as repetições e todos os protótipos ficam
diretamente comparáveis, sem cortar nem preencher matriz nenhuma.

### 3.3 Detecção do instante do comando

Fim do platô inicial: primeira amostra em que |θ − θ(0)| passa de
max(0,15·passo; 0,1°) e assim permanece por 3 amostras seguidas. τ = 0
fica na última amostra parada, de modo que o tempo morto do servo entra
no tempo de subida em vez de ser escondido.

Nos testes sintéticos o instante é recuperado com erro ≤ 1 amostra
(33 ms) para os passos de 2°, 5° e 10°.

### 3.4 Trajetória desejada

Escada: primeiro degrau em τ = 0, degraus de `passo` graus a cada 1 s,
saturando em 180°. O passo é lido do nome da aba (`P02` → 2°), o que
elimina a chance de passar o passo errado na chamada.

### 3.5 Métricas

Por degrau: erro de regime (média dos últimos 30% da janela),
sobressinal (% do passo), tempo de subida 10–90% e tempo de acomodação
em faixa de ±5% do passo. Global: RMSE e erro absoluto máximo contra o
comando. Entre repetições: média e desvio padrão numa grade temporal
comum, obtida por **interpolação** — não por repetição do último valor.

Tudo sai em CSV (`;` e vírgula decimal, abre direto no Excel pt-BR).

### 3.6 Achado importante: os dados estão gravados com 3 algarismos significativos

Repare no formato que sai do Tracker e fica na planilha:

```
0,00E+00   3,07E+02   5,03E+00
```

São **três algarismos significativos**. Perto de x = 307 mm isso
significa que x só pode assumir valores inteiros — o passo mínimo
representável é 1 mm. Propagando para o ângulo:

$$\delta\theta = \frac{\sqrt{(\Delta y\,q_x)^2 + (\Delta x\,q_y)^2}}{r^2}$$

| raio | pior caso de δθ | δθ típico |
|---|---|---|
| R = 306 mm (servo 1, PE01) | 0,19° | 0,12° |
| R = 111 mm (servo 2, PE10) | 0,23° | 0,05° |

Duas consequências:

1. **A ondulação de ±0,3° que aparece no regime permanente dos seus
   gráficos é da mesma ordem da quantização.** Não dá para afirmar, com
   os dados como estão, que ela é oscilação real do servo (*dither*) —
   parte dela é arredondamento do arquivo. Se essa ondulação for um
   resultado do artigo, vale reexportar do Tracker com mais casas
   decimais antes de discuti-la.
2. **A quantização é sistemática, não aleatória**, então não some com
   média: ela desloca o ajuste de circunferência. Foi assim que
   encontrei o problema — nos testes, o ajuste livre num arco de 40°
   com dados quantizados deslocou o centro em 1,8 mm e produziu um erro
   de regime que crescia degrau a degrau, chegando a 1,3°. Com o ajuste
   de raio fixo, o mesmo caso cai para 0,09°.

O script agora detecta o número de algarismos significativos dos dados,
calcula essa incerteza e a exporta em `metricas_por_ensaio.csv`
(colunas `algarismos_significativos`, `resolucao_angular_graus`,
`resolucao_angular_max_graus`), avisando no log quando ela passa de 10%
do passo comandado.

### 3.7 Demais incertezas a declarar no artigo

- resolução temporal: 33,3 ms (30 fps) — o alinhamento pelo instante do
  comando tem incerteza de ±1 amostra;
- desvio entre as três repetições: sai direto de
  `resumo_por_categoria.csv` (`erro_desvio_graus`);
- validação do comprimento do elo: raio ajustado × AB+BC nominal,
  exportado por ensaio.

### 3.8 Por que o ajuste do centro usa raio fixo

Medindo o erro do centro em função da varredura angular, com dados
quantizados a 3 algarismos:

| varredura | ajuste livre (3 parâmetros) | raio fixo (2 parâmetros) |
|---|---|---|
| 10° | **89,3 mm** | 0,05 mm |
| 20° | **20,0 mm** | 0,03 mm |
| 40° | 0,97 mm | 0,05 mm |
| 60° | 0,27 mm | 0,01 mm |
| 90° | 0,13 mm | 0,06 mm |
| 180° | 0,02 mm | 0,02 mm |

O ajuste livre só é confiável a partir de ~60° de varredura, e é por
isso que o script só o considera acima de 90° — nessa faixa ele vale a
pena, porque mede o raio de forma independente e valida AB+BC. Abaixo
disso entra o ajuste de raio fixo, que é bem condicionado em qualquer
varredura. Empates ficam com a origem do Tracker, para não trocar um
centro fisicamente significativo por um deslocamento de décimos de
milímetro.

---

## 4. Otimização da leitura

O gargalo é a API do Sheets, e foi por isso que os `time.sleep`
apareceram no script.

**Antes**

| etapa | chamadas |
|---|---|
| PARTE 3: `worksheet()` + `get_all_values()` para 4×18 abas | 144 |
| PARTE 4: `coletar_colunas` 3× por categoria, `worksheet()` + `col_values()` por aba | 432 |
| `gc.open()` | 4 |
| **total** | **~580** |

O limite da API é de 60 leituras por minuto por usuário, ou seja ~10
minutos só de espera — daí os `sleep` espalhados, que tratam o sintoma.

**Depois**

| etapa | chamadas |
|---|---|
| `gc.open()` | 4 |
| `worksheets()` (uma por planilha, para saber quais abas existem) | 4 |
| `values_batch_get()` (uma por planilha, todas as abas de uma vez) | 4 |
| **total** | **12** |

Mais: os dados brutos são gravados em CSV numa pasta de cache no Drive,
então **reprocessar gráficos não usa a API nenhuma vez**. Os `sleep`
fixos foram substituídos por *retry* com espera exponencial nos códigos
429/5xx, que é o tratamento correto para quota.

Outras mudanças estruturais:

- as ~81 variáveis globais do tipo `I_S1_P02_TEMPOS_PE01` viraram uma
  lista de objetos `Ensaio`, então acrescentar uma categoria ou um
  protótipo não exige copiar bloco de código;
- abas ausentes geram aviso e são puladas em vez de derrubar a execução
  (as categorias `II_D700`, `II_D1000` e `III_D1000` existem nas
  planilhas mas não estão na lista de análise — basta acrescentá-las em
  `Config.categorias`);
- estilo das figuras centralizado em `rcParams`. As fontes de 24–26 pt
  em figura de 12×8 pol geravam legenda cobrindo os dados (visível nos
  gráficos enviados) e arquivos de 3600×2400 px. O padrão agora é 7×4,5
  pol com fonte 11 pt, salvando **PNG e PDF** — o PDF é vetorial e é o
  que o template do CREEM aceita sem perda.

---

## 5. Verificação

Nenhuma dessas conclusões veio de leitura de código apenas — todas
foram medidas com dados sintéticos de parâmetros conhecidos.

**`tests/test_proj1_analise.py`** gera ensaios com resposta de segunda
ordem (ζ = 0,65, ωn = 28 rad/s), ângulo de repouso de 11,9°, escada de
degraus, ruído e quantização de 3 algarismos significativos, e confere
se a análise recupera os parâmetros. Cobre conversão de texto pt-BR,
ajuste de circunferência, escolha do centro (origem deslocada, arco
curto, dados quantizados), detecção do comando nos três passos, sentido
de rotação negativo, sobreposição das curvas em X-Y, métricas,
alinhamento de repetições com durações diferentes e casos de borda
(movimento na segunda amostra, ensaio parado).

Alguns resultados:

- alinhamento de três repetições com comandos em 1,8 s / 0,6 s / 2,7 s
  e durações diferentes: desvio máximo entre elas de **0,051°**;
- instante do comando recuperado com erro de **0 ms** (≤ 1 amostra) nos
  passos de 2°, 5° e 10°;
- erro de regime com dados quantizados: **0,09°** de máximo, sem
  deriva ao longo dos degraus (+0,004°/degrau).

**`tests/test_e2e_simulado.py`** roda `executar()` inteiro contra um
cliente do Sheets simulado, com os dados formatados exatamente como o
Tracker exporta. Verifica a leitura em lote (**3 chamadas por
planilha**), o descarte de abas fora da análise, a geração das 4
figuras por grupo, a exportação dos CSVs e que a **segunda execução não
faz nenhuma chamada à API** (cache) produzindo métricas idênticas.

**`exemplos/demo_sem_colab.py`** gera as figuras "antes × depois" sem
precisar de Colab nem das planilhas.
