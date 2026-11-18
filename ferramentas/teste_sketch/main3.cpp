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
  cmd("A");
  cmd("I 450 430 200"); cmd("A"); rodar(500);
  cmd("I 1440 1450 200");          // cancela o movimento sem F
  cmd("V0");                        // marca 1440 como 0 (teste)
  cmd("li"); cmd("x");
  cmd("V90"); cmd("V180"); cmd("V0"); cmd("V45");
}
