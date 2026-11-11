// =====================================================================
// CARACTERIZACAO DO SG90 - tudo dentro do Arduino IDE
// =====================================================================
// Acha a faixa util do servo, calibra graus -> microssegundos e passa a
// posicionar pela calibracao medida. Nao precisa de Python.
//
// COMO O SERVO RESPONDE AO PULSO  (leia antes de rodar)
// O SG90 e um servo de POSICAO, nao de passo. Cada largura de pulso
// corresponde a uma posicao ABSOLUTA do braco, e ele vai para la
// sozinho, pelo caminho mais curto, na velocidade que conseguir:
//
//     ~500 us   ---->  um extremo do curso  (chame de 0 graus)
//     ~1500 us  ---->  o meio               (~90 graus)
//     ~2500 us  ---->  o outro extremo      (~180 graus)
//
// Entao o braco NAO "comeca em zero e sobe". Ele comeca onde o PRIMEIRO
// pulso mandar. Se o sketch acordasse ja enviando 500 us, o braco
// atravessaria o curso inteiro de uma vez e bateria no batente -- por
// isso o primeiro pulso aqui e 1500 us, o meio, que e sempre seguro.
//
// O que a varredura de micropassos faz e percorrer essa escala devagar,
// parando em cada largura, para medir QUAL angulo corresponde a QUAL
// largura. A escala existe desde o inicio; o que nao se conhece ainda e
// onde ela comeca, onde termina, e quantos graus cabem em cada
// microssegundo.
//
// Fora dos extremos o braco nao tem para onde ir: encosta no batente
// interno e o servo continua empurrando, puxando corrente e zumbindo.
// ZUMBIDO COM O BRACO PARADO = passou do limite. Recue.
//
// O SKETCH NAO ENXERGA O BRACO
// Malha aberta: nao ha realimentacao. Ele nao sabe se o braco andou,
// parou ou travou. Por isso quem marca o limite e voce -- e para isso o
// avanco e passo a passo, pausavel e reversivel, nunca uma corrida as
// cegas ate a ponta.
//
// LIGACAO
//   sinal -> pino 9
//   VCC   -> fonte externa de 5 V (o 5 V da placa nao aguenta: o SG90
//            passa de 700 mA no arranque e derruba o Arduino)
//   GND   -> GND da fonte E GND do Arduino, no mesmo ponto
//
// ---------------------------------------------------------------------
// ROTEIRO
//   1. Monitor Serial em 9600, com "Nova linha" ao final.
//   2. A         o braco comeca a andar, um micropasso por vez, a
//                partir do meio, descendo. Cada passo sai na serial.
//   3. P         pausa assim que ele parar de avancar (ou zumbir).
//      -  +      ajuste fino: recue ou avance de um passo para achar o
//                ULTIMO pulso em que ele ainda se mexeu.
//      A         se quiser continuar descendo, retoma de onde parou.
//   4. F         fecha este lado: grava o limite, inverte o sentido e
//                volta ao meio. Mande A de novo para procurar o outro.
//   5. F         no segundo lado, encerra a busca e mostra a faixa.
//   6. M <graus> dentro da faixa, posicione (U <us>), meca o angulo com
//                transferidor ou video e registre o par.
//   7. R         ajusta a reta graus->us com os pares registrados.
//   8. G <graus> daqui em diante o braco vai ao angulo de verdade.
//      E         grava a calibracao na EEPROM.
//   9. V         varredura completa, para registrar a curva em video.
//
// Se voce ja conhece a faixa, pule 2 a 5 com  J <min> <max>.
//
// NO TINKERCAD
// O servo simulado e ideal: aceita 544..2400 us, nao tem zona morta,
// nem folga, nem batente, e nao zumbe. Serve para conferir os comandos
// e a serial; os limites e a calibracao so saem do servo de verdade.
// Se o Tinkercad reclamar do EEPROM.h, troque USAR_EEPROM para 0.
// =====================================================================
#define USAR_EEPROM 1

