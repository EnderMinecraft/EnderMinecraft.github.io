// Parallax drift for the decorative coin floaters in the hero section.
// Desktop only — matches the CSS breakpoint that shows .floaters at all.
(function () {
    var isDesktop = window.matchMedia("(min-width: 781px)").matches;
    if (!isDesktop) return;

    var hero = document.querySelector(".hero");
    var coins = document.querySelectorAll(".coin-wrap");
    if (!hero || !coins.length) return;

    hero.addEventListener("mousemove", function (e) {
        var rect = hero.getBoundingClientRect();
        var x = e.clientX - rect.left - rect.width / 2;
        var y = e.clientY - rect.top - rect.height / 2;

        coins.forEach(function (coin) {
            var depth = parseFloat(coin.dataset.depth) || 0.03;
            coin.style.transform = "translate(" + (x * depth) + "px, " + (y * depth) + "px)";
        });
    });

    hero.addEventListener("mouseleave", function () {
        coins.forEach(function (coin) {
            coin.style.transform = "translate(0, 0)";
        });
    });
})();
