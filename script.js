const factors = {

    car: 0.20,

    bus: 0.08,

    flight: 0.25,

    electricity: 0.80,

    veg_meal: 0.50,

    nonveg_meal: 2.00

};


const units = {

    car: "km",

    bus: "km",

    flight: "km",

    electricity: "kWh",

    veg_meal: "meal",

    nonveg_meal: "meal"

};


const names = {

    car: "🚗 Car Travel",

    bus: "🚌 Bus Travel",

    flight: "✈️ Flight",

    electricity: "⚡ Electricity",

    veg_meal: "🥗 Vegetarian Meal",

    nonveg_meal: "🍗 Non-Vegetarian Meal"

};


const categories = {

    car: "Transport",

    bus: "Transport",

    flight: "Transport",

    electricity: "Energy",

    veg_meal: "Food",

    nonveg_meal: "Food"

};



/* =========================================================
   UTILITIES
========================================================= */


function localDate() {

    const d = new Date();

    const year = d.getFullYear();

    const month =
        String(d.getMonth() + 1)
        .padStart(2, "0");

    const day =
        String(d.getDate())
        .padStart(2, "0");

    return `${year}-${month}-${day}`;
}


function formatDate(value) {

    if (!value) return "—";

    const d =
        new Date(value + "T00:00:00");

    return d.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );

}


function showMessage(text) {

    const box =
        document.getElementById("message");

    box.className = "message";

    box.textContent = text;


    setTimeout(() => {

        box.className = "";

    }, 3000);

}


/* =========================================================
   DAILY ACTIVITY
========================================================= */


function updateUnit() {

    const type =
        document.getElementById(
            "activityType"
        ).value;


    document.getElementById("unit").value =
        units[type];


    updatePreview();

}


function updatePreview() {

    const type =
        document.getElementById(
            "activityType"
        ).value;


    const quantity =
        parseFloat(
            document.getElementById(
                "quantity"
            ).value
        ) || 0;


    const co2 =
        quantity * factors[type];


    document.getElementById("preview").innerHTML =
        `Estimated impact: <strong>${co2.toFixed(2)} kg CO₂</strong>`;

}


async function addActivity(event) {

    event.preventDefault();


    const type =
        document.getElementById(
            "activityType"
        ).value;


    const quantity =
        parseFloat(
            document.getElementById(
                "quantity"
            ).value
        );


    const date =
        document.getElementById(
            "activityDate"
        ).value;


    if (!quantity || quantity <= 0) {

        showMessage(
            "Please enter a valid quantity."
        );

        return;
    }


    try {

        const response =
            await fetch(
                "/api/activities",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        type,
                        quantity,
                        date
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Could not add activity."
            );

        }


        showMessage(
            "Activity added successfully 🌱"
        );


        document.getElementById(
            "quantity"
        ).value = "";


        updatePreview();


        await refreshAll();

    }

    catch (error) {

        showMessage(error.message);

    }

}


/* =========================================================
   DASHBOARD
========================================================= */


async function loadDashboard() {

    const response =
        await fetch("/api/dashboard");


    const data =
        await response.json();


    const total =
        Number(data.total_co2 || 0);


    const weekly =
        Number(data.weekly_co2 || 0);


    const target =
        Number(data.weekly_target || 50);


    document.getElementById(
        "totalCO2"
    ).textContent =
        `${total.toFixed(2)} kg`;


    document.getElementById(
        "weeklyCO2"
    ).textContent =
        `${weekly.toFixed(2)} kg`;


    document.getElementById(
        "targetCO2"
    ).textContent =
        `${target.toFixed(2)} kg`;


    document.getElementById(
        "weekText"
    ).textContent =
        `${formatDate(data.week_start)} – ${formatDate(data.week_end)}`;


    let percent = 0;


    if (target > 0) {

        percent =
            (weekly / target) * 100;

    }


    document.getElementById(
        "progressPercent"
    ).textContent =
        `${Math.round(percent)}%`;


    document.getElementById(
        "progressBar"
    ).style.width =
        `${Math.min(percent, 100)}%`;


    document.getElementById(
        "progressText"
    ).textContent =
        `${weekly.toFixed(2)} kg used`;


    document.getElementById(
        "progressTarget"
    ).textContent =
        `${target.toFixed(2)} kg target`;


    const status =
        document.getElementById(
            "targetStatus"
        );


    if (weekly === 0) {

        status.textContent =
            "Start tracking your activities.";

    }

    else if (weekly <= target) {

        status.textContent =
            "You're currently within your weekly target. Keep going! 🌱";

    }

    else {

        status.textContent =
            "Your emissions are above your weekly target. Explore your personalized action.";

    }


    updateInsight(
        weekly,
        target
    );


    renderCategories(
        data.category_breakdown || {}
    );

}


/* =========================================================
   INSIGHT
========================================================= */


function updateInsight(
    weekly,
    target
) {

    const title =
        document.getElementById(
            "insightTitle"
        );


    const text =
        document.getElementById(
            "insightText"
        );


    if (weekly === 0) {

        title.textContent =
            "Start your climate journey";

        text.textContent =
            "Add your first activity to see your personal carbon footprint.";

        return;

    }


    if (weekly <= target * 0.5) {

        title.textContent =
            "You're making steady progress 🌱";

        text.textContent =
            "Your weekly footprint is currently below half of your target.";

    }

    else if (weekly <= target) {

        title.textContent =
            "You're on track";

        text.textContent =
            "Your current footprint is within your weekly target.";

    }

    else {

        title.textContent =
            "An opportunity to improve";

        text.textContent =
            "Your weekly footprint is above your target. Review your biggest emission source.";

    }

}


/* =========================================================
   CATEGORY BREAKDOWN
========================================================= */


function renderCategories(data) {

    const chart =
        document.getElementById(
            "categoryChart"
        );


    const entries =
        Object.entries(data);


    if (!entries.length) {

        chart.innerHTML = `
            <div class="empty-chart">
                No emissions recorded this week.
            </div>
        `;

        return;

    }


    const total =
        entries.reduce(
            (sum, [, value]) =>
                sum + Number(value),
            0
        );


    chart.innerHTML =
        entries.map(
            ([category, value]) => {

                const amount =
                    Number(value);


                const percentage =
                    total > 0
                        ? (amount / total) * 100
                        : 0;


                return `

                    <div class="category-row">

                        <div class="category-info">

                            <span>
                                ${category}
                            </span>

                            <strong>
                                ${amount.toFixed(2)} kg
                            </strong>

                        </div>

                        <div class="category-track">

                            <div
                                class="category-fill"
                                style="width:${percentage}%"
                            ></div>

                        </div>

                        <small>
                            ${percentage.toFixed(0)}%
                        </small>

                    </div>

                `;

            }
        ).join("");

}


/* =========================================================
   RECOMMENDATION
========================================================= */


async function loadRecommendation() {

    const response =
        await fetch(
            "/api/recommendation"
        );


    const data =
        await response.json();


    document.getElementById(
        "recommendationTitle"
    ).textContent =
        data.title;


    document.getElementById(
        "recommendationText"
    ).textContent =
        data.message;


    document.getElementById(
        "recommendationAction"
    ).textContent =
        data.action;


    const reduction =
        Number(
            data.potential_reduction || 0
        );


    document.getElementById(
        "recommendationReduction"
    ).textContent =
        reduction > 0
            ? `${reduction.toFixed(2)} kg CO₂`
            : "—";

}


/* =========================================================
   WHAT IF
========================================================= */


async function runWhatIf(event) {

    event.preventDefault();


    const current =
        document.getElementById(
            "whatIfCurrent"
        ).value;


    const alternative =
        document.getElementById(
            "whatIfAlternative"
        ).value;


    const quantity =
        parseFloat(
            document.getElementById(
                "whatIfQuantity"
            ).value
        );


    if (!quantity || quantity <= 0) {

        showMessage(
            "Enter a valid quantity."
        );

        return;

    }


    try {

        const response =
            await fetch(
                "/api/what-if",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        current_activity:
                            current,

                        alternative_activity:
                            alternative,

                        quantity:
                            quantity

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Could not calculate."
            );

        }


        document.getElementById(
            "whatIfCurrentCO2"
        ).textContent =
            `${Number(data.current_co2).toFixed(2)} kg`;


        document.getElementById(
            "whatIfAlternativeCO2"
        ).textContent =
            `${Number(data.alternative_co2).toFixed(2)} kg`;


        const reduction =
            Number(
                data.potential_reduction || 0
            );


        document.getElementById(
            "whatIfReduction"
        ).textContent =
            reduction > 0
                ? `${reduction.toFixed(2)} kg CO₂`
                : "No reduction";


        document.getElementById(
            "whatIfResult"
        ).classList.remove(
            "hidden"
        );

    }

    catch (error) {

        showMessage(error.message);

    }

}


