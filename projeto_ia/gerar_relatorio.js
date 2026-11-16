// Gera Relatorio_Tecnico_Projeto_IA_Carlos_Jose.docx
// Uso: node gerar_relatorio.js <pasta_das_figuras>
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, LevelFormat, WidthType, ShadingType, BorderStyle,
  Footer, Header, PageNumber, TabStopType, VerticalAlign,
} = require('docx');

const FIG = process.argv[2] || 'figuras';
const FONTE = 'Arial';
const AZUL = '1F3864';
const LARGURA = 9638; // A4 com margens de 2 cm, em DXA

// ---------- auxiliares ----------
// Converte "texto **negrito** texto" em TextRuns
function runs(texto, extra = {}) {
  return texto.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map(p =>
    p.startsWith('**') ? new TextRun({ text: p.slice(2, -2), bold: true, ...extra })
                       : new TextRun({ text: p, ...extra }));
}
const par = (t, o = {}) => new Paragraph({ children: runs(t), alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 120, line: 276 }, ...o });
const item = t => new Paragraph({ children: runs(t), numbering: { reference: 'marcadores', level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 276 } });
const h1 = t => new Paragraph({ text: t, heading: HeadingLevel.HEADING_1 });
const h2 = t => new Paragraph({ text: t, heading: HeadingLevel.HEADING_2 });
const legenda = t => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 },
  children: [new TextRun({ text: t, italics: true, size: 18, color: '555555' })] });
const legendaTabela = t => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 80 },
  keepNext: true, children: [new TextRun({ text: t, italics: true, size: 18, color: '555555' })] });

function img(arquivo, largura) {
  const dados = fs.readFileSync(path.join(FIG, arquivo));
  const w = dados.readUInt32BE(16), h = dados.readUInt32BE(20); // tamanho do PNG
  return new ImageRun({ type: 'png', data: dados,
    transformation: { width: largura, height: Math.round(largura * h / w) } });
}
const figura = (...imagens) => new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
  spacing: { before: 120 }, children: imagens.flatMap((im, i) => i ? [new TextRun('  '), im] : [im]) });

const borda = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const bordas = { top: borda, bottom: borda, left: borda, right: borda };

// tabela(cabecalho, linhas, larguras, {destaque: [índices de linhas], alinhar: 'center'})
function tabela(cab, linhas, larguras, opc = {}) {
  const total = larguras.reduce((a, b) => a + b, 0);
  const celula = (texto, w, tipo, i) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders: bordas, verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: tipo === 'cab' ? { fill: AZUL, type: ShadingType.CLEAR, color: 'auto' }
           : tipo === 'dest' ? { fill: 'DCEFE6', type: ShadingType.CLEAR, color: 'auto' }
           : (i % 2 ? { fill: 'F2F5FA', type: ShadingType.CLEAR, color: 'auto' } : undefined),
    children: [new Paragraph({
      alignment: (tipo === 'cab' || i === undefined || opc.esquerda?.includes(i)) ? AlignmentType.CENTER
                 : AlignmentType.CENTER,
      children: runs(String(texto), tipo === 'cab' ? { bold: true, color: 'FFFFFF', size: 18 } : { size: 18 }),
    })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: larguras, alignment: AlignmentType.CENTER,
    rows: [
      new TableRow({ tableHeader: true, children: cab.map((c, j) => celula(c, larguras[j], 'cab')) }),
      ...linhas.map((l, i) => new TableRow({ cantSplit: true,
        children: l.map((c, j) => celula(c, larguras[j], (opc.destaque || []).includes(i) ? 'dest' : '', i)) })),
    ],
  });
}
const espaco = () => new Paragraph({ spacing: { after: 80 }, children: [] });

// ---------- conteúdo ----------
const c = [];

// Capa / cabeçalho
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400, after: 120 },
  children: [new TextRun({ text: 'Relatório Técnico', size: 26, bold: true, color: '666666' })] }));