// Botoes fisicos em paralelo com a serial: A, P e F tambem acontecem
// apertando um botao. Duas razoes:
//   1. o monitor serial do TinkerCad pode nao ter campo de envio, e sem
//      ele a busca nao poderia ser conduzida ali;
//   2. na bancada, a mao fica no botao e o olho no braco -- digitar no
//      teclado enquanto se observa o braco e justamente o que faz
//      passar do ponto.
// Ligue cada botao entre o pino e o GND; o pull-up interno cuida do
// resto. Para desligar, troque por 0.
#define USAR_BOTOES 1

#include <Servo.h>
#if USAR_EEPROM
#include <EEPROM.h>
#endif

const uint8_t PINO_SERVO = 9;
const uint8_t PINO_LED = LED_BUILTIN;
#if USAR_BOTOES
const uint8_t PINO_BOTAO_A = 2;   // avanca
const uint8_t PINO_BOTAO_P = 3;   // pausa
const uint8_t PINO_BOTAO_F = 4;   // fecha o lado
const unsigned long ANTIRRUIDO_MS = 40;
#endif

// Nenhum comando passa daqui, em nenhuma circunstancia. E a trava que
// impede uma busca distraida de levar o servo muito alem do batente.
const int LIMITE_ABSOLUTO_MIN = 400;
const int LIMITE_ABSOLUTO_MAX = 2600;
const int PULSO_SEGURO = 1500;         // meio do curso
const unsigned long PAUSA_COMANDO_MS = 80;  // silencio que fecha a linha
const uint8_t MAX_PARES = 12;          // pontos de calibracao guardados

int larguraMin = 1000;     // faixa de trabalho, estreita ate ser medida
int larguraMax = 2000;
int micropasso = 5;        // us por passo da busca
int intervaloMs = 1200;    // tempo parado em cada passo da busca
int esperaMs = 400;        // tempo parado em cada largura da varredura
int larguraAtual = PULSO_SEGURO;

// Busca do limite --------------------------------------------------
// sentido: -1 procura o limite de baixo, +1 o de cima.
// andando: true enquanto o braco avanca sozinho.
// Os dois lados ja fechados sao marcados para o F saber se ainda falta
// um lado ou se e hora de encerrar.
int sentido = -1;
bool andando = false;
bool fechadoBaixo = false;
bool fechadoCima = false;
unsigned long proximoPasso = 0;

// Calibracao. Comeca com o padrao da biblioteca, que e justamente o que
// se quer substituir por medicao.
float usPorGrau = (2400.0 - 544.0) / 180.0;
float usEmZeroGrau = 544.0;

int paresUs[MAX_PARES];
float paresGrau[MAX_PARES];
uint8_t nPares = 0;

Servo servo;

// ---------------------------------------------------------------------
// MOVIMENTO
// ---------------------------------------------------------------------
void aplicar(int largura) {
  largura = constrain(largura, LIMITE_ABSOLUTO_MIN, LIMITE_ABSOLUTO_MAX);
  if (!servo.attached()) {
    servo.attach(PINO_SERVO, LIMITE_ABSOLUTO_MIN, LIMITE_ABSOLUTO_MAX);
  }
  servo.writeMicroseconds(largura);
  larguraAtual = largura;
}

void mostrarPulso(const char* prefixo) {
  Serial.print(prefixo);
  Serial.print(larguraAtual);
  Serial.print(F(" us  (grau estimado "));
  Serial.print((larguraAtual - usEmZeroGrau) / usPorGrau, 1);
  Serial.println(F(")"));
}

bool darPasso(int direcao) {
  int alvo = larguraAtual + direcao * micropasso;
  if (alvo < LIMITE_ABSOLUTO_MIN || alvo > LIMITE_ABSOLUTO_MAX) {
    Serial.println(F("! trava do sketch; nao vou alem"));
    return false;
  }
  aplicar(alvo);
  mostrarPulso("  ");
  return true;
}

