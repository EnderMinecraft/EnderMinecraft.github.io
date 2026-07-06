// Neo-brutalist palette doesn't use photo backgrounds, so instead of swapping
// in a random image, we randomize which accent color the hero's grid dots
// and headline pop-shadow use on each visit.
var accents = ["#ff80c1", "#ffd992", "#94ff99", "#a7c3ff"];
var pick = accents[Math.floor(Math.random() * accents.length)];
var backgrndcl = ["#a4b1ff", "#8effe3", "#559e1a", "#ffeab2"];
var bgPick = backgrndcl[Math.floor(Math.random() * backgrndcl.length)];
document.documentElement.style.setProperty('--pink', pick);
document.documentElement.style.setProperty('--bgcl', bgPick);

$(function () {
    $('.hero h1').css('text-shadow', '4px 4px 0 ' + pick);
    $('.hero .kicker').css('background', '#0B0B0B');
});