c.push(new Paragraph({ heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER,
  children: [new TextRun('Projeto de Classificação de Dados – 2026.2')] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new TextRun({ text: 'Introdução à Inteligência Artificial para Engenharia', size: 22 })] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: AZUL, space: 8 } },
  children: runs('Aluno: **Carlos José**   |   Entrega: 02/12/2026', { size: 22 }) }));

c.push(h2('Resumo'));
c.push(par('Este relatório apresenta as duas atividades do projeto. Em ambas foram comparados os classificadores vistos em aula: **Regressão Logística, Árvore de Decisão, SVM, Rede Neural Perceptron simples e Rede Neural Multicamadas (MLP)**. Na **Parte 1**, eles foram aplicados à base Iris em três cenários de variáveis, usando matrizes de confusão e as métricas de sensibilidade, precisão e acurácia por classe. A melhor combinação foi a **Rede Neural MLP com PCA 1 e PCA 2**, com 97,3% de acurácia (4 erros em 150 flores). Na **Parte 2**, os mesmos algoritmos foram avaliados para classificar vinhos verdes brancos em "Bom" (nota maior ou igual a 6) ou "Regular" a partir de 11 análises físico-químicas. O **SVM com kernel RBF (C = 10)** obteve a maior acurácia na validação cruzada (78,9%) e, no conjunto de teste, alcançou acurácia de 78,7%, sensibilidade de 87,1% e especificidade de 61,9%. Nas duas bases, os modelos de fronteira não linear (MLP e SVM) superaram os lineares (Perceptron e Regressão Logística), como prevê a teoria.'));
c.push(par('Em todo o projeto foi usado **random_state = 68**, obtido pela soma das letras do primeiro nome: C(3) + A(1) + R(18) + L(12) + O(15) + S(19) = 68. O código-fonte está nos notebooks Projeto_IA_Parte1_Iris.ipynb e Projeto_IA_Parte2_Vinho.ipynb.'));

// ================= PARTE 1 =================
c.push(h1('1. Parte 1 – Classificação da base Iris'));
c.push(h2('1.1 Metodologia'));
c.push(par('A base Iris tem 150 flores (50 de cada espécie: setosa, versicolor e virginica) e 4 atributos, todos medidos em centímetros. Foram definidos três cenários de entrada:'));
c.push(item('**Cenário A:** as duas variáveis de maior correlação entre si – **comprimento e largura da pétala** (r = 0,963). São também as duas mais correlacionadas com a espécie (0,949 e 0,957).'));
c.push(item('**Cenário B:** as duas variáveis do cenário A + o primeiro componente principal (PCA 1).'));
c.push(item('**Cenário C:** apenas PCA 1 e PCA 2.'));
c.push(par('**PCA:** seguindo o procedimento da aula, o PCA foi aplicado diretamente sobre os 4 atributos originais, o que é adequado porque estão todos na mesma unidade (cm). O PCA 1 explica 92,5% da variação e o PCA 2 explica 5,3% (total de 97,8%). O PCA 1 é dominado pelo comprimento da pétala (peso 0,86) e o PCA 2 pelas medidas da sépala; por construção, os dois não são correlacionados.'));
c.push(par('**Classificadores:** Regressão Logística; Árvore de Decisão (profundidade máxima 3); SVM com kernel RBF; e as duas redes da aula de RNA, com a mesma configuração usada em sala – Perceptron simples (taxa de aprendizado 0,001) e MLP com duas camadas ocultas de 10 neurônios, ativação tanh e treinamento por gradiente descendente (sgd). Todos padronizam os dados antes de classificar.'));
c.push(par('**Avaliação:** como a base é pequena (um teste de 20% teria só 30 flores), usou-se **validação cruzada estratificada de 5 partes** com cross_val_predict (mesma técnica da aula de classificação): cada flor é prevista uma única vez por um modelo que não a viu no treino, e a matriz de confusão reúne as 150 previsões. As métricas por classe tratam cada espécie como "positiva" contra as demais: Sensibilidade = VP/(VP+FN), Precisão = VP/(VP+FP) e Acurácia da classe = (VP+VN)/total.'));
c.push(figura(img('p1_1.png', 300), img('p1_3.png', 300)));
c.push(legenda('Figura 1 – Matriz de correlação da Iris (esq.) e projeção das flores em PCA 1 x PCA 2 (dir.).'));

