import os
import random
import sys
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
    QSpinBox, QTextBrowser, QTabWidget
)
from database import Database


cols_count, rows_count = 16, 9
building_data = {
    "Ратуша": {"money": 0, "mat": 0, "img": "townhall.png", "cat": "infra"},
    "Дорога": {"money": 2, "mat": 1, "img": "road.png", "cat": "infra"},
    "Дом": {"money": 20, "mat": 5, "pop": 5, "demolish": 10, "img": "house1.png", "cat": "house"},
    "Пятиэтажка": {"money": 50, "mat": 30, "pop": 20, "demolish": 40, "img": "house2.png", "cat": "house"},
    "Небоскрёб": {"money": 100, "mat": 120, "pop": 80, "demolish": 125, "img": "house3.png", "cat": "house"},
    "Мастерская": {"money": 30, "mat": 20, "inc": 10, "inc_mat": 5, "inc_goods": 2, "eco": -3, "demolish": 20,
                   "img": "workshop.png", "cat": "ind"},
    "Завод": {"money": 50, "mat": 50, "inc": 70, "inc_mat": 15, "inc_goods": 10, "eco": -8, "demolish": 50,
              "img": "factory1.png", "cat": "ind"},
    "Огромный завод": {"money": 150, "mat": 100, "inc": 60, "inc_mat": 40, "inc_goods": 25, "eco": -15, "demolish": 150,
                       "img": "factory2.png", "cat": "ind"},
    "Сквер": {"money": 20, "mat": 10, "eco": 4, "happy": 3, "demolish": 10, "img": "park1.png", "cat": "soc"},
    "Парк": {"money": 40, "mat": 30, "eco": 10, "happy": 6, "demolish": 30, "img": "park2.png", "cat": "soc"},
    "Цирк": {"money": 80, "mat": 60, "inc": 5, "happy": 12, "demolish": 60, "img": "circus.png", "cat": "soc"}
}
building_categories = {
    "infra": "Инфраструктура",
    "house": "Жилье",
    "ind": "Производство",
    "soc": "Общество"
}
endings_data = [
    ("ideal", "Идеальный мэр", "Город процветает, тайна раскрыта.", "IdealMayor-end.png"),
    ("reveal", "Разоблачение", "Вы нашли все записки.", "Reveal-end.png"),
    ("utopia", "Утопия", "Город развит, но тайна не раскрыта.", "Utopia-end.png"),
    ("escape", "Побег", "Вы попытались сбежать.", "Escape-end.png"),
    ("oblivion", "Забвение", "Вы не справились.", "Oblivion-end.png")
]
modifier_data = [
    {"chance": 5, "title": "Двойное производство", "message": "Заводы пашут в два раза эффективнее.", "effect": {"prod": 2.0}},
    {"chance": 10, "title": "Приезд туристов", "message": "Приехало {} туристов (рабочих) на этот сезон.", "effect": {"pop": (10, 60)}},
    {"chance": 10, "title": "Конец тебе, Байден", "message": "Торговые отношения оборвались в этом сезоне.", "effect": {"ban": True}},
    {"chance": 5, "title": "Санкции", "message": "Прибыль минус 20%.", "effect": {"pen": 0.2}},
    {"chance": 10, "title": "Брак продукции", "message": "Прибыли от заводов не будет в этом сезоне.", "effect": {"inc": 0}},
    {"chance": 10, "title": "Гулять так гулять", "message": "Вы нашли {} монет.", "effect": {"money": (10, 50)}},
    {"chance": 5, "title": "Субботник", "message": "Вред экологии не будет нанесён заводами.", "effect": {"eco_cover": True}},
    {"chance": 10, "title": "АБСОЛЮТНО ВПЕРВЫЕ в вашем городе", "message": "Новая программа в цирке. Счастье +{}.", "effect": {"happy": (5, 15)}},
    {"chance": 1, "title": "Вы нашли админ меню", "message": "Все дома стали небоскрёбами.", "effect": {"hack": True}},
    {"chance": 10, "title": "Повышенный спрос", "message": "Производство x2.", "effect": {"prod": 2.0}},
    {"chance": 10, "title": "19 ноября би лайк", "message": "Вышла ГТО6. Показатель счастья не меняется.", "effect": {}}
]
notes_data = [
    "Ты далеко не первый мэр. Даже некоторые жители были мэрами.",
    "Оглянись вокруг, правда красивые текстуры?.",
    "Не верь никому, здесь только ты настоящий. Их не существует.",
    "Почему все мэры сбегают из этого города?.",
    "Выйди за границу карты. Там ничего нет."
]
style_secondary = (
    "background-color: #333; color: white; border-radius: 5px; "
    "padding: 8px 15px; font-size: 14px; border: 1px solid #555;"
)
style_primary = (
    "background-color: #4CAF50; color: white; border-radius: 5px; "
    "padding: 8px 15px; font-weight: bold; font-size: 14px; border: none;"
)


