// =====================================================================
// ENSAIO 2 - 25 COMBINACOES ANGULARES  (revisao do Apendice B)
// =====================================================================
// Todas as combinacoes de 0, 45, 90, 135 e 180 graus nos dois
// atuadores. Mesmas correcoes do Ensaio 1 -- comando em
// microssegundos, millis() na serial, piscada de sincronismo,
// repeticoes numeradas -- mais duas proprias deste ensaio:
//
// 1. Entre o ultimo ponto de uma linha (180 graus) e o primeiro da
//    seguinte (0 graus), o atuador 2 da um salto de 180 graus de uma
//    vez. Um unico periodo nao basta para esse percurso, e a leitura
//    do primeiro ponto da linha sai com o braco ainda chegando. Aqui
//    o retorno ganha tempo proprio (PERIODO_RETORNO_MS) e nao e
//    registrado como ponto de medicao.
//
// 2. Os dois atuadores recebem o comando no mesmo instante, entao os
//    dois se movem juntos e o braco passeia por posicoes
//    intermediarias que nao sao nenhuma das 25. Para a medicao em
//    regime isso e inofensivo, mas quem filma vai ver o caminho; fica
//    registrado o porque.
// =====================================================================
#include <Servo.h>

const int PINO_SERVO_1 = 9;
const int PINO_SERVO_2 = 10;
const uint8_t PINO_LED = LED_BUILTIN;

const int ALVOS[] = {0, 45, 90, 135, 180};
const uint8_t N_ALVOS = sizeof(ALVOS) / sizeof(ALVOS[0]);
const int PERIODO_MS = 1000;
const int PERIODO_RETORNO_MS = 2000;
const uint8_t N_REPETICOES = 3;

// ---- Calibracao medida (saida do sg90_caracterizacao.ino) -----------
// SG90 n.6, ensaio 3: 0/90/180 graus visuais em 3 passadas subindo.
// Residuo RMS 0,56 grau. Troque pelos valores de cada servo medido.
const float US_POR_GRAU_1 = 11.2130;
const float US_ZERO_1 = 433.6;
const float US_POR_GRAU_2 = 11.2130;
const float US_ZERO_2 = 433.6;

// Faixa aceita pelo attach. ISTO IMPORTA: writeMicroseconds e LIMITADO
// aos extremos passados no attach, e attach(pino) sozinho usa os 544 e
// 2400 da biblioteca. Se a calibracao medida pedir 500 ou 2500 us, o
// comando seria cortado em silencio e o ensaio inteiro sairia com os
// extremos errados, sem nenhum aviso.
const int US_MIN_ATTACH = 400;   // o 0 grau calibrado fica em 434 us
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

void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
  servo1.attach(PINO_SERVO_1, US_MIN_ATTACH, US_MAX_ATTACH);
  servo2.attach(PINO_SERVO_2, US_MIN_ATTACH, US_MAX_ATTACH);

  Serial.println(F("# Ensaio 2 - 25 combinacoes"));
  Serial.println(F("# ms;repeticao;ponto;servo1_graus;servo2_graus"));

  for (uint8_t repeticao = 1; repeticao <= N_REPETICOES; repeticao++) {
    posicionar(ALVOS[0], ALVOS[0]);
    delay(PERIODO_RETORNO_MS);
    piscarSincronismo();

    uint8_t ponto = 0;
    for (uint8_t i = 0; i < N_ALVOS; i++) {
      for (uint8_t j = 0; j < N_ALVOS; j++) {
        posicionar(ALVOS[i], ALVOS[j]);
        Serial.print(millis());   Serial.print(';');
        Serial.print(repeticao);  Serial.print(';');
        Serial.print(++ponto);    Serial.print(';');
        Serial.print(ALVOS[i]);   Serial.print(';');
        Serial.println(ALVOS[j]);
        delay(PERIODO_MS);
      }
      // Volta do atuador 2 de 180 para 0: percurso longo, tempo proprio
      // e sem registro, para nao entrar como ponto medido.
      if (i + 1 < N_ALVOS) {
        posicionar(ALVOS[i], ALVOS[0]);
        delay(PERIODO_RETORNO_MS);
      }
    }
    Serial.print(F("# fim da repeticao ")); Serial.println(repeticao);
  }

  delay(PERIODO_RETORNO_MS);
  servo1.detach();
  servo2.detach();
  Serial.println(F("# concluido"));
}

void loop() {
}
