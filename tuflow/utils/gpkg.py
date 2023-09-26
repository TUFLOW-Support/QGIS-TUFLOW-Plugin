import os
import re


class GPKG:
    """A class that helps with GPKGs."""

    def __init__(self, gpkg_path):
        self.gpkg_path = str(gpkg_path)

    def glob(self, pattern):
        """Do a glob search of the database for tables matching the pattern."""

        p = pattern.replace('*', '.*')
        for lyr in self.layers():
            if re.findall(p, lyr, flags=re.IGNORECASE):
                yield lyr

    def layers(self):
        """Return the GPKG layers in the database."""
        import sqlite3

        res = []

        if not os.path.exists(self.gpkg_path):
            return res

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()

        try:
            cur.execute(f"SELECT table_name FROM gpkg_contents;")
            res = [x[0] for x in cur.fetchall()]
        except Exception:
            pass
        finally:
            cur.close()

        return res