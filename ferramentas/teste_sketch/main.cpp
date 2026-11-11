#include "Arduino.h"
#include "Servo.h"
#include "EEPROM.h"
SerialClass Serial;
EEPROMClass EEPROM;
unsigned long RELOGIO = 0;
int PULSO_APLICADO = 0;
#include "sketch.cpp"

static void rodar(unsigned long ms){           // deixa o loop correr
  for (unsigned long t = 0; t < ms; t += 50) { RELOGIO += 50; loop(); }
}
int main(){
  setup();
  printf("\n########## A: comeca a descer ##########\n");
  Serial.manda("A"); loop(); rodar(5000);
  printf("\n########## P: pausa ##########\n");
  Serial.manda("P"); loop(); rodar(3000);   // nao pode andar mais
  printf("\n########## - e +: ajuste fino ##########\n");
  Serial.manda("-"); loop(); Serial.manda("+"); loop();
  printf("\n########## A: retoma ##########\n");
  Serial.manda("A"); loop(); rodar(3000);
  printf("\n########## F: fecha o lado de baixo ##########\n");
  Serial.manda("F"); loop();
  printf("\n########## A + F: o outro lado ##########\n");
  Serial.manda("A"); loop(); rodar(4000);
  Serial.manda("F"); loop();
  printf("\n########## estado final ##########\n");
  Serial.manda("?"); loop();
  printf("\n########## F extra ##########\n");
  Serial.manda("F"); loop();
  printf("\n########## calibracao: 2 pontos e R ##########\n");
  Serial.manda("U 1000"); loop(); Serial.manda("M 10"); loop();
  Serial.manda("U 2000"); loop(); Serial.manda("M 170"); loop();
  Serial.manda("R"); loop();
  Serial.manda("G 90"); loop();
  printf("\npulso realmente aplicado no servo: %d us\n", PULSO_APLICADO);
  return 0;
}