c.push(h2('1.2 Resultados'));
c.push(legendaTabela('Tabela 1 – Acurácia geral por cenário e classificador (entre parênteses: nº de erros em 150 flores; em negrito, o melhor de cada cenário)'));
c.push(tabela(['Cenário', 'Regressão Logística', 'Árvore de Decisão', 'SVM', 'Perceptron', 'Rede Neural MLP'], [
  ['A: 2 variáveis', '**95,3% (7)**', '94,0% (9)', '**95,3% (7)**', '90,0% (15)', '**95,3% (7)**'],
  ['B: 2 variáveis + PCA1', '95,3% (7)', '94,7% (8)', '95,3% (7)', '90,7% (14)', '**96,7% (5)**'],
  ['C: PCA1 + PCA2', '96,0% (6)', '92,7% (11)', '96,0% (6)', '89,3% (16)', '**97,3% (4)**'],
], [2238, 1480, 1480, 1480, 1480, 1480]));
c.push(figura(img('p1_4.png', 560)));
c.push(legenda('Figura 2 – Acurácia por cenário e classificador.'));
c.push(figura(img('p1_5.png', 640)));
c.push(legenda('Figura 3 – Matrizes de confusão (linhas: cenários A, B e C; colunas: classificadores). Linhas da matriz = espécie real; colunas = espécie prevista.'));

c.push(legendaTabela('Tabela 2 – Métricas por classe de casos selecionados (todas as combinações estão no notebook)'));
c.push(tabela(['Cenário / classificador', 'Classe', 'Precisão', 'Sensibilidade', 'Acurácia da classe'], [
  ['**C – MLP (melhor geral)**', 'setosa', '1,000', '1,000', '1,000'],
  ['', 'versicolor', '0,979', '0,940', '0,973'],
  ['', 'virginica', '0,942', '0,980', '0,973'],
  ['**B – MLP (melhor do B)**', 'setosa', '1,000', '1,000', '1,000'],
  ['', 'versicolor', '0,959', '0,940', '0,967'],
  ['', 'virginica', '0,941', '0,960', '0,967'],
  ['**A – Reg. Logística / SVM / MLP (empate)**', 'setosa', '1,000', '1,000', '1,000'],
  ['', 'versicolor', '0,922', '0,940', '0,953'],
  ['', 'virginica', '0,939', '0,920', '0,953'],
  ['**C – Perceptron (pior)**', 'setosa', '0,909', '1,000', '0,967'],
  ['', 'versicolor', '0,886', '0,780', '0,893'],
  ['', 'virginica', '0,882', '0,900', '0,927'],
], [3238, 1500, 1500, 1700, 1700], { destaque: [0, 1, 2] }));

c.push(h2('1.3 Análise e escolha do melhor classificador'));
c.push(item('**Setosa é sempre reconhecida** pelos modelos não lineares e pela Regressão Logística (100% de precisão e sensibilidade). Todos os erros desses modelos ocorrem entre **versicolor e virginica**, que se sobrepõem levemente nas medidas de pétala.'));
c.push(item('**Cenário A** já resolve bem o problema (94,0% a 95,3%): as pétalas são as variáveis mais discriminantes.'));
c.push(item('**Cenário B** traz ganho pequeno: o PCA 1 tem correlação de 0,998 com o comprimento da pétala, ou seja, é quase a mesma informação. Só a MLP (7 para 5 erros) e a Árvore (9 para 8) melhoraram.'));
c.push(item('**Cenário C** foi o melhor para Regressão Logística, SVM e MLP. PCA 1 e PCA 2 guardam 97,8% da variação e são não correlacionados: o PCA 1 resume as pétalas e o PCA 2 acrescenta a informação das sépalas sem repetição. A Árvore piorou (11 erros) porque só faz cortes paralelos aos eixos, e a fronteira entre versicolor e virginica fica inclinada no plano PCA 1 x PCA 2.'));
c.push(item('**O Perceptron simples foi o pior em todos os cenários** (cerca de 90%), inclusive errando algumas setosas. Como visto na aula de RNA, ele tem uma única camada e só traça fronteiras retas; a **MLP**, com camadas ocultas, resolve problemas não linearmente separáveis.'));
c.push(item('**Melhor classificador: Rede Neural MLP no cenário C** – maior acurácia (97,3%, 4 erros), com precisão, sensibilidade e acurácia por classe acima de 94% nas três espécies.'));

