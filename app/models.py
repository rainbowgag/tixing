import os
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), default="")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def ensure_default_admin(cls):
        if cls.query.first():
            return
        user = cls(username=os.getenv("ADMIN_USERNAME", "admin"), email=os.getenv("ADMIN_EMAIL", ""))
        user.set_password(os.getenv("ADMIN_PASSWORD", "admin123456"))
        db.session.add(user)
        db.session.commit()


class Customer(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    contact = db.Column(db.String(120), default="")
    wechat = db.Column(db.String(120), default="")
    telegram = db.Column(db.String(120), default="")
    email = db.Column(db.String(255), default="")
    phone = db.Column(db.String(60), default="")
    status = db.Column(db.String(20), default="正常")
    remark = db.Column(db.Text, default="")
    devices = db.relationship("Device", backref="customer", lazy=True)
    lines = db.relationship("Line", backref="customer", lazy=True)
    remotes = db.relationship("RemoteAccess", backref="customer", lazy=True)
    renewals = db.relationship("Renewal", backref="customer", lazy=True)


class Device(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=True)
    country = db.Column(db.String(80), default="")
    device_type = db.Column(db.String(120), default="")
    remark = db.Column(db.Text, default="")
    remotes = db.relationship("RemoteAccess", backref="device", lazy=True)
    renewals = db.relationship("Renewal", backref="device", lazy=True)


class Line(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=True)
    code = db.Column(db.String(120), nullable=False, index=True)
    country = db.Column(db.String(80), default="")
    line_type = db.Column(db.String(120), default="")
    remark = db.Column(db.Text, default="")
    renewals = db.relationship("Renewal", backref="line", lazy=True)


class RemoteAccess(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id"), nullable=True)
    address = db.Column(db.String(255), nullable=False, index=True)
    username = db.Column(db.String(120), default="")
    password = db.Column(db.String(255), default="")
    remark = db.Column(db.Text, default="")

    @property
    def owner_customer(self):
        return self.customer or (self.device.customer if self.device else None)


class Renewal(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id"), nullable=True)
    line_id = db.Column(db.Integer, db.ForeignKey("line.id"), nullable=True)
    price = db.Column(db.Numeric(10, 2), default=0)
    start_date = db.Column(db.Date, nullable=True)
    expire_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), default="正常")
    remark = db.Column(db.Text, default="")

    @property
    def days_left(self):
        return (self.expire_date - datetime.utcnow().date()).days

    @property
    def computed_status(self):
        if self.status == "已续费":
            return self.status
        if self.days_left < 0:
            return "已到期"
        if self.days_left <= 7:
            return "即将到期"
        return "正常"
