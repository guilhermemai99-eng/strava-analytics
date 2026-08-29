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
STRAVA_ACTIVITY_PHOTOS_URL = (
    "https://www.strava.com/api/v3/activities/{activity_id}/photos"
)
STRAVA_ACTIVITY_STREAMS_URL = (
    "https://www.strava.com/api/v3/activities/{activity_id}/streams"
)

# Cap detail/photo/stream fetches per sync so enrichment cannot explode rate limits.
MAX_MEDIA_DETAIL_FETCHES = 80

# Prefer largest Strava CDN sizes for Feed cards.
_PHOTO_SIZE_PREF = ("2048", "1200", "1000", "800", "600", "300", "100")


def _map_polyline(item: dict | None) -> str | None:
    if not item:
        return None
    map_obj = item.get("map") or {}
    if not isinstance(map_obj, dict):
        return None
    # Prefer full-resolution polyline from detail payloads.
    for key in ("polyline", "summary_polyline"):
        raw = map_obj.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def encode_polyline(coords: list[tuple[float, float]]) -> str:
    """Google encoded polyline (precision 5) from [[lat, lng], ...]."""
    result: list[str] = []
    prev_lat = 0
    prev_lng = 0

    def _write(value: int) -> None:
        value = ~(value << 1) if value < 0 else (value << 1)
        while value >= 0x20:
            result.append(chr((0x20 | (value & 0x1F)) + 63))
            value >>= 5
        result.append(chr(value + 63))

    for lat, lng in coords:
        ilat = int(round(lat * 1e5))
        ilng = int(round(lng * 1e5))
        _write(ilat - prev_lat)
        _write(ilng - prev_lng)
        prev_lat = ilat
        prev_lng = ilng

    return "".join(result)


def _downsample_latlng(
    points: list[tuple[float, float]],
    max_points: int = 200,
) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    sampled = points[::step]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled


def _polyline_from_latlng_stream(payload: dict | list | None) -> str | None:
    """Build encoded polyline from Strava latlng stream."""
    data = None
    if isinstance(payload, dict):
        stream = payload.get("latlng") or {}
        if isinstance(stream, dict):
            data = stream.get("data")
    elif isinstance(payload, list):
        for stream in payload:
            if isinstance(stream, dict) and stream.get("type") == "latlng":
                data = stream.get("data")
                break

    if not isinstance(data, list) or len(data) < 2:
        return None

    coords: list[tuple[float, float]] = []
    for point in data:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            lat = float(point[0])
            lng = float(point[1])
        except (TypeError, ValueError):
            continue
        coords.append((lat, lng))

    if len(coords) < 2:
        return None
    return encode_polyline(_downsample_latlng(coords))


def _best_url_from_urls_map(urls: dict) -> str | None:
    if not isinstance(urls, dict) or not urls:
        return None
    for key in _PHOTO_SIZE_PREF:
        value = urls.get(key)
        if value:
            return str(value)
    # Numeric keys descending (largest first).
    numeric_keys = []
    for key in urls.keys():
        try:
            numeric_keys.append(int(key))
        except (TypeError, ValueError):
            continue
    for key in sorted(numeric_keys, reverse=True):
        value = urls.get(str(key)) or urls.get(key)
        if value:
            return str(value)
    for value in urls.values():
        if value:
            return str(value)
    return None


def _extract_primary_photo_url(detail: dict) -> tuple[str | None, int]:
    """From activity detail payload (photos.primary.urls). Often max 600."""
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
    return _best_url_from_urls_map(urls), count


def _extract_photo_url_from_photos_list(photos: list) -> tuple[str | None, int]:
    """From GET /activities/{id}/photos?size=2048&photo_sources=true."""
    if not isinstance(photos, list) or not photos:
        return None, 0
    # Prefer native Strava photos (source=1) over Instagram (source=2).
    ordered = sorted(
        photos,
        key=lambda p: (
            0 if (p or {}).get("source") == 1 else 1,
            0 if (p or {}).get("default_photo") else 1,
        ),
    )
    best = None
    for photo in ordered:
        if not isinstance(photo, dict):
            continue
        url = _best_url_from_urls_map(photo.get("urls") or {})
        if url:
            best = url
            break
    return best, len(photos)


