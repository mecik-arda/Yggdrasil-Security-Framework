import sqlite3

def init_db():
    conn = sqlite3.connect('stats.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY, total_scans INTEGER, last_target TEXT, active_tool TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scan_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT UNIQUE, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, tool TEXT, target TEXT, status TEXT, output TEXT)''')
    c.execute('SELECT COUNT(*) FROM stats')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO stats (total_scans, last_target, active_tool) VALUES (0, "NONE", "IDLE")')
    conn.commit()
    conn.close()

def get_db_stats():
    conn = sqlite3.connect('stats.db')
    c = conn.cursor()
    c.execute('SELECT total_scans, last_target, active_tool FROM stats WHERE id=1')
    row = c.fetchone()
    conn.close()
    return {'total_scans': row[0], 'last_target': row[1], 'active_tool': row[2]}

def update_db_stats(target, tool):
    conn = sqlite3.connect('stats.db')
    c = conn.cursor()
    c.execute('UPDATE stats SET total_scans = total_scans + 1, last_target = ?, active_tool = ? WHERE id=1', (target, tool))
    conn.commit()
    conn.close()

def log_scan_start(task_id, tool, target):
    try:
        conn = sqlite3.connect('stats.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO scan_history (task_id, tool, target, status, output) VALUES (?, ?, ?, ?, ?)',
                  (task_id, tool.upper(), target, 'RUNNING', ''))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging scan start: {e}")

def log_scan_end(task_id, status, output):
    try:
        conn = sqlite3.connect('stats.db')
        c = conn.cursor()
        c.execute('UPDATE scan_history SET status = ?, output = ? WHERE task_id = ?',
                  (status, output, task_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging scan end: {e}")