// ================= PARTE 2 =================
c.push(new Paragraph({ pageBreakBefore: true, text: '2. Parte 2 – Qualidade do Vinho Verde Branco', heading: HeadingLevel.HEADING_1 }));
c.push(par('A base Wine Quality (UCI) tem 4.898 vinhos verdes brancos, 11 atributos físico-químicos e uma nota de 0 a 10. A nota foi binarizada: **Bom (1)** se nota maior ou igual a 6 e **Regular (0)** caso contrário. Não há valores faltando. Existem 937 linhas repetidas, que foram mantidas por representarem vinhos distintos com as mesmas medições.'));

c.push(h2('2.1 Fase 1 – Análise descritiva e exploratória'));
c.push(figura(img('p2_1.png', 620)));
c.push(legenda('Figura 4 – Distribuição das notas originais e das classes após a binarização.'));
c.push(par('A base é **desbalanceada**: 3.258 vinhos "Bom" (66,5%) e 1.640 "Regular" (33,5%). Um classificador que respondesse sempre "Bom" já teria 66,5% de acurácia; por isso a acurácia deve ser analisada junto com sensibilidade e especificidade.'));
c.push(legendaTabela('Tabela 3 – Estatísticas descritivas dos 11 atributos (base completa)'));
c.push(tabela(['Atributo', 'Média', 'Mediana', 'Desvio padrão', 'Mínimo', 'Máximo', 'Correlação c/ rótulo'], [
  ['Acidez fixa', '6,855', '6,800', '0,844', '3,800', '14,200', '-0,090'],
  ['Acidez volátil', '0,278', '0,260', '0,101', '0,080', '1,100', '-0,225'],
  ['Ácido cítrico', '0,334', '0,320', '0,121', '0,000', '1,660', '-0,001'],
  ['Açúcar residual', '6,391', '5,200', '5,072', '0,600', '65,800', '-0,093'],
  ['Cloretos', '0,046', '0,043', '0,022', '0,009', '0,346', '-0,184'],
  ['SO₂ livre', '35,308', '34,000', '17,007', '2,000', '289,000', '-0,001'],
  ['SO₂ total', '138,361', '134,000', '42,498', '9,000', '440,000', '-0,171'],
  ['Densidade', '0,9940', '0,9937', '0,0030', '0,9871', '1,0390', '-0,269'],
  ['pH', '3,188', '3,180', '0,151', '2,720', '3,820', '0,084'],
  ['Sulfatos', '0,490', '0,470', '0,114', '0,220', '1,080', '0,052'],
  ['Álcool', '10,514', '10,400', '1,231', '8,000', '14,200', '0,383'],
], [1838, 1200, 1200, 1300, 1200, 1300, 1600]));
c.push(espaco());
c.push(par('Os atributos têm escalas muito diferentes (densidade em torno de 0,99 e SO₂ total em torno de 138), o que justifica a padronização na Fase 2. Comparando as classes, os vinhos bons têm em média **mais álcool** (10,8 contra 9,8) e **menos densidade, cloretos, acidez volátil e SO₂ total**.'));
c.push(figura(img('p2_2.png', 620)));
c.push(legenda('Figura 5 – Boxplots de cada atributo por classe (laranja = Regular, verde = Bom).'));
c.push(figura(img('p2_3.png', 620)));
c.push(legenda('Figura 6 – Histogramas normalizados por classe (1% dos valores mais extremos omitidos para legibilidade).'));
c.push(par('Boxplots e histogramas mostram que **as distribuições das duas classes se sobrepõem em quase todos os atributos**. A diferença mais nítida está no **álcool** (a mediana dos bons é 10,8 contra 9,6 dos regulares), seguida da **densidade**. Ácido cítrico, SO₂ livre, sulfatos e pH praticamente não mudam entre as classes.'));
c.push(figura(img('p2_4.png', 500)));
c.push(legenda('Figura 7 – Matriz de correlação entre os atributos e o rótulo.'));
c.push(figura(img('p2_5.png', 480)));
c.push(legenda('Figura 8 – Correlação de cada atributo com o rótulo (verde: positiva; laranja: negativa).'));
c.push(figura(img('p2_6.png', 640)));
c.push(legenda('Figura 9 – Gráficos de dispersão das melhores candidatas, coloridos pela classe.'));
c.push(par('**Análise de sobreposição.** Nos gráficos de dispersão os pontos "Bom" e "Regular" aparecem misturados: existe uma tendência (mais álcool e menos densidade/acidez volátil/cloretos favorecem a classe Bom), mas a fronteira entre as classes não é limpa nem linear. As **melhores candidatas** para a classificação são álcool (r = +0,38), densidade (r = −0,27), acidez volátil (−0,23), cloretos (−0,18) e SO₂ total (−0,17). A densidade é fortemente correlacionada com álcool (r = −0,78) e com açúcar residual (r = +0,84), ou seja, parte da informação é repetida. Essa sobreposição indica que o problema é bem mais difícil que o da Iris e que modelos capazes de traçar fronteiras curvas (SVM com kernel RBF e Rede Neural MLP) devem ter vantagem.'));

