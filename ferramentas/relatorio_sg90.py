# -*- coding: utf-8 -*-
"""Relatorio de uma pagina da caracterizacao do SG90 (PDF).

Preencha PASSADAS com as marcacoes de cada passada (None = ainda nao
feita) e rode:  python relatorio_sg90.py
Media, ajuste e conclusoes sao recalculados com as passadas presentes.
"""
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SERVO = "SG90 nº 6"
ANGULOS = (0, 90, 180)
# pulso (µs) marcado em cada angulo visual, por passada
PASSADAS = [
    (440, 1445, 2460),
    (435, 1435, 2455),
    (435, 1430, 2450),
    None, None, None,
]
BATENTES = (350, 2640)                # µs, limites mecanicos medidos
LIB_US_POR_GRAU = (2400 - 544) / 180  # tabela da biblioteca Servo
GANHO_MAPA = "0,925 (PE01) e 0,904 (PE02)"
SAIDA = "relatorio_sg90.pdf"


def br(x, casas=1):
    return f"{x:.{casas}f}".replace(".", ",")


feitas = [p for p in PASSADAS if p]
g = np.repeat(ANGULOS, 1)[None, :].repeat(len(feitas), 0).ravel().astype(float)
u = np.array(feitas, float).ravel()
b, a = np.polyfit(g, u, 1)
res = u - (a + b * g)
rms, rmax = np.sqrt(np.mean(res**2)) / b, np.abs(res).max() / b
ganho = LIB_US_POR_GRAU / b
medias = np.mean(feitas, axis=0)
disp = np.ptp(feitas, axis=0)

est = getSampleStyleSheet()
corpo = ParagraphStyle("c", parent=est["BodyText"], fontSize=9.5, leading=12.5)
tit = ParagraphStyle("t", parent=est["Title"], fontSize=15, spaceAfter=2)
sub = ParagraphStyle("s", parent=est["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=3)
nota = ParagraphStyle("n", parent=corpo, fontSize=8, textColor=colors.grey)

def tabela(dados, larguras, cab=1):
    t = Table(dados, colWidths=larguras)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, cab - 1), colors.HexColor("#E8EDF3")),
        ("FONTNAME", (0, 0), (-1, cab - 1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA5B1")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t

# tabela das passadas: angulos nas linhas, passadas nas colunas
cab = ["Ângulo visual"] + [f"P{i}" for i in range(1, 7)] + ["Média", "Disp."]
linhas = [cab]
for j, ang in enumerate(ANGULOS):
    lin = [f"{ang}°"] + [str(p[j]) if p else "" for p in PASSADAS]
    lin += [br(medias[j]), f"{disp[j]:.0f}"]
    linhas.append(lin)
t_pass = tabela(linhas, [28 * mm] + [15 * mm] * 6 + [19 * mm, 15 * mm])

lib0, lib180 = (544 - a) / b, (2400 - a) / b
t_comp = tabela([
    ["Comando", "Pulso enviado", "Posição real"],
    ["write(0)", "544 µs", f"≈ {br(lib0)}°"],
    ["write(180)", "2400 µs", f"≈ {br(lib180)}°"],
], [40 * mm, 40 * mm, 40 * mm])

n = len(feitas)
doc = SimpleDocTemplate(SAIDA, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                        topMargin=15 * mm, bottomMargin=13 * mm)
partes = [
    Paragraph(f"Caracterização do servo {SERVO}", tit),
    Paragraph(f"Ensaio 3 — pulso (µs) × ângulo, {n} de {len(PASSADAS)} passadas realizadas, "
              "marcação visual de 0°, 90° e 180°, todas as passadas subindo.", corpo),

    Paragraph("1. Marcações por passada (µs)", sub), t_pass,
    Paragraph("Disp. = maior menos menor marcação entre as passadas realizadas. "
              "Colunas em branco: passadas ainda não feitas.", nota),

    Paragraph("2. Calibração", sub),
    Paragraph(f"<b>µs = {br(a)} + {br(b, 4)} × graus</b> &nbsp; (mínimos quadrados, {len(u)} marcações)", corpo),
    Paragraph(f"Resíduo RMS: <b>{br(rms, 2)}°</b> &nbsp;|&nbsp; resíduo máximo: {br(rmax, 2)}° "
              f"&nbsp;|&nbsp; repetibilidade entre passadas: {br(disp.min() / b)}° a {br(disp.max() / b)}°", corpo),
    Paragraph(f"Batentes mecânicos: {BATENTES[0]} e {BATENTES[1]} µs, equivalentes a "
              f"{br((BATENTES[0] - a) / b)}° e {br((BATENTES[1] - a) / b)}°: "
              f"curso mecânico de ≈ {br((BATENTES[1] - BATENTES[0]) / b, 0)}°, com o 0–180° visual folgado dentro dele.", corpo),

    Paragraph("3. Comparação com a biblioteca Servo", sub),
    Paragraph(f"A biblioteca converte 0–180° em 544–2400 µs, ou <b>{br(LIB_US_POR_GRAU, 2)} µs/grau</b>. "
              f"Este servo precisa de <b>{br(b, 2)} µs/grau</b>. Ganho previsto ao comandar por "
              f"<i>write(graus)</i>: {br(LIB_US_POR_GRAU, 2)} / {br(b, 2)} = <b>{br(ganho, 3)}</b>.", corpo),
    Spacer(1, 3), t_comp,
    Paragraph(f"Com <i>write()</i>, os ensaios antigos percorreram ≈ {br(lib180 - lib0, 0)}°, e não 180°.", corpo),

    Paragraph("4. Conclusão", sub),
    Paragraph(f"O ganho previsto ({br(ganho, 3)}) coincide com o observado no mapa angular para o "
              f"atuador 2: {GANHO_MAPA}. A sub-entrega do atuador 2 decorre da conversão graus → µs "
              "da biblioteca aplicada a um servo de outra escala, e não da estrutura dos protótipos. "
              "Os Apêndices A e B passam a comandar por <i>writeMicroseconds</i> com esta calibração.", corpo),

    Paragraph("5. Ressalvas", sub),
    Paragraph("• Calibração de um único servo; cada SG90 dos protótipos precisa da sua.<br/>"
              "• Marcação visual; com transferidor ou Tracker o resíduo deve diminuir.<br/>"
              "• Histerese não medida: todas as passadas subindo. Uma passada descendo nos mesmos "
              "pontos quantifica a folga.<br/>"
              "• O atuador 1 teve ganho de 0,96 a 0,99 no mapa angular; vale caracterizar os dois "
              "servos de cada protótipo.", corpo),
]
doc.build(partes)
print(f"gerado: {SAIDA}  ({n} passadas, ganho previsto {ganho:.4f})")
