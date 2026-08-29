import sys
import time

import requests

import athlete  # noqa: F401  # ensure athletes table is registered for FK
from database import SessionLocal
from models import Activity
from strava_tokens import (
    StravaTokenError,
    get_valid_access_token,
)
from ai_cache import clear_ai_cache
from pr_cache import clear_cache


STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
STRAVA_ACTIVITY_URL = "https://www.strava.com/api/v3/activities/{activity_id}"

# Cap detail fetches per sync so photo enrichment cannot explode rate limits.
MAX_PHOTO_DETAIL_FETCHES = 15


def _map_polyline(item: dict) -> str | None:
    raw = (item.get("map") or {}).get("summary_polyline")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _extract_primary_photo_url(detail: dict) -> tuple[str | None, int]:
    photos = detail.get("photos") or {}
    count = photos.get("count")
    if count is None:
        count = detail.get("total_photo_count") or 0
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0

    primary = photos.get("primary") or {}
    urls = primary.get("urls") or {}
    if not isinstance(urls, dict) or not urls:
        return None, count

    # Prefer larger sizes for feed cards.
    preferred = ["600", "1200", "1000", "800", "300", "100"]
    for key in preferred:
        if key in urls and urls[key]:
            return str(urls[key]), count

    # Fallback: first non-empty URL value.
    for value in urls.values():
        if value:
            return str(value), count
    return None, count


def _fetch_activity_detail(access_token: str, strava_id: int) -> dict | None:
    try:
        response = requests.get(
            STRAVA_ACTIVITY_URL.format(activity_id=strava_id),
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"photo detail network error for {strava_id}: {exc!r}")
        return None

    if response.status_code != 200:
        print(
            f"photo detail failed for {strava_id}: "
            f"{response.status_code}"
        )
        return None

    try:
        return response.json()
    except ValueError:
        return None


def _maybe_enrich_photo(
    access_token: str,
    activity: Activity,
    list_item: dict,
    remaining_fetches: list[int],
) -> None:
    """Fetch primary photo URL when Strava hints media exists.

    Mutates remaining_fetches[0] as a simple mutable counter.
    Never raises — activity stays valid without a photo.
    """

    if activity.photo_url:
        return
    if remaining_fetches[0] <= 0:
        return

    hint = list_item.get("total_photo_count")
    try:
        hint_count = int(hint) if hint is not None else 0
    except (TypeError, ValueError):
        hint_count = 0

    # total_photo_count is unreliable on some Strava responses; still try
    # a limited number of detail fetches for recent activities missing photos
    # only when the list payload suggests media.
    if hint_count <= 0:
        photos_summary = list_item.get("photos") or {}
        try:
            hint_count = int(photos_summary.get("count") or 0)
        except (TypeError, ValueError):
            hint_count = 0

    if hint_count <= 0:
        return

    remaining_fetches[0] -= 1
    detail = _fetch_activity_detail(access_token, activity.strava_id)
    if not detail:
        return

    url, count = _extract_primary_photo_url(detail)
    if url:
        activity.photo_url = url
    activity.photo_count = count or hint_count
    # Be polite to Strava when enriching multiple activities.
    time.sleep(0.15)


def _activity_from_list_item(athlete_id: int, item: dict) -> Activity:
    start_lat = start_lng = end_lat = end_lng = None
    if item.get("start_latlng"):
        start_lat = item["start_latlng"][0]
        start_lng = item["start_latlng"][1]
    if item.get("end_latlng"):
        end_lat = item["end_latlng"][0]
        end_lng = item["end_latlng"][1]

    return Activity(
        athlete_id=athlete_id,
        strava_id=item["id"],
        name=item.get("name"),
        sport_type=item.get("sport_type"),
        distance_m=item.get("distance"),
        moving_time_s=item.get("moving_time"),
        elapsed_time_s=item.get("elapsed_time"),
        elevation_gain_m=item.get("total_elevation_gain"),
        elev_high=item.get("elev_high"),
        elev_low=item.get("elev_low"),
        average_speed_m_s=item.get("average_speed"),
        max_speed_m_s=item.get("max_speed"),
        start_date=item.get("start_date"),
        start_date_local=item.get("start_date_local"),
        timezone=item.get("timezone"),
        device_name=item.get("device_name"),
        kudos_count=item.get("kudos_count"),
        achievement_count=item.get("achievement_count"),
        average_temp=item.get("average_temp"),
        has_heartrate=item.get("has_heartrate"),
        start_lat=start_lat,
        start_lng=start_lng,
        end_lat=end_lat,
        end_lng=end_lng,
        summary_polyline=_map_polyline(item),
        photo_url=None,
        photo_count=None,
    )


