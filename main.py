"""
CPU Scheduler Simulator
Algoritmos: SJF, SRTF, Prioridades, Round Robin
UI: Pygame — estética terminal / industrial refinada
"""

import pygame
import sys

pygame.init()

# ═══════════════════════════════════════════════════════════════════════════════
#  PALETA
# ═══════════════════════════════════════════════════════════════════════════════
# Catppuccin Mocha
C = {
    "bg":        ( 30,  30,  46),   # base
    "surface":   ( 36,  36,  54),   # mantle
    "card":      ( 49,  50,  68),   # surface0
    "card2":     ( 58,  60,  78),   # surface1
    "border":    ( 69,  71,  90),   # surface2
    "border_hi": (137, 180, 250),   # blue
    "amber":     (250, 179, 135),   # peach
    "amber_dim": (180, 120,  80),   # peach dimmed
    "cyan":      (137, 220, 235),   # sky
    "cyan_dim":  ( 60, 110, 120),   # sky dimmed
    "green":     (166, 227, 161),   # green
    "red":       (243, 139, 168),   # red
    "text":      (205, 214, 244),   # text
    "text_dim":  (108, 112, 134),   # overlay0
    "text_hi":   (245, 224, 220),   # rosewater
    "wait_cell": ( 49,  50,  68),   # surface0
    "row_a":     ( 36,  36,  54),   # mantle
    "row_b":     ( 42,  42,  60),   # between mantle and surface0
}

# Catppuccin Mocha accent colors for processes
PROC_COLORS = [
    (243, 139, 168),   # red
    (137, 180, 250),   # blue
    (166, 227, 161),   # green
    (250, 179, 135),   # peach
    (203, 166, 247),   # mauve
    (137, 220, 235),   # sky
    (245, 194, 231),   # pink
    (249, 226, 175),   # yellow
]

# ═══════════════════════════════════════════════════════════════════════════════
#  FUENTES
# ═══════════════════════════════════════════════════════════════════════════════
F_HUGE  = pygame.font.SysFont("consolas", 32, bold=True)
F_TITLE = pygame.font.SysFont("consolas", 20, bold=True)
F_HEAD  = pygame.font.SysFont("consolas", 14, bold=True)
F_BODY  = pygame.font.SysFont("consolas", 13)
F_MONO  = pygame.font.SysFont("consolas", 12)
F_SMALL = pygame.font.SysFont("consolas", 11)
F_TINY  = pygame.font.SysFont("consolas", 10)

# ═══════════════════════════════════════════════════════════════════════════════
#  ALGORITMOS
# ═══════════════════════════════════════════════════════════════════════════════

def sjf(procs):
    remaining = {p[0]: p[2] for p in procs}
    done, finish, start_time, gantt = set(), {}, {}, []
    clock = 0
    proc_list = sorted(procs, key=lambda x: x[1])
    while len(done) < len(procs):
        available = [p for p in proc_list if p[1] <= clock and p[0] not in done]
        if not available:
            clock += 1
            continue
        chosen = min(available, key=lambda p: (remaining[p[0]], p[3]))
        pid = chosen[0]
        idx = next(i for i, p in enumerate(procs) if p[0] == pid)
        if pid not in start_time:
            start_time[pid] = clock
        t0 = clock
        clock += remaining[pid]
        remaining[pid] = 0
        done.add(pid)
        finish[pid] = clock
        gantt.append((pid, t0, clock, idx))
    metrics = {}
    for p in procs:
        pid, tll, tr, pd = p
        metrics[pid] = (max(0, finish[pid] - tll - tr), max(0, start_time[pid] - tll))
    return gantt, metrics


