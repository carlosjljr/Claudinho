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
  cmd("A");
  cmd("I 500 485 1000"); cmd("A"); rodar(1100); cmd("P"); rodar(3000); cmd("A"); rodar(4000);
  cmd("L");
  cmd("V 1000"); cmd("M 45"); cmd("V 2000"); cmd("M 135"); cmd("R");
  cmd("I 1500 1510 500"); cmd("A"); rodar(1500);
  cmd("G 90"); cmd("S");
}