def sync_strava_activities(athlete_id):
    if athlete_id is None:
        raise StravaTokenError("athlete_id é obrigatório.")

    db = SessionLocal()
    total_imported = 0
    total_updated = 0
    photos_enriched = 0
    page = 1
    per_page = 100
    photo_budget = [MAX_PHOTO_DETAIL_FETCHES]
    pending_photo_rows: list[tuple[Activity, dict]] = []

    try:
        access_token = get_valid_access_token(db, athlete_id)

        while True:
            print(f"\nA obter página {page}...")

            response = requests.get(
                STRAVA_ACTIVITIES_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"per_page": per_page, "page": page},
                timeout=15,
            )
            print("STATUS:", response.status_code)

            if response.status_code == 401:
                access_token = get_valid_access_token(
                    db,
                    athlete_id,
                    force_refresh=True,
                )
                response = requests.get(
                    STRAVA_ACTIVITIES_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"per_page": per_page, "page": page},
                    timeout=15,
                )
                print("STATUS:", response.status_code)

            if response.status_code != 200:
                raise StravaTokenError(
                    "Erro ao obter atividades do Strava."
                )

            activities = response.json()
            print(
                f"Atividades recebidas nesta página: {len(activities)}"
            )
            if not activities:
                break

            for item in activities:
                existing = (
                    db.query(Activity)
                    .filter(Activity.strava_id == item["id"])
                    .one_or_none()
                )

                if existing:
                    changed = False
                    if existing.athlete_id is None:
                        existing.athlete_id = athlete_id
                        changed = True

                    polyline = _map_polyline(item)
                    if polyline and not existing.summary_polyline:
                        existing.summary_polyline = polyline
                        changed = True

                    if changed:
                        total_updated += 1

                    if not existing.photo_url:
                        pending_photo_rows.append((existing, item))
                    continue

                activity = _activity_from_list_item(athlete_id, item)
                db.add(activity)
                total_imported += 1
                pending_photo_rows.append((activity, item))
                print("Importada:", item.get("name"))

            db.commit()
            page += 1

        # Enrich photos after flush so new rows have PKs; failures are soft.
        for activity, item in pending_photo_rows:
            before = activity.photo_url
            _maybe_enrich_photo(access_token, activity, item, photo_budget)
            if activity.photo_url and activity.photo_url != before:
                photos_enriched += 1

        if photos_enriched or total_updated:
            db.commit()

        print()
        print("==============================")
        print("SINCRONIZAÇÃO CONCLUÍDA")
        print("==============================")
        print(f"Novas atividades importadas: {total_imported}")
        print(f"Atividades atualizadas (media): {total_updated}")
        print(f"Fotos enriquecidas: {photos_enriched}")

        clear_ai_cache(athlete_id)
        clear_cache(athlete_id)

        return {
            "athlete_id": athlete_id,
            "imported": total_imported,
            "updated": total_updated,
            "photos_enriched": photos_enriched,
            "status": "ok",
        }

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python import_strava.py <athlete_id>")
        sys.exit(1)

    try:
        cli_athlete_id = int(sys.argv[1])
    except ValueError:
        print("athlete_id inválido.")
        sys.exit(1)

    try:
        result = sync_strava_activities(cli_athlete_id)
        print(result)
    except StravaTokenError as error:
        print(error)
        sys.exit(1)
