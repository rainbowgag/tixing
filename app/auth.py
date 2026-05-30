from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .models import User, db

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=False)
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        flash("用户名或密码错误", "danger")
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm", "")
        if not current_user.check_password(old_password):
            flash("原密码错误", "danger")
        elif len(new_password) < 8:
            flash("新密码至少 8 位", "warning")
        elif new_password != confirm:
            flash("两次输入的新密码不一致", "warning")
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash("密码已修改，请重新登录", "success")
            logout_user()
            return redirect(url_for("auth.login"))
    return render_template("password.html")
