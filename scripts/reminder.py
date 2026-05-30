from app import create_app
from app.utils import send_reminder_email

app = create_app()
with app.app_context():
    print(f"sent {send_reminder_email()} reminder items")
