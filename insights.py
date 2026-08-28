from database import SessionLocal
from models import Activity


def get_insights(athlete_id=None):

    db = SessionLocal()

    query = (
        db.query(Activity)
        .filter(Activity.sport_type == "Run")
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

    db.close()

    if not activities:
        return {
            "insights": []
        }

    insights = []

    # --------------------------------------------------
    # VOLUME TOTAL
    # --------------------------------------------------

    total_km = sum(
        (a.distance_m or 0) / 1000
        for a in activities
    )

    insights.append({
        "type": "volume",
        "title": "Volume acumulado",
        "message": (
            f"Já percorreste {total_km:.1f} km "
            f"em {len(activities)} corridas registadas."
        )
    })


    # --------------------------------------------------
    # LONGEST RUN
    # --------------------------------------------------

    longest = max(
        activities,
        key=lambda a: a.distance_m or 0
    )

    longest_km = (
        longest.distance_m or 0
    ) / 1000

    insights.append({
        "type": "long_run",
        "title": "Maior corrida",
        "message": (
            f"A tua maior corrida registada "
            f"foi de {longest_km:.2f} km."
        )
    })


    # --------------------------------------------------
    # MÉDIA DE DISTÂNCIA
    # --------------------------------------------------

    average_km = (
        total_km / len(activities)
    )

    insights.append({
        "type": "average",
        "title": "Distância média",
        "message": (
            f"A tua corrida média tem "
            f"{average_km:.2f} km."
        )
    })


    # --------------------------------------------------
    # CORRIDAS LONGAS
    # --------------------------------------------------

    long_runs = [
        a for a in activities
        if (a.distance_m or 0) >= 15000
    ]

    insights.append({
        "type": "long_runs",
        "title": "Corridas longas",
        "message": (
            f"Tens {len(long_runs)} corridas "
            f"com pelo menos 15 km."
        )
    })


    # --------------------------------------------------
    # CONSISTÊNCIA
    # --------------------------------------------------

    dates = set()

    for activity in activities:

        date = activity.start_date_local[:10]

        dates.add(date)


    insights.append({
        "type": "consistency",
        "title": "Dias de corrida",
        "message": (
            f"Registaste corrida em "
            f"{len(dates)} dias diferentes."
        )
    })


    return {
        "insights": insights
    }