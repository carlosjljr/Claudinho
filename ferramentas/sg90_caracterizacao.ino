// SG90 - caracterização por intervalos de pulso (µs)
// O menu de comandos aparece ao ligar e a cada comando não reconhecido.
#include <Servo.h>

const int PINO = 9, TRAVA_MIN = 300, TRAVA_MAX = 2700, PASSO = 5;
const byte MAX_PASSADAS = 10;

Servo servo;
int atual = 1500, inicio = 0, fim = 0, tempoMs = 1000;
int limInf = 0, limSup = 0;
bool rodando = false;
unsigned long proximo = 0;

// marcações de 0, 90 e 180 graus; a k-ésima de cada lista é a passada k
int marca[3][MAX_PASSADAS]; byte nMarca[3] = {0, 0, 0};
const int ANG[3] = {0, 90, 180};
float usPorGrau = 0, usZero = 0;

void menu() {
  Serial.println(F("+---------------------------------------------------+"));
  Serial.println(F("|              COMANDOS DE CARACTERIZAÇÃO           |"));
  Serial.println(F("+---------------------------------------------------+"));
  Serial.println(F("| I <início> <fim> <ms>  define o intervalo         |"));
  Serial.println(F("|                        ex.: I 500 300 1000        |"));
  Serial.println(F("|                        (cancela o movimento atual)|"));
  Serial.println(F("| A      avançar                                    |"));
  Serial.println(F("| P      parar                                      |"));
  Serial.println(F("| LI     marcar limite inferior                     |"));
  Serial.println(F("| LS     marcar limite superior                     |"));
  Serial.println(F("| V0     marcar pulso atual como 0 grau             |"));
  Serial.println(F("| V90    marcar pulso atual como 90 graus           |"));
  Serial.println(F("| V180   marcar pulso atual como 180 graus          |"));
  Serial.println(F("+---------------------------------------------------+"));
}

// Ângulo previsto: pela calibração das marcações, se já existe; senão pela
// tabela da biblioteca Servo (544 a 2400 µs = 0 a 180°), só como referência.
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

// Reta µs = usZero + usPorGrau * graus, por mínimos quadrados sobre todas
// as marcações feitas. Precisa de pelo menos dois ângulos diferentes.
void ajustarReta() {
  float sx = 0, sy = 0, sxy = 0, sxx = 0, n = 0;
  for (byte j = 0; j < 3; j++)
    for (byte k = 0; k < nMarca[j]; k++) {
      sx += ANG[j]; sy += marca[j][k];
      sxy += (float)ANG[j] * marca[j][k]; sxx += (float)ANG[j] * ANG[j]; n++;
    }
  float den = n * sxx - sx * sx;
  if (n < 2 || fabs(den) < 1e-6) return;
  usPorGrau = (n * sxy - sx * sy) / den;
  usZero = (sy - usPorGrau * sx) / n;
}

void tabela() {
  Serial.println(F("--- marcações (µs) ---"));
  Serial.println(F("passada;0_grau;90_graus;180_graus"));
  byte linhas = max(nMarca[0], max(nMarca[1], nMarca[2]));
  for (byte k = 0; k < linhas; k++) {
    Serial.print(k + 1);
    for (byte j = 0; j < 3; j++) {
      Serial.print(';');
      if (k < nMarca[j]) Serial.print(marca[j][k]);
    }
    Serial.println();
  }
  if (usPorGrau) {
    Serial.print(F("Reta: µs = ")); Serial.print(usZero, 1);
    Serial.print(F(" + ")); Serial.print(usPorGrau, 4); Serial.println(F(" × graus"));
  }
  if (limInf || limSup) {
    Serial.print(F("Limites: ")); Serial.print(limInf);
    Serial.print(F(" e ")); Serial.print(limSup); Serial.println(F(" µs"));
  }
}

void marcarValor(int angulo) {
  byte j = angulo == 0 ? 0 : angulo == 90 ? 1 : angulo == 180 ? 2 : 3;
  if (j == 3) { Serial.println(F("! Use V0, V90 ou V180.")); return; }
  if (nMarca[j] >= MAX_PASSADAS) { Serial.println(F("! Limite de passadas atingido.")); return; }
  marca[j][nMarca[j]++] = atual;
  Serial.print(F("Passada ")); Serial.print(nMarca[j]); Serial.print(F(": "));
  Serial.print(angulo); Serial.print(F("° = ")); Serial.print(atual); Serial.println(F(" µs"));
  ajustarReta();
  tabela();
}

void executar(char* l) {
  while (*l == ' ') l++;
  for (char* p = l; *p; p++) *p = toupper(*p);

  if (l[0] == 'I') {
    char* arg = l + 1;
    long a = strtol(arg, &arg, 10), b = strtol(arg, &arg, 10), ms = strtol(arg, NULL, 10);
    if (a < TRAVA_MIN || a > TRAVA_MAX || b < TRAVA_MIN || b > TRAVA_MAX || a == b) {
      Serial.print(F("! O intervalo deve ficar entre ")); Serial.print(TRAVA_MIN);
      Serial.print(F(" e ")); Serial.print(TRAVA_MAX); Serial.println(F(" µs."));
      return;
    }
    if (rodando) { rodando = false; Serial.print(F("Movimento cancelado em ")); mostrar(atual); }
    if (ms > 0) tempoMs = ms;
    inicio = a; fim = b;
    irSuave(inicio);
    Serial.print(F("Intervalo de ")); Serial.print(inicio); Serial.print(F(" a "));
    Serial.print(fim); Serial.print(F(" µs, passo de ")); Serial.print(PASSO);
    Serial.print(F(" µs a cada ")); Serial.print(tempoMs); Serial.println(F(" ms. Envie A para avançar."));
  }
  else if (!strcmp(l, "A")) {
    if (!inicio) { Serial.println(F("! Defina antes o intervalo: I <início> <fim> <ms>")); return; }
    rodando = true; proximo = millis();
  }
  else if (!strcmp(l, "P")) {
    rodando = false;
    Serial.print(F("Parado em ")); mostrar(atual);
  }
  else if (!strcmp(l, "LI")) { limInf = atual; Serial.print(F("Limite inferior: ")); mostrar(atual); }
  else if (!strcmp(l, "LS")) { limSup = atual; Serial.print(F("Limite superior: ")); mostrar(atual); }
  else if (l[0] == 'V' && l[1] >= '0' && l[1] <= '9') marcarValor(atoi(l + 1));
  else { Serial.print(F("! Comando não reconhecido: ")); Serial.println(l); menu(); }
}

void setup() {
  Serial.begin(9600);
  servo.attach(PINO, TRAVA_MIN, TRAVA_MAX);
  ir(1500);
  menu();
  Serial.print(F("SG90 no meio do curso: ")); mostrar(atual);
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
    if (atual == fim) {
      rodando = false; inicio = fim = 0;
      Serial.print(F("Fim do intervalo em ")); mostrar(atual);
      Serial.println(F("Envie I <início> <fim> <ms> para um novo intervalo."));
      return;
    }
    int sentido = fim > atual ? 1 : -1;
    ir(abs(fim - atual) < PASSO ? fim : atual + sentido * PASSO);
    mostrar(atual);
    proximo = millis() + tempoMs;
  }
}
