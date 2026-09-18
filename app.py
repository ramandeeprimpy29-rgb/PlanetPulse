from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

app = Flask(__name__)

DB_PATH = Path(__file__).parent / "planetpulse.db"


# ============================================================
# CARBON EMISSION FACTORS
# ============================================================

FACTORS = {
    "car": 0.20,            # kg CO2 / km
    "bus": 0.08,            # kg CO2 / km
    "flight": 0.25,         # kg CO2 / km
    "electricity": 0.80,    # kg CO2 / kWh
    "veg_meal": 0.50,       # kg CO2 / meal
    "nonveg_meal": 2.00     # kg CO2 / meal
}


UNITS = {
    "car": "km",
    "bus": "km",
    "flight": "km",
    "electricity": "kWh",
    "veg_meal": "meal",
    "nonveg_meal": "meal"
}


ACTIVITY_NAMES = {
    "car": "Car Travel",
    "bus": "Bus Travel",
    "flight": "Flight",
    "electricity": "Electricity",
    "veg_meal": "Vegetarian Meal",
    "nonveg_meal": "Non-Vegetarian Meal"
}


CATEGORIES = {
    "car": "Transport",
    "bus": "Transport",
    "flight": "Transport",
    "electricity": "Energy",
    "veg_meal": "Food",
    "nonveg_meal": "Food"
}


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            co2 REAL NOT NULL,
            activity_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    existing = conn.execute(
        "SELECT value FROM settings WHERE key = 'weekly_target'"
    ).fetchone()

    if existing is None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("weekly_target", "50")
        )

    conn.commit()
    conn.close()


# ============================================================
# HELPERS
# ============================================================

def get_week_range(offset=0):

    today = date.today()

    monday = today - timedelta(days=today.weekday())

    monday = monday + timedelta(days=offset * 7)

    sunday = monday + timedelta(days=6)

    return monday, sunday


def get_weekly_target():

    conn = get_db()

    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'weekly_target'"
    ).fetchone()

    conn.close()

    if row:
        return float(row["value"])

    return 50.0


def calculate_co2(activity_type, quantity):

    if activity_type not in FACTORS:
        raise ValueError("Invalid activity type.")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    return round(quantity * FACTORS[activity_type], 2)


# ============================================================
# MAIN PAGE
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# ACTIVITIES
# ============================================================

@app.route("/api/activities", methods=["GET", "POST"])
def activities():

    if request.method == "POST":

        data = request.get_json(silent=True) or {}

        activity_type = data.get("type")
        quantity = data.get("quantity")
        activity_date = data.get("date") or date.today().isoformat()

        if activity_type not in FACTORS:
            return jsonify({
                "error": "Invalid activity type."
            }), 400

        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            return jsonify({
                "error": "Quantity must be a number."
            }), 400

        if quantity <= 0:
            return jsonify({
                "error": "Quantity must be greater than zero."
            }), 400

        try:
            datetime.strptime(activity_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "error": "Invalid date."
            }), 400

        co2 = calculate_co2(activity_type, quantity)

        conn = get_db()

        cursor = conn.execute("""
            INSERT INTO activities
            (activity_type, quantity, unit, co2, activity_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            activity_type,
            quantity,
            UNITS[activity_type],
            co2,
            activity_date
        ))

        conn.commit()

        activity_id = cursor.lastrowid

        conn.close()

        return jsonify({
            "success": True,
            "id": activity_id,
            "activity_type": activity_type,
            "quantity": quantity,
            "unit": UNITS[activity_type],
            "co2": co2,
            "date": activity_date
        }), 201


    # GET
    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            activity_type,
            quantity,
            unit,
            co2,
            activity_date
        FROM activities
        ORDER BY activity_date DESC, id DESC
    """).fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append({
            "id": row["id"],
            "type": row["activity_type"],
            "activity_type": row["activity_type"],
            "name": ACTIVITY_NAMES.get(
                row["activity_type"],
                row["activity_type"]
            ),
            "quantity": row["quantity"],
            "unit": row["unit"],
            "co2": row["co2"],
            "category": CATEGORIES.get(
                row["activity_type"],
                "Other"
            ),
            "date": row["activity_date"]
        })

    return jsonify(result)


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/api/dashboard")
def dashboard():

    conn = get_db()

    total_row = conn.execute("""
        SELECT COALESCE(SUM(co2), 0) AS total
        FROM activities
    """).fetchone()

    week_start, week_end = get_week_range()

    weekly_row = conn.execute("""
        SELECT COALESCE(SUM(co2), 0) AS total
        FROM activities
        WHERE activity_date BETWEEN ? AND ?
    """, (
        week_start.isoformat(),
        week_end.isoformat()
    )).fetchone()


    category_rows = conn.execute("""
        SELECT
            activity_type,
            SUM(co2) AS total
        FROM activities
        WHERE activity_date BETWEEN ? AND ?
        GROUP BY activity_type
    """, (
        week_start.isoformat(),
        week_end.isoformat()
    )).fetchall()


    conn.close()


    total_co2 = float(total_row["total"] or 0)

    weekly_co2 = float(weekly_row["total"] or 0)

    target = get_weekly_target()


    category_totals = {
        "Transport": 0,
        "Energy": 0,
        "Food": 0
    }


    for row in category_rows:

        activity_type = row["activity_type"]

        category = CATEGORIES.get(
            activity_type,
            "Other"
        )

        if category not in category_totals:
            category_totals[category] = 0

        category_totals[category] += float(
            row["total"] or 0
        )


    return jsonify({
        "total_co2": round(total_co2, 2),
        "weekly_co2": round(weekly_co2, 2),
        "weekly_target": round(target, 2),
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "category_breakdown": {
            key: round(value, 2)
            for key, value in category_totals.items()
            if value > 0
        }
    })


