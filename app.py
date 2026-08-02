import math
import random
import re
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

APP_DIRECTORY = Path(__file__).resolve().parent

if str(APP_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(APP_DIRECTORY))

from friendship import (
    load_results as load_local_results,
    normalize_scores,
    save_results as save_local_results
)
from cloud_store import (
    delete_cloud_results,
    load_cloud_results,
    save_cloud_results
)
from draggable_map import draggable_relationship_map


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


def normalized_display_settings(settings=None):
    normalized = dict(DEFAULT_DISPLAY_SETTINGS)

    if isinstance(settings, dict):
        for key in normalized:
            value = str(settings.get(key, "")).strip()
            if value:
                normalized[key] = value[:80]

    return normalized


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
    display_settings
):
    return {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "names": names,
        "familiarity_scores": familiarity_scores,
        "likability_scores": likability_scores,
        "x_coordinates": x_coordinates,
        "y_coordinates": y_coordinates,
        "display_settings": normalized_display_settings(display_settings)
    }


def save_current_results(
    names,
    familiarity_scores,
    likability_scores,
    x_coordinates,
    y_coordinates
):
    if guest_mode_enabled():
        return

    if not cloud_mode_enabled():
        save_local_results(
            names,
            familiarity_scores,
            likability_scores,
            x_coordinates,
            y_coordinates,
            display_settings=st.session_state.display_settings
        )
        return

    url, service_key = cloud_credentials()
    save_cloud_results(
        url,
        service_key,
        current_owner_id(),
        build_result_data(
            names,
            familiarity_scores,
            likability_scores,
            x_coordinates,
            y_coordinates,
            st.session_state.display_settings
        )
    )


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
        return

    url, service_key = cloud_credentials()
    delete_cloud_results(
        url,
        service_key,
        current_owner_id()
    )


