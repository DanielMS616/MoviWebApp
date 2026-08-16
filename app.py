import os

from flask import Flask, redirect, render_template, request, url_for

from data_manager import DataManager
from models import db, Movie


# Creates the Flask application.
app = Flask(__name__)


# Determines the absolute path of the project directory.
basedir = os.path.abspath(os.path.dirname(__file__))


# Configures the SQLite database used by the application.
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'data/movies.db')}"
)

# Disables SQLAlchemy's additional modification tracking.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Connects the SQLAlchemy database object to the Flask application.
db.init_app(app)


# Creates the object used for database CRUD operations.
data_manager = DataManager()


@app.route("/")
def index():
    """Displays all registered users."""

    users = data_manager.get_users()

    return render_template(
        "index.html",
        users=users
    )


@app.route("/users", methods=["POST"])
def create_user():
    """Creates a new user from the submitted form data."""

    name = request.form.get("name", "").strip()

    if name:
        data_manager.create_user(name)

    return redirect(url_for("index"))


@app.route("/users/<int:user_id>/movies", methods=["GET"])
def get_movies(user_id):
    """Displays all favorite movies belonging to a user."""

    movies = data_manager.get_movies(user_id)

    return render_template(
        "movies.html",
        movies=movies
    )


if __name__ == "__main__":
    # The application context gives SQLAlchemy access to the
    # Flask application's database configuration.
    with app.app_context():
        # Creates all database tables that do not exist yet.
        db.create_all()

    # Starts the local Flask development server.
    app.run()