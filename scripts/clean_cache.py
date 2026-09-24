import sqlite3
import shutil
from pathlib import Path

# Clean cache
with sqlite3.connect("data/translations_cache.sqlite") as conn:
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM cache WHERE translated_text = '...' OR length(translated_text) < 2")
    bad_count = cur.fetchone()[0]
    print(f"Bad cache entries found: {bad_count}")
    cur.execute("DELETE FROM cache WHERE translated_text = '...' OR length(translated_text) < 2")
    conn.commit()
    print("Cleaned translations cache.")

# Delete corrupt code-geass files
cg_dir = Path("subtitles/code-geass")
if cg_dir.exists():
    shutil.rmtree(cg_dir)
    print("Deleted corrupt code-geass files.")