c.push(h2('2.2 Fase 2 – Preparação dos dados'));
c.push(legendaTabela('Tabela 4 – Separação estratificada treino/teste (random_state = 68)'));
c.push(tabela(['Grupo', 'Vinhos', 'Regular (0)', 'Bom (1)'], [
  ['Base completa', '4.898', '33,5%', '66,5%'],
  ['Treino (80%)', '3.918', '33,5%', '66,5%'],
  ['Teste (20%)', '980', '33,5%', '66,5%'],
], [3000, 2000, 2000, 2000]));
c.push(espaco());
c.push(par('**Justificativas das escolhas:**', { spacing: { after: 60 } }));
c.push(item('**Divisão 80/20:** 3.918 vinhos para aprender e 980 reservados como prova final, usados apenas na Fase 4.'));
c.push(item('**stratify = y:** garante a mesma proporção de classes (33,5% / 66,5%) no treino e no teste. Sem isso, o teste poderia ter menos vinhos regulares e distorcer a especificidade.'));
c.push(item('**random_state = 68:** usado na divisão, na validação cruzada e em todos os classificadores, garantindo resultados reproduzíveis.'));
c.push(item('**Padronização (StandardScaler – média 0 e desvio 1):** necessária para Regressão Logística, SVM e Redes Neurais, que trabalham com distâncias e somas ponderadas e seriam dominadas pelos atributos de valores grandes (SO₂ total, SO₂ livre). Para a Árvore de Decisão não é necessária, mas também não prejudica.'));
c.push(item('**Sem vazamento de informação:** a padronização fica dentro de um Pipeline junto com o classificador. Em cada rodada da validação cruzada, média e desvio são calculados apenas com os dados de treino daquela rodada; o conjunto de teste nunca participa desse cálculo.'));
c.push(item('**Todos os 11 atributos foram mantidos:** apesar da sobreposição, cada atributo contribui com um pouco de informação, e os modelos não lineares conseguem combiná-los.'));

