// =====================================================================
// CARACTERIZACAO DO SG90 - tudo dentro do Arduino IDE
// =====================================================================
// Acha a faixa util do servo, calibra graus -> microssegundos e passa a
// posicionar pela calibracao medida. Nao precisa de Python.
//
// POR QUE NAO Servo.write(graus)
// A biblioteca Servo converte 0..180 graus para 544..2400 us. Essa
// faixa e uma convencao da biblioteca, NAO do SG90. Como cada servo tem
// a sua, a diferenca aparece como erro de ganho: o braco entrega menos
// grau do que foi pedido. Aqui tudo e comandado em microssegundos e a
// conversao graus->us e MEDIDA.
//
// O SKETCH NAO ENXERGA O BRACO
// Malha aberta: nao ha realimentacao. Ele nao sabe se o braco andou,
// parou ou travou. Por isso o limite da faixa e marcado por VOCE, com a
// busca guiada: o braco anda um micropasso por comando e para. Assim
// nunca se corre a faixa inteira as cegas contra o batente.
//
//   ZUMBIDO COM O BRACO PARADO = servo empurrando o batente. Recue um
//   passo na hora: parado ali ele puxa corrente, esquenta e desgasta a
//   engrenagem.
//
// LIGACAO
//   sinal -> pino 9
//   VCC   -> fonte externa de 5 V (o 5 V da placa nao aguenta: o SG90
//            passa de 700 mA no arranque e derruba o Arduino)
//   GND   -> GND da fonte E GND do Arduino, no mesmo ponto
//
// ROTEIRO
//   1. Abra o Monitor Serial em 9600, com "Nova linha" ao final.
//   2. C         centraliza em 1500 us (posicao segura)
//   3. - - -     desce de micropasso em micropasso ate o braco parar de
//                avancar; ZUMBIU, volte um passo com +
//      [         marca ali o limite INFERIOR
//   4. + + +     sobe ate o braco parar de avancar
//      ]         marca o limite SUPERIOR
//   5. M <graus> em algumas posicoes dentro da faixa, meca o angulo com
//                transferidor ou video e registre o par (pulso, angulo)
//   6. A         ajusta a reta graus->us com os pares registrados
//   7. G <graus> daqui em diante o braco vai ao angulo de verdade
//   8. V         varredura completa, so para registrar a curva em video
//
// NO TINKERCAD
// O servo simulado e ideal: aceita 544..2400 us, nao tem zona morta,
// nem folga, nem batente, e nao zumbe. Serve para conferir os comandos
// e a serial; os limites e a calibracao so saem do servo de verdade.
// Se o Tinkercad reclamar do EEPROM.h, troque USAR_EEPROM para 0.
// =====================================================================
#define USAR_EEPROM 1

#include <Servo.h>
#if USAR_EEPROM
#include <EEPROM.h>
#endif

const uint8_t PINO_SERVO = 9;
const uint8_t PINO_LED = LED_BUILTIN;
const int LIMITE_ABSOLUTO_MIN = 400;   // nenhum comando passa daqui
const int LIMITE_ABSOLUTO_MAX = 2600;
const uint8_t MAX_PARES = 12;          // pontos de calibracao guardados

int larguraMin = 1000;     // faixa de trabalho, estreita ate ser medida
int larguraMax = 2000;
int micropasso = 5;        // us por toque em + ou -
int esperaMs = 400;        // parada em cada largura durante a varredura
int larguraAtual = 1500;

// Caminhada automatica: 0 parada, +1 subindo, -1 descendo.
int andando = 0;
unsigned long proximoPasso = 0;
int esperaCaminhada = 1200;   // ms entre micropassos, tempo de olhar
int ultimoSentido = +1;       // em que sentido foi o ultimo passo

// Calibracao. Comeca com o padrao da biblioteca, que e justamente o que
// se quer substituir por medicao.
float usPorGrau = (2400.0 - 544.0) / 180.0;
float usEmZeroGrau = 544.0;

int paresUs[MAX_PARES];
float paresGrau[MAX_PARES];
uint8_t nPares = 0;

