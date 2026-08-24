/*
 * Preserves the user's position around movie actions that reload
 * the current browsing page.
 *
 * MoviWeb uses the Post/Redirect/Get pattern for movie actions.
 * A normal redirect reloads the page and would therefore lose the
 * exact viewport position of the movie the user was working with.
 *
 * Before a supported form is submitted, this script stores the
 * vertical position of the affected movie area in sessionStorage.
 *
 * After the redirected page and its images have loaded, the same
 * area is found again and returned to approximately the same
 * position inside the browser window.
 */


const movieScrollStorageKey = "moviwebMovieScrollState";


function saveMovieScrollPosition(form) {
    /*
     * Finds the relevant movie area for the submitted form.
     *
     * Add Movie forms are located inside a movie-action-area.
     * Update Movie forms are located inside a complete movie-card.
     */
    const movieArea = form.closest(
        ".movie-action-area, .movie-card"
    );

    if (!movieArea || !movieArea.id) {
        return;
    }

    /*
     * getBoundingClientRect().top measures the element's current
     * position relative to the top of the visible browser window.
     */
    const scrollState = {
        anchorId: movieArea.id,
        viewportTop: movieArea.getBoundingClientRect().top
    };

    sessionStorage.setItem(
        movieScrollStorageKey,
        JSON.stringify(scrollState)
    );
}


function restoreMovieScrollPosition() {
    /*
     * Restores the affected movie area to its previous position
     * inside the browser viewport after the redirected page loads.
     */
    const savedState = sessionStorage.getItem(
        movieScrollStorageKey
    );

    if (!savedState) {
        return;
    }

    let scrollState;

    try {
        scrollState = JSON.parse(savedState);
    } catch (error) {
        sessionStorage.removeItem(
            movieScrollStorageKey
        );
        return;
    }

    /*
     * Movie-action redirects contain an HTML anchor.
     * Matching the current URL fragment prevents stale stored
     * positions from affecting unrelated page loads.
     */
    if (
        window.location.hash
        !== `#${scrollState.anchorId}`
    ) {
        sessionStorage.removeItem(
            movieScrollStorageKey
        );
        return;
    }

    const movieArea = document.getElementById(
        scrollState.anchorId
    );

    if (!movieArea) {
        sessionStorage.removeItem(
            movieScrollStorageKey
        );
        return;
    }

    /*
     * The browser may already have moved to the HTML anchor.
     * The remaining difference is calculated so that the element
     * returns to the position it had before the form submission.
     */
    const currentTop = (
        movieArea.getBoundingClientRect().top
    );

    const positionDifference = (
        currentTop - scrollState.viewportTop
    );

    window.scrollBy({
        top: positionDifference,
        left: 0,
        behavior: "auto"
    });

    /*
     * The position is needed for only one redirect.
     * Removing it prevents later page loads from reusing stale data.
     */
    sessionStorage.removeItem(
        movieScrollStorageKey
    );
}


/*
 * Replaces one broken remote movie poster with MoviWeb's existing
 * poster placeholder.
 *
 * Keeping this logic in its own function lets us use it both when
 * a new image error occurs and when an image already failed before
 * JavaScript attached its event listener.
 */
function showPosterFallback(poster) {
    const posterFrame = poster.closest(
        ".movie-poster-frame"
    );

    if (!posterFrame) {
        return;
    }

    const fallback = posterFrame.querySelector(
        ".movie-poster-fallback"
    );

    if (!fallback) {
        return;
    }

    poster.style.display = "none";

    fallback.classList.add(
        "is-visible"
    );

    fallback.setAttribute(
        "aria-hidden",
        "false"
    );
}


/*
 * Replaces broken remote movie posters with MoviWeb's existing
 * poster placeholder.
 *
 * OMDb can provide a poster URL even when the image behind that
 * URL is no longer available.
 *
 * The error listener handles images that fail after this function
 * runs. The complete/naturalWidth check also handles images that
 * already failed before JavaScript attached the listener.
 */
function setupPosterFallbacks() {
    const posters = document.querySelectorAll(
        ".movie-poster-with-fallback"
    );

    posters.forEach((poster) => {
        /*
         * Handles poster errors that happen after the listener has
         * been registered.
         */
        poster.addEventListener(
            "error",
            () => showPosterFallback(poster)
        );

        /*
         * Browsers may start loading images while the HTML is still
         * being parsed.
         *
         * A broken image can therefore fail before this JavaScript
         * code attaches the error listener.
         *
         * complete tells us that the loading attempt has finished.
         * naturalWidth === 0 means that no usable image was loaded.
         */
        if (
            poster.complete
            && poster.naturalWidth === 0
        ) {
            showPosterFallback(
                poster
            );
        }
    });
}


setupPosterFallbacks();


/*
 * Add Movie and Update Movie both reload a page on which the same
 * movie still exists. Their forms therefore use the same position
 * preservation mechanism.
 */
document.querySelectorAll(
    ".add-movie-form, .update-movie-form"
).forEach((form) => {
    form.addEventListener(
        "submit",
        () => saveMovieScrollPosition(form)
    );
});


/*
 * Waiting for the complete window load is intentional.
 *
 * Movie posters can change the page layout while they are loading.
 * Restoring the position after images have loaded makes the final
 * scroll position more reliable.
 */
window.addEventListener(
    "load",
    restoreMovieScrollPosition
);