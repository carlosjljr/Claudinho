# -*- coding: utf-8 -*-
"""Testes da geometria do medidor (sem abrir janela).

Rodar com:  python test_medidor_angulo.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from medidor_angulo import (angulo_da_reta, angulo_entre, comprimento,  # noqa
                            gravar_medicao, medir)

FALHAS = []


def verificar(condicao, mensagem):
    print(("  ok   " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


def perto(a, b, tol=1e-9):
    return abs(a - b) < tol


V = (100.0, 100.0)

print("\n[1] Ângulo da reta (eixo Y da tela cresce para baixo)")
verificar(perto(angulo_da_reta(V, (200.0, 100.0)), 0.0), "direita = 0°")
verificar(perto(angulo_da_reta(V, (100.0, 0.0)), 90.0),
          "para cima na tela = +90° (e não -90°)")
verificar(perto(angulo_da_reta(V, (0.0, 100.0)), 180.0), "esquerda = 180°")
verificar(perto(angulo_da_reta(V, (100.0, 200.0)), 270.0),
          "para baixo na tela = 270°")
verificar(perto(angulo_da_reta(V, (200.0, 0.0)), 45.0), "diagonal = 45°")

print("\n[2] Ângulo entre as retas: sempre o menor, de 0 a 180")
verificar(perto(angulo_entre(0.0, 45.0), 45.0), "0° e 45° -> 45°")
verificar(perto(angulo_entre(45.0, 0.0), 45.0), "ordem não importa")
verificar(perto(angulo_entre(10.0, 350.0), 20.0),
          "atravessando o zero: 10° e 350° -> 20°")
verificar(perto(angulo_entre(0.0, 190.0), 170.0), "nunca passa de 180°")
verificar(perto(angulo_entre(0.0, 180.0), 180.0), "retas opostas -> 180°")

print("\n[3] Comprimento e medição completa")
verificar(perto(comprimento(V, (103.0, 104.0)), 5.0), "3-4-5")
medida = medir(V, (200.0, 100.0), (100.0, 0.0))
verificar(perto(medida["angulo_entre_graus"], 90.0),
          "retas perpendiculares -> 90°")
verificar(perto(medida["comprimento_a_px"], 100.0)
          and perto(medida["comprimento_b_px"], 100.0),
          "comprimentos das duas retas")

print("\n[4] Gravação no CSV")
with tempfile.TemporaryDirectory() as pasta:
    caminho = os.path.join(pasta, "medicoes.csv")
    gravar_medicao(medida, caminho)
    gravar_medicao(medida, caminho)
    with open(caminho, encoding="utf-8-sig") as arquivo:
        linhas = arquivo.read().strip().split("\n")
    verificar(len(linhas) == 3, f"cabeçalho + 2 medições ({len(linhas)} linhas)")
    verificar(linhas[0].startswith("instante;vertice_x"), "cabeçalho correto")
    verificar(linhas[1].count(";") == linhas[0].count(";"),
              "mesma quantidade de campos na linha de dados")

print()
if FALHAS:
    print(f"{len(FALHAS)} verificação(ões) falharam.")
    sys.exit(1)
print("Todas as verificações passaram.")