Servo servo;

// ---------------------------------------------------------------------
// MOVIMENTO
// ---------------------------------------------------------------------
void aplicar(int largura) {
  largura = constrain(largura, LIMITE_ABSOLUTO_MIN, LIMITE_ABSOLUTO_MAX);
  if (!servo.attached()) {
    servo.attach(PINO_SERVO, LIMITE_ABSOLUTO_MIN, LIMITE_ABSOLUTO_MAX);
  }
  servo.writeMicroseconds(largura);
  larguraAtual = largura;
}

void passo(int sentido) {
  int alvo = larguraAtual + sentido * micropasso;
  if (alvo < LIMITE_ABSOLUTO_MIN || alvo > LIMITE_ABSOLUTO_MAX) {
    Serial.println(F("! limite absoluto do sketch; nao vou alem"));
    return;
  }
  aplicar(alvo);
  ultimoSentido = sentido;
  Serial.print(F("pulso = "));
  Serial.print(larguraAtual);
  Serial.print(F(" us   (grau estimado "));
  Serial.print((larguraAtual - usEmZeroGrau) / usPorGrau, 1);
  Serial.println(F(")"));
  Serial.println(F("  avancou? deixe seguir. parou ou zumbiu? mande K"));
}

void pararCaminhada(const char* motivo) {
  if (andando == 0) return;
  andando = 0;
  Serial.print(F("caminhada parada ("));
  Serial.print(motivo);
  Serial.print(F(") em "));
  Serial.print(larguraAtual);
  Serial.println(F(" us"));
}

void marcarLimite() {
  // Marca no sentido do ultimo passo, recuando a margem de seguranca:
  // quando o braco para de avancar ele JA esta no batente, e deixar o
  // limite ali significa trabalhar empurrando a trava.
  pararCaminhada("K");
  int margem = 2 * micropasso;
  if (ultimoSentido > 0) {
    larguraMax = larguraAtual - margem;
    Serial.print(F("limite SUPERIOR = "));
    Serial.print(larguraMax);
  } else {
    larguraMin = larguraAtual + margem;
    Serial.print(F("limite INFERIOR = "));
    Serial.print(larguraMin);
  }
  Serial.print(F(" us  (o braco parou em "));
  Serial.print(larguraAtual);
  Serial.print(F("; recuei "));
  Serial.print(margem);
  Serial.println(F(" us de margem)"));
  aplicar(ultimoSentido > 0 ? larguraMax : larguraMin);
}

// ---------------------------------------------------------------------
// CALIBRACAO
// ---------------------------------------------------------------------
void registrarPar(float graus) {
  if (nPares >= MAX_PARES) {
    Serial.println(F("! cheio; use A para ajustar ou Z para zerar"));
    return;
  }
  paresUs[nPares] = larguraAtual;
  paresGrau[nPares] = graus;
  nPares++;
  Serial.print(F("ponto "));   Serial.print(nPares);
  Serial.print(F(": "));       Serial.print(larguraAtual);
  Serial.print(F(" us = "));   Serial.print(graus, 2);
  Serial.println(F(" graus"));
}

