// SG90 - caracterização por intervalos de pulso (µs)
// Comandos (Monitor Serial 9600):
//   I <início> <fim> [ms]  define o intervalo e, opcional, o tempo por passo
//                          ex.: I 500 300 1000  (de 500 a 300 µs, 1 s por passo)
//   A  avançar      P  pausar      F  finalizar o intervalo
//   L  marcar o pulso atual como limite
//   V <µs>     vai direto a um pulso
//   D <µs>     tamanho do passo (padrão 5)
//   T <ms>     tempo por passo (padrão 1000)
//   M <graus>  medição: pulso atual = ângulo medido
//   R          ajusta a reta de calibração
//   G <graus>  gira até o ângulo calibrado
//   S          sumário       X  soltar o servo
#include <Servo.h>

const int PINO = 9, TRAVA_MIN = 300, TRAVA_MAX = 2700;

Servo servo;
int atual = 1500, inicio = 0, fim = 0, passo = 5, tempoMs = 1000;
int limMin = 0, limMax = 0;
bool rodando = false;
unsigned long proximo = 0;

int parUs[12]; float parGrau[12]; byte nPares = 0;
float usPorGrau = 0, usZero = 0;

// Ângulo previsto: pela calibração, se já existe; senão pela tabela da
// biblioteca Servo (544 a 2400 µs = 0 a 180°), só como referência.
float anguloPrevisto(int us) {
  if (usPorGrau) return (us - usZero) / usPorGrau;
  return (us - 544.0) * 180.0 / (2400.0 - 544.0);
}

void mostrar(int us) {
  Serial.print(us); Serial.print(F(" µs  ->  "));
  Serial.print(anguloPrevisto(us), 1);
  Serial.println(usPorGrau ? F("° (calibrado)") : F("° (estimativa da biblioteca)"));
}

void ir(int us) {
  atual = constrain(us, TRAVA_MIN, TRAVA_MAX);
  servo.writeMicroseconds(atual);
}

// Rampa: evita que o braço atravesse o curso de uma vez.
void irSuave(int us) {
  us = constrain(us, TRAVA_MIN, TRAVA_MAX);
  while (abs(us - atual) > 20) { ir(atual + (us > atual ? 20 : -20)); delay(20); }
  ir(us);
}

void finalizar(const __FlashStringHelper* motivo) {
  rodando = false;
  inicio = fim = 0;
  Serial.print(motivo); Serial.print(F(" em ")); mostrar(atual);
  Serial.println(F("Continuar? Envie I <início> <fim> para um novo intervalo, ou L para marcar o limite."));
}

void marcarLimite() {
  if (atual < 1500) limMin = atual; else limMax = atual;
  Serial.print(atual < 1500 ? F("Limite inferior: ") : F("Limite superior: "));
  mostrar(atual);
}

void ajustarReta() {
  if (nPares < 2) { Serial.println(F("! São necessárias ao menos 2 medições (M).")); return; }
  float sx = 0, sy = 0, sxy = 0, sxx = 0, n = nPares;
  for (byte i = 0; i < nPares; i++) {
    sx += parGrau[i]; sy += parUs[i];
    sxy += parGrau[i] * parUs[i]; sxx += parGrau[i] * parGrau[i];
  }
  float den = n * sxx - sx * sx;
  if (fabs(den) < 1e-6) { Serial.println(F("! Meça em ângulos diferentes.")); return; }
  usPorGrau = (n * sxy - sx * sy) / den;
  usZero = (sy - usPorGrau * sx) / n;
  Serial.print(F("Reta: µs = ")); Serial.print(usZero, 1);
  Serial.print(F(" + ")); Serial.print(usPorGrau, 4); Serial.println(F(" × graus"));
}

void sumario() {
  Serial.println(F("--- sumário ---"));
  Serial.print(F("limites_us;")); Serial.print(limMin); Serial.print(';'); Serial.println(limMax);
  Serial.print(F("us_zero;us_por_grau;")); Serial.print(usZero, 1); Serial.print(';'); Serial.println(usPorGrau, 4);
  Serial.println(F("pulso_us;angulo_graus"));
  for (byte i = 0; i < nPares; i++) {
    Serial.print(parUs[i]); Serial.print(';'); Serial.println(parGrau[i], 1);
  }
}

