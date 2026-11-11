#include "Arduino.h"
#include "Servo.h"
SerialClass Serial;
unsigned long RELOGIO = 0;
int PULSO_APLICADO = 0;
#include "sketch.cpp"
static void rodar(unsigned long ms){ for(unsigned long t=0;t<ms;t+=50){RELOGIO+=50;loop();} }
static void cmd(const char* s){ Serial.manda(s); rodar(200); }
int main(){
  setup();
  cmd("A");                      // sem intervalo: deve recusar
  cmd("I 500 480"); cmd("A"); rodar(2000);     // termina sozinho e pergunta
  cmd("I 2000 2100"); cmd("A"); rodar(700); cmd("P"); rodar(1500); cmd("A"); rodar(500); cmd("K"); cmd("F");
  cmd("U 1000"); cmd("M 45"); cmd("U 2000"); cmd("M 135"); cmd("R"); cmd("G 90");
  cmd("H");
  printf("pulso aplicado: %d\n", PULSO_APLICADO);
}
