import sqlite3


class Database:
    def __init__(self):
        self.conn = sqlite3.connect("city.db")
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS player (
                id INTEGER PRIMARY KEY, money INTEGER, materials INTEGER, 
                season INTEGER, population INTEGER, happiness INTEGER, ecology INTEGER
            )
        """)
        self.cursor.execute("SELECT COUNT(*) FROM player")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("""
                INSERT INTO player (money, materials, season, population, happiness, ecology) 
                VALUES (50, 100, 1, 2, 100, 100)
            """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_map (
                x INTEGER, y INTEGER, building TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                code TEXT PRIMARY KEY
            )
        """)
        self.conn.commit()

    def get_player(self):
        self.cursor.execute("SELECT money, materials, season, population, happiness, ecology FROM player WHERE id=1")
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

    def unlock_achievement(self, code):
        try:
            self.cursor.execute("INSERT INTO achievements (code) VALUES (?)", (code,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_unlocked_achievements(self):
        self.cursor.execute("SELECT code FROM achievements")
        return [row[0] for row in self.cursor.fetchall()]