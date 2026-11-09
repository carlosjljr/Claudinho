# -*- coding: utf-8 -*-
# =====================================================================
# MEDIDOR DE ANGULO EM SOBREPOSICAO (transferidor de tela)
# =====================================================================
# Desenha duas retas por cima de qualquer coisa que esteja na tela --
# um video, uma foto, o Tracker -- e mede o angulo entre elas.
#
# Para rodar:  python medidor_angulo.py
#
# Teclas:
#   F2       alterna edicao / clique atravessa a janela
#   R        volta a configuracao inicial
#   S        salva a medicao atual no arquivo CSV
#   C        copia a medicao para a area de transferencia
#   setas    ajuste fino do ponto selecionado (Shift = 10x)
#   ESC      sai
#
# Tres alcas arrastaveis: o VERTICE e as duas PONTAS. A versao anterior
# prendia as duas retas no centro da tela e so deixava girar; aqui o
# vertice vai para onde esta a junta do manipulador na imagem, que e o
# que um transferidor precisa fazer.
# =====================================================================
import csv
import math
import os
import sys
from datetime import datetime

# Arquivo das medicoes, criado ao lado do programa (ou do .exe).
PASTA = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__))
ARQUIVO_MEDICOES = os.path.join(PASTA, "medicoes_angulo.csv")

CORES = {"reta_a": "#00FF7F", "reta_b": "#00BFFF", "vertice": "#FFFFFF",
         "texto": "#FFFFFF", "arco": "#FFD400"}
RAIO_ALCA = 7          # raio do circulo de cada alca, em pixels
DISTANCIA_PEGA = 22    # a que distancia o clique agarra uma alca


# ---------------------------------------------------------------------
# GEOMETRIA (sem dependencia de interface, para poder ser testada)
# ---------------------------------------------------------------------
def angulo_da_reta(vertice, ponta):
    """Angulo da reta com a horizontal, em graus, de 0 a 360.

    O eixo Y da tela cresce para BAIXO. Sem inverter o sinal, uma reta
    subindo apareceria com angulo negativo e a leitura sairia espelhada
    em relacao a convencao usada no resto da analise (anti-horario
    positivo, como no Tracker).
    """
    dx = ponta[0] - vertice[0]
    dy = -(ponta[1] - vertice[1])
    return math.degrees(math.atan2(dy, dx)) % 360.0


def angulo_entre(angulo_a, angulo_b):
    """Menor angulo entre duas retas, de 0 a 180 graus."""
    diferenca = abs(angulo_b - angulo_a) % 360.0
    return 360.0 - diferenca if diferenca > 180.0 else diferenca


def comprimento(vertice, ponta):
    return math.hypot(ponta[0] - vertice[0], ponta[1] - vertice[1])


def medir(vertice, ponta_a, ponta_b):
    """Todas as grandezas da medicao, num dicionario."""
    a = angulo_da_reta(vertice, ponta_a)
    b = angulo_da_reta(vertice, ponta_b)
    return {
        "vertice_x": vertice[0], "vertice_y": vertice[1],
        "ponta_a_x": ponta_a[0], "ponta_a_y": ponta_a[1],
        "ponta_b_x": ponta_b[0], "ponta_b_y": ponta_b[1],
        "angulo_a_graus": a,
        "angulo_b_graus": b,
        "angulo_entre_graus": angulo_entre(a, b),
        "comprimento_a_px": comprimento(vertice, ponta_a),
        "comprimento_b_px": comprimento(vertice, ponta_b),
    }


def gravar_medicao(medida, caminho=ARQUIVO_MEDICOES):
    """Acrescenta uma linha ao CSV, criando o cabecalho na primeira vez.

    Sem isto a ferramenta so mostra o numero na tela e o valor tem de
    ser copiado a mao para a planilha -- que e justamente onde entram os
    erros de transcricao.
    """
    linha = {"instante": datetime.now().isoformat(timespec="seconds")}
    linha.update({chave: round(valor, 2) for chave, valor in medida.items()})
    novo = not os.path.exists(caminho)
    with open(caminho, "a", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linha),
                                  delimiter=";")
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)
    return caminho