// ---------------------------------------------------------------------
// BUSCA DO LIMITE: A avanca, P pausa, F fecha o lado
// ---------------------------------------------------------------------
void avancar() {
  if (fechadoBaixo && fechadoCima) {
    Serial.println(F("A busca ja terminou. J <min> <max> refaz a faixa "
                     "na mao."));
    return;
  }
  andando = true;
  proximoPasso = millis();
  Serial.print(F("[A] andando "));
  Serial.print(sentido < 0 ? F("para BAIXO") : F("para CIMA"));
  Serial.print(F(", "));
  Serial.print(micropasso);
  Serial.print(F(" us a cada "));
  Serial.print(intervaloMs);
  Serial.println(F(" ms."));
  Serial.println(F("    P pausa  |  - e + ajustam de um passo  |  "
                   "F fecha este lado"));
}

void pausar(bool avisar) {
  if (!andando) {
    if (avisar) mostrarPulso("[P] parado em ");
    return;
  }
  andando = false;
  if (avisar) {
    mostrarPulso("[P] pausado em ");
    Serial.println(F("    ainda avancava? A retoma. Parou de vez? "
                     "ajuste com - / + e feche com F"));
  }
}

void finalizar() {
  pausar(false);

  // Com os dois lados ja fechados, um F extra -- tecla repetida, linha
  // reenviada -- sobrescreveria a faixa com a posicao atual, que pode
  // estar em qualquer lugar. Aqui ele so repete o resumo.
  if (fechadoBaixo && fechadoCima) {
    Serial.print(F("[F] a busca ja terminou: faixa "));
    Serial.print(larguraMin);
    Serial.print(F(" a "));
    Serial.print(larguraMax);
    Serial.println(F(" us. Para refazer, use J <min> <max>."));
    return;
  }

  // O limite guardado recua uma margem: quando o braco para de avancar
  // ele JA esta encostado no batente, e deixar o limite exatamente ali
  // significa trabalhar empurrando a trava.
  int margem = 2 * micropasso;
  if (sentido < 0) {
    larguraMin = larguraAtual + margem;
    fechadoBaixo = true;
    Serial.print(F("[F] limite INFERIOR = "));
    Serial.print(larguraMin);
  } else {
    larguraMax = larguraAtual - margem;
    fechadoCima = true;
    Serial.print(F("[F] limite SUPERIOR = "));
    Serial.print(larguraMax);
  }
  Serial.print(F(" us   (parou em "));
  Serial.print(larguraAtual);
  Serial.print(F(", recuei "));
  Serial.print(margem);
  Serial.println(F(" us de margem)"));

  if (fechadoBaixo && fechadoCima) {
    if (larguraMax <= larguraMin) {
      Serial.println(F("! os dois limites se cruzaram; refaca com J "
                       "<min> <max>"));
      return;
    }
    aplicar((larguraMin + larguraMax) / 2);
    Serial.println(F("--- busca concluida ---"));
    Serial.print(F("  faixa util: "));
    Serial.print(larguraMin);
    Serial.print(F(" a "));
    Serial.print(larguraMax);
    Serial.print(F(" us  ("));
    Serial.print(larguraMax - larguraMin);
    Serial.println(F(" us de curso)"));
    Serial.println(F("  Agora a calibracao: U <us> posiciona, meca o "
                     "angulo e registre com M <graus>."));
    Serial.println(F("  Com 2 ou mais pontos, R ajusta a reta."));
  } else {
    sentido = -sentido;
    aplicar(PULSO_SEGURO);
    Serial.print(F("    volto ao meio; agora o outro lado ("));
    Serial.print(sentido < 0 ? F("para BAIXO") : F("para CIMA"));
    Serial.println(F("). Mande A."));
  }
}

// ---------------------------------------------------------------------
// CALIBRACAO
// ---------------------------------------------------------------------
void registrarPar(float graus) {
  if (nPares >= MAX_PARES) {
    Serial.println(F("! cheio; use R para ajustar ou Z para zerar"));
    return;
  }
  paresUs[nPares] = larguraAtual;
  paresGrau[nPares] = graus;
  nPares++;
  Serial.print(F("ponto "));   Serial.print(nPares);
  Serial.print(F(": "));       Serial.print(larguraAtual);
  Serial.print(F(" us = "));   Serial.print(graus, 2);
  Serial.println(F(" graus"));
}