def initialize_state():
    defaults = {
        "stage": "names",
        "names": [],
        "pairs": [],
        "question_index": 0,
        "answer_history": [],
        "guest_mode": False,
        "display_settings": normalized_display_settings(),
        "display_settings_loaded": False,
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


def make_pairs(names):
    pairs = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs.append((names[i], names[j]))

    random.shuffle(pairs)
    return pairs


def make_incremental_pairs(names, new_names):
    new_name_set = set(new_names)
    pairs = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            person_a = names[i]
            person_b = names[j]

            if person_a in new_name_set or person_b in new_name_set:
                pairs.append((person_a, person_b))

    random.shuffle(pairs)
    return pairs


def make_current_pairs():
    if st.session_state.comparison_mode == "incremental":
        return make_incremental_pairs(
            st.session_state.names,
            st.session_state.new_names
        )

    return make_pairs(st.session_state.names)


def start_comparison(names):
    st.session_state.names = names
    st.session_state.familiarity_scores = {
        name: 0 for name in names
    }
    st.session_state.likability_scores = {
        name: 0 for name in names
    }
    st.session_state.pairs = make_pairs(names)
    st.session_state.question_index = 0
    st.session_state.answer_history = []
    st.session_state.comparison_mode = "initial"
    st.session_state.new_names = []
    st.session_state.stage = "familiarity"


def start_incremental_comparison(new_names):
    st.session_state.new_names = new_names
    st.session_state.comparison_mode = "incremental"

    for name in new_names:
        st.session_state.names.append(name)
        st.session_state.familiarity_scores[name] = 0
        st.session_state.likability_scores[name] = 0

    st.session_state.pairs = make_current_pairs()
    st.session_state.question_index = 0
    st.session_state.answer_history = []
    st.session_state.stage = "familiarity"


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

    st.session_state.answer_history.append(
        {
            "stage": stage,
            "question_index": question_index,
            "pairs": list(pairs),
            "person_a": person_a,
            "person_b": person_b,
            "result": result,
            "comparison_mode": st.session_state.comparison_mode,
            "new_names": list(st.session_state.new_names)
        }
    )

    if stage == "familiarity":
        scores = st.session_state.familiarity_scores
    else:
        scores = st.session_state.likability_scores

    if result == ">":
        scores[person_a] += 1
        scores[person_b] -= 1
    elif result == "<":
        scores[person_a] -= 1
        scores[person_b] += 1

    st.session_state.question_index += 1

    if st.session_state.question_index < len(st.session_state.pairs):
        return

    if stage == "familiarity":
        st.session_state.stage = "likability"
        st.session_state.pairs = make_current_pairs()
        st.session_state.question_index = 0
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

    answer = st.session_state.answer_history.pop()
    stage = answer["stage"]
    person_a = answer["person_a"]
    person_b = answer["person_b"]
    result = answer["result"]

    if stage == "familiarity":
        scores = st.session_state.familiarity_scores
    else:
        scores = st.session_state.likability_scores

    if result == ">":
        scores[person_a] -= 1
        scores[person_b] += 1
    elif result == "<":
        scores[person_a] += 1
        scores[person_b] -= 1

    st.session_state.stage = stage
    st.session_state.question_index = answer["question_index"]
    st.session_state.pairs = answer["pairs"]
    st.session_state.comparison_mode = answer["comparison_mode"]
    st.session_state.new_names = answer["new_names"]


def load_saved_into_state(saved_results):
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
    st.session_state.comparison_mode = "initial"
    st.session_state.new_names = []
    st.session_state.pairs = []
    st.session_state.question_index = 0
    st.session_state.answer_history = []
    st.session_state.editor_version += 1
    st.session_state.stage = "results"


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

    name = moved_point.get("name")

    if name not in st.session_state.names:
        return

    try:
        x = max(-100, min(100, round(float(moved_point["x"]))))
        y = max(-100, min(100, round(float(moved_point["y"]))))
    except (KeyError, TypeError, ValueError):
        return

    st.session_state.x_coordinates[name] = x
    st.session_state.y_coordinates[name] = y

    save_current_results(
        st.session_state.names,
        st.session_state.familiarity_scores,
        st.session_state.likability_scores,
        st.session_state.x_coordinates,
        st.session_state.y_coordinates
    )

    st.session_state.drag_message = (
        f"{name} 的座標已更新為 ({x}, {y})"
    )
    st.session_state.editor_version += 1


def make_figure():
    plt.rcParams["font.family"] = "PingFang TC"
    plt.rcParams["axes.unicode_minus"] = False

    figure, axis = plt.subplots(figsize=(8, 8))
    axis.axhline(0, color="gray", linewidth=1)
    axis.axvline(0, color="gray", linewidth=1)

    for name in st.session_state.names:
        x = st.session_state.x_coordinates[name]
        y = st.session_state.y_coordinates[name]

        axis.scatter(x, y, s=100)
        axis.annotate(
            name,
            (x, y),
            xytext=(5, 5),
            textcoords="offset points"
        )

    axis.set_xlim(-110, 110)
    axis.set_ylim(-110, 110)
    settings = st.session_state.display_settings
    axis.set_xlabel(settings["x_axis_title"])
    axis.set_ylabel(settings["y_axis_title"])
    axis.set_title(settings["app_title"])
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
    saved_results = load_current_results()
except Exception as error:
    st.error("目前無法連接私人資料庫，請稍後再試。")
    st.exception(error)
    st.stop()

if not st.session_state.display_settings_loaded:
    if saved_results is not None:
        st.session_state.display_settings = normalized_display_settings(
            saved_results.get("display_settings")
        )
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

    if saved_results is not None:
        if st.button("載入上次結果", width="stretch"):
            load_saved_into_state(saved_results)
            st.rerun()

    if st.button("重新開始", width="stretch"):
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


if st.session_state.stage == "names":
    st.subheader("1. 輸入朋友名單")
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
            start_comparison(names)
            st.rerun()


elif st.session_state.stage in ["familiarity", "likability"]:
    question_index = st.session_state.question_index
    total_questions = len(st.session_state.pairs)
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

    st.progress((question_index + 1) / total_questions)
    st.caption(f"第 {question_index + 1} / {total_questions} 題")
    st.markdown(f"### {question}")

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
        "拖動圓點即可微調 X/Y 座標；原始熟悉度與好感度分數不會改變。"
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
        figure = make_figure()
        st.pyplot(figure, width="stretch")
        plt.close(figure)
