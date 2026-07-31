from datetime import datetime, timezone


TABLE_NAME = "friendship_results"


def _client(url, service_key):
    try:
        from supabase import create_client
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "尚未安裝 Supabase 套件，請執行 "
            "python3 -m pip install -r requirements.txt"
        ) from error

    return create_client(url, service_key)


def load_cloud_results(url, service_key, owner_id):
    response = (
        _client(url, service_key)
        .table(TABLE_NAME)
        .select("result")
        .eq("owner_id", owner_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]["result"]


def save_cloud_results(url, service_key, owner_id, result):
    (
        _client(url, service_key)
        .table(TABLE_NAME)
        .upsert(
            {
                "owner_id": owner_id,
                "result": result,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            on_conflict="owner_id"
        )
        .execute()
    )


def delete_cloud_results(url, service_key, owner_id):
    (
        _client(url, service_key)
        .table(TABLE_NAME)
        .delete()
        .eq("owner_id", owner_id)
        .execute()
    )
