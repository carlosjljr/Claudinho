// =====================================================================
// ENSAIO 1 - VARREDURA DE 0 A 180 GRAUS  (revisao do Apendice A)
// =====================================================================
// Um atuador fica parado em 90 graus e o outro percorre 0..180 em
// passos de PASSO_GRAUS, com PERIODO_MS entre eles.
//
// O QUE MUDOU EM RELACAO A VERSAO DO APENDICE, E POR QUE
//
// 1. write(graus) virou writeMicroseconds(grausParaUs(graus)).
//    write() usa a tabela da biblioteca: 0..180 graus -> 544..2400 us.
//    Essa faixa e uma convencao da biblioteca, nao do SG90. Se o servo
//    real precisa de outra faixa, cada grau comandado vira um numero
//    diferente de graus no braco -- e isso aparece nos resultados como
//    "o servo entrega 92% do comandado". Com as constantes medidas na
//    caracterizacao, o grau comandado passa a ser grau de verdade.
//
// 2. Cada linha da serial leva millis(), e tres piscadas do LED marcam
//    o inicio. Sem isso o video e a serial so podem ser casados no
//    olho, e o instante de cada degrau fica incerto em algumas dezenas
//    de milissegundos -- que e a ordem do proprio tempo de assentamento
//    que se quer medir.
//
// 3. O ensaio roda em N_REPETICOES repeticoes seguidas, numeradas na
//    serial, em vez de uma so por compilacao.
//
// 4. O detach() do final espera o braco assentar. Soltando na hora, o
//    peso proprio derruba o braco ainda dentro do video, e o ultimo
//    degrau sai contaminado.
//
// ATENCAO A ALIMENTACAO: dois SG90 passam de 1,4 A no arranque. Pelo
// 5 V da placa a tensao cai, o servo perde passo e o Arduino chega a
// reiniciar no meio do ensaio. Fonte externa de 5 V, GND comum.
// =====================================================================
#include <Servo.h>

const int PINO_SERVO_1 = 9;
const int PINO_SERVO_2 = 10;
const uint8_t PINO_LED = LED_BUILTIN;

// ---- O que este ensaio faz ------------------------------------------
const int PASSO_GRAUS = 10;      // tomadas: 2, 5 e 10
const int ANGULO_FIXO = 90;      // onde o outro atuador fica parado
const bool MOVER_SERVO_2 = true; // false inverte os papeis
const int PERIODO_MS = 1000;     // intervalo entre degraus
const uint8_t N_REPETICOES = 3;

// ---- Calibracao medida (saida do sg90_caracterizacao.ino) -----------
// Enquanto estiver com os valores da biblioteca, o ensaio reproduz o
// comportamento antigo -- inclusive o erro de ganho.
const float US_POR_GRAU_1 = (2400.0 - 544.0) / 180.0;
const float US_ZERO_1 = 544.0;
const float US_POR_GRAU_2 = (2400.0 - 544.0) / 180.0;
const float US_ZERO_2 = 544.0;

// Faixa aceita pelo attach. ISTO IMPORTA: writeMicroseconds e LIMITADO
// aos extremos passados no attach, e attach(pino) sozinho usa os 544 e
// 2400 da biblioteca. Se a calibracao medida pedir 500 ou 2500 us, o
// comando seria cortado em silencio e o ensaio inteiro sairia com os
// extremos errados, sem nenhum aviso.
const int US_MIN_ATTACH = 500;
const int US_MAX_ATTACH = 2500;

Servo servo1, servo2;

int grausParaUs(int graus, float usPorGrau, float usZero) {
  return (int)(usZero + usPorGrau * graus + 0.5);
}

void posicionar(int graus1, int graus2) {
  servo1.writeMicroseconds(grausParaUs(graus1, US_POR_GRAU_1, US_ZERO_1));
  servo2.writeMicroseconds(grausParaUs(graus2, US_POR_GRAU_2, US_ZERO_2));
}

void piscarSincronismo() {
  for (uint8_t i = 0; i < 3; i++) {
    digitalWrite(PINO_LED, HIGH); delay(120);
    digitalWrite(PINO_LED, LOW);  delay(120);
  }
}

void registrar(uint8_t repeticao, int degrau, int graus1, int graus2) {
  Serial.print(millis());   Serial.print(';');
  Serial.print(repeticao);  Serial.print(';');
  Serial.print(degrau);     Serial.print(';');
  Serial.print(graus1);     Serial.print(';');
  Serial.println(graus2);
}

void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
  servo1.attach(PINO_SERVO_1, US_MIN_ATTACH, US_MAX_ATTACH);
  servo2.attach(PINO_SERVO_2, US_MIN_ATTACH, US_MAX_ATTACH);

  Serial.println(F("# Ensaio 1 - varredura 0..180"));
  Serial.print(F("# passo="));        Serial.print(PASSO_GRAUS);
  Serial.print(F(" graus; periodo=")); Serial.print(PERIODO_MS);
  Serial.print(F(" ms; movendo o servo "));
  Serial.println(MOVER_SERVO_2 ? 2 : 1);
  Serial.println(F("# ms;repeticao;degrau;servo1_graus;servo2_graus"));

  for (uint8_t repeticao = 1; repeticao <= N_REPETICOES; repeticao++) {
    // Parte sempre do mesmo lugar: comecar de onde a repeticao anterior
    // terminou carrega o transitorio dela para o primeiro degrau.
    posicionar(MOVER_SERVO_2 ? ANGULO_FIXO : 0,
               MOVER_SERVO_2 ? 0 : ANGULO_FIXO);
    delay(2 * PERIODO_MS);
    piscarSincronismo();

    int degrau = 0;
    for (int angulo = 0; angulo <= 180; angulo += PASSO_GRAUS) {
      if (MOVER_SERVO_2) posicionar(ANGULO_FIXO, angulo);
      else               posicionar(angulo, ANGULO_FIXO);
      registrar(repeticao, ++degrau,
                MOVER_SERVO_2 ? ANGULO_FIXO : angulo,
                MOVER_SERVO_2 ? angulo : ANGULO_FIXO);
      delay(PERIODO_MS);
    }
    Serial.print(F("# fim da repeticao ")); Serial.println(repeticao);
  }

  delay(2 * PERIODO_MS);     // deixa assentar antes de soltar
  servo1.detach();
  servo2.detach();
  Serial.println(F("# concluido"));
}

void loop() {
}
