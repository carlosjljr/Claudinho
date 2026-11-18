#include "Arduino.h"
#include "Servo.h"
SerialClass Serial;
unsigned long RELOGIO = 0;
int PULSO_APLICADO = 0;
#include "sketch.cpp"
static void rodar(unsigned long ms){ for(unsigned long t=0;t<ms;t+=50){RELOGIO+=50;loop();} }
static void cmd(const char* s){ printf(">> %s\n", s); Serial.manda(s); rodar(200); }
int main(){
  setup();
  cmd("I 450 400 200"); cmd("A"); rodar(500); cmd("-"); rodar(600); cmd("+"); cmd("+"); cmd("LI"); cmd("A"); rodar(300);
}
