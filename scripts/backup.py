import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.utils import create_backup

app = create_app()
with app.app_context():
    print(create_backup())
