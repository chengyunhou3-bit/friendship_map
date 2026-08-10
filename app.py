import math
import random
import re
import sys
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
from matplotlib import font_manager

APP_DIRECTORY = Path(__file__).resolve().parent
CHINESE_FONT_PATH = APP_DIRECTORY / "static" / "NotoSansTC-ExtraBold.otf"
CHINESE_FONT = font_manager.FontProperties(fname=CHINESE_FONT_PATH)
STATIC_CHART_TEXT_COLOR = "#000000"

if str(APP_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(APP_DIRECTORY))

from friendship import (
    load_results as load_local_results,
    normalize_scores,
    save_data as save_local_data
)
from cloud_store import (
    delete_cloud_results,
    load_cloud_results,
    save_cloud_results
)
from draggable_map import draggable_relationship_map
from comparison_keyboard import comparison_keyboard_listener
from pin_keyboard import pin_keyboard_listener
from sidebar_control import collapse_sidebar
from result_library import (
    default_record_title,
    delete_record as remove_record_from_library,
    get_record,
    normalize_library,
    record_label,
    upsert_record
)
from record_pin import (
    create_pin_protection,
    disabled_pin_protection,
    pin_protection_is_disabled,
    pin_protection_is_enabled,
    validate_pin,
    verify_pin
)


st.set_page_config(
    page_title="人際關係座標圖",
    page_icon=str(APP_DIRECTORY / "static" / "app-icon-512.png"),
    layout="centered"
)

DEFAULT_DISPLAY_SETTINGS = {
    "app_title": "人際關係座標圖",
    "familiarity_question": "你跟誰比較熟？",
    "likability_question": "誰的人品更好？",
    "x_axis_title": "熟悉度：不熟 ← → 熟悉",
    "y_axis_title": "好感度：負面 ← → 喜歡"
}

DEFAULT_QUADRANT_SETTINGS = {
    "top_right": {"name": "右上象限", "color": "#D9EAF7"},
    "top_left": {"name": "左上象限", "color": "#E3F2DD"},
    "bottom_left": {"name": "左下象限", "color": "#FBE5D6"},
    "bottom_right": {"name": "右下象限", "color": "#EADCF4"}
}


def normalized_display_settings(settings=None):
    normalized = dict(DEFAULT_DISPLAY_SETTINGS)

    if isinstance(settings, dict):
        for key in normalized:
            value = str(settings.get(key, "")).strip()
            if value:
                normalized[key] = value[:80]

    return normalized


def normalized_quadrant_settings(settings=None):
    normalized = deepcopy(DEFAULT_QUADRANT_SETTINGS)

    if not isinstance(settings, dict):
        return normalized

    for quadrant, defaults in DEFAULT_QUADRANT_SETTINGS.items():
        supplied = settings.get(quadrant)
        if not isinstance(supplied, dict):
            continue

        name = str(supplied.get("name", "")).strip()
        color = str(supplied.get("color", "")).strip()
        if name:
            normalized[quadrant]["name"] = name[:30]
        if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            normalized[quadrant]["color"] = color.upper()

    return normalized


def normalized_annotations(annotations=None):
    normalized = []

    if not isinstance(annotations, list):
        return normalized

    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue

        target_type = str(annotation.get("target_type", "")).strip()
        target_id = str(annotation.get("target_id", "")).strip()
        note = str(annotation.get("note", "")).strip()
        if target_type not in {"quadrant", "friend", "custom"}:
            continue
        if not target_id or not note:
            continue

        normalized.append(
            {
                "target_type": target_type,
                "target_id": target_id[:80],
                "note": note[:500]
            }
        )

    return normalized


def display_record_label(record):
    label = record_label(record)
    pin_protection = record.get("result", {}).get("pin_protection")

    if pin_protection_is_enabled(pin_protection):
        return f"🔒 {label}"

    return label


def secret_section(name):
    try:
        return st.secrets.get(name, {})
    except (FileNotFoundError, KeyError):
        return {}


def cloud_mode_enabled():
    return secret_section("app").get("mode", "local") == "cloud"


def guest_mode_enabled():
    return (
        cloud_mode_enabled()
        and st.session_state.get("guest_mode", False)
    )


def user_is_logged_in():
    return bool(getattr(st.user, "is_logged_in", False))


def current_owner_id():
    subject = str(st.user.get("sub", ""))

    if not subject:
        raise RuntimeError("登入資料中找不到使用者 ID。")

    return sha256(subject.encode("utf-8")).hexdigest()


def cloud_credentials():
    settings = secret_section("supabase")
    url = str(settings.get("url", "")).strip()
    service_key = str(settings.get("service_key", "")).strip()

    if not url or not service_key:
        raise RuntimeError("尚未設定 Supabase 網址或 service key。")

    return url, service_key


def build_result_data(
    names,
    familiarity_scores,
    likability_scores,
    x_coordinates,
    y_coordinates,
    display_settings,
    pin_protection=None
):
    result = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "names": names,
        "familiarity_scores": familiarity_scores,
        "likability_scores": likability_scores,
        "x_coordinates": x_coordinates,
        "y_coordinates": y_coordinates,
        "display_settings": normalized_display_settings(display_settings),
        "quadrant_settings": normalized_quadrant_settings(
            st.session_state.quadrant_settings
        ),
        "annotations": normalized_annotations(
            st.session_state.annotations
        )
    }

    if pin_protection is not None:
        result["pin_protection"] = pin_protection

    return result


def save_current_results(
    names,
    familiarity_scores,
    likability_scores,
    x_coordinates,
    y_coordinates
):
    global result_library

    if guest_mode_enabled():
        return

    result = build_result_data(
        names,
        familiarity_scores,
        likability_scores,
        x_coordinates,
        y_coordinates,
        st.session_state.display_settings,
        st.session_state.pin_protection
    )
    result_library, record_id = upsert_record(
        result_library,
        st.session_state.current_record_id,
        st.session_state.record_title,
        result
    )
    persist_result_library(result_library)
    st.session_state.current_record_id = record_id
    st.session_state.selected_record_id = record_id
    st.session_state.record_selector_pending = record_id


def persist_result_library(library):
    if guest_mode_enabled():
        return

    if not cloud_mode_enabled():
        save_local_data(library)
        return

    url, service_key = cloud_credentials()
    save_cloud_results(
        url,
        service_key,
        current_owner_id(),
        library
    )


def save_pin_protection(record, pin_protection):
    global result_library

    updated_result = dict(record["result"])
    updated_result["pin_protection"] = pin_protection
    record["result"] = updated_result
    result_library, record_id = upsert_record(
        result_library,
        record["id"],
        record["title"],
        updated_result
    )
    persist_result_library(result_library)

    if st.session_state.current_record_id == record_id:
        st.session_state.pin_protection = pin_protection

    st.session_state.selected_record_id = record_id
    st.session_state.record_selector_pending = record_id


def load_current_results():
    if guest_mode_enabled():
        return None

    if not cloud_mode_enabled():
        return load_local_results()

    url, service_key = cloud_credentials()
    return load_cloud_results(
        url,
        service_key,
        current_owner_id()
    )


def delete_current_results():
    if guest_mode_enabled():
        return

    if not cloud_mode_enabled():
        persist_result_library(normalize_library(None))
        return

    url, service_key = cloud_credentials()
    delete_cloud_results(
        url,
        service_key,
        current_owner_id()
    )