void ajustarReta() {
  // Minimos quadrados de us = a*graus + b. Com dois pontos vira a reta
  // que passa por eles; com mais, a media ponderada que melhor os
  // representa -- e e por isso que vale medir em varias posicoes, e nao
  // so nas duas pontas, onde a folga e maior.
  if (nPares < 2) {
    Serial.println(F("! preciso de pelo menos 2 pontos (comando M)"));
    return;
  }
  float somaX = 0, somaY = 0, somaXY = 0, somaXX = 0;
  for (uint8_t i = 0; i < nPares; i++) {
    somaX += paresGrau[i];
    somaY += paresUs[i];
    somaXY += paresGrau[i] * paresUs[i];
    somaXX += paresGrau[i] * paresGrau[i];
  }
  float n = nPares;
  float denominador = n * somaXX - somaX * somaX;
  if (fabs(denominador) < 1e-6) {
    Serial.println(F("! os pontos tem o mesmo angulo; meca em posicoes "
                     "diferentes"));
    return;
  }
  usPorGrau = (n * somaXY - somaX * somaY) / denominador;
  usEmZeroGrau = (somaY - usPorGrau * somaX) / n;

  float pior = 0;
  for (uint8_t i = 0; i < nPares; i++) {
    float previsto = usEmZeroGrau + usPorGrau * paresGrau[i];
    float desvio = fabs(paresUs[i] - previsto);
    // Comparacao explicita em vez de max(): em placas cujo core define
    // max como template (ESP32, SAMD), misturar float com double nao
    // compila. Assim o sketch vale em qualquer placa.
    if (desvio > pior) pior = desvio;
  }

  Serial.println(F("--- calibracao ajustada ---"));
  Serial.print(F("  us = "));     Serial.print(usEmZeroGrau, 1);
  Serial.print(F(" + "));         Serial.print(usPorGrau, 4);
  Serial.println(F(" * graus"));
  Serial.print(F("  0 grau -> "));   Serial.print(usEmZeroGrau, 0);
  Serial.print(F(" us ; 180 graus -> "));
  Serial.print(usEmZeroGrau + 180.0 * usPorGrau, 0);
  Serial.println(F(" us"));
  Serial.print(F("  maior desvio: ")); Serial.print(pior, 1);
  Serial.print(F(" us ("));            Serial.print(pior / usPorGrau, 2);
  Serial.println(F(" graus)"));
  float padrao = (2400.0 - 544.0) / 180.0;
  Serial.print(F("  a biblioteca Servo usa "));  Serial.print(padrao, 4);
  Serial.print(F(" us/grau ("));
  Serial.print(100.0 * (usPorGrau / padrao - 1.0), 1);
  Serial.println(F("% de diferenca)"));
}

#if USAR_EEPROM
const int ENDERECO = 0;
const uint32_t ASSINATURA = 0x53473930;   // "SG90"

void gravarEeprom() {
  int endereco = ENDERECO;
  EEPROM.put(endereco, ASSINATURA);       endereco += sizeof(ASSINATURA);
  EEPROM.put(endereco, usPorGrau);        endereco += sizeof(usPorGrau);
  EEPROM.put(endereco, usEmZeroGrau);     endereco += sizeof(usEmZeroGrau);
  EEPROM.put(endereco, larguraMin);       endereco += sizeof(larguraMin);
  EEPROM.put(endereco, larguraMax);
  Serial.println(F("gravado na EEPROM; sobrevive a desligar a placa"));
}

bool lerEeprom() {
  int endereco = ENDERECO;
  uint32_t marca;
  EEPROM.get(endereco, marca);
  if (marca != ASSINATURA) return false;
  endereco += sizeof(marca);
  EEPROM.get(endereco, usPorGrau);        endereco += sizeof(usPorGrau);
  EEPROM.get(endereco, usEmZeroGrau);     endereco += sizeof(usEmZeroGrau);
  EEPROM.get(endereco, larguraMin);       endereco += sizeof(larguraMin);
  EEPROM.get(endereco, larguraMax);
  return true;
}
#endif

// ---------------------------------------------------------------------
// VARREDURA
// ---------------------------------------------------------------------
void piscarSincronismo() {
  for (uint8_t i = 0; i < 3; i++) {
    digitalWrite(PINO_LED, HIGH); delay(120);
    digitalWrite(PINO_LED, LOW);  delay(120);
  }
}

void registrar(const char* sentido) {
  Serial.print(millis());       Serial.print(';');
  Serial.print(larguraAtual);   Serial.print(';');
  Serial.print(sentido);        Serial.print(';');
  Serial.println((larguraAtual - usEmZeroGrau) / usPorGrau, 2);
}

