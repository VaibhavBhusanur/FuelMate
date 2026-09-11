// rides.js — FuelMate v2 core logic (with full-page fuel screen + fixed Start Ride + Back buttons)
const BASE = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
  // ---------- GLOBAL STATE ----------
  let allVehicles = [];
  let selectedVehicle = null;   // full vehicle object
  let currentRideId = null;
  let gpsTimer = null;
  let fuelForNextRide = null;   // from fuel screen
  let currentFuelPrice = null;
let currentFuelState = null;
  let fuelOpenedFromHome = false;
  // ---------- RESTORE SAVED RIDE SETUP ----------

try {
  const savedVehicle = localStorage.getItem(
    "fuelmate_selected_vehicle"
  );

  const savedFuel = localStorage.getItem(
    "fuelmate_fuel_for_next_ride"
  );

  if (savedVehicle) {
    selectedVehicle = JSON.parse(savedVehicle);
  }

  if (savedFuel !== null) {
    const parsedFuel = parseFloat(savedFuel);

    if (!Number.isNaN(parsedFuel)) {
      fuelForNextRide = parsedFuel;
    }
  }

  console.log("Restored selectedVehicle:", selectedVehicle);
  console.log("Restored fuelForNextRide:", fuelForNextRide);

} catch (err) {
  console.warn("Could not restore saved ride setup:", err);
}
  let wizardAnimated = false; // track if we've already run the shift animation
