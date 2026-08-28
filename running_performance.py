import requests

from database import SessionLocal
from models import Activity
from pr_cache import load_cache, save_cache
from strava_tokens import get_valid_access_token


STRAVA_STREAM_URL = (
    "https://www.strava.com/api/v3/activities/{}/streams"
)


# =========================================================
# FORMATAÇÃO
# =========================================================

def format_pace(seconds_per_km):

    if seconds_per_km is None:
        return None

    minutes = int(seconds_per_km // 60)

    seconds = int(
        round(seconds_per_km % 60)
    )

    if seconds >= 60:
        minutes += 1
        seconds -= 60

    return f"{minutes}:{seconds:02d}"


def format_duration(total_seconds):

    if total_seconds is None:
        return None

    total_seconds = int(
        round(total_seconds)
    )

    hours = total_seconds // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    seconds = total_seconds % 60

    if hours > 0:

        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes}:"
        f"{seconds:02d}"
    )


# =========================================================
# AUTENTICAÇÃO
# =========================================================

def get_access_token(db, athlete_id):

    return get_valid_access_token(
        db,
        athlete_id
    )


# =========================================================
# STRAVA STREAMS
# =========================================================

def get_streams(
    activity_id,
    access_token
):

    url = STRAVA_STREAM_URL.format(
        activity_id
    )

    response = requests.get(

        url,

        headers={
            "Authorization":
                f"Bearer {access_token}"
        },

        params={
            "keys":
                "time,distance",

            "key_by_type":
                "true"
        },

        timeout=15
    )

    if response.status_code != 200:

        print(
            f"Erro nos streams "
            f"{activity_id}: "
            f"HTTP {response.status_code}"
        )

        return None

    return response.json()


# =========================================================
# CALCULAR SEGMENTO
# =========================================================

def calculate_best_segment(
    streams,
    target_distance_m
):

    if not streams:
        return None

    distance_stream = streams.get(
        "distance"
    )

    time_stream = streams.get(
        "time"
    )

    if not distance_stream:
        return None

    if not time_stream:
        return None

    distances = distance_stream.get(
        "data",
        []
    )

    times = time_stream.get(
        "data",
        []
    )

    if not distances or not times:
        return None

    if len(distances) != len(times):
        return None

    best_time = None

    best_start_distance = None

    best_end_distance = None

    start_index = 0

    for end_index in range(
        len(distances)
    ):

        current_distance = (
            distances[end_index]
        )

        while (

            start_index < end_index

            and

            current_distance -
            distances[start_index]
            >= target_distance_m

        ):

            segment_distance = (
                current_distance -
                distances[start_index]
            )

            start_time = (
                times[start_index]
            )

            end_time = (
                times[end_index]
            )

            segment_time = (
                end_time -
                start_time
            )

            if segment_distance >= target_distance_m:

                ratio = (
                    target_distance_m /
                    segment_distance
                )

                exact_time = (
                    segment_time *
                    ratio
                )

                if (

                    best_time is None

                    or

                    exact_time <
                    best_time

                ):

                    best_time = exact_time

                    best_start_distance = (
                        distances[start_index]
                    )

                    best_end_distance = (
                        distances[start_index]
                        +
                        target_distance_m
                    )

            start_index += 1

    if best_time is None:
        return None

    pace_seconds = (
        best_time /
        (target_distance_m / 1000)
    )

    return {

        "distance_km":
            round(
                target_distance_m / 1000,
                2
            ),

        "time_seconds":
            round(
                best_time,
                1
            ),

        "pace":
            format_pace(
                pace_seconds
            ),

        "start_distance_m":
            round(
                best_start_distance,
                1
            ),

        "end_distance_m":
            round(
                best_end_distance,
                1
            )

    }


# =========================================================
# PRs REAIS 5K / 10K
# =========================================================

def get_real_prs(
    activities,
    access_token
):

    best_5k = None

    best_10k = None


    # -----------------------------------------------------
    # CANDIDATAS 5K
    # -----------------------------------------------------

    candidates_5k = [

        activity

        for activity in activities

        if (

            activity.distance_m

            and

            activity.distance_m >= 5000

        )

    ]


    # -----------------------------------------------------
    # CANDIDATAS 10K
    # -----------------------------------------------------

    candidates_10k = [

        activity

        for activity in activities

        if (

            activity.distance_m

            and

            activity.distance_m >= 10000

        )

    ]


    # -----------------------------------------------------
    # 5K
    # -----------------------------------------------------

    for index, activity in enumerate(
        candidates_5k,
        start=1
    ):

        print(
            f"5K "
            f"[{index}/{len(candidates_5k)}]: "
            f"{activity.name}"
        )

        streams = get_streams(

            activity.strava_id,

            access_token

        )

        result = calculate_best_segment(

            streams,

            5000

        )

        if result is None:
            continue

        result["activity_id"] = (
            activity.strava_id
        )

        result["name"] = (
            activity.name
        )

        result["date"] = (
            activity.start_date_local
        )

        if (

            best_5k is None

            or

            result["time_seconds"]
            <
            best_5k["time_seconds"]

        ):

            best_5k = result


    # -----------------------------------------------------
    # 10K
    # -----------------------------------------------------

    for index, activity in enumerate(
        candidates_10k,
        start=1
    ):

        print(
            f"10K "
            f"[{index}/{len(candidates_10k)}]: "
            f"{activity.name}"
        )

        streams = get_streams(

            activity.strava_id,

            access_token

        )

        result = calculate_best_segment(

            streams,

            10000

        )

        if result is None:
            continue

        result["activity_id"] = (
            activity.strava_id
        )

        result["name"] = (
            activity.name
        )

        result["date"] = (
            activity.start_date_local
        )

        if (

            best_10k is None

            or

            result["time_seconds"]
            <
            best_10k["time_seconds"]

        ):

            best_10k = result


    return {

        "best_5k":
            best_5k,

        "best_10k":
            best_10k

    }


