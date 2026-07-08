// Hardcoded post list — add a new entry here every time you publish a post.
var allPosts = [
    { title: "Lorem Ipsum Dolor Sit Amet", meta: "Category · Jun 2026", url: "../../blogs/post-template.html" },
    { title: "Ut Enim Ad Minim Veniam", meta: "Category · May 2026", url: "../../blogs/post-template.html" },
    { title: "Duis Aute Irure Dolor", meta: "Category · Apr 2026", url: "../../blogs/post-template.html" },
    { title: "Excepteur Sint Occaecat", meta: "Category · Mar 2026", url: "../../blogs/post-template.html" },
    { title: "Sed Ut Perspiciatis Unde", meta: "Category · Feb 2026", url: "../../blogs/post-template.html" }
];

function pickRandomPost() {
    var titleEl = document.getElementById("randomPostTitle");
    var metaEl = document.getElementById("randomPostMeta");
    var linkEl = document.getElementById("randomPostLink");
    if (!titleEl || !allPosts.length) return;

    var currentUrl = window.location.pathname.split("/").pop();
    var choices = allPosts.filter(function (p) {
        return p.url.indexOf(currentUrl) === -1;
    });
    if (!choices.length) choices = allPosts;

    var pick = choices[Math.floor(Math.random() * choices.length)];

    titleEl.textContent = pick.title;
    metaEl.textContent = pick.meta;
    linkEl.href = pick.url;
}

document.addEventListener("DOMContentLoaded", function () {
    pickRandomPost();
    var btn = document.getElementById("shuffleBtn");
    if (btn) btn.addEventListener("click", pickRandomPost);
});