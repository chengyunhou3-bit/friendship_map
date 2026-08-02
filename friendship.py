import json
import os
import random
from datetime import datetime
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

RESULTS_FILE = Path(
    os.environ.get(
        "FRIENDSHIP_RESULTS_FILE",
        Path(__file__).with_name("results.json")
    )
)


def collect_names():
    names = []

    while True:
        name = input("輸入朋友名字（輸入 done 結束）：").strip()

        if name.lower() == "done":
            break

        if name == "":
            print("名字不能是空白！")
        elif name in names:
            print("這個名字已經輸入過了！")
        else:
            names.append(name)

    return names


def compare_people(names, question):
    scores = {}

    for name in names:
        scores[name] = 0

    pairs = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs.append((names[i], names[j]))

    random.shuffle(pairs)
    total_questions = len(pairs)

    for question_number, (person_a, person_b) in enumerate(
        pairs,
        start=1
    ):
        print(f"\n第 {question_number} / {total_questions} 題")

        while True:
            result = input(
                f"{question}：{person_a} >、=、< {person_b}？"
            ).strip()

            if result in [">", "=", "<"]:
                break

            print("輸入錯誤，請輸入 >、= 或 <")

        if result == ">":
            scores[person_a] += 1
            scores[person_b] -= 1
        elif result == "<":
            scores[person_a] -= 1
            scores[person_b] += 1

    return scores


def show_ranking(title, scores):
    ranking = sorted(
        scores,
        key=scores.get,
        reverse=True
    )

    print(f"\n{title}排名：")

    for position, name in enumerate(ranking, start=1):
        print(f"{position}. {name}：{scores[name]} 分")


def normalize_scores(scores):
    lowest = min(scores.values())
    highest = max(scores.values())

    if lowest == highest:
        return {name: 0 for name in scores}

    normalized = {}

    for name, score in scores.items():
        position = (score - lowest) / (highest - lowest)
        normalized[name] = round(position * 200 - 100)

    return normalized


def draw_map(names, x_coordinates, y_coordinates):
    if plt is None:
        print("\n尚未安裝繪圖套件，請在 Terminal 執行：")
        print("python3 -m pip install matplotlib")
        return

    plt.rcParams["font.family"] = "PingFang TC"
    plt.rcParams["axes.unicode_minus"] = False

    plt.figure(figsize=(8, 8))

    # 畫出座標軸，將圖分成四個象限。
    plt.axhline(0, color="gray", linewidth=1)
    plt.axvline(0, color="gray", linewidth=1)

    for name in names:
        x = x_coordinates[name]
        y = y_coordinates[name]

        plt.scatter(x, y, s=100)
        plt.annotate(
            name,
            (x, y),
            xytext=(5, 5),
            textcoords="offset points"
        )

    plt.xlim(-110, 110)
    plt.ylim(-110, 110)
    plt.xlabel("熟悉度：不熟 ← → 熟悉")
    plt.ylabel("好感度：負面 ← → 喜歡")
    plt.title("人際關係座標圖")
    plt.grid(alpha=0.2)
    plt.show()


def save_results(
    names,
    familiarity_scores,
    likability_scores,
    x_coordinates,
    y_coordinates,
    display_settings=None,
    pin_protection=None
):
    data = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "names": names,
        "familiarity_scores": familiarity_scores,
        "likability_scores": likability_scores,
        "x_coordinates": x_coordinates,
        "y_coordinates": y_coordinates
    }

    if display_settings is not None:
        data["display_settings"] = display_settings

    if pin_protection is not None:
        data["pin_protection"] = pin_protection

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print(f"\n結果已保存到：{RESULTS_FILE}")


def load_results():
    if not RESULTS_FILE.exists():
        return None

    try:
        with RESULTS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        print("\n舊的結果檔無法讀取，將開始新的比較。")
        return None


def show_coordinates(names, x_coordinates, y_coordinates):
    print("\n最終人際關係座標：")

    for name in names:
        x = x_coordinates[name]
        y = y_coordinates[name]
        print(f"{name}：({x}, {y})")


def main():
    saved_results = load_results()
    use_saved_results = False

    if saved_results is not None:
        while True:
            choice = input(
                "找到上次的結果，要直接查看嗎？(y/n)："
            ).strip().lower()

            if choice in ["y", "yes"]:
                use_saved_results = True
                break

            if choice in ["n", "no"]:
                break

            print("請輸入 y 或 n")

    if use_saved_results:
        names = saved_results["names"]
        familiarity_scores = saved_results["familiarity_scores"]
        likability_scores = saved_results["likability_scores"]
        x_coordinates = saved_results["x_coordinates"]
        y_coordinates = saved_results["y_coordinates"]

        print(f"\n載入時間：{saved_results['saved_at']}")
        show_ranking("熟悉度", familiarity_scores)
        show_ranking("好感度", likability_scores)
        show_coordinates(names, x_coordinates, y_coordinates)
        draw_map(names, x_coordinates, y_coordinates)
        return

    names = collect_names()

    print("\n朋友名單：", names)

    if len(names) < 2:
        print("至少需要輸入兩個名字！")
        return

    familiarity_scores = compare_people(
        names,
        "熟悉度（你跟誰比較熟）"
    )

    show_ranking("熟悉度", familiarity_scores)

    print("\n接下來比較好感度！")

    likability_scores = compare_people(
        names,
        "好感度（誰的人品更好）"
    )

    show_ranking("好感度", likability_scores)

    x_coordinates = normalize_scores(familiarity_scores)
    y_coordinates = normalize_scores(likability_scores)

    show_coordinates(names, x_coordinates, y_coordinates)

    save_results(
        names,
        familiarity_scores,
        likability_scores,
        x_coordinates,
        y_coordinates
    )

    draw_map(
        names,
        x_coordinates,
        y_coordinates
    )


if __name__ == "__main__":
    main()
