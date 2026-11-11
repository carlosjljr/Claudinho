// SG90 - caracterizacao por intervalos de pulso (us)
// Comandos (Monitor Serial 9600):
//   I <ini> <fim>  define o intervalo (ex.: I 500 300)
//   A              inicia / retoma      P  pausa      F  encerra o intervalo
//   K              marca o pulso atual como limite
//   U <us>         vai direto a um pulso
//   D <us>         passo (padrao 5)     T <ms>  tempo por passo (padrao 300)
//   M <graus>      registra pulso atual = angulo medido
//   R              ajusta a reta        G <graus>  vai ao angulo calibrado
//   H              resumo               S  solta o servo
#include <Servo.h>

const int PINO = 9, TRAVA_MIN = 300, TRAVA_MAX = 2700;

Servo servo;
int atual = 1500, ini = 0, fim = 0, passo = 5, tempoMs = 300;
int limMin = 0, limMax = 0;
bool rodando = false;
unsigned long proximo = 0;

int parUs[12]; float parGrau[12]; byte nPares = 0;
float usPorGrau = 0, usZero = 0;

void ir(int us) {
  atual = constrain(us, TRAVA_MIN, TRAVA_MAX);
  servo.writeMicroseconds(atual);
}

// Rampa: evita que o braco atravesse o curso de uma vez.
void irSuave(int us) {
  us = constrain(us, TRAVA_MIN, TRAVA_MAX);
  while (abs(us - atual) > 20) { ir(atual + (us > atual ? 20 : -20)); delay(20); }
  ir(us);
}

void pergunta() {
  Serial.println(F("Mais? I <ini> <fim> para novo intervalo, ou K para marcar o limite."));
}

void encerrar(const __FlashStringHelper* motivo) {
  rodando = false;
  ini = fim = 0;
  Serial.print(motivo); Serial.print(F(" em ")); Serial.print(atual); Serial.println(F(" us"));
  pergunta();
}

void marcar() {
  if (atual < 1500) limMin = atual; else limMax = atual;
  Serial.print(F("Limite ")); Serial.print(atual < 1500 ? F("inferior") : F("superior"));
  Serial.print(F(" = ")); Serial.print(atual); Serial.println(F(" us"));
}

void ajustar() {
  if (nPares < 2) { Serial.println(F("! minimo 2 pontos (M)")); return; }
  float sx = 0, sy = 0, sxy = 0, sxx = 0, n = nPares;
  for (byte i = 0; i < nPares; i++) {
    sx += parGrau[i]; sy += parUs[i];
    sxy += parGrau[i] * parUs[i]; sxx += parGrau[i] * parGrau[i];
  }
  float den = n * sxx - sx * sx;
  if (fabs(den) < 1e-6) { Serial.println(F("! angulos iguais")); return; }
  usPorGrau = (n * sxy - sx * sy) / den;
  usZero = (sy - usPorGrau * sx) / n;
  Serial.print(F("us = ")); Serial.print(usZero, 1);
  Serial.print(F(" + ")); Serial.print(usPorGrau, 4); Serial.println(F(" * graus"));
}

void resumo() {
  Serial.println(F("--- resumo ---"));
  Serial.print(F("limites_us;")); Serial.print(limMin); Serial.print(';'); Serial.println(limMax);
  Serial.print(F("us_zero;us_por_grau;")); Serial.print(usZero, 1); Serial.print(';'); Serial.println(usPorGrau, 4);
  for (byte i = 0; i < nPares; i++) {
    Serial.print(parUs[i]); Serial.print(';'); Serial.println(parGrau[i], 1);
  }
}

void executar(char* l) {
  char c = toupper(l[0]);
  char* arg = l + 1;
  long a = strtol(arg, &arg, 10), b = strtol(arg, NULL, 10);

  switch (c) {
    case 'I':
      if (a < TRAVA_MIN || a > TRAVA_MAX || b < TRAVA_MIN || b > TRAVA_MAX || a == b) {
        Serial.print(F("! intervalo entre ")); Serial.print(TRAVA_MIN);
        Serial.print(F(" e ")); Serial.println(TRAVA_MAX);
        break;
      }
      ini = a; fim = b; rodando = false;
      irSuave(ini);
      Serial.print(F("Intervalo ")); Serial.print(ini); Serial.print(F(" -> "));
      Serial.print(fim); Serial.println(F(" us. A inicia."));
      break;
    case 'A':
      if (!ini) { Serial.println(F("! defina antes: I <ini> <fim>")); break; }
      rodando = true; proximo = millis();
      break;
    case 'P':
      rodando = false;
      Serial.print(F("Pausado em ")); Serial.print(atual); Serial.println(F(" us. A retoma, F encerra."));
      break;
    case 'F': encerrar(F("Encerrado")); break;
    case 'K': marcar(); break;
    case 'U': rodando = false; irSuave(a); Serial.print(atual); Serial.println(F(" us")); break;
    case 'D': if (a > 0) passo = a; Serial.print(F("passo = ")); Serial.println(passo); break;
    case 'T': if (a > 0) tempoMs = a; Serial.print(F("tempo = ")); Serial.println(tempoMs); break;
    case 'M':
      if (nPares < 12) {
        parUs[nPares] = atual; parGrau[nPares++] = atof(l + 1);
        Serial.print(F("ponto ")); Serial.println(nPares);
      }
      break;
    case 'R': ajustar(); break;
    case 'G':
      if (!usPorGrau) { Serial.println(F("! calibre antes (M e R)")); break; }
      irSuave(round(usZero + usPorGrau * atof(l + 1)));
      Serial.print(atual); Serial.println(F(" us"));
      break;
    case 'H': resumo(); break;
    case 'S': rodando = false; servo.detach(); Serial.println(F("solto")); break;
  }
}

void setup() {
  Serial.begin(9600);
  servo.attach(PINO, TRAVA_MIN, TRAVA_MAX);
  ir(1500);
  Serial.println(F("SG90 no meio (1500 us). Defina: I <ini> <fim>"));
}

void loop() {
  static char l[24]; static byte n = 0; static unsigned long ultimo = 0;
  while (Serial.available()) {
    char ch = Serial.read(); ultimo = millis();
    if (ch == '\n' || ch == '\r') { if (n) { l[n] = 0; executar(l); n = 0; } }
    else if (n < 23) l[n++] = ch;
  }
  if (n && millis() - ultimo > 80) { l[n] = 0; executar(l); n = 0; }  // sem terminador

  if (rodando && (long)(millis() - proximo) >= 0) {
    if (atual == fim) { encerrar(F("Fim do intervalo")); return; }
    int dir = fim > atual ? 1 : -1;
    ir(abs(fim - atual) < passo ? fim : atual + dir * passo);
    Serial.println(atual);
    proximo = millis() + tempoMs;
  }
}
