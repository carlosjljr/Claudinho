// =====================================================================
// CARACTERIZACAO DO SG90 - varredura por largura de pulso
// =====================================================================
// Liga o servo e varre a faixa inteira em micropassos, parando em cada
// largura o tempo necessario para o braco assentar. A cada parada envia
// uma linha CSV pela serial; basta filmar o braco e casar as linhas com
// o video pelo piscar do LED, que marca o inicio da varredura.
//
// POR QUE LARGURA DE PULSO, E NAO Servo.write(graus)
// A biblioteca Servo converte 0..180 graus para 544..2400 us por
// padrao. Essa faixa e uma convencao da biblioteca, nao do SG90: o
// servo real tem a sua, e a diferenca entre as duas aparece como ganho
// (o braco entrega menos grau do que foi pedido) e como offset. Medindo
// a largura de pulso diretamente, a conversao graus->us passa a ser
// medida, nao suposta.
//
// LIGACAO
//   sinal   -> pino 9 (qualquer PWM serve)
//   VCC     -> fonte externa de 5 V (NAO o 5 V do Arduino: o SG90 puxa
//              de 150 mA parado a mais de 700 mA no arranque e derruba
//              a placa)
//   GND     -> GND da fonte E GND do Arduino, no mesmo ponto
//
// COMANDOS PELA SERIAL (9600 bps, "Nova linha" ao final)
//   V            varre de MIN a MAX e volta
//   P <us>       vai para uma largura de pulso e fica
//   G <graus>    vai para um angulo usando a calibracao abaixo
//   F <min> <max>  muda a faixa varrida
//   D <us>       muda o micropasso (padrao 5 us)
//   T <ms>       muda a espera em cada parada (padrao 400 ms)
//   L            solta o servo (detach): para de segurar e de aquecer
//   ?            mostra a configuracao atual
// =====================================================================
#include <Servo.h>

const uint8_t PINO_SERVO = 9;
const uint8_t PINO_LED = LED_BUILTIN;

// Faixa varrida. Comece conservador: amplie so depois de ver, no
// proprio ensaio, que o braco ainda se move e NAO esta zunindo. Zumbido
// parado = servo empurrando contra o batente mecanico, consumindo
// corrente e esquentando sem sair do lugar.
int larguraMin = 600;      // us
int larguraMax = 2400;     // us
int micropasso = 5;        // us entre paradas
int esperaMs = 400;        // tempo parado em cada largura

// Calibracao medida (preencha com a saida do sg90_calibracao.py).
// Enquanto nao houver medicao, estes valores sao so o padrao da
// biblioteca -- o mesmo que gerou o erro de ganho.
float usPorGrau = (2400.0 - 544.0) / 180.0;
float usEmZeroGrau = 544.0;

Servo servo;
int larguraAtual = 1500;

void aplicar(int largura) {
  largura = constrain(largura, larguraMin, larguraMax);
  if (!servo.attached()) servo.attach(PINO_SERVO, larguraMin, larguraMax);
  servo.writeMicroseconds(largura);
  larguraAtual = largura;
}

void cabecalho() {
  Serial.println(F("# ms;largura_us;sentido;grau_nominal"));
}

void registrar(const char* sentido) {
  // grau_nominal e so a leitura da calibracao ATUAL, para conferencia.
  // O angulo de verdade vem da medicao em video, fora daqui.
  float grau = (larguraAtual - usEmZeroGrau) / usPorGrau;
  Serial.print(millis());      Serial.print(';');
  Serial.print(larguraAtual);  Serial.print(';');
  Serial.print(sentido);       Serial.print(';');
  Serial.println(grau, 2);
}

void piscarSincronismo() {
  // Marca visivel no video: tres piscadas curtas antes de comecar.
  for (uint8_t i = 0; i < 3; i++) {
    digitalWrite(PINO_LED, HIGH); delay(120);
    digitalWrite(PINO_LED, LOW);  delay(120);
  }
}

