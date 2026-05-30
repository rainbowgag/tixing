from app import create_app
from app.utils import create_backup

app = create_app()
with app.app_context():
    print(create_backup())
