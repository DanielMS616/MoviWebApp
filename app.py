import os

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

from data_manager import DataManager
from models import db, Movie


# Loads environment variables from the local .env file.
# This keeps sensitive values such as the OMDb API key
# outside of the source code.
load_dotenv()


# Creates the Flask application object.
app = Flask(__name__)


# Determines the absolute path of the project directory.
# This makes the SQLite database path independent of the directory
# from which the application is started.
basedir = os.path.abspath(os.path.dirname(__file__))


# Configures the SQLite database used by MoviWeb.
# The database file is stored inside the project's data directory.
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'data/movies.db')}"
)

# Disables SQLAlchemy's additional modification tracking because
# MoviWeb does not use this feature.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Connects the SQLAlchemy object from models.py to this Flask application.
db.init_app(app)


# Creates the object responsible for database CRUD operations.
data_manager = DataManager()


def normalize_omdb_value(value):
    """
    Converts missing OMDb values into Python None.

    OMDb often returns the string "N/A" when information is unavailable.
    Inside MoviWeb and the database, None represents missing data more
    accurately than storing "N/A" as if it were real information.
    """

    # None already represents missing information.
    if value is None:
        return None

    # Removes unnecessary whitespace around API values.
    value = value.strip()

    # Empty strings and OMDb's "N/A" both mean that no useful
    # information is available.
    if not value or value == "N/A":
        return None

    return value


def parse_runtime(runtime):
    """
    Converts an OMDb runtime such as "117 min" into the integer 117.

    Runtime is optional movie information. If OMDb does not provide
    a usable value, None is returned instead of rejecting the movie.
    """

    # Applies the general missing-value handling first.
    runtime = normalize_omdb_value(runtime)

    if runtime is None:
        return None

    # OMDb normally returns values such as "117 min".
    # The database stores only the numeric number of minutes.
    runtime = runtime.replace(" min", "").strip()

    try:
        return int(runtime)

    # Invalid optional runtime information should not prevent
    # an otherwise valid movie from being stored.
    except ValueError:
        return None


def parse_imdb_rating(rating):
    """
    Converts an OMDb IMDb rating such as "8.1" into the float 8.1.

    IMDb ratings are optional. Missing or invalid ratings therefore
    become None instead of causing the movie insert to fail.
    """

    # Applies the same missing-value handling used for the other
    # optional OMDb fields.
    rating = normalize_omdb_value(rating)

    if rating is None:
        return None

    try:
        return float(rating)

    # An invalid rating is treated as missing optional information.
    except ValueError:
        return None


@app.route("/")
def index():
    """Displays all registered users."""

    # Loads all users so that they can be displayed on the home page.
    users = data_manager.get_users()

    return render_template(
        "index.html",
        users=users
    )


@app.route("/users", methods=["POST"])
def create_user():
    """Creates a new user from the submitted form data."""

    # Reads and cleans the submitted user name.
    # A value containing only whitespace is treated as empty.
    name = request.form.get("name", "").strip()

    if name:
        data_manager.create_user(name)

    # Redirects after the POST request so that refreshing the page
    # does not submit the form again.
    return redirect(url_for("index"))


