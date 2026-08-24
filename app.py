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
from notes_editor import notes_editor
from i18n import ENGLISH_TRANSLATIONS, language, t, tf
from result_library import (
    default_record_title,
    delete_record as remove_record_from_library,
    get_record,
    get_preferred_language,
    normalize_library,
    record_label,
    set_preferred_language,
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


if "language" not in st.session_state:
    st.session_state.language = "en"

if "language_preference_loaded" not in st.session_state:
    st.session_state.language_preference_loaded = False

if "language_preference_owner_id" not in st.session_state:
    st.session_state.language_preference_owner_id = None

if "language_preference_pending" not in st.session_state:
    st.session_state.language_preference_pending = False


st.set_page_config(
    page_title=t("人際關係座標圖"),
    page_icon=str(APP_DIRECTORY / "static" / "app-icon-512.png"),
    layout="centered"
)

st.markdown(
    """
    <style>
    .st-key-author_info_login,
    .st-key-author_info_main {
        position: fixed;
        right: 1.5rem;
        top: 5rem;
        width: auto;
        z-index: 999;
    }
    .st-key-author_info_login button,
    .st-key-author_info_main button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        min-height: 2rem !important;
        padding: 0.1rem 0.25rem !important;
    }
    .st-key-author_info_login button:hover,
    .st-key-author_info_main button:hover {
        background: transparent !important;
        border: none !important;
    }
    @media (max-width: 640px) {
        .st-key-author_info_login,
        .st-key-author_info_main {
            right: 0.75rem;
            top: 4.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
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

AUTHOR_NOTES = {
    "zh": """好的朋友，能夠支持你走過人生中困難的時刻；但一段不好的關係，也可能輕易消耗掉大量的時間與精神。生活中，我們會遇到許多來來去去的過客，每個人都有自己獨特的地方。然而，人的時間與精力終究是有限的，因此我們應該時常思考身邊不同的人對自己的重要性，以及彼此之間的真誠度、信任程度、合作性和能夠帶來的支持。

這個工具正是希望幫助我們將平時累積的經驗與認知具象化，進一步量化並記錄下來。它的目的並不是單純替身邊的人評分，而是把原本模糊、散落在記憶中的感受整理成可以重新檢視的資訊，降低我們記憶這些抽象資訊的負擔。同時，也可以透過圖表定期回顧自己的判斷，反思自己的行為、想法與真正重視的事情是否一致。

事實上，這樣的方法並不只適用於朋友或人際關係。生活中的許多事情，例如餐廳的排名、飯店的品質，甚至家具的性價比，都可以利用這種雙軸圖表來整理，讓原本模糊的感受與認知變得更加清晰。這個工具對我來說非常實用，也希望它能幫助大家更有系統地整理自己的經驗與想法。""",
    "en": """Good relationships can make life easier, while bad ones can take up a surprising amount of time and energy. Since our attention is limited, it can be useful to step back and think more clearly about the people around us, including how much we trust them, how supportive they are, and how well we work together.

This tool helps turn those scattered impressions into something more concrete. Instead of keeping everything in your head, you can record and visualize your own experiences over time. The goal is not to reduce people to a score, but to make your thinking easier to review and reflect on.

The same idea can also be applied to things beyond relationships. Restaurants, hotels, furniture, or almost anything with multiple factors can be compared using a simple two axis chart. I find this approach useful for organizing subjective opinions and making them easier to understand, and I hope you will too."""
}

AUTHOR_NOTE_TITLES = {
    "zh": "作者的話",
    "en": "A Note from the Creator"
}


def show_author_note_dialog():
    @st.dialog(AUTHOR_NOTE_TITLES[language()], width="large")
    def author_note_dialog():
        st.markdown(AUTHOR_NOTES[language()])

    author_note_dialog()


def show_author_note_button(container_key):
    with st.container(key=container_key):
        if st.button(
            "ⓘ",
            key=f"{container_key}_button",
            help=t("閱讀作者的話")
        ):
            show_author_note_dialog()


def normalized_display_settings(settings=None):
    normalized = dict(DEFAULT_DISPLAY_SETTINGS)

    if isinstance(settings, dict):
        for key in normalized:
            value = str(settings.get(key, "")).strip()
            if value:
                normalized[key] = value[:80]

    return normalized


def localized_display_settings(settings=None):
    localized = normalized_display_settings(settings)

    for key, chinese_default in DEFAULT_DISPLAY_SETTINGS.items():
        english_default = ENGLISH_TRANSLATIONS[chinese_default]
        if localized[key] in {chinese_default, english_default}:
            localized[key] = (
                english_default if language() == "en" else chinese_default
            )

    return localized


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


def localized_quadrant_settings(settings=None):
    localized = normalized_quadrant_settings(settings)

    for quadrant, defaults in DEFAULT_QUADRANT_SETTINGS.items():
        chinese_default = defaults["name"]
        english_default = ENGLISH_TRANSLATIONS[chinese_default]
        if localized[quadrant]["name"] in {
            chinese_default,
            english_default
        }:
            localized[quadrant]["name"] = (
                english_default if language() == "en" else chinese_default
            )

    return localized


def toggle_language():
    st.session_state.language = "zh" if language() == "en" else "en"
    st.session_state.language_preference_pending = True
    if "editor_version" in st.session_state:
        st.session_state.editor_version += 1


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
        raise RuntimeError(t("登入資料中找不到使用者 ID。"))

    return sha256(subject.encode("utf-8")).hexdigest()


def cloud_credentials():
    settings = secret_section("supabase")
    url = str(settings.get("url", "")).strip()
    service_key = str(settings.get("service_key", "")).strip()

    if not url or not service_key:
        raise RuntimeError(t("尚未設定 Supabase 網址或 service key。"))

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
    selected_language = language()

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    if preserve_access_mode and was_guest:
        st.session_state.guest_mode = True

    st.session_state.language = selected_language


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

def values_for_new_groups(groups, existing_values, new_names, bounds=None):
    """Interpolate values for new people without changing old people."""
    new_name_set = set(new_names)
    anchors = []

    for index, group in enumerate(groups):
        old_values = [
            existing_values[name]
            for name in group
            if name not in new_name_set
        ]
        if old_values:
            anchors.append((index, sum(old_values) / len(old_values)))

    if not anchors:
        return {name: 0 for name in new_names}

    group_values = {index: value for index, value in anchors}

    for (left_index, left_value), (right_index, right_value) in zip(
        anchors,
        anchors[1:]
    ):
        distance = right_index - left_index
        for index in range(left_index + 1, right_index):
            progress = (index - left_index) / distance
            group_values[index] = (
                left_value + (right_value - left_value) * progress
            )

    first_index, first_value = anchors[0]
    last_index, last_value = anchors[-1]

    if bounds is not None:
        lower_bound, upper_bound = bounds
        for index in range(first_index):
            progress = (index + 1) / (first_index + 1)
            group_values[index] = (
                upper_bound + (first_value - upper_bound) * progress
            )

        trailing_count = len(groups) - last_index - 1
        for offset, index in enumerate(
            range(last_index + 1, len(groups)),
            start=1
        ):
            progress = offset / (trailing_count + 1)
            group_values[index] = (
                last_value + (lower_bound - last_value) * progress
            )
    else:
        slopes = [
            abs((right_value - left_value) / (right_index - left_index))
            for (left_index, left_value), (right_index, right_value) in zip(
                anchors,
                anchors[1:]
            )
            if right_index != left_index and right_value != left_value
        ]
        step = max(1, sum(slopes) / len(slopes)) if slopes else 1

        for index in range(first_index - 1, -1, -1):
            group_values[index] = first_value + step * (
                first_index - index
            )
        for index in range(last_index + 1, len(groups)):
            group_values[index] = last_value - step * (
                index - last_index
            )

    assigned = {}
    for index, group in enumerate(groups):
        value = round(group_values[index])
        for name in group:
            if name in new_name_set:
                assigned[name] = value

    return assigned


def apply_incremental_ranking(stage):
    """Assign only new scores and coordinates from the fixed old scale."""
    if stage == "familiarity":
        scores = st.session_state.familiarity_scores
        coordinates = st.session_state.x_coordinates
    else:
        scores = st.session_state.likability_scores
        coordinates = st.session_state.y_coordinates

    scores.update(
        values_for_new_groups(
            st.session_state.adaptive_groups,
            scores,
            st.session_state.new_names
        )
    )
    coordinates.update(
        values_for_new_groups(
            st.session_state.adaptive_groups,
            coordinates,
            st.session_state.new_names,
            bounds=(-100, 100)
        )
    )


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

    if st.session_state.comparison_mode == "incremental":
        apply_incremental_ranking(stage)
    else:
        apply_fast_ranking_to_scores(stage)

    if stage == "familiarity":
        begin_fast_stage("likability")
        return

    if st.session_state.comparison_mode != "incremental":
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
    st.session_state.pin_unlock_message = tf(
        "PIN 正確，已載入「{title}」。",
        title=record["title"]
    )
    st.session_state.collapse_sidebar_requested = True


def try_unlock_record(record, entered_pin):
    pin_protection = record["result"].get("pin_protection")

    if verify_pin(entered_pin, pin_protection):
        complete_pin_unlock(record, entered_pin, pin_protection)
        return True

    st.session_state.pin_keypad_value = ""
    st.session_state.pin_keypad_error = t("PIN 錯誤，請再試一次。")
    return False


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
    t("輸入紀錄 PIN"),
    width="small",
    icon="🔒",
    on_dismiss=close_pin_prompt
)
def show_pin_keypad(record):
    st.caption(record["title"])
    st.caption(t("可點擊下方鍵盤，或直接使用電腦數字鍵輸入。"))

    pin_protection = record["result"].get("pin_protection")
    expected_pin_length = (
        pin_protection.get("length")
        if isinstance(pin_protection, dict)
        else None
    )
    if st.session_state.pin_keypad_error:
        st.error(t(st.session_state.pin_keypad_error))

    keyboard_result = pin_keyboard_listener(
        data={
            "currentPin": st.session_state.pin_keypad_value,
            "expectedLength": expected_pin_length,
            "language": language()
        },
        key=f"pin_keyboard_{record['id']}",
        on_action_change=ignore_pin_keyboard_action,
        width="stretch",
        height=350
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
                        t("PIN 只能輸入數字。")
                    )
                    st.rerun(scope="fragment")
                if confirm_keypad_pin(record):
                    st.rerun(scope="app")
                st.rerun(scope="fragment")
            elif action_type == "cancel":
                close_pin_prompt()
                st.rerun(scope="app")


def apply_result_edits(ranking, edited_data):
    if hasattr(edited_data, "to_dict"):
        edited_rows = edited_data.to_dict("records")
    else:
        edited_rows = list(edited_data)

    if len(edited_rows) != len(ranking):
        return False, t("表格資料不完整，請重新整理後再試。")

    rename_map = {}
    edited_coordinates = {}
    new_names = []

    for old_name, row in zip(ranking, edited_rows):
        new_name = str(row.get(t("名字"), "")).strip()

        if not new_name:
            return False, t("名字不能是空白。")

        if new_name in new_names:
            return False, tf("名字「{name}」重複了。", name=new_name)

        try:
            x = float(row[t("X 座標")])
            y = float(row[t("Y 座標")])
        except (KeyError, TypeError, ValueError):
            return False, tf(
                "{name} 的座標必須是數字。",
                name=new_name
            )

        if not math.isfinite(x) or not math.isfinite(y):
            return False, tf(
                "{name} 的座標必須是有效數字。",
                name=new_name
            )

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
    return True, t("名字與座標已更新並保存。")


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
        st.session_state.drag_message = tf(
            "{name} 的座標已更新為 ({x}, {y})",
            name=name,
            x=x,
            y=y
        )
    else:
        st.session_state.drag_message = tf(
            "已更新並保存 {count} 個人物的座標",
            count=len(applied_points)
        )
    st.session_state.editor_version += 1


def apply_saved_annotations():
    component_result = st.session_state.get("notes_editor_component")
    saved = getattr(component_result, "saved", None)
    rows = saved.get("rows") if isinstance(saved, dict) else None
    if not isinstance(rows, list):
        return

    annotations = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        note = str(row.get("note", "")).strip()
        if row.get("mode") == "custom":
            target_type = "custom"
            target_id = str(row.get("custom", "")).strip()
        else:
            target_type, separator, target_id = str(
                row.get("target", "")
            ).partition(":")
            if not separator:
                continue

        if target_type not in {"quadrant", "friend", "custom"}:
            continue
        if not target_id or not note:
            continue
        annotations.append(
            {
                "target_type": target_type,
                "target_id": target_id,
                "note": note
            }
        )

    st.session_state.annotations = normalized_annotations(annotations)
    save_current_results(
        st.session_state.names,
        st.session_state.familiarity_scores,
        st.session_state.likability_scores,
        st.session_state.x_coordinates,
        st.session_state.y_coordinates
    )
    st.session_state.annotation_message = t("備註已保存。")


def make_figure():
    plt.rcParams["axes.unicode_minus"] = False

    figure, axis = plt.subplots(figsize=(8, 8))
    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")
    quadrants = localized_quadrant_settings(
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
    settings = localized_display_settings(
        st.session_state.display_settings
    )
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
    show_author_note_button("author_info_login")
    _, login_language_column = st.columns([0.78, 0.22])
    with login_language_column:
        st.button(
            "中文" if language() == "en" else "English",
            key="login_language_toggle",
            width="stretch",
            on_click=toggle_language
        )
    st.title(t("🗺️ 人際關係座標圖"))
    st.write(t("登入可保存並載入自己的結果；也可以不登入單次使用。"))
    st.button(
        t("使用 Google 登入"),
        type="primary",
        width="stretch",
        on_click=st.login
    )
    st.button(
        t("以訪客身分使用"),
        width="stretch",
        on_click=start_guest_mode
    )
    st.caption(t("訪客結果不會儲存，離開後無法載入。"))
    st.stop()


initialize_state()

try:
    stored_results = load_current_results()
except Exception as error:
    st.error(t("目前無法連接私人資料庫，請稍後再試。"))
    st.exception(error)
    st.stop()

result_library = normalize_library(stored_results)

if (
    cloud_mode_enabled()
    and user_is_logged_in()
    and not guest_mode_enabled()
):
    preference_owner_id = current_owner_id()
    preference_needs_loading = (
        not st.session_state.language_preference_loaded
        or st.session_state.language_preference_owner_id
        != preference_owner_id
    )

    if preference_needs_loading:
        preferred_language = (
            get_preferred_language(result_library) or "en"
        )
        language_changed = preferred_language != language()
        st.session_state.language = preferred_language
        st.session_state.language_preference_loaded = True
        st.session_state.language_preference_owner_id = (
            preference_owner_id
        )
        st.session_state.language_preference_pending = False

        if language_changed:
            st.rerun()
    elif st.session_state.language_preference_pending:
        result_library = set_preferred_language(
            result_library,
            language()
        )
        persist_result_library(result_library)
        st.session_state.language_preference_pending = False
else:
    st.session_state.language_preference_loaded = True
    st.session_state.language_preference_owner_id = None
    st.session_state.language_preference_pending = False

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

show_author_note_button("author_info_main")

title_column, language_column, settings_column = st.columns(
    [0.68, 0.20, 0.12],
    vertical_alignment="center"
)

visible_display_settings = localized_display_settings(
    st.session_state.display_settings
)

with title_column:
    st.title(f"🗺️ {visible_display_settings['app_title']}")

with language_column:
    st.button(
        "中文" if language() == "en" else "English",
        key="language_toggle",
        width="stretch",
        on_click=toggle_language
    )


with settings_column:
    with st.popover("⚙️", help=t("自訂標題與問題文字")):
        st.markdown(t("#### 自訂文字"))
        current_settings = visible_display_settings

        with st.form("display_settings_form"):
            custom_app_title = st.text_input(
                t("畫面標題"),
                value=current_settings["app_title"],
                max_chars=80
            )
            custom_familiarity_question = st.text_input(
                t("第一組選擇題"),
                value=current_settings["familiarity_question"],
                max_chars=80
            )
            custom_x_axis_title = st.text_input(
                t("X 軸標題"),
                value=current_settings["x_axis_title"],
                max_chars=80
            )
            custom_likability_question = st.text_input(
                t("第二組選擇題"),
                value=current_settings["likability_question"],
                max_chars=80
            )
            custom_y_axis_title = st.text_input(
                t("Y 軸標題"),
                value=current_settings["y_axis_title"],
                max_chars=80
            )

            save_custom_text = st.form_submit_button(
                t("套用文字"),
                type="primary",
                width="stretch"
            )
            restore_default_text = st.form_submit_button(
                t("恢復預設"),
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
                st.error(t("文字欄位不能留白。"))
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

st.caption(t("用兩兩比較，把朋友放進熟悉度與好感度座標。"))

with st.sidebar:
    st.subheader(t("選單"))

    if guest_mode_enabled():
        st.caption(t("訪客模式：結果不會儲存"))
    elif cloud_mode_enabled():
        display_name = st.user.get("name") or st.user.get("email")
        if display_name:
            st.caption(tf("已登入：{name}", name=display_name))

    if saved_records:
        record_by_id = {
            record["id"]: record for record in saved_records
        }
        st.selectbox(
            t("已保存紀錄"),
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
            if st.button(t("檢視選取紀錄"), width="stretch"):
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
                st.info(t("是否要替這份紀錄加上 PIN 保護？"))

                with st.form("choose_record_pin_form"):
                    pin_choice = st.radio(
                        t("載入方式"),
                        [t("使用 PIN"), t("不使用 PIN")],
                        horizontal=True
                    )

                    if pin_choice == t("使用 PIN"):
                        new_pin = st.text_input(
                            t("建立 PIN"),
                            type="password",
                            max_chars=8
                        )
                        confirm_pin = st.text_input(
                            t("再次輸入 PIN"),
                            type="password",
                            max_chars=8
                        )
                    else:
                        new_pin = ""
                        confirm_pin = ""

                    confirm_pin_choice = st.form_submit_button(
                        t("確認並載入"),
                        type="primary",
                        width="stretch"
                    )

                if confirm_pin_choice:
                    if pin_choice == t("不使用 PIN"):
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
                            st.error(t(pin_error))
                        elif new_pin != confirm_pin:
                            st.error(t("兩次輸入的 PIN 不一致。"))
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
                st.caption(t("請在彈出的數字鍵盤輸入 PIN。"))

            if st.button(
                t("取消"),
                key="cancel_pin_prompt",
                width="stretch"
            ):
                close_pin_prompt()
                st.rerun()

    if st.button(t("建立新紀錄"), width="stretch"):
        reset_app()
        st.rerun()

    if (
        selected_record is not None
        and not guest_mode_enabled()
        and not st.session_state.pin_prompt_open
    ):
        with st.expander(t("管理選取紀錄")):
            st.caption(display_record_label(selected_record))

            with st.form(
                f"rename_record_form_{selected_record['id']}"
            ):
                renamed_record_title = st.text_input(
                    t("紀錄名稱"),
                    value=selected_record["title"],
                    max_chars=80,
                    key=f"rename_record_title_{selected_record['id']}"
                )
                rename_record = st.form_submit_button(
                    t("更改紀錄名稱"),
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
                    st.error(t("紀錄名稱不能留白。"))

            st.divider()
            selected_pin_protection = selected_record["result"].get(
                "pin_protection"
            )
            pin_settings_open = (
                st.session_state.pin_settings_record_id
                == selected_record["id"]
            )

            if pin_protection_is_enabled(selected_pin_protection):
                st.markdown(t("**🔒 PIN 保護已啟用**"))
            else:
                st.markdown(t("**PIN 保護未啟用**"))

            if st.button(
                t("收起 PIN 設定") if pin_settings_open else t("調整 PIN"),
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
                            t("目前 PIN"),
                            type="password",
                            max_chars=8,
                            key=f"current_pin_change_{selected_record['id']}"
                        )
                        changed_pin = st.text_input(
                            t("新 PIN"),
                            type="password",
                            max_chars=8,
                            key=f"changed_pin_{selected_record['id']}"
                        )
                        changed_pin_confirm = st.text_input(
                            t("再次輸入新 PIN"),
                            type="password",
                            max_chars=8,
                            key=(
                                "changed_pin_confirm_"
                                f"{selected_record['id']}"
                            )
                        )
                        change_pin = st.form_submit_button(
                            t("更改 PIN"),
                            type="primary",
                            width="stretch"
                        )

                    if change_pin:
                        valid, pin_error = validate_pin(changed_pin)

                        if not verify_pin(
                            current_pin_for_change,
                            selected_pin_protection
                        ):
                            st.error(t("目前 PIN 錯誤。"))
                        elif not valid:
                            st.error(t(pin_error))
                        elif changed_pin != changed_pin_confirm:
                            st.error(t("兩次輸入的新 PIN 不一致。"))
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
                            t("目前 PIN（關閉保護）"),
                            type="password",
                            max_chars=8,
                            key=(
                                "current_pin_disable_"
                                f"{selected_record['id']}"
                            )
                        )
                        confirm_disable_pin = st.checkbox(
                            t("我確定要關閉 PIN 保護"),
                            key=(
                                "confirm_disable_pin_"
                                f"{selected_record['id']}"
                            )
                        )
                        disable_pin = st.form_submit_button(
                            t("關閉 PIN 保護"),
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
                            st.error(t("目前 PIN 錯誤，無法關閉保護。"))
                else:
                    with st.form(
                        f"enable_record_pin_form_{selected_record['id']}"
                    ):
                        settings_pin = st.text_input(
                            t("建立 PIN"),
                            type="password",
                            max_chars=8,
                            key=f"enable_pin_{selected_record['id']}"
                        )
                        settings_pin_confirm = st.text_input(
                            t("再次輸入 PIN"),
                            type="password",
                            max_chars=8,
                            key=(
                                "enable_pin_confirm_"
                                f"{selected_record['id']}"
                            )
                        )
                        enable_pin = st.form_submit_button(
                            t("啟用 PIN 保護"),
                            type="primary",
                            width="stretch"
                        )

                    if enable_pin:
                        valid, pin_error = validate_pin(settings_pin)

                        if not valid:
                            st.error(t(pin_error))
                        elif settings_pin != settings_pin_confirm:
                            st.error(t("兩次輸入的 PIN 不一致。"))
                        else:
                            save_pin_protection(
                                selected_record,
                                create_pin_protection(settings_pin)
                            )
                            st.session_state.pin_settings_record_id = None
                            st.rerun()

            st.divider()
            confirm_delete_record = st.checkbox(
                t("我確定要刪除這份紀錄")
            )

            if st.button(
                t("刪除選取紀錄"),
                disabled=not confirm_delete_record,
                width="stretch"
            ):
                delete_saved_record(selected_record["id"])
                reset_app()
                st.rerun()

    if guest_mode_enabled():
        st.divider()
        st.button(
            t("結束訪客模式"),
            width="stretch",
            on_click=exit_guest_mode
        )
    elif cloud_mode_enabled():
        st.divider()

        with st.expander(t("帳號與資料")):
            confirm_delete = st.checkbox(
                t("我確定要刪除自己的雲端結果")
            )

            if st.button(
                t("刪除我的雲端結果"),
                width="stretch",
                disabled=not confirm_delete
            ):
                delete_current_results()
                reset_app()
                st.rerun()

        st.button(
            t("登出"),
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
    st.subheader(t("1. 輸入朋友名單"))
    record_title_input = st.text_input(
        t("這份紀錄名稱（選填）"),
        max_chars=80,
        placeholder=t("例如：大學朋友")
    )
    raw_names = st.text_area(
        t("一行一個名字，也可以用逗號分隔"),
        height=180,
        placeholder="Amy\nKevin\nLeo"
    )

    if st.button(t("開始比較"), type="primary", width="stretch"):
        names = parse_names(raw_names)

        if len(names) < 2:
            st.error(t("至少需要兩個不同的名字。"))
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
            title = t("新增人物：熟悉度比較")
        else:
            title = t("2. 熟悉度比較")

        question = visible_display_settings["familiarity_question"]
    else:
        if is_incremental:
            title = t("新增人物：好感度比較")
        else:
            title = t("3. 好感度比較")

        question = visible_display_settings["likability_question"]

    st.subheader(title)

    st.button(
        t("← 回上一題"),
        key="undo_comparison_answer",
        disabled=not st.session_state.answer_history,
        on_click=undo_last_answer
    )

    if is_incremental:
        st.info(
            t("只會比較包含新人物的組合，舊人物彼此不用重選。")
        )

    answered = st.session_state.stage_answer_count
    estimated_max = max(
        answered + 1,
        st.session_state.stage_question_max
    )
    st.progress(min((answered + 1) / estimated_max, 1.0))
    st.caption(
        tf(
            "智慧比較 · 已回答 {answered} 題 · "
            "此階段最多約 {maximum} 題",
            answered=answered,
            maximum=estimated_max
        )
    )
    st.markdown(f"### {question}")

    keyboard_result = comparison_keyboard_listener(
        data={"language": language()},
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
            t("一樣"),
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
    if st.button(t("← 回到主頁"), width="stretch"):
        reset_app()
        st.rerun()

    st.subheader(t("4. 最終結果"))

    if guest_mode_enabled():
        st.info(
            t("目前是訪客模式：可繼續查看與編輯本次結果，"
            "但離開後無法載入。")
        )

    if st.session_state.answer_history:
        st.button(
            t("← 回上一題"),
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
        st.markdown(t("### ➕ 新增人物"))
        raw_new_names = st.text_area(
            t("輸入新名字，一行一個或用逗號分隔"),
            key="new_names_input",
            height=100,
            placeholder=t("新朋友")
        )

        if st.button(
            t("加入並比較新人物"),
            width="stretch"
        ):
            entered_names = parse_names(raw_new_names)
            new_names = [
                name
                for name in entered_names
                if name not in st.session_state.names
            ]

            if not entered_names:
                st.error(t("請至少輸入一個名字。"))
            elif not new_names:
                st.error(t("輸入的名字都已經在目前名單中。"))
            else:
                start_incremental_comparison(new_names)
                st.rerun()

    if not guest_mode_enabled():
        if st.button(
            t("儲存目前結果"),
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
            st.success(t("目前畫面中的結果已保存。"))

    ranking = sorted(
        st.session_state.names,
        key=st.session_state.familiarity_scores.get,
        reverse=True
    )

    rows = []

    for name in ranking:
        rows.append(
            {
                t("名字"): name,
                t("熟悉度分數"): st.session_state.familiarity_scores[name],
                t("好感度分數"): st.session_state.likability_scores[name],
                t("X 座標"): st.session_state.x_coordinates[name],
                t("Y 座標"): st.session_state.y_coordinates[name]
            }
        )

    st.markdown(t("### ✏️ 編輯名字與座標"))
    st.caption(
        t("名字與 X/Y 可以修改；熟悉度與好感度原始分數為唯讀。")
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
            disabled=[t("熟悉度分數"), t("好感度分數")],
            column_config={
                t("名字"): st.column_config.TextColumn(
                    t("名字"),
                    required=True
                ),
                t("熟悉度分數"): st.column_config.NumberColumn(
                    t("熟悉度分數"),
                    disabled=True
                ),
                t("好感度分數"): st.column_config.NumberColumn(
                    t("好感度分數"),
                    disabled=True
                ),
                t("X 座標"): st.column_config.NumberColumn(
                    t("X 座標"),
                    min_value=-100,
                    max_value=100,
                    step=1,
                    required=True
                ),
                t("Y 座標"): st.column_config.NumberColumn(
                    t("Y 座標"),
                    min_value=-100,
                    max_value=100,
                    step=1,
                    required=True
                )
            }
        )

        apply_edits = st.form_submit_button(
            t("套用名字與座標修改"),
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

    st.markdown(t("### 🖐️ 拖曳調整座標"))
    st.caption(
        t("拖動圓點即可微調 X/Y 座標；停止拖曳 30 秒後自動保存，"
        "也可以按「儲存座標」立即保存。"
        "原始熟悉度與好感度分數不會改變。")
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
            "language": language(),
            "title": visible_display_settings["app_title"],
            "points": map_points,
            "axisTitles": {
                "x": visible_display_settings["x_axis_title"],
                "y": visible_display_settings["y_axis_title"]
            }
        },
        key="relationship_map_component",
        on_moved_change=apply_dragged_point,
        width="stretch",
        height=660
    )

    with st.expander(t("查看靜態圖")):
        st.markdown(t("#### 設定四個象限"))
        st.caption(t("輸入各區名稱並選擇背景色，設定會顯示在下方靜態圖並隨結果保存。"))
        quadrant_settings = localized_quadrant_settings(
            st.session_state.quadrant_settings
        )

        with st.form("quadrant_settings_form"):
            quadrant_inputs = {}
            quadrant_labels = (
                ("top_left", t("左上象限")),
                ("top_right", t("右上象限")),
                ("bottom_left", t("左下象限")),
                ("bottom_right", t("右下象限"))
            )

            for row in (quadrant_labels[:2], quadrant_labels[2:]):
                columns = st.columns(2)
                for column, (quadrant, label) in zip(columns, row):
                    with column:
                        name = st.text_input(
                            f"{label}{t('名稱')}",
                            value=quadrant_settings[quadrant]["name"],
                            max_chars=30,
                            key=f"{quadrant}_name"
                        )
                        color = st.color_picker(
                            f"{label}{t('色塊')}",
                            value=quadrant_settings[quadrant]["color"],
                            key=f"{quadrant}_color"
                        )
                        quadrant_inputs[quadrant] = {
                            "name": name,
                            "color": color
                        }

            apply_quadrants = st.form_submit_button(
                t("套用象限設定"),
                type="primary",
                width="stretch"
            )

        if apply_quadrants:
            if any(
                not setting["name"].strip()
                for setting in quadrant_inputs.values()
            ):
                st.error(t("四個象限的名稱都不能留白。"))
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
                st.toast(t("象限名稱與色塊已套用並保存。"), icon="✅")
                st.rerun()

        figure = make_figure()
        st.pyplot(figure, width="stretch")
        plt.close(figure)

    st.markdown(t("### 📝 備註與定義"))
    st.caption(
        t("按 ＋ 新增；「自訂」會在同一格切換成文字輸入。"
        "將滑鼠移到資料列上即可看到左側的 － 刪除按鈕。")
    )
    annotation_message = st.session_state.pop("annotation_message", None)
    if annotation_message:
        st.toast(annotation_message, icon="✅")

    quadrant_settings = localized_quadrant_settings(
        st.session_state.quadrant_settings
    )
    note_options = [{"value": "custom", "label": t("自訂")}]
    note_options.extend(
        {
            "value": f"quadrant:{quadrant}",
            "label": f"{t('象限｜')}{setting['name']}"
        }
        for quadrant, setting in quadrant_settings.items()
    )
    note_options.extend(
        {"value": f"friend:{name}", "label": f"{t('朋友｜')}{name}"}
        for name in st.session_state.names
    )
    note_rows = []
    for annotation in normalized_annotations(st.session_state.annotations):
        if annotation["target_type"] == "custom":
            note_rows.append(
                {
                    "mode": "custom",
                    "target": "",
                    "custom": annotation["target_id"],
                    "note": annotation["note"]
                }
            )
        else:
            note_rows.append(
                {
                    "mode": "option",
                    "target": (
                        f"{annotation['target_type']}:"
                        f"{annotation['target_id']}"
                    ),
                    "custom": "",
                    "note": annotation["note"]
                }
            )

    notes_editor(
        data={
            "language": language(),
            "options": note_options,
            "rows": note_rows
        },
        key="notes_editor_component",
        on_saved_change=apply_saved_annotations,
        width="stretch",
        height=420
    )