c.push(h2('2.3 Fase 3 – Escolha e treinamento do classificador'));
c.push(par('Os cinco classificadores vistos em aula foram avaliados com **validação cruzada estratificada de 5 partes, somente no grupo de treino**. Para cada um foram testadas algumas configurações (busca em grade – GridSearchCV, como na aula de classificação), mantendo a de maior acurácia média. A Tabela 5 resume a teoria de cada modelo e o que foi testado.'));
c.push(legendaTabela('Tabela 5 – Classificadores comparados: base teórica e configurações testadas'));
c.push(tabela(['Modelo', 'Como funciona (aulas)', 'Fronteira', 'Configurações testadas'], [
  ['Regressão Logística', 'Combinação linear dos atributos convertida em probabilidade (sigmoide); classe 1 se p > 0,5', 'Reta', 'C = 0,1; 1; 10'],
  ['Árvore de Decisão', 'Sequência de perguntas; cada divisão busca a menor impureza (Gini ou Entropia)', 'Cortes retos em degraus', 'Gini ou Entropia; profundidade 4, 8, 12 ou livre'],
  ['SVM', 'Fronteira de maior margem; margem suave (C) para classes sobrepostas; truque do kernel', 'Reta ou curva (kernel)', 'Kernels linear, polinomial, RBF e sigmoide; C = 0,1; 1; 10'],
  ['Perceptron', 'Rede de uma camada com função limiar', 'Reta', 'Taxa de aprendizado 0,001; 0,01; 0,1'],
  ['Rede Neural MLP', 'Camadas ocultas treinadas por retropropagação', 'Curva', 'Camadas (10,10) ou (50,25); ativação tanh ou relu'],
], [1700, 3538, 1700, 2700]));

c.push(legendaTabela('Tabela 6 – Fase 3: média ± desvio padrão das 5 partes da validação cruzada (grupo de treino)'));
c.push(tabela(['Métrica', 'SVM (escolhido)', 'Rede Neural MLP', 'Árvore de Decisão', 'Regressão Logística', 'Perceptron'], [
  ['Melhor configuração', 'kernel RBF, C = 10', '(50, 25), tanh', 'entropia, sem limite', 'C = 10', 'taxa 0,001'],
  ['**Acurácia**', '0,789 ± 0,016', '0,776 ± 0,016', '0,773 ± 0,010', '0,747 ± 0,007', '0,684 ± 0,033'],
  ['**Sensibilidade**', '0,864 ± 0,015', '0,833 ± 0,024', '0,837 ± 0,020', '0,874 ± 0,012', '0,690 ± 0,062'],
  ['**Especificidade**', '0,641 ± 0,034', '0,662 ± 0,022', '0,646 ± 0,020', '0,495 ± 0,023', '0,673 ± 0,072'],
  ['**Precisão**', '0,827 ± 0,014', '0,831 ± 0,009', '0,824 ± 0,006', '0,775 ± 0,007', '0,809 ± 0,027'],
  ['**F1-Score**', '0,845 ± 0,012', '0,832 ± 0,014', '0,831 ± 0,009', '0,821 ± 0,005', '0,742 ± 0,037'],
], [1638, 1600, 1600, 1600, 1600, 1600]));
c.push(figura(img('p2_7.png', 560)));
c.push(legenda('Figura 10 – Acurácia, sensibilidade e especificidade médias na validação cruzada.'));

c.push(legendaTabela('Tabela 7 – Melhor resultado de cada kernel do SVM na validação cruzada'));
c.push(tabela(['Kernel do SVM', 'Melhor C', 'Acurácia', 'Sensibilidade', 'Especificidade'], [
  ['RBF (gaussiano)', '10,0', '78,9%', '86,4%', '64,1%'],
  ['Linear', '0,1', '75,0%', '88,9%', '47,3%'],
  ['Polinomial', '10,0', '74,5%', '89,8%', '44,1%'],
  ['Sigmoide', '0,1', '70,4%', '87,1%', '37,0%'],
], [2238, 1600, 1800, 2000, 2000], { destaque: [0] }));
c.push(espaco());
c.push(par('O kernel RBF foi claramente superior ao linear, principalmente na especificidade (64% contra 47%). Isso confirma, com o próprio SVM, a conclusão da Fase 1: as classes se sobrepõem e não são linearmente separáveis, e o "truque do kernel" permite traçar a fronteira curva necessária.'));
c.push(par('**Classificador escolhido: SVM com kernel RBF (C = 10).** Justificativa:', { spacing: { after: 60 } }));
c.push(item('Obteve a **maior acurácia** (78,9%) e o **maior F1-Score** (84,5%) na validação cruzada, com sensibilidade alta (86,4%) e especificidade de 64,1%.'));
c.push(item('A **Rede Neural MLP** ficou próxima (77,6%) e teve especificidade um pouco maior (66,2%), mas com acurácia e F1 menores, treino mais lento e maior dependência da configuração.'));
c.push(item('A **Árvore de Decisão** ficou no meio-termo; a melhor foi a de profundidade livre, que tende a se sobreajustar ao treino, como alertado na aula.'));
c.push(item('Os dois modelos **lineares** foram os piores: a **Regressão Logística** teve especificidade de apenas 49,5% (classifica quase tudo como "Bom") e o **Perceptron simples** obteve 68,4% de acurácia, praticamente igual aos 66,5% do chute "sempre Bom".'));
c.push(item('O resultado confirma a teoria: como as classes se sobrepõem de forma não linear, os modelos de fronteira curva (SVM com RBF e MLP) foram superiores.'));

c.push(h2('2.4 Fase 4 – Avaliação no conjunto de teste'));
c.push(par('O SVM escolhido foi treinado com todo o grupo de treino e aplicado aos 980 vinhos do conjunto de teste, que não participaram de nenhuma etapa anterior.'));
c.push(figura(img('p2_8.png', 300), img('p2_9.png', 290)));
c.push(legenda('Figura 11 – Matriz de confusão do SVM no conjunto de teste (esq.) e curva ROC (dir., AUC = 0,841).'));
c.push(legendaTabela('Tabela 8 – Matriz de confusão no teste (classe positiva = Bom)'));
c.push(tabela(['', 'Previsto: Regular', 'Previsto: Bom', 'Total real'], [
  ['**Real: Regular**', 'VN = 203', 'FP = 125', '328'],
  ['**Real: Bom**', 'FN = 84', 'VP = 568', '652'],
], [2400, 2400, 2400, 2000]));
c.push(legendaTabela('Tabela 9 – Tabela comparativa das métricas do SVM: validação cruzada (Fase 3) x conjunto de teste (Fase 4)'));
c.push(tabela(['Métrica', 'Fórmula aplicada', 'Validação cruzada (Fase 3)', 'Teste (Fase 4)', 'Diferença'], [
  ['**Acurácia**', '(VP+VN)/(VP+VN+FP+FN) = 771/980', '78,9%', '**78,7%**', '−0,3 p.p.'],
  ['**Precisão**', 'VP/(VP+FP) = 568/693', '82,7%', '**82,0%**', '−0,8 p.p.'],
  ['**Sensibilidade**', 'VP/(VP+FN) = 568/652', '86,4%', '**87,1%**', '+0,7 p.p.'],
  ['**Especificidade**', 'VN/(VN+FP) = 203/328', '64,1%', '**61,9%**', '−2,2 p.p.'],
  ['**F1-Score**', '2·P·S/(P+S)', '84,5%', '**84,5%**', '−0,1 p.p.'],
], [1638, 3000, 1800, 1600, 1600]));
c.push(espaco());
c.push(par('**Impacto prático dos erros para a vinícola:**', { spacing: { after: 60 } }));
c.push(item('**Falso Positivo (125 vinhos) – Regular aprovado como Bom:** é o erro mais grave para a marca. O vinho entra no lote e no preço de vinho bom, o consumidor percebe a qualidade inferior e o resultado é reclamação, devolução e desgaste da reputação.'));
c.push(item('**Falso Negativo (84 vinhos) – Bom rebaixado para Regular:** representa perda de receita, pois o vinho é vendido como produto de menor valor (ou volta para nova análise), mas não chega a decepcionar o cliente.'));
c.push(par('**Interpretação das métricas:**', { spacing: { before: 120, after: 60 } }));
c.push(item('**Acurácia de 78,7%:** cerca de 4 em cada 5 vinhos são classificados corretamente, bem acima dos 66,5% do chute "sempre Bom".'));
c.push(item('**Precisão de 82,0%:** quando o modelo aprova um vinho como Bom, acerta em cerca de 8 a cada 10 casos.'));
c.push(item('**Sensibilidade de 87,1%:** o modelo reconhece a grande maioria dos vinhos bons; poucos são rebaixados sem necessidade.'));
c.push(item('**Especificidade de 61,9%:** é o ponto fraco – quase 4 em cada 10 vinhos regulares passam como Bom, reflexo de a classe Regular ser minoria e se sobrepor à classe Bom.'));
c.push(item('**F1-Score de 84,5%:** bom equilíbrio entre precisão e sensibilidade.'));
c.push(item('As métricas de teste ficaram a no máximo 2,2 p.p. das obtidas na validação cruzada e a AUC foi de 0,841: o modelo **não decorou o treino** e deve manter desempenho semelhante com vinhos novos.'));
c.push(par('**Uso recomendado:** como a especificidade é a métrica mais fraca e o Falso Positivo é o erro mais caro, o modelo é indicado como **ferramenta de triagem**: vinhos classificados como "Regular" podem ser separados com boa confiança, e os classificados como "Bom" passam por degustação de confirmação. Se a vinícola quiser reduzir os Falsos Positivos, é possível ajustar o limite de decisão do SVM (deslocando-se na curva ROC) ou dar mais peso à classe Regular no treino, trocando um pouco de sensibilidade por especificidade.', { spacing: { before: 120, after: 120 } }));

// ================= CONCLUSÃO =================
c.push(h1('3. Conclusão'));
c.push(par('**Parte 1 (Iris):** a melhor combinação foi a **Rede Neural MLP com PCA 1 e PCA 2** (97,3% de acurácia, 4 erros em 150). As duas variáveis de maior correlação (pétalas) já contêm quase toda a informação necessária; acrescentar o PCA 1 traz pouco ganho, pois ele é praticamente igual ao comprimento da pétala. Já PCA 1 e PCA 2 juntos resumem 97,8% da variação em duas variáveis não correlacionadas, o que favoreceu os modelos que traçam fronteiras inclinadas ou curvas. O Perceptron simples, limitado a fronteiras retas, foi o pior em todos os cenários.'));
c.push(par('**Parte 2 (Vinho):** o melhor modelo foi o **SVM com kernel RBF (C = 10)**. Ele teve a maior acurácia (78,9%) e o maior F1-Score na validação cruzada dentro do grupo de treino e manteve desempenho praticamente igual no teste (acurácia de 78,7%, F1 de 84,5%). O SVM venceu porque as classes se sobrepõem de forma não linear, como mostrado na Fase 1, e o kernel RBF permite traçar fronteiras curvas combinando os 11 atributos padronizados (o mesmo SVM com kernel linear caiu para 75%). A Rede Neural MLP foi a segunda colocada; a Árvore de Decisão ficou no meio-termo, e os modelos lineares (Regressão Logística e Perceptron) foram os piores. O principal limite do modelo é a especificidade (cerca de 62%), o que o torna mais adequado como apoio à triagem do controle de qualidade do que como substituto da avaliação sensorial.'));

// ---------- documento ----------
const doc = new Document({
  creator: 'Carlos José',
  title: 'Relatório Técnico – Projeto de Classificação de Dados 2026.2',
  styles: {
    default: { document: { run: { font: FONTE, size: 21 } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONTE, size: 40, bold: true, color: AZUL },
        paragraph: { spacing: { before: 0, after: 160 }, keepNext: true } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONTE, size: 30, bold: true, color: AZUL },
        paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONTE, size: 25, bold: true, color: AZUL },
        paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: 'marcadores', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•',
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 },
      margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: LARGURA }],
      children: [new TextRun({ text: 'Projeto de Classificação de Dados – 2026.2 · Carlos José', size: 16, color: '888888' }),
        new TextRun({ children: ['\tPágina ', PageNumber.CURRENT], size: 16, color: '888888' })] })] }) },
    children: c,
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync('Relatorio_Tecnico_Projeto_IA_Carlos_Jose.docx', b);
  console.log('Gerado: Relatorio_Tecnico_Projeto_IA_Carlos_Jose.docx');
});
