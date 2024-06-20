import os
import sys


def get_base_path():
    if getattr(sys, 'frozen', False):
        # The application is bundled
        return sys._MEIPASS
    else:
        # The application is not bundled
        return os.path.dirname(os.path.abspath(__file__))


def get_database_url():
    base_path = get_base_path()
    db_path = os.path.join(base_path, 'db', 'auto_db.sqlite')
    return f"sqlite:///{db_path}"
