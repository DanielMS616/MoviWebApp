import os

from flask import Flask

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
def home():
    """Displays a simple welcome message."""

    return "Welcome to MoviWeb App!"


if __name__ == "__main__":
    # The application context gives SQLAlchemy access to the
    # Flask application's database configuration.
    with app.app_context():
        # Creates all database tables that do not exist yet.
        db.create_all()

    # Starts the local Flask development server.
    app.run()