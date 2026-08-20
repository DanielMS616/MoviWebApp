import json
import os
import random

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from data_manager import DataManager
from models import db, Movie


# Loads environment variables from the local .env file.
# This keeps sensitive values such as the OMDb API key and Flask's
# secret key outside of the source code.
load_dotenv()


# Creates the Flask application object.
app = Flask(__name__)


# Loads Flask's secret key from the environment.
# Flask uses this key to securely sign session data.
# Flash messages and the temporary Explore shuffle seed are stored
# in the session and therefore require a secret key.
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


# The application cannot safely use sessions or flash messages
# without a configured secret key.
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY is not configured."
    )


# Determines the absolute path of the project directory.
# This makes file paths independent of the directory from which
# the Flask application is started.
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
# Database queries remain separated from the Flask route logic.
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

    # Removes unnecessary whitespace around values returned by the API.
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


def flash_movie_message(text, category, imdb_id=None):
    """
    Stores feedback for a movie action in Flask's flash session.

    The IMDb ID connects the message to the exact movie card that caused
    the action. Messages without an IMDb ID can later be displayed as
    general page-level feedback.
    """

    flash(
        {
            "text": text,
            "imdb_id": imdb_id
        },
        category
    )


def redirect_after_movie_action(
    user_id,
    source,
    query=None,
    imdb_id=None
):
    """
    Redirects the user back to the page where a movie action started.

    Search actions return to the same search results and Explore actions
    return to the same recommendation collection. If an IMDb ID is
    available, an HTML anchor is added so that the browser can locate
    the affected movie card after the redirect.
    """

    # Each movie action area has an HTML id such as:
    #
    # movie-tt0133093
    #
    # This becomes the URL fragment:
    #
    # #movie-tt0133093
    #
    # It provides a useful fallback even when JavaScript is unavailable.
    anchor = None

    if imdb_id:
        anchor = f"movie-{imdb_id}"

    # Search needs the original query so that the same result list
    # can be generated again after the redirect.
    if source == "search" and query:
        return redirect(
            url_for(
                "search_movies",
                user_id=user_id,
                query=query,
                _anchor=anchor
            )
        )

    # Explore receives preserve_order=1 after a movie action.
    # This tells the Explore route to reuse the current shuffle seed
    # instead of creating a new random order.
    if source == "explore":
        return redirect(
            url_for(
                "explore_movies",
                user_id=user_id,
                preserve_order=1,
                _anchor=anchor
            )
        )

    # Only known application destinations are accepted.
    # Any unexpected source value safely returns to the favorites page.
    return redirect(
        url_for(
            "get_movies",
            user_id=user_id,
            _anchor=anchor
        )
    )


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
    return redirect(
        url_for("index")
    )


@app.route(
    "/users/<int:user_id>/delete",
    methods=["POST"]
)
def delete_user(user_id):
    """Deletes a user together with all of their favorite movies."""

    # The DataManager handles both parts of the delete operation:
    # first the user's favorite movies and then the user itself.
    data_manager.delete_user(user_id)

    # Redirects back to the user overview after the delete request.
    # Using POST prevents a user from being deleted simply by opening
    # or following a normal URL.
    return redirect(
        url_for("index")
    )


