# ============================================================
# WEEKLY TRAINING PLAN
# ============================================================


def calculate_weekly_plan(
    athlete_score,
    evolution_data,
    performance_comparison
):

    categories = athlete_score.get(
        "categories",
        {}
    )

    consistency = categories.get(
        "consistency",
        {}
    ).get(
        "score",
        50
    )

    volume = categories.get(
        "volume",
        {}
    ).get(
        "score",
        50
    )

    speed = categories.get(
        "speed",
        {}
    ).get(
        "score",
        50
    )

    endurance = categories.get(
        "endurance",
        {}
    ).get(
        "score",
        50
    )

    recent = (
        performance_comparison
        .get(
            "periods",
            {}
        )
        .get(
            "recent",
            {}
        )
    )

    recent_distance = (
        recent.get(
            "distance_km",
            0
        )
    )

    # ========================================================
    # VOLUME ALVO
    # ========================================================

    if recent_distance <= 60:

        weekly_km = 25

    elif recent_distance <= 100:

        weekly_km = 30

    else:

        weekly_km = 35


    # ========================================================
    # AJUSTES
    # ========================================================

    if consistency < 55:

        weekly_km = min(
            weekly_km,
            28
        )

    if volume < 60:

        weekly_km = min(
            weekly_km,
            30
        )


    # ========================================================
    # PLANO BASE
    # ========================================================

    plan = [

        {
            "day": "Monday",
            "type": "Rest",
            "distance_km": 0,
            "rpe": None,
            "focus": "Recovery"
        },

        {
            "day": "Tuesday",
            "type": "Easy Run",
            "distance_km": 6,
            "rpe": "3–4",
            "focus": "Aerobic base"
        },

        {
            "day": "Wednesday",
            "type": "Strength",
            "distance_km": 0,
            "rpe": None,
            "focus": "Strength"
        },

        {
            "day": "Thursday",
            "type": "Quality Run",
            "distance_km": 7,
            "rpe": "6",
            "focus": "Threshold"
        },

        {
            "day": "Friday",
            "type": "Rest",
            "distance_km": 0,
            "rpe": None,
            "focus": "Recovery"
        },

        {
            "day": "Saturday",
            "type": "Easy Run",
            "distance_km": 5,
            "rpe": "3–4",
            "focus": "Aerobic base"
        },

        {
            "day": "Sunday",
            "type": "Long Run",
            "distance_km": 10,
            "rpe": "4",
            "focus": "Endurance"
        }

    ]


    # ========================================================
    # CONSISTÊNCIA BAIXA
    # ========================================================

    if consistency < 55:

        plan = [

            {
                "day": "Monday",
                "type": "Rest",
                "distance_km": 0,
                "rpe": None,
                "focus": "Recovery"
            },

            {
                "day": "Tuesday",
                "type": "Easy Run",
                "distance_km": 6,
                "rpe": "3–4",
                "focus": "Consistency"
            },

            {
                "day": "Wednesday",
                "type": "Rest",
                "distance_km": 0,
                "rpe": None,
                "focus": "Recovery"
            },

            {
                "day": "Thursday",
                "type": "Easy Run",
                "distance_km": 6,
                "rpe": "3–4",
                "focus": "Aerobic base"
            },

            {
                "day": "Friday",
                "type": "Rest",
                "distance_km": 0,
                "rpe": None,
                "focus": "Recovery"
            },

            {
                "day": "Saturday",
                "type": "Easy Run",
                "distance_km": 5,
                "rpe": "3–4",
                "focus": "Consistency"
            },

            {
                "day": "Sunday",
                "type": "Long Easy Run",
                "distance_km": 10,
                "rpe": "3–4",
                "focus": "Endurance"
            }

        ]


    # ========================================================
    # RESISTÊNCIA
    # ========================================================

    if (
        endurance >= 70
        and consistency >= 60
    ):

        plan[-1]["distance_km"] = 12


    # ========================================================
    # VELOCIDADE
    # ========================================================

    if (
        speed >= 75
        and consistency >= 60
    ):

        plan[3] = {

            "day": "Thursday",

            "type":
                "Interval Run",

            "distance_km":
                8,

            "rpe":
                "7–8",

            "focus":
                "Speed"

        }


    # ========================================================
    # DISTÂNCIA TOTAL
    # ========================================================

    running_km = sum(

        session["distance_km"]

        for session in plan

    )


    # ========================================================
    # FOCO
    # ========================================================

    if consistency < 55:

        focus = "Consistency"

    elif endurance < 60:

        focus = "Endurance"

    elif speed >= 75:

        focus = "Speed"

    elif volume < 60:

        focus = "Aerobic volume"

    else:

        focus = "Base"


    # ========================================================
    # RESULTADO
    # ========================================================

    return {

        "status":
            "ok",

        "weekly_distance_km":
            running_km,

        "target_distance_km":
            weekly_km,

        "focus":
            focus,

        "sessions":
            plan

    }