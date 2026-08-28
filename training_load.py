from database import SessionLocal
from models import Activity
from datetime import datetime, timedelta


def get_training_load(athlete_id=None):

    db = SessionLocal()

    try:
        query = (
            db.query(Activity)
            .filter(Activity.start_date_local.isnot(None))
        )

        if athlete_id is not None:
            query = query.filter(
                Activity.athlete_id == athlete_id
            )

        activities = (
            query
            .order_by(Activity.start_date_local)
            .all()
        )

    finally:
        db.close()

    if not activities:
        return {
            "athlete_id": athlete_id,
            "current_load": 0,
            "baseline_load": 0,
            "average_load": 0,
            "change_percent": None,
            "status": "Sem dados",
            "weeks": []
        }

    weeks = {}

    for activity in activities:
        try:
            activity_date = datetime.strptime(
                activity.start_date_local[:10],
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            continue

        monday = activity_date - timedelta(
            days=activity_date.weekday()
        )

        week_key = monday.isoformat()

        if week_key not in weeks:
            weeks[week_key] = {
                "week": week_key,
                "km": 0,
                "hours": 0,
                "elevation": 0,
                "activities": 0
            }

        weeks[week_key]["km"] += (
            (activity.distance_m or 0) / 1000
        )

        weeks[week_key]["hours"] += (
            (activity.moving_time_s or 0) / 3600
        )

        weeks[week_key]["elevation"] += (
            activity.elevation_gain_m or 0
        )

        weeks[week_key]["activities"] += 1

    if not weeks:
        return {
            "athlete_id": athlete_id,
            "current_load": 0,
            "baseline_load": 0,
            "average_load": 0,
            "change_percent": None,
            "status": "Sem dados",
            "weeks": []
        }

    latest_week = max(weeks.keys())

    latest_monday = datetime.strptime(
        latest_week,
        "%Y-%m-%d"
    ).date()

    last_8 = []

    for i in range(7, -1, -1):

        week_date = (
            latest_monday
            - timedelta(days=i * 7)
        )

        week_key = week_date.isoformat()

        week = weeks.get(
            week_key,
            {
                "week": week_key,
                "km": 0,
                "hours": 0,
                "elevation": 0,
                "activities": 0
            }
        )

        week["load"] = round(
            week["km"]
            + (week["hours"] * 5)
            + (week["elevation"] / 100),
            2
        )

        last_8.append(week)

    current = last_8[-1]["load"]

    previous_4 = last_8[-5:-1]

    active_previous = [
        week["load"]
        for week in previous_4
        if week["activities"] > 0
    ]

    if active_previous:
        baseline = round(
            sum(active_previous) / len(active_previous),
            2
        )
    else:
        baseline = 0

    if baseline > 0:
        change_percent = round(
            ((current - baseline) / baseline) * 100,
            1
        )
    else:
        change_percent = None

    if current == 0:
        status = "Muito baixa"
    elif baseline == 0:
        status = "Sem histórico"
    elif change_percent <= -30:
        status = "Baixa"
    elif change_percent < 15:
        status = "Normal"
    elif change_percent < 30:
        status = "Elevada"
    else:
        status = "Muito elevada"

    all_active = [
        week["load"]
        for week in last_8
        if week["activities"] > 0
    ]

    if all_active:
        average_load = round(
            sum(all_active) / len(all_active),
            2
        )
    else:
        average_load = 0

    return {
        "athlete_id": athlete_id,
        "current_load": round(current, 2),
        "baseline_load": baseline,
        "average_load": average_load,
        "change_percent": change_percent,
        "status": status,
        "weeks": [
            {
                "week": week["week"],
                "km": round(week["km"], 2),
                "hours": round(week["hours"], 2),
                "elevation": round(week["elevation"], 1),
                "activities": week["activities"],
                "load": week["load"]
            }
            for week in last_8
        ]
    }