# ============================================================
# TARGET
# ============================================================

@app.route("/api/target", methods=["POST"])
def update_target():

    data = request.get_json(silent=True) or {}

    try:
        target = float(data.get("target"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Target must be a number."
        }), 400

    if target <= 0:
        return jsonify({
            "error": "Target must be greater than zero."
        }), 400


    conn = get_db()

    conn.execute("""
        INSERT INTO settings (key, value)
        VALUES ('weekly_target', ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (str(target),))

    conn.commit()
    conn.close()


    return jsonify({
        "success": True,
        "target": target
    })


# ============================================================
# PERSONALIZED RECOMMENDATION
# ============================================================

@app.route("/api/recommendation")
def recommendation():

    week_start, week_end = get_week_range()

    conn = get_db()

    rows = conn.execute("""
        SELECT
            activity_type,
            SUM(quantity) AS quantity,
            SUM(co2) AS co2
        FROM activities
        WHERE activity_date BETWEEN ? AND ?
        GROUP BY activity_type
        ORDER BY co2 DESC
    """, (
        week_start.isoformat(),
        week_end.isoformat()
    )).fetchall()

    conn.close()


    if not rows:

        return jsonify({
            "title": "Start your climate journey",
            "message": "Add your first activity and PlanetPulse will generate a personalized action.",
            "action": "Log an activity to unlock your recommendation.",
            "potential_reduction": 0
        })


    biggest = rows[0]

    activity = biggest["activity_type"]

    quantity = float(biggest["quantity"])

    co2 = float(biggest["co2"])


    if activity == "car":

        replace_quantity = min(quantity, 10)

        reduction = calculate_co2(
            "car",
            replace_quantity
        ) - calculate_co2(
            "bus",
            replace_quantity
        )

        return jsonify({
            "title": "Reduce your transport footprint 🚗",
            "message": f"Car travel is your largest recorded source this week.",
            "action": f"Replace {replace_quantity:g} km of car travel with bus travel.",
            "potential_reduction": round(max(reduction, 0), 2)
        })


    if activity == "nonveg_meal":

        replace_quantity = min(quantity, 2)

        reduction = calculate_co2(
            "nonveg_meal",
            replace_quantity
        ) - calculate_co2(
            "veg_meal",
            replace_quantity
        )

        return jsonify({
            "title": "Try a lower-impact meal 🥗",
            "message": "Non-vegetarian meals are your largest recorded source this week.",
            "action": f"Replace {replace_quantity:g} non-vegetarian meal(s) with vegetarian meal(s).",
            "potential_reduction": round(max(reduction, 0), 2)
        })


    if activity == "electricity":

        reduction = calculate_co2(
            "electricity",
            min(quantity, 5)
        )

        return jsonify({
            "title": "Reduce electricity usage ⚡",
            "message": "Electricity is your largest recorded source this week.",
            "action": "Try reducing electricity consumption by 5 kWh where practical.",
            "potential_reduction": round(reduction, 2)
        })


    if activity == "flight":

        reduction = calculate_co2(
            "flight",
            min(quantity, 100)
        )

        return jsonify({
            "title": "Consider lower-carbon travel ✈️",
            "message": "Flight activity is your largest recorded source this week.",
            "action": "Where practical, replace part of a flight journey with a lower-emission travel option.",
            "potential_reduction": round(reduction, 2)
        })


    if activity == "bus":

        return jsonify({
            "title": "Great transport choice 🚌",
            "message": "Bus travel is currently your largest recorded activity source.",
            "action": "Keep using shared transport when practical.",
            "potential_reduction": 0
        })


    if activity == "veg_meal":

        return jsonify({
            "title": "Keep building sustainable food habits 🥗",
            "message": "Vegetarian meals are currently your largest recorded activity source.",
            "action": "Continue tracking your meals and maintain sustainable choices.",
            "potential_reduction": 0
        })


    return jsonify({
        "title": "Keep tracking 🌱",
        "message": "Continue recording your daily activities.",
        "action": "Use your activity history to identify your biggest opportunities.",
        "potential_reduction": 0
    })


# ============================================================
# WHAT-IF SIMULATOR
# ============================================================

@app.route("/api/what-if", methods=["POST"])
def what_if():

    data = request.get_json(silent=True) or {}

    current = data.get("current_activity")

    alternative = data.get("alternative_activity")

    quantity = data.get("quantity")


    if current not in FACTORS or alternative not in FACTORS:

        return jsonify({
            "error": "Invalid activity selected."
        }), 400


    try:
        quantity = float(quantity)
    except (TypeError, ValueError):

        return jsonify({
            "error": "Quantity must be a number."
        }), 400


    if quantity <= 0:

        return jsonify({
            "error": "Quantity must be greater than zero."
        }), 400


    current_co2 = calculate_co2(
        current,
        quantity
    )

    alternative_co2 = calculate_co2(
        alternative,
        quantity
    )


    reduction = round(
        current_co2 - alternative_co2,
        2
    )


    percentage = 0

    if current_co2 > 0:

        percentage = round(
            (reduction / current_co2) * 100,
            1
        )


    return jsonify({
        "current_co2": current_co2,
        "alternative_co2": alternative_co2,
        "potential_reduction": max(reduction, 0),
        "percentage_reduction": max(percentage, 0)
    })


# ============================================================
# WEEKLY COMPARISON
# ============================================================

@app.route("/api/weekly-comparison")
def weekly_comparison():

    current_start, current_end = get_week_range(0)

    previous_start, previous_end = get_week_range(-1)


    conn = get_db()


    current_row = conn.execute("""
        SELECT COALESCE(SUM(co2), 0) AS total
        FROM activities
        WHERE activity_date BETWEEN ? AND ?
    """, (
        current_start.isoformat(),
        current_end.isoformat()
    )).fetchone()


    previous_row = conn.execute("""
        SELECT COALESCE(SUM(co2), 0) AS total
        FROM activities
        WHERE activity_date BETWEEN ? AND ?
    """, (
        previous_start.isoformat(),
        previous_end.isoformat()
    )).fetchone()


    conn.close()


    current = float(current_row["total"] or 0)

    previous = float(previous_row["total"] or 0)


    difference = round(
        current - previous,
        2
    )


    if previous > 0:

        percentage = round(
            (difference / previous) * 100,
            1
        )

    elif current > 0:

        percentage = 100.0

    else:

        percentage = 0.0


    if current == 0 and previous == 0:

        message = "Start tracking to compare your weekly footprint."

    elif previous == 0:

        message = "This is your first recorded week. Keep tracking to build a comparison."

    elif difference < 0:

        message = (
            f"Your footprint is {abs(difference):.2f} kg CO₂ "
            f"lower than last week."
        )

    elif difference > 0:

        message = (
            f"Your footprint is {difference:.2f} kg CO₂ "
            f"higher than last week."
        )

    else:

        message = "Your footprint is unchanged from last week."


    return jsonify({
        "current_week": round(current, 2),
        "previous_week": round(previous, 2),
        "difference": difference,
        "percentage_change": percentage,
        "message": message
    })


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )