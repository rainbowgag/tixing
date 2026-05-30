import os
from calendar import monthrange
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from .models import Customer, Device, Line, RemoteAccess, Renewal, db
from .utils import create_backup, export_workbook, global_search, list_backups, money, parse_date, send_reminder_email

bp = Blueprint("main", __name__)


def form_value(name, default=""):
    return request.form.get(name, default).strip()


def ensure_customer_device(customer_id):
    if not customer_id:
        return None
    customer_id = int(customer_id)
    device = Device.query.filter_by(customer_id=customer_id).order_by(Device.id.asc()).first()
    if device:
        return device.id
    customer = db.session.get(Customer, customer_id)
    name = f"{customer.name}-默认设备" if customer else "默认设备"
    device = Device(name=name, customer_id=customer_id, remark="系统自动创建，用于兼容续费和远程信息")
    db.session.add(device)
    db.session.flush()
    return device.id


def add_one_month(value):
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@bp.route("/")
@login_required
def dashboard():
    today = datetime.utcnow().date()
    renewals = Renewal.query.all()
    stats = {
        "customers": Customer.query.count(),
        "lines": Line.query.count(),
        "expiring_7": sum(1 for r in renewals if 0 <= (r.expire_date - today).days <= 7 and r.status != "已续费"),
        "expiring_3": sum(1 for r in renewals if 0 <= (r.expire_date - today).days <= 3 and r.status != "已续费"),
        "expired": sum(1 for r in renewals if (r.expire_date - today).days < 0 and r.status != "已续费"),
    }
    recent = Renewal.query.order_by(Renewal.updated_at.desc()).limit(8).all()
    return render_template("dashboard.html", stats=stats, recent=recent)


@bp.route("/customers")
@login_required
def customers():
    q = request.args.get("q", "").strip()
    query = Customer.query
    if q:
        query = query.filter((Customer.name.like(f"%{q}%")) | (Customer.contact.like(f"%{q}%")) | (Customer.remark.like(f"%{q}%")))
    return render_template("customers.html", items=query.order_by(Customer.id.desc()).all(), q=q)


@bp.route("/customers/new", methods=["GET", "POST"])
@bp.route("/customers/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def customer_form(item_id=None):
    item = db.session.get(Customer, item_id) if item_id else Customer()
    if request.method == "POST":
        item.name = form_value("name")
        item.contact = form_value("contact")
        item.wechat = form_value("wechat")
        item.telegram = form_value("telegram")
        item.email = form_value("email")
        item.phone = form_value("phone")
        item.status = form_value("status", "正常")
        item.remark = form_value("remark")
        db.session.add(item)
        db.session.commit()
        flash("客户信息已保存", "success")
        return redirect(url_for("main.customers"))
    return render_template("customer_form.html", item=item)


@bp.route("/customers/<int:item_id>")
@login_required
def customer_detail(item_id):
    item = Customer.query.get_or_404(item_id)
    lines = Line.query.filter_by(customer_id=item.id).order_by(Line.id.desc()).all()
    remotes = (
        RemoteAccess.query.outerjoin(Device)
        .filter((RemoteAccess.customer_id == item.id) | (Device.customer_id == item.id))
        .order_by(RemoteAccess.id.desc())
        .all()
    )
    return render_template("customer_detail.html", item=item, lines=lines, remotes=remotes)


@bp.route("/customers/<int:item_id>/delete", methods=["POST"])
@login_required
def customer_delete(item_id):
    db.session.delete(Customer.query.get_or_404(item_id))
    db.session.commit()
    flash("客户已删除", "success")
    return redirect(url_for("main.customers"))


@bp.route("/devices")
@login_required
def devices():
    q = request.args.get("q", "").strip()
    query = Device.query
    if q:
        query = query.filter((Device.name.like(f"%{q}%")) | (Device.country.like(f"%{q}%")) | (Device.remark.like(f"%{q}%")))
    return render_template("devices.html", items=query.order_by(Device.id.desc()).all(), q=q)


@bp.route("/devices/new", methods=["GET", "POST"])
@bp.route("/devices/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def device_form(item_id=None):
    item = db.session.get(Device, item_id) if item_id else Device()
    if request.method == "POST":
        item.name = form_value("name")
        item.customer_id = request.form.get("customer_id") or None
        item.country = form_value("country")
        item.device_type = form_value("device_type")
        item.remark = form_value("remark")
        db.session.add(item)
        db.session.commit()
        flash("设备信息已保存", "success")
        return redirect(url_for("main.devices"))
    return render_template("device_form.html", item=item, customers=Customer.query.order_by(Customer.name).all())


@bp.route("/devices/<int:item_id>")
@login_required
def device_detail(item_id):
    return render_template("device_detail.html", item=Device.query.get_or_404(item_id))


@bp.route("/devices/<int:item_id>/delete", methods=["POST"])
@login_required
def device_delete(item_id):
    db.session.delete(Device.query.get_or_404(item_id))
    db.session.commit()
    flash("设备已删除", "success")
    return redirect(url_for("main.devices"))


@bp.route("/lines")
@login_required
def lines():
    q = request.args.get("q", "").strip()
    query = Line.query.outerjoin(Customer)
    if q:
        query = query.filter((Line.code.like(f"%{q}%")) | (Line.country.like(f"%{q}%")) | (Line.remark.like(f"%{q}%")) | (Customer.name.like(f"%{q}%")))
    return render_template("lines.html", items=query.order_by(Line.id.desc()).all(), q=q)


@bp.route("/lines/new", methods=["GET", "POST"])
@bp.route("/lines/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def line_form(item_id=None):
    item = db.session.get(Line, item_id) if item_id else Line()
    if request.method == "POST":
        item.customer_id = request.form.get("customer_id") or None
        item.code = form_value("code")
        item.country = form_value("country")
        item.line_type = form_value("line_type")
        item.remark = form_value("remark")
        db.session.add(item)
        db.session.commit()
        flash("线路信息已保存", "success")
        return redirect(url_for("main.lines"))
    return render_template("line_form.html", item=item, customers=Customer.query.order_by(Customer.name).all())


@bp.route("/lines/<int:item_id>/delete", methods=["POST"])
@login_required
def line_delete(item_id):
    db.session.delete(Line.query.get_or_404(item_id))
    db.session.commit()
    flash("线路已删除", "success")
    return redirect(url_for("main.lines"))


@bp.route("/remotes")
@login_required
def remotes():
    q = request.args.get("q", "").strip()
    query = RemoteAccess.query.outerjoin(Customer, RemoteAccess.customer_id == Customer.id)
    if q:
        query = query.filter((RemoteAccess.address.like(f"%{q}%")) | (RemoteAccess.username.like(f"%{q}%")) | (RemoteAccess.remark.like(f"%{q}%")) | (Customer.name.like(f"%{q}%")))
    return render_template("remotes.html", items=query.order_by(RemoteAccess.id.desc()).all(), q=q)


@bp.route("/remotes/new", methods=["GET", "POST"])
@bp.route("/remotes/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def remote_form(item_id=None):
    item = db.session.get(RemoteAccess, item_id) if item_id else RemoteAccess()
    if request.method == "POST":
        item.customer_id = request.form.get("customer_id") or None
        item.device_id = ensure_customer_device(item.customer_id)
        item.address = form_value("address")
        item.username = form_value("username")
        item.password = request.form.get("password", "")
        item.remark = form_value("remark")
        db.session.add(item)
        db.session.commit()
        flash("远程管理信息已保存", "success")
        return redirect(url_for("main.remotes"))
    customer_id = item.customer_id or (item.device.customer_id if item.device else None)
    return render_template("remote_form.html", item=item, customer_id=customer_id, customers=Customer.query.order_by(Customer.name).all())


@bp.route("/remotes/<int:item_id>/delete", methods=["POST"])
@login_required
def remote_delete(item_id):
    db.session.delete(RemoteAccess.query.get_or_404(item_id))
    db.session.commit()
    flash("远程管理信息已删除", "success")
    return redirect(url_for("main.remotes"))


@bp.route("/renewals")
@login_required
def renewals():
    q = request.args.get("q", "").strip()
    query = Renewal.query.join(Customer)
    if q:
        query = query.filter((Customer.name.like(f"%{q}%")) | (Renewal.remark.like(f"%{q}%")))
    return render_template("renewals.html", items=query.order_by(Renewal.expire_date.asc()).all(), q=q)


@bp.route("/renewals/new", methods=["GET", "POST"])
@bp.route("/renewals/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def renewal_form(item_id=None):
    item = db.session.get(Renewal, item_id) if item_id else Renewal()
    if request.method == "POST":
        item.customer_id = request.form.get("customer_id")
        item.device_id = request.form.get("device_id") or None
        item.line_id = request.form.get("line_id") or None
        item.price = money(request.form.get("price"))
        item.start_date = parse_date(request.form.get("start_date"))
        item.expire_date = parse_date(request.form.get("expire_date"))
        item.status = form_value("status", "正常")
        item.remark = form_value("remark")
        db.session.add(item)
        db.session.commit()
        flash("续费记录已保存", "success")
        return redirect(url_for("main.renewals"))
    return render_template(
        "renewal_form.html",
        item=item,
        customers=Customer.query.order_by(Customer.name).all(),
        devices=Device.query.order_by(Device.name).all(),
        lines=Line.query.order_by(Line.code).all(),
    )


@bp.route("/renewals/<int:item_id>/delete", methods=["POST"])
@login_required
def renewal_delete(item_id):
    db.session.delete(Renewal.query.get_or_404(item_id))
    db.session.commit()
    flash("续费记录已删除", "success")
    return redirect(url_for("main.renewals"))


@bp.route("/renewals/<int:item_id>/renew", methods=["POST"])
@login_required
def renewal_mark_renewed(item_id):
    item = Renewal.query.get_or_404(item_id)
    item.expire_date = add_one_month(item.expire_date)
    item.status = "正常"
    db.session.commit()
    flash(f"{item.customer.name} 已续费，到期时间已延长至 {item.expire_date}", "success")
    return redirect(request.referrer or url_for("main.dashboard"))


@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = global_search(q) if q else {}
    return render_template("search.html", q=q, results=results)


@bp.route("/export.xlsx")
@login_required
def export_excel():
    stream = export_workbook()
    return send_file(stream, as_attachment=True, download_name=f"线路客户管理-{datetime.now().strftime('%Y%m%d')}.xlsx")


@bp.route("/backups")
@login_required
def backups():
    return render_template("backups.html", items=list_backups())


@bp.route("/backups/create", methods=["POST"])
@login_required
def backup_create():
    create_backup()
    flash("备份已创建", "success")
    return redirect(url_for("main.backups"))


@bp.route("/backups/<name>")
@login_required
def backup_download(name):
    backups = {item["name"] for item in list_backups()}
    if name not in backups or not name.endswith(".db"):
        abort(404)
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))
    return send_file(os.path.join(backup_dir, name), as_attachment=True)


@bp.cli.command("backup")
def backup_command():
    create_backup()
    print("backup completed")


@bp.cli.command("send-reminders")
def reminders_command():
    count = send_reminder_email()
    print(f"sent {count} reminder items")
