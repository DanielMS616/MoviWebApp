import json
import os
import sys

import requests
from dotenv import load_dotenv


# Loads the OMDb API key from the project's .env file.
load_dotenv()


# Determines the project directory based on this script's location.
basedir = os.path.abspath(os.path.dirname(__file__))

# The script is intended to live in a scripts directory.
project_dir = os.path.abspath(os.path.join(basedir, ".."))

seed_path = os.path.join(
    project_dir,
    "data",
    "../data/movie_suggestions_seed.json"
)

output_path = os.path.join(
    project_dir,
    "data",
    "movie_suggestions.json"
)


def normalize_omdb_value(value):
    """Converts missing OMDb values into Python None."""

    if value is None:
        return None

    value = value.strip()

    if not value or value == "N/A":
        return None

    return value


def load_seed_movies():
    """Loads the curated movie titles from the local seed JSON file."""

    with open(seed_path, "r", encoding="utf-8") as file:
        return json.load(file)


def fetch_movie(movie, api_key):
    """
    Looks up one curated movie on OMDb.

    If the seed already contains an IMDb ID, the movie is loaded directly
    by that ID. Otherwise, title and release year are used for the lookup.
    """

    # An IMDb ID is the most precise way to identify a movie.
    # Most seed entries do not need one, but it can be supplied when
    # title-based lookup is unreliable.
    imdb_id = movie.get("imdb_id")

    if imdb_id:
        params = {
            "apikey": api_key,
            "i": imdb_id
        }

    else:
        params = {
            "apikey": api_key,
            "t": movie["title"],
            "y": movie["year"],
            "type": "movie"
        }

    response = requests.get(
        "https://www.omdbapi.com/",
        params=params,
        timeout=10
    )

    response.raise_for_status()

    movie_data = response.json()

    if movie_data.get("Response") == "False":
        return None

    if movie_data.get("Type") != "movie":
        return None

    verified_imdb_id = normalize_omdb_value(
        movie_data.get("imdbID")
    )

    if verified_imdb_id is None:
        return None

    return {
        "title": movie_data.get(
            "Title",
            movie["title"]
        ),
        "year": movie["year"],
        "imdb_id": verified_imdb_id,
        "poster_url": normalize_omdb_value(
            movie_data.get("Poster")
        ),
        "tags": movie.get("tags", [])
    }


def main():
    """Builds the verified movie suggestions JSON file."""

    api_key = os.getenv("OMDB_API_KEY")

    if not api_key:
        print("OMDB_API_KEY is not configured.")
        sys.exit(1)

    seed_movies = load_seed_movies()
    verified_movies = []
    failed_movies = []

    for number, movie in enumerate(seed_movies, start=1):
        print(
            f"[{number}/{len(seed_movies)}] "
            f"Checking {movie['title']} ({movie['year']})..."
        )

        try:
            verified_movie = fetch_movie(movie, api_key)

        except requests.RequestException as error:
            print(f"  Request failed: {error}")
            failed_movies.append(movie)
            continue

        if verified_movie is None:
            print("  No matching OMDb movie found.")
            failed_movies.append(movie)
            continue

        verified_movies.append(verified_movie)

    if failed_movies:
        print()
        print("The final JSON was not written because some movies failed:")
        for movie in failed_movies:
            print(f"- {movie['title']} ({movie['year']})")

        print()
        print(
            f"Verified {len(verified_movies)} of "
            f"{len(seed_movies)} movies."
        )
        sys.exit(1)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            verified_movies,
            file,
            ensure_ascii=False,
            indent=2
        )
        file.write("\n")

    print()
    print(
        f"Created {output_path} with "
        f"{len(verified_movies)} verified movies."
    )


if __name__ == "__main__":
    main()