@app.route(
    "/users/<int:user_id>/movies",
    methods=["GET"]
)
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
    """Searches OMDb and displays matching movie results."""

    # Search uses GET, so the search term is read from the URL
    # query parameters instead of request.form.
    query = request.args.get("query", "").strip()

    # An empty search should simply return the user to the
    # favorite movie page instead of calling OMDb.
    if not query:
        return redirect(
            url_for(
                "get_movies",
                user_id=user_id
            )
        )

    # Reads the OMDb API key loaded from the .env file.
    api_key = os.getenv("OMDB_API_KEY")

    # Search errors should be displayed on the search results page
    # instead of replacing the application with a plain text error.
    if not api_key:
        return render_template(
            "search_results.html",
            user_id=user_id,
            query=query,
            search_results=[],
            total_results=0,
            search_error=(
                "Movie search is currently unavailable."
            )
        ), 500

    try:
        # Searches OMDb for movies matching the partial title.
        #
        # "s" performs a title search.
        # "type=movie" excludes series and episodes.
        # Only the first result page is requested because pagination
        # is intentionally outside the scope of Movie Search v1.
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

        # Converts the JSON response into a Python dictionary.
        search_data = response.json()

    # Handles connection errors, timeouts and unsuccessful HTTP responses
    # without leaving the search results page.
    except requests.RequestException as error:
        print(f"OMDb search request failed: {error}")

        return render_template(
            "search_results.html",
            user_id=user_id,
            query=query,
            search_results=[],
            total_results=0,
            search_error=(
                "The movie service is currently unavailable. "
                "Please try again."
            )
        ), 502

    # OMDb may return HTTP 200 even when the actual search did not
    # produce usable results.
    if search_data.get("Response") == "False":
        omdb_error = search_data.get("Error", "")

        # Very broad searches receive a more useful MoviWeb message.
        if omdb_error == "Too many results.":
            search_error = (
                "Too many results. Please refine your search."
            )
        else:
            search_error = "No movies found."

        return render_template(
            "search_results.html",
            user_id=user_id,
            query=query,
            search_results=[],
            total_results=0,
            search_error=search_error
        )

    # OMDb stores successful search matches inside the "Search" list.
    search_results = search_data.get("Search", [])

    # OMDb normally returns totalResults as a string.
    # If the value is unexpectedly invalid, the number of results
    # actually received is used as a safe fallback.
    try:
        total_results = int(
            search_data.get("totalResults", 0)
        )

    except (TypeError, ValueError):
        total_results = len(search_results)

    return render_template(
        "search_results.html",
        user_id=user_id,
        query=query,
        search_results=search_results,
        total_results=total_results,
        search_error=None
    )


@app.route(
    "/users/<int:user_id>/movies/explore",
    methods=["GET"]
)
def explore_movies(user_id):
    """Displays MoviWeb's curated movie recommendations."""

    # Builds the absolute path to the local recommendation file.
    # Using basedir keeps the path independent of the directory
    # from which the Flask application is started.
    suggestions_path = os.path.join(
        basedir,
        "data",
        "movie_suggestions.json"
    )

    # Loads the curated movie collection from the local JSON file.
    with open(
        suggestions_path,
        "r",
        encoding="utf-8"
    ) as file:
        movie_suggestions = json.load(file)

    # preserve_order is only added to the URL when the user returns
    # to Explore after a movie action such as Add Movie.
    preserve_order = (
        request.args.get("preserve_order") == "1"
    )

    # When Explore is opened normally, a new shuffle seed is generated.
    #
    # Only this small integer is stored in Flask's session. Storing the
    # complete 100-movie order would unnecessarily enlarge the session.
    if not preserve_order or "explore_seed" not in session:
        session["explore_seed"] = random.randint(
            0,
            2**32 - 1
        )

    # A dedicated Random object uses the saved seed.
    # The same seed always produces the same shuffled order.
    shuffle_generator = random.Random(
        session["explore_seed"]
    )

    shuffle_generator.shuffle(
        movie_suggestions
    )

    return render_template(
        "explore.html",
        user_id=user_id,
        movie_suggestions=movie_suggestions
    )