void ajustarReta() {
  // Minimos quadrados de us = a*graus + b. Com dois pontos vira a reta
  // que passa por eles; com mais, a que melhor representa o conjunto --
  // e por isso vale medir em varias posicoes, e nao so nas duas pontas,
  // onde a folga e maior.
  if (nPares < 2) {
    Serial.println(F("! preciso de pelo menos 2 pontos (comando M)"));
    return;
  }
  float somaX = 0, somaY = 0, somaXY = 0, somaXX = 0;
  for (uint8_t i = 0; i < nPares; i++) {
    somaX += paresGrau[i];
    somaY += paresUs[i];
    somaXY += paresGrau[i] * paresUs[i];
    somaXX += paresGrau[i] * paresGrau[i];
  }
  float n = nPares;
  float denominador = n * somaXX - somaX * somaX;
  if (fabs(denominador) < 1e-6) {
    Serial.println(F("! os pontos tem o mesmo angulo; meca em posicoes "
                     "diferentes"));
    return;
  }
  usPorGrau = (n * somaXY - somaX * somaY) / denominador;
  usEmZeroGrau = (somaY - usPorGrau * somaX) / n;

  float pior = 0;
  for (uint8_t i = 0; i < nPares; i++) {
    float previsto = usEmZeroGrau + usPorGrau * paresGrau[i];
    float desvio = fabs(paresUs[i] - previsto);
    // Comparacao explicita em vez de max(): em placas cujo core define
    // max como template (ESP32, SAMD), misturar float com double nao
    // compila. Assim o sketch vale em qualquer placa.
    if (desvio > pior) pior = desvio;
  }

  Serial.println(F("--- calibracao ajustada ---"));
  Serial.print(F("  us = "));     Serial.print(usEmZeroGrau, 1);
  Serial.print(F(" + "));         Serial.print(usPorGrau, 4);
  Serial.println(F(" * graus"));
  Serial.print(F("  0 grau -> "));   Serial.print(usEmZeroGrau, 0);
  Serial.print(F(" us ; 180 graus -> "));
  Serial.print(usEmZeroGrau + 180.0 * usPorGrau, 0);
  Serial.println(F(" us"));
  Serial.print(F("  maior desvio: ")); Serial.print(pior, 1);
  Serial.print(F(" us ("));            Serial.print(pior / usPorGrau, 2);
  Serial.println(F(" graus)"));
  float padrao = (2400.0 - 544.0) / 180.0;
  Serial.print(F("  a biblioteca Servo usa "));  Serial.print(padrao, 4);
  Serial.print(F(" us/grau ("));
  Serial.print(100.0 * (usPorGrau / padrao - 1.0), 1);
  Serial.println(F("% de diferenca)"));
}

#if USAR_EEPROM
const int ENDERECO = 0;
const uint32_t ASSINATURA = 0x53473930;   // "SG90"

void gravarEeprom() {
  int endereco = ENDERECO;
  EEPROM.put(endereco, ASSINATURA);       endereco += sizeof(ASSINATURA);
  EEPROM.put(endereco, usPorGrau);        endereco += sizeof(usPorGrau);
  EEPROM.put(endereco, usEmZeroGrau);     endereco += sizeof(usEmZeroGrau);
  EEPROM.put(endereco, larguraMin);       endereco += sizeof(larguraMin);
  EEPROM.put(endereco, larguraMax);
  Serial.println(F("gravado na EEPROM; sobrevive a desligar a placa"));
}

bool lerEeprom() {
  int endereco = ENDERECO;
  uint32_t marca;
  EEPROM.get(endereco, marca);
  if (marca != ASSINATURA) return false;
  endereco += sizeof(marca);
  EEPROM.get(endereco, usPorGrau);        endereco += sizeof(usPorGrau);
  EEPROM.get(endereco, usEmZeroGrau);     endereco += sizeof(usEmZeroGrau);
  EEPROM.get(endereco, larguraMin);       endereco += sizeof(larguraMin);
  EEPROM.get(endereco, larguraMax);
  return true;
}
#endif

// ---------------------------------------------------------------------
// VARREDURA
// ---------------------------------------------------------------------
void piscarSincronismo() {
  for (uint8_t i = 0; i < 3; i++) {
    digitalWrite(PINO_LED, HIGH); delay(120);
    digitalWrite(PINO_LED, LOW);  delay(120);
  }
}

void registrar(const char* direcao) {
  Serial.print(millis());       Serial.print(';');
  Serial.print(larguraAtual);   Serial.print(';');
  Serial.print(direcao);        Serial.print(';');
  Serial.println((larguraAtual - usEmZeroGrau) / usPorGrau, 2);
}

void varrer() {
  Serial.println(F("# varredura; 3 piscadas marcam o inicio no video"));
  Serial.println(F("# ms;largura_us;sentido;grau_estimado"));
  aplicar(larguraMin);
  delay(1000);
  piscarSincronismo();

  for (int us = larguraMin; us <= larguraMax; us += micropasso) {
    aplicar(us); delay(esperaMs); registrar("sobe");
  }
  // A volta mede a folga da engrenagem: o braco nao para no mesmo lugar
  // chegando por cima e por baixo. Sem ela, essa parcela some dentro do
  // erro e nao da para separar do ganho.
  for (int us = larguraMax; us >= larguraMin; us -= micropasso) {
    aplicar(us); delay(esperaMs); registrar("desce");
  }
  Serial.println(F("# fim"));
}

// ---------------------------------------------------------------------
// SERIAL
// ---------------------------------------------------------------------
void mostrarEstado() {
  Serial.println(F("--- estado ---"));
  Serial.print(F("  pulso atual: "));  Serial.print(larguraAtual);
  Serial.print(F(" us   |   "));
  Serial.println(andando ? F("ANDANDO") : F("parado"));
  Serial.print(F("  faixa: "));        Serial.print(larguraMin);
  Serial.print(F(" a "));              Serial.print(larguraMax);
  Serial.print(F(" us   |   lado de baixo "));
  Serial.print(fechadoBaixo ? F("fechado") : F("em aberto"));
  Serial.print(F(", de cima "));
  Serial.println(fechadoCima ? F("fechado") : F("em aberto"));
  Serial.print(F("  micropasso: "));   Serial.print(micropasso);
  Serial.print(F(" us   |   intervalo: ")); Serial.print(intervaloMs);
  Serial.print(F(" ms   |   pontos: ")); Serial.println(nPares);
  Serial.print(F("  us = "));  Serial.print(usEmZeroGrau, 1);
  Serial.print(F(" + "));      Serial.print(usPorGrau, 4);
  Serial.println(F(" * graus"));
}

void mostrarAjuda() {
  Serial.println(F("=== comandos ==="));
  Serial.println(F("  A          avanca passo a passo (retoma depois do P)"));
  Serial.println(F("  P          pausa onde esta"));
  Serial.println(F("  F          fecha o lado: grava o limite e inverte"));
  Serial.println(F("  -  /  +    recua / avanca UM micropasso"));
  Serial.println(F("  U <us>     vai direto para uma largura de pulso"));
  Serial.println(F("  J <a> <b>  define a faixa na mao, sem busca"));
  Serial.println(F("  C          volta ao meio (1500 us)"));
  Serial.println(F("  M <graus>  registra: pulso atual = angulo medido"));
  Serial.println(F("  R          ajusta a reta graus->us"));
  Serial.println(F("  Z          apaga os pontos de calibracao"));
  Serial.println(F("  G <graus>  vai ao angulo usando a calibracao"));
  Serial.println(F("  V          varredura completa (sobe e desce)"));
  Serial.println(F("  D <us>     micropasso   I <ms> intervalo da busca"));
  Serial.println(F("  T <ms>     espera da varredura"));
#if USAR_EEPROM
  Serial.println(F("  E / B      grava / busca na EEPROM"));
#endif
  Serial.println(F("  L          solta o servo     ?  estado"));
}

long lerInteiro(const char* texto, const char** fim) {
  while (*texto == ' ') texto++;
  long valor = atol(texto);
  if (fim) {
    while (*texto && *texto != ' ') texto++;
    *fim = texto;
  }
  return valor;
}

float lerDecimal(const char* texto) {
  while (*texto == ' ') texto++;
  return atof(texto);
}

