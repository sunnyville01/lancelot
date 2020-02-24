import sqlite3

def create_table():
    conn = sqlite3.connect('lancelot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS results_W(Coin TEXT, Change Real, Exchange TEXT)')

create_table()