def is_low_res_photo_url(url: str | None) -> bool:
    """Heuristic: Strava 100/600 CDN variants look soft on Feed cards."""
    if not url:
        return True
    u = url.lower()
    soft_markers = (
        "-100.jpg",
        "-100.jpeg",
        "-100.png",
        "-100.webp",
        "-600.jpg",
        "-600.jpeg",
        "-600.png",
        "-600.webp",
        "/100-",
        "/600-",
        "_100.",
        "_600.",
        "100x100",
        "600x600",
    )
    return any(m in u for m in soft_markers)


def _fetch_json(
    url: str,
    access_token: str,
    *,
    params: dict | None = None,
) -> dict | list | None:
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"strava media network error: {exc!r} url={url}")
        return None

    if response.status_code != 200:
        print(f"strava media failed: {response.status_code} url={url}")
        return None

    try:
        return response.json()
    except ValueError:
        return None


def _fetch_activity_detail(access_token: str, strava_id: int) -> dict | None:
    data = _fetch_json(
        STRAVA_ACTIVITY_URL.format(activity_id=strava_id),
        access_token,
    )
    return data if isinstance(data, dict) else None


def _fetch_activity_photos_hq(access_token: str, strava_id: int) -> list | None:
    data = _fetch_json(
        STRAVA_ACTIVITY_PHOTOS_URL.format(activity_id=strava_id),
        access_token,
        params={"size": 2048, "photo_sources": "true"},
    )
    return data if isinstance(data, list) else None


def _fetch_activity_latlng_stream(
    access_token: str,
    strava_id: int,
) -> dict | list | None:
    data = _fetch_json(
        STRAVA_ACTIVITY_STREAMS_URL.format(activity_id=strava_id),
        access_token,
        params={"keys": "latlng", "key_by_type": "true"},
    )
    if isinstance(data, (dict, list)):
        return data
    return None


def _list_photo_hint(list_item: dict) -> int:
    hint = list_item.get("total_photo_count")
    try:
        hint_count = int(hint) if hint is not None else 0
    except (TypeError, ValueError):
        hint_count = 0
    if hint_count > 0:
        return hint_count
    photos_summary = list_item.get("photos") or {}
    try:
        return int(photos_summary.get("count") or 0)
    except (TypeError, ValueError):
        return 0


