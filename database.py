import csv
import os
import sqlite3
import sys


def app_dir():
    """Папка для данных (bd, csv): рядом с .exe или main.py."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(".")

    # Создаем папку bd, если её нет
    data_dir = os.path.join(base, "bd")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


class Database:
    def __init__(self, db_name=None):
        if db_name is None:
            db_name = os.path.join(app_dir(), "city.db")
        self.db_path = db_name
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS player (id INTEGER PRIMARY KEY, money INTEGER, materials INTEGER, goods INTEGER, season INTEGER, population INTEGER, happiness INTEGER, ecology INTEGER)")
        self.cursor.execute("SELECT COUNT(*) FROM player")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute(
                "INSERT INTO player (money, materials, goods, season, population, happiness, ecology) VALUES (100, 100, 0, 1, 2, 100, 100)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS city_map (x INTEGER, y INTEGER, building TEXT, UNIQUE(x, y))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS endings (code TEXT PRIMARY KEY)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS notes (code TEXT PRIMARY KEY)")
        self.conn.commit()

    def get_player(self):
        self.cursor.execute(
            "SELECT money, materials, goods, season, population, happiness, ecology FROM player WHERE id=1")
        return tuple(self.cursor.fetchone())

    def update_player(self, **kwargs):
        if not kwargs: return
        updates = ", ".join(f"{k} = ?" for k in kwargs)
        self.cursor.execute(f"UPDATE player SET {updates} WHERE id=1", list(kwargs.values()))
        self.conn.commit()

    def save_building(self, x, y, name):
        self.cursor.execute("INSERT OR REPLACE INTO city_map (x, y, building) VALUES (?, ?, ?)", (x, y, name))
        self.conn.commit()

    def remove_building(self, x, y):
        self.cursor.execute("DELETE FROM city_map WHERE x = ? AND y = ?", (x, y))
        self.conn.commit()

    def get_buildings(self):
        self.cursor.execute("SELECT x, y, building FROM city_map")
        return [tuple(r) for r in self.cursor.fetchall()]

    def reset_progress(self):
        self.cursor.execute("DELETE FROM city_map")
        self.cursor.execute("DELETE FROM notes")
        self.cursor.execute(
            "UPDATE player SET money=100, materials=100, goods=0, season=1, population=2, happiness=100, ecology=100 WHERE id=1")
        self.conn.commit()
        for fname in ("city_stats.csv", "game_log.csv"):
            path = os.path.join(app_dir(), fname)
            if os.path.exists(path): os.remove(path)

    def log_action_to_csv(self, action_type, details):
        path = os.path.join(app_dir(), "game_log.csv")
        file_exists = os.path.isfile(path)
        with open(path, mode="a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            if not file_exists: writer.writerow(["Сезон", "Тип действия", "Детали"])
            writer.writerow([self.get_player()[3], action_type, details])

    def export_stats_to_csv(self):
        money, mats, goods, season, pop, happy, eco = self.get_player()
        path = os.path.join(app_dir(), "city_stats.csv")
        file_exists = os.path.isfile(path)
        with open(path, mode="a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            if not file_exists: writer.writerow(
                ["Сезон", "Деньги", "Материалы", "Товары", "Население", "Счастье", "Экология"])
            writer.writerow([season, money, mats, goods, pop, happy, eco])

    def unlock_ending(self, code):
        try:
            self.cursor.execute("INSERT INTO endings (code) VALUES (?)", (code,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_unlocked_endings(self):
        self.cursor.execute("SELECT code FROM endings")
        return [r[0] for r in self.cursor.fetchall()]

    def unlock_note(self, code):
        try:
            self.cursor.execute("INSERT INTO notes (code) VALUES (?)", (code,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_found_notes_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM notes")
        return self.cursor.fetchone()[0]

    def has_progress(self):
        self.cursor.execute("SELECT season, population FROM player WHERE id=1")
        season, pop = self.cursor.fetchone()
        self.cursor.execute("SELECT COUNT(*) FROM city_map")
        buildings = self.cursor.fetchone()[0]
        return season > 1 or buildings > 1 or pop > 2

    def close(self):
        self.conn.close()