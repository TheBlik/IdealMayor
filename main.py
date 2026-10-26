import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from database import Database

SCALE = 10
TILE_SIZE = 12
TILE_MARGIN = 4
GRID_STEP = TILE_SIZE + TILE_MARGIN

BUILDINGS = {
    "Частный дом": {
        "cost_money": 10,
        "cost_mat": 3,
        "img": "house1.png",
        "cat": "house",
    },
    "5-этажный дом": {
        "cost_money": 30,
        "cost_mat": 15,
        "img": "house2.png",
        "cat": "house",
    },
    "Многоэтажка": {
        "cost_money": 100,
        "cost_mat": 50,
        "img": "house3.png",
        "cat": "house",
    },
    "Мастерская": {
        "cost_money": 10,
        "cost_mat": 5,
        "img": "workshop.png",
        "cat": "ind",
    },
    "Малый завод": {
        "cost_money": 30,
        "cost_mat": 20,
        "img": "factory_small.png",
        "cat": "ind",
    },
    "Большой завод": {
        "cost_money": 100,
        "cost_mat": 60,
        "img": "factory_big.png",
        "cat": "ind",
    },
    "Сквер": {
        "cost_money": 5,
        "cost_mat": 2,
        "img": "square.png",
        "cat": "soc",
    },
    "Парк": {
        "cost_money": 10,
        "cost_mat": 5,
        "img": "park.png",
        "cat": "soc",
    },
    "Поликлиника": {
        "cost_money": 10,
        "cost_mat": 3,
        "img": "clinic.png",
        "cat": "soc",
    },
    "Больница": {
        "cost_money": 30,
        "cost_mat": 10,
        "img": "hospital.png",
        "cat": "soc",
    },
    "Школа": {
        "cost_money": 50,
        "cost_mat": 10,
        "img": "school.png",
        "cat": "soc",
    },
}


