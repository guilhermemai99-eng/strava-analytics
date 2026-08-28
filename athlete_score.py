# ============================================================
# ATHLETE SCORE
# ============================================================


def clamp(
    value,
    minimum=0,
    maximum=100
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


# ============================================================
# TENDÊNCIA
# ============================================================

def get_trend(score):

    if score >= 75:

        return "up"

    if score <= 55:

        return "down"

    return "stable"


# ============================================================
# ATHLETE SCORE
# ============================================================

def calculate_athlete_score(
    evolution_data,
    performance_comparison,
    running_performance,
    athlete_id=None
):


    # ========================================================
    # DADOS DE PERFORMANCE
    # ========================================================

    comparison = (

        performance_comparison.get(

            "performance_comparison",

            {}

        )

    )


    five_k = comparison.get(

        "5k",

        {}

    )


    ten_k = comparison.get(

        "10k",

        {}

    )


    periods = (

        performance_comparison.get(

            "periods",

            {}

        )

    )


    recent = periods.get(

        "recent",

        {}

    )


    previous = periods.get(

        "previous",

        {}

    )


    # ========================================================
    # PERFORMANCE
    # ========================================================

    performance_score = 70

    performance_confidence = "medium"


    if five_k.get("status") == "ok":

        improvement = (

            five_k.get(

                "improvement_percent"

            )

            or 0

        )


        performance_score += (

            improvement * 2

        )


    if ten_k.get("status") == "ok":

        improvement = (

            ten_k.get(

                "improvement_percent"

            )

            or 0

        )


        performance_score += (

            improvement * 0.5

        )


    performance_score = round(

        clamp(

            performance_score

        )

    )


    # ========================================================
    # SPEED
    # ========================================================

    speed_score = 70

    speed_confidence = "low"


    if five_k.get("status") == "ok":

        improvement = (

            five_k.get(

                "improvement_percent"

            )

            or 0

        )


        speed_score += (

            improvement * 4

        )


        recent_5k_runs = (

            recent.get(

                "runs_5k_or_more",

                0

            )

        )


        previous_5k_runs = (

            previous.get(

                "runs_5k_or_more",

                0

            )

        )


        # ----------------------------------------------------
        # Confiança
        # ----------------------------------------------------

        if (

            recent_5k_runs >= 5

            and

            previous_5k_runs >= 5

        ):

            speed_confidence = "high"


        elif (

            recent_5k_runs >= 2

            and

            previous_5k_runs >= 2

        ):

            speed_confidence = "medium"


        else:

            speed_confidence = "low"


    else:

        speed_confidence = "low"


    speed_score = round(

        clamp(

            speed_score

        )

    )


    # ========================================================
    # CONSISTÊNCIA
    # ========================================================

    consistency_score = 70

    consistency_confidence = "high"


    frequency_change = (

        evolution_data

        .get(

            "changes",

            {}

        )

        .get(

            "frequency_percent"

        )

    )


    if frequency_change is not None:

        consistency_score += (

            frequency_change * 0.8

        )


    recent_runs = (

        recent.get(

            "runs",

            0

        )

    )


    previous_runs = (

        previous.get(

            "runs",

            0

        )

    )


    if recent_runs < 3:

        consistency_confidence = "medium"


    if recent_runs < 2:

        consistency_confidence = "low"


    consistency_score = round(

        clamp(

            consistency_score

        )

    )


    # ========================================================
    # VOLUME
    # ========================================================

    volume_score = 70

    volume_confidence = "high"


    volume_change = (

        evolution_data

        .get(

            "changes",

            {}

        )

        .get(

            "volume_percent"

        )

    )


    if volume_change is not None:

        volume_score += (

            volume_change * 0.5

        )


    recent_distance = (

        recent.get(

            "distance_km",

            0

        )

    )


    previous_distance = (

        previous.get(

            "distance_km",

            0

        )

    )


    if (

        recent_distance <= 0

        or

        previous_distance <= 0

    ):

        volume_confidence = "low"


    volume_score = round(

        clamp(

            volume_score

        )

    )


    # ========================================================
    # RESISTÊNCIA
    # ========================================================

    endurance_score = 70

    endurance_confidence = "low"


    recent_10k_runs = (

        recent.get(

            "runs_10k_or_more",

            0

        )

    )


    previous_10k_runs = (

        previous.get(

            "runs_10k_or_more",

            0

        )

    )


    # --------------------------------------------------------
    # Confiança alta
    # --------------------------------------------------------

    if (

        ten_k.get("status") == "ok"

        and

        recent_10k_runs >= 10

        and

        previous_10k_runs >= 10

    ):

        improvement = (

            ten_k.get(

                "improvement_percent"

            )

            or 0

        )


        endurance_score += (

            improvement * 1.5

        )


        endurance_confidence = "high"


    # --------------------------------------------------------
    # Confiança média
    # --------------------------------------------------------

    elif (

        ten_k.get("status") == "ok"

        and

        recent_10k_runs >= 8

        and

        previous_10k_runs >= 8

    ):

        improvement = (

            ten_k.get(

                "improvement_percent"

            )

            or 0

        )


        endurance_score += (

            improvement * 1.5

        )


        endurance_confidence = "medium"


    # --------------------------------------------------------
    # Dados insuficientes
    # --------------------------------------------------------

    else:

        endurance_score = 70

        endurance_confidence = "low"


    endurance_score = round(

        clamp(

            endurance_score

        )

    )


    # ========================================================
    # OVERALL
    # ========================================================

    overall = round(

        (

            performance_score * 0.25

            +

            consistency_score * 0.20

            +

            volume_score * 0.15

            +

            speed_score * 0.20

            +

            endurance_score * 0.20

        )

    )


    # ========================================================
    # RESULTADO
    # ========================================================

    return {

        "status":

            "ok",

	"athlete_id":
    athlete_id,


        "overall":

            overall,


        "categories": {


            "performance": {

                "score":

                    performance_score,

                "trend":

                    get_trend(

                        performance_score

                    ),

                "confidence":

                    performance_confidence

            },


            "consistency": {

                "score":

                    consistency_score,

                "trend":

                    get_trend(

                        consistency_score

                    ),

                "confidence":

                    consistency_confidence

            },


            "volume": {

                "score":

                    volume_score,

                "trend":

                    get_trend(

                        volume_score

                    ),

                "confidence":

                    volume_confidence

            },


            "speed": {

                "score":

                    speed_score,

                "trend":

                    get_trend(

                        speed_score

                    ),

                "confidence":

                    speed_confidence

            },


            "endurance": {

                "score":

                    endurance_score,

                "trend":

                    get_trend(

                        endurance_score

                    ),

                "confidence":

                    endurance_confidence

            }

        }

    }