void executar(char* linha) {
  char comando = toupper(linha[0]);
  char* argumento = linha + 1;

  switch (comando) {
    // --- busca do limite ---
    case 'A': avancar(); break;
    case 'P': pausar(true); break;
    case 'F': finalizar(); break;

    case '-': pausar(false); darPasso(-1); break;
    case '+': pausar(false); darPasso(+1); break;

    case 'U': {
      pausar(false);
      int us = (int)lerInteiro(argumento, NULL);
      if (us > 0) {
        // Fora da faixa ja medida o braco pode estar contra o batente.
        // O comando continua valendo -- a trava absoluta e que protege
        // o servo -- mas sai avisado, para nao passar despercebido.
        if (fechadoBaixo && fechadoCima
            && (us < larguraMin || us > larguraMax)) {
          Serial.print(F("! "));
          Serial.print(us);
          Serial.print(F(" us esta fora da faixa medida ("));
          Serial.print(larguraMin);
          Serial.print(F(" a "));
          Serial.print(larguraMax);
          Serial.println(F(" us); confira se o braco nao travou"));
        }
        aplicar(us);
        mostrarPulso("pulso = ");
      }
      break;
    }
    case 'J': {
      const char* resto;
      int a = (int)lerInteiro(argumento, &resto);
      int b = (int)lerInteiro(resto, NULL);
      if (a > 0 && b > a) {
        larguraMin = constrain(a, LIMITE_ABSOLUTO_MIN, LIMITE_ABSOLUTO_MAX);
        larguraMax = constrain(b, LIMITE_ABSOLUTO_MIN, LIMITE_ABSOLUTO_MAX);
        fechadoBaixo = fechadoCima = true;
        pausar(false);
        aplicar((larguraMin + larguraMax) / 2);
        Serial.println(F("faixa definida na mao"));
      } else {
        Serial.println(F("! uso: J <min> <max>, com max > min"));
      }
      mostrarEstado();
      break;
    }
    case 'C':
      pausar(false);
      aplicar(PULSO_SEGURO);
      mostrarPulso("meio do curso: ");
      break;

    // --- calibracao ---
    case 'M': registrarPar(lerDecimal(argumento)); break;
    case 'R': ajustarReta(); break;
    case 'Z': nPares = 0; Serial.println(F("pontos apagados")); break;
    case 'G': {
      float graus = lerDecimal(argumento);
      int alvo = (int)round(usEmZeroGrau + usPorGrau * graus);
      if (alvo < larguraMin || alvo > larguraMax) {
        Serial.print(F("! "));            Serial.print(graus, 1);
        Serial.print(F(" graus daria ")); Serial.print(alvo);
        Serial.println(F(" us, fora da faixa"));
        break;
      }
      pausar(false);
      aplicar(alvo);
      Serial.print(graus, 1);     Serial.print(F(" graus -> "));
      Serial.print(larguraAtual); Serial.println(F(" us"));
      break;
    }

    // --- varredura e parametros ---
    case 'V': pausar(false); varrer(); break;
    case 'D': {
      int valor = (int)lerInteiro(argumento, NULL);
      if (valor > 0) micropasso = valor;
      mostrarEstado();
      break;
    }
    case 'I': {
      int valor = (int)lerInteiro(argumento, NULL);
      if (valor > 0) intervaloMs = valor;
      mostrarEstado();
      break;
    }
    case 'T': {
      int valor = (int)lerInteiro(argumento, NULL);
      if (valor > 0) esperaMs = valor;
      mostrarEstado();
      break;
    }
#if USAR_EEPROM
    case 'E': gravarEeprom(); break;
    case 'B':
      if (lerEeprom()) {
        fechadoBaixo = fechadoCima = true;
        Serial.println(F("calibracao e faixa recuperadas da EEPROM"));
        mostrarEstado();
      } else {
        Serial.println(F("! nao ha calibracao gravada"));
      }
      break;
#endif
    case 'L': pausar(false); servo.detach();
              Serial.println(F("servo solto")); break;
    case '?': mostrarEstado(); break;
    default:  mostrarAjuda(); break;
  }
}