void varrer() {
  Serial.println(F("# inicio da varredura"));
  cabecalho();

  // Sai da faixa pelo lado de baixo e espera: a primeira parada precisa
  // comecar de um repouso conhecido, senao ela carrega o transitorio da
  // posicao anterior.
  aplicar(larguraMin);
  delay(1000);
  piscarSincronismo();

  for (int us = larguraMin; us <= larguraMax; us += micropasso) {
    aplicar(us);
    delay(esperaMs);
    registrar("sobe");
  }
  // A volta mede a HISTERESE: o SG90 nao para na mesma posicao quando
  // chega por cima ou por baixo, por causa da folga da engrenagem. Sem
  // a volta, essa folga some dentro do erro e nao da para separar.
  for (int us = larguraMax; us >= larguraMin; us -= micropasso) {
    aplicar(us);
    delay(esperaMs);
    registrar("desce");
  }

  Serial.println(F("# fim da varredura"));
}

void mostrarConfig() {
  Serial.print(F("# faixa=")); Serial.print(larguraMin);
  Serial.print(F(".."));       Serial.print(larguraMax);
  Serial.print(F(" us; micropasso=")); Serial.print(micropasso);
  Serial.print(F(" us; espera="));     Serial.print(esperaMs);
  Serial.print(F(" ms; paradas="));
  Serial.println(2 * ((larguraMax - larguraMin) / micropasso + 1));
  Serial.print(F("# calibracao: us = "));
  Serial.print(usEmZeroGrau, 1); Serial.print(F(" + "));
  Serial.print(usPorGrau, 4);    Serial.println(F(" * graus"));
}

long lerNumero(String& texto) {
  texto.trim();
  int espaco = texto.indexOf(' ');
  String parte = (espaco < 0) ? texto : texto.substring(0, espaco);
  texto = (espaco < 0) ? "" : texto.substring(espaco + 1);
  return parte.toInt();
}

void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
  aplicar(1500);
  Serial.println(F("# SG90 - caracterizacao por largura de pulso"));
  Serial.println(F("# comandos: V  P <us>  G <graus>  F <min> <max>  "
                   "D <us>  T <ms>  L  ?"));
  mostrarConfig();
}

void loop() {
  if (!Serial.available()) return;

  String linha = Serial.readStringUntil('\n');
  linha.trim();
  if (linha.length() == 0) return;

  char comando = toupper(linha.charAt(0));
  String resto = linha.substring(1);

  switch (comando) {
    case 'V':
      varrer();
      break;
    case 'P': {
      int us = lerNumero(resto);
      aplicar(us);
      Serial.print(F("# largura = ")); Serial.println(larguraAtual);
      break;
    }
    case 'G': {
      long graus = lerNumero(resto);
      aplicar((int)round(usEmZeroGrau + usPorGrau * graus));
      Serial.print(F("# "));      Serial.print(graus);
      Serial.print(F(" graus -> ")); Serial.print(larguraAtual);
      Serial.println(F(" us"));
      break;
    }
    case 'F': {
      int novoMin = lerNumero(resto);
      int novoMax = lerNumero(resto);
      if (novoMin > 0 && novoMax > novoMin) {
        larguraMin = novoMin;
        larguraMax = novoMax;
        servo.detach();          // reatacha com a faixa nova
        aplicar(larguraAtual);
      }
      mostrarConfig();
      break;
    }
    case 'D': {
      int passo = lerNumero(resto);
      if (passo > 0) micropasso = passo;
      mostrarConfig();
      break;
    }
    case 'T': {
      int espera = lerNumero(resto);
      if (espera > 0) esperaMs = espera;
      mostrarConfig();
      break;
    }
    case 'L':
      servo.detach();
      Serial.println(F("# servo solto"));
      break;
    default:
      mostrarConfig();
      break;
  }
}
