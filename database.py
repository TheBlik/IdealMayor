import sqlite3

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("city.db")
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS player (
                id INTEGER PRIMARY KEY, money INTEGER, materials INTEGER, season INTEGER
            )
        """)
        self.cursor.execute("SELECT COUNT(*) FROM player")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("INSERT INTO player (money, materials, season) VALUES (50, 30, 1)")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_map (
                x INTEGER, y INTEGER, building TEXT
            )
        """)
        self.conn.commit()

    def get_player(self):
        self.cursor.execute("SELECT money, materials, season FROM player")
        return self.cursor.fetchone()

    def update_player(self, money=None, materials=None, season=None):
        updates, params = [], []
        if money is not None:
            updates.append("money = ?")
            params.append(money)
        if materials is not None:
            updates.append("materials = ?")
            params.append(materials)
        if season is not None:
            updates.append("season = ?")
            params.append(season)
        if updates:
            self.cursor.execute(f"UPDATE player SET {', '.join(updates)}", params)
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