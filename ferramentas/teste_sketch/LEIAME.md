# Sessão simulada do sketch, sem Arduino

Compila o `sg90_caracterizacao.ino` como C++ comum, contra versões de
mentira das bibliotecas `Servo`, `EEPROM` e `Serial`, e roda uma sessão
de comandos escrita no `main.cpp`. Serve para conferir a lógica do
A / P / F — e a sintaxe — antes de subir para a placa ou o TinkerCad.

O relógio é simulado: `rodar(5000)` avança 5 segundos em passos de
50 ms chamando `loop()`, então a caminhada automática acontece sem
esperar de verdade.

```sh
cd ferramentas/teste_sketch
cp ../sg90_caracterizacao.ino sketch.cpp
sed -i '1i #include "Arduino.h"' sketch.cpp
g++ -std=c++17 -I. -o sessao main.cpp && ./sessao
```

Não substitui o ensaio real: aqui não há batente, zumbido, folga nem
queda de tensão. O que isto pega é erro de programa.