def delete_saved_record(record_id):
    global result_library

    result_library = remove_record_from_library(
        result_library,
        record_id
    )
    persist_result_library(result_library)


def rename_saved_record(record_id, new_title):
    global result_library

    record = get_record(result_library, record_id)

    if record is None:
        return False

    clean_title = str(new_title).strip()[:80]

    if not clean_title:
        return False

    result_library, _ = upsert_record(
        result_library,
        record_id,
        clean_title,
        record["result"]
    )
    persist_result_library(result_library)

    if st.session_state.current_record_id == record_id:
        st.session_state.record_title = clean_title

    st.session_state.selected_record_id = record_id
    st.session_state.record_selector_pending = record_id
    return True


def initialize_state():
    defaults = {
        "stage": "names",
        "names": [],
        "pairs": [],
        "question_index": 0,
        "answer_history": [],
        "adaptive_groups": [],
        "adaptive_pending": [],
        "adaptive_candidate": None,
        "adaptive_low": 0,
        "adaptive_high": 0,
        "adaptive_mid": None,
        "stage_answer_count": 0,
        "stage_question_max": 1,
        "guest_mode": False,
        "display_settings": normalized_display_settings(),
        "quadrant_settings": normalized_quadrant_settings(),
        "annotations": [],
        "display_settings_loaded": False,
        "pin_protection": None,
        "pin_prompt_open": False,
        "pin_prompt_record_id": None,
        "pin_keypad_value": "",
        "pin_keypad_error": "",
        "pin_keyboard_event_id": None,
        "comparison_keyboard_event_id": None,
        "pin_unlock_message": None,
        "collapse_sidebar_requested": False,
        "pin_settings_record_id": None,
        "current_record_id": None,
        "selected_record_id": None,
        "record_selector": None,
        "record_selector_pending": None,
        "record_title": "",
        "comparison_mode": "initial",
        "new_names": [],
        "editor_version": 0,
        "familiarity_scores": {},
        "likability_scores": {},
        "x_coordinates": {},
        "y_coordinates": {}
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_app(preserve_access_mode=True):
    was_guest = guest_mode_enabled()

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    if preserve_access_mode and was_guest:
        st.session_state.guest_mode = True


def start_guest_mode():
    st.session_state.guest_mode = True


def exit_guest_mode():
    reset_app(preserve_access_mode=False)


def parse_names(raw_names):
    pieces = re.split(r"[\n,，]+", raw_names)
    names = []

    for piece in pieces:
        name = piece.strip()

        if name and name not in names:
            names.append(name)

    return names


def estimated_fast_question_count(new_count, starting_count=1):
    """Return a readable upper estimate for binary-insertion questions."""
    total = 0

    for existing_count in range(starting_count, starting_count + new_count):
        total += max(1, math.ceil(math.log2(existing_count + 1)))

    return max(1, total)


def groups_from_coordinates(names, coordinates):
    """Build descending tie groups from an existing saved coordinate axis."""
    groups = []

    for name in sorted(names, key=lambda item: coordinates[item], reverse=True):
        value = coordinates[name]

        if groups and coordinates[groups[-1][0]] == value:
            groups[-1].append(name)
        else:
            groups.append([name])

    return groups


def begin_fast_stage(stage):
    """Prepare one adaptive comparison stage and its first question."""
    st.session_state.stage = stage
    st.session_state.pairs = []
    st.session_state.question_index = 0
    st.session_state.stage_answer_count = 0

    if st.session_state.comparison_mode == "incremental":
        old_names = [
            name for name in st.session_state.names
            if name not in set(st.session_state.new_names)
        ]
        coordinates = (
            st.session_state.x_coordinates
            if stage == "familiarity"
            else st.session_state.y_coordinates
        )
        st.session_state.adaptive_groups = groups_from_coordinates(
            old_names,
            coordinates
        )
        pending = list(st.session_state.new_names)
        random.shuffle(pending)
        st.session_state.adaptive_pending = pending
        st.session_state.stage_question_max = estimated_fast_question_count(
            len(pending),
            max(1, len(st.session_state.adaptive_groups))
        )
    else:
        pending = list(st.session_state.names)
        random.shuffle(pending)
        st.session_state.adaptive_groups = [[pending.pop()]]
        st.session_state.adaptive_pending = pending
        st.session_state.stage_question_max = estimated_fast_question_count(
            len(pending)
        )

    st.session_state.adaptive_candidate = None
    st.session_state.adaptive_low = 0
    st.session_state.adaptive_high = 0
    st.session_state.adaptive_mid = None
    schedule_fast_question()


def schedule_fast_question():
    """Append the next useful comparison, or finish the current stage."""
    while st.session_state.adaptive_candidate is None:
        if not st.session_state.adaptive_pending:
            return False

        st.session_state.adaptive_candidate = (
            st.session_state.adaptive_pending.pop(0)
        )
        st.session_state.adaptive_low = 0
        st.session_state.adaptive_high = len(
            st.session_state.adaptive_groups
        )

        if st.session_state.adaptive_high == 0:
            st.session_state.adaptive_groups.append(
                [st.session_state.adaptive_candidate]
            )
            st.session_state.adaptive_candidate = None

    low = st.session_state.adaptive_low
    high = st.session_state.adaptive_high

    if low >= high:
        st.session_state.adaptive_groups.insert(
            low,
            [st.session_state.adaptive_candidate]
        )
        st.session_state.adaptive_candidate = None
        return schedule_fast_question()

    middle = (low + high) // 2
    st.session_state.adaptive_mid = middle
    st.session_state.pairs.append(
        (
            st.session_state.adaptive_candidate,
            st.session_state.adaptive_groups[middle][0]
        )
    )
    return True


def apply_fast_ranking_to_scores(stage):
    """Infer the original all-pairs scores from a consistent ordered result."""
    groups = st.session_state.adaptive_groups
    scores = (
        st.session_state.familiarity_scores
        if stage == "familiarity"
        else st.session_state.likability_scores
    )
    total_people = sum(len(group) for group in groups)
    higher_count = 0

    for group in groups:
        lower_count = total_people - higher_count - len(group)
        score = lower_count - higher_count
        for name in group:
            scores[name] = score
        higher_count += len(group)


def fast_state_snapshot():
    keys = (
        "stage", "pairs", "question_index", "comparison_mode",
        "new_names", "adaptive_groups", "adaptive_pending",
        "adaptive_candidate", "adaptive_low", "adaptive_high",
        "adaptive_mid", "stage_answer_count", "stage_question_max",
        "familiarity_scores", "likability_scores"
    )
    return {key: deepcopy(st.session_state[key]) for key in keys}


def start_comparison(names, record_title):
    st.session_state.names = names
    st.session_state.current_record_id = None
    st.session_state.record_title = (
        str(record_title).strip()[:80]
        or default_record_title()
    )
    st.session_state.pin_protection = None
    st.session_state.familiarity_scores = {
        name: 0 for name in names
    }
    st.session_state.likability_scores = {
        name: 0 for name in names
    }
    st.session_state.answer_history = []
    st.session_state.comparison_mode = "initial"
    st.session_state.new_names = []
    begin_fast_stage("familiarity")


def start_incremental_comparison(new_names):
    st.session_state.new_names = new_names
    st.session_state.comparison_mode = "incremental"

    for name in new_names:
        st.session_state.names.append(name)
        st.session_state.familiarity_scores[name] = 0
        st.session_state.likability_scores[name] = 0

    st.session_state.answer_history = []
    begin_fast_stage("familiarity")


def record_answer(result, expected_stage, expected_question_index):
    stage = st.session_state.stage
    question_index = st.session_state.question_index

    # 忽略上一題或已結束頁面延遲送達的重複點擊。
    if stage != expected_stage or question_index != expected_question_index:
        return

    if stage not in ["familiarity", "likability"]:
        return

    pairs = st.session_state.pairs

    if question_index < 0 or question_index >= len(pairs):
        return

    person_a, person_b = pairs[question_index]

    st.session_state.answer_history.append(fast_state_snapshot())

    middle = st.session_state.adaptive_mid
    if result == ">":
        st.session_state.adaptive_high = middle
    elif result == "<":
        st.session_state.adaptive_low = middle + 1
    else:
        st.session_state.adaptive_groups[middle].append(person_a)
        st.session_state.adaptive_candidate = None

    st.session_state.question_index += 1
    st.session_state.stage_answer_count += 1

    if schedule_fast_question():
        return

    apply_fast_ranking_to_scores(stage)

    if stage == "familiarity":
        begin_fast_stage("likability")
        return

    st.session_state.x_coordinates = normalize_scores(
        st.session_state.familiarity_scores
    )
    st.session_state.y_coordinates = normalize_scores(
        st.session_state.likability_scores
    )

    save_current_results(
        st.session_state.names,
        st.session_state.familiarity_scores,
        st.session_state.likability_scores,
        st.session_state.x_coordinates,
        st.session_state.y_coordinates
    )

    st.session_state.comparison_mode = "initial"
    st.session_state.new_names = []
    st.session_state.editor_version += 1
    st.session_state.pop("new_names_input", None)
    st.session_state.stage = "results"


def undo_last_answer():
    if not st.session_state.answer_history:
        return

    snapshot = st.session_state.answer_history.pop()
    for key, value in snapshot.items():
        st.session_state[key] = value


def load_saved_into_state(record):
    saved_results = record["result"]
    st.session_state.names = saved_results["names"]
    st.session_state.familiarity_scores = saved_results[
        "familiarity_scores"
    ]
    st.session_state.likability_scores = saved_results[
        "likability_scores"
    ]
    st.session_state.x_coordinates = saved_results["x_coordinates"]
    st.session_state.y_coordinates = saved_results["y_coordinates"]
    st.session_state.display_settings = normalized_display_settings(
        saved_results.get("display_settings")
    )
    st.session_state.quadrant_settings = normalized_quadrant_settings(
        saved_results.get("quadrant_settings")
    )
    st.session_state.annotations = normalized_annotations(
        saved_results.get("annotations")
    )
    st.session_state.current_record_id = record["id"]
    st.session_state.selected_record_id = record["id"]
    st.session_state.record_title = record["title"]
    st.session_state.pin_protection = saved_results.get("pin_protection")
    st.session_state.comparison_mode = "initial"
    st.session_state.new_names = []
    st.session_state.pairs = []
    st.session_state.question_index = 0
    st.session_state.answer_history = []
    st.session_state.editor_version += 1
    st.session_state.stage = "results"


def close_pin_prompt():
    st.session_state.pin_prompt_open = False
    st.session_state.pin_prompt_record_id = None
    st.session_state.pin_keypad_value = ""
    st.session_state.pin_keypad_error = ""
    st.session_state.pin_keyboard_event_id = None


def open_pin_prompt(record):
    st.session_state.pin_prompt_open = True
    st.session_state.pin_prompt_record_id = record["id"]
    st.session_state.pin_keypad_value = ""
    st.session_state.pin_keypad_error = ""
    st.session_state.pin_keyboard_event_id = None


def complete_pin_unlock(record, entered_pin, pin_protection):
    if not isinstance(pin_protection.get("length"), int):
        upgraded_protection = dict(pin_protection)
        upgraded_protection["length"] = len(str(entered_pin))
        save_pin_protection(record, upgraded_protection)
    load_saved_into_state(record)
    close_pin_prompt()
    st.session_state.pin_unlock_message = (
        f"PIN 正確，已載入「{record['title']}」。"
    )
    st.session_state.collapse_sidebar_requested = True


def try_unlock_record(record, entered_pin):
    pin_protection = record["result"].get("pin_protection")

    if verify_pin(entered_pin, pin_protection):
        complete_pin_unlock(record, entered_pin, pin_protection)
        return True

    st.session_state.pin_keypad_value = ""
    st.session_state.pin_keypad_error = "PIN 錯誤，請再試一次。"
    return False


def apply_pin_value(entered_pin, record):
    entered_pin = str(entered_pin)
    if not entered_pin.isdigit() or len(entered_pin) > 8:
        return False

    st.session_state.pin_keypad_value = entered_pin
    st.session_state.pin_keypad_error = ""

    pin_protection = record["result"].get("pin_protection")
    expected_length = pin_protection.get("length")

    if verify_pin(entered_pin, pin_protection):
        complete_pin_unlock(record, entered_pin, pin_protection)
        return True
    elif (
        isinstance(expected_length, int)
        and 4 <= expected_length <= 8
        and len(entered_pin) >= expected_length
    ) or len(entered_pin) >= 8:
        st.session_state.pin_keypad_value = ""
        st.session_state.pin_keypad_error = "PIN 錯誤，請再試一次。"

    return False


def enter_pin_digit(digit, record):
    current_pin = st.session_state.pin_keypad_value
    if len(current_pin) >= 8:
        return False

    return apply_pin_value(f"{current_pin}{digit}", record)


def remove_pin_digit():
    st.session_state.pin_keypad_value = (
        st.session_state.pin_keypad_value[:-1]
    )
    st.session_state.pin_keypad_error = ""


def confirm_keypad_pin(record):
    entered_pin = st.session_state.pin_keypad_value
    valid, pin_error = validate_pin(entered_pin)

    if not valid:
        st.session_state.pin_keypad_error = pin_error
        return False

    return try_unlock_record(record, entered_pin)


def ignore_pin_keyboard_action():
    pass


def ignore_comparison_keyboard_action():
    pass


@st.dialog(
    "輸入紀錄 PIN",
    width="small",
    icon="🔒",
    on_dismiss=close_pin_prompt
)
def show_pin_keypad(record):
    st.caption(record["title"])
    st.caption("可直接使用電腦數字鍵輸入，Enter 確認。")
    st.markdown(
        """
        <style>
        .st-key-pin_keypad_grid [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 0.5rem !important;
        }
        .st-key-pin_keypad_grid [data-testid="stColumn"],
        .st-key-pin_keypad_grid [data-testid="column"] {
            flex: 1 1 0 !important;
            width: 0 !important;
            min-width: 0 !important;
        }
        .st-key-pin_keypad_grid button {
            min-height: 3rem;
            font-size: 1.15rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    pin_protection = record["result"].get("pin_protection")
    expected_pin_length = (
        pin_protection.get("length")
        if isinstance(pin_protection, dict)
        else None
    )
    keyboard_result = pin_keyboard_listener(
        data={
            "currentPin": st.session_state.pin_keypad_value,
            "expectedLength": expected_pin_length
        },
        key=f"pin_keyboard_{record['id']}",
        on_action_change=ignore_pin_keyboard_action,
        width="stretch",
        height=64
    )
    keyboard_event = getattr(keyboard_result, "action", None)

    if isinstance(keyboard_event, dict):
        event_id = keyboard_event.get("eventId")
        action_type = keyboard_event.get("type")
        keyboard_pin = keyboard_event.get("value")

        if event_id != st.session_state.pin_keyboard_event_id:
            st.session_state.pin_keyboard_event_id = event_id

            if action_type == "submit":
                if (
                    isinstance(keyboard_pin, str)
                    and (not keyboard_pin or keyboard_pin.isdigit())
                ):
                    st.session_state.pin_keypad_value = keyboard_pin
                else:
                    st.session_state.pin_keypad_error = (
                        "PIN 只能輸入數字。"
                    )
                    st.rerun(scope="fragment")
                if confirm_keypad_pin(record):
                    st.rerun(scope="app")
                st.rerun(scope="fragment")
            elif action_type == "cancel":
                close_pin_prompt()
                st.rerun(scope="app")

    entered_length = len(st.session_state.pin_keypad_value)

    if st.session_state.pin_keypad_error:
        st.error(st.session_state.pin_keypad_error)

    keypad_grid = st.container(key="pin_keypad_grid")
    clicked_digit = None

    for row in (("1", "2", "3"), ("4", "5", "6"), ("7", "8", "9")):
        columns = keypad_grid.columns(3)
        for column, digit in zip(columns, row):
            if column.button(
                digit,
                key=f"pin_key_{record['id']}_{digit}",
                width="stretch"
            ):
                clicked_digit = digit

    backspace_column, zero_column, confirm_column = keypad_grid.columns(3)
    backspace_clicked = backspace_column.button(
        "⌫",
        key=f"pin_key_{record['id']}_backspace",
        width="stretch",
        disabled=entered_length == 0
    )
    if zero_column.button(
        "0",
        key=f"pin_key_{record['id']}_0",
        width="stretch"
    ):
        clicked_digit = "0"
    confirm_clicked = confirm_column.button(
        "✓",
        key=f"pin_key_{record['id']}_confirm",
        type="primary",
        width="stretch"
    )

    cancel_clicked = st.button(
        "取消",
        key=f"pin_key_{record['id']}_cancel",
        width="stretch"
    )

    if clicked_digit is not None:
        unlocked = enter_pin_digit(clicked_digit, record)
        st.rerun(scope="app" if unlocked else "fragment")

    if backspace_clicked:
        remove_pin_digit()
        st.rerun(scope="fragment")

    if confirm_clicked:
        unlocked = confirm_keypad_pin(record)
        st.rerun(scope="app" if unlocked else "fragment")

    if cancel_clicked:
        close_pin_prompt()
        st.rerun(scope="app")


def apply_result_edits(ranking, edited_data):
    if hasattr(edited_data, "to_dict"):
        edited_rows = edited_data.to_dict("records")
    else:
        edited_rows = list(edited_data)

    if len(edited_rows) != len(ranking):
        return False, "表格資料不完整，請重新整理後再試。"

    rename_map = {}
    edited_coordinates = {}
    new_names = []

    for old_name, row in zip(ranking, edited_rows):
        new_name = str(row.get("名字", "")).strip()

        if not new_name:
            return False, "名字不能是空白。"

        if new_name in new_names:
            return False, f"名字「{new_name}」重複了。"

        try:
            x = float(row["X 座標"])
            y = float(row["Y 座標"])
        except (KeyError, TypeError, ValueError):
            return False, f"{new_name} 的座標必須是數字。"

        if not math.isfinite(x) or not math.isfinite(y):
            return False, f"{new_name} 的座標必須是有效數字。"

        x = max(-100, min(100, round(x)))
        y = max(-100, min(100, round(y)))

        rename_map[old_name] = new_name
        edited_coordinates[new_name] = (x, y)
        new_names.append(new_name)

    old_familiarity_scores = st.session_state.familiarity_scores
    old_likability_scores = st.session_state.likability_scores
    old_names = st.session_state.names

    st.session_state.names = [
        rename_map[name] for name in old_names
    ]
    st.session_state.familiarity_scores = {
        rename_map[name]: old_familiarity_scores[name]
        for name in old_names
    }
    st.session_state.likability_scores = {
        rename_map[name]: old_likability_scores[name]
        for name in old_names
    }
    st.session_state.x_coordinates = {
        name: edited_coordinates[name][0]
        for name in st.session_state.names
    }
    st.session_state.y_coordinates = {
        name: edited_coordinates[name][1]
        for name in st.session_state.names
    }
    st.session_state.annotations = [
        {
            **annotation,
            "target_id": rename_map.get(
                annotation["target_id"],
                annotation["target_id"]
            )
        }
        if annotation["target_type"] == "friend"
        else annotation
        for annotation in normalized_annotations(
            st.session_state.annotations
        )
    ]

    save_current_results(
        st.session_state.names,
        st.session_state.familiarity_scores,
        st.session_state.likability_scores,
        st.session_state.x_coordinates,
        st.session_state.y_coordinates
    )

    st.session_state.answer_history = []
    st.session_state.editor_version += 1
    return True, "名字與座標已更新並保存。"


def apply_dragged_point():
    component_result = st.session_state.get(
        "relationship_map_component"
    )
    moved_point = getattr(component_result, "moved", None)

    if not isinstance(moved_point, dict):
        return

    moved_points = moved_point.get("points")
    if not isinstance(moved_points, list):
        moved_points = [moved_point]

    applied_points = []
    for point in moved_points:
        if not isinstance(point, dict):
            continue

        name = point.get("name")
        if name not in st.session_state.names:
            continue

        try:
            x = max(-100, min(100, round(float(point["x"]))))
            y = max(-100, min(100, round(float(point["y"]))))
        except (KeyError, TypeError, ValueError):
            continue

        st.session_state.x_coordinates[name] = x
        st.session_state.y_coordinates[name] = y
        applied_points.append((name, x, y))

    if not applied_points:
        return

    save_current_results(
        st.session_state.names,
        st.session_state.familiarity_scores,
        st.session_state.likability_scores,
        st.session_state.x_coordinates,
        st.session_state.y_coordinates
    )

    if len(applied_points) == 1:
        name, x, y = applied_points[0]
        st.session_state.drag_message = (
            f"{name} 的座標已更新為 ({x}, {y})"
        )
    else:
        st.session_state.drag_message = (
            f"已更新並保存 {len(applied_points)} 個人物的座標"
        )
    st.session_state.editor_version += 1


def make_figure():
    plt.rcParams["axes.unicode_minus"] = False

    figure, axis = plt.subplots(figsize=(8, 8))
    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")
    quadrants = normalized_quadrant_settings(
        st.session_state.quadrant_settings
    )
    quadrant_areas = {
        "top_right": (0, 0, 110, 110, 55, 55),
        "top_left": (-110, 0, 110, 110, -55, 55),
        "bottom_left": (-110, -110, 110, 110, -55, -55),
        "bottom_right": (0, -110, 110, 110, 55, -55)
    }

    for quadrant, area in quadrant_areas.items():
        x, y, width, height, label_x, label_y = area
        setting = quadrants[quadrant]
        axis.add_patch(
            plt.Rectangle(
                (x, y),
                width,
                height,
                facecolor=setting["color"],
                edgecolor="none",
                alpha=0.38,
                zorder=0
            )
        )
        axis.text(
            label_x,
            label_y,
            setting["name"],
            horizontalalignment="center",
            verticalalignment="center",
            fontproperties=CHINESE_FONT,
            fontsize=18,
            color=STATIC_CHART_TEXT_COLOR,
            alpha=0.52,
            zorder=1
        )

    axis.axhline(0, color="gray", linewidth=1)
    axis.axvline(0, color="gray", linewidth=1)

    for name in st.session_state.names:
        x = st.session_state.x_coordinates[name]
        y = st.session_state.y_coordinates[name]

        axis.scatter(x, y, s=100, zorder=3)
        axis.annotate(
            name,
            (x, y),
            xytext=(5, 5),
            textcoords="offset points",
            fontproperties=CHINESE_FONT,
            color=STATIC_CHART_TEXT_COLOR,
            zorder=4
        )

    axis.set_xlim(-110, 110)
    axis.set_ylim(-110, 110)
    settings = st.session_state.display_settings
    axis.set_xlabel(
        settings["x_axis_title"],
        fontproperties=CHINESE_FONT,
        color=STATIC_CHART_TEXT_COLOR
    )
    axis.set_ylabel(
        settings["y_axis_title"],
        fontproperties=CHINESE_FONT,
        color=STATIC_CHART_TEXT_COLOR
    )
    axis.set_title(
        settings["app_title"],
        fontproperties=CHINESE_FONT,
        color=STATIC_CHART_TEXT_COLOR
    )
    axis.tick_params(colors=STATIC_CHART_TEXT_COLOR)
    for spine in axis.spines.values():
        spine.set_color(STATIC_CHART_TEXT_COLOR)
    axis.grid(alpha=0.2)

    return figure


if (
    cloud_mode_enabled()
    and not user_is_logged_in()
    and not guest_mode_enabled()
):
    st.title("🗺️ 人際關係座標圖")
    st.write("登入可保存並載入自己的結果；也可以不登入單次使用。")
    st.button(
        "使用 Google 登入",
        type="primary",
        width="stretch",
        on_click=st.login
    )
    st.button(
        "以訪客身分使用",
        width="stretch",
        on_click=start_guest_mode
    )
    st.caption("訪客結果不會儲存，離開後無法載入。")
    st.stop()


initialize_state()

try:
    stored_results = load_current_results()
except Exception as error:
    st.error("目前無法連接私人資料庫，請稍後再試。")
    st.exception(error)
    st.stop()

result_library = normalize_library(stored_results)
saved_records = result_library["records"]
saved_record_ids = [record["id"] for record in saved_records]

if st.session_state.selected_record_id not in saved_record_ids:
    st.session_state.selected_record_id = (
        saved_record_ids[0] if saved_record_ids else None
    )

pending_record_selector = st.session_state.pop(
    "record_selector_pending",
    None
)

if pending_record_selector in saved_record_ids:
    st.session_state.record_selector = pending_record_selector
elif st.session_state.record_selector not in saved_record_ids:
    st.session_state.record_selector = st.session_state.selected_record_id

selected_record = get_record(
    result_library,
    st.session_state.selected_record_id
)

if not st.session_state.display_settings_loaded:
    st.session_state.display_settings_loaded = True

title_column, settings_column = st.columns(
    [0.88, 0.12],
    vertical_alignment="center"
)

with title_column:
    st.title(f"🗺️ {st.session_state.display_settings['app_title']}")

with settings_column:
    with st.popover("⚙️", help="自訂標題與問題文字"):
        st.markdown("#### 自訂文字")
        current_settings = st.session_state.display_settings

        with st.form("display_settings_form"):
            custom_app_title = st.text_input(
                "畫面標題",
                value=current_settings["app_title"],
                max_chars=80
            )
            custom_familiarity_question = st.text_input(
                "第一組選擇題",
                value=current_settings["familiarity_question"],
                max_chars=80
            )
            custom_x_axis_title = st.text_input(
                "X 軸標題",
                value=current_settings["x_axis_title"],
                max_chars=80
            )
            custom_likability_question = st.text_input(
                "第二組選擇題",
                value=current_settings["likability_question"],
                max_chars=80
            )
            custom_y_axis_title = st.text_input(
                "Y 軸標題",
                value=current_settings["y_axis_title"],
                max_chars=80
            )

            save_custom_text = st.form_submit_button(
                "套用文字",
                type="primary",
                width="stretch"
            )
            restore_default_text = st.form_submit_button(
                "恢復預設",
                width="stretch"
            )

        if save_custom_text:
            new_settings = {
                "app_title": custom_app_title,
                "familiarity_question": custom_familiarity_question,
                "likability_question": custom_likability_question,
                "x_axis_title": custom_x_axis_title,
                "y_axis_title": custom_y_axis_title
            }

            if any(not value.strip() for value in new_settings.values()):
                st.error("文字欄位不能留白。")
            else:
                st.session_state.display_settings = (
                    normalized_display_settings(new_settings)
                )

                if st.session_state.stage == "results":
                    save_current_results(
                        st.session_state.names,
                        st.session_state.familiarity_scores,
                        st.session_state.likability_scores,
                        st.session_state.x_coordinates,
                        st.session_state.y_coordinates
                    )
                st.rerun()

        if restore_default_text:
            st.session_state.display_settings = normalized_display_settings()

            if st.session_state.stage == "results":
                save_current_results(
                    st.session_state.names,
                    st.session_state.familiarity_scores,
                    st.session_state.likability_scores,
                    st.session_state.x_coordinates,
                    st.session_state.y_coordinates
                )
            st.rerun()

st.caption("用兩兩比較，把朋友放進熟悉度與好感度座標。")

with st.sidebar:
    st.subheader("選單")

    if guest_mode_enabled():
        st.caption("訪客模式：結果不會儲存")
    elif cloud_mode_enabled():
        display_name = st.user.get("name") or st.user.get("email")
        if display_name:
            st.caption(f"已登入：{display_name}")

    if saved_records:
        record_by_id = {
            record["id"]: record for record in saved_records
        }
        st.selectbox(
            "已保存紀錄",
            options=saved_record_ids,
            format_func=lambda record_id: display_record_label(
                record_by_id[record_id]
            ),
            key="record_selector"
        )
        st.session_state.selected_record_id = (
            st.session_state.record_selector
        )
        selected_record = get_record(
            result_library,
            st.session_state.selected_record_id
        )

        if not st.session_state.pin_prompt_open:
            if st.button("檢視選取紀錄", width="stretch"):
                if pin_protection_is_disabled(
                    selected_record["result"].get("pin_protection")
                ):
                    load_saved_into_state(selected_record)
                else:
                    open_pin_prompt(selected_record)
                st.rerun()
        else:
            selected_results = selected_record["result"]
            pin_protection = selected_results.get("pin_protection")

            if not pin_protection_is_enabled(pin_protection):
                st.info("是否要替這份紀錄加上 PIN 保護？")

                with st.form("choose_record_pin_form"):
                    pin_choice = st.radio(
                        "載入方式",
                        ["使用 PIN", "不使用 PIN"],
                        horizontal=True
                    )

                    if pin_choice == "使用 PIN":
                        new_pin = st.text_input(
                            "建立 PIN",
                            type="password",
                            max_chars=8
                        )
                        confirm_pin = st.text_input(
                            "再次輸入 PIN",
                            type="password",
                            max_chars=8
                        )
                    else:
                        new_pin = ""
                        confirm_pin = ""

                    confirm_pin_choice = st.form_submit_button(
                        "確認並載入",
                        type="primary",
                        width="stretch"
                    )

                if confirm_pin_choice:
                    if pin_choice == "不使用 PIN":
                        pin_protection = disabled_pin_protection()
                        save_pin_protection(
                            selected_record,
                            pin_protection
                        )
                        load_saved_into_state(selected_record)
                        close_pin_prompt()
                        st.rerun()
                    else:
                        valid, pin_error = validate_pin(new_pin)

                        if not valid:
                            st.error(pin_error)
                        elif new_pin != confirm_pin:
                            st.error("兩次輸入的 PIN 不一致。")
                        else:
                            pin_protection = create_pin_protection(new_pin)
                            save_pin_protection(
                                selected_record,
                                pin_protection
                            )
                            load_saved_into_state(selected_record)
                            close_pin_prompt()
                            st.rerun()
            else:
                st.caption("請在彈出的數字鍵盤輸入 PIN。")

            if st.button(
                "取消",
                key="cancel_pin_prompt",
                width="stretch"
            ):
                close_pin_prompt()
                st.rerun()

    if st.button("建立新紀錄", width="stretch"):
        reset_app()
        st.rerun()

    if (
        selected_record is not None
        and not guest_mode_enabled()
        and not st.session_state.pin_prompt_open
    ):
        with st.expander("管理選取紀錄"):
            st.caption(display_record_label(selected_record))

            with st.form(
                f"rename_record_form_{selected_record['id']}"
            ):
                renamed_record_title = st.text_input(
                    "紀錄名稱",
                    value=selected_record["title"],
                    max_chars=80,
                    key=f"rename_record_title_{selected_record['id']}"
                )
                rename_record = st.form_submit_button(
                    "更改紀錄名稱",
                    type="primary",
                    width="stretch"
                )

            if rename_record:
                if rename_saved_record(
                    selected_record["id"],
                    renamed_record_title
                ):
                    st.rerun()
                else:
                    st.error("紀錄名稱不能留白。")

            st.divider()
            selected_pin_protection = selected_record["result"].get(
                "pin_protection"
            )
            pin_settings_open = (
                st.session_state.pin_settings_record_id
                == selected_record["id"]
            )

            if pin_protection_is_enabled(selected_pin_protection):
                st.markdown("**🔒 PIN 保護已啟用**")
            else:
                st.markdown("**PIN 保護未啟用**")

            if st.button(
                "收起 PIN 設定" if pin_settings_open else "調整 PIN",
                key=f"toggle_pin_settings_{selected_record['id']}",
                width="stretch"
            ):
                st.session_state.pin_settings_record_id = (
                    None if pin_settings_open else selected_record["id"]
                )
                st.rerun()

            if pin_settings_open:
                if pin_protection_is_enabled(selected_pin_protection):
                    with st.form(
                        f"change_record_pin_form_{selected_record['id']}"
                    ):
                        current_pin_for_change = st.text_input(
                            "目前 PIN",
                            type="password",
                            max_chars=8,
                            key=f"current_pin_change_{selected_record['id']}"
                        )
                        changed_pin = st.text_input(
                            "新 PIN",
                            type="password",
                            max_chars=8,
                            key=f"changed_pin_{selected_record['id']}"
                        )
                        changed_pin_confirm = st.text_input(
                            "再次輸入新 PIN",
                            type="password",
                            max_chars=8,
                            key=(
                                "changed_pin_confirm_"
                                f"{selected_record['id']}"
                            )
                        )
                        change_pin = st.form_submit_button(
                            "更改 PIN",
                            type="primary",
                            width="stretch"
                        )

                    if change_pin:
                        valid, pin_error = validate_pin(changed_pin)

                        if not verify_pin(
                            current_pin_for_change,
                            selected_pin_protection
                        ):
                            st.error("目前 PIN 錯誤。")
                        elif not valid:
                            st.error(pin_error)
                        elif changed_pin != changed_pin_confirm:
                            st.error("兩次輸入的新 PIN 不一致。")
                        else:
                            save_pin_protection(
                                selected_record,
                                create_pin_protection(changed_pin)
                            )
                            st.session_state.pin_settings_record_id = None
                            st.rerun()

                    with st.form(
                        f"disable_record_pin_form_{selected_record['id']}"
                    ):
                        current_pin_for_disable = st.text_input(
                            "目前 PIN（關閉保護）",
                            type="password",
                            max_chars=8,
                            key=(
                                "current_pin_disable_"
                                f"{selected_record['id']}"
                            )
                        )
                        confirm_disable_pin = st.checkbox(
                            "我確定要關閉 PIN 保護",
                            key=(
                                "confirm_disable_pin_"
                                f"{selected_record['id']}"
                            )
                        )
                        disable_pin = st.form_submit_button(
                            "關閉 PIN 保護",
                            disabled=not confirm_disable_pin,
                            width="stretch"
                        )

                    if disable_pin:
                        if verify_pin(
                            current_pin_for_disable,
                            selected_pin_protection
                        ):
                            save_pin_protection(
                                selected_record,
                                disabled_pin_protection()
                            )
                            st.session_state.pin_settings_record_id = None
                            st.rerun()
                        else:
                            st.error("目前 PIN 錯誤，無法關閉保護。")
                else:
                    with st.form(
                        f"enable_record_pin_form_{selected_record['id']}"
                    ):
                        settings_pin = st.text_input(
                            "建立 PIN",
                            type="password",
                            max_chars=8,
                            key=f"enable_pin_{selected_record['id']}"
                        )
                        settings_pin_confirm = st.text_input(
                            "再次輸入 PIN",
                            type="password",
                            max_chars=8,
                            key=(
                                "enable_pin_confirm_"
                                f"{selected_record['id']}"
                            )
                        )
                        enable_pin = st.form_submit_button(
                            "啟用 PIN 保護",
                            type="primary",
                            width="stretch"
                        )

                    if enable_pin:
                        valid, pin_error = validate_pin(settings_pin)

                        if not valid:
                            st.error(pin_error)
                        elif settings_pin != settings_pin_confirm:
                            st.error("兩次輸入的 PIN 不一致。")
                        else:
                            save_pin_protection(
                                selected_record,
                                create_pin_protection(settings_pin)
                            )
                            st.session_state.pin_settings_record_id = None
                            st.rerun()

            st.divider()
            confirm_delete_record = st.checkbox(
                "我確定要刪除這份紀錄"
            )

            if st.button(
                "刪除選取紀錄",
                disabled=not confirm_delete_record,
                width="stretch"
            ):
                delete_saved_record(selected_record["id"])
                reset_app()
                st.rerun()

    if guest_mode_enabled():
        st.divider()
        st.button(
            "結束訪客模式",
            width="stretch",
            on_click=exit_guest_mode
        )
    elif cloud_mode_enabled():
        st.divider()

        with st.expander("帳號與資料"):
            confirm_delete = st.checkbox(
                "我確定要刪除自己的雲端結果"
            )

            if st.button(
                "刪除我的雲端結果",
                width="stretch",
                disabled=not confirm_delete
            ):
                delete_current_results()
                reset_app()
                st.rerun()

        st.button(
            "登出",
            width="stretch",
            on_click=st.logout
        )


if st.session_state.pop("collapse_sidebar_requested", False):
    collapse_sidebar(
        key=f"collapse_sidebar_{st.session_state.editor_version}",
        width=1,
        height=1
    )


pin_unlock_message = st.session_state.pop("pin_unlock_message", None)
if pin_unlock_message:
    st.success(f"✅ {pin_unlock_message}")


if st.session_state.pin_prompt_open:
    pin_prompt_record = get_record(
        result_library,
        st.session_state.pin_prompt_record_id
    )
    if (
        pin_prompt_record is not None
        and pin_protection_is_enabled(
            pin_prompt_record["result"].get("pin_protection")
        )
    ):
        show_pin_keypad(pin_prompt_record)


if st.session_state.stage == "names":
    st.subheader("1. 輸入朋友名單")
    record_title_input = st.text_input(
        "這份紀錄名稱（選填）",
        max_chars=80,
        placeholder="例如：大學朋友"
    )
    raw_names = st.text_area(
        "一行一個名字，也可以用逗號分隔",
        height=180,
        placeholder="Amy\nKevin\nLeo"
    )

    if st.button("開始比較", type="primary", width="stretch"):
        names = parse_names(raw_names)

        if len(names) < 2:
            st.error("至少需要兩個不同的名字。")
        else:
            start_comparison(names, record_title_input)
            st.rerun()


elif st.session_state.stage in ["familiarity", "likability"]:
    question_index = st.session_state.question_index
    person_a, person_b = st.session_state.pairs[question_index]

    is_incremental = (
        st.session_state.comparison_mode == "incremental"
    )

    if st.session_state.stage == "familiarity":
        if is_incremental:
            title = "新增人物：熟悉度比較"
        else:
            title = "2. 熟悉度比較"

        question = st.session_state.display_settings[
            "familiarity_question"
        ]
    else:
        if is_incremental:
            title = "新增人物：好感度比較"
        else:
            title = "3. 好感度比較"

        question = st.session_state.display_settings[
            "likability_question"
        ]

    st.subheader(title)

    st.button(
        "← 回上一題",
        key="undo_comparison_answer",
        disabled=not st.session_state.answer_history,
        on_click=undo_last_answer
    )

    if is_incremental:
        st.info(
            "只會比較包含新人物的組合，舊人物彼此不用重選。"
        )

    answered = st.session_state.stage_answer_count
    estimated_max = max(
        answered + 1,
        st.session_state.stage_question_max
    )
    st.progress(min((answered + 1) / estimated_max, 1.0))
    st.caption(
        f"智慧比較 · 已回答 {answered} 題 · "
        f"此階段最多約 {estimated_max} 題"
    )
    st.markdown(f"### {question}")

    keyboard_result = comparison_keyboard_listener(
        key=f"comparison_keyboard_{st.session_state.stage}_{question_index}",
        on_action_change=ignore_comparison_keyboard_action,
        width="stretch",
        height=44
    )
    keyboard_action = getattr(keyboard_result, "action", None)

    if isinstance(keyboard_action, dict):
        keyboard_event_id = keyboard_action.get("eventId")
        keyboard_choice = keyboard_action.get("choice")

        if (
            keyboard_event_id
            and keyboard_event_id
            != st.session_state.comparison_keyboard_event_id
            and keyboard_choice in (">", "=", "<")
        ):
            st.session_state.comparison_keyboard_event_id = (
                keyboard_event_id
            )
            record_answer(
                keyboard_choice,
                st.session_state.stage,
                question_index
            )
            st.rerun()

    left, middle, right = st.columns(3)

    with left:
        st.button(
            person_a,
            key=f"{st.session_state.stage}-{question_index}-a",
            type="primary",
            width="stretch",
            on_click=record_answer,
            args=(
                ">",
                st.session_state.stage,
                question_index
            )
        )

    with middle:
        st.button(
            "一樣",
            key=f"{st.session_state.stage}-{question_index}-equal",
            width="stretch",
            on_click=record_answer,
            args=(
                "=",
                st.session_state.stage,
                question_index
            )
        )

    with right:
        st.button(
            person_b,
            key=f"{st.session_state.stage}-{question_index}-b",
            type="primary",
            width="stretch",
            on_click=record_answer,
            args=(
                "<",
                st.session_state.stage,
                question_index
            )
        )


elif st.session_state.stage == "results":
    if st.button("← 回到主頁", width="stretch"):
        reset_app()
        st.rerun()

    st.subheader("4. 最終結果")

    if guest_mode_enabled():
        st.info(
            "目前是訪客模式：可繼續查看與編輯本次結果，"
            "但離開後無法載入。"
        )

    if st.session_state.answer_history:
        st.button(
            "← 回上一題",
            key="undo_result_answer",
            on_click=undo_last_answer
        )

    drag_message = st.session_state.pop("drag_message", None)
    edit_message = st.session_state.pop("edit_message", None)

    if drag_message:
        st.toast(drag_message, icon="✅")

    if edit_message:
        st.toast(edit_message, icon="✅")

    with st.container(border=True):
        st.markdown("### ➕ 新增人物")
        raw_new_names = st.text_area(
            "輸入新名字，一行一個或用逗號分隔",
            key="new_names_input",
            height=100,
            placeholder="新朋友"
        )

        if st.button(
            "加入並比較新人物",
            width="stretch"
        ):
            entered_names = parse_names(raw_new_names)
            new_names = [
                name
                for name in entered_names
                if name not in st.session_state.names
            ]

            if not entered_names:
                st.error("請至少輸入一個名字。")
            elif not new_names:
                st.error("輸入的名字都已經在目前名單中。")
            else:
                start_incremental_comparison(new_names)
                st.rerun()

    if not guest_mode_enabled():
        if st.button(
            "儲存目前結果",
            type="primary",
            width="stretch"
        ):
            save_current_results(
                st.session_state.names,
                st.session_state.familiarity_scores,
                st.session_state.likability_scores,
                st.session_state.x_coordinates,
                st.session_state.y_coordinates
            )
            st.success("目前畫面中的結果已保存。")

    ranking = sorted(
        st.session_state.names,
        key=st.session_state.familiarity_scores.get,
        reverse=True
    )

    rows = []

    for name in ranking:
        rows.append(
            {
                "名字": name,
                "熟悉度分數": st.session_state.familiarity_scores[name],
                "好感度分數": st.session_state.likability_scores[name],
                "X 座標": st.session_state.x_coordinates[name],
                "Y 座標": st.session_state.y_coordinates[name]
            }
        )

    st.markdown("### ✏️ 編輯名字與座標")
    st.caption(
        "名字與 X/Y 可以修改；熟悉度與好感度原始分數為唯讀。"
    )

    with st.form("edit_results_form"):
        edited_rows = st.data_editor(
            rows,
            key=(
                "results_editor_"
                f"{st.session_state.editor_version}"
            ),
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            disabled=["熟悉度分數", "好感度分數"],
            column_config={
                "名字": st.column_config.TextColumn(
                    "名字",
                    required=True
                ),
                "熟悉度分數": st.column_config.NumberColumn(
                    "熟悉度分數",
                    disabled=True
                ),
                "好感度分數": st.column_config.NumberColumn(
                    "好感度分數",
                    disabled=True
                ),
                "X 座標": st.column_config.NumberColumn(
                    "X 座標",
                    min_value=-100,
                    max_value=100,
                    step=1,
                    required=True
                ),
                "Y 座標": st.column_config.NumberColumn(
                    "Y 座標",
                    min_value=-100,
                    max_value=100,
                    step=1,
                    required=True
                )
            }
        )

        apply_edits = st.form_submit_button(
            "套用名字與座標修改",
            type="primary",
            width="stretch"
        )

    if apply_edits:
        edit_succeeded, edit_feedback = apply_result_edits(
            ranking,
            edited_rows
        )

        if edit_succeeded:
            st.session_state.edit_message = edit_feedback
            st.rerun()
        else:
            st.error(edit_feedback)

    st.markdown("### 🖐️ 拖曳調整座標")
    st.caption(
        "拖動圓點即可微調 X/Y 座標；停止拖曳 30 秒後自動保存，"
        "也可以按「儲存座標」立即保存。"
        "原始熟悉度與好感度分數不會改變。"
    )

    map_points = [
        {
            "name": name,
            "x": st.session_state.x_coordinates[name],
            "y": st.session_state.y_coordinates[name]
        }
        for name in st.session_state.names
    ]

    draggable_relationship_map(
        data={
            "title": st.session_state.display_settings["app_title"],
            "points": map_points,
            "axisTitles": {
                "x": st.session_state.display_settings["x_axis_title"],
                "y": st.session_state.display_settings["y_axis_title"]
            }
        },
        key="relationship_map_component",
        on_moved_change=apply_dragged_point,
        width="stretch",
        height=660
    )

    with st.expander("查看靜態圖"):
        st.markdown("#### 設定四個象限")
        st.caption("輸入各區名稱並選擇背景色，設定會顯示在下方靜態圖並隨結果保存。")
        quadrant_settings = normalized_quadrant_settings(
            st.session_state.quadrant_settings
        )

        with st.form("quadrant_settings_form"):
            quadrant_inputs = {}
            quadrant_labels = (
                ("top_left", "左上象限"),
                ("top_right", "右上象限"),
                ("bottom_left", "左下象限"),
                ("bottom_right", "右下象限")
            )

            for row in (quadrant_labels[:2], quadrant_labels[2:]):
                columns = st.columns(2)
                for column, (quadrant, label) in zip(columns, row):
                    with column:
                        name = st.text_input(
                            f"{label}名稱",
                            value=quadrant_settings[quadrant]["name"],
                            max_chars=30,
                            key=f"{quadrant}_name"
                        )
                        color = st.color_picker(
                            f"{label}色塊",
                            value=quadrant_settings[quadrant]["color"],
                            key=f"{quadrant}_color"
                        )
                        quadrant_inputs[quadrant] = {
                            "name": name,
                            "color": color
                        }

            apply_quadrants = st.form_submit_button(
                "套用象限設定",
                type="primary",
                width="stretch"
            )

        if apply_quadrants:
            if any(
                not setting["name"].strip()
                for setting in quadrant_inputs.values()
            ):
                st.error("四個象限的名稱都不能留白。")
            else:
                st.session_state.quadrant_settings = (
                    normalized_quadrant_settings(quadrant_inputs)
                )
                save_current_results(
                    st.session_state.names,
                    st.session_state.familiarity_scores,
                    st.session_state.likability_scores,
                    st.session_state.x_coordinates,
                    st.session_state.y_coordinates
                )
                st.toast("象限名稱與色塊已套用並保存。", icon="✅")
                st.rerun()

        figure = make_figure()
        st.pyplot(figure, width="stretch")
        plt.close(figure)

    st.markdown("### 📝 備註與定義")
    st.caption(
        "按表格下方的 ＋ 新增一列；對象可輸入象限、朋友或任何自訂文字。"
        "備註只會顯示在這裡，不會出現在圖表上。"
    )

    quadrant_settings = normalized_quadrant_settings(
        st.session_state.quadrant_settings
    )
    quadrant_labels = {
        f"象限｜{setting['name']}": quadrant
        for quadrant, setting in quadrant_settings.items()
    }
    friend_labels = {
        f"朋友｜{name}": name
        for name in st.session_state.names
    }
    stored_annotations = normalized_annotations(
        st.session_state.annotations
    )
    annotation_rows = []

    for annotation in stored_annotations:
        if annotation["target_type"] == "quadrant":
            target_label = next(
                (
                    label
                    for label, quadrant in quadrant_labels.items()
                    if quadrant == annotation["target_id"]
                ),
                None
            )
        elif annotation["target_type"] == "friend":
            target_label = next(
                (
                    label
                    for label, friend in friend_labels.items()
                    if friend == annotation["target_id"]
                ),
                None
            )
        else:
            target_label = annotation["target_id"]

        if target_label:
            annotation_rows.append(
                {"對象": target_label, "備註／定義": annotation["note"]}
            )

    annotation_editor_data = annotation_rows or [
        {"對象": None, "備註／定義": ""}
    ]

    with st.form("annotations_form"):
        edited_annotations = st.data_editor(
            annotation_editor_data,
            key=f"annotations_editor_{st.session_state.editor_version}",
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "對象": st.column_config.TextColumn(
                    "對象",
                    required=True,
                    max_chars=80,
                    help="可輸入象限、朋友或任何自訂文字"
                ),
                "備註／定義": st.column_config.TextColumn(
                    "備註／定義",
                    required=True,
                    max_chars=500
                )
            }
        )
        save_annotations = st.form_submit_button(
            "保存備註",
            type="primary",
            width="stretch"
        )

    if save_annotations:
        if hasattr(edited_annotations, "to_dict"):
            edited_annotation_rows = edited_annotations.to_dict("records")
        else:
            edited_annotation_rows = list(edited_annotations)

        new_annotations = []
        invalid_annotation = False
        for row in edited_annotation_rows:
            target = str(row.get("對象", "")).strip()
            note = str(row.get("備註／定義", "")).strip()
            if not target or not note:
                invalid_annotation = True
                break

            if target in quadrant_labels:
                target_type = "quadrant"
                target_id = quadrant_labels[target]
            elif target in friend_labels:
                target_type = "friend"
                target_id = friend_labels[target]
            else:
                target_type = "custom"
                target_id = target

            new_annotations.append(
                {
                    "target_type": target_type,
                    "target_id": target_id,
                    "note": note
                }
            )

        if invalid_annotation:
            st.error("每一列都需要選擇對象並填寫備註。")
        else:
            st.session_state.annotations = normalized_annotations(
                new_annotations
            )
            save_current_results(
                st.session_state.names,
                st.session_state.familiarity_scores,
                st.session_state.likability_scores,
                st.session_state.x_coordinates,
                st.session_state.y_coordinates
            )
            st.session_state.editor_version += 1
            st.toast("備註已保存。", icon="✅")
            st.rerun()