void varrer() {
  Serial.println(F("# varredura; 3 piscadas marcam o inicio no video"));
  Serial.println(F("# ms;largura_us;sentido;grau_estimado"));
  aplicar(larguraMin);
  delay(1000);
  piscarSincronismo();

  for (int us = larguraMin; us <= larguraMax; us += micropasso) {
    aplicar(us); delay(esperaMs); registrar("sobe");
  }
  // A volta mede a folga da engrenagem: o braco nao para no mesmo lugar
  // chegando por cima e por baixo. Sem ela, essa parcela some dentro do
  // erro e nao da para separar do ganho.
  for (int us = larguraMax; us >= larguraMin; us -= micropasso) {
    aplicar(us); delay(esperaMs); registrar("desce");
  }
  Serial.println(F("# fim"));
}

// ---------------------------------------------------------------------
// SERIAL
// ---------------------------------------------------------------------
void mostrarEstado() {
  Serial.println(F("--- estado ---"));
  Serial.print(F("  faixa marcada: ")); Serial.print(larguraMin);
  Serial.print(F(" a "));               Serial.print(larguraMax);
  Serial.print(F(" us   |   pulso atual: ")); Serial.print(larguraAtual);
  Serial.println(F(" us"));
  Serial.print(F("  micropasso: "));    Serial.print(micropasso);
  Serial.print(F(" us   |   espera: ")); Serial.print(esperaMs);
  Serial.print(F(" ms   |   pontos de calibracao: "));
  Serial.println(nPares);
  Serial.print(F("  us = "));  Serial.print(usEmZeroGrau, 1);
  Serial.print(F(" + "));      Serial.print(usPorGrau, 4);
  Serial.println(F(" * graus"));
}

void mostrarAjuda() {
  Serial.println(F("=== comandos ==="));
  Serial.println(F("  C          centraliza em 1500 us"));
  Serial.println(F("  +  /  -    anda UM micropasso para cima / para baixo"));
  Serial.println(F("  W+ / W-    anda sozinho, passo a passo, ate voce mandar K"));
  Serial.println(F("  K          PARA e marca o limite no sentido em que ia"));
  Serial.println(F("  [  /  ]    marca o pulso atual como limite inf / sup"));
  Serial.println(F("  P <us>     vai para uma largura de pulso"));
  Serial.println(F("  M <graus>  registra: pulso atual = este angulo medido"));
  Serial.println(F("  A          ajusta a reta graus->us com os pontos"));
  Serial.println(F("  Z          apaga os pontos de calibracao"));
  Serial.println(F("  G <graus>  vai ao angulo usando a calibracao"));
  Serial.println(F("  V          varredura completa (sobe e desce)"));
  Serial.println(F("  D <us>     micropasso   T <ms> espera da varredura"));
  Serial.println(F("  I <ms>     intervalo entre passos da caminhada"));
#if USAR_EEPROM
  Serial.println(F("  E / R      grava / recarrega da EEPROM"));
#endif
  Serial.println(F("  L          solta o servo     ?  estado"));
}

long lerInteiro(const char* texto) {
  while (*texto == ' ') texto++;
  return atol(texto);
}

float lerDecimal(const char* texto) {
  while (*texto == ' ') texto++;
  return atof(texto);
}