class GameMap(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.map_img = QPixmap("resources/map.png")
        self.buildings = []
        self.setMinimumSize(800, 600)

    def paintEvent(self, event):
        painter = QPainter(self)

        if not self.map_img.isNull():
            painter.drawPixmap(
                0, 0, self.map_img.scaled(self.width(), self.height())
            )
        else:
            painter.fillRect(self.rect(), QColor("#7BA05B"))

        w_ratio = self.width() / 192.0
        h_ratio = self.height() / 108.0

        painter.setPen(QColor(255, 255, 255, 120))
        painter.setBrush(QColor(255, 255, 255, 40))

        for y in range(12, 108 - TILE_SIZE, GRID_STEP):
            for x in range(12, 192 - TILE_SIZE, GRID_STEP):
                if not any(
                    b[0] == x and b[1] == y for b in self.buildings
                ):
                    painter.drawRect(
                        int(x * w_ratio),
                        int(y * h_ratio),
                        int(TILE_SIZE * w_ratio),
                        int(TILE_SIZE * h_ratio),
                    )

        for (x, y, name) in self.buildings:
            img_path = f"resources/buildings/{BUILDINGS[name]['img']}"
            pixmap = QPixmap(img_path)

            if not pixmap.isNull():
                painter.drawPixmap(
                    int(x * w_ratio),
                    int(y * h_ratio),
                    int(TILE_SIZE * w_ratio),
                    int(TILE_SIZE * h_ratio),
                    pixmap,
                )
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                sq_w = int(TILE_SIZE * w_ratio) // 4
                sq_h = int(TILE_SIZE * h_ratio) // 4

                for iy in range(4):
                    for ix in range(4):
                        if (ix + iy) % 2 == 0:
                            painter.setBrush(QColor("#1A1A1A"))
                        else:
                            painter.setBrush(QColor("#FF00FF"))

                        rect_x = int(x * w_ratio) + (ix * sq_w)
                        rect_y = int(y * h_ratio) + (iy * sq_h)

                        painter.drawRect(rect_x, rect_y, sq_w, sq_h)

    def mousePressEvent(self, event):
        w_ratio = self.width() / 192.0
        h_ratio = self.height() / 108.0

        click_x = int(event.pos().x() / w_ratio)
        click_y = int(event.pos().y() / h_ratio)

        for y in range(12, 108 - TILE_SIZE, GRID_STEP):
            for x in range(12, 192 - TILE_SIZE, GRID_STEP):
                if (
                    x <= click_x < x + GRID_STEP
                    and y <= click_y < y + GRID_STEP
                ):
                    for bx, by, bname in self.buildings:
                        if bx == x and by == y:
                            self.window.demolish_menu(x, y, bname)
                            return

                    self.window.open_build_menu(x, y)
                    return


class BuildDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Что строим?")
        self.resize(400, 400)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.list_house = QListWidget()
        self.list_ind = QListWidget()
        self.list_soc = QListWidget()

        for name, data in BUILDINGS.items():
            item = QListWidgetItem(
                f"{name} (💰{data['cost_money']} 🧱{data['cost_mat']})"
            )
            item.setData(Qt.ItemDataRole.UserRole, name)

            if data["cat"] == "house":
                self.list_house.addItem(item)
            elif data["cat"] == "ind":
                self.list_ind.addItem(item)
            elif data["cat"] == "soc":
                self.list_soc.addItem(item)

        self.tabs.addTab(self.list_house, "🏠 Жилье")
        self.tabs.addTab(self.list_ind, "🏭 Производство")
        self.tabs.addTab(self.list_soc, "🌳 Соцсфера")
        layout.addWidget(self.tabs)

        btn = QPushButton("Построить")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_selected(self):
        current_tab = self.tabs.currentWidget()
        item = current_tab.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class AchievementsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Достижения")
        self.resize(500, 400)

        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        endings = [
            "Идеальный мэр (3 записки и город развит)",
            "Разоблачение (Найдены все 5 записок)",
            "Побег (Сбежали из города)",
            "Утопия (Город развит, но тайна не раскрыта)",
            "Забвение (Показатели упали до нуля)",
        ]

        for text in endings:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "font-size: 16px; color: gray; padding: 5px;"
            )
            content_layout.addWidget(lbl)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn = QPushButton("Закрыть")
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
        title.setStyleSheet(
            "font-size: 50px; font-weight: bold; color: white; "
            "margin-bottom: 30px;"
        )
        menu_layout.addWidget(
            title, alignment=Qt.AlignmentFlag.AlignCenter
        )

        btn_start = QPushButton("Начать")
        btn_start.setFixedSize(250, 50)
        btn_start.clicked.connect(self.start_game)
        menu_layout.addWidget(
            btn_start, alignment=Qt.AlignmentFlag.AlignCenter
        )

        btn_continue = QPushButton("Продолжить")
        btn_continue.setFixedSize(250, 50)
        btn_continue.clicked.connect(self.show_game)
        menu_layout.addWidget(
            btn_continue, alignment=Qt.AlignmentFlag.AlignCenter
        )

        btn_ach = QPushButton("Достижения")
        btn_ach.setFixedSize(250, 50)
        btn_ach.clicked.connect(
            lambda: AchievementsDialog(self).exec()
        )
        menu_layout.addWidget(
            btn_ach, alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.stack.addWidget(self.menu_screen)

        self.game_screen = None
        self.stack.setCurrentWidget(self.menu_screen)

    def start_game(self):
        if self.db:
            self.db.conn.close()

        if os.path.exists("city.db"):
            os.remove("city.db")

        self.db = Database()
        self.show_game()

    def show_game(self):
        if not self.game_screen:
            self.game_screen = QWidget()

            self.map_widget = GameMap(self)
            self.map_widget.setParent(self.game_screen)

            self.season_label = QLabel("Сезон 1", self.game_screen)
            self.season_label.setStyleSheet(
                "color: white; background: rgba(0,0,0,150); "
                "font-size: 20px; padding: 5px;"
            )

            self.btn_next_season = QPushButton(
                "Завершить сезон", self.game_screen
            )
            self.btn_next_season.clicked.connect(self.next_season)

            self.btn_pause = QPushButton("⏸️", self.game_screen)
            self.btn_pause.clicked.connect(self.show_pause)

            self.res_label = QLabel("Ресурсы", self.game_screen)
            self.res_label.setStyleSheet(
                "color: white; background: rgba(0,0,0,150); "
                "font-size: 16px; padding: 15px;"
            )

            self.stack.addWidget(self.game_screen)

        self.stack.setCurrentWidget(self.game_screen)
        self.update_ui()
        self.resizeEvent(None)

    def resizeEvent(self, event):
        if event is not None:
            super().resizeEvent(event)

        if self.game_screen and self.map_widget:
            w, h = self.width(), self.height()

            self.map_widget.setGeometry(0, 0, w, h)
            self.season_label.setGeometry(10, 10, 150, 40)
            self.btn_pause.setGeometry(w - 60, 10, 50, 40)
            self.btn_next_season.setGeometry(w - 230, 10, 160, 40)
            self.res_label.setGeometry(10, h - 200, 250, 180)

    def update_ui(self):
        money, mats, season = self.db.get_player()

        self.season_label.setText(f"Сезон {season}")
        self.res_label.setText(
            f"💰 Деньги: {money}\n"
            f"🧱 Материалы: {mats}\n"
            f"👥 Население: 2\n"
            f"😊 Счастье: 100%\n"
            f"🌿 Экология: 100%"
        )

        self.map_widget.buildings = self.db.get_buildings()
        self.map_widget.update()

    def open_build_menu(self, x, y):
        dialog = BuildDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_selected()

            if name:
                data = BUILDINGS[name]
                money, mats, _ = self.db.get_player()

                if (
                    money >= data["cost_money"]
                    and mats >= data["cost_mat"]
                ):
                    self.db.update_player(
                        money=money - data["cost_money"],
                        materials=mats - data["cost_mat"],
                    )
                    self.db.save_building(x, y, name)
                    self.update_ui()
                else:
                    QMessageBox.warning(
                        self, "Ошибка", "Недостаточно ресурсов!"
                    )

    def demolish_menu(self, x, y, name):
        reply = QMessageBox.question(
            self,
            "Снос",
            f"Снести {name}?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_building(x, y)
            self.update_ui()

    def next_season(self):
        money, mats, season = self.db.get_player()
        self.db.update_player(season=season + 1)
        self.update_ui()

        QMessageBox.information(
            self, "Сезон", "Вы завершили сезон и начали новый!"
        )

    def show_pause(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Пауза")
        dialog.setFixedSize(250, 200)

        layout = QVBoxLayout(dialog)

        btn_resume = QPushButton("Продолжить")
        btn_resume.clicked.connect(dialog.accept)
        layout.addWidget(btn_resume)

        btn_ach = QPushButton("Достижения")
        btn_ach.clicked.connect(
            lambda: AchievementsDialog(self).exec()
        )
        layout.addWidget(btn_ach)

        btn_menu = QPushButton("Выйти в меню")
        btn_menu.clicked.connect(
            lambda: (
                dialog.accept(),
                self.stack.setCurrentWidget(self.menu_screen),
            )
        )
        layout.addWidget(btn_menu)

        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow()
    window.showFullScreen()
    sys.exit(app.exec())