def _maybe_enrich_media(
    access_token: str,
    activity: Activity,
    list_item: dict,
    remaining_fetches: list[int],
) -> dict:
    """Backfill polyline + upgrade photo URL. Soft-fail; never raises."""
    changed = {"map": False, "photo": False}

    # 1) Map from list payload (free).
    if not activity.summary_polyline:
        poly = _map_polyline(list_item)
        if poly:
            activity.summary_polyline = poly
            changed["map"] = True

    needs_map = not activity.summary_polyline
    hint_count = _list_photo_hint(list_item)
    needs_photo = hint_count > 0 and (
        not activity.photo_url or is_low_res_photo_url(activity.photo_url)
    )

    if not needs_map and not needs_photo:
        return changed
    if remaining_fetches[0] <= 0:
        return changed

    # 2) Detail fetch: map + photo summary fallback.
    remaining_fetches[0] -= 1
    detail = _fetch_activity_detail(access_token, activity.strava_id)
    time.sleep(0.08)

    if detail:
        if needs_map:
            poly = _map_polyline(detail)
            if poly:
                activity.summary_polyline = poly
                changed["map"] = True
                needs_map = False
        else:
            # Upgrade summary → full polyline when detail has higher-res route.
            poly = _map_polyline(detail)
            if poly and poly != activity.summary_polyline:
                activity.summary_polyline = poly
                changed["map"] = True

        if needs_photo:
            url, count = _extract_primary_photo_url(detail)
            if count:
                activity.photo_count = count
            # Detail primary is often ≤600 — keep as interim, then upgrade.
            if url and (not activity.photo_url or is_low_res_photo_url(activity.photo_url)):
                if url != activity.photo_url:
                    activity.photo_url = url
                    changed["photo"] = True

    # 3) Streams latlng → polyline when map still missing (owner can see private maps).
    if needs_map and remaining_fetches[0] > 0:
        remaining_fetches[0] -= 1
        streams = _fetch_activity_latlng_stream(access_token, activity.strava_id)
        time.sleep(0.08)
        poly = _polyline_from_latlng_stream(streams)
        if poly:
            activity.summary_polyline = poly
            changed["map"] = True
            needs_map = False

    # 4) Dedicated photos endpoint for 2048 when media is expected.
    if needs_photo and remaining_fetches[0] > 0:
        remaining_fetches[0] -= 1
        photos = _fetch_activity_photos_hq(access_token, activity.strava_id)
        time.sleep(0.08)
        if photos is not None:
            url, count = _extract_photo_url_from_photos_list(photos)
            if count:
                activity.photo_count = max(int(activity.photo_count or 0), count)
            if url and url != activity.photo_url:
                activity.photo_url = url
                changed["photo"] = True

    if hint_count and not activity.photo_count:
        activity.photo_count = hint_count

    return changed


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
    maps_enriched = 0
    page = 1
    per_page = 100
    media_budget = [MAX_MEDIA_DETAIL_FETCHES]
    pending_media_rows: list[tuple[Activity, dict]] = []

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
                        maps_enriched += 1

                    if changed:
                        total_updated += 1

                    needs_photo = _list_photo_hint(item) > 0 and (
                        not existing.photo_url
                        or is_low_res_photo_url(existing.photo_url)
                    )
                    needs_map = not existing.summary_polyline
                    if needs_photo or needs_map:
                        pending_media_rows.append((existing, item))
                    continue

                activity = _activity_from_list_item(athlete_id, item)
                db.add(activity)
                total_imported += 1
                pending_media_rows.append((activity, item))
                print("Importada:", item.get("name"))

            db.commit()
            page += 1

        # Enrich media after flush so new rows have PKs; failures are soft.
        # Prefer map backfill first so Feed routes appear even when photo budget runs out.
        pending_media_rows.sort(
            key=lambda pair: (
                0 if not (pair[0].summary_polyline or "").strip() else 1,
                0 if _list_photo_hint(pair[1]) > 0 else 1,
            )
        )
        for activity, item in pending_media_rows:
            before_photo = activity.photo_url
            before_map = activity.summary_polyline
            result = _maybe_enrich_media(
                access_token, activity, item, media_budget
            )
            if activity.photo_url and activity.photo_url != before_photo:
                photos_enriched += 1
            elif result.get("photo"):
                photos_enriched += 1
            if activity.summary_polyline and activity.summary_polyline != before_map:
                maps_enriched += 1

        if photos_enriched or maps_enriched or total_updated:
            db.commit()

        print()
        print("==============================")
        print("SINCRONIZAÇÃO CONCLUÍDA")
        print("==============================")
        print(f"Novas atividades importadas: {total_imported}")
        print(f"Atividades atualizadas (media): {total_updated}")
        print(f"Fotos enriquecidas: {photos_enriched}")
        print(f"Mapas enriquecidos: {maps_enriched}")

        clear_ai_cache(athlete_id)
        clear_cache(athlete_id)

        return {
            "athlete_id": athlete_id,
            "imported": total_imported,
            "updated": total_updated,
            "photos_enriched": photos_enriched,
            "maps_enriched": maps_enriched,
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
        print("athlete_id deve ser um inteiro.")
        sys.exit(1)

    result = sync_strava_activities(cli_athlete_id)
    print(result)
