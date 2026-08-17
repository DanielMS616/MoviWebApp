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

    def get_movies(self, user_id):
        """Returns all movies belonging to a specific user."""

        return Movie.query.filter_by(
            user_id=user_id
        ).all()

    def add_movie(self, movie):
        """Stores a Movie object in the database."""

        db.session.add(movie)
        db.session.commit()

    def update_movie(self, user_id, movie_id, new_title):
        """Updates a movie only if it belongs to the specified user."""

        movie = Movie.query.filter_by(
            id=movie_id,
            user_id=user_id
        ).first()

        if movie:
            movie.name = new_title
            db.session.commit()

    def delete_movie(self, user_id, movie_id):
        """Deletes a movie only if it belongs to the specified user."""

        movie = Movie.query.filter_by(
            id=movie_id,
            user_id=user_id
        ).first()

        if movie:
            db.session.delete(movie)
            db.session.commit()
