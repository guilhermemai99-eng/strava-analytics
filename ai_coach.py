# ============================================================
# AI RUNNING COACH
# ============================================================


def get_recommendation(
    athlete_score,
    evolution_data,
    performance_comparison
):

    overall = athlete_score.get(
        "overall",
        50
    )

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

    endurance = categories.get(
        "endurance",
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


    # ========================================================
    # DECISÃO
    # ========================================================

    # Prioridade 1 — pouca consistência
    if consistency < 55:

        return {

            "status": "ok",

            "session": {

                "type":
                    "Easy Run",

                "distance_km":
                    6,

                "rpe":
                    "3–4",

                "duration":
                    "35–45 min"

            },

            "objective":
                "Recuperar consistência " \
                "sem adicionar stress excessivo.",

            "reason":
                "A consistência é atualmente " \
                "um dos principais pontos a melhorar.",

            "priority":
                "Consistency"

        }


    # ========================================================
    # Prioridade 2 — volume baixo
    # ========================================================

    if volume < 60:

        return {

            "status": "ok",

            "session": {

                "type":
                    "Easy Run",

                "distance_km":
                    8,

                "rpe":
                    "3–4",

                "duration":
                    "45–55 min"

            },

            "objective":
                "Aumentar gradualmente o volume " \
                "aeróbio.",

            "reason":
                "O volume recente está abaixo " \
                "do histórico.",

            "priority":
                "Volume"

        }


    # ========================================================
    # Prioridade 3 — resistência
    # ========================================================

    if endurance < 60:

        return {

            "status": "ok",

            "session": {

                "type":
                    "Long Easy Run",

                "distance_km":
                    12,

                "rpe":
                    "3–4",

                "duration":
                    "65–80 min"

            },

            "objective":
                "Desenvolver resistência aeróbia.",

            "reason":
                "A resistência necessita de " \
                "mais estímulo consistente.",

            "priority":
                "Endurance"

        }


    # ========================================================
    # Prioridade 4 — velocidade
    # ========================================================

    if speed >= 75:

        return {

            "status": "ok",

            "session": {

                "type":
                    "Tempo Run",

                "distance_km":
                    8,

                "rpe":
                    "6–7",

                "duration":
                    "45–55 min"

            },

            "objective":
                "Desenvolver capacidade de " \
                "sustentar ritmos elevados.",

            "reason":
                "A velocidade está suficientemente " \
                "estável para introduzir intensidade.",

            "priority":
                "Speed"

        }


    # ========================================================
    # DEFAULT
    # ========================================================

    return {

        "status": "ok",

        "session": {

            "type":
                "Easy Run",

            "distance_km":
                8,

            "rpe":
                "3–4",

            "duration":
                "45–55 min"

        },

        "objective":
            "Manter a base aeróbia " \
            "e consolidar a consistência.",

        "reason":
            "O estado atual não justifica " \
            "um estímulo de intensidade elevada.",

        "priority":
            "Base"

    }