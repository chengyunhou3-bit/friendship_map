from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from uuid import uuid4


STORAGE_VERSION = 2
SUPPORTED_LANGUAGES = {"en", "zh"}


def empty_library():
    return {
        "storage_version": STORAGE_VERSION,
        "preferences": {},
        "records": []
    }


def _normalize_preferences(payload):
    preferences = payload.get("preferences", {})

    if not isinstance(preferences, dict):
        return {}

    selected_language = str(preferences.get("language", "")).strip()

    if selected_language not in SUPPORTED_LANGUAGES:
        return {}

    return {"language": selected_language}


def get_preferred_language(library):
    return _normalize_preferences(
        library if isinstance(library, dict) else {}
    ).get("language")


def set_preferred_language(library, selected_language):
    updated_library = normalize_library(library)

    if selected_language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language preference")

    updated_library["preferences"] = {
        "language": selected_language
    }
    return updated_library


def default_record_title(result=None):
    result = result if isinstance(result, dict) else {}
    saved_at = str(result.get("saved_at", "")).strip()

    try:
        saved_time = datetime.fromisoformat(saved_at)
    except ValueError:
        saved_time = datetime.now()

    return f"紀錄 {saved_time:%Y-%m-%d %H:%M}"


def _legacy_record_id(result):
    identity = "|".join(
        [
            str(result.get("saved_at", "")),
            ",".join(map(str, result.get("names", [])))
        ]
    )
    return f"legacy-{sha256(identity.encode('utf-8')).hexdigest()[:16]}"


def normalize_library(payload):
    if not isinstance(payload, dict):
        return empty_library()

    if payload.get("storage_version") == STORAGE_VERSION:
        records = []

        for item in payload.get("records", []):
            if not isinstance(item, dict):
                continue

            result = item.get("result")

            if not isinstance(result, dict) or "names" not in result:
                continue

            record_id = str(item.get("id", "")).strip() or uuid4().hex
            title = str(item.get("title", "")).strip()
            created_at = str(item.get("created_at", "")).strip()
            updated_at = str(item.get("updated_at", "")).strip()
            fallback_time = str(result.get("saved_at", "")).strip()

            records.append(
                {
                    "id": record_id,
                    "title": title[:80] or default_record_title(result),
                    "created_at": created_at or fallback_time,
                    "updated_at": updated_at or fallback_time,
                    "result": deepcopy(result)
                }
            )

        records.sort(
            key=lambda record: record.get("updated_at", ""),
            reverse=True
        )
        return {
            "storage_version": STORAGE_VERSION,
            "preferences": _normalize_preferences(payload),
            "records": records
        }

    if "names" in payload:
        saved_at = str(payload.get("saved_at", "")).strip()
        return {
            "storage_version": STORAGE_VERSION,
            "preferences": {},
            "records": [
                {
                    "id": _legacy_record_id(payload),
                    "title": default_record_title(payload),
                    "created_at": saved_at,
                    "updated_at": saved_at,
                    "result": deepcopy(payload)
                }
            ]
        }

    return empty_library()


def get_record(library, record_id):
    for record in library.get("records", []):
        if record.get("id") == record_id:
            return record

    return None


def upsert_record(library, record_id, title, result):
    updated_library = normalize_library(library)
    now = datetime.now().isoformat(timespec="seconds")
    clean_title = str(title).strip()[:80] or default_record_title(result)
    record = get_record(updated_library, record_id)

    if record is None:
        record_id = uuid4().hex
        record = {
            "id": record_id,
            "title": clean_title,
            "created_at": now,
            "updated_at": now,
            "result": deepcopy(result)
        }
        updated_library["records"].append(record)
    else:
        record["title"] = clean_title
        record["updated_at"] = now
        record["result"] = deepcopy(result)

    updated_library["records"].sort(
        key=lambda item: item.get("updated_at", ""),
        reverse=True
    )
    return updated_library, record_id


def delete_record(library, record_id):
    updated_library = normalize_library(library)
    updated_library["records"] = [
        record
        for record in updated_library["records"]
        if record.get("id") != record_id
    ]
    return updated_library


def record_label(record):
    title = str(record.get("title", "")).strip() or "未命名紀錄"
    updated_at = str(record.get("updated_at", "")).strip()

    try:
        timestamp = datetime.fromisoformat(updated_at).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        timestamp = "日期不明"

    return f"{title} · {timestamp}"