def srtf(procs):
    remaining = {p[0]: p[2] for p in procs}
    finish, start_first, gantt = {}, {}, []
    done = set()
    clock = 0
    last_pid = None
    seg_start = 0
    max_t = sum(p[2] for p in procs) + max(p[1] for p in procs) + 5
    while len(done) < len(procs) and clock < max_t:
        available = [p for p in procs if p[1] <= clock and p[0] not in done]
        if not available:
            clock += 1
            continue
        chosen = min(available, key=lambda p: (remaining[p[0]], p[3]))
        pid = chosen[0]
        idx = next(i for i, p in enumerate(procs) if p[0] == pid)
        if pid not in start_first:
            start_first[pid] = clock
        if last_pid != pid:
            if last_pid is not None:
                lidx = next(i for i, p in enumerate(procs) if p[0] == last_pid)
                gantt.append((last_pid, seg_start, clock, lidx))
            seg_start = clock
            last_pid = pid
        remaining[pid] -= 1
        clock += 1
        if remaining[pid] == 0:
            done.add(pid)
            finish[pid] = clock
            gantt.append((pid, seg_start, clock, idx))
            last_pid = None
            seg_start = clock
    metrics = {}
    for p in procs:
        pid, tll, tr, pd = p
        metrics[pid] = (max(0, finish[pid] - tll - tr), max(0, start_first[pid] - tll))
    return gantt, metrics


def priority_sched(procs):
    remaining = {p[0]: p[2] for p in procs}
    done, finish, start_time, gantt = set(), {}, {}, []
    clock = 0
    proc_list = sorted(procs, key=lambda x: x[1])
    while len(done) < len(procs):
        available = [p for p in proc_list if p[1] <= clock and p[0] not in done]
        if not available:
            clock += 1
            continue
        chosen = min(available, key=lambda p: (p[3], remaining[p[0]]))
        pid = chosen[0]
        idx = next(i for i, p in enumerate(procs) if p[0] == pid)
        if pid not in start_time:
            start_time[pid] = clock
        t0 = clock
        clock += remaining[pid]
        remaining[pid] = 0
        done.add(pid)
        finish[pid] = clock
        gantt.append((pid, t0, clock, idx))
    metrics = {}
    for p in procs:
        pid, tll, tr, pd = p
        metrics[pid] = (max(0, finish[pid] - tll - tr), max(0, start_time[pid] - tll))
    return gantt, metrics


def round_robin(procs, quantum=2):
    remaining = {p[0]: p[2] for p in procs}
    finish, start_first, gantt = {}, {}, []
    done = set()
    clock = 0
    queue = []
    added = set()
    proc_list = sorted(procs, key=lambda x: (x[1], x[3]))
    for p in proc_list:
        if p[1] == 0:
            queue.append(p)
            added.add(p[0])
    max_t = sum(p[2] for p in procs) + max(p[1] for p in procs) + 10
    while len(done) < len(procs) and clock < max_t:
        if not queue:
            clock += 1
            for p in proc_list:
                if p[1] <= clock and p[0] not in done and p[0] not in added:
                    queue.append(p)
                    added.add(p[0])
            continue
        proc = queue.pop(0)
        pid = proc[0]
        idx = next(i for i, p in enumerate(procs) if p[0] == pid)
        if pid not in start_first:
            start_first[pid] = clock
        exec_t = min(quantum, remaining[pid])
        t0 = clock
        clock += exec_t
        remaining[pid] -= exec_t
        new_arr = sorted(
            [p for p in proc_list if p[1] <= clock and p[0] not in done and p[0] not in added],
            key=lambda x: (x[1], x[3])
        )
        for p in new_arr:
            added.add(p[0])
        gantt.append((pid, t0, clock, idx))
        if remaining[pid] == 0:
            done.add(pid)
            finish[pid] = clock
            queue.extend(new_arr)
        else:
            queue.extend(new_arr)
            queue.append(proc)
    metrics = {}
    for p in procs:
        pid, tll, tr, pd = p
        metrics[pid] = (max(0, finish[pid] - tll - tr), max(0, start_first[pid] - tll))
    return gantt, metrics


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS DE DIBUJO
# ═══════════════════════════════════════════════════════════════════════════════