# ---------------------------------------------------------------------
# INTERFACE
# ---------------------------------------------------------------------
def executar():
    import tkinter as tk

    class Medidor:
        def __init__(self):
            self.raiz = tk.Tk()
            self.raiz.attributes("-fullscreen", True)
            self.raiz.attributes("-topmost", True)
            self.raiz.configure(bg="black")
            # Fundo transparente so existe no Windows; nos outros
            # sistemas a janela fica escura, mas a ferramenta funciona.
            try:
                self.raiz.wm_attributes("-transparentcolor", "black")
            except tk.TclError:
                self.raiz.attributes("-alpha", 0.75)

            self.tela = tk.Canvas(self.raiz, bg="black", highlightthickness=0)
            self.tela.pack(fill="both", expand=True)
            self.largura = self.raiz.winfo_screenwidth()
            self.altura = self.raiz.winfo_screenheight()

            self.editando = True
            self.arrastando = None
            self.mensagem = ""
            self.reiniciar()

            self.tela.bind("<Button-1>", self.pegar)
            self.tela.bind("<B1-Motion>", self.arrastar)
            self.tela.bind("<ButtonRelease-1>", self.soltar)
            self.raiz.bind("<Escape>", lambda e: self.raiz.destroy())
            self.raiz.bind("<F2>", self.alternar_edicao)
            for tecla in ("r", "R"):
                self.raiz.bind(tecla, self.reiniciar)
            for tecla in ("s", "S"):
                self.raiz.bind(tecla, self.salvar)
            for tecla in ("c", "C"):
                self.raiz.bind(tecla, self.copiar)
            for tecla, passo in (("Left", (-1, 0)), ("Right", (1, 0)),
                                 ("Up", (0, -1)), ("Down", (0, 1))):
                self.raiz.bind(f"<{tecla}>",
                               lambda e, p=passo: self.empurrar(p, 1))
                self.raiz.bind(f"<Shift-{tecla}>",
                               lambda e, p=passo: self.empurrar(p, 10))

            self.atravessar_cliques(False)
            self.desenhar()
            self.raiz.mainloop()

        # --- estado -------------------------------------------------
        def reiniciar(self, evento=None):
            meio = (self.largura // 2, self.altura // 2)
            self.vertice = list(meio)
            self.ponta_a = [meio[0] + 300, meio[1]]
            self.ponta_b = [meio[0] + 212, meio[1] - 212]
            self.selecionada = "a"
            self.mensagem = ""
            self.desenhar()

        def alcas(self):
            return {"v": self.vertice, "a": self.ponta_a, "b": self.ponta_b}

        # --- mouse e teclado ----------------------------------------
        def pegar(self, evento):
            if not self.editando:
                return
            nome, perto = None, DISTANCIA_PEGA
            for chave, ponto in self.alcas().items():
                distancia = math.hypot(evento.x - ponto[0], evento.y - ponto[1])
                if distancia < perto:
                    nome, perto = chave, distancia
            self.arrastando = nome
            if nome in ("a", "b"):
                self.selecionada = nome

        def arrastar(self, evento):
            if not self.editando or self.arrastando is None:
                return
            if self.arrastando == "v":
                # Arrastar o vertice leva as duas pontas junto: a figura
                # inteira se desloca sem perder os angulos ja ajustados.
                dx = evento.x - self.vertice[0]
                dy = evento.y - self.vertice[1]
                for ponto in (self.vertice, self.ponta_a, self.ponta_b):
                    ponto[0] += dx
                    ponto[1] += dy
            else:
                ponto = self.alcas()[self.arrastando]
                ponto[0], ponto[1] = evento.x, evento.y
            self.desenhar()

        def soltar(self, evento):
            self.arrastando = None

        def empurrar(self, passo, fator):
            if not self.editando:
                return
            ponto = self.alcas()[self.selecionada]
            ponto[0] += passo[0] * fator
            ponto[1] += passo[1] * fator
            self.desenhar()

        def alternar_edicao(self, evento=None):
            self.editando = not self.editando
            self.atravessar_cliques(not self.editando)
            self.desenhar()

        def atravessar_cliques(self, ativar=True):
            """Deixa o clique passar para a janela de baixo (so Windows)."""
            if not sys.platform.startswith("win"):
                return
            import ctypes
            try:
                janela = ctypes.windll.user32.GetParent(self.raiz.winfo_id())
                estilo = ctypes.windll.user32.GetWindowLongW(janela, -20)
                if ativar:
                    estilo |= 0x00080000 | 0x00000020   # LAYERED | TRANSPARENT
                else:
                    estilo &= ~0x00000020
                ctypes.windll.user32.SetWindowLongW(janela, -20, estilo)
            except OSError as erro:
                # Sem silenciar: se falhar, a pessoa precisa saber por que
                # o clique nao esta passando.
                self.mensagem = f"clique-atraves indisponivel ({erro})"

        # --- acoes --------------------------------------------------
        def medida(self):
            return medir(tuple(self.vertice), tuple(self.ponta_a),
                         tuple(self.ponta_b))

        def resumo(self):
            m = self.medida()
            return (f"{m['angulo_a_graus']:.2f};{m['angulo_b_graus']:.2f};"
                    f"{m['angulo_entre_graus']:.2f}")

        def salvar(self, evento=None):
            try:
                caminho = gravar_medicao(self.medida())
                self.mensagem = f"salvo em {os.path.basename(caminho)}"
            except OSError as erro:
                self.mensagem = f"nao foi possivel salvar ({erro})"
            self.desenhar()

        def copiar(self, evento=None):
            self.raiz.clipboard_clear()
            self.raiz.clipboard_append(self.resumo())
            self.mensagem = "copiado (ângulo A; ângulo B; entre)"
            self.desenhar()

        # --- desenho ------------------------------------------------
        def desenhar(self):
            self.tela.delete("all")
            m = self.medida()

            for ponta, cor in ((self.ponta_a, CORES["reta_a"]),
                               (self.ponta_b, CORES["reta_b"])):
                self.tela.create_line(*self.vertice, *ponta, fill=cor, width=3)
                self.tela.create_oval(ponta[0] - RAIO_ALCA, ponta[1] - RAIO_ALCA,
                                      ponta[0] + RAIO_ALCA, ponta[1] + RAIO_ALCA,
                                      outline=cor, width=2)

            # Arco entre as duas retas, do tamanho da menor delas: mostra
            # QUAL angulo esta sendo medido, que e o que um numero
            # sozinho nao diz.
            raio = max(30.0, 0.35 * min(m["comprimento_a_px"],
                                        m["comprimento_b_px"]))
            inicio = m["angulo_a_graus"]
            extensao = (m["angulo_b_graus"] - m["angulo_a_graus"]) % 360.0
            if extensao > 180.0:
                inicio, extensao = m["angulo_b_graus"], 360.0 - extensao
            self.tela.create_arc(self.vertice[0] - raio, self.vertice[1] - raio,
                                 self.vertice[0] + raio, self.vertice[1] + raio,
                                 start=inicio, extent=extensao, style="arc",
                                 outline=CORES["arco"], width=2)

            self.tela.create_oval(
                self.vertice[0] - RAIO_ALCA, self.vertice[1] - RAIO_ALCA,
                self.vertice[0] + RAIO_ALCA, self.vertice[1] + RAIO_ALCA,
                fill=CORES["vertice"], outline=CORES["vertice"])

            texto = (f"Reta A: {m['angulo_a_graus']:7.2f}°   "
                     f"({m['comprimento_a_px']:.0f} px)\n"
                     f"Reta B: {m['angulo_b_graus']:7.2f}°   "
                     f"({m['comprimento_b_px']:.0f} px)\n"
                     f"Entre elas: {m['angulo_entre_graus']:.2f}°\n\n")
            texto += ("[F2] edição ligada — arraste o vértice ou as pontas\n"
                      if self.editando else
                      "[F2] edição desligada — o clique atravessa\n")
            texto += ("[S] salvar   [C] copiar   [R] reiniciar   "
                      "[setas] 1 px   [Shift+setas] 10 px   [ESC] sair")
            if self.mensagem:
                texto += f"\n\n{self.mensagem}"

            # Sombra atras do texto, para ele continuar legivel sobre
            # qualquer imagem clara.
            for deslocamento, cor in (((1, 1), "#000000"), ((0, 0), CORES["texto"])):
                self.tela.create_text(20 + deslocamento[0], 20 + deslocamento[1],
                                      text=texto, fill=cor, anchor="nw",
                                      font=("Consolas", 12))

    Medidor()


if __name__ == "__main__":
    executar()
