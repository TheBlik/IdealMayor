import os
import random
import sys
import csv

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QVBoxLayout, QWidget, QSpinBox, QTextBrowser, QTabWidget, QFrame
)

from database import Database

COLS, ROWS = 16, 9

# ОБНОВЛЕННАЯ ЭКОНОМИКА (заводы дают больше материалов, цены чуть скорректированы)
BUILDINGS = {
    "Ратуша": {"money": 0, "mat": 0, "img": "townhall.png", "cat": "infra"},
    "Дорога": {"money": 2, "mat": 1, "img": "road.png", "cat": "infra"},
    "Дом": {"money": 20, "mat": 10, "pop": 5, "demolish": 10, "img": "house1.png", "cat": "house"},
    "Пятиэтажка": {"money": 50, "mat": 40, "pop": 20, "demolish": 40, "img": "house2.png", "cat": "house"},
    "Небоскрёб": {"money": 100, "mat": 150, "pop": 80, "demolish": 125, "img": "house3.png", "cat": "house"},
    "Мастерская": {"money": 30, "mat": 15, "inc": 10, "inc_mat": 8, "inc_goods": 2, "eco": -3, "demolish": 20,
                   "img": "workshop.png", "cat": "ind"},
    "Завод": {"money": 50, "mat": 30, "inc": 40, "inc_mat": 25, "inc_goods": 10, "eco": -8, "demolish": 50,
              "img": "factory1.png", "cat": "ind"},
    "Огромный завод": {"money": 150, "mat": 80, "inc": 80, "inc_mat": 50, "inc_goods": 25, "eco": -15, "demolish": 150,
                       "img": "factory2.png", "cat": "ind"},
    "Сквер": {"money": 20, "mat": 15, "eco": 4, "happy": 3, "demolish": 10, "img": "park1.png", "cat": "soc"},
    "Парк": {"money": 40, "mat": 25, "eco": 10, "happy": 6, "demolish": 30, "img": "park2.png", "cat": "soc"},
    "Цирк": {"money": 80, "mat": 40, "inc": 5, "happy": 12, "demolish": 60, "img": "circus.png", "cat": "soc"}
}

CATEGORIES = {
    "infra": "Инфраструктура",
    "house": "Жилье",
    "ind": "Производство",
    "soc": "Общество"
}

ENDINGS = [
    ("ideal", "Идеальный мэр", "Вы построили утопию и раскрыли секрет симуляции. Система поражена. Вы — легенда."),
    ("reveal", "Разоблачение", "Все записки собраны. Вы взломали код и вырвались на свободу. Что ждет снаружи?"),
    ("utopia", "Утопия", "Город процветает, но вы так и не узнали его главной тайны. Новый цикл начинается."),
    ("escape", "Побег", "Вы попытались сбежать, но мир замкнулся в петлю. Теперь вы навсегда в ловушке."),
    ("oblivion", "Забвение", "Вы допустили крах экономики. Ваш профиль удален из системы навсегда.")
]


def load_modifiers():
    mods = []
    try:
        with open("resources/content/modifiers.txt", "r", encoding="utf-8") as f:
            for line in f:
                p = line.strip().split(";")
                if len(p) < 5: continue
                m = {"chance": int(p[0]), "title": p[1], "message": p[2], "effect": {}}
                t, v = p[3], p[4]
                if t == "prod":
                    m["effect"]["prod"] = float(v)
                elif t == "pen":
                    m["effect"]["pen"] = float(v)
                elif t == "inc":
                    m["effect"]["inc"] = int(v)
                elif t == "ban":
                    m["effect"]["ban"] = True
                elif t == "eco_cover":
                    m["effect"]["eco_cover"] = True
                elif t == "hack":
                    m["effect"]["hack"] = True
                elif t in ("pop", "money", "happy"):
                    m["effect"][t] = tuple(map(int, v.split(",")))
                if len(p) > 5 and p[5] == "instant": m["instant"] = True
                mods.append(m)
    except FileNotFoundError:
        pass
    return mods


