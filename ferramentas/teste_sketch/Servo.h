#pragma once
extern int PULSO_APLICADO;
class Servo { public: bool at=false;
  void attach(int){at=true;} void attach(int,int,int){at=true;}
  bool attached(){return at;}
  void writeMicroseconds(int us){ PULSO_APLICADO = us; }
  void detach(){at=false;} };
