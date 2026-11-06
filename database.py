import sqlite3
import csv
import os


class Database:
    def __init__(self, db_name="city.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS player (
                id INTEGER PRIMARY KEY, money INTEGER, materials INTEGER, goods INTEGER,
                season INTEGER, population INTEGER, happiness INTEGER, ecology INTEGER
            )
        """)

        self.cursor.execute("SELECT COUNT(*) FROM player")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("""
                INSERT INTO player (money, materials, goods, season, population, happiness, ecology) 
                VALUES (100, 100, 0, 1, 2, 100, 100)
            """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_map (x INTEGER, y INTEGER, building TEXT)
        """)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS endings (code TEXT PRIMARY KEY)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS notes (code TEXT PRIMARY KEY)")
        self.conn.commit()

    def get_player(self):
        self.cursor.execute(
            "SELECT money, materials, goods, season, population, happiness, ecology FROM player WHERE id=1")
        return self.cursor.fetchone()

    def update_player(self, **kwargs):
        updates, params = [], []
        for key, val in kwargs.items():
            updates.append(f"{key} = ?")
            params.append(val)
        if updates:
            self.cursor.execute(f"UPDATE player SET {', '.join(updates)} WHERE id=1", params)
            self.conn.commit()

    def save_building(self, x, y, name):
        self.cursor.execute("INSERT INTO city_map (x, y, building) VALUES (?, ?, ?)", (x, y, name))
        self.conn.commit()

    def remove_building(self, x, y):
        self.cursor.execute("DELETE FROM city_map WHERE x = ? AND y = ?", (x, y))
        self.conn.commit()

    def get_buildings(self):
        self.cursor.execute("SELECT x, y, building FROM city_map")
        return self.cursor.fetchall()

    def reset_progress(self):
        self.cursor.execute("DELETE FROM city_map")
        self.cursor.execute("DELETE FROM notes")
        self.cursor.execute("""
            UPDATE player SET money=100, materials=100, goods=0, season=1, population=2, happiness=100, ecology=100 WHERE id=1
        """)
        self.conn.commit()

        if os.path.exists("city_stats.csv"): os.remove("city_stats.csv")
        if os.path.exists("game_log.csv"): os.remove("game_log.csv")

    def log_action_to_csv(self, action_type, details):
        file_exists = os.path.isfile("game_log.csv")
        with open("game_log.csv", mode="a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            if not file_exists:
                writer.writerow(["Сезон", "Тип действия", "Детали"])
            season = self.get_player()[3]
            writer.writerow([season, action_type, details])

    def export_stats_to_csv(self):
        money, mats, goods, season, pop, happy, eco = self.get_player()
        file_exists = os.path.isfile("city_stats.csv")
        with open("city_stats.csv", mode="a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            if not file_exists:
                writer.writerow(["Сезон", "Деньги", "Материалы", "Товары", "Население", "Счастье", "Экология"])
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
        return [row[0] for row in self.cursor.fetchall()]

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

    def close(self):
        self.conn.close()