void executar(char* linha) {
  char comando = toupper(linha[0]);
  char* argumento = linha + 1;

  switch (comando) {
    case 'C': aplicar(1500); Serial.println(F("centralizado em 1500 us")); break;
    case '+': pararCaminhada("comando"); passo(+1); break;
    case '-': pararCaminhada("comando"); passo(-1); break;

    case 'W': {
      // Caminhada automatica: um micropasso a cada esperaCaminhada ms,
      // ate voce mandar K. Entre um passo e outro o loop continua
      // livre, entao o comando de parada e atendido na hora -- com
      // delay() dentro de um laco ele so seria lido no fim.
      char sentido = argumento[0];
      while (*argumento == ' ') { argumento++; sentido = argumento[0]; }
      andando = (sentido == '-') ? -1 : +1;
      proximoPasso = millis();
      Serial.print(F("andando "));
      Serial.print(andando > 0 ? F("para cima") : F("para baixo"));
      Serial.print(F(", um passo de "));
      Serial.print(micropasso);
      Serial.print(F(" us a cada "));
      Serial.print(esperaCaminhada);
      Serial.println(F(" ms. Mande K quando parar de avancar ou zumbir."));
      break;
    }
    case 'K': marcarLimite(); break;

    case '[':
      larguraMin = larguraAtual;
      Serial.print(F("limite inferior = ")); Serial.print(larguraMin);
      Serial.println(F(" us"));
      break;
    case ']':
      larguraMax = larguraAtual;
      Serial.print(F("limite superior = ")); Serial.print(larguraMax);
      Serial.println(F(" us"));
      break;

    case 'P': {
      int us = lerInteiro(argumento);
      if (us > 0) { aplicar(us);
        Serial.print(F("pulso = ")); Serial.print(larguraAtual);
        Serial.println(F(" us"));
      }
      break;
    }
    case 'M': registrarPar(lerDecimal(argumento)); break;
    case 'A': ajustarReta(); break;
    case 'Z': nPares = 0; Serial.println(F("pontos apagados")); break;

    case 'G': {
      float graus = lerDecimal(argumento);
      int alvo = (int)round(usEmZeroGrau + usPorGrau * graus);
      if (alvo < larguraMin || alvo > larguraMax) {
        Serial.print(F("! "));      Serial.print(graus, 1);
        Serial.print(F(" graus daria ")); Serial.print(alvo);
        Serial.println(F(" us, fora da faixa marcada"));
        break;
      }
      aplicar(alvo);
      Serial.print(graus, 1);     Serial.print(F(" graus -> "));
      Serial.print(larguraAtual); Serial.println(F(" us"));
      break;
    }

    case 'V': varrer(); break;
    case 'I': {
      int valor = lerInteiro(argumento);
      if (valor > 0) esperaCaminhada = valor;
      mostrarEstado();
      break;
    }
    case 'D': {
      int valor = lerInteiro(argumento);
      if (valor > 0) micropasso = valor;
      mostrarEstado();
      break;
    }
    case 'T': {
      int valor = lerInteiro(argumento);
      if (valor > 0) esperaMs = valor;
      mostrarEstado();
      break;
    }
#if USAR_EEPROM
    case 'E': gravarEeprom(); break;
    case 'R':
      if (lerEeprom()) { Serial.println(F("recarregado da EEPROM"));
                         mostrarEstado(); }
      else Serial.println(F("! nao ha calibracao gravada"));
      break;
#endif
    case 'L': servo.detach(); Serial.println(F("servo solto")); break;
    case '?': mostrarEstado(); break;
    default:  mostrarAjuda(); break;
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
  aplicar(1500);
  Serial.println(F("=== SG90: faixa util e calibracao ==="));
#if USAR_EEPROM
  if (lerEeprom()) Serial.println(F("calibracao recuperada da EEPROM"));
#endif
  mostrarAjuda();
  mostrarEstado();
  Serial.println(F("Comece em C, depois - e + para achar os limites. "
                   "Zumbiu? volte um passo."));
}

void loop() {
  // Leitura byte a byte num buffer fixo: sem String, que fragmenta a
  // memoria do AVR em uso prolongado.
  static char linha[24];
  static uint8_t n = 0;

  while (Serial.available()) {
    char caractere = Serial.read();
    if (caractere == '\n' || caractere == '\r') {
      if (n > 0) { linha[n] = '\0'; executar(linha); n = 0; }
    } else if (n < sizeof(linha) - 1) {
      linha[n++] = caractere;
    }
  }

  // A caminhada vive aqui, e nao dentro de um laco com delay(): assim
  // o K e lido entre um passo e outro, e nao so no fim.
  if (andando != 0 && (long)(millis() - proximoPasso) >= 0) {
    int alvo = larguraAtual + andando * micropasso;
    if (alvo < LIMITE_ABSOLUTO_MIN || alvo > LIMITE_ABSOLUTO_MAX) {
      pararCaminhada("limite absoluto do sketch");
      return;
    }
    passo(andando);
    proximoPasso = millis() + esperaCaminhada;
  }
}