@app.route(
    "/users/<int:user_id>/movies",
    methods=["POST"]
)
def add_movie(user_id):
    """Adds a selected OMDb movie to a user's favorite movies."""

    # The search or Explore page submits the unique IMDb ID
    # of the movie selected by the user.
    imdb_id = request.form.get("imdb_id", "").strip()

    # These values describe where the Add Movie action started.
    # They allow MoviWeb to return the user to the same browsing page
    # after success, duplicate detection or another handled error.
    source = request.form.get("source", "").strip()
    query = request.form.get("query", "").strip()

    # Without an IMDb ID, no movie can be identified.
    # This is a general action error because there is no movie ID
    # available that could identify a specific card.
    if not imdb_id:
        flash_movie_message(
            "No movie was selected.",
            "error"
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query
        )

    # Reads the OMDb API key from the environment.
    api_key = os.getenv("OMDB_API_KEY")

    if not api_key:
        flash_movie_message(
            "The movie service is currently unavailable.",
            "error",
            imdb_id
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query,
            imdb_id
        )

    try:
        # Loads the complete OMDb details for the selected IMDb ID.
        #
        # A short plot is sufficient for MoviWeb's favorite movie cards
        # and prevents unnecessarily long descriptions from being stored.
        response = requests.get(
            "https://www.omdbapi.com/",
            params={
                "apikey": api_key,
                "i": imdb_id,
                "plot": "short"
            },
            timeout=10
        )

        # Raises an exception for unsuccessful HTTP status codes.
        response.raise_for_status()

        # Converts the OMDb detail response into a Python dictionary.
        movie_data = response.json()

    # Connection errors, timeouts or unsuccessful HTTP responses
    # return the user directly to the selected movie card.
    except requests.RequestException as error:
        print(f"OMDb movie request failed: {error}")

        flash_movie_message(
            (
                "The selected movie could not be loaded. "
                "Please try again."
            ),
            "error",
            imdb_id
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query,
            imdb_id
        )

    # OMDb can return HTTP 200 even when the supplied IMDb ID
    # does not identify an available movie.
    if movie_data.get("Response") == "False":
        flash_movie_message(
            "The selected movie could not be found.",
            "error",
            imdb_id
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query,
            imdb_id
        )

    # The IMDb ID comes from a client request.
    # Although Search and Explore normally provide movie IDs,
    # the returned OMDb type is checked again before storing anything.
    if movie_data.get("Type") != "movie":
        flash_movie_message(
            "The selected result is not a movie.",
            "error",
            imdb_id
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query,
            imdb_id
        )

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

    # A movie without one of these required values cannot satisfy
    # the Movie model and therefore must not be stored.
    if (
        title is None
        or year_value is None
        or movie_imdb_id is None
    ):
        flash_movie_message(
            (
                "The selected movie contains incomplete data "
                "and could not be added."
            ),
            "error",
            imdb_id
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query,
            imdb_id
        )

    try:
        # MoviWeb stores one numeric release year for every movie.
        year = int(year_value)

    # Unlike runtime or rating, year is required by our data model.
    # An invalid release year therefore prevents the movie from
    # being stored.
    except ValueError:
        flash_movie_message(
            (
                "The selected movie contains an invalid release year "
                "and could not be added."
            ),
            "error",
            movie_imdb_id
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query,
            movie_imdb_id
        )

    # Optional OMDb values are normalized before they are stored.
    # Missing information becomes Python None and later SQL NULL.
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

    # The DataManager checks whether this user already has a movie
    # with the same IMDb ID before attempting to insert it.
    movie_added = data_manager.add_movie(movie)

    # A duplicate is not treated as an application crash.
    # The message is attached to the movie's IMDb ID so that the
    # template can display it directly beside the selected card.
    if not movie_added:
        flash_movie_message(
            f"{movie.name} is already in your favorites.",
            "warning",
            movie.imdb_id
        )

        return redirect_after_movie_action(
            user_id,
            source,
            query,
            movie.imdb_id
        )

    # A successful action is handled in exactly the same way.
    # The flash message survives the redirect and can be displayed
    # directly on the card that caused the action.
    flash_movie_message(
        f"{movie.name} was added to your favorites.",
        "success",
        movie.imdb_id
    )

    # Search users return to the same search and the affected card.
    # Explore users return to the same recommendation order and card.
    return redirect_after_movie_action(
        user_id,
        source,
        query,
        movie.imdb_id
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

    # Returns to the updated favorite movie card.
    # The HTML anchor also provides a useful fallback if JavaScript
    # is unavailable.
    return redirect(
        url_for(
            "get_movies",
            user_id=user_id,
            _anchor=f"favorite-movie-{movie_id}"
        )
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
        url_for(
            "get_movies",
            user_id=user_id
        )
    )


@app.errorhandler(404)
def page_not_found(error):
    """Displays a custom page when a requested resource is not found."""

    # Flask passes the original error object to the handler.
    # MoviWeb currently only needs to display its custom error page.
    return render_template(
        "404.html"
    ), 404


if __name__ == "__main__":
    # The application context gives SQLAlchemy access to the
    # Flask application's database configuration.
    with app.app_context():
        # Creates database tables that do not exist yet.
        #
        # create_all() creates missing tables but does not migrate
        # already existing tables when a model changes.
        db.create_all()

    # Starts Flask's local development server.
    # A production deployment will later use a WSGI server instead.
    app.run(port=5001)