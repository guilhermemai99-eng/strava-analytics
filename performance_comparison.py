from datetime import datetime, timedelta

from database import SessionLocal
from models import Activity


def parse_date(value):

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except Exception:

        return None


def format_pace(seconds_per_km):

    if seconds_per_km is None:
        return None

    minutes = int(
        seconds_per_km // 60
    )

    seconds = int(
        round(seconds_per_km % 60)
    )

    if seconds >= 60:

        minutes += 1
        seconds -= 60

    return f"{minutes}:{seconds:02d}"


def get_period_performance(activities):

    if not activities:

        return {
            "runs": 0,
            "distance_km": 0,
            "average_pace": None,
            "best_5k_pace": None,
            "best_10k_pace": None,
            "runs_5k_or_more": 0,
            "runs_10k_or_more": 0
        }

    total_distance = 0

    total_time = 0

    best_5k = None

    best_10k = None

    runs_5k_or_more = 0

    runs_10k_or_more = 0

    for activity in activities:

        distance_m = (
            activity.distance_m or 0
        )

        moving_time = (
            activity.moving_time_s or 0
        )

        if (
            distance_m <= 0
            or moving_time <= 0
        ):

            continue

        distance_km = (
            distance_m / 1000
        )

        total_distance += distance_km

        total_time += moving_time

        # ----------------------------------------------------
        # Corridas >= 5 km
        # ----------------------------------------------------

        if distance_km >= 5:

            runs_5k_or_more += 1

            pace = (
                moving_time /
                distance_km
            )

            if (
                best_5k is None
                or pace < best_5k
            ):

                best_5k = pace

        # ----------------------------------------------------
        # Corridas >= 10 km
        # ----------------------------------------------------

        if distance_km >= 10:

            runs_10k_or_more += 1

            pace = (
                moving_time /
                distance_km
            )

            if (
                best_10k is None
                or pace < best_10k
            ):

                best_10k = pace

    average_pace = None

    if total_distance > 0:

        average_pace = (
            total_time /
            total_distance
        )

    return {

        "runs":
            len(activities),

        "distance_km":
            round(
                total_distance,
                2
            ),

        "average_pace":
            format_pace(
                average_pace
            ),

        "best_5k_pace":
            format_pace(
                best_5k
            )
            if runs_5k_or_more >= 1
            else None,

        "best_10k_pace":
            format_pace(
                best_10k
            )
            if runs_10k_or_more >= 1
            else None,

        "runs_5k_or_more":
            runs_5k_or_more,

        "runs_10k_or_more":
            runs_10k_or_more

    }


def compare_pace(
    recent_pace,
    previous_pace,
    recent_count,
    previous_count
):

    if (
        recent_pace is None
        or previous_pace is None
    ):

        return {

            "status":
                "insufficient_data",

            "improvement_percent":
                None,

            "message":
                "Dados insuficientes para comparação."

        }

    if (
        recent_count < 2
        or previous_count < 2
    ):

        return {

            "status":
                "low_confidence",

            "improvement_percent":
                None,

            "message":
                "Existem dados nos dois períodos, "
                "mas são insuficientes para uma "
                "comparação robusta."

        }

    improvement = (

        (
            previous_pace -
            recent_pace
        )
        /
        previous_pace

    ) * 100

    if improvement > 0:

        message = (
            f"Melhoria estimada de "
            f"{improvement:.1f}%."
        )

    elif improvement < 0:

        message = (
            f"Queda estimada de "
            f"{abs(improvement):.1f}%."
        )

    else:

        message = (
            "Performance praticamente estável."
        )

    return {

        "status":
            "ok",

        "improvement_percent":
            round(
                improvement,
                1
            ),

        "message":
            message

    }


def calculate_performance_comparison(
    athlete_id=None
):

    db = SessionLocal()

    try:

        # =====================================================
        # ATIVIDADES DO ATLETA
        # =====================================================

        query = (

            db.query(Activity)

            .filter(
                Activity.sport_type == "Run"
            )

            .filter(
                Activity.distance_m.isnot(None)
            )

            .filter(
                Activity.moving_time_s.isnot(None)
            )

        )

        if athlete_id is not None:

            query = query.filter(
                Activity.athlete_id == athlete_id
            )

        activities = (
            query
            .all()
        )

        dated_activities = []

        for activity in activities:

            date = parse_date(
                activity.start_date_local
            )

            if date:

                dated_activities.append(
                    (
                        date,
                        activity
                    )
                )

        if not dated_activities:

            return {

                "status":
                    "insufficient_data",

                "athlete_id":
                    athlete_id

            }

        latest_date = max(

            date

            for date, activity
            in dated_activities

        )

        recent_start = (
            latest_date -
            timedelta(days=84)
        )

        previous_start = (
            recent_start -
            timedelta(days=84)
        )

        recent_activities = [

            activity

            for date, activity
            in dated_activities

            if (
                recent_start
                <= date
                <= latest_date
            )

        ]

        previous_activities = [

            activity

            for date, activity
            in dated_activities

            if (
                previous_start
                <= date
                < recent_start
            )

        ]

        recent = get_period_performance(
            recent_activities
        )

        previous = get_period_performance(
            previous_activities
        )

        # ----------------------------------------------------
        # Comparação 5K
        # ----------------------------------------------------

        comparison_5k = compare_pace(

            pace_to_seconds(
                recent["best_5k_pace"]
            ),

            pace_to_seconds(
                previous["best_5k_pace"]
            ),

            recent["runs_5k_or_more"],

            previous["runs_5k_or_more"]

        )

        # ----------------------------------------------------
        # Comparação 10K
        # ----------------------------------------------------

        comparison_10k = compare_pace(

            pace_to_seconds(
                recent["best_10k_pace"]
            ),

            pace_to_seconds(
                previous["best_10k_pace"]
            ),

            recent["runs_10k_or_more"],

            previous["runs_10k_or_more"]

        )

        return {

            "status":
                "ok",

            "athlete_id":
                athlete_id,

            "periods": {

                "recent": {

                    "label":
                        "Últimas 12 semanas",

                    **recent

                },

                "previous": {

                    "label":
                        "12 semanas anteriores",

                    **previous

                }

            },

            "performance_comparison": {

                "5k":
                    comparison_5k,

                "10k":
                    comparison_10k

            }

        }

    finally:

        db.close()


def pace_to_seconds(pace):

    if not pace:
        return None

    try:

        minutes, seconds = pace.split(":")

        return (

            int(minutes) * 60

            +

            int(seconds)

        )

    except Exception:

        return None