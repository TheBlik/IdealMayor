import os
import random
import sys

from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QTimer
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QStackedWidget, QTabWidget, QVBoxLayout, QWidget, QGraphicsOpacityEffect
)
from database import Database


COLS = 16
ROWS = 9

BUILDINGS = {
    "Ратуша": {"cost_money": 0, "cost_mat": 0, "img": "townhall.png", "cat": "infra"},
    "Дорога": {"cost_money": 5, "cost_mat": 2, "img": "road.png", "cat": "road"},
    "Дом": {"cost_money": 30, "cost_mat": 10, "pop_limit": 5, "demolish_money": 15, "img": "house1.png",
            "cat": "house"},
    "Пятиэтажка": {"cost_money": 80, "cost_mat": 30, "pop_limit": 20, "demolish_money": 40, "img": "house2.png",
                   "cat": "house"},
    "Небоскрёб": {"cost_money": 250, "cost_mat": 120, "pop_limit": 80, "demolish_money": 125, "img": "house3.png",
                  "cat": "house"},
    "Мастерская": {"cost_money": 40, "cost_mat": 20, "income": 10, "income_mat": 5, "eco": -3, "demolish_money": 20,
                   "img": "workshop.png", "cat": "ind"},
    "Завод": {"cost_money": 100, "cost_mat": 50, "income": 25, "income_mat": 15, "eco": -8, "demolish_money": 50,
              "img": "factory1.png", "cat": "ind"},
    "Огромный завод": {"cost_money": 300, "cost_mat": 150, "income": 60, "income_mat": 40, "eco": -15,
                       "demolish_money": 150, "img": "factory2.png", "cat": "ind"},
    "Сквер": {"cost_money": 20, "cost_mat": 10, "eco": 4, "happiness": 3, "demolish_money": 10, "img": "park1.png",
              "cat": "soc"},
    "Парк": {"cost_money": 60, "cost_mat": 30, "eco": 10, "happiness": 6, "demolish_money": 30, "img": "park2.png",
             "cat": "soc"},
    "Поликлиника": {"cost_money": 80, "cost_mat": 40, "demolish_money": 40, "img": "hospital1.png", "cat": "soc"},
    "Больница": {"cost_money": 150, "cost_mat": 80, "demolish_money": 75, "img": "hospital2.png", "cat": "soc"},
    "Цирк": {"cost_money": 120, "cost_mat": 60, "income": 5, "happiness": 12, "demolish_money": 60, "img": "circus.png",
             "cat": "soc"}
}

ACHIEVEMENTS = [
    ("Не делай так", "Удалить ратушу", "townhall.png"),
    ("Трумэн", "Увидеть упавшее здание", "house1-fall.png"),
    ("Центр логистики", "Построить 10 дорог", "road-cross.png"),
    ("Москва-сити", "Построить 5 небоскрёбов", "house3.png"),
    ("Хорошее начало", "Получить первую концовку", "park1.png"),
    ("Опа, налоги", "Пройти первый сезон", "park2.png")
]

ENDINGS = [
    ("Идеальный мэр", "Найдено 3 записки и город развит", "house1.png"),
    ("Разоблачение", "Найти все 5 записок", "house2.png"),
    ("Утопия", "Город развит, но не найдено 3 записки", "workshop.png"),
    ("Побег", "Найдена 1 записка", "factory1.png"),
    ("Забвение", "Показатели упали до нуля", "factory2.png")
]


class AchievementToast(QLabel):
    def __init__(self, parent, title, img_path):
        super().__init__(parent)
        self.setStyleSheet("""
            background-color: #1a1a1a; color: white; 
            border: 2px solid #4CAF50; border-radius: 10px;
        """)
        self.setFixedSize(320, 80)

        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            icon = QLabel(self)
            icon.setPixmap(
                pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))
            icon.setStyleSheet("background: transparent; border: none;")
            icon.move(10, 10)

        text = QLabel(
            f"<b style='font-size: 12px; color: #4CAF50;'>ДОСТИЖЕНИЕ</b><br><span style='font-size: 14px;'>{title}</span>",
            self)
        text.setStyleSheet("background: transparent; border: none;")
        text.move(80, 15)

        start_x = (parent.width() - 320) // 2
        self.move(start_x, -100)

        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(500)
        self.anim.setStartValue(QPoint(start_x, -100))
        self.anim.setEndValue(QPoint(start_x, 20))
        self.anim.start()

        self.timer_hide = QTimer(self)
        self.timer_hide.setSingleShot(True)
        self.timer_hide.timeout.connect(self.hide_anim)
        self.timer_hide.start(3000)

    def hide_anim(self):
        self.anim2 = QPropertyAnimation(self, b"pos")
        self.anim2.setDuration(500)
        self.anim2.setStartValue(self.pos())
        self.anim2.setEndValue(QPoint(self.x(), -100))
        self.anim2.finished.connect(self.deleteLater)
        self.anim2.start()