void executar(char* l) {
  char c = toupper(l[0]);
  char* arg = l + 1;
  long a = strtol(arg, &arg, 10), b = strtol(arg, &arg, 10), ms = strtol(arg, NULL, 10);

  switch (c) {
    case 'I':
      if (a < TRAVA_MIN || a > TRAVA_MAX || b < TRAVA_MIN || b > TRAVA_MAX || a == b) {
        Serial.print(F("! O intervalo deve ficar entre ")); Serial.print(TRAVA_MIN);
        Serial.print(F(" e ")); Serial.print(TRAVA_MAX); Serial.println(F(" µs."));
        break;
      }
      if (ms > 0) tempoMs = ms;
      inicio = a; fim = b; rodando = false;
      irSuave(inicio);
      Serial.print(F("Intervalo de ")); Serial.print(inicio); Serial.print(F(" a "));
      Serial.print(fim); Serial.print(F(" µs, passo de ")); Serial.print(passo);
      Serial.print(F(" µs a cada ")); Serial.print(tempoMs); Serial.println(F(" ms. Envie A para avançar."));
      break;
    case 'A':
      if (!inicio) { Serial.println(F("! Defina antes o intervalo: I <início> <fim>")); break; }
      rodando = true; proximo = millis();
      break;
    case 'P':
      rodando = false;
      Serial.print(F("Pausado em ")); mostrar(atual);
      Serial.println(F("A retoma, F finaliza."));
      break;
    case 'F': finalizar(F("Finalizado")); break;
    case 'L': marcarLimite(); break;
    case 'V': rodando = false; irSuave(a); mostrar(atual); break;
    case 'D': if (a > 0) passo = a; Serial.print(F("Passo: ")); Serial.print(passo); Serial.println(F(" µs")); break;
    case 'T': if (a > 0) tempoMs = a; Serial.print(F("Tempo por passo: ")); Serial.print(tempoMs); Serial.println(F(" ms")); break;
    case 'M':
      if (nPares < 12) {
        parUs[nPares] = atual; parGrau[nPares++] = atof(l + 1);
        Serial.print(F("Medição ")); Serial.print(nPares); Serial.print(F(": "));
        Serial.print(atual); Serial.print(F(" µs = ")); Serial.print(parGrau[nPares - 1], 1); Serial.println(F("°"));
      }
      break;
    case 'R': ajustarReta(); break;
    case 'G':
      if (!usPorGrau) { Serial.println(F("! Calibre antes (M e R).")); break; }
      rodando = false;
      irSuave(round(usZero + usPorGrau * atof(l + 1)));
      mostrar(atual);
      break;
    case 'S': sumario(); break;
    case 'X': rodando = false; servo.detach(); Serial.println(F("Servo solto.")); break;
  }
}

void setup() {
  Serial.begin(9600);
  servo.attach(PINO, TRAVA_MIN, TRAVA_MAX);
  ir(1500);
  Serial.print(F("SG90 no meio do curso: ")); mostrar(atual);
  Serial.println(F("Defina o intervalo: I <início> <fim> [ms]"));
}

void loop() {
  static char l[24]; static byte n = 0; static unsigned long ultimo = 0;
  while (Serial.available()) {
    char ch = Serial.read(); ultimo = millis();
    if (ch == '\n' || ch == '\r') { if (n) { l[n] = 0; executar(l); n = 0; } }
    else if (n < 23) l[n++] = ch;
  }
  if (n && millis() - ultimo > 80) { l[n] = 0; executar(l); n = 0; }  // sem terminador de linha

  if (rodando && (long)(millis() - proximo) >= 0) {
    if (atual == fim) { finalizar(F("Fim do intervalo")); return; }
    int sentido = fim > atual ? 1 : -1;
    ir(abs(fim - atual) < passo ? fim : atual + sentido * passo);
    mostrar(atual);
    proximo = millis() + tempoMs;
  }
}