function navigateTo(screen) {
  const screens = [loginPage, splash, wizard, fuelScreen, dashboard];

  screens.forEach(s => {
    if (!s) return;
    s.classList.add("hidden");
  });

  if (screen) {
    screen.classList.remove("hidden");
  }
}
async function checkExistingLogin() {

  const token = localStorage.getItem("fuelmate_token");

  if (!token) {
    return false;
  }

  try {

    const res = await fetch(`${BASE}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    if (!res.ok) {
      localStorage.removeItem("fuelmate_token");
      localStorage.removeItem("fuelmate_user");
      return false;
    }

    return true;

  } catch (err) {

    console.error(err);

    return false;

  }

}
  

  // ---------- ELEMENTS ----------
  
  const wizardStepsCard = document.querySelector(".wizard-steps-card");
  const wizardSummaryCard = document.getElementById("wizardSummary");

  const loginPage = document.getElementById("loginPage");
  const loginForm = document.getElementById("loginForm");
  const splash = document.getElementById("splash");
  const splashMessage = document.getElementById("splashMessage");

  const wizard = document.getElementById("vehicleWizard");
  const fuelScreen = document.getElementById("fuelScreen");
  const dashboard = document.getElementById("dashboard");
  const homePage = document.getElementById("homePage");

  const homeStartRideBtn = document.getElementById("homeStartRideBtn");
  const homeFuelBtn = document.getElementById("homeFuelBtn");
  const homeHistoryBtn = document.getElementById("homeHistoryBtn");
  const homeVehicleBtn = document.getElementById("homeVehicleBtn");
  const homeUserName = document.getElementById("homeUserName");
  const homeVehicle = document.getElementById("homeVehicle");
  const homeFuelLeft = document.getElementById("homeFuelLeft");
  const homeRange = document.getElementById("homeRange");

  // wizard selects
  const brandSelect = document.getElementById("wizardBrandSelect");
  const modelSelect = document.getElementById("wizardModelSelect");
  const yearSelect = document.getElementById("wizardYearSelect");

  // wizard steps
  const stepBrand = document.getElementById("stepBrand");
  const stepModel = document.getElementById("stepModel");
  const stepYear = document.getElementById("stepYear");

  // wizard summary (NEW IDs from HTML)
  const summaryTitle = document.getElementById("summaryTitle");
  const summaryMileage = document.getElementById("summaryMileage");
  const summaryTank = document.getElementById("summaryTank");

  const confirmBtn = document.getElementById("confirmWizard");

  // fuel screen
  const fuelInputLitres = document.getElementById("fuelInputLitres");
  const fuelContinueBtn = document.getElementById("fuelContinueBtn");
  const fuelError = document.getElementById("fuelError");
  const fuelModeLitres = document.getElementById("fuelModeLitres");
  const fuelModeRupees = document.getElementById("fuelModeRupees");

  const litresFuelInputGroup =
  document.getElementById("litresFuelInputGroup");

  const rupeesFuelInputGroup =
  document.getElementById("rupeesFuelInputGroup");

  const fuelInputRupees =
  document.getElementById("fuelInputRupees");

  const fuelPriceDisplay =
  document.getElementById("fuelPriceDisplay");

  // dashboard
  const startRideBtn = document.getElementById("startRideBtn");
  const endRideBtn = document.getElementById("endRideBtn");


  const liveDistance = document.getElementById("liveDistance");
  const liveAvgSpeed = document.getElementById("liveAvgSpeed");
  const liveFuelUsed = document.getElementById("liveFuelUsed");
  const liveFuelLeft = document.getElementById("liveFuelLeft");
  const liveMileage = document.getElementById("liveMileage");
  const liveDuration = document.getElementById("liveDuration");

  const rideControlsPage = document.getElementById("rideControlsPage");
  const liveMetricsPage = document.getElementById("liveMetricsPage");

  const goToMetricsBtn = document.getElementById("goToMetricsBtn");
  const backToControlsBtn = document.getElementById("backToControlsBtn");
  const historyBtn = document.getElementById("historyBtn");
  const backFromControls = document.getElementById("backFromControls");
  const rideHistoryPage = document.getElementById("rideHistoryPage");
  const rideHistoryBody = document.getElementById("rideHistoryBody");
  const backFromHistoryBtn = document.getElementById("backFromHistoryBtn");

  const rideIndicator = document.getElementById("rideIndicator");
  const rideDetailsPage = document.getElementById("rideDetailsPage");

  const detailRideTitle = document.getElementById("detailRideTitle");
  const detailRideDate = document.getElementById("detailRideDate");

  const detailDistance = document.getElementById("detailDistance");
  const detailFuelUsed = document.getElementById("detailFuelUsed");
  const detailSpeed = document.getElementById("detailSpeed");
  const detailMileage = document.getElementById("detailMileage");
  const detailFuelLeft = document.getElementById("detailFuelLeft");
  const detailDuration = document.getElementById("detailDuration");

  const backFromDetailsBtn = document.getElementById("backFromDetailsBtn");


    // ride controls / summary UI
  const rideStatusText   = document.getElementById("rideStatusText");
  const rideStatusHint   = document.getElementById("rideStatusHint");


  // ---------- UTILS ----------
  const norm = (s) => (s || "").trim().toLowerCase();
  const show = (el) => el && el.classList.remove("hidden");
  const hide = (el) => el && el.classList.add("hidden");
  const setText = (el, text) => { if (el) el.textContent = text; };
  // ---------- HOME PAGE ----------
async function showHomePage() {

  // Show Home
  homePage.classList.remove("hidden");

  // Hide other dashboard pages
  rideControlsPage.classList.add("hidden");
  liveMetricsPage.classList.add("hidden");
  rideHistoryPage.classList.add("hidden");

  // ---------- HOME DATA ----------

  // User name
  try {
    const storedUser = JSON.parse(
      localStorage.getItem("fuelmate_user") || "null"
    );

    if (storedUser?.name) {
      setText(homeUserName, storedUser.name);
    }
  } catch (err) {
    console.warn("Could not load saved user:", err);
  }

  // Selected vehicle
  if (selectedVehicle) {

    setText(
      homeVehicle,
      `${selectedVehicle.brand} ${selectedVehicle.model}`
    );

    const vehicleYear = document.querySelector(".vehicle-year");

    if (vehicleYear) {
      setText(
        vehicleYear,
        `${selectedVehicle.year}`
      );
    }

    // Vehicle image
    const vehicleImage = document.getElementById("vehicleImage");

    if (vehicleImage) {
      vehicleImage.alt =
        `${selectedVehicle.brand} ${selectedVehicle.model}`;
    }
  }

  // Fuel
  // Fuel
if (selectedVehicle && selectedVehicle.id) {

  try {

    const fuelResponse = await fetch(
      `${BASE}/fuel/${selectedVehicle.id}`
    );

    if (fuelResponse.ok) {

      const fuelData = await fuelResponse.json();

      const fuel = Number(
        fuelData.fuel_level || 0
      );

      // Keep local state synchronized
      fuelForNextRide = fuel;

      localStorage.setItem(
        "fuelmate_fuel_for_next_ride",
        String(fuel)
      );

      setText(
        homeFuelLeft,
        `${fuel.toFixed(1)} L`
      );

      if (selectedVehicle.mileage != null) {

        const range =
          fuel * Number(selectedVehicle.mileage);

        setText(
          homeRange,
          `${range.toFixed(0)} km`
        );
      }
    }

  } catch (err) {

    console.warn(
      "Could not load current fuel:",
      err
    );
  }
}
}

function hideHomePage() {

  homePage.classList.add("hidden");

}
function showControlsPage() {
  hide(homePage);
  hide(liveMetricsPage);
  hide(backToControlsBtn);
  hide(goToMetricsBtn);
  show(rideControlsPage);
}




function showMetricsPage() {
  hide(homePage);
  hide(rideControlsPage);
  show(liveMetricsPage);
}
function showHistoryPage() {
  hide(homePage);
  hide(rideControlsPage);
  hide(liveMetricsPage);
  show(rideHistoryPage);
}

function hideHistoryPage() {
  hide(rideHistoryPage);
  showHomePage();
}

function showRideDetailsPage() {
    rideHistoryPage.classList.add("hidden");
    rideDetailsPage.classList.remove("hidden");
}

function hideRideDetailsPage() {
    rideDetailsPage.classList.add("hidden");
    rideHistoryPage.classList.remove("hidden");
}


/* ----------------------------
   RideController (authoritative)
   ---------------------------- */
const RideController = {

  async start(evt) {
    evt?.preventDefault?.();

    if (!selectedVehicle) {
      alert("Select and confirm a vehicle first.");
      return;
    }

    const startFuel = fuelForNextRide;
    if (startFuel == null || Number.isNaN(startFuel) || startFuel <= 0) {
      alert("Enter fuel in the previous step first.");
      return;
    }

    // SHOW CONTROLS PAGE FIRST
// SHOW CONTROLS PAGE FIRST
showControlsPage();
hide(goToMetricsBtn);

// THEN TURN INDICATOR ON
rideIndicator.classList.remove("indicator-off");
rideIndicator.classList.add("indicator-active");


   // UI feedback immediately
startRideBtn.disabled = true;
setText(rideStatusText, "Starting ride…");
setText(rideStatusHint, "Initializing, please wait…");

// smooth fade + lift animation (new)
if (window.gsap) {
  gsap.fromTo(
    rideControlsPage,
    { opacity: 0, y: 20 },
    { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }
  );
}


    try {
      const res = await fetch(`${BASE}/rides/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: 1,
          vehicle_id: selectedVehicle.id,
          start_fuel: startFuel,
          odometer_start: 0
        })
      });

     const data = await res.json();

