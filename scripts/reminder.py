import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import Renewal
from app.utils import get_reminder_notices, send_reminder_email

app = create_app()
with app.app_context():
    notices = get_reminder_notices()
    print(f"checked {Renewal.query.count()} renewal records, matched {len(notices)} reminder items")
    for item in notices:
        print(f"- {item.customer.name if item.customer else ''} / {item.device.name if item.device else ''} / {item.line.code if item.line else ''}: {item.expire_date}, {item.days_left} days left")
    print(f"sent {send_reminder_email()} reminder items")
