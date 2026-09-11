// animations.js — Works with FuelMate scope restrictions

(function () {
  if (!window.gsap) return;

  const watchedIds = [
    "loginPage",
    "splash",
    "vehicleWizard",
    "fuelScreen",
    "dashboard",
    "rideControlsPage",
    "liveMetricsPage"
  ];

  const elements = watchedIds
    .map(id => document.getElementById(id))
    .filter(Boolean);

  // Watch for hidden -> visible changes
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((m) => {
      if (m.attributeName !== "class") return;

      const el = m.target;

      if (!el.classList.contains("hidden")) {
        // If element just became visible, force pre-animation state
        gsap.set(el, { opacity: 0, y: 40 });

        // Animate IN
        gsap.to(el, {
          opacity: 1,
          y: 0,
          duration: 0.45,
          ease: "power3.out"
        });
      }
    });
  });

  // Attach observer to every screen element
  elements.forEach(el => {
    observer.observe(el, { attributes: true });
  });

})();
