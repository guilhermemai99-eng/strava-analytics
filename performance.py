from database import SessionLocal
from models import Activity

from datetime import datetime, timedelta


def get_running_performance():

    db = SessionLocal()

    activities = (
        db.query(Activity)
        .filter(Activity.sport_type == "Run")
        .filter(Activity.start_date_local.isnot(None))
        .order_by(Activity.start_date_local)
        .all()
    )

    db.close()

    if not activities:
        return {
            "message": "Não existem corridas."
        }

    weeks = {}

    for activity in activities:

        date_text = activity.start_date_local[:10]

        activity_date = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).date()

        monday = (
            activity_date
            - timedelta(days=activity_date.weekday())
        )

        week_key = monday.isoformat()

        if week_key not in weeks:

            weeks[week_key] = {
                "week_start": monday,
                "km": 0,
                "runs": 0
            }

        weeks[week_key]["km"] += (
            activity.distance_m or 0
        ) / 1000

        weeks[week_key]["runs"] += 1


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

        data = weeks.get(
            week_key,
            {
                "week_start": week_date,
                "km": 0,
                "runs": 0
            }
        )

        last_8.append(data)


    average_km = (
        sum(w["km"] for w in last_8)
        / 8
    )

    average_runs = (
        sum(w["runs"] for w in last_8)
        / 8
    )


    best_week = max(
        last_8,
        key=lambda x: x["km"]
    )


    first_half = last_8[:4]

    second_half = last_8[4:]


    first_average = (
        sum(w["km"] for w in first_half)
        / 4
    )

    second_average = (
        sum(w["km"] for w in second_half)
        / 4
    )


    if first_average == 0:

        trend = "Sem histórico suficiente"


    elif second_average > first_average * 1.10:

        trend = "Aumento significativo"


    elif second_average < first_average * 0.90:

        trend = "Diminuição significativa"


    else:

        trend = "Estável"


    return {

        "periodo": "Últimas 8 semanas consecutivas",

        "media_km_semana": round(
            average_km,
            2
        ),

        "media_corridas_semana": round(
            average_runs,
            2
        ),

        "melhor_semana": {

            "week": best_week[
                "week_start"
            ].isoformat(),

            "km": round(
                best_week["km"],
                2
            ),

            "corridas": best_week["runs"]

        },

        "tendencia_volume": trend,

        "semanas": [

            {
                "week": w[
                    "week_start"
                ].isoformat(),

                "km": round(
                    w["km"],
                    2
                ),

                "corridas": w["runs"]

            }

            for w in last_8

        ]

    }