def load_notes():
    try:
        with open("resources/content/notes.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return ["Ошибка чтения файла notes.txt."]


MODIFIERS = load_modifiers()
NOTES = load_notes()

STYLE_SEC = "background-color: #333; color: white; border-radius: 5px; padding: 8px 15px; font-size: 14px; border: 1px solid #555;"
STYLE_PRI = "background-color: #4CAF50; color: white; border-radius: 5px; padding: 8px 15px; font-weight: bold; font-size: 14px; border: none;"


def draw_missing_texture(p, px, py, w, h):
    sq_w, sq_h = w / 4, h / 4
    for iy in range(4):
        for ix in range(4):
            p.setBrush(QColor("#1A1A1A") if (ix + iy) % 2 == 0 else QColor("#FF00FF"))
            p.drawRect(int(px + ix * sq_w), int(py + iy * sq_h), int(sq_w), int(sq_h))


class GameMap(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.map_img = QPixmap("resources/map.png")
        self.buildings = []
        self.note_pos = None
        self.note_img = QPixmap("resources/note.png")

    def get_road_angle(self, col, row):
        top = bottom = left = right = False
        for b in self.buildings:
            if b[2] == "Дорога":
                if b[0] == col and b[1] == row - 1: top = True
                if b[0] == col and b[1] == row + 1: bottom = True
                if b[0] == col - 1 and b[1] == row: left = True
                if b[0] == col + 1 and b[1] == row: right = True
        c = sum([top, bottom, left, right])
        if c == 0: return "road.png", 0
        if c == 1:
            if left: return "road_end.png", 0
            if top: return "road_end.png", 90
            if right: return "road_end.png", 180
            if bottom: return "road_end.png", 270
        if c == 2:
            if top and bottom: return "road_v.png", 0
            if left and right: return "road_h.png", 0
            if left and bottom: return "road_turn.png", 0
            if left and top: return "road_turn.png", 90
            if right and top: return "road_turn.png", 180
            if right and bottom: return "road_turn.png", 270
        if c == 3:
            if left and right and bottom: return "road_t.png", 0
            if left and top and bottom: return "road_t.png", 90
            if left and right and top: return "road_t.png", 180
            if right and top and bottom: return "road_t.png", 270
        return "road_cross.png", 0

    def paintEvent(self, event):
        p = QPainter(self)
        if not self.map_img.isNull():
            p.drawPixmap(0, 0, self.map_img.scaled(self.width(), self.height()))
        else:
            p.fillRect(self.rect(), QColor("#7BA05B"))

        cw, ch = self.width() / COLS, self.height() / ROWS
        p.setPen(QColor(255, 255, 255, 40))
        for c in range(COLS + 1): p.drawLine(int(c * cw), 0, int(c * cw), self.height())
        for r in range(ROWS + 1): p.drawLine(0, int(r * ch), self.width(), int(r * ch))

        p.setPen(Qt.PenStyle.NoPen)
        for (c, r, name) in self.buildings:
            px, py = c * cw, r * ch
            if name not in BUILDINGS:
                draw_missing_texture(p, px, py, cw, ch)
                continue
            img, ang = BUILDINGS[name]['img'], 0
            if BUILDINGS[name]["cat"] == "infra" and name == "Дорога": img, ang = self.get_road_angle(c, r)
            pix = QPixmap(f"resources/buildings/{img}")
            if not pix.isNull():
                p.save()
                if ang != 0:
                    p.translate(px + cw / 2, py + ch / 2)
                    p.rotate(ang)
                    p.translate(-(px + cw / 2), -(py + ch / 2))
                p.drawPixmap(int(px), int(py), int(cw), int(ch), pix)
                p.restore()
            else:
                draw_missing_texture(p, px, py, cw, ch)

        if self.note_pos:
            nx, ny = self.note_pos[0] * cw, self.note_pos[1] * ch
            if not self.note_img.isNull():
                p.drawPixmap(int(nx + 5), int(ny + 5), int(cw - 10), int(ch - 10), self.note_img)
            else:
                draw_missing_texture(p, nx, ny, cw, ch)

        notes = self.window.db.get_found_notes_count()
        if notes > 0: p.fillRect(self.rect(), QColor(10, 0, 20, notes * 40))

    def mousePressEvent(self, event):
        c, r = int(event.pos().x() / (self.width() / COLS)), int(event.pos().y() / (self.height() / ROWS))
        if self.note_pos and c == self.note_pos[0] and r == self.note_pos[1]:
            self.window.found_note()
            self.note_pos = None
            self.update()
            return
        if 0 <= c < COLS and 0 <= r < ROWS:
            for bx, by, bname in self.buildings:
                if bx == c and by == r:
                    if bname == "Ратуша":
                        QMessageBox.information(self, "Ратуша", "Это здание сносить нельзя!")
                        return
                    self.window.demolish(c, r, bname)
                    return
            self.window.build_menu(c, r)


class BuildDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Строительство")
        self.resize(500, 600)
        self.setStyleSheet("background-color: #222; color: white;")
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #444;} QTabBar::tab{background:#333;color:white;padding:8px 15px;} QTabBar::tab:selected{background:#4CAF50;}")
        self.lists = {k: QListWidget() for k in CATEGORIES}
        for k, lst in self.lists.items():
            lst.setIconSize(QSize(40, 40))
            lst.setStyleSheet(
                "QListWidget{background:#1a1a1a;border:1px solid #333;} QListWidget::item{padding:5px;border-bottom:1px solid #333;color:white;} QListWidget::item:selected{background:#4CAF50;}")
            self.tabs.addTab(lst, CATEGORIES[k])
        for name, data in BUILDINGS.items():
            if name == "Ратуша" or (name == "Дорога" and data["cat"] != "infra"): continue
            item = QListWidgetItem(f"{name}  |  💰 {data['money']}  🧱 {data['mat']}")
            pix = QPixmap(f"resources/buildings/{data['img']}")
            if not pix.isNull(): item.setIcon(QIcon(pix))
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.lists[data["cat"]].addItem(item)
        layout.addWidget(self.tabs)
        btn = QPushButton("Построить")
        btn.setStyleSheet(STYLE_PRI)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_selected(self):
        item = self.tabs.currentWidget().currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class EndingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Достижения")
        self.resize(450, 400)
        self.setStyleSheet("background-color: #222; color: white;")
        layout = QVBoxLayout(self)
        unlocked = parent.db.get_unlocked_endings()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        cl = QVBoxLayout(content)

        for code, title, desc in ENDINGS:
            is_unlocked = code in unlocked
            block = QWidget()
            bl = QHBoxLayout(block)
            block.setStyleSheet("background-color: #333; border-radius: 5px; margin-bottom: 5px; padding: 10px;")

            color = "white" if is_unlocked else "gray"
            status = "✅" if is_unlocked else "🔒"

            if is_unlocked:
                text_html = f"<b style='color: {color}; font-size: 14px;'>{status} {title}</b><br><span style='color: #aaa; font-size: 12px;'>{desc}</span>"
            else:
                text_html = f"<b style='color: {color}; font-size: 14px;'>{status} {title}</b>"

            text = QLabel(text_html)
            text.setWordWrap(True)

            bl.addWidget(text)
            cl.addWidget(block)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        btn = QPushButton("Закрыть")
        btn.setStyleSheet(STYLE_SEC)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class FinalScreenDialog(QDialog):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.setWindowTitle("Конец игры")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #000;")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #4CAF50; font-size: 50px; font-weight: bold; margin-bottom: 30px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label = QLabel(text)
        text_label.setStyleSheet("color: white; font-size: 24px; line-height: 1.5;")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        btn = QPushButton("В главное меню")
        btn.setStyleSheet(STYLE_PRI + "font-size: 20px; padding: 15px 40px; margin-top: 30px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(title_label)
        layout.addWidget(text_label)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


class HistoryDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("История изменений")
        self.resize(600, 500)
        self.setStyleSheet("background-color: #222; color: white;")
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #444;} QTabBar::tab{background:#333;color:white;padding:8px 15px;} QTabBar::tab:selected{background:#4CAF50;}")
        hist = []
        try:
            with open("city_stats.csv", "r", encoding="utf-8") as f:
                r = csv.reader(f, delimiter=";")
                next(r)
                for row in r:
                    if len(row) == 7: hist.append([int(x) for x in row])
        except FileNotFoundError:
            layout.addWidget(QLabel("История пуста."))
            layout.addWidget(QPushButton("Закрыть", clicked=self.accept))
            return

        for i in range(len(hist)):
            cur = hist[i]
            tab = QWidget()
            tl = QVBoxLayout(tab)
            tl.addWidget(QLabel(f"<h3>Сезон {cur[0]}</h3>"))

            def add_stat(name, val, diff=None):
                if diff is not None:
                    c = "#4CAF50" if diff > 0 else "#f44336" if diff < 0 else "gray"
                    s = "+" if diff > 0 else ""
                    tl.addWidget(QLabel(f"{name}: {val} <span style='color: {c};'>({s}{diff})</span>"))
                else:
                    tl.addWidget(QLabel(f"{name}: {val}"))

            if i == 0:
                add_stat("💰 Деньги", cur[1])
                add_stat("🧱 Материалы", cur[2])
                add_stat("📦 Товары", cur[3])
                add_stat("👥 Население", cur[4])
                add_stat("😊 Счастье", f"{cur[5]}%")
                add_stat("🌿 Экология", f"{cur[6]}%")
            else:
                p = hist[i - 1]
                add_stat("💰 Деньги", cur[1], cur[1] - p[1])
                add_stat("🧱 Материалы", cur[2], cur[2] - p[2])
                add_stat("📦 Товары", cur[3], cur[3] - p[3])
                add_stat("👥 Население", cur[4], cur[4] - p[4])
                add_stat("😊 Счастье", f"{cur[5]}%", cur[5] - p[5])
                add_stat("🌿 Экология", f"{cur[6]}%", cur[6] - p[6])
            tl.addStretch()
            tabs.addTab(tab, f"Сезон {cur[0]}")
        layout.addWidget(tabs)
        btn = QPushButton("Закрыть")
        btn.setStyleSheet(STYLE_SEC)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class HelpDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Справочник мэра")
        self.resize(600, 700)
        self.setStyleSheet("background-color: #222; color: white;")

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setStyleSheet(
            "QTextBrowser { background-color: #1a1a1a; color: #ddd; border: 1px solid #444; padding: 15px; font-size: 14px; }")

        html_text = """
        <h2 style='color: #4CAF50;'>С чего начать?</h2>
        <p>Вы мэр города Аллотерра. Ваша цель — развивать его <b>12 сезонов</b>.</p>
        <ul>
            <li><b>Стройте только рядом с дорогой.</b></li>
            <li>Кнопка <b>«Завершить сезон»</b> дает ресурсы.</li>
            <li>Если <b>Счастье</b> или <b>Экология</b> упадут до 0 — вы проиграли.</li>
            <li>Ищите записки на карте, чтобы раскрыть тайну.</li>
        </ul>

        <hr style='border: 1px solid #333; margin: 20px 0;'>

        <h2 style='color: #4CAF50;'>Экономика</h2>
        <ul>
            <li><b>Дома</b> дают население (налоги).</li>
            <li><b>Заводы</b> дают деньги, но портят экологию.</li>
            <li>Заводы рядом с домами снижают счастье.</li>
            <li><b>Парки и Скверы</b> спасают экологию.</li>
        </ul>
        <p>Товары можно продавать в другие города (кнопка «Торговля»). Там есть лимиты!</p>

        <hr style='border: 1px solid #333; margin: 20px 0;'>

        <h2 style='color: #4CAF50;'>Каталог зданий</h2>
        """

        for name, data in BUILDINGS.items():
            if name in ("Ратуша", "Дорога"): continue
            desc = ""
            if data["cat"] == "house":
                desc = f"Население +{data['pop']}."
            elif data["cat"] == "ind":
                desc = f"Доход +{data['inc']}. <span style='color:#f44336;'>Эко {data['eco']}.</span>"
            elif data["cat"] == "soc":
                desc = f"Эко +{data.get('eco', 0)}, Счастье +{data.get('happy', 0)}."
            html_text += f"""
            <div style='margin-bottom: 15px; background-color: #222; padding: 10px; border-radius: 5px;'>
                <b style='color: #4CAF50; font-size: 16px;'>{name}</b><br>
                <span style='color: #aaa;'>Цена: 💰 {data['money']}  🧱 {data['mat']}</span><br>
                <span style='color: #ddd;'>{desc}</span>
            </div>
            """

        browser.setHtml(html_text)
        layout.addWidget(browser)

        btn = QPushButton("Понятно")
        btn.setStyleSheet(STYLE_PRI)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Идеальный мэр")
        self.db = Database()
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.setStatusBar(None)
        self.game = None
        self.trade_banned = False
        self.trade_penalty = 0.0
        self.tourists = 0
        self.prices = {}
        self.city_limits = {}
        self.active_modifier = None
        self.active_mod_value = 0
        self.init_menu()

    def init_menu(self):
        self.menu = QWidget()
        self.menu.setStyleSheet("background-color: #111;")
        layout = QVBoxLayout(self.menu)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("ИДЕАЛЬНЫЙ МЭР")
        title.setStyleSheet("font-size: 60px; color: #4CAF50; margin-bottom: 40px;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        for text, slot, style in [
            ("Начать заново", self.start_game, STYLE_PRI),
            ("Продолжить", self.show_game, STYLE_SEC),
            ("Достижения", lambda: EndingsDialog(self).exec(), STYLE_SEC),
            ("Справочник", lambda: HelpDialog(self).exec(), STYLE_SEC)
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(250, 45)
            btn.setStyleSheet(style)
            btn.clicked.connect(slot)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn_continue = layout.itemAt(2).widget()
        if not os.path.exists("city.db"): self.btn_continue.setEnabled(False)
        self.stack.addWidget(self.menu)
        self.stack.setCurrentWidget(self.menu)

    def start_game(self):
        if not self.db: self.db = Database()
        self.db.reset_progress()
        self.db.save_building(8, 4, "Ратуша")
        self.prices = {"Блик": random.randint(8, 15), "Набережные Челны": random.randint(5, 12),
                       "Муринск": random.randint(3, 9)}
        self.city_limits = {"Блик": random.randint(10, 20), "Набережные Челны": random.randint(5, 15),
                            "Муринск": random.randint(3, 10)}
        self.active_modifier = None
        self.show_game()

    def show_game(self):
        _, _, _, season, _, _, _ = self.db.get_player()
        if season > 12:
            QMessageBox.information(self, "Конец", "Игра пройдена!")
            return
        if self.game:
            self.stack.removeWidget(self.game)
            self.game.deleteLater()
        self.game = QWidget()
        self.map_widget = GameMap(self)
        self.map_widget.setParent(self.game)
        self.season_label = QLabel(f"Сезон {season}", self.game)
        self.season_label.setStyleSheet(
            "color: white; background: rgba(0,0,0,180); font-size: 20px; padding: 8px 15px; border-radius: 8px;")
        self.btn_next = QPushButton("Завершить сезон", self.game)
        self.btn_next.setStyleSheet(STYLE_PRI)
        self.btn_next.clicked.connect(self.next_season)
        self.btn_pause = QPushButton("Пауза", self.game)
        self.btn_pause.setStyleSheet(STYLE_SEC)
        self.btn_pause.clicked.connect(self.show_pause)
        self.btn_market = QPushButton("Торговля", self.game)
        self.btn_market.setStyleSheet(
            "background-color: #2196F3; color: white; padding: 8px 15px; border-radius: 5px; border: none;")
        self.btn_market.clicked.connect(self.open_market)
        self.btn_history = QPushButton("История", self.game)
        self.btn_history.setStyleSheet(
            "background-color: #9C27B0; color: white; padding: 8px 15px; border-radius: 5px; border: none;")
        self.btn_history.clicked.connect(lambda: HistoryDialog(self).exec())
        self.res_label = QLabel("Ресурсы", self.game)
        self.res_label.setStyleSheet(
            "color: white; background: rgba(0,0,0,180); font-size: 15px; padding: 15px; border-radius: 10px;")
        self.stack.addWidget(self.game)
        self.stack.setCurrentWidget(self.game)
        self.update_ui()
        self.resizeEvent(None)

    def resizeEvent(self, event):
        if event: super().resizeEvent(event)
        if self.game and hasattr(self, 'map_widget'):
            w, h = self.width(), self.height()
            self.map_widget.setGeometry(0, 0, w, h)
            self.season_label.setGeometry(20, 20, 150, 45)
            self.btn_pause.setGeometry(w - 100, 20, 80, 40)
            self.btn_next.setGeometry(w - 280, 20, 160, 40)
            self.btn_market.setGeometry(w - 420, 20, 120, 40)
            self.btn_history.setGeometry(w - 550, 20, 110, 40)
            self.res_label.setGeometry(20, h - 230, 250, 210)

    def update_ui(self):
        if not self.db: return
        m, mat, g, s, p, h, e = self.db.get_player()
        self.season_label.setText(f"Сезон {s}")
        self.res_label.setText(
            f"💰 Деньги: <b>{m}</b><br>🧱 Материалы: <b>{mat}</b><br>📦 Товары: <b>{g}</b><br>👥 Население: <b>{p}</b><br>😊 Счастье: <b>{h}%</b><br>🌿 Экология: <b>{e}%</b>")
        if hasattr(self, 'map_widget'):
            self.map_widget.buildings = self.db.get_buildings()
            self.map_widget.update()

    def check_road(self, c, r):
        for bx, by, bname in self.db.get_buildings():
            if abs(bx - c) + abs(by - r) == 1 and bname == "Дорога": return True
        return False

    def build_menu(self, c, r):
        dialog = BuildDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        name = dialog.get_selected()
        if not name: return
        data = BUILDINGS[name]
        money, mats, _, _, _, _, _ = self.db.get_player()
        if name not in ("Дорога", "Ратуша") and not self.check_road(c, r):
            QMessageBox.warning(self, "Ошибка", "Нужна дорога рядом.")
            return
        if money >= data["money"] and mats >= data["mat"]:
            self.db.update_player(money=money - data["money"], materials=mats - data["mat"])
            self.db.save_building(c, r, name)
            self.db.log_action_to_csv("Постройка", f"{name} на ({c}, {r})")
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка", "Не хватает ресурсов.")

    def demolish(self, c, r, name):
        if QMessageBox.question(self, "Снос", f"Снести {name}?") == QMessageBox.StandardButton.Yes:
            refund = BUILDINGS[name].get("demolish", 0)
            money, _, _, _, _, _, _ = self.db.get_player()
            self.db.update_player(money=money + refund)
            self.db.remove_building(c, r)
            self.update_ui()

    def open_market(self):
        if self.trade_banned:
            QMessageBox.warning(self, "Торговля", "Соседи не хотят торговать!")
            return
        _, _, goods, _, _, _, _ = self.db.get_player()

        dialog = QDialog(self)
        dialog.setWindowTitle("Рынок")
        dialog.setFixedSize(550, 500)
        dialog.setStyleSheet("background-color: #121212; color: white;")

        layout = QVBoxLayout(dialog)

        header = QFrame()
        header.setStyleSheet("background-color: #1e1e1e; border-radius: 8px; padding: 10px;")
        h_layout = QVBoxLayout(header)
        h_layout.addWidget(QLabel(f"<h2 style='color: #4CAF50; margin: 0;'>Городской Рынок</h2>"))
        h_layout.addWidget(QLabel(f"📦 Товаров на складе: <b>{goods} шт.</b>"))
        if self.trade_penalty > 0:
            h_layout.addWidget(
                QLabel(f"<span style='color: #f44336;'>⚠️ Санкции: -{int(self.trade_penalty * 100)}% к цене!</span>"))
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(10)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)

        for city, base in self.prices.items():
            final = int(base * (1 - self.trade_penalty))
            limit = self.city_limits.get(city, 0)

            card = QFrame()
            card.setStyleSheet("background-color: #1e1e1e; border-radius: 8px; border: 1px solid #333;")
            row = QHBoxLayout(card)
            row.setContentsMargins(15, 15, 15, 15)

            info_layout = QVBoxLayout()
            info_layout.addWidget(QLabel(f"<b style='font-size: 18px; color: #2196F3;'>{city}</b>"))
            info_layout.addWidget(QLabel(f"<span style='color: #888; font-size: 12px;'>Лимит: {limit} шт.</span>"))
            row.addLayout(info_layout)

            row.addStretch()

            price_layout = QVBoxLayout()
            price_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            price_label = QLabel(
                f"<b style='font-size: 22px; color: #4CAF50;'>{final}</b> <span style='color: #aaa;'>монет</span>")
            if self.trade_penalty > 0:
                price_label.setText(f"<s style='color: #555;'>{base}</s> {price_label.text()}")
            price_layout.addWidget(price_label)
            row.addLayout(price_layout)

            action_layout = QHBoxLayout()
            spin = QSpinBox()
            max_sell = min(goods, limit)
            spin.setRange(1, max(1, max_sell))
            spin.setFixedSize(80, 40)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.setStyleSheet(
                "QSpinBox{background:#121212;color:white;border:1px solid #555;border-radius: 5px; padding:2px;}")
            if goods == 0 or limit == 0: spin.setEnabled(False)
            action_layout.addWidget(spin)

            btn = QPushButton("Продать")
            btn.setFixedSize(100, 40)
            btn.setStyleSheet(STYLE_PRI)
            if goods == 0 or limit == 0: btn.setEnabled(False)
            btn.clicked.connect(lambda _, p=final, s=spin, c=city: self.sell(p, s.value(), c, dialog))
            action_layout.addWidget(btn)

            row.addLayout(action_layout)
            cl.addWidget(card)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        close = QPushButton("Закрыть")
        close.setStyleSheet(STYLE_SEC)
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def sell(self, price, amount, city, dialog):
        money, _, goods, _, _, _, _ = self.db.get_player()
        if goods < amount or self.city_limits.get(city, 0) < amount:
            QMessageBox.warning(self, "Ошибка", "Недостаточно товаров или лимит исчерпан!")
            return
        earned = amount * price
        self.db.update_player(money=money + earned, goods=goods - amount)
        self.city_limits[city] -= amount
        self.db.log_action_to_csv("Продажа", f"{amount} шт. в {city} за {earned} монет")
        QMessageBox.information(self, "Сделка", f"Продано {amount} шт. за {earned} монет.")
        self.update_ui()
        dialog.accept()

    def found_note(self):
        found = self.db.get_found_notes_count()
        if found >= 5: return
        self.db.unlock_note(f"note_{found}")
        msg = QMessageBox(self)
        msg.setWindowTitle("Записка")
        msg.setText(f"{NOTES[found]}\n\nСбежать или остаться?")
        escape = msg.addButton("Сбежать", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Остаться", QMessageBox.ButtonRole.ActionRole)
        msg.exec()
        if msg.clickedButton() == escape:
            self.db.unlock_ending("escape")
            self.end_game()
        elif self.db.get_found_notes_count() == 5:
            self.db.unlock_ending("reveal")
            self.end_game()

    def end_game(self):
        unlocked = self.db.get_unlocked_endings()
        if unlocked:
            last = unlocked[-1]
            for code, title, desc in ENDINGS:
                if code == last:
                    FinalScreenDialog(self, title, desc).exec()
                    break
        self.stack.setCurrentWidget(self.menu)
        self.btn_continue.setEnabled(False)

    def next_season(self):
        money, mats, goods, season, pop, happy, eco = self.db.get_player()
        buildings_list = self.db.get_buildings()
        if money <= 0 or happy <= 0 or eco <= 0:
            self.db.unlock_ending("oblivion")
            self.end_game()
            return
        self.trade_banned = False
        self.trade_penalty = 0.0
        if self.tourists > 0:
            pop = max(2, pop - self.tourists)
            self.tourists = 0
        effect = {}
        if hasattr(self, 'active_modifier') and self.active_modifier:
            effect = self.active_modifier["effect"]
            if "money" in effect: money += self.active_mod_value
            if "pop" in effect:
                pop += self.active_mod_value
                self.tourists = self.active_mod_value
            if "happy" in effect: happy += self.active_mod_value
            self.trade_banned = effect.get("ban", False)
            self.trade_penalty = effect.get("pen", 0.0)
            self.active_modifier = None

        income = income_mat = income_goods = eco_change = 0
        capacity = building_count = 0
        for _, _, bname in buildings_list:
            d = BUILDINGS[bname]
            if bname not in ("Ратуша", "Дорога"): building_count += 1
            capacity += d.get("pop", 0)
            income += d.get("inc", 0)
            income_mat += d.get("inc_mat", 0)
            income_goods += d.get("inc_goods", 0)
            eco_change += d.get("eco", 0)

        new_pop = min(capacity, pop + random.randint(2, 5))
        if new_pop < pop: new_pop = pop

        happiness_penalty = 0
        for bx, by, bname in buildings_list:
            if BUILDINGS[bname]["cat"] == "house":
                for obx, oby, obname in buildings_list:
                    if abs(bx - obx) + abs(by - oby) == 1 and BUILDINGS[obname]["cat"] == "ind":
                        happiness_penalty -= 10

        income_mult = effect.get("inc", 1.0)
        prod_mult = effect.get("prod", 1.0)
        final_income = int(income * income_mult * prod_mult)
        final_mats = int(income_mat * prod_mult)
        final_goods = int(income_goods * prod_mult)
        taxes = int(new_pop * 1.5)

        new_money = money + final_income + taxes
        new_mats = mats + final_mats
        new_goods = goods + final_goods
        new_eco = max(0, min(100, eco + eco_change)) if "eco_cover" not in effect else eco
        new_happy = max(0, min(100, happy + happiness_penalty))

        self.db.update_player(money=new_money, materials=new_mats, goods=new_goods, ecology=new_eco,
                              happiness=new_happy, population=new_pop)
        self.db.export_stats_to_csv()

        report = f"<b>Сезон {season} завершен!</b><br>"
        if new_money - money: report += f"💰: {new_money - money:+}<br>"
        if new_mats - mats: report += f"🧱: {new_mats - mats:+}<br>"
        if new_goods - goods: report += f"📦: {new_goods - goods:+}<br>"
        if new_pop - pop: report += f"👥: {new_pop - pop:+}<br>"
        if new_eco - eco: report += f"🌿: {new_eco - eco:+}%<br>"
        if new_happy - happy: report += f"😊: {new_happy - happy:+}%<br>"
        QMessageBox.information(self, "Итоги сезона", report)

        found = self.db.get_found_notes_count()
        if not self.map_widget.note_pos:
            lagging = (season >= 4 and found == 0) or (season >= 8 and found < 2)
            if random.random() < 0.6 or lagging:
                occupied = [(b[0], b[1]) for b in buildings_list]
                spots = [(c, r) for c in range(COLS) for r in range(ROWS) if (c, r) not in occupied]
                if spots:
                    self.map_widget.note_pos = random.choice(spots)
                    self.map_widget.update()

        if season >= 12:
            self.db.update_player(season=99)
            found = self.db.get_found_notes_count()
            developed = building_count >= 10 and new_pop >= 40 and (
                    final_income + taxes) >= 100 and new_happy >= 30 and new_eco >= 30
            if not developed:
                self.db.unlock_ending("oblivion")
            elif found >= 3:
                self.db.unlock_ending("ideal")
            else:
                self.db.unlock_ending("utopia")
            self.end_game()
            return

        self.db.update_player(season=season + 1)
        self.city_limits = {"Блик": random.randint(10, 20), "Набережные Челны": random.randint(5, 15),
                            "Муринск": random.randint(3, 10)}

        if MODIFIERS:
            next_mod = random.choice(MODIFIERS)
            next_message = next_mod["message"]
            next_effect = next_mod["effect"]
            if next_mod.get("instant"):
                if "money" in next_effect:
                    val = random.randint(*next_effect["money"])
                    cur_money, _, _, _, _, _, _ = self.db.get_player()
                    self.db.update_player(money=cur_money + val)
                    next_message = next_message.format(val)
                if "hack" in next_effect:
                    for b in buildings_list:
                        if BUILDINGS[b[2]]["cat"] == "house":
                            self.db.remove_building(b[0], b[1])
                            self.db.save_building(b[0], b[1], "Небоскрёб")
                    self.map_widget.buildings = self.db.get_buildings()
                    self.map_widget.update()
            else:
                self.active_mod_value = 0
                if "money" in next_effect:
                    val = random.randint(*next_effect["money"])
                    self.active_mod_value = val
                    next_message = next_message.format(val)
                elif "pop" in next_effect:
                    val = random.randint(*next_effect["pop"])
                    self.active_mod_value = val
                    next_message = next_message.format(val)
                elif "happy" in next_effect:
                    val = random.randint(*next_effect["happy"])
                    self.active_mod_value = val
                    next_message = next_message.format(val)
                self.active_modifier = next_mod
            self.db.log_action_to_csv("Событие", next_mod["title"])
            QMessageBox.information(self, "Модификатор сезона", next_message)
        self.update_ui()

    def show_pause(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Пауза")
        dialog.setFixedSize(250, 250)
        dialog.setStyleSheet("background-color: #222; color: white;")
        layout = QVBoxLayout(dialog)
        for t, s, st in [
            ("Продолжить", dialog.accept, STYLE_PRI),
            ("Справочник", lambda: HelpDialog(self).exec(), STYLE_SEC),
            ("Достижения", lambda: EndingsDialog(self).exec(), STYLE_SEC),
            ("В меню", lambda: (dialog.accept(), self.stack.setCurrentWidget(self.menu)), STYLE_SEC)
        ]:
            btn = QPushButton(t)
            btn.setStyleSheet(st)
            btn.clicked.connect(s)
            layout.addWidget(btn)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow()
    window.showFullScreen()
    sys.exit(app.exec())