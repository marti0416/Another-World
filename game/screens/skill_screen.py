"""
skill_screen.py — Screen della ruota delle skill (State GoF).

Visualizza le skill del personaggio attivo con stato di sblocco, cooldown e
costo in tech points. Permette di usare le skill fuori dal combattimento.
"""

import pygame
import math
from game.screens.base_screen import Screen
from game.world.world_data import W, H, CYAN, GREY, GREEN, WHITE, RED, MAGENTA
from game.controller.game_manager import GameManager

_DARK_BG      = (6,  8, 14)
_PANEL_BG     = (12, 16, 26)
_RING_DIM     = (30, 45, 60)
_RING_BRIGHT  = (0, 160, 200)
_LOCKED_NODE  = (70, 18, 18)
_LOCKED_RIM   = (140, 35, 35)
_UNLOCKED_NODE= (10, 70, 20)
_UNLOCKED_RIM = GREEN
_GLOW_GREEN   = (57, 255, 20)
_GLOW_CYAN    = (0, 229, 255)
_GOLD         = (255, 200, 50)
_DIM_TEXT     = (90, 110, 130)

_SKILL_DESC = {
    "Schianto Brutale":        ("Combattimento", "Colpo devastante su bersaglio casuale. Danno ATK×1.5. Prob. dipende da ATK (50%→100%). CD 1."),
    "Sintesi Tossicologica":   ("Passiva · Crafting", "Sblocca kit medico avanzato, antibiotici e Acid Gun nel banco da lavoro."),
    "Rattoppo d'Emergenza":    ("Combattimento", "Ripara le ferite sul campo. Recupera HP. Prob. dipende da DEF (35%→100%). 1× per battaglia."),
    "Esperto di Esplosivi":    ("Passiva · Crafting", "Sblocca Esplosivo da Battaglia, C4, Granata Flash, Granata Antimateria."),
    "Onda al Plasma":          ("Combattimento", "Colpisce il nemico con più HP di ATK×1.5 e tutti gli altri di ATK. Prob. da ATK (75%→100%). CD 2."),
    "Ingegneria Bellica":      ("Passiva · Crafting", "Sblocca Fucile d'Assalto Pesante, Designatore Artiglieria, Cannone a Rail, Missile Incendiario."),
    "Punto di Fusione":        ("Combattimento", "Plasma totale: ATK×3 al nemico con più HP, ATK×1.5 agli altri. Prob. da ATK (85%→100%). 1× per battaglia."),
    "Sintesi Instabile":       ("Passiva · Crafting", "Sblocca Termite e Soluzione Piranha. Sintesi pericolose ad alto rendimento."),
    "Manovra Evasiva":         ("Combattimento", "Schiva il prossimo attacco nemico. Prob. dipende da DEF (50%→100%). CD 1."),
    "Hacking Veloce":          ("Passiva · Hacking", "Dimezza il lockout in caso di errori durante l'hacking. Si sblocca dopo il primo terminale hackerato."),
    "Interferenza Cognitiva":  ("Combattimento", "Confonde il nemico per 1 turno. Prob. dipende da DEF (75%→100%). CD 2."),
    "Espansione di Banda":     ("Passiva · Hacking", "Sblocca connessioni avanzate nei circuiti di hacking."),
    "Miraggio Tattico":        ("Combattimento", "Confonde il nemico per 1 turno + 35% di infliggere ATK danno. Prob. da DEF (75%→100%). 1× per battaglia."),
    "Override Radar":          ("Passiva · Hacking", "Mostra la posizione di tutti i nemici sulla mappa radar."),
    "Cortocircuito Sinaptico": ("Combattimento", "ATK×2.5 danni + Shock (turno saltato) per 1 turno. Prob. da DEF+ATK (85%→100%). CD 3."),
    "Decrittazione Automatica":("Passiva · Hacking", "Permette di bypassare nodi protetti senza affrontare il puzzle."),
}


def _a(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _glow(surf, color, center, glow_r, alpha_max=110):
    cx, cy = int(center[0]), int(center[1])
    for i in range(6, 0, -1):
        r = int(glow_r * i / 6)
        a = int(alpha_max * (1 - i / 7))
        s = _a(r*2+2, r*2+2)
        pygame.draw.circle(s, (*color, a), (r+1, r+1), r)
        surf.blit(s, (cx-r-1, cy-r-1))


def _arc_dashes(surf, color, center, radius, n=36):
    cx, cy = center
    step = math.pi * 2 / (n * 2)
    for i in range(n):
        a0 = i * 2 * step
        a1 = a0 + step
        pts = [(cx + radius*math.cos(a0+(a1-a0)*t/7),
                cy + radius*math.sin(a0+(a1-a0)*t/7)) for t in range(8)]
        pygame.draw.lines(surf, color, False, pts, 1)


def _hex_bg(surf, cx, cy):
    size = 34
    dx = size * math.sqrt(3)
    dy = size * 1.5
    cols, rows = 22, 14
    ox = cx - cols * dx / 2
    oy = cy - rows * dy / 2
    color = (20, 30, 45)
    for row in range(rows+1):
        for col in range(cols+1):
            x = ox + col*dx + (dx/2 if row % 2 else 0)
            y = oy + row*dy
            pts = [(x + size*0.92*math.cos(math.pi/6 + math.pi/3*k),
                    y + size*0.92*math.sin(math.pi/6 + math.pi/3*k)) for k in range(6)]
            pygame.draw.polygon(surf, color, pts, 1)


def _brackets(surf, rect, color, sz=14, w=2):
    x, y, rw, rh = rect
    for pts in [[(x,y+sz),(x,y),(x+sz,y)],
                [(x+rw-sz,y),(x+rw,y),(x+rw,y+sz)],
                [(x,y+rh-sz),(x,y+rh),(x+sz,y+rh)],
                [(x+rw-sz,y+rh),(x+rw,y+rh),(x+rw,y+rh-sz)]]:
        pygame.draw.lines(surf, color, False, pts, w)


def _lerp(c1, c2, t):
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))


def _wrap_text(text, font, max_w):
    """Spezza il testo in righe che entrano in max_w pixel."""
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if font.size(test)[0] <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


class SkillWheelScreen(Screen):
    def __init__(self, fonts):
        self.fonts = fonts
        self.active_char_name = "Rivet"
        self._tick    = 0
        self._pulse   = 0.0
        self._hovered = -1
        self._mouse   = (0, 0)

    def handle_event(self, event):
        gs = GameManager.get_instance()
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_r, pygame.K_ESCAPE):
                gs.screen = "explore"
            elif event.key == pygame.K_TAB:
                self.active_char_name = "Echo" if self.active_char_name == "Rivet" else "Rivet"
        elif event.type == pygame.MOUSEMOTION:
            self._mouse = event.pos

    def update(self):
        self._tick += 1
        self._pulse = math.sin(self._tick * 0.04) * 0.5 + 0.5

    def draw(self, surf: pygame.Surface):
        gs     = GameManager.get_instance()
        char   = gs.Rivet if self.active_char_name == "Rivet" else gs.Echo
        stats  = char.stats
        wheel  = char.skill_wheel
        skills = list(wheel)

        surf.fill(_DARK_BG)
        cx, cy = W // 2, H // 2 + 15
        _hex_bg(surf, cx, cy)

        vign = _a(W, H)
        for i in range(8):
            r = int(W * 0.85 * (1 - i/8))
            a = int(80 * i/8)
            pygame.draw.ellipse(vign, (0,0,0,a),
                                (W//2-r, H//2-int(r*0.65), r*2, int(r*1.3)))
        surf.blit(vign, (0, 0))

        char_color = _GLOW_CYAN if self.active_char_name == "Rivet" else MAGENTA

        hdr = (W//2-320, 12, 640, 115)
        hb = _a(640, 115); hb.fill((10,18,30,200))
        surf.blit(hb, (hdr[0], hdr[1]))
        _brackets(surf, hdr, _RING_BRIGHT)

        pygame.draw.line(surf, _RING_BRIGHT, (W//2-260, 76), (W//2+260, 76), 1)

        t = self.fonts["xl"].render(f"RUOTA DELLE ABILITÀ  -  {char.name.upper()}", True, char_color)
        surf.blit(t, t.get_rect(center=(W//2, 40)))

        s = self.fonts["sm"].render(
            f"LVL {stats.level}    ATK {stats.atk}    DEF {stats.defense}    TECH {stats.tech_points}",
            True, _DIM_TEXT)
        surf.blit(s, s.get_rect(center=(W//2, 96)))

        hint = self.fonts["sm"].render("Passa il cursore su un nodo per i dettagli", True, _DIM_TEXT)
        surf.blit(hint, hint.get_rect(center=(W//2, 155)))

        if not skills:
            return

        radius     = 175
        node_r     = 28
        num        = len(skills)
        angle_step = 2 * math.pi / num

        positions = []
        hovered   = -1
        mx, my    = self._mouse
        for i in range(num):
            angle = i * angle_step - math.pi / 2
            nx = cx + radius * math.cos(angle)
            ny = cy + radius * math.sin(angle)
            positions.append((nx, ny, angle))
            dist = math.hypot(mx - nx, my - ny)
            if dist <= node_r + 8:
                hovered = i
        self._hovered = hovered

        for rr, alpha, dash in [(radius+32, 30, True),
                                  (radius,   80, False),
                                  (radius-32, 20, True)]:
            if dash:
                _arc_dashes(surf, (*_RING_DIM, alpha), (cx,cy), rr)
            else:
                rs = _a(rr*2+4, rr*2+4)
                pygame.draw.circle(rs, (*_RING_BRIGHT, alpha), (rr+2,rr+2), rr, 2)
                surf.blit(rs, (cx-rr-2, cy-rr-2))

        pr = radius + 42 + int(self._pulse * 6)
        pa = int(25 + self._pulse * 35)
        ps = _a(pr*2+4, pr*2+4)
        pygame.draw.circle(ps, (*char_color, pa), (pr+2,pr+2), pr, 1)
        surf.blit(ps, (cx-pr-2, cy-pr-2))

        _glow(surf, char_color, (cx,cy), int(18+self._pulse*5), 100)
        pygame.draw.circle(surf, _PANEL_BG, (cx,cy), 8)
        pygame.draw.circle(surf, char_color, (cx,cy), 8, 2)

        for i, (skill, (nx, ny, angle)) in enumerate(zip(skills, positions)):
            ni          = (int(nx), int(ny))
            is_unlocked = skill.is_available(stats.tech_points)
            is_hover    = (i == hovered)
            rim_col     = _UNLOCKED_RIM if is_unlocked else _LOCKED_RIM
            node_col    = _UNLOCKED_NODE if is_unlocked else _LOCKED_NODE
            glow_col    = _GLOW_GREEN    if is_unlocked else (120,20,20)

            sp = _a(W, H)
            pygame.draw.line(sp, (*rim_col, 180 if is_unlocked else 60), (cx,cy), ni, 2)
            surf.blit(sp, (0,0))

            mx2 = int(cx + (radius/2) * math.cos(angle))
            my2 = int(cy + (radius/2) * math.sin(angle))
            pygame.draw.circle(surf, rim_col, (mx2, my2), 3)

            gr = node_r + int(self._pulse*7) + (6 if is_hover else 0)
            _glow(surf, glow_col if not is_hover else char_color, ni, gr,
                  alpha_max=120 if is_hover else (90 if is_unlocked else 30))

            nr_draw = node_r + (3 if is_hover else 0)
            pygame.draw.circle(surf, node_col, ni, nr_draw)
            pygame.draw.circle(surf, rim_col if not is_hover else char_color, ni, nr_draw,
                               3 if is_hover else 2)

            ra = _a(nr_draw*2+14, nr_draw*2+14)
            rim_a_col = char_color if is_hover else rim_col
            pygame.draw.circle(ra, (*rim_a_col, 80), (nr_draw+7, nr_draw+7), nr_draw+6, 1)
            surf.blit(ra, (ni[0]-nr_draw-7, ni[1]-nr_draw-7))

            ltr = self.fonts["lg"].render(skill.name[0].upper(), True,
                                          char_color if is_hover else rim_col)
            surf.blit(ltr, ltr.get_rect(center=ni))

            if not is_unlocked:
                cost_str = f"{skill.unlock_tech} TECH" if skill.unlock_tech < 999 else "?"
                cs = self.fonts["sm"].render(cost_str, True, _GOLD)
                cw, ch = cs.get_size()
                pad = 4
                dist_out = nr_draw + 10 + ch//2
                bx_ = int(nx + math.cos(angle) * dist_out)
                by_ = int(ny + math.sin(angle) * dist_out)
                cb_ = _a(cw+pad*2, ch+pad*2)
                cb_.fill((30,20,10,200))
                bp = (bx_-cw//2-pad, by_-ch//2-pad)
                surf.blit(cb_, bp)
                pygame.draw.rect(surf, (*_GOLD, 140), (*bp, cw+pad*2, ch+pad*2), 1)
                surf.blit(cs, cs.get_rect(center=(bx_, by_)))

        if hovered >= 0:
            self._draw_tooltip(surf, skills[hovered], stats, cx, cy)

        self._draw_xp_bar(surf, stats, cx, wheel)
        self._draw_footer(surf, cx)

    def _draw_tooltip(self, surf, skill, stats, cx, cy):
        """Tooltip fisso centrato in basso, sopra la barra XP."""
        is_unlocked = skill.is_available(stats.tech_points)
        rim_col     = _UNLOCKED_RIM if is_unlocked else _LOCKED_RIM
        char_color  = _GLOW_CYAN if self.active_char_name == "Rivet" else MAGENTA

        desc_data = _SKILL_DESC.get(skill.name, ("—", "Nessuna descrizione disponibile."))
        tipo, desc = desc_data

        fn_sm = self.fonts["sm"]
        fn_md = self.fonts["md"]
        fn_bold = self.fonts["bold"]

        max_desc_w = 460
        desc_lines = _wrap_text(desc, fn_sm, max_desc_w)

        pad     = 14
        line_h  = fn_sm.get_height() + 4
        name_h  = fn_bold.get_height()
        tipo_h  = fn_sm.get_height()
        sep_h   = 8
        tt_w    = max_desc_w + pad * 2
        tt_h    = (pad + name_h + 6 + tipo_h + sep_h +
                   len(desc_lines) * line_h + 6 +
                   fn_sm.get_height() + pad)

        tt_x = cx - tt_w // 2
        tt_y = H - 80 - tt_h - 18

        bg = _a(tt_w, tt_h)
        bg.fill((8, 14, 26, 230))
        surf.blit(bg, (tt_x, tt_y))

        pygame.draw.rect(surf, rim_col, (tt_x, tt_y, tt_w, tt_h), 2)
        _brackets(surf, (tt_x, tt_y, tt_w, tt_h), char_color, sz=10, w=2)

        pygame.draw.line(surf, rim_col, (tt_x+2, tt_y+2), (tt_x+tt_w-2, tt_y+2), 2)

        iy = tt_y + pad

        ns = fn_bold.render(skill.name, True, rim_col)
        surf.blit(ns, ns.get_rect(midleft=(tt_x + pad, iy + name_h//2)))
        iy += name_h + 6

        tipo_color = MAGENTA if "Passiva" in tipo else _GLOW_CYAN
        ts = fn_sm.render(tipo, True, tipo_color)
        surf.blit(ts, (tt_x + pad, iy))
        iy += tipo_h + sep_h

        pygame.draw.line(surf, (*_RING_DIM, 160),
                         (tt_x+pad, iy), (tt_x+tt_w-pad, iy), 1)
        iy += 6

        for line in desc_lines:
            ls = fn_sm.render(line, True, WHITE)
            surf.blit(ls, (tt_x + pad, iy))
            iy += line_h

        iy += 4
        parts = []
        if skill.unlock_tech > 0:
            txt = f"Richiede: {skill.unlock_tech} TECH" if skill.unlock_tech < 999 else "Richiede di hackerare un terminale"
            parts.append(txt)
        if skill.max_cooldown > 0:
            parts.append(f"Cooldown: {skill.max_cooldown} turni")
        if hasattr(skill, "success_rate") and skill.is_combat is True:
            parts.append(f"Successo: {int(skill.success_rate*100)}%")
        stat_str = "  ·  ".join(parts) if parts else "Passiva — nessun cooldown"
        stat_col = _GOLD if is_unlocked else _DIM_TEXT
        ss = fn_sm.render(stat_str, True, stat_col)
        surf.blit(ss, ss.get_rect(midleft=(tt_x + pad, iy + fn_sm.get_height()//2)))

        status_str  = "SBLOCCATA" if is_unlocked else "BLOCCATA"
        status_col  = _GLOW_GREEN if is_unlocked else (160, 60, 60)
        status_bg_c = (10, 40, 10) if is_unlocked else (40, 10, 10)
        sss = fn_sm.render(status_str, True, status_col)
        sw, sh = sss.get_size()
        icon_w  = 16 if is_unlocked else 0
        badge_w = sw + 10 + icon_w
        sbg = _a(badge_w, sh + 6)
        sbg.fill((*status_bg_c, 220))
        sp_pos = (tt_x + tt_w - badge_w - 10, tt_y + pad)
        surf.blit(sbg, sp_pos)
        pygame.draw.rect(surf, (*status_col, 140), (*sp_pos, badge_w, sh + 6), 1)
        if is_unlocked:
            ox = sp_pos[0] + 4
            oy = sp_pos[1] + 3
            pygame.draw.lines(surf, status_col, False,
                               [(ox, oy + 5), (ox + 3, oy + 8), (ox + 9, oy + 1)], 2)
            surf.blit(sss, (sp_pos[0] + icon_w, sp_pos[1] + 3))
        else:
            surf.blit(sss, (sp_pos[0] + 5, sp_pos[1] + 3))

    def _draw_xp_bar(self, surf, stats, cx, wheel):
        bar_w, bar_h = 500, 14

        by = H - 105

        valid_xps = sorted(set(
            s.unlock_tech for s in wheel
            if 0 < s.unlock_tech < 999
        ))

        max_xp = max(valid_xps) if valid_xps else 1
        bx = cx - bar_w // 2

        fill_ratio = min(1.0, stats.tech_points / max_xp)

        bg_b = _a(bar_w+4, bar_h+4)
        bg_b.fill((15,22,35,220))
        surf.blit(bg_b, (bx-2, by-2))
        pygame.draw.rect(surf, _RING_BRIGHT, (bx-2, by-2, bar_w+4, bar_h+4), 1)

        fill_px = int(bar_w * fill_ratio)
        if fill_px > 0:
            fs = _a(fill_px, bar_h)
            for x in range(fill_px):
                t = x / max(1, fill_px-1)
                pygame.draw.line(fs, _lerp((0,160,60), _GLOW_GREEN, t), (x,0),(x,bar_h-1))
            surf.blit(fs, (bx, by))

        for xp in valid_xps:
            mx = bx + int(bar_w * xp / max_xp)
            mc = _GLOW_GREEN if stats.tech_points >= xp else _GOLD
            pygame.draw.line(surf, mc, (mx, by-4), (mx, by+bar_h+4), 1)

        locked_xps = [xp for xp in valid_xps if xp > stats.tech_points]
        label = f"TECH  {stats.tech_points}"

        if locked_xps:
            label += f"  /  {locked_xps[0]}  (prossima abilità)"
        else:
            label += "  (Progressione completata)"

        ls = self.fonts["sm"].render(label, True, _GOLD)
        surf.blit(ls, ls.get_rect(center=(cx, by+bar_h+16)))

        ps = self.fonts["sm"].render("TECH POINTS", True, _DIM_TEXT)
        surf.blit(ps, ps.get_rect(midright=(bx-10, by+bar_h//2)))

    def _draw_footer(self, surf, cx):
        bar_h   = 60
        bar_y   = H - bar_h
        foot    = pygame.Surface((W, bar_h), pygame.SRCALPHA)
        foot.fill((10, 12, 18, 235))
        surf.blit(foot, (0, bar_y))
        pygame.draw.line(surf, _RING_BRIGHT, (0, bar_y), (W, bar_y), 2)

        buttons = [
            ("TAB",    "Cambia personaggio", _GLOW_CYAN),
            ("ESC / R","Chiudi",             RED),
        ]
        margin  = 16
        gap     = 10
        btn_w   = (W - margin * 2 - gap * (len(buttons) - 1)) // len(buttons)
        bx      = margin
        btn_top = bar_y + 6
        btn_hi  = 44
        btn_mid = btn_top + btn_hi // 2
        row1_y  = btn_mid - 9
        row2_y  = btn_mid + 9

        fn_sm = self.fonts["sm"]
        for key_str, label, col in buttons:
            btn_cx = bx + btn_w // 2
            pygame.draw.rect(surf, (col[0]//4, col[1]//4, col[2]//4),
                             (bx, btn_top, btn_w, btn_hi), border_radius=6)
            pygame.draw.rect(surf, col, (bx, btn_top, btn_w, btn_hi), 1, border_radius=6)
            pygame.draw.line(surf, col, (bx + 4, btn_top), (bx + btn_w - 4, btn_top), 2)
            ks = fn_sm.render(key_str, True, WHITE)
            ls = fn_sm.render(label,   True, (200, 205, 215))
            surf.blit(ks, ks.get_rect(center=(btn_cx, row1_y)))
            surf.blit(ls, ls.get_rect(center=(btn_cx, row2_y)))
            bx += btn_w + gap