class GameMap(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.map_img = QPixmap("resources/map.png")
        self.buildings = []

    def get_road_angle(self, col, row):
        top = any(b[0] == col and b[1] == row - 1 and BUILDINGS[b[2]]["cat"] == "road" for b in self.buildings)
        bottom = any(b[0] == col and b[1] == row + 1 and BUILDINGS[b[2]]["cat"] == "road" for b in self.buildings)
        left = any(b[0] == col - 1 and b[1] == row and BUILDINGS[b[2]]["cat"] == "road" for b in self.buildings)
        right = any(b[0] == col + 1 and b[1] == row and BUILDINGS[b[2]]["cat"] == "road" for b in self.buildings)
        connections = sum([top, bottom, left, right])

        if connections == 0:
            return "road.png", 0
        elif connections == 1:
            if top: return "road_end.png", 90
            if bottom: return "road_end.png", 270
            if left: return "road_end.png", 180
            if right: return "road_end.png", 0
        elif connections == 2:
            if top and bottom: return "road_v.png", 0
            if left and right: return "road_h.png", 0
            if top and right: return "road_turn.png", 0
            if right and bottom: return "road_turn.png", 90
            if bottom and left: return "road_turn.png", 180
            if left and top: return "road_turn.png", 270
        elif connections == 3:
            if not top: return "road_t.png", 0
            if not right: return "road_t.png", 90
            if not bottom: return "road_t.png", 180
            if not left: return "road_t.png", 270
        else:
            return "road_cross.png", 0
        return "road.png", 0

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.map_img.isNull():
            painter.drawPixmap(0, 0, self.map_img.scaled(self.width(), self.height()))
        else:
            painter.fillRect(self.rect(), QColor("#7BA05B"))

        cell_w = self.width() / COLS
        cell_h = self.height() / ROWS

        painter.setPen(QColor(255, 255, 255, 40))
        for col in range(COLS + 1):
            painter.drawLine(int(col * cell_w), 0, int(col * cell_w), self.height())
        for row in range(ROWS + 1):
            painter.drawLine(0, int(row * cell_h), self.width(), int(row * cell_h))

        painter.setPen(Qt.PenStyle.NoPen)
        for (col, row, name) in self.buildings:
            px = col * cell_w
            py = row * cell_h
            img_name = BUILDINGS[name]['img']
            angle = 0
            if BUILDINGS[name]["cat"] == "road":
                img_name, angle = self.get_road_angle(col, row)

            pixmap = QPixmap(f"resources/buildings/{img_name}")

            if not pixmap.isNull():
                painter.save()
                if angle != 0:
                    center_x = int(px + cell_w / 2)
                    center_y = int(py + cell_h / 2)
                    painter.translate(center_x, center_y)
                    painter.rotate(angle)
                    painter.translate(-center_x, -center_y)
                painter.drawPixmap(int(px), int(py), int(cell_w), int(cell_h), pixmap)
                painter.restore()
            else:
                sq_w = cell_w / 4
                sq_h = cell_h / 4
                for iy in range(4):
                    for ix in range(4):
                        color = QColor("#1A1A1A") if (ix + iy) % 2 == 0 else QColor("#FF00FF")
                        painter.setBrush(color)
                        painter.drawRect(int(px + ix * sq_w), int(py + iy * sq_h), int(sq_w), int(sq_h))

    def mousePressEvent(self, event):
        cell_w = self.width() / COLS
        cell_h = self.height() / ROWS
        col = int(event.pos().x() / cell_w)
        row = int(event.pos().y() / cell_h)

        if 0 <= col < COLS and 0 <= row < ROWS:
            for bx, by, bname in self.buildings:
                if bx == col and by == row:
                    if bname == "Ратуша":
                        self.window.show_achievement("Не делай так", "townhall.png")
                        QMessageBox.information(self, "Ратуша", "Это здание нельзя снести!")
                        return
                    self.window.demolish_menu(col, row, bname)
                    return
            self.window.open_build_menu(col, row)


class BuildDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Что строим?")
        self.resize(400, 400)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.list_infra = QListWidget()
        self.list_house = QListWidget()
        self.list_ind = QListWidget()
        self.list_soc = QListWidget()

        for name, data in BUILDINGS.items():
            if name == "Ратуша": continue
            if data["cat"] == "road" and name != "Дорога": continue
            item = QListWidgetItem(f"{name} (💰{data['cost_money']} 🧱{data['cost_mat']})")
            item.setData(Qt.ItemDataRole.UserRole, name)
            if data["cat"] == "road":
                self.list_infra.addItem(item)
            elif data["cat"] == "house":
                self.list_house.addItem(item)
            elif data["cat"] == "ind":
                self.list_ind.addItem(item)
            elif data["cat"] == "soc":
                self.list_soc.addItem(item)

        self.tabs.addTab(self.list_infra, "🛣️ Инфра")
        self.tabs.addTab(self.list_house, "🏠 Жилье")
        self.tabs.addTab(self.list_ind, "🏭 Производство")
        self.tabs.addTab(self.list_soc, "🌳 Соцсфера")
        layout.addWidget(self.tabs)

        btn = QPushButton("Построить")
        btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_selected(self):
        current_tab = self.tabs.currentWidget()
        item = current_tab.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class AchievementsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Достижения и Концовки")
        self.resize(600, 500)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        unlocked = parent.db.get_unlocked_achievements()

        tab_ach = QWidget()
        layout_ach = QVBoxLayout(tab_ach)
        scroll_ach = QScrollArea()
        scroll_ach.setWidgetResizable(True)
        content_ach = QWidget()
        content_layout_ach = QVBoxLayout(content_ach)

        for title, desc, img in ACHIEVEMENTS:
            is_unlocked = title in unlocked
            block = QWidget()
            block_layout = QHBoxLayout(block)
            bg_color = "#2b2b2b" if is_unlocked else "#111111"
            block.setStyleSheet(f"background-color: {bg_color}; border-radius: 5px; margin-bottom: 5px;")

            img_label = QLabel()
            img_label.setFixedSize(64, 64)
            pixmap = QPixmap(f"resources/achievements/{img}")
            if not pixmap.isNull():
                if not is_unlocked:
                    effect = QGraphicsOpacityEffect()
                    effect.setOpacity(0.3)
                    img_label.setGraphicsEffect(effect)
                img_label.setPixmap(
                    pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))
            else:
                img_label.setStyleSheet("background-color: #555; border-radius: 5px;")

            color = "white" if is_unlocked else "gray"
            text_label = QLabel(
                f"<b style='font-size: 16px; color: {color};'>{title}</b><br><span style='color: gray;'>{desc}</span>")
            block_layout.addWidget(img_label)
            block_layout.addWidget(text_label)
            block_layout.addStretch()
            content_layout_ach.addWidget(block)

        scroll_ach.setWidget(content_ach)
        layout_ach.addWidget(scroll_ach)
        self.tabs.addTab(tab_ach, "🏆 Достижения")

        tab_end = QWidget()
        layout_end = QVBoxLayout(tab_end)
        scroll_end = QScrollArea()
        scroll_end.setWidgetResizable(True)
        content_end = QWidget()
        content_layout_end = QVBoxLayout(content_end)

        for title, desc, img in ENDINGS:
            block = QWidget()
            block_layout = QHBoxLayout(block)
            block.setStyleSheet("background-color: #2b2b2b; border-radius: 5px; margin-bottom: 5px;")
            img_label = QLabel()
            img_label.setFixedSize(64, 64)
            pixmap = QPixmap(f"resources/achievements/{img}")
            if not pixmap.isNull():
                img_label.setPixmap(
                    pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))
            else:
                img_label.setStyleSheet("background-color: #555; border-radius: 5px;")
            text_label = QLabel(
                f"<b style='font-size: 16px; color: white;'>{title}</b><br><span style='color: gray;'>{desc}</span>")
            block_layout.addWidget(img_label)
            block_layout.addWidget(text_label)
            block_layout.addStretch()
            content_layout_end.addWidget(block)

        scroll_end.setWidget(content_end)
        layout_end.addWidget(scroll_end)
        self.tabs.addTab(tab_end, "🎬 Концовки")

        layout.addWidget(self.tabs)
        btn = QPushButton("Закрыть")
        btn.setStyleSheet("padding: 8px; font-weight: bold;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Идеальный мэр")
        self.db = Database()
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.menu_screen = QWidget()
        menu_layout = QVBoxLayout(self.menu_screen)
        menu_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("ИДЕАЛЬНЫЙ МЭР")
        title.setStyleSheet("font-size: 50px; font-weight: bold; color: white; margin-bottom: 30px;")
        menu_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_start = QPushButton("Начать")
        btn_start.setFixedSize(250, 50)
        btn_start.clicked.connect(self.start_game)
        menu_layout.addWidget(btn_start, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_continue = QPushButton("Продолжить")
        btn_continue.setFixedSize(250, 50)
        btn_continue.clicked.connect(self.show_game)
        menu_layout.addWidget(btn_continue, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_ach = QPushButton("Достижения")
        btn_ach.setFixedSize(250, 50)
        btn_ach.clicked.connect(lambda: AchievementsDialog(self).exec())
        menu_layout.addWidget(btn_ach, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stack.addWidget(self.menu_screen)
        self.game_screen = None
        self.stack.setCurrentWidget(self.menu_screen)

    def show_achievement(self, title, img):
        if self.db.unlock_achievement(title):
            toast = AchievementToast(self, title, f"resources/achievements/{img}")
            toast.show()
            toast.raise_()

    def start_game(self):
        if self.db: self.db.conn.close()
        if os.path.exists("city.db"):
            try:
                os.remove("city.db")
            except:
                pass
        self.db = Database()
        self.db.save_building(8, 4, "Ратуша")
        self.show_game()

    def show_game(self):
        money, mats, season, pop, happy, eco = self.db.get_player()
        if season > 12:
            QMessageBox.information(self, "Конец", "Эта игра уже завершена. Начните новую!")
            return

        if self.game_screen:
            self.stack.removeWidget(self.game_screen)
            self.game_screen.deleteLater()

        self.game_screen = QWidget()
        self.map_widget = GameMap(self)
        self.map_widget.setParent(self.game_screen)

        self.season_label = QLabel("Сезон 1", self.game_screen)
        self.season_label.setStyleSheet("color: white; background: rgba(0,0,0,150); font-size: 20px; padding: 5px;")

        self.btn_next_season = QPushButton("Завершить сезон", self.game_screen)
        self.btn_next_season.clicked.connect(self.next_season)

        self.btn_pause = QPushButton("⏸️", self.game_screen)
        self.btn_pause.clicked.connect(self.show_pause)

        self.res_label = QLabel("Ресурсы", self.game_screen)
        self.res_label.setStyleSheet("color: white; background: rgba(0,0,0,150); font-size: 16px; padding: 15px;")

        self.stack.addWidget(self.game_screen)
        self.stack.setCurrentWidget(self.game_screen)

        self.update_ui()
        self.resizeEvent(None)

    def resizeEvent(self, event):
        if event is not None:
            super().resizeEvent(event)
        if self.game_screen and hasattr(self, 'map_widget'):
            w, h = self.width(), self.height()
            self.map_widget.setGeometry(0, 0, w, h)
            self.season_label.setGeometry(10, 10, 150, 40)
            self.btn_pause.setGeometry(w - 60, 10, 50, 40)
            self.btn_next_season.setGeometry(w - 230, 10, 160, 40)
            self.res_label.setGeometry(10, h - 200, 250, 180)

    def update_ui(self):
        if not self.db: return
        money, mats, season, pop, happy, eco = self.db.get_player()
        self.season_label.setText(f"Сезон {season}")
        self.res_label.setText(
            f"💰 Деньги: {money}\n🧱 Материалы: {mats}\n👥 Население: {pop}\n😊 Счастье: {happy}%\n🌿 Экология: {eco}%")
        if hasattr(self, 'map_widget'):
            self.map_widget.buildings = self.db.get_buildings()
            self.map_widget.update()

    def has_road_nearby(self, col, row):
        neighbors = [(col - 1, row), (col + 1, row), (col, row - 1), (col, row + 1)]
        for bx, by, bname in self.db.get_buildings():
            if (bx, by) in neighbors and bname == "Дорога":
                return True
        return False

    def open_build_menu(self, col, row):
        dialog = BuildDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_selected()
            if name:
                data = BUILDINGS[name]
                money, mats, season, pop, happy, eco = self.db.get_player()

                if name != "Дорога" and name != "Ратуша" and not self.has_road_nearby(col, row):
                    QMessageBox.warning(self, "Ошибка", "Здесь нет дороги! Постройте дорогу рядом.")
                    return

                if money >= data["cost_money"] and mats >= data["cost_mat"]:
                    self.db.update_player(money=money - data["cost_money"], materials=mats - data["cost_mat"])
                    self.db.save_building(col, row, name)
                    self.update_ui()
                else:
                    QMessageBox.warning(self, "Ошибка", "Недостаточно ресурсов!")

    def demolish_menu(self, col, row, name):
        reply = QMessageBox.question(self, "Снос", f"Снести {name}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            data = BUILDINGS[name]
            money, mats, season, pop, happy, eco = self.db.get_player()
            refund_money = data.get("demolish_money", 0)
            refund_mat = data.get("demolish_mat", 0)
            self.db.update_player(money=money + refund_money, materials=mats + refund_mat)
            self.db.remove_building(col, row)
            self.update_ui()

    def next_season(self):
        money, mats, season, pop, happy, eco = self.db.get_player()
        buildings = self.db.get_buildings()

        income, income_mat, eco_change = 0, 0, 0
        for bx, by, bname in buildings:
            data = BUILDINGS[bname]
            income += data.get("income", 0)
            income_mat += data.get("income_mat", 0)
            eco_change += data.get("eco", 0)

        synergy_income = 0
        synergy_eco = 0
        for bx, by, bname in buildings:
            if BUILDINGS[bname]["cat"] == "ind":
                neighbors = [(bx - 1, by), (bx + 1, by), (bx, by - 1), (bx, by + 1)]
                for nx, ny in neighbors:
                    for obx, oby, obname in buildings:
                        if obx == nx and oby == ny and BUILDINGS[obname]["cat"] == "ind":
                            synergy_income += 5
                            synergy_eco -= 1

        happiness_penalty = 0
        for bx, by, bname in buildings:
            if BUILDINGS[bname]["cat"] == "house":
                neighbors = [(bx - 1, by), (bx + 1, by), (bx, by - 1), (bx, by + 1)]
                for nx, ny in neighbors:
                    for obx, oby, obname in buildings:
                        if obx == nx and oby == ny and BUILDINGS[obname]["cat"] == "ind":
                            happiness_penalty -= 3

        taxes = pop
        new_money = money + income + synergy_income + taxes
        new_mats = mats + income_mat
        new_eco = max(0, min(100, eco + eco_change + synergy_eco))
        new_happy = max(0, min(100, happy + happiness_penalty))

        self.db.update_player(money=new_money, materials=new_mats, ecology=new_eco, happiness=new_happy)

        if season == 1:
            self.show_achievement("Опа, налоги", "park2.png")

        roads_count = sum(1 for b in buildings if b[2] == "Дорога")
        if roads_count >= 10:
            self.show_achievement("Центр логистики", "road-cross.png")

        skyscrapers = sum(1 for b in buildings if b[2] == "Небоскрёб")
        if skyscrapers >= 5:
            self.show_achievement("Москва-сити", "house3.png")

        if season >= 12:
            self.db.update_player(season=99)
            QMessageBox.information(self, "Конец", "Вы прошли 12 сезонов! Игра окончена.")
            self.show_achievement("Хорошее начало", "park1.png")
            self.stack.setCurrentWidget(self.menu_screen)
            return

        self.db.update_player(season=season + 1)
        self.update_ui()

        report = (
            f"Сезон {season} завершен!\n\n"
            f"💰 Доход с заводов: +{income}\n"
            f"🤝 Бонус за кластеры: +{synergy_income}\n"
            f"💰 Налоги: +{taxes}\n"
            f"🧱 Материалы: +{income_mat}\n"
            f"🌿 Изменение экологии: {eco_change + synergy_eco}%\n"
            f"😊 Штраф от заводов: {happiness_penalty}%"
        )
        QMessageBox.information(self, "Отчет", report)

    def show_pause(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Пауза")
        dialog.setFixedSize(250, 200)
        layout = QVBoxLayout(dialog)
        btn_resume = QPushButton("Продолжить")
        btn_resume.clicked.connect(dialog.accept)
        layout.addWidget(btn_resume)
        btn_ach = QPushButton("Достижения")
        btn_ach.clicked.connect(lambda: AchievementsDialog(self).exec())
        layout.addWidget(btn_ach)
        btn_menu = QPushButton("Выйти в меню")
        btn_menu.clicked.connect(lambda: (dialog.accept(), self.stack.setCurrentWidget(self.menu_screen)))
        layout.addWidget(btn_menu)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow()
    window.showFullScreen()
    sys.exit(app.exec())