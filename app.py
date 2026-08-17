import os

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

from data_manager import DataManager
from models import db, Movie


# Loads environment variables from the .env file.
load_dotenv()


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
        movies=movies,
        user_id=user_id
    )


@app.route(
    "/users/<int:user_id>/movies/search",
    methods=["GET"]
)
def search_movies(user_id):
    """Searches OMDb for movies matching the user's search query."""

    query = request.args.get("query", "").strip()
    movies = data_manager.get_movies(user_id)

    if not query:
        return render_template(
            "movies.html",
            movies=movies,
            user_id=user_id
        )

    api_key = os.getenv("OMDB_API_KEY")

    if not api_key:
        return "OMDb API key is not configured.", 500

    try:
        response = requests.get(
            "https://www.omdbapi.com/",
            params={
                "apikey": api_key,
                "s": query,
                "type": "movie",
                "page": 1
            },
            timeout=10
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(f"OMDb search request failed: {error}")

        return "Could not connect to OMDb.", 502

    search_data = response.json()

    if search_data.get("Response") == "False":
        omdb_error = search_data.get("Error", "")

        if omdb_error == "Too many results.":
            search_error = (
                "Too many results. Please refine your search."
            )
        else:
            search_error = "No movies found."

        return render_template(
            "movies.html",
            movies=movies,
            user_id=user_id,
            query=query,
            search_results=[],
            total_results=0,
            search_error=search_error
        )

    search_results = search_data.get("Search", [])
    total_results = int(
        search_data.get("totalResults", 0)
    )

    return render_template(
        "movies.html",
        movies=movies,
        user_id=user_id,
        query=query,
        search_results=search_results,
        total_results=total_results,
        search_error=None
    )


@app.route(
    "/users/<int:user_id>/movies",
    methods=["POST"]
)
def add_movie(user_id):
    """Adds a selected OMDb movie to a user's favorite movies."""

    imdb_id = request.form.get("imdb_id", "").strip()

    if not imdb_id:
        return redirect(
            url_for("get_movies", user_id=user_id)
        )

    api_key = os.getenv("OMDB_API_KEY")

    if not api_key:
        return "OMDb API key is not configured.", 500

    try:
        response = requests.get(
            "https://www.omdbapi.com/",
            params={
                "apikey": api_key,
                "i": imdb_id
            },
            timeout=10
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(f"OMDb movie request failed: {error}")

        return "Could not connect to OMDb.", 502

    movie_data = response.json()

    if movie_data.get("Response") == "False":
        return "Movie could not be found.", 404

    if movie_data.get("Type") != "movie":
        return "Selected result is not a movie.", 400

    movie = Movie(
        name=movie_data["Title"],
        director=movie_data["Director"],
        year=int(movie_data["Year"]),
        poster_url=movie_data["Poster"],
        user_id=user_id
    )

    data_manager.add_movie(movie)

    return redirect(
        url_for("get_movies", user_id=user_id)
    )


@app.route(
    "/users/<int:user_id>/movies/<int:movie_id>/update",
    methods=["POST"]
)
def update_movie(user_id, movie_id):
    """Updates the title of a movie."""

    new_title = request.form.get("title", "").strip()

    if new_title:
        data_manager.update_movie(
            user_id,
            movie_id,
            new_title
        )

    return redirect(
        url_for("get_movies", user_id=user_id)
    )


@app.route(
    "/users/<int:user_id>/movies/<int:movie_id>/delete",
    methods=["POST"]
)
def delete_movie(user_id, movie_id):
    """Deletes a movie from a user's favorite movies."""

    data_manager.delete_movie(
        user_id,
        movie_id
    )

    return redirect(
        url_for("get_movies", user_id=user_id)
    )


@app.errorhandler(404)
def page_not_found(error):
    """Displays a custom page when a requested resource is not found."""

    return render_template("404.html"), 404


if __name__ == "__main__":
    # The application context gives SQLAlchemy access to the
    # Flask application's database configuration.
    with app.app_context():
        # Creates all database tables that do not exist yet.
        db.create_all()

    # Starts the local Flask development server.
    app.run()