if (!res.ok) {
  alert("Failed to start ride.");
  startRideBtn.disabled = false;
  return;
}

      currentRideId = data.ride_id;

hide(startRideBtn);
show(endRideBtn);
endRideBtn.disabled = false;
hide(historyBtn);

setText(rideStatusText, "Ride in progress");
      setText(rideStatusHint, "Tracking your trip. Tap End Ride when done.");

      if (gpsTimer) clearInterval(gpsTimer);
      gpsTimer = setInterval(() => {
        if (currentRideId) pingLocation(currentRideId);
      }, 5000);

    } catch (err) {
      alert("Server error starting ride.");
      startRideBtn.disabled = false;
    }
  },

  async end(evt) {
    evt?.preventDefault?.();

    if (!currentRideId) {
      alert("No active ride to end.");
      return;
    }

    endRideBtn.disabled = true;
hide(endRideBtn);   // <--- add this immediately

setText(rideStatusText, "Ending ride…");
setText(rideStatusHint, "Finalizing trip data…");


    try {
      const res = await fetch(`${BASE}/rides/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ride_id: currentRideId })
      });

      if (!res.ok) {
  const errorText = await res.text();

  console.error("END RIDE API ERROR:", res.status, errorText);

  alert("Failed to end ride.");
  endRideBtn.disabled = false;
  show(endRideBtn);

  return;
}

const data = await res.json();
      // ---- Update final metrics from /rides/end ----
if (data.distance_km != null) {
  setText(liveDistance, `${data.distance_km.toFixed(3)} km`);
}

if (data.avg_speed_kmh != null) {
  setText(liveAvgSpeed, `${data.avg_speed_kmh.toFixed(2)} km/h`);
}

if (data.fuel_used_l != null) {
  setText(liveFuelUsed, `${data.fuel_used_l.toFixed(3)} L`);
}

if (data.fuel_left_l != null) {
  setText(liveFuelLeft, `${data.fuel_left_l.toFixed(3)} L`);
}

if (data.mileage_km_per_l != null) {
  setText(liveMileage, `${data.mileage_km_per_l.toFixed(2)} km/L`);
}

if (data.duration != null) {
  setText(liveDuration, data.duration);
}

if (data.predicted_range_km != null) {
  const rangeEl = document.getElementById("liveRange");
  if (rangeEl) {
    rangeEl.textContent = `${data.predicted_range_km.toFixed(2)} km`;
  }
}

      if (gpsTimer) {
        clearInterval(gpsTimer);
        gpsTimer = null;
      }

      currentRideId = null;

      // TURN INDICATOR OFF + SWITCH TO METRICS PAGE
      rideIndicator.classList.remove("indicator-active");
      rideIndicator.classList.add("indicator-off");
      showMetricsPage();

// strong slide-in from right
if (window.gsap) {
  gsap.fromTo(
    liveMetricsPage,
    { x: 80, opacity: 0, scale: 0.95 },
    {
      x: 0,
      opacity: 1,
      scale: 1,
      duration: 0.55,
      ease: "power3.out",
      onComplete: () => {
        show(backToControlsBtn);  // show back button after animation
      }
    }
  );
} else {
  show(backToControlsBtn);
}
// -------- LOW FUEL ALERT UI --------
const lowFuelEl = document.getElementById("lowFuelAlert");

if (lowFuelEl) {
  if (data.low_fuel_alert === true) {
    lowFuelEl.classList.remove("hidden");
  } else {
    lowFuelEl.classList.add("hidden");
  }
}
// -------- NEARBY PETROL PUMPS FETCH (ONLY WHEN LOW FUEL) --------
if (data.low_fuel_alert === true && data.last_location) {
  try {
    const lat = data.last_location.lat;
    const lon = data.last_location.lon;

    const resFuel = await fetch(
      `${BASE}/rides/nearby_fuel?lat=${lat}&lon=${lon}`
    );

    if (resFuel.ok) {
      const fuelData = await resFuel.json();

      const box = document.getElementById("fuelStationsBox");
      const list = document.getElementById("fuelStationsList");

      if (box && list && fuelData.stations && fuelData.stations.length > 0) {
        list.innerHTML = "";

        fuelData.stations.forEach(station => {
          const li = document.createElement("li");
          li.textContent = station.name || "Fuel Station";
          list.appendChild(li);
        });

        box.classList.remove("hidden");
      }
    }
  } catch (err) {
    console.error("Nearby fuel fetch failed:", err);
  }
}



hide(endRideBtn);
show(startRideBtn);
show(historyBtn);

endRideBtn.disabled = false;
startRideBtn.disabled = false;
startRideBtn.textContent = "Start New Ride";

setText(rideStatusText, "Ride finished");
setText(rideStatusHint, "Review your stats or start a new ride.");


    } catch (err) {
      alert("Server error ending ride.");
      endRideBtn.disabled = false;
    }
  }
};


  

  // ----------------------------------------------
// CLEAN BACK BUTTONS (FINAL, WORKING)
// ----------------------------------------------
const backFromWizard = document.getElementById("backFromWizard");
if (backFromWizard) {
  backFromWizard.addEventListener("click", () => {
    hide(wizard);
    show(loginPage);
  });
}

const backFromFuel = document.getElementById("backFromFuel");

if (backFromFuel) {
  backFromFuel.addEventListener("click", () => {

    hide(fuelScreen);

    if (fuelOpenedFromHome) {
      fuelOpenedFromHome = false;
      navigateTo(dashboard);
      showHomePage();
    } else {
      show(wizard);
    }

  });
}

const backFromDashboard = document.getElementById("backFromDashboard");

if (backFromDashboard) {
  backFromDashboard.addEventListener("click", () => {
    showHomePage();
  });
}

// ---------- AUTO LOGIN ----------
(async () => {

  const loggedIn = await checkExistingLogin();

  if (loggedIn) {

    navigateTo(splash);

    if (splashMessage) {
      setText(splashMessage, "Welcome back...");
    }

    try {

      await loadVehicles();

      await new Promise(r => setTimeout(r, 800));

      navigateTo(dashboard);
      showHomePage();

    } catch (err) {

      console.error(err);

      navigateTo(loginPage);

    }

  }

})();



 // ---------- LOGIN FLOW ----------
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("username").value.trim();
    const pass = document.getElementById("password").value.trim();

    if (!email || !pass) {
      alert("Enter email and password");
      return;
    }

    // STEP 1: Fade login out and WAIT for animation
    if (window.gsap) {
      await new Promise(resolve => {
        gsap.to(loginPage, {
          opacity: 0,
          y: -10,
          duration: 0.35,
          ease: "power2.out",
          onComplete: resolve
        });
      });
    }

try {

  // Authenticate user
  const loginRes = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      email: email,
      password: pass
    })
  });

  const loginData = await loginRes.json();

  if (!loginRes.ok) {
    alert(loginData.detail || "Login failed.");
    navigateTo(loginPage);
    return;
  }

  // Save JWT
  localStorage.setItem(
    "fuelmate_token",
    loginData.access_token
  );

  localStorage.setItem(
    "fuelmate_user",
    JSON.stringify(loginData.user)
  );

  // Show splash
  navigateTo(splash);

  if (splashMessage) {
    setText(
      splashMessage,
      `Welcome ${loginData.user.name}...`
    );
  }

  // Load vehicles
  await loadVehicles();

  await new Promise(r => setTimeout(r, 800));

  navigateTo(wizard);

  if (window.gsap) {
    gsap.fromTo(
      wizard,
      { opacity: 0, x: 40 },
      {
        opacity: 1,
        x: 0,
        duration: 0.55,
        ease: "power3.out"
      }
    );
  }

} catch (err) {

  console.error(err);

  alert("Unable to connect to server.");

  navigateTo(loginPage);

}
  });
}

  // ---------- LOAD VEHICLES ----------
  async function loadVehicles() {
    const res = await fetch(`${BASE}/vehicles/list`);
    if (!res.ok) {
      throw new Error("Failed to fetch vehicles");
    }
    const data = await res.json();

console.log("API RESPONSE:", data);
console.log("Vehicles property:", data.vehicles);

allVehicles = data.vehicles || [];

console.log("Loaded vehicles:", allVehicles.length);
    allVehicles = data.vehicles || [];
    console.log("allVehicles:", allVehicles);
    console.log("Loaded vehicles:", allVehicles.length);
    populateBrandSelect();
  }

  function populateBrandSelect() {
    brandSelect.innerHTML = `<option value="">-- Select Brand --</option>`;

    const brands = [...new Set(
      allVehicles
        .map(v => (v.brand || "").trim())
        .filter(Boolean)
    )].sort((a, b) => a.localeCompare(b));

    brands.forEach(brand => {
      const opt = document.createElement("option");
      opt.value = brand;
      opt.textContent = brand;
      brandSelect.appendChild(opt);
    });
  }

  // ---------- WIZARD: BRAND → MODEL ----------
  if (brandSelect) {
    brandSelect.addEventListener("change", () => {
      const brand = brandSelect.value;
      console.log("Brand selected:", brand);

        hide(stepModel);
      hide(stepYear);
      hide(wizardSummaryCard);
      modelSelect.innerHTML = `<option value="">-- Select Model --</option>`;
      modelSelect.disabled = true;
      yearSelect.innerHTML = `<option value="">-- Select Year --</option>`;
      yearSelect.disabled = true;
      selectedVehicle = null;


      if (!brand) return;

      const models = [...new Set(
        allVehicles
          .filter(v => norm(v.brand) === norm(brand))
          .map(v => (v.model || "").trim())
          .filter(Boolean)
      )].sort((a, b) => a.localeCompare(b));

      console.log("Models for brand:", brand, models);

      models.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m;
        modelSelect.appendChild(opt);
      });

      modelSelect.disabled = false;
      show(stepModel);
    });
  }

  // ---------- WIZARD: MODEL → YEAR ----------
  if (modelSelect && yearSelect) {
    modelSelect.addEventListener("change", () => {
      const brand = brandSelect.value;
      const model = modelSelect.value.trim();
      console.log("Model selected:", model);

            hide(stepYear);
      hide(wizardSummaryCard);
      yearSelect.innerHTML = `<option value="">-- Select Year --</option>`;
      yearSelect.disabled = true;
      selectedVehicle = null;


      if (!model) return;

      const years = [...new Set(
        allVehicles
          .filter(v =>
            norm(v.brand) === norm(brand) &&
            norm(v.model) === norm(model)
          )
          .map(v => v.year)
      )]
        .filter(y => y !== null && y !== undefined)
        .map(y => Number(y))
        .filter(y => !Number.isNaN(y))
        .sort((a, b) => a - b);

      console.log("Years for brand/model:", brand, model, years);

      years.forEach(y => {
        const opt = document.createElement("option");
        opt.value = String(y);
        opt.textContent = String(y);
        yearSelect.appendChild(opt);
      });

      if (years.length > 0) {
        yearSelect.disabled = false;
        show(stepYear);
      }
    });
  }

  // ---------- WIZARD: YEAR → SUMMARY ----------
    if (yearSelect) {
    yearSelect.addEventListener("change", () => {
      const brand = brandSelect.value;
      const model = modelSelect.value.trim();
      const year = yearSelect.value;
      console.log("Year selected:", year);

      if (!year) {
        hide(wizardSummaryCard);
        selectedVehicle = null;
        return;
      }

      const vehicle = allVehicles.find(v =>
        norm(v.brand) === norm(brand) &&
        norm(v.model) === norm(model) &&
        String(v.year) === String(year)
      );

      console.log("Matched vehicle:", vehicle);

      if (!vehicle) {
        hide(wizardSummaryCard);
        selectedVehicle = null;
        return;
      }

      selectedVehicle = vehicle;

  // Persist selected vehicle for the current logged-in session
  localStorage.setItem(
  "fuelmate_selected_vehicle",
  JSON.stringify(selectedVehicle)
);

// 🔥 BIND TO NEW SUMMARY IDS
      setText(summaryTitle, `${vehicle.brand} ${vehicle.model} (${vehicle.year})`);
      setText(summaryMileage, `Mileage: ${vehicle.mileage} km/L`);
      setText(summaryTank, `Tank capacity: ${vehicle.tank_capacity} L`);

      show(wizardSummaryCard);

      // Optional GSAP animation (safe)
      if (!wizardAnimated && window.gsap && wizardStepsCard && wizardSummaryCard) {
        wizardAnimated = true;

        const tl = gsap.timeline();

        tl.to(wizardStepsCard, {
          duration: 0.6,
          x: -120,
          ease: "power3.inOut"
        });

        tl.fromTo(
          wizardSummaryCard,
          { opacity: 0, x: 40, scale: 0.97 },
          { opacity: 1, x: 0, scale: 1, duration: 0.6, ease: "power3.out" },
          "-=0.3"
        );
      }
    });
  }


  // ---------- CONFIRM VEHICLE → FUEL SCREEN ----------
  if (confirmBtn) {
    confirmBtn.addEventListener("click", () => {
      if (!selectedVehicle) {
        alert("Please complete all steps before confirming.");
        return;
      }

      console.log("Vehicle confirmed:", selectedVehicle);

      navigateTo(fuelScreen);
    });
  }

  // ---------- FUEL SCREEN ----------
  if (fuelModeLitres) {
  fuelModeLitres.addEventListener("click", () => {

    fuelModeLitres.classList.add("active");
    fuelModeRupees.classList.remove("active");

    show(litresFuelInputGroup);
    hide(rupeesFuelInputGroup);

    hide(fuelError);
  });
}


if (fuelModeRupees) {
  fuelModeRupees.addEventListener("click", () => {

    fuelModeRupees.classList.add("active");
    fuelModeLitres.classList.remove("active");

    hide(litresFuelInputGroup);
    show(rupeesFuelInputGroup);

    hide(fuelError);

    // Reset previous price
    currentFuelPrice = null;
    currentFuelState = null;

    setText(
      fuelPriceDisplay,
      "Fuel price: Detecting your location..."
    );

    // Ask browser for current location
    if (!navigator.geolocation) {
      setText(
        fuelPriceDisplay,
        "Location services are not available."
      );
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {

        try {

          const lat = position.coords.latitude;
          const lon = position.coords.longitude;

          const response = await fetch(
            `${BASE}/fuel/price?lat=${lat}&lon=${lon}`
          );

          const data = await response.json();

          if (!response.ok) {
            throw new Error(
              data.detail || "Could not get fuel price."
            );
          }

          currentFuelPrice = Number(
            data.price_per_litre
          );

          currentFuelState = data.state;

          setText(
            fuelPriceDisplay,
            `Petrol price in ${data.state}: ₹${currentFuelPrice.toFixed(2)} / litre`
          );

          console.log(
            "Fuel price detected:",
            currentFuelState,
            currentFuelPrice
          );

        } catch (error) {

          console.error(
            "Fuel price lookup failed:",
            error
          );

          currentFuelPrice = null;

          setText(
            fuelPriceDisplay,
            "Could not determine fuel price."
          );
        }
      },

      (error) => {

        console.error(
          "Location permission error:",
          error
        );

        currentFuelPrice = null;

        setText(
          fuelPriceDisplay,
          "Location permission is required for automatic fuel price."
        );
      },

      {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 300000
      }
    );
  });
}
if (fuelContinueBtn) {
  fuelContinueBtn.addEventListener("click", async () => {

    let val;

// ==========================================
// LITRES MODE
// ==========================================

if (fuelModeLitres.classList.contains("active")) {

  val = parseFloat(fuelInputLitres.value);

  if (Number.isNaN(val) || val <= 0) {
    setText(
      fuelError,
      "Please enter a valid fuel amount in litres."
    );
    show(fuelError);
    return;
  }

}


// ==========================================
// RUPEES MODE
// ==========================================

else if (fuelModeRupees.classList.contains("active")) {

  const rupees =
  parseFloat(fuelInputRupees.value);

const price = currentFuelPrice;

  if (Number.isNaN(rupees) || rupees <= 0) {
    setText(
      fuelError,
      "Please enter a valid amount in rupees."
    );
    show(fuelError);
    return;
  }

  if (!price || price <= 0) {
  setText(
    fuelError,
    "Fuel price could not be determined. Please allow location access."
  );
  show(fuelError);
  return;
}

  // Convert rupees → litres
  val = rupees / price;

}

    hide(fuelError);

    // ==========================================
    // ADD FUEL FROM HOME
    // ==========================================

    if (fuelOpenedFromHome) {

      if (!selectedVehicle || !selectedVehicle.id) {
        setText(
          fuelError,
          "No vehicle selected."
        );
        show(fuelError);
        return;
      }

      try {

        // Get current fuel
        const currentResponse = await fetch(
          `${BASE}/fuel/${selectedVehicle.id}`
        );

        const currentData = await currentResponse.json();

        if (!currentResponse.ok) {
          throw new Error(
            currentData.detail || "Unable to get current fuel."
          );
        }

        const currentFuel =
          Number(currentData.fuel_level || 0);

        const newFuel =
          currentFuel + val;

        // Save new total fuel
        const updateResponse = await fetch(
          `${BASE}/fuel/update`,
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json"
            },

            body: JSON.stringify({
              vehicle_id: selectedVehicle.id,
              fuel_level: newFuel
            })
          }
        );

        const updateData =
          await updateResponse.json();

        if (!updateResponse.ok) {
          throw new Error(
            updateData.detail || "Unable to update fuel."
          );
        }

        // Update local ride fuel value
        fuelForNextRide =
          Number(updateData.fuel_level);

        localStorage.setItem(
          "fuelmate_fuel_for_next_ride",
          String(fuelForNextRide)
        );

        // Update Home display
        if (homeFuelLeft) {
          homeFuelLeft.textContent =
            `${fuelForNextRide.toFixed(1)} L`;
        }

        if (homeRange) {
          const range =
            fuelForNextRide *
            Number(selectedVehicle.mileage || 0);

          homeRange.textContent =
            `${range.toFixed(0)} km`;
        }

        // Return directly to Home
        fuelOpenedFromHome = false;

        navigateTo(dashboard);
        showHomePage();

        return;

      } catch (err) {

        console.error("Add Fuel failed:", err);

        setText(
          fuelError,
          err.message || "Unable to update fuel."
        );

        show(fuelError);

        return;
      }
    }


    // ==========================================
    // ORIGINAL INITIAL SETUP FLOW
    // ==========================================

    fuelForNextRide = val;

    localStorage.setItem(
      "fuelmate_fuel_for_next_ride",
      String(fuelForNextRide)
    );

    hide(fuelScreen);

    if (splashMessage) {
      setText(
        splashMessage,
        "Setting up your dashboard..."
      );
    }

    show(splash);

    setTimeout(() => {
      navigateTo(dashboard);
      showHomePage();
    }, 4200);

  });
}

  // ---------- PING LOCATION ----------
  async function pingLocation(rideId) {
    if (!navigator.geolocation) {
      console.warn("Geolocation not available.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const res = await fetch(`${BASE}/rides/update_location`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ride_id: rideId,
              lat: pos.coords.latitude,
              lon: pos.coords.longitude,
              timestamp: new Date().toISOString()
            })
          });

          let data = null;
try {
  data = await res.json();
  console.log("UPDATE LOCATION RESPONSE:", data);
} catch (e) {
  console.error("Invalid JSON from update_location");
  return;
}

if (!res.ok || !data) {
  console.error("Update location failed:", data);
  return;
}


          if (data.distance_km != null) {
  setText(liveDistance, `${data.distance_km.toFixed(3)} km`);
}

          if (data.avg_speed_kmh != null) {
            setText(liveAvgSpeed, `${data.avg_speed_kmh.toFixed(2)} km/h`);
          }
          if (data.fuel_used_l != null) {
            setText(liveFuelUsed, `${data.fuel_used_l.toFixed(3)} L`);
          }
          if (data.fuel_remaining_l != null) {
            setText(liveFuelLeft, `${data.fuel_remaining_l.toFixed(3)} L`);
          }
          if (data.mileage_km_per_l != null) {
            setText(liveMileage, `${data.mileage_km_per_l.toFixed(2)} km/L`);
          }
          if (data.duration != null) {
            setText(liveDuration, data.duration);
          }
        } catch (err) {
          console.error("Ping failed:", err);
        }
      },
      (err) => {
        console.warn("Geolocation error:", err.message);
      },
      {
  enableHighAccuracy: true,
  timeout: 15000,
  maximumAge: 0
}
    );
  }

// ---------- LOAD RIDE HISTORY ----------
async function loadRideHistory() {

  try {

    const res = await fetch(`${BASE}/rides/recent/1`);

    if (!res.ok) {
      alert("Unable to load ride history.");
      return;
    }

    const data = await res.json();
    console.log("RAW RESPONSE:", data);
    console.log("VEHICLES ARRAY:", data.vehicles);
    console.log("COUNT:", data.vehicles?.length);

    rideHistoryBody.innerHTML = "";

    if (!data.rides || data.rides.length === 0) {

      rideHistoryBody.innerHTML = `
<div class="ride-card">
    <p style="text-align:center;">No rides found.</p>
</div>
`;

      return;
    }

    data.rides.forEach((ride) => {

    const date = new Date(ride.start_time);

    const rideDate = date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });

    const rideTime = date.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit"
    });

    const mileage =
        (ride.fuel_used_l ?? 0) > 0
            ? (ride.distance_km / ride.fuel_used_l).toFixed(2)
            : "-";

    const card = document.createElement("div");

    card.className = "ride-card";

    card.innerHTML = `
        <div class="ride-header">

            <div>
                <div class="ride-title">
                    Ride #${ride.ride_id}
                </div>

                <div class="ride-date">
                    ${rideDate} • ${rideTime}
                </div>
            </div>

        </div>

        <div class="ride-grid">

            <div class="ride-item">
                <span class="ride-label">Distance</span>
                <span class="ride-value">${(ride.distance_km ?? 0).toFixed(2)} km</span>
            </div>

            <div class="ride-item">
                <span class="ride-label">Fuel Used</span>
                <span class="ride-value">${(ride.fuel_used_l ?? 0).toFixed(3)} L</span>
            </div>

            <div class="ride-item">
                <span class="ride-label">Avg Speed</span>
                <span class="ride-value">${(ride.avg_speed_kmh ?? 0).toFixed(2)} km/h</span>
            </div>

            <div class="ride-item">
                <span class="ride-label">Mileage</span>
                <span class="ride-value">${mileage} km/L</span>
            </div>

        </div>

        <button
    class="btn-secondary view-ride-btn"
    data-ride='${JSON.stringify(ride)}'>
    View Details
</button>
    `;

    rideHistoryBody.appendChild(card);
    const btn = card.querySelector(".view-ride-btn");

btn.addEventListener("click", () => {

    const rideData = JSON.parse(btn.dataset.ride);

    const mileage =
        rideData.fuel_used_l > 0
            ? (rideData.distance_km / rideData.fuel_used_l).toFixed(2)
            : "-";

    detailRideTitle.textContent = `Ride #${rideData.ride_id}`;

    detailRideDate.textContent =
        `${rideDate} • ${rideTime}`;

    detailDistance.textContent =
        `${(rideData.distance_km ?? 0).toFixed(2)} km`;

    detailFuelUsed.textContent =
        `${(rideData.fuel_used_l ?? 0).toFixed(3)} L`;

    detailSpeed.textContent =
        `${(rideData.avg_speed_kmh ?? 0).toFixed(2)} km/h`;

    detailMileage.textContent =
        `${mileage} km/L`;

    detailFuelLeft.textContent =
        `${(rideData.fuel_left_l ?? 0).toFixed(3)} L`;

    detailDuration.textContent =
    rideData.duration ?? "--";

    showRideDetailsPage();

});

});

  } catch (err) {

    console.error(err);
    alert("Failed to load ride history.");

  }

}

  // ---------- START RIDE ----------
if (startRideBtn) startRideBtn.addEventListener("click", RideController.start);

// ---------- END RIDE ----------
if (endRideBtn) endRideBtn.addEventListener("click", RideController.end);

if (goToMetricsBtn) {
  goToMetricsBtn.addEventListener("click", () => {
    showMetricsPage();
  });
}

if (backToControlsBtn) {
  backToControlsBtn.addEventListener("click", () => {
    showControlsPage();
  });
} 
if (backFromControls) {
  backFromControls.addEventListener("click", () => {
    showHomePage();
  });
}
if (historyBtn) {
  historyBtn.addEventListener("click", async () => {

    showHistoryPage();

    await loadRideHistory();

  });
}

if (backFromHistoryBtn) {
  backFromHistoryBtn.addEventListener("click", () => {

    hideHistoryPage();

  });
}
if (backFromDetailsBtn) {

    backFromDetailsBtn.addEventListener("click", () => {

        hideRideDetailsPage();
    });
}
if (homeStartRideBtn) {
  homeStartRideBtn.addEventListener("click", () => {

    console.log("HOME START CLICKED");
    console.log("selectedVehicle:", selectedVehicle);
    console.log("fuelForNextRide:", fuelForNextRide);

    RideController.start();
  });
}

if (homeFuelBtn) {
  homeFuelBtn.addEventListener("click", () => {
    fuelOpenedFromHome = true;

    fuelInputLitres.value = "";
    hide(fuelError);

    navigateTo(fuelScreen);
  });
}

if (homeHistoryBtn) {
  homeHistoryBtn.addEventListener("click", async () => {
    showHistoryPage();
    await loadRideHistory();
  });
}


});