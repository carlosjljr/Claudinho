#pragma once
#include <cstdint>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <cctype>
#include <cstdio>
#include <string>
#include <deque>
#define F(x) (x)
#define LED_BUILTIN 13
#define OUTPUT 1
#define HIGH 1
#define LOW 0
typedef uint8_t byte;
extern unsigned long RELOGIO;        // ms simulados
inline void pinMode(int,int){} inline void digitalWrite(int,int){}
inline void delay(unsigned long ms){ RELOGIO += ms; }
inline unsigned long millis(){ return RELOGIO; }
template<class T> T constrain(T v,T a,T b){return v<a?a:(v>b?b:v);}
struct SerialClass{
  std::deque<char> entrada;
  void begin(long){}
  void manda(const std::string& s){ for(char c: s) entrada.push_back(c); entrada.push_back('\n'); }
  int available(){ return (int)entrada.size(); }
  int read(){ if(entrada.empty()) return -1; char c=entrada.front(); entrada.pop_front(); return c; }
  void print(const char* s){ std::fputs(s, stdout); }
  void print(char c){ std::putchar(c); }
  void print(int v){ std::printf("%d", v); }
  void print(long v){ std::printf("%ld", v); }
  void print(unsigned long v){ std::printf("%lu", v); }
  void print(double v,int d=2){ std::printf("%.*f", d, v); }
  void println(const char* s){ std::printf("%s\n", s); }
  void println(int v){ std::printf("%d\n", v); }
  void println(long v){ std::printf("%ld\n", v); }
  void println(double v,int d=2){ std::printf("%.*f\n", d, v); }
  void println(){ std::putchar('\n'); }
};
extern SerialClass Serial;