def draw_rrect(surf, color, rect, r=6, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if border:
        pygame.draw.rect(surf, border_color or C["border"], rect, border, border_radius=r)


def txt(surf, s, font, color, x, y, anchor="tl"):
    img = font.render(str(s), True, color)
    w, h = img.get_size()
    ox = {"tl": 0, "tc": -w // 2, "tr": -w,
          "cl": 0, "cc": -w // 2, "cr": -w}.get(anchor, 0)
    oy = {"tl": 0, "tc": 0, "tr": 0,
          "cl": -h // 2, "cc": -h // 2, "cr": -h // 2}.get(anchor, 0)
    surf.blit(img, (x + ox, y + oy))
    return w, h


def glow(surf, color, rect, r=6, alpha=55):
    s = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color[:3], alpha), s.get_rect(), border_radius=r + 5)
    surf.blit(s, (rect.x - 8, rect.y - 8))


# ═══════════════════════════════════════════════════════════════════════════════
#  BOTÓN
# ═══════════════════════════════════════════════════════════════════════════════

class Btn:
    def __init__(self, rect, label, cn, ch, ca=None, tc=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.cn, self.ch = cn, ch
        self.ca = ca or ch
        self.tc = tc or C["text_hi"]
        self.hovered = self.active = False

    def draw(self, surf):
        c = self.ca if self.active else (self.ch if self.hovered else self.cn)
        if self.hovered or self.active:
            glow(surf, c, self.rect, alpha=45)
        draw_rrect(surf, c, self.rect, 6)
        bc = C["amber"] if self.active else (C["border_hi"] if self.hovered else C["border"])
        pygame.draw.rect(surf, bc, self.rect, 1, border_radius=6)
        txt(surf, self.label, F_HEAD, self.tc,
            self.rect.centerx, self.rect.centery, "cc")

    def update(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

    def hit(self, mx, my):
        return self.rect.collidepoint(mx, my)


# ═══════════════════════════════════════════════════════════════════════════════
#  TOOLTIP
# ═══════════════════════════════════════════════════════════════════════════════

class Tooltip:
    def __init__(self):
        self.msg = ""
        self.x = self.y = 0
        self.on = False

    def show(self, msg, x, y):
        self.msg, self.x, self.y, self.on = msg, x, y, True

    def hide(self):
        self.on = False

    def draw(self, surf):
        if not self.on or not self.msg:
            return
        w, h = F_SMALL.size(self.msg)
        pad = 6
        bx = min(self.x + 14, surf.get_width() - w - pad * 2 - 4)
        by = self.y - h - pad * 2 - 4
        box = pygame.Rect(bx, by, w + pad * 2, h + pad * 2)
        draw_rrect(surf, C["card2"], box, 4, 1, C["amber_dim"])
        txt(surf, self.msg, F_SMALL, C["amber"], box.x + pad, box.y + pad)


# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_PROCS = [
    ("P1", 1, 3, 1),
    ("P2", 2, 3, 4),
    ("P3", 3, 4, 2),
    ("P4", 1, 4, 1),
    ("P5", 4, 2, 3),
    ("P6", 0, 6, 7),
]

ALGO_NAMES = ["SJF", "SRTF", "Prioridades", "Round Robin"]
ALGO_DESC = [
    "Shortest Job First — no expulsivo",
    "Shortest Remaining Time First — expulsivo",
    "Planificación por Prioridad — no expulsivo",
    "Round Robin — quantum configurable",
]

COL_LABELS = ["P", "TLL", "TR", "PD"]
COL_TIPS = [
    "Nombre del proceso",
    "Tiempo de llegada (Arrival Time)",
    "Tiempo de ráfaga / Burst Time",
    "Prioridad — menor valor = mayor prioridad",
]
COL_W = [60, 64, 64, 64]

TABLE_W   = 316
SEP       = 12
CONTENT_Y = 72
ROW_H     = 32
ROWS_START_OFFSET = 52   # offset desde panel.y hasta primera fila de datos


# ═══════════════════════════════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════════════════════════════

class App:
    def __init__(self):
        self.W, self.H = 1340, 830
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.RESIZABLE)
        pygame.display.set_caption("CPU Scheduler Simulator")
        self.clk = pygame.time.Clock()

        self.processes = list(DEFAULT_PROCS)
        self.algo_idx  = 0
        self.quantum   = 2
        self.gantt     = []
        self.metrics   = {}

        self.editing   = None
        self.edit_buf  = ""
        self.edit_err  = False

        self.sim_flash = 0

        self.tooltip = Tooltip()
        self._build_btns()
        self._simulate()

    # ── botones ───────────────────────────────────────────────────────────────
    def _build_btns(self):
        self.btn_algos = [
            Btn((338 + i * 158, 14, 151, 36), name,
                C["card"], C["card2"])
            for i, name in enumerate(ALGO_NAMES)
        ]
        self.btn_qminus = Btn((1010, 14, 32, 36), "−", C["card"], C["card2"])
        self.btn_qplus  = Btn((1090, 14, 32, 36), "+", C["card"], C["card2"])
        self.btn_run    = Btn((0, 14, 162, 36), "▶  SIMULAR",
                             (18, 58, 28), (24, 88, 44), (30, 108, 52),
                             tc=C["green"])
        self.btn_add    = Btn((0, 0, 140, 28), "+ Proceso",
                             (18, 46, 22), (24, 66, 30), tc=C["green"])
        self.btn_del    = Btn((0, 0, 140, 28), "− Eliminar",
                             (50, 16, 16), (70, 22, 22), tc=(255, 110, 110))

    def _simulate(self):
        if not self.processes:
            self.gantt, self.metrics = [], {}
            return
        p = self.processes
        fns = [sjf, srtf, priority_sched, lambda p: round_robin(p, self.quantum)]
        self.gantt, self.metrics = fns[self.algo_idx](p)
        self.sim_flash = 20

    # ═════════════════════════════════════════════════════════════════════════
    #  DRAW
    # ═════════════════════════════════════════════════════════════════════════
    def draw(self):
        W, H = self.screen.get_size()
        self.screen.fill(C["bg"])

        # grid background
        for gx in range(0, W, 40):
            pygame.draw.line(self.screen, (16, 20, 32), (gx, 0), (gx, H))
        for gy in range(0, H, 40):
            pygame.draw.line(self.screen, (16, 20, 32), (0, gy), (W, gy))

        # ── HEADER ────────────────────────────────────────────────────────────
        pygame.draw.rect(self.screen, C["surface"], (0, 0, W, 64))
        pygame.draw.line(self.screen, C["amber_dim"], (0, 64), (W, 64))
        txt(self.screen, "⬡", F_HUGE, C["amber"], 16, 32, "cl")
        txt(self.screen, "CPU SCHEDULER", F_TITLE, C["amber"], 50, 15)
        txt(self.screen, "simulator — SJF · SRTF · Prioridades · Round Robin",
            F_SMALL, C["text_dim"], 52, 38)
        txt(self.screen, "v2.0", F_TINY, C["amber_dim"], 52, 52)

        # botones algoritmo
        for i, b in enumerate(self.btn_algos):
            is_active = (i == self.algo_idx)
            if is_active:
                glow(self.screen, C["amber"], b.rect, alpha=50)
                draw_rrect(self.screen, (48, 36, 6), b.rect, 6)
                pygame.draw.rect(self.screen, C["amber"], b.rect, 1, border_radius=6)
                txt(self.screen, b.label, F_HEAD, C["amber"],
                    b.rect.centerx, b.rect.centery, "cc")
            else:
                b.draw(self.screen)

        # quantum
        qx = 1010
        txt(self.screen, "Q=", F_HEAD, C["text_dim"], qx - 36, 32, "cl")
        self.btn_qminus.rect = pygame.Rect(qx, 14, 32, 36)
        self.btn_qplus.rect  = pygame.Rect(qx + 78, 14, 32, 36)
        self.btn_qminus.draw(self.screen)
        self.btn_qplus.draw(self.screen)
        qbox = pygame.Rect(qx + 34, 14, 42, 36)
        qc = C["amber"] if self.algo_idx == 3 else C["text_dim"]
        draw_rrect(self.screen, C["card"], qbox, 4, 1, C["border"])
        txt(self.screen, str(self.quantum), F_TITLE, qc,
            qbox.centerx, qbox.centery, "cc")

        # botón SIMULAR (anclado a la derecha)
        self.btn_run.rect = pygame.Rect(W - 176, 14, 163, 36)
        if self.sim_flash > 0:
            glow(self.screen, C["green"], self.btn_run.rect, alpha=90)
            self.sim_flash -= 1
        self.btn_run.draw(self.screen)

        # ── PANEL IZQUIERDO — TABLA ───────────────────────────────────────────
        panel = pygame.Rect(10, CONTENT_Y, TABLE_W, H - CONTENT_Y - 10)
        draw_rrect(self.screen, C["surface"], panel, 8, 1, C["border"])

        # cabecera tabla
        thead = pygame.Rect(panel.x, panel.y, panel.w, 30)
        draw_rrect(self.screen, C["card2"], thead, 8)
        pygame.draw.rect(self.screen, C["card2"],
                         pygame.Rect(panel.x, panel.y + 14, panel.w, 16))
        pygame.draw.line(self.screen, C["border"],
                         (panel.x, panel.y + 30), (panel.x + panel.w, panel.y + 30))

        CW = COL_W
        cx0 = [panel.x + 14]
        for w in CW[:-1]:
            cx0.append(cx0[-1] + w)

        for lab, cx in zip(COL_LABELS, cx0):
            txt(self.screen, lab, F_HEAD, C["cyan"], cx + 4, panel.y + 8)

        # subtítulo
        txt(self.screen,
            "TLL=llegada   TR=ráfaga   PD=prioridad",
            F_TINY, C["text_dim"], panel.x + 8, panel.y + 34)

        ROWS_Y = panel.y + ROWS_START_OFFSET
        for ri, proc in enumerate(self.processes):
            ry = ROWS_Y + ri * ROW_H
            rbg = C["row_a"] if ri % 2 == 0 else C["row_b"]
            draw_rrect(self.screen, rbg,
                       pygame.Rect(panel.x + 4, ry + 1, panel.w - 8, ROW_H - 2), 4)
            pc = PROC_COLORS[ri % len(PROC_COLORS)]
            pygame.draw.rect(self.screen, pc,
                             pygame.Rect(panel.x + 4, ry + 1, 4, ROW_H - 2),
                             border_radius=2)

            for ci, (val, cx) in enumerate(zip(proc, cx0)):
                if self.editing == (ri, ci):
                    erect = pygame.Rect(cx + 2, ry + 5, CW[ci] - 6, ROW_H - 10)
                    bc = C["red"] if self.edit_err else C["cyan"]
                    draw_rrect(self.screen, C["bg"], erect, 3, 2, bc)
                    blink = "_" if pygame.time.get_ticks() // 500 % 2 == 0 else " "
                    txt(self.screen, self.edit_buf + blink, F_BODY, bc, cx + 5, ry + 8)
                else:
                    txt(self.screen, str(val), F_BODY, C["text"], cx + 6, ry + 8)

        # botones Add / Del
        btn_y = ROWS_Y + len(self.processes) * ROW_H + 8
        self.btn_add.rect = pygame.Rect(panel.x + 6, btn_y, 140, 28)
        self.btn_del.rect = pygame.Rect(panel.x + 154, btn_y, 140, 28)
        self.btn_add.draw(self.screen)
        self.btn_del.draw(self.screen)

        # instrucciones
        iy = btn_y + 36
        for line in [
            "↑ Clic en celda para editar valor",
            "  Enter = confirmar  |  Tab = siguiente",
            "  Esc = cancelar",
            "",
            "▶ SIMULAR aplica todos los cambios",
            "  y recalcula el diagrama.",
        ]:
            c = C["amber_dim"] if "SIMULAR" in line else C["text_dim"]
            txt(self.screen, line, F_TINY, c, panel.x + 8, iy)
            iy += 14

        # separador vertical
        sx = TABLE_W + 18
        pygame.draw.line(self.screen, C["border"], (sx, CONTENT_Y + 4), (sx, H - 14))

        # ── PANEL DERECHO ─────────────────────────────────────────────────────
        RX = sx + SEP
        RW = W - RX - 12

        if not self.gantt:
            txt(self.screen,
                "Sin datos — agrega procesos y pulsa  ▶ SIMULAR",
                F_BODY, C["text_dim"], RX + 20, CONTENT_Y + 40)
            self.tooltip.draw(self.screen)
            pygame.display.flip()
            return

        max_t   = max(seg[2] for seg in self.gantt)
        n_procs = len(self.processes)

        # ── DIAGRAMA DE GANTT ─────────────────────────────────────────────────
        algo_label = ALGO_NAMES[self.algo_idx]
        txt(self.screen, "DIAGRAMA DE GANTT", F_HEAD, C["cyan"], RX, CONTENT_Y)
        txt(self.screen, f"  [{ALGO_DESC[self.algo_idx]}]",
            F_SMALL, C["text_dim"],
            RX + F_HEAD.size("DIAGRAMA DE GANTT")[0] + 4, CONTENT_Y + 2)

        GY     = CONTENT_Y + 22
        CELL_H = 26
        RGAP   = 4
        PID_W  = 40

        avail = RW - PID_W - 4
        cell_w = max(10, min(30, avail // (max_t + 1)))
        GANTT_TOTAL_H = n_procs * (CELL_H + RGAP) + 30

        gbg = pygame.Rect(RX - 4, GY - 4, PID_W + max_t * cell_w + 8, GANTT_TOTAL_H + 4)
        draw_rrect(self.screen, C["surface"], gbg, 8, 1, C["border"])

        for ri, pid in enumerate([p[0] for p in self.processes]):
            ry = GY + ri * (CELL_H + RGAP)
            pc = PROC_COLORS[ri % len(PROC_COLORS)]
            txt(self.screen, pid, F_MONO, pc, RX + PID_W // 2, ry + CELL_H // 2, "cc")

            segs = [(s, e) for (p, s, e, _) in self.gantt if p == pid]

            # fondo espera
            pygame.draw.rect(self.screen, C["wait_cell"],
                             pygame.Rect(RX + PID_W, ry, max_t * cell_w, CELL_H),
                             border_radius=2)

            # segmentos activos
            for s, e in segs:
                cx = RX + PID_W + s * cell_w
                cw = (e - s) * cell_w
                cr = pygame.Rect(cx + 1, ry + 1, cw - 2, CELL_H - 2)
                draw_rrect(self.screen, pc, cr, 3)
                shine = pygame.Surface((cw - 2, 5), pygame.SRCALPHA)
                shine.fill((255, 255, 255, 35))
                self.screen.blit(shine, (cx + 1, ry + 1))
                if cw > 20:
                    txt(self.screen, pid, F_TINY, C["bg"],
                        cx + cw // 2, ry + CELL_H // 2, "cc")

            # marca TLL
            tll = self.processes[ri][1]
            tx = RX + PID_W + tll * cell_w
            pygame.draw.line(self.screen, C["amber"],
                             (tx, ry), (tx, ry + CELL_H), 2)

        # eje de tiempo
        CLK_Y = GY + n_procs * (CELL_H + RGAP) + 2
        step = max(1, max_t // 26)
        for t in range(0, max_t + 1, step):
            tx = RX + PID_W + t * cell_w
            pygame.draw.line(self.screen, C["border"], (tx, CLK_Y), (tx, CLK_Y + 5))
            txt(self.screen, str(t), F_TINY, C["text_dim"], tx, CLK_Y + 7, "tc")
        lx = RX + PID_W + max_t * cell_w
        pygame.draw.line(self.screen, C["cyan"], (lx, CLK_Y), (lx, CLK_Y + 5))
        txt(self.screen, str(max_t), F_TINY, C["cyan"], lx, CLK_Y + 7, "tc")

        # leyenda
        LEG_Y = CLK_Y + 22
        pygame.draw.rect(self.screen, C["amber"], (RX, LEG_Y + 5, 3, 12))
        txt(self.screen, "= llegada (TLL)", F_TINY, C["amber_dim"], RX + 6, LEG_Y + 4)
        pygame.draw.rect(self.screen, C["wait_cell"],
                         (RX + 130, LEG_Y + 4, 16, 12), border_radius=2)
        txt(self.screen, "= en espera", F_TINY, C["text_dim"], RX + 150, LEG_Y + 4)

        # ── MÉTRICAS ──────────────────────────────────────────────────────────
        MET_Y = GY + GANTT_TOTAL_H + 36
        txt(self.screen, "MÉTRICAS DE RENDIMIENTO", F_HEAD, C["cyan"], RX, MET_Y - 18)

        # separador
        pygame.draw.line(self.screen, C["cyan_dim"],
                         (RX - 4, MET_Y - 4), (RX + 340, MET_Y - 4))

        MCX = [RX + 4, RX + 72, RX + 200]
        # cabecera
        mhdr = pygame.Rect(RX - 4, MET_Y, 344, 26)
        draw_rrect(self.screen, C["card2"], mhdr, 6)
        pygame.draw.line(self.screen, C["cyan"],
                         (RX - 4, MET_Y + 26), (RX + 340, MET_Y + 26))
        for lab, cx in zip(["Proceso", "T. Espera", "T. Respuesta"], MCX):
            txt(self.screen, lab, F_HEAD, C["cyan"], cx, MET_Y + 5)

        sum_te = sum_tr = 0
        n = len(self.processes)
        for ri, proc in enumerate(self.processes):
            pid = proc[0]
            if pid not in self.metrics:
                continue
            te, tr_m = self.metrics[pid]
            sum_te += te
            sum_tr += tr_m
            my = MET_Y + 28 + ri * 24
            rbg = C["row_a"] if ri % 2 == 0 else C["row_b"]
            draw_rrect(self.screen, rbg,
                       pygame.Rect(RX - 4, my + 1, 344, 22), 4)
            pc = PROC_COLORS[ri % len(PROC_COLORS)]
            pygame.draw.rect(self.screen, pc,
                             pygame.Rect(RX - 4, my + 1, 3, 22), border_radius=1)
            txt(self.screen, pid,    F_BODY, C["text"],  MCX[0], my + 4)
            txt(self.screen, str(te), F_MONO, C["amber"], MCX[1], my + 4)
            txt(self.screen, str(tr_m), F_MONO, C["cyan"], MCX[2], my + 4)

        # promedio
        if n:
            avg_y = MET_Y + 28 + n * 24 + 4
            draw_rrect(self.screen, (38, 48, 28),
                       pygame.Rect(RX - 4, avg_y, 344, 26), 5, 1, C["amber_dim"])
            txt(self.screen, "PROMEDIO", F_HEAD, C["amber_dim"], MCX[0], avg_y + 5)
            txt(self.screen, f"{sum_te / n:.3f}", F_HEAD, C["amber"], MCX[1], avg_y + 5)
            txt(self.screen, f"{sum_tr / n:.3f}", F_HEAD, C["cyan"],  MCX[2], avg_y + 5)

        # ── BARRA DE ESTADO ────────────────────────────────────────────────────
        sbar_y = H - 22
        pygame.draw.line(self.screen, C["border"], (0, sbar_y), (W, sbar_y))
        pygame.draw.rect(self.screen, C["surface"], pygame.Rect(0, sbar_y, W, 22))
        info = (
            f"  Procesos: {n}  |  Algoritmo: {ALGO_NAMES[self.algo_idx]}"
            + (f"  Q={self.quantum}" if self.algo_idx == 3 else "")
            + f"  |  Tiempo total: {max_t} u.t."
            + f"  |  Prom. espera: {sum_te / n:.3f}"
            + f"  |  Prom. respuesta: {sum_tr / n:.3f}"
        )
        txt(self.screen, info, F_TINY, C["text_dim"], 0, sbar_y + 5)

        self.tooltip.draw(self.screen)
        pygame.display.flip()

    # ═════════════════════════════════════════════════════════════════════════
    #  EVENTOS
    # ═════════════════════════════════════════════════════════════════════════
    def handle_events(self):
        mx, my = pygame.mouse.get_pos()
        self.tooltip.hide()

        for b in self.btn_algos:
            b.update(mx, my)
            if b.hovered:
                i = self.btn_algos.index(b)
                self.tooltip.show(ALGO_DESC[i], mx, my)

        for b in [self.btn_qminus, self.btn_qplus, self.btn_run,
                  self.btn_add, self.btn_del]:
            b.update(mx, my)

        if self.btn_run.hovered:
            self.tooltip.show("Aplica cambios y recalcula el diagrama", mx, my)
        if self.btn_qminus.hovered or self.btn_qplus.hovered:
            self.tooltip.show("Quantum para Round Robin", mx, my)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.VIDEORESIZE:
                self.W, self.H = event.w, event.h
                self.screen = pygame.display.set_mode(
                    (self.W, self.H), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if self.editing is not None:
                    ri, ci = self.editing
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.commit_edit()
                        self._simulate()
                    elif event.key == pygame.K_TAB:
                        self.commit_edit()
                        nc = (ci + 1) % 4
                        self.editing = (ri, nc)
                        self.edit_buf = str(self.processes[ri][nc])
                        self.edit_err = False
                    elif event.key == pygame.K_ESCAPE:
                        self.editing = None
                        self.edit_buf = ""
                        self.edit_err = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.edit_buf = self.edit_buf[:-1]
                    else:
                        if event.unicode:
                            self.edit_buf += event.unicode
                            self.edit_err = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._click(mx, my)

    def _click(self, mx, my):
        if self.editing is not None:
            self.commit_edit()

        # algoritmos
        for i, b in enumerate(self.btn_algos):
            if b.hit(mx, my):
                self.algo_idx = i
                self._simulate()
                return

        # quantum
        if self.btn_qminus.hit(mx, my):
            self.quantum = max(1, self.quantum - 1)
            self._simulate()
            return
        if self.btn_qplus.hit(mx, my):
            self.quantum += 1
            self._simulate()
            return

        # SIMULAR — re-ejecuta con estado actual
        if self.btn_run.hit(mx, my):
            self._simulate()
            return

        # agregar / eliminar proceso
        if self.btn_add.hit(mx, my):
            n = len(self.processes) + 1
            self.processes.append((f"P{n}", 0, 1, 1))
            self._simulate()
            return
        if self.btn_del.hit(mx, my) and self.processes:
            self.processes.pop()
            self._simulate()
            return

        # clic en celda de tabla
        ROWS_Y = CONTENT_Y + ROWS_START_OFFSET
        panel_x = 10
        cx0 = [panel_x + 14]
        for w in COL_W[:-1]:
            cx0.append(cx0[-1] + w)

        for ri, proc in enumerate(self.processes):
            ry = ROWS_Y + ri * ROW_H
            for ci, cx in enumerate(cx0):
                cell = pygame.Rect(cx + 2, ry + 5, COL_W[ci] - 6, ROW_H - 10)
                if cell.collidepoint(mx, my):
                    self.editing = (ri, ci)
                    self.edit_buf = str(proc[ci])
                    self.edit_err = False
                    return

    def commit_edit(self):
        if self.editing is None:
            return
        ri, ci = self.editing
        proc = list(self.processes[ri])
        val = self.edit_buf.strip()
        if ci == 0:
            if val:
                proc[0] = val
        else:
            try:
                v = int(val)
                proc[ci] = max(1 if ci == 2 else 0, v)
                self.edit_err = False
            except ValueError:
                self.edit_err = True
                self.editing = None
                self.edit_buf = ""
                return
        self.processes[ri] = tuple(proc)
        self.editing = None
        self.edit_buf = ""

    # ═════════════════════════════════════════════════════════════════════════
    #  LOOP
    # ═════════════════════════════════════════════════════════════════════════
    def run(self):
        while True:
            self.handle_events()
            self.draw()
            self.clk.tick(60)


if __name__ == "__main__":
    app = App()
    app.run()
