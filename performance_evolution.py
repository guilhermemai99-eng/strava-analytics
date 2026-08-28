def calculate_evolution(weekly_data):

    if not weekly_data:
        return {
            "status": "insufficient_data",
            "message": "Não existem dados semanais."
        }

    # Ordenar cronologicamente
    weeks = sorted(
        weekly_data,
        key=lambda x: x.get("week", "")
    )

    # Precisamos de pelo menos 8 semanas
    if len(weeks) < 8:
        return {
            "status": "insufficient_data",
            "message": (
                "São necessárias pelo menos "
                "8 semanas de dados."
            )
        }

    # Últimas 4 semanas
    recent = weeks[-4:]

    # 4 semanas anteriores
    previous = weeks[-8:-4]

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    recent_km = sum(
        week.get("running_km", 0) or 0
        for week in recent
    )

    previous_km = sum(
        week.get("running_km", 0) or 0
        for week in previous
    )

    # --------------------------------------------------------
    # FREQUÊNCIA
    # --------------------------------------------------------

    recent_runs = sum(
        week.get("activities", 0) or 0
        for week in recent
    )

    previous_runs = sum(
        week.get("activities", 0) or 0
        for week in previous
    )

    # --------------------------------------------------------
    # HORAS
    # --------------------------------------------------------

    recent_hours = sum(
        week.get("training_hours", 0) or 0
        for week in recent
    )

    previous_hours = sum(
        week.get("training_hours", 0) or 0
        for week in previous
    )

    # --------------------------------------------------------
    # ELEVAÇÃO
    # --------------------------------------------------------

    recent_elevation = sum(
        week.get("elevation_m", 0) or 0
        for week in recent
    )

    previous_elevation = sum(
        week.get("elevation_m", 0) or 0
        for week in previous
    )

    # --------------------------------------------------------
    # FUNÇÃO PARA CALCULAR VARIAÇÃO
    # --------------------------------------------------------

    def percentage_change(
        current,
        previous_value
    ):

        if previous_value <= 0:
            return None

        return round(
            (
                (
                    current -
                    previous_value
                )
                /
                previous_value
            ) * 100,
            1
        )

    # --------------------------------------------------------
    # ALTERAÇÕES
    # --------------------------------------------------------

    volume_change = percentage_change(
        recent_km,
        previous_km
    )

    frequency_change = percentage_change(
        recent_runs,
        previous_runs
    )

    hours_change = percentage_change(
        recent_hours,
        previous_hours
    )

    elevation_change = percentage_change(
        recent_elevation,
        previous_elevation
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    return {

        "status": "ok",

        "recent_period": {

            "weeks": 4,

            "distance_km": round(
                recent_km,
                2
            ),

            "runs": recent_runs,

            "training_hours": round(
                recent_hours,
                2
            ),

            "elevation_m": round(
                recent_elevation,
                1
            )

        },

        "previous_period": {

            "weeks": 4,

            "distance_km": round(
                previous_km,
                2
            ),

            "runs": previous_runs,

            "training_hours": round(
                previous_hours,
                2
            ),

            "elevation_m": round(
                previous_elevation,
                1
            )

        },

        "changes": {

            "volume_percent":
                volume_change,

            "frequency_percent":
                frequency_change,

            "training_hours_percent":
                hours_change,

            "elevation_percent":
                elevation_change

        }

    }