/* =========================================================
   HISTORY
========================================================= */


async function loadHistory() {

    const response =
        await fetch(
            "/api/activities"
        );


    const activities =
        await response.json();


    const type =
        document.getElementById(
            "filterType"
        ).value;


    const start =
        document.getElementById(
            "filterStart"
        ).value;


    const end =
        document.getElementById(
            "filterEnd"
        ).value;


    let filtered =
        activities;


    if (type) {

        filtered =
            filtered.filter(
                item => item.type === type
            );

    }


    if (start) {

        filtered =
            filtered.filter(
                item => item.date >= start
            );

    }


    if (end) {

        filtered =
            filtered.filter(
                item => item.date <= end
            );

    }


    const body =
        document.getElementById(
            "historyBody"
        );


    if (!filtered.length) {

        body.innerHTML = `

            <tr>

                <td
                    colspan="5"
                    class="empty-table"
                >
                    No activities found.
                </td>

            </tr>

        `;

        return;

    }


    body.innerHTML =
        filtered.map(
            item => {

                const type =
                    item.type;


                return `

                    <tr>

                        <td>
                            ${formatDate(item.date)}
                        </td>

                        <td>
                            ${names[type] || type}
                        </td>

                        <td>
                            ${Number(item.quantity).toLocaleString(
                                "en-IN",
                                {
                                    maximumFractionDigits: 2
                                }
                            )}
                            ${item.unit}
                        </td>

                        <td>
                            ${categories[type] || "Other"}
                        </td>

                        <td>
                            <strong>
                                ${Number(item.co2).toFixed(2)} kg
                            </strong>
                        </td>

                    </tr>

                `;

            }
        ).join("");

}


/* =========================================================
   TARGET
========================================================= */


async function updateTarget(event) {

    event.preventDefault();


    const target =
        parseFloat(
            document.getElementById(
                "weeklyTarget"
            ).value
        );


    if (!target || target <= 0) {

        showMessage(
            "Enter a valid target."
        );

        return;

    }


    const response =
        await fetch(
            "/api/target",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    target
                })
            }
        );


    const data =
        await response.json();


    if (!response.ok) {

        showMessage(
            data.error ||
            "Could not update target."
        );

        return;

    }


    showMessage(
        "Weekly target updated 🎯"
    );


    await loadDashboard();

}


/* =========================================================
   FILTERS
========================================================= */


function clearFilters() {

    document.getElementById(
        "filterType"
    ).value = "";


    document.getElementById(
        "filterStart"
    ).value = "";


    document.getElementById(
        "filterEnd"
    ).value = "";


    loadHistory();

}


/* =========================================================
   REFRESH
========================================================= */


async function refreshAll() {

    await loadDashboard();

    await loadHistory();

    await loadRecommendation();

}


/* =========================================================
   INITIALIZATION
========================================================= */


document.addEventListener(
    "DOMContentLoaded",
    async () => {


        document.getElementById(
            "activityDate"
        ).value =
            localDate();


        document.getElementById(
            "activityType"
        ).addEventListener(
            "change",
            updateUnit
        );


        document.getElementById(
            "quantity"
        ).addEventListener(
            "input",
            updatePreview
        );


        document.getElementById(
            "activityForm"
        ).addEventListener(
            "submit",
            addActivity
        );


        document.getElementById(
            "targetForm"
        ).addEventListener(
            "submit",
            updateTarget
        );


        document.getElementById(
            "whatIfForm"
        ).addEventListener(
            "submit",
            runWhatIf
        );


        document.getElementById(
            "filterType"
        ).addEventListener(
            "change",
            loadHistory
        );


        document.getElementById(
            "filterStart"
        ).addEventListener(
            "change",
            loadHistory
        );


        document.getElementById(
            "filterEnd"
        ).addEventListener(
            "change",
            loadHistory
        );


        updateUnit();


        await refreshAll();

    }
);