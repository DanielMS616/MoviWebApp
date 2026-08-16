from flask_sqlalchemy import SQLAlchemy


# Creates the SQLAlchemy database object.
# The Flask application will be connected to this object later.
db = SQLAlchemy()


class User(db.Model):
    """Represents a user of the MoviWeb application."""

    # Unique identifier for each user.
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Stores the user's name.
    # nullable=False means that every user must have a name.
    name = db.Column(
        db.String(100),
        nullable=False
    )


class Movie(db.Model):
    """Represents a movie stored in a user's favorite movies."""

    # Unique identifier for each movie.
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Stores the movie title.
    name = db.Column(
        db.String(100),
        nullable=False
    )

    # Stores the name of the movie director.
    director = db.Column(
        db.String(100),
        nullable=False
    )

    # Stores the movie's release year.
    year = db.Column(
        db.Integer,
        nullable=False
    )

    # Stores the URL of the movie poster.
    poster_url = db.Column(
        db.String(500),
        nullable=False
    )

    # Links this movie to the user who owns it.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