@app.route("/users/<int:user_id>/movies", methods=["GET"])
def get_movies(user_id):
    """Displays all favorite movies belonging to a user."""

    # Loads only movies that belong to the selected user.
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

    # Search uses GET, so the search term is read from the URL
    # query parameters instead of request.form.
    query = request.args.get("query", "").strip()

    # The page still displays the user's existing favorites together
    # with possible search results.
    movies = data_manager.get_movies(user_id)

    # An empty query should not cause an unnecessary OMDb request.
    if not query:
        return render_template(
            "movies.html",
            movies=movies,
            user_id=user_id
        )

    # Reads the API key loaded from the .env file.
    api_key = os.getenv("OMDB_API_KEY")

    if not api_key:
        return "OMDb API key is not configured.", 500

    try:
        # Searches for movies matching the partial title.
        #
        # "s" performs a search.
        # "type=movie" excludes series and episodes.
        # Only page 1 is used because pagination is intentionally
        # outside the scope of Movie Search v1.
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

        # Raises an exception for unsuccessful HTTP status codes.
        response.raise_for_status()

    # Handles connection errors, timeouts and HTTP errors.
    except requests.RequestException as error:
        print(f"OMDb search request failed: {error}")

        return "Could not connect to OMDb.", 502

    # Converts the JSON response into a Python dictionary.
    search_data = response.json()

    # OMDb may return HTTP 200 even when the actual search failed.
    # Its own Response field therefore also needs to be checked.
    if search_data.get("Response") == "False":
        omdb_error = search_data.get("Error", "")

        # MoviWeb translates the external API response into its own
        # user-facing message.
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

    # Successful OMDb search results are stored inside the "Search" list.
    search_results = search_data.get("Search", [])

    # OMDb returns totalResults as a string.
    # MoviWeb converts it into an integer for easier comparison.
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

    # The search result submits the unique IMDb ID instead of a title.
    # This ensures that exactly the movie selected by the user is loaded.
    imdb_id = request.form.get("imdb_id", "").strip()

    # Without an IMDb ID, no movie can be identified.
    if not imdb_id:
        return redirect(
            url_for("get_movies", user_id=user_id)
        )

    # Reads the API key from the environment.
    api_key = os.getenv("OMDB_API_KEY")

    if not api_key:
        return "OMDb API key is not configured.", 500

    try:
        # Loads the complete OMDb details for the selected IMDb ID.
        #
        # A short plot is sufficient for MoviWeb's movie cards and
        # prevents unnecessarily long descriptions from being stored.
        response = requests.get(
            "https://www.omdbapi.com/",
            params={
                "apikey": api_key,
                "i": imdb_id,
                "plot": "short"
            },
            timeout=10
        )

        response.raise_for_status()

    # Handles connection errors, timeouts and unsuccessful HTTP responses.
    except requests.RequestException as error:
        print(f"OMDb movie request failed: {error}")

        return "Could not connect to OMDb.", 502

    # Converts the detail response into a Python dictionary.
    movie_data = response.json()

    # OMDb can return HTTP 200 even when the supplied IMDb ID is invalid.
    if movie_data.get("Response") == "False":
        return "Movie could not be found.", 404

    # The IMDb ID comes from the client request.
    # The response is therefore checked again before anything is stored.
    if movie_data.get("Type") != "movie":
        return "Selected result is not a movie.", 400

    # Title, year and IMDb ID are required core movie information.
    title = normalize_omdb_value(
        movie_data.get("Title")
    )

    year_value = normalize_omdb_value(
        movie_data.get("Year")
    )

    movie_imdb_id = normalize_omdb_value(
        movie_data.get("imdbID")
    )

    # A movie without one of these required core values cannot satisfy
    # the Movie model and therefore must not be stored.
    if title is None or year_value is None or movie_imdb_id is None:
        return "OMDb returned incomplete movie data.", 502

    try:
        # MoviWeb stores one numeric release year for every movie.
        year = int(year_value)

    # Unlike runtime or rating, year is required.
    # An invalid year therefore prevents the movie from being stored.
    except ValueError:
        return "OMDb returned an invalid movie year.", 502

    # Optional values are normalized before they are stored.
    # Missing OMDb information becomes Python None and later SQL NULL.
    director = normalize_omdb_value(
        movie_data.get("Director")
    )

    genre = normalize_omdb_value(
        movie_data.get("Genre")
    )

    runtime_minutes = parse_runtime(
        movie_data.get("Runtime")
    )

    plot = normalize_omdb_value(
        movie_data.get("Plot")
    )

    imdb_rating = parse_imdb_rating(
        movie_data.get("imdbRating")
    )

    poster_url = normalize_omdb_value(
        movie_data.get("Poster")
    )

    # Creates the final Movie object from the validated and converted
    # OMDb data.
    movie = Movie(
        name=title,
        director=director,
        year=year,
        genre=genre,
        runtime_minutes=runtime_minutes,
        plot=plot,
        imdb_rating=imdb_rating,
        imdb_id=movie_imdb_id,
        poster_url=poster_url,
        user_id=user_id
    )

    # The DataManager returns False if this user already has a movie
    # with the same IMDb ID in their favorites.
    movie_added = data_manager.add_movie(movie)

    if not movie_added:
        return "This movie is already in your favorites.", 409

    # Redirects back to the user's favorites after a successful insert.
    return redirect(
        url_for("get_movies", user_id=user_id)
    )


@app.route(
    "/users/<int:user_id>/movies/<int:movie_id>/update",
    methods=["POST"]
)
def update_movie(user_id, movie_id):
    """Updates the title of a movie."""

    # Reads and cleans the manually entered replacement title.
    new_title = request.form.get("title", "").strip()

    if new_title:
        # Both IDs are passed to the DataManager so that the movie
        # can only be changed through the user it actually belongs to.
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

    # The DataManager checks user_id together with movie_id.
    # This prevents deletion through another user's URL.
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

    # Flask passes the original error object to the handler.
    # MoviWeb currently only needs to display its custom error page.
    return render_template("404.html"), 404


if __name__ == "__main__":
    # The application context gives SQLAlchemy access to the
    # Flask application's database configuration.
    with app.app_context():
        # Creates tables that do not exist yet.
        #
        # create_all() does not migrate an already existing table when
        # the Python model changes. That is why we are performing one
        # deliberate database reset during the current schema redesign.
        db.create_all()

    # Starts Flask's local development server.
    # A production deployment will later use a WSGI server instead.
    app.run()