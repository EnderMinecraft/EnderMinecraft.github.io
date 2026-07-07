(function () {
    var isDesktop = window.matchMedia("(min-width: 781px)").matches;
    if (!isDesktop) return;
    var hero = document.querySelector(".hero");
    var coins = document.querySelectorAll(".coin-wrap");
    if (!hero || !coins.length) return;

    var target = { x: 0, y: 0 };
    var current = new Map();
    coins.forEach(function (c) { current.set(c, { x: 0, y: 0 }); });

    document.addEventListener("mousemove", function (e) {
        var rect = hero.getBoundingClientRect();
        target.x = e.clientX - rect.left - rect.width / 2;
        target.y = e.clientY - rect.top - rect.height / 2;

    });
    document.addEventListener("mouseleave", function () {
        target.x = 0;
        target.y = 0;
    });

    function animate() {
        coins.forEach(function (coin) {
            var depth = parseFloat(coin.dataset.depth) || 0.03;
            var c = current.get(coin);
            var tx = target.x * depth;
            var ty = target.y * depth;
            c.x += (tx - c.x) * 0.1; // ease factor
            c.y += (ty - c.y) * 0.1;
            coin.style.transform = "translate(" + c.x + "px, " + c.y + "px)";
        });
        requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
})();
