from flask_sqlalchemy import SQLAlchemy


# Creates the SQLAlchemy database object.
# The Flask application connects to this object in app.py.
db = SQLAlchemy()


class User(db.Model):
    """Represents a user of the MoviWeb application."""

    # Primary key used to uniquely identify each user in the database.
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # The user's display name.
    # A user must always have a name, so NULL values are not allowed.
    name = db.Column(
        db.String(100),
        nullable=False
    )


class Movie(db.Model):
    """Represents a movie stored in a user's favorite movies."""

    # A movie may appear in the favorites of different users,
    # but the same user should not be able to add the same IMDb movie twice.
    #
    # Therefore, imdb_id is not globally unique on its own.
    # Instead, the combination of user_id and imdb_id must be unique.
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "imdb_id",
            name="uq_user_movie_imdb"
        ),
    )

    # Internal primary key of the movie entry inside MoviWeb.
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Movie title returned by OMDb.
    # Every stored movie must have a title.
    name = db.Column(
        db.String(100),
        nullable=False
    )

    # Director information is supplied by OMDb.
    # Some movies may not have this information available, so NULL is allowed.
    director = db.Column(
        db.String(100),
        nullable=True
    )

    # Release year of the movie.
    # MoviWeb only stores movies, not series, so this is stored as one integer.
    year = db.Column(
        db.Integer,
        nullable=False
    )

    # Genre information such as "Comedy, Crime".
    # This is useful for displaying additional movie details.
    genre = db.Column(
        db.String(200),
        nullable=True
    )

    # Runtime is stored as a number of minutes instead of a string such as
    # "117 min". This keeps the value usable for possible future calculations
    # or sorting.
    runtime_minutes = db.Column(
        db.Integer,
        nullable=True
    )

    # Short movie description returned by OMDb.
    # Text is used because plots can be longer than normal short string fields.
    plot = db.Column(
        db.Text,
        nullable=True
    )

    # IMDb rating stored as a numeric value, for example 8.1.
    # Ratings may be unavailable for some movies, so NULL is allowed.
    imdb_rating = db.Column(
        db.Float,
        nullable=True
    )

    # IMDb ID uniquely identifies the selected external movie,
    # for example "tt0118715" for The Big Lebowski.
    #
    # Together with user_id, this is also used to prevent duplicate favorites.
    imdb_id = db.Column(
        db.String(20),
        nullable=False
    )

    # URL of the movie poster supplied by OMDb.
    # Some movies do not have a poster available, so NULL is allowed.
    poster_url = db.Column(
        db.String(500),
        nullable=True
    )

    # Foreign key connecting this movie entry to the user who added it.
    # Every favorite movie must belong to an existing user.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )