/*
 * Preserves the user's position around an Add Movie action.
 *
 * MoviWeb uses the Post/Redirect/Get pattern when a movie is added.
 * A normal redirect reloads the page and would therefore lose the
 * exact viewport position of the clicked button.
 *
 * Before submitting an Add Movie form, this script stores the vertical
 * position of that movie's action area in sessionStorage.
 *
 * After the redirected page and its images have loaded, the same movie
 * action area is found again and returned to approximately the same
 * position inside the browser window.
 */


const movieScrollStorageKey = "moviwebMovieScrollState";


function saveMovieScrollPosition(form) {
    /*
     * Stores the position of the movie action area before the form
     * leaves the current page.
     */

    const actionArea = form.closest(".movie-action-area");

    if (!actionArea || !actionArea.id) {
        return;
    }

    const scrollState = {
        anchorId: actionArea.id,
        viewportTop: actionArea.getBoundingClientRect().top
    };

    sessionStorage.setItem(
        movieScrollStorageKey,
        JSON.stringify(scrollState)
    );
}


function restoreMovieScrollPosition() {
    /*
     * Restores the affected movie action area to its previous position
     * inside the browser viewport after the redirected page has loaded.
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
     * The server adds the movie anchor to redirects caused by movie
     * actions. This check prevents an old saved position from affecting
     * an unrelated page load.
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

    const actionArea = document.getElementById(
        scrollState.anchorId
    );

    if (!actionArea) {
        sessionStorage.removeItem(
            movieScrollStorageKey
        );
        return;
    }

    /*
     * The browser may already have moved to the HTML anchor.
     * We calculate the remaining difference between the current
     * position and the position the user saw before clicking.
     */
    const currentTop = (
        actionArea.getBoundingClientRect().top
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
     * The state is only needed for this single redirect.
     * Removing it prevents later page loads from reusing stale data.
     */
    sessionStorage.removeItem(
        movieScrollStorageKey
    );
}


/*
 * Connects the position-saving behavior to every Add Movie form
 * currently rendered on the page.
 */
document.querySelectorAll(
    ".add-movie-form"
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
 * scroll position more reliable than restoring it immediately when
 * only the HTML structure is available.
 */
window.addEventListener(
    "load",
    restoreMovieScrollPosition
);