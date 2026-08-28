import json
import os
from datetime import datetime


CACHE_DIR = "cache"


def _get_cache_file(athlete_id=None):

    # ---------------------------------------------------------
    # COMPATIBILIDADE
    # ---------------------------------------------------------
    # Sem athlete_id, mantém o comportamento antigo.
    # Isto evita partir chamadas antigas durante a migração.

    if athlete_id is None:

        return "running_pr_cache.json"

    # ---------------------------------------------------------
    # CACHE POR ATLETA
    # ---------------------------------------------------------

    os.makedirs(
        CACHE_DIR,
        exist_ok=True
    )

    return os.path.join(
        CACHE_DIR,
        f"running_pr_cache_{athlete_id}.json"
    )


def load_cache(athlete_id=None):

    cache_file = _get_cache_file(
        athlete_id
    )

    if not os.path.exists(
        cache_file
    ):

        return None

    try:

        with open(
            cache_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return None


def save_cache(
    data,
    athlete_id=None
):

    cache_file = _get_cache_file(
        athlete_id
    )

    # Não alterar o objeto original
    # recebido pela função.
    data_to_save = dict(data)

    data_to_save["cached_at"] = (
        datetime.now().isoformat()
    )

    if athlete_id is not None:

        data_to_save["athlete_id"] = (
            athlete_id
        )

    with open(
        cache_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data_to_save,
            file,
            ensure_ascii=False,
            indent=2
        )


def clear_cache(
    athlete_id=None
):

    cache_file = _get_cache_file(
        athlete_id
    )

    if os.path.exists(
        cache_file
    ):

        os.remove(
            cache_file
        )