#if USAR_BOTOES
// Le os tres botoes e dispara a mesma acao do comando digitado. Sem
// delay(): um delay aqui travaria o avanco entre os passos.
void lerBotoes() {
  static const uint8_t pinos[3] = {PINO_BOTAO_A, PINO_BOTAO_P, PINO_BOTAO_F};
  static bool anterior[3] = {true, true, true};      // pull-up: solto = HIGH
  static unsigned long ultimaMudanca[3] = {0, 0, 0};

  for (uint8_t i = 0; i < 3; i++) {
    bool agora = digitalRead(pinos[i]);
    if (agora != anterior[i]) {
      // So aceita a mudanca depois de ANTIRRUIDO_MS estavel: o contato
      // mecanico repica e um unico toque viraria varios comandos.
      if (millis() - ultimaMudanca[i] >= ANTIRRUIDO_MS) {
        ultimaMudanca[i] = millis();
        anterior[i] = agora;
        if (!agora) {                                 // apertou
          if (i == 0) avancar();
          else if (i == 1) pausar(true);
          else finalizar();
        }
      }
    } else {
      ultimaMudanca[i] = millis();
    }
  }
}
#endif

void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
#if USAR_BOTOES
  pinMode(PINO_BOTAO_A, INPUT_PULLUP);
  pinMode(PINO_BOTAO_P, INPUT_PULLUP);
  pinMode(PINO_BOTAO_F, INPUT_PULLUP);
#endif
  // Primeiro pulso no MEIO do curso: qualquer outro valor faria o braco
  // atravessar o curso de uma vez, sem aviso, ao ligar.
  aplicar(PULSO_SEGURO);
  Serial.println(F("=== SG90: faixa util e calibracao ==="));
#if USAR_EEPROM
  if (lerEeprom()) {
    fechadoBaixo = fechadoCima = true;
    Serial.println(F("calibracao recuperada da EEPROM"));
  }
#endif
  mostrarAjuda();
#if USAR_BOTOES
  Serial.println(F("Botoes: pino 2 = A, pino 3 = P, pino 4 = F "
                   "(cada um entre o pino e o GND)"));
#endif
  mostrarEstado();
  Serial.println(F("Braco no meio do curso. Mande A (ou aperte o botao) "
                   "para procurar o limite de baixo."));
}

void loop() {
#if USAR_BOTOES
  lerBotoes();
#endif

  // Leitura byte a byte num buffer fixo: sem String, que fragmenta a
  // memoria do AVR em uso prolongado.
  static char linha[24];
  static uint8_t n = 0;
  static unsigned long ultimoByte = 0;

  while (Serial.available()) {
    char caractere = Serial.read();
    ultimoByte = millis();
    if (caractere == '\n' || caractere == '\r') {
      if (n > 0) { linha[n] = '\0'; executar(linha); n = 0; }
    } else if (n < sizeof(linha) - 1) {
      linha[n++] = caractere;
    }
  }

  // Executa tambem sem terminador, depois de uma pausa curta na
  // chegada dos bytes. Nem todo monitor serial acrescenta \n ao enviar:
  // o da IDE depende do seletor "Nova linha", e outros nao tem seletor
  // nenhum. Esperando so pelo \n, o comando digitado ficaria no buffer
  // para sempre e o programa pareceria surdo. Os bytes de um envio
  // chegam em rajada, entao PAUSA_COMANDO_MS de silencio significa que
  // a linha acabou.
  if (n > 0 && (millis() - ultimoByte) >= PAUSA_COMANDO_MS) {
    linha[n] = '\0';
    executar(linha);
    n = 0;
  }

  // O avanco vive aqui, e nao num laco com delay(): assim o P e lido
  // ENTRE um passo e outro. Dentro de um laco, o comando de parada so
  // seria atendido quando o laco terminasse -- ou seja, depois de ja
  // ter passado do batente.
  if (andando && (long)(millis() - proximoPasso) >= 0) {
    if (!darPasso(sentido)) {
      andando = false;
      Serial.println(F("    avanco interrompido pela trava do sketch"));
      return;
    }
    proximoPasso = millis() + intervaloMs;
  }
}
