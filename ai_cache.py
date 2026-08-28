import json
import os
from datetime import datetime, timedelta


CACHE_DIR = "cache"


def _get_cache_file(athlete_id=None):

    if athlete_id is None:

        return "ai_insights_cache.json"

    os.makedirs(
        CACHE_DIR,
        exist_ok=True
    )

    return os.path.join(
        CACHE_DIR,
        f"ai_insights_cache_{athlete_id}.json"
    )


def load_ai_cache(athlete_id=None):

    cache_file = _get_cache_file(
        athlete_id
    )

    if not os.path.exists(cache_file):

        return None

    try:

        with open(
            cache_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        generated_at = data.get(
            "generated_at"
        )

        if generated_at:

            try:

                created = datetime.fromisoformat(
                    generated_at
                )

                if (
                    datetime.now() - created
                    >
                    timedelta(hours=12)
                ):

                    return None

            except Exception:

                return None

        return data

    except Exception:

        return None


def save_ai_cache(
    insights,
    athlete_id=None
):

    cache_file = _get_cache_file(
        athlete_id
    )

    data = {
        "generated_at":
            datetime.now().isoformat(),

        "insights":
            insights
    }

    if athlete_id is not None:

        data["athlete_id"] = athlete_id

    with open(
        cache_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def clear_ai_cache(athlete_id=None):

    cache_file = _get_cache_file(
        athlete_id
    )

    if os.path.exists(cache_file):

        os.remove(
            cache_file
        )