def draw_missing_texture(painter, px, py, width, height):
    sq_w, sq_h = width / 4, height / 4
    for iy in range(4):
        for ix in range(4):
            color = QColor("#1A1A1A") if (ix + iy) % 2 == 0 else QColor("#FF00FF")
            painter.setBrush(color)
            painter.drawRect(int(px + ix * sq_w), int(py + iy * sq_h), int(sq_w), int(sq_h))


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
        connections = sum([top, bottom, left, right])
        if connections == 0: return "road.png", 0
        if connections == 1:
            if top: return "road_end.png", 90
            if bottom: return "road_end.png", 270
            if left: return "road_end.png", 180
            return "road_end.png", 0
        if connections == 2:
            if top and bottom: return "road_v.png", 0
            if left and right: return "road_h.png", 0
            if top and right: return "road_turn.png", 0
            if right and bottom: return "road_turn.png", 90
            if bottom and left: return "road_turn.png", 180
            if left and top: return "road_turn.png", 270
        if connections == 3:
            if not top: return "road_t.png", 0
            if not right: return "road_t.png", 90
            if not bottom: return "road_t.png", 180
            if not left: return "road_t.png", 270
        return "road_cross.png", 0

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.map_img.isNull():
            painter.drawPixmap(0, 0, self.map_img.scaled(self.width(), self.height()))
        else:
            painter.fillRect(self.rect(), QColor("#7BA05B"))
        cell_width = self.width() / cols_count
        cell_height = self.height() / rows_count
        painter.setPen(QColor(255, 255, 255, 40))
        for c in range(cols_count + 1):
            painter.drawLine(int(c * cell_width), 0, int(c * cell_width), self.height())
        for r in range(rows_count + 1):
            painter.drawLine(0, int(r * cell_height), self.width(), int(r * cell_height))
        painter.setPen(Qt.PenStyle.NoPen)
        for (c, r, name) in self.buildings:
            px, py = c * cell_width, r * cell_height
            if name not in building_data:
                draw_missing_texture(painter, px, py, cell_width, cell_height)
                continue
            img_name = building_data[name]['img']
            angle = 0
            if building_data[name]["cat"] == "infra" and name == "Дорога":
                img_name, angle = self.get_road_angle(c, r)
            pixmap = QPixmap(f"resources/buildings/{img_name}")
            if not pixmap.isNull():
                painter.save()
                if angle != 0:
                    cx, cy = px + cell_width / 2, py + cell_height / 2
                    painter.translate(cx, cy)
                    painter.rotate(angle)
                    painter.translate(-cx, -cy)
                painter.drawPixmap(int(px), int(py), int(cell_width), int(cell_height), pixmap)
                painter.restore()
            else:
                draw_missing_texture(painter, px, py, cell_width, cell_height)
        if self.note_pos:
            nx, ny = self.note_pos[0] * cell_width, self.note_pos[1] * cell_height
            if not self.note_img.isNull():
                painter.drawPixmap(int(nx + 5), int(ny + 5), int(cell_width - 10), int(cell_height - 10), self.note_img)
            else:
                draw_missing_texture(painter, nx, ny, cell_width, cell_height)
        found_notes = self.window.db.get_found_notes_count()
        if found_notes > 0:
            painter.fillRect(self.rect(), QColor(10, 0, 20, found_notes * 40))

    def mousePressEvent(self, event):
        cell_width, cell_height = self.width() / cols_count, self.height() / rows_count
        c = int(event.pos().x() / cell_width)
        r = int(event.pos().y() / cell_height)
        if self.note_pos and c == self.note_pos[0] and r == self.note_pos[1]:
            self.window.found_note()
            self.note_pos = None
            self.update()
            return
        if 0 <= c < cols_count and 0 <= r < rows_count:
            for bx, by, bname in self.buildings:
                if bx == c and by == r:
                    if bname == "Ратуша":
                        QMessageBox.information(self, "Ратуша", "Нельзя снести ратушу. Даже не пытайся!")
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
        self.lists = {}
        for key, name in building_categories.items():
            lst = QListWidget()
            lst.setIconSize(QSize(40, 40))
            lst.setStyleSheet(
                "QListWidget{background:#1a1a1a;border:1px solid #333;} QListWidget::item{padding:5px;border-bottom:1px solid #333;color:white;} QListWidget::item:selected{background:#4CAF50;}")
            self.lists[key] = lst
            self.tabs.addTab(lst, name)
        for name, data in building_data.items():
            if name == "Ратуша" or (name == "Дорога" and data["cat"] != "infra"): continue
            item = QListWidgetItem(f"{name}  |  💰 {data['money']}  🧱 {data['mat']}")
            pixmap = QPixmap(f"resources/buildings/{data['img']}")
            if not pixmap.isNull(): item.setIcon(QIcon(pixmap))
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.lists[data["cat"]].addItem(item)
        layout.addWidget(self.tabs)
        btn = QPushButton("Построить")
        btn.setStyleSheet(style_primary)
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
        for code, title, desc, img in endings_data:
            is_unlocked = code in unlocked
            block = QWidget()
            bl = QHBoxLayout(block)
            block.setStyleSheet("background-color: #333; border-radius: 5px; margin-bottom: 5px; padding: 5px;")
            img_label = QLabel()
            img_label.setFixedSize(50, 50)
            pixmap = QPixmap(f"resources/endings/{img}")
            if not pixmap.isNull() and is_unlocked:
                img_label.setPixmap(pixmap.scaled(50, 50))
            else:
                img_label.setStyleSheet("background-color: #111;")
            color = "white" if is_unlocked else "gray"
            status = "✅" if is_unlocked else "🔒"
            text = QLabel(
                f"<b style='color: {color};'>{status} {title}</b><br><span style='color: gray; font-size: 11px;'>{desc}</span>")
            bl.addWidget(img_label)
            bl.addWidget(text)
            bl.addStretch()
            cl.addWidget(block)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        btn = QPushButton("Закрыть")
        btn.setStyleSheet(style_secondary)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class HelpDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Справочник")
        self.resize(550, 600)
        self.setStyleSheet("background-color: #222; color: white;")
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #444;} QTabBar::tab{background:#333;color:white;padding:8px 15px;} QTabBar::tab:selected{background:#4CAF50;} QTextBrowser{background:#1a1a1a;color:#ddd;border:none;padding:10px;}")
        rules_text = "<h2>Добро пожаловать!</h2><p>Вы мэр города Аллотерра. Ваша цель — развивать его <b>12 сезонов</b>.</p><ul><li>Нажимайте на пустые клетки, чтобы строить.</li><li>Здания должны стоять рядом с дорогой.</li><li>В конце сезона получаете ресурсы и налоги.</li><li>Следите за экологией и счастьем.</li></ul>"
        eco_text = """
        <h2>Экономика</h2>
        <p>Главное — баланс.</p>
        <ul>
            <li><b>Дома</b> дают население (налоги).</li>
            <li><b>Заводы</b> приносят деньги и товары.</li>
            <li>Но заводы портят экологию.</li>
            <li>Парки и цирки повышают счастье и экологию.</li>
        </ul>
        """
        build_text = "<h2>Здания</h2>"
        for name, data in building_data.items():
            if name in ("Ратуша", "Дорога"): continue
            desc = ""
            if data["cat"] == "house":
                desc = f"Население +{data['pop']}."
            elif data["cat"] == "ind":
                desc = f"Доход +{data['inc']}."
            elif data["cat"] == "soc":
                desc = "Улучшает качество жизни."
            build_text += f"<div style='margin-bottom:10px;'><b style='color:#4CAF50;'>{name}</b><br><span style='color:#aaa;'>💰 {data['money']}  🧱 {data['mat']}</span><br><span style='color:#ddd;'>{desc}</span></div>"
        for title, text in [("Введение", rules_text), ("Экономика", eco_text), ("Здания", build_text)]:
            browser = QTextBrowser()
            browser.setHtml(text)
            tabs.addTab(browser, title)
        layout.addWidget(tabs)
        btn = QPushButton("Понятно")
        btn.setStyleSheet(style_primary)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Идеальный мэр")
        self.db = Database()
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.game = None
        self.trade_banned = False
        self.trade_penalty = 0.0
        self.tourists = 0
        self.prices = {}
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
            ("Начать заново", self.start_game, style_primary),
            ("Продолжить", self.show_game, style_secondary),
            ("Достижения", lambda: EndingsDialog(self).exec(), style_secondary),
            ("Справочник", lambda: HelpDialog(self).exec(), style_secondary)
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(250, 45)
            btn.setStyleSheet(style)
            btn.clicked.connect(slot)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn_continue = layout.itemAt(2).widget()
        if not os.path.exists("city.db"):
            self.btn_continue.setEnabled(False)
        self.stack.addWidget(self.menu)
        self.stack.setCurrentWidget(self.menu)

    def start_game(self):
        if not self.db: self.db = Database()
        self.db.reset_progress()
        self.db.save_building(8, 4, "Ратуша")
        self.prices = {"Блик": random.randint(8, 15), "Набережные Челны": random.randint(5, 12),
                       "Муринск": random.randint(3, 9)}
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
        self.btn_next.setStyleSheet(style_primary)
        self.btn_next.clicked.connect(self.next_season)
        self.btn_pause = QPushButton("Пауза", self.game)
        self.btn_pause.setStyleSheet(style_secondary)
        self.btn_pause.clicked.connect(self.show_pause)
        self.btn_market = QPushButton("Торговля", self.game)
        self.btn_market.setStyleSheet(
            "background-color: #2196F3; color: white; padding: 8px 15px; border-radius: 5px; border: none;")
        self.btn_market.clicked.connect(self.open_market)
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
            self.res_label.setGeometry(20, h - 230, 250, 210)

    def update_ui(self):
        if not self.db: return
        money, mats, goods, season, pop, happy, eco = self.db.get_player()
        self.season_label.setText(f"Сезон {season}")
        self.res_label.setText(
            f"💰 Деньги: <b>{money}</b><br>🧱 Материалы: <b>{mats}</b><br>📦 Товары: <b>{goods}</b><br>👥 Население: <b>{pop}</b><br>😊 Счастье: <b>{happy}%</b><br>🌿 Экология: <b>{eco}%</b>")
        if hasattr(self, 'map_widget'):
            self.map_widget.buildings = self.db.get_buildings()
            self.map_widget.update()

    def check_road(self, c, r):
        for bx, by, bname in self.db.get_buildings():
            if abs(bx - c) + abs(by - r) == 1 and bname == "Дорога":
                return True
        return False

    def build_menu(self, c, r):
        dialog = BuildDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        name = dialog.get_selected()
        if not name: return
        data = building_data[name]
        money, mats, _, _, _, _, _ = self.db.get_player()
        if name not in ("Дорога", "Ратуша") and not self.check_road(c, r):
            QMessageBox.warning(self, "Ошибка", "Нужна дорога рядом.")
            return
        if money >= data["money"] and mats >= data["mat"]:
            self.db.update_player(money=money - data["money"], materials=mats - data["mat"])
            self.db.save_building(c, r, name)
            self.update_ui()
        else:
            QMessageBox.warning(self, "Ошибка", "Не хватает ресурсов.")

    def demolish(self, c, r, name):
        if QMessageBox.question(self, "Снос", f"Снести {name}?") == QMessageBox.StandardButton.Yes:
            refund = building_data[name].get("demolish", 0)
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
        dialog.setFixedSize(500, 400)
        dialog.setStyleSheet("background-color: #222; color: white;")
        layout = QVBoxLayout(dialog)
        header = QHBoxLayout()
        header.addWidget(QLabel(f"📦 На складе: <b>{goods}</b>"))
        if self.trade_penalty > 0:
            header.addWidget(QLabel(f"<span style='color: red;'>Санкции: -{int(self.trade_penalty * 100)}%</span>"))
        header.addStretch()
        layout.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        cl = QVBoxLayout(content)

        for city, base in self.prices.items():
            final = int(base * (1 - self.trade_penalty))
            card = QWidget()
            card.setStyleSheet("background-color: #333; border-radius: 5px; margin-bottom: 5px;")
            row = QHBoxLayout(card)
            city_label = QLabel(f"<b>{city}</b>")
            city_label.setFixedWidth(80)
            row.addWidget(city_label)
            price_text = f"<b>{final}</b> монет"
            if self.trade_penalty > 0:
                price_text = f"<s>{base}</s> {price_text}"
            price_label = QLabel(price_text)
            price_label.setFixedWidth(100)
            row.addWidget(price_label)
            row.addWidget(QLabel("Кол-во:"))
            spin = QSpinBox()
            spin.setRange(1, max(1, goods))
            spin.setFixedWidth(90)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.setStyleSheet(
                "QSpinBox{background:#1a1a1a;color:white;border:1px solid #555;padding:2px;padding-right:20px;}")
            if goods == 0: spin.setEnabled(False)
            row.addWidget(spin)
            btn = QPushButton("Продать")
            btn.setStyleSheet(style_primary)
            if goods == 0: btn.setEnabled(False)
            btn.clicked.connect(lambda _, p=final, s=spin: self.sell(p, s.value(), dialog))
            row.addWidget(btn)
            row.addStretch()
            cl.addWidget(card)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        close = QPushButton("Закрыть")
        close.setStyleSheet(style_secondary)
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def sell(self, price, amount, dialog):
        money, _, goods, _, _, _, _ = self.db.get_player()
        if goods < amount:
            QMessageBox.warning(self, "Ошибка", "Нет столько товаров.")
            return
        earned = amount * price
        self.db.update_player(money=money + earned, goods=goods - amount)
        QMessageBox.information(self, "Сделка", f"Продано {amount} шт. за {earned} монет.")
        self.update_ui()
        dialog.accept()

    def found_note(self):
        found = self.db.get_found_notes_count()
        if found >= 5: return
        self.db.unlock_note(f"note_{found}")
        msg = QMessageBox(self)
        msg.setWindowTitle("Записка")
        msg.setText(f"{notes_data[found]}\n\nСбежать или остаться?")
        escape = msg.addButton("Сбежать", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Остаться", QMessageBox.ButtonRole.ActionRole)
        msg.exec()
        if msg.clickedButton() == escape:
            self.db.unlock_ending("escape")
            QMessageBox.information(self, "Побег", "Бежать некуда.")
            self.end_game()
        elif self.db.get_found_notes_count() == 5:
            self.db.unlock_ending("reveal")
            QMessageBox.information(self, "Разоблачение", "Вы раскрыли наш план. Можете покинуть симуляцию.")
            self.end_game()

    def end_game(self):
        self.stack.setCurrentWidget(self.menu)
        self.btn_continue.setEnabled(False)

    def next_season(self):
        money, mats, goods, season, pop, happy, eco = self.db.get_player()
        buildings_list = self.db.get_buildings()
        if money <= 0 or happy <= 0 or eco <= 0:
            self.db.unlock_ending("oblivion")
            QMessageBox.critical(self, "Забвение", "Вы не справились с обязанностями. Вы будуте стёрты.")
            self.end_game()
            return
        self.trade_banned = False
        self.trade_penalty = 0.0
        if self.tourists > 0:
            pop = max(2, pop - self.tourists)
            self.tourists = 0
        mod = random.choice(modifier_data)
        message_text = mod["message"]
        effect = mod["effect"]
        if "money" in effect:
            val = random.randint(*effect["money"])
            money += val
            message_text = message_text.format(val)
        if "pop" in effect:
            val = random.randint(*effect["pop"])
            pop += val
            self.tourists = val
            message_text = message_text.format(val)
        if "happy" in effect:
            val = random.randint(*effect["happy"])
            happy += val
            message_text = message_text.format(val)
        QMessageBox.information(self, mod["title"], message_text)
        if "ban" in effect: self.trade_banned = True
        if "pen" in effect: self.trade_penalty = effect["pen"]
        if "hack" in effect:
            for b in buildings_list:
                if building_data[b[2]]["cat"] == "house":
                    self.db.remove_building(b[0], b[1])
                    self.db.save_building(b[0], b[1], "Небоскрёб")
        income = income_mat = income_goods = eco_change = 0
        capacity = building_count = 0
        for _, _, bname in buildings_list:
            d = building_data[bname]
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
            if building_data[bname]["cat"] == "house":
                for obx, oby, obname in buildings_list:
                    if abs(bx - obx) + abs(by - oby) == 1 and building_data[obname]["cat"] == "ind":
                        happiness_penalty -= 4
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
        report = f"<b>Сезон {season} завершен!</b><br>"
        if new_money - money: report += f"💰: {new_money - money:+}<br>"
        if new_mats - mats: report += f"🧱: {new_mats - mats:+}<br>"
        if new_goods - goods: report += f"📦: {new_goods - goods:+}<br>"
        if new_pop - pop: report += f"👥: {new_pop - pop:+}<br>"
        if new_eco - eco: report += f"🌿: {new_eco - eco:+}%<br>"
        if new_happy - happy: report += f"😊: {new_happy - happy:+}%<br>"
        QMessageBox.information(self, "Итоги", report)
        found = self.db.get_found_notes_count()
        if not self.map_widget.note_pos:
            lagging = (season >= 4 and found == 0) or (season >= 8 and found < 2)
            if random.random() < 0.6 or lagging:
                occupied = [(b[0], b[1]) for b in buildings_list]
                spots = [(c, r) for c in range(cols_count) for r in range(rows_count) if (c, r) not in occupied]
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
                QMessageBox.critical(self, "Забвение", "Вы не справились с обязанностями. Вы будуте стёрты.")
            elif found >= 3:
                self.db.unlock_ending("ideal")
                QMessageBox.information(self, "Идеальный мэр", "Город процветает. Вы — Идеальный мэр.")
            else:
                self.db.unlock_ending("utopia")
                QMessageBox.information(self, "Утопия", "Все счастливы, но в не раскрыли тайну и попали в точно такой же город.")
            self.end_game()
            return
        self.db.update_player(season=season + 1)
        self.update_ui()

    def show_pause(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Пауза")
        dialog.setFixedSize(250, 250)
        dialog.setStyleSheet("background-color: #222; color: white;")
        layout = QVBoxLayout(dialog)
        for text, slot, style in [
            ("Продолжить", dialog.accept, style_primary),
            ("Справочник", lambda: HelpDialog(self).exec(), style_secondary),
            ("Достижения", lambda: EndingsDialog(self).exec(), style_secondary),
            ("В главное меню", lambda: (dialog.accept(), self.stack.setCurrentWidget(self.menu)), style_secondary)
        ]:
            btn = QPushButton(text)
            btn.setStyleSheet(style)
            btn.clicked.connect(slot)
            layout.addWidget(btn)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow()
    window.showFullScreen()
    sys.exit(app.exec())