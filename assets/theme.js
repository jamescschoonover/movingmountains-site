/* Moving Mountains — shared UI behavior (nav scroll, scroll-reveal, bfcache reload) */
(function () {
  var nav = document.getElementById('nav');
  if (nav) {
    var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 40); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  var els = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.14 });
    els.forEach(function (el) { io.observe(el); });
  } else {
    els.forEach(function (el) { el.classList.add('in'); });
  }

  var navToggle=document.getElementById("navToggle"), navLinks=document.getElementById("navLinks");
  if(navToggle&&navLinks){
    navToggle.addEventListener("click",function(){var o=navLinks.classList.toggle("open");navToggle.setAttribute("aria-expanded",o?"true":"false");});
    navLinks.querySelectorAll("a").forEach(function(a){a.addEventListener("click",function(){navLinks.classList.remove("open");navToggle.setAttribute("aria-expanded","false");});});
  }

  // iOS back/forward cache → force fresh load (matches hub no-cache behavior)
  window.addEventListener('pageshow', function (e) { if (e.persisted) location.reload(); });
})();