# =========================================================
# MEIA MARATONA / MARATONA
# =========================================================

def get_best_race(
    activities,
    minimum_distance_km,
    maximum_distance_km
):

    candidates = []


    for activity in activities:

        if not activity.distance_m:
            continue

        if not activity.moving_time_s:
            continue

        distance_km = (
            activity.distance_m / 1000
        )


        if (

            distance_km >=
            minimum_distance_km

            and

            distance_km <=
            maximum_distance_km

        ):

            candidates.append(
                activity
            )


    if not candidates:
        return None


    # Para meia/maratona usamos o tempo
    # total da atividade, porque são provas
    # completas e não segmentos internos.

    best = min(

        candidates,

        key=lambda activity:
            activity.moving_time_s

    )


    distance_km = (
        best.distance_m / 1000
    )


    pace_seconds = (
        best.moving_time_s /
        distance_km
    )


    return {

        "activity_id":
            best.strava_id,

        "name":
            best.name,

        "distance_km":
            round(
                distance_km,
                2
            ),

        "time_seconds":
            best.moving_time_s,

        "time":
            format_duration(
                best.moving_time_s
            ),

        "pace":
            format_pace(
                pace_seconds
            ),

        "date":
            best.start_date_local

    }


# =========================================================
# PERFORMANCE PRINCIPAL
# =========================================================

def get_running_performance(athlete_id=None):

    # -----------------------------------------------------
    # CACHE
    # -----------------------------------------------------

    cached = load_cache(
        athlete_id
    )


    # -----------------------------------------------------
    # BASE DE DADOS
    # -----------------------------------------------------

    db = SessionLocal()


    try:

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

            .order_by(
                Activity.start_date_local
            )

            .all()

        )


        if not activities:

            result = {

                "total_runs": 0,

                "total_km": 0,

                "average_distance_km": 0,

                "average_pace": None,

                "best_5k": None,

                "best_10k": None,

                "best_half_marathon": None,

                "best_marathon": None,

                "real_prs": {

                    "best_5k": None,

                    "best_10k": None

                }

            }

            save_cache(
                result,
                athlete_id
            )

            return result


        # -------------------------------------------------
        # SE EXISTE CACHE
        # -------------------------------------------------

        if cached:

            # O cache já tem 5K/10K.
            # Só verificamos se faltam
            # meia maratona ou maratona.

            needs_update = (

                not cached.get(
                    "best_half_marathon"
                )

                or

                not cached.get(
                    "best_marathon"
                )

            )


            if not needs_update:

                print(
                    "Running performance: "
                    "dados carregados do cache."
                )

                return cached


            print(
                "Running performance: "
                "a atualizar meia maratona "
                "e maratona..."
            )


            best_half_marathon = (
                get_best_race(

                    activities,

                    20.5,

                    23.0

                )
            )


            best_marathon = (
                get_best_race(

                    activities,

                    42.0,

                    45.0

                )
            )


            cached[
                "best_half_marathon"
            ] = best_half_marathon


            cached[
                "best_marathon"
            ] = best_marathon


            save_cache(
                cached,
                athlete_id
            )


            print(
                "Cache atualizado."
            )


            return cached


        # -------------------------------------------------
        # SEM CACHE
        # -------------------------------------------------

        print(
            "Running performance: "
            "a calcular..."
        )


        # -------------------------------------------------
        # DISTÂNCIA TOTAL
        # -------------------------------------------------

        total_distance_m = sum(

            activity.distance_m or 0

            for activity in activities

        )


        total_km = (
            total_distance_m / 1000
        )


        # -------------------------------------------------
        # TEMPO TOTAL
        # -------------------------------------------------

        total_time = sum(

            activity.moving_time_s or 0

            for activity in activities

        )


        # -------------------------------------------------
        # MÉDIAS
        # -------------------------------------------------

        average_distance_km = (

            total_km /
            len(activities)

        )


        average_pace_seconds = (

            total_time /
            total_km

            if total_km > 0

            else None

        )


        # -------------------------------------------------
        # TOKEN
        # -------------------------------------------------

        access_token = get_access_token(
            db,
            athlete_id
        )


        # -------------------------------------------------
        # PRs 5K / 10K
        # -------------------------------------------------

        real_prs = get_real_prs(

            activities,

            access_token

        )


        # -------------------------------------------------
        # MEIA MARATONA
        # -------------------------------------------------

        best_half_marathon = (
            get_best_race(

                activities,

                20.5,

                23.0

            )
        )


        # -------------------------------------------------
        # MARATONA
        # -------------------------------------------------

        best_marathon = (
            get_best_race(

                activities,

                42.0,

                45.0

            )
        )


        # -------------------------------------------------
        # RESULTADO
        # -------------------------------------------------

        result = {

            "total_runs":
                len(activities),

            "total_km":
                round(
                    total_km,
                    2
                ),

            "average_distance_km":
                round(
                    average_distance_km,
                    2
                ),

            "average_pace":
                format_pace(
                    average_pace_seconds
                ),

            "best_5k":
                real_prs[
                    "best_5k"
                ],

            "best_10k":
                real_prs[
                    "best_10k"
                ],

            "best_half_marathon":
                best_half_marathon,

            "best_marathon":
                best_marathon,

            "real_prs":
                real_prs

        }


        # -------------------------------------------------
        # CACHE
        # -------------------------------------------------

        save_cache(
            result,
            athlete_id
        )


        print(
            "Running performance: "
            "cache guardado."
        )


        return result


    finally:

        db.close()