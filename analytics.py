from sqlalchemy import func

from database import SessionLocal
from models import Activity


# ============================================================
# HELPER — FILTRO POR ATLETA
# ============================================================

def _query_activities(db, athlete_id=None):
    """
    Cria uma query de atividades.

    Se athlete_id for fornecido:
        devolve apenas atividades desse atleta.

    Se athlete_id for None:
        mantém compatibilidade com o sistema antigo.
    """

    query = db.query(Activity)

    if athlete_id is not None:
        query = query.filter(
            Activity.athlete_id == athlete_id
        )

    return query


# ============================================================
# SUMMARY
# ============================================================

def get_summary(athlete_id=None):

    db = SessionLocal()

    try:

        query = _query_activities(
            db,
            athlete_id
        )

        total_activities = (
            query.count()
        )

        total_distance = (
            query.with_entities(
                func.sum(
                    Activity.distance_m
                )
            ).scalar()
            or 0
        )

        total_time = (
            query.with_entities(
                func.sum(
                    Activity.moving_time_s
                )
            ).scalar()
            or 0
        )

        total_elevation = (
            query.with_entities(
                func.sum(
                    Activity.elevation_gain_m
                )
            ).scalar()
            or 0
        )

        running_activities = (
            query
            .filter(
                Activity.sport_type == "Run"
            )
            .all()
        )

        running_count = len(
            running_activities
        )

        running_distance = sum(
            activity.distance_m or 0
            for activity
            in running_activities
        )

        longest_run = max(
            (
                activity.distance_m or 0
                for activity
                in running_activities
            ),
            default=0
        )

        average_run_distance = (
            running_distance /
            running_count
            if running_count > 0
            else 0
        )

        return {

            "total_activities":
                total_activities,

            "total_distance_km":
                round(
                    total_distance / 1000,
                    2
                ),

            "total_running_km":
                round(
                    running_distance / 1000,
                    2
                ),

            "running_activities":
                running_count,

            "average_run_distance_km":
                round(
                    average_run_distance / 1000,
                    2
                ),

            "longest_run_km":
                round(
                    longest_run / 1000,
                    2
                ),

            "total_training_hours":
                round(
                    total_time / 3600,
                    2
                ),

            "total_elevation_m":
                round(
                    total_elevation,
                    1
                )
        }

    finally:

        db.close()


# ============================================================
# WEEKLY
# ============================================================

def get_weekly(athlete_id=None):

    db = SessionLocal()

    try:

        query = _query_activities(
            db,
            athlete_id
        )

        activities = (
            query
            .filter(
                Activity.start_date_local.isnot(None)
            )
            .order_by(
                Activity.start_date_local
            )
            .all()
        )

    finally:

        db.close()

    weeks = {}

    from datetime import datetime

    for activity in activities:

        date_text = (
            activity.start_date_local[:10]
        )

        try:

            activity_date = (
                datetime.strptime(
                    date_text,
                    "%Y-%m-%d"
                ).date()
            )

        except Exception:

            continue

        iso = (
            activity_date.isocalendar()
        )

        week_key = (
            f"{iso.year}-W{iso.week:02d}"
        )

        if week_key not in weeks:

            weeks[week_key] = {

                "week":
                    week_key,

                "activities":
                    0,

                "running_km":
                    0,

                "training_hours":
                    0,

                "elevation_m":
                    0
            }

        weeks[week_key][
            "activities"
        ] += 1

        weeks[week_key][
            "training_hours"
        ] += (
            (activity.moving_time_s or 0)
            / 3600
        )

        weeks[week_key][
            "elevation_m"
        ] += (
            activity.elevation_gain_m or 0
        )

        if activity.sport_type == "Run":

            weeks[week_key][
                "running_km"
            ] += (
                (activity.distance_m or 0)
                / 1000
            )

    result = []

    for week in weeks.values():

        week["running_km"] = round(
            week["running_km"],
            2
        )

        week["training_hours"] = round(
            week["training_hours"],
            2
        )

        week["elevation_m"] = round(
            week["elevation_m"],
            1
        )

        result.append(
            week
        )

    return result