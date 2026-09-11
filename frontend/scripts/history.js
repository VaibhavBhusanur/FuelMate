const BASE_URL = "http://127.0.0.1:8000";

const USER_ID = 1;

const rideList = document.getElementById("rideList");

async function loadHistory(){

    const res = await fetch(`${BASE_URL}/rides/recent/${USER_ID}`);

    const data = await res.json();

    rideList.innerHTML="";

    data.rides.forEach(ride=>{

        const card=document.createElement("div");

        card.className="ride-card";

        card.innerHTML=`

            <div class="row">
                <strong>${new Date(ride.start_time).toLocaleDateString()}</strong>
                <span>${new Date(ride.start_time).toLocaleTimeString()}</span>
            </div>

            <div class="row">
                <span>Distance</span>
                <span>${ride.distance_km.toFixed(2)} km</span>
            </div>

            <div class="row">
                <span>Fuel Used</span>
                <span>${ride.fuel_used_l.toFixed(3)} L</span>
            </div>

            <div class="row">
                <span>Avg Speed</span>
                <span>${ride.avg_speed_kmh.toFixed(1)} km/h</span>
            </div>

        `;

        rideList.appendChild(card);

    });

}

loadHistory();