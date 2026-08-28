import sys

import requests

from database import SessionLocal
from models import Activity
from strava_tokens import (
    StravaTokenError,
    get_valid_access_token
)


def sync_strava_activities(athlete_id):

    if athlete_id is None:

        raise StravaTokenError(
            "athlete_id é obrigatório."
        )


    db = SessionLocal()

    total_imported = 0

    page = 1
    per_page = 100


    try:

        access_token = get_valid_access_token(
            db,
            athlete_id
        )


        while True:

            print(
                f"\nA obter página {page}..."
            )

            response = requests.get(

                "https://www.strava.com/api/v3/athlete/activities",

                headers={
                    "Authorization":
                        f"Bearer {access_token}"
                },

                params={
                    "per_page":
                        per_page,
                    "page":
                        page
                },

                timeout=15

            )

            print(
                "STATUS:",
                response.status_code
            )

            if response.status_code == 401:

                access_token = get_valid_access_token(
                    db,
                    athlete_id,
                    force_refresh=True
                )

                response = requests.get(

                    "https://www.strava.com/api/v3/athlete/activities",

                    headers={
                        "Authorization":
                            f"Bearer {access_token}"
                    },

                    params={
                        "per_page":
                            per_page,
                        "page":
                            page
                    },

                    timeout=15

                )

                print(
                    "STATUS:",
                    response.status_code
                )


            if response.status_code != 200:

                raise StravaTokenError(
                    "Erro ao obter atividades do Strava."
                )


            activities = response.json()

            print(
                f"Atividades recebidas nesta página: "
                f"{len(activities)}"
            )

            if not activities:
                break


            for item in activities:

                existing = (

                    db.query(Activity)
                    .filter(
                        Activity.strava_id
                        ==
                        item["id"]
                    )
                    .one_or_none()

                )

                if existing:

                    if existing.athlete_id is None:

                        existing.athlete_id = (
                            athlete_id
                        )

                    continue


                start_lat = None
                start_lng = None
                end_lat = None
                end_lng = None


                if item.get("start_latlng"):

                    start_lat = item["start_latlng"][0]
                    start_lng = item["start_latlng"][1]


                if item.get("end_latlng"):

                    end_lat = item["end_latlng"][0]
                    end_lng = item["end_latlng"][1]


                activity = Activity(

                    athlete_id=
                        athlete_id,

                    strava_id=
                        item["id"],

                    name=
                        item.get("name"),

                    sport_type=
                        item.get("sport_type"),

                    distance_m=
                        item.get("distance"),

                    moving_time_s=
                        item.get("moving_time"),

                    elapsed_time_s=
                        item.get("elapsed_time"),

                    elevation_gain_m=
                        item.get(
                            "total_elevation_gain"
                        ),

                    elev_high=
                        item.get("elev_high"),

                    elev_low=
                        item.get("elev_low"),

                    average_speed_m_s=
                        item.get(
                            "average_speed"
                        ),

                    max_speed_m_s=
                        item.get(
                            "max_speed"
                        ),

                    start_date=
                        item.get(
                            "start_date"
                        ),

                    start_date_local=
                        item.get(
                            "start_date_local"
                        ),

                    timezone=
                        item.get(
                            "timezone"
                        ),

                    device_name=
                        item.get(
                            "device_name"
                        ),

                    kudos_count=
                        item.get(
                            "kudos_count"
                        ),

                    achievement_count=
                        item.get(
                            "achievement_count"
                        ),

                    average_temp=
                        item.get(
                            "average_temp"
                        ),

                    has_heartrate=
                        item.get(
                            "has_heartrate"
                        ),

                    start_lat=
                        start_lat,

                    start_lng=
                        start_lng,

                    end_lat=
                        end_lat,

                    end_lng=
                        end_lng

                )


                db.add(activity)

                total_imported += 1

                print(
                    "Importada:",
                    item["name"]
                )


            db.commit()

            page += 1


        print()
        print("==============================")
        print("SINCRONIZAÇÃO CONCLUÍDA")
        print("==============================")
        print(
            f"Novas atividades importadas: "
            f"{total_imported}"
        )


        return {

            "athlete_id":
                athlete_id,

            "imported":
                total_imported,

            "status":
                "ok"

        }


    finally:

        db.close()


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            "Uso: python import_strava.py <athlete_id>"
        )

        sys.exit(1)


    try:

        cli_athlete_id = int(
            sys.argv[1]
        )

    except ValueError:

        print(
            "athlete_id inválido."
        )

        sys.exit(1)


    try:

        result = sync_strava_activities(
            cli_athlete_id
        )

        print(result)

    except StravaTokenError as error:

        print(error)

        sys.exit(1)
