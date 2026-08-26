from sqlalchemy.exc import IntegrityError

from models import db, User, Movie


class DataManager:
    """Handles database operations for users and movies."""

    def create_user(self, name):
        """Creates a new user and stores it in the database."""

        new_user = User(name=name)
        db.session.add(new_user)
        db.session.commit()

    def get_users(self):
        """Returns all users stored in the database."""

        return User.query.all()

    def get_user(self, user_id):
        """
        Returns one user with the specified ID.

        If no matching user exists, the query returns None.
        """

        # The user ID uniquely identifies one user in the database.
        # first() returns the matching User object or None if no user
        # with this ID exists.
        return User.query.filter_by(
            id=user_id
        ).first()

    def delete_user(self, user_id):
        """
        Deletes a user together with all of their favorite movies.

        A user's movies are removed first so that no movie records remain
        in the database without the user they belong to.

        Returns True if the user was deleted and False if the user
        could not be found.
        """

        # Looks up the user before deleting anything.
        # This avoids running delete operations for a user that does
        # not exist.
        user = User.query.filter_by(
            id=user_id
        ).first()

        if not user:
            return False

        # Deletes all favorite movies belonging to this user first.
        #
        # The Movie table references User through user_id, so removing
        # the dependent movie records before the user keeps the database
        # data consistent.
        Movie.query.filter_by(
            user_id=user_id
        ).delete()

        # Deletes the user itself after their movie records are removed.
        db.session.delete(user)

        # Both delete operations are committed together.
        db.session.commit()

        return True

    def get_movies(self, user_id):
        """Returns all movies belonging to a specific user."""

        return Movie.query.filter_by(
            user_id=user_id
        ).all()

    def add_movie(self, movie):
        """
        Adds a movie to a user's favorites.

        Before saving, the method checks whether the same user has already
        added a movie with the same IMDb ID. This prevents normal duplicate
        entries before the database constraint needs to reject them.

        Returns True if the movie was added and False if it already exists.
        """

        # The IMDb ID identifies the selected movie.
        # Together with the user ID, it identifies one favorite entry.
        existing_movie = Movie.query.filter_by(
            user_id=movie.user_id,
            imdb_id=movie.imdb_id
        ).first()

        # Normal duplicate attempts are handled before an INSERT is made.
        if existing_movie:
            return False

        db.session.add(movie)

        try:
            db.session.commit()

        # The database UNIQUE constraint is the final protection against
        # duplicate movies if another insert happens after the check above.
        except IntegrityError:
            db.session.rollback()

            # After the rollback, check whether the expected duplicate now
            # exists. If so, the operation can be handled like any other
            # duplicate attempt.
            existing_movie = Movie.query.filter_by(
                user_id=movie.user_id,
                imdb_id=movie.imdb_id
            ).first()

            if existing_movie:
                return False

            # A different integrity error is unexpected and should not be
            # disguised as a normal duplicate.
            raise

        return True

    def update_movie(self, user_id, movie_id, new_title):
        """
        Updates a movie only if it belongs to the specified user.

        Returns True if the movie was updated and False if no matching
        movie belongs to the specified user.
        """

        # Both IDs are part of the lookup.
        #
        # This prevents a movie from being changed through another
        # user's URL simply because the movie ID itself exists.
        movie = Movie.query.filter_by(
            id=movie_id,
            user_id=user_id
        ).first()

        if not movie:
            return False

        movie.name = new_title
        db.session.commit()

        return True

    def delete_movie(self, user_id, movie_id):
        """
        Deletes a movie only if it belongs to the specified user.

        Returns True if the movie was deleted and False if no matching
        movie belongs to the specified user.
        """

        # Both IDs are checked so that a user can only delete movies
        # that actually belong to their own collection.
        movie = Movie.query.filter_by(
            id=movie_id,
            user_id=user_id
        ).first()

        if not movie:
            return False

        db.session.delete(movie)
        db.session.commit()

        return True
