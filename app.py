import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from sqlalchemy import or_

app = Flask(__name__)

# ==========================
# CONFIGURATION (AUTOMATED)
# ==========================
# 1. Fetch Secret Key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-prod')

# 2. Smart Database Connection
# If DB_HOST is set (Production), use MySQL. Otherwise, use local SQLite file.
db_user = os.environ.get('DB_USERNAME', 'root')
db_pass = os.environ.get('DB_PASSWORD', '')
db_host = os.environ.get('DB_HOST', 'localhost')
db_name = os.environ.get('DB_NAME', 'movie_reviews_db')

if os.environ.get('DB_HOST'):
    # Production / MySQL Mode
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'
else:
    # Development / Local Mode (SQLite)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local_movies.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ==========================
# MODELS
# ==========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    reviews = db.relationship('Review', backref='author', lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# ==========================
# HELPERS
# ==========================
def get_current_user():
    if "user_id" not in session:
        return None
    return db.session.get(User, session["user_id"])


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Login required", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


# ==========================
# ROUTES
# ==========================
@app.route("/")
def index():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("index.html", reviews=reviews, current_user=get_current_user())


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", current_user=get_current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

    return render_template("login.html", current_user=get_current_user())


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out", "info")
    return redirect(url_for("index"))


@app.route("/review/new", methods=["GET", "POST"])
@login_required
def new_review():
    if request.method == "POST":
        title = request.form["title"]
        genre = request.form["genre"]
        rating = int(request.form["rating"])
        content = request.form["content"]

        review = Review(
            title=title,
            genre=genre,
            rating=rating,
            content=content,
            user_id=session["user_id"]
        )
        db.session.add(review)
        db.session.commit()

        flash("Review posted!", "success")
        return redirect(url_for("index"))

    return render_template("new_review.html", current_user=get_current_user(), is_edit=False)


@app.route("/review/<int:review_id>")
def view_review(review_id):
    review = Review.query.get_or_404(review_id)
    return render_template("view_review.html", review=review, current_user=get_current_user())


@app.route("/review/<int:review_id>/edit", methods=["GET", "POST"])
@login_required
def edit_review(review_id):
    review = Review.query.get_or_404(review_id)

    if review.user_id != session["user_id"]:
        flash("You are not allowed to edit this review.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        review.title = request.form["title"]
        review.genre = request.form["genre"]
        review.rating = int(request.form["rating"])
        review.content = request.form["content"]

        db.session.commit()
        flash("Review updated!", "success")
        return redirect(url_for("view_review", review_id=review.id))

    return render_template("new_review.html",
                           review=review,
                           is_edit=True,
                           current_user=get_current_user())


@app.route("/review/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)

    if review.user_id != session["user_id"]:
        flash("Not allowed to delete.", "danger")
        return redirect(url_for("index"))

    db.session.delete(review)
    db.session.commit()
    flash("Review deleted.", "info")
    return redirect(url_for("index"))


@app.route("/user/<int:user_id>")
def user_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found", "danger")
        return redirect(url_for("index"))

    reviews = Review.query.filter_by(user_id=user_id).order_by(Review.created_at.desc()).all()
    return render_template("user_profile.html", user=user, reviews=reviews, current_user=get_current_user())


@app.route("/users")
def users_list():
    users = User.query.all()
    user_data = []
    for user in users:
        review_count = Review.query.filter_by(user_id=user.id).count()
        user_data.append({
            'user': user,
            'review_count': review_count
        })
    return render_template("users_list.html", user_data=user_data, current_user=get_current_user())


@app.route("/search")
def search():
    query = request.args.get('q', '').strip()

    if not query:
        flash("Please enter a search term", "warning")
        return redirect(url_for("index"))

    reviews = Review.query.filter(
        or_(
            Review.title.ilike(f'%{query}%'),
            Review.genre.ilike(f'%{query}%'),
            Review.content.ilike(f'%{query}%')
        )
    ).order_by(Review.created_at.desc()).all()

    return render_template("search_results.html",
                           reviews=reviews,
                           query=query,
                           current_user=get_current_user())


# ==========================
# AUTO-SETUP (RUNS ON GUNICORN TOO)
# ==========================
# This creates tables when Gunicorn loads the app
with app.app_context():
    db.create_all()

# ==========================
# DEV SERVER ONLY
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
