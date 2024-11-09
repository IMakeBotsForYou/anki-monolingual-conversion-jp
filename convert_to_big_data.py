"""
Used to initially convert decks to
the big data.json file.
Has some usful functions and variables too
"""

import sys
import json
import re
import os
from scraper import convert_word_to_hiragana, get_hiragana_only

big_data_dictionary = {}
word_to_readings_map = {}
BIG_DATA_FILE = "big_data.json"

RED = "CC2222"
YELLOW = "ECE0B2"
GRAY = "808080"

PRIORITY_ORDER = [
    "故事・ことわざ・慣用句オンライン",
    "実用日本語表現辞典",
    "使い方の分かる 類語例解辞典",
    "三省堂国語辞典",
    "旺文社国語辞典 第十一版",
    "大辞泉",
    "大辞林",
    "Weblio",
]
OPENING_BRACKETS = r"<（「\[【〔\(『［〈《〔〘｟"
CLOSING_BRACKETS = r">）」\]】〕\)』］〉》〕〙｠"

KANSUUJI = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

KANJI = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f"
HIRAGANA = r"あ-ゔ"
KANA = r"あ-ヺ"
NUMBER_CHARS = r"①-⑳❶-❿㉑-㉟⑴-⒇⒈-⒛➊-➓➀-➉🈩🈔🈪㊀-㊉㊤㊥㊦㋐-㋾１-９ⓐ-ⓩⒶ-Ⓩ🅐-🅩"
FIRST_NUMBER_CHARS = r"①❶⑴⒈➊➀🈩㊀㊤㋐１ⓐⒶ🅐"
LAST_NUMBER_CHARS = r"⑳❿⑳⒇⒛➓➉🈪㊉㊦㋾９ⓩⓏ🅩"
NUMBERS_AND_EMOJIS = rf"[{NUMBER_CHARS}]|\d️⃣"
PREFIX = rf"{NUMBERS_AND_EMOJIS}|^|。|・|<br />|\n|[{CLOSING_BRACKETS}{OPENING_BRACKETS}]| |　|記号.+?"
SUFFIX = rf"。|\n|<br ?/>|[{CLOSING_BRACKETS}{OPENING_BRACKETS}]| |　"
ARROWS = r"⇔→←☞⇒⇐⇨"

NUMBER_CATEGORIES = {
    "①": "".join(chr(i) for i in range(ord("①"), ord("⑳") + 1))
    + "".join(chr(i) for i in range(ord("㉑"), ord("㉟") + 1)),
    "❶": "".join(chr(i) for i in range(ord("❶"), ord("❿") + 1)),
    "⑴": "".join(chr(i) for i in range(ord("⑴"), ord("⒇") + 1)),
    "⒈": "".join(chr(i) for i in range(ord("⒈"), ord("⒛") + 1)),
    "➊": "".join(chr(i) for i in range(ord("➊"), ord("➓") + 1)),
    "➀": "".join(chr(i) for i in range(ord("➀"), ord("➉") + 1)),
    "🈩": "🈩🈔🈪",
    "㊀": "".join(chr(i) for i in range(ord("㊀"), ord("㊉") + 1)),
    "㊤": "㊤㊥㊦",
    "㋐": "".join(chr(i) for i in range(ord("㋐"), ord("㋾") + 1)),
    # "１": "".join(chr(i) for i in range(ord("０"), ord("９") + 1)),
    "ⓐ": "".join(chr(i) for i in range(ord("ⓐ"), ord("ⓩ") + 1)),
    "Ⓐ": "".join(chr(i) for i in range(ord("Ⓐ"), ord("Ⓩ") + 1)),
    "🅐": "".join(chr(i) for i in range(ord("🅐"), ord("🅩") + 1)),
    "(1)": [f"({i})" for i in range(ord("1"), ord("9") + 1)],
    "KeyCapEmoji": [f"{i}️⃣" for i in range(1, 10)],
}

NUMBER_CATEGORIES_REGEX = {
    "①": r"[①-⑳㉑-㉟]+",
    "❶": r"[❶-❿]+",
    "⑴": r"[⑴-⒇]+",
    "⒈": r"[⒈-⒛]+",
    "➊": r"[➊-➓]+",
    "➀": r"[➀-➉]+",
    "🈩": r"[🈩🈔🈪]+",
    "㊀": r"[㊀-㊉]+",
    "㊤": r"[㊤-㊦]+",
    "㋐": r"[㋐-㋾]+",
    # "１": r"[０-９]+",
    "ⓐ": r"[ⓐ-ⓩ]+",
    "Ⓐ": r"[Ⓐ-Ⓩ]+",
    "🅐": r"[🅐-🅩]+",
    "(1)": r"(\(\d+?\))+",
    "KeyCapEmoji": r"(?:\d+️⃣)+",
}

REFERENCE_NUMBER_MAP = {
    **{f"({i})": i for i in range(1, 10)},
    **{chr(i): i - ord("①") + 1 for i in range(ord("①"), ord("⑳") + 1)},
    **{chr(i): i - ord("⑴") + 1 for i in range(ord("⑴"), ord("⒇") + 1)},
    **{f"{i}️⃣": i for i in range(1, 10)},
    **{chr(i): i - ord("❶") + 1 for i in range(ord("❶"), ord("❿") + 1)},
    **{chr(i): i - ord("㉑") + 21 for i in range(ord("㉑"), ord("㉟") + 1)},
    **{chr(i): i - ord("㊀") + 1 for i in range(ord("㊀"), ord("㊉") + 1)},
    "㊤": "上",
    "㊥": "中",
    "㊦": "下",
    **{
        chr(i): chr(ord("ア") + (i - ord("㋐")))
        for i in range(ord("㋐"), ord("㋾") + 1)
    },
    # **{chr(i): i - ord("０") for i in range(ord("１"), ord("９") + 1)},
    **{chr(i): chr(i - ord("ⓐ") + ord("a")) for i in range(ord("ⓐ"), ord("ⓩ") + 1)},
    **{chr(i): chr(i - ord("Ⓐ") + ord("A")) for i in range(ord("Ⓐ"), ord("Ⓩ") + 1)},
    **{chr(i): chr(i - ord("🅐") + ord("A")) for i in range(ord("🅐"), ord("🅩") + 1)},
}


def convert_reference_numbers(text):
    """Convert reference numbers in text to the format (number)."""

    # Function to replace each match with its mapped numeric value
    def replace_match(match):
        char = match.group(0)
        number = REFERENCE_NUMBER_MAP.get(char)
        return (
            f"〚{number}〛" if number else char
        )  # Return the number in parentheses or the char itself

    # Substitute each reference character with the desired format
    result = re.sub(
        r"|".join(map(re.escape, REFERENCE_NUMBER_MAP.keys())), replace_match, text
    )
    return result


def dict_to_text(d, level=0):
    """Convert a nested dictionary to a formatted string with indentation based on nesting level."""
    result = d["prefix"]

    for key, value in [(k, v) for k, v in d.items() if k != "prefix"]:
        if value in ["", ":", "\n"]:
            continue

        # Add a newline, then tabs based on the current level
        prefix = "└" if level == 0 else "└" + "─" * level
        result += "\n" + prefix + key

        # If the value is a string, add it after the key
        if isinstance(value, str):
            value = re.sub(r"^:|└*$", "", value)
            result += " " + value
        # If the value is a nested dictionary, recursively convert it
        elif isinstance(value, dict):
            result += dict_to_text(value, level + 1)

    result = re.sub(r"(?:<br />|\n)+", r"\n", result)
    result = re.sub(
        rf"^(└─*)({NUMBERS_AND_EMOJIS})└─*({NUMBERS_AND_EMOJIS})", r"\1\2 \3 ", result
    )
    # a = result[:]
    result = re.sub(r"(?:└─*)(?:\n|<br />|$)", "", result)
    return result


def find_first_category(text):
    """Identify the first number category that appears in the text."""
    first_category = None
    earliest_index = len(text) + 1  # Beyond bounds
    for category, pattern in NUMBER_CATEGORIES_REGEX.items():
        match_object = re.search(pattern, text)
        if match_object:
            start_index = match_object.span()[0]
            if start_index < earliest_index:
                earliest_index = start_index
                first_category = category
    return first_category


def segment_by_category(text, category, first_category, level):
    """
    Segments text by the first number characters of a specified category.
    If a key has a lower value than the previous or a jump of 2 or more,
    it includes that key and the rest of the segment in the key's segment.
    parameters:
        - text: str
        - category: str
        - first_category: str
        - level: int

    """

    # Get the pattern for the category and initialize tracking variables
    pattern = NUMBER_CATEGORIES_REGEX[category]
    category_regex = re.compile(f"({pattern[:-1]})")
    remove_prefixes = re.compile(r"└─*$")

    def clean_text(string):
        return remove_prefixes.sub("", string).strip()

    segments_dict = {"prefix": ""}
    segments = category_regex.split(text)
    previous = 0  # Keep track of the last processed key's value
    previous_key = None
    i = 0
    while i < len(segments) - 1:
        try:
            if re.match(pattern, segments[i]):
                key = segments[i]
                current_number = NUMBER_CATEGORIES[category].index(key) + 1
                # Check if the current key is valid based on previous key's value

                is_referencing_other_level = level > 0 and first_category == category
                if is_referencing_other_level or (
                    current_number <= previous or current_number > previous + 1
                ):
                    # If the current key is lower or jumps 2 or more,
                    # we're talking about a different key in reference
                    segments_dict[previous_key] += key + clean_text(
                        "".join(segments[i + 1])
                    )
                else:
                    # Otherwise, add the segment normally
                    segments_dict[key] = clean_text(segments[i + 1])
                    previous = current_number  # Update highest
                    previous_key = key

                i += 2  # Move to the next potential key-value pair
            else:
                segments_dict["prefix"] += segments[i]
                i += 1  # Move to the next segment if not a key pattern match
        except ValueError:
            segments_dict[previous_key] += key
            if i + 1 < len(segments):
                segments_dict[previous_key] += clean_text("".join(segments[i + 1]))
            i += 1  # Move to the next segment if not a key pattern match

    return segments_dict


def recursive_nesting_by_category(
    text, first_category=None, next_category=None, level=0
):
    """Recursively separates the text into nested dictionaries by number character categories."""

    next_category = find_first_category(text)
    if not next_category:
        return text  # Base case: no number characters left
    if not first_category:
        first_category = next_category

    try:
        segments_dict = segment_by_category(
            text, first_category=first_category, category=next_category, level=level
        )
    except KeyError:
        return text  # Text, no longer has any segments

    for key, sub_text in segments_dict.items():
        # if not isinstance(sub_text, str):
        #     print(json.dumps(segments_dict, indent=2, ensure_ascii=False))
        #     print(sub_text)
        segments_dict[key] = recursive_nesting_by_category(
            sub_text,
            first_category=first_category,
            next_category=next_category,
            level=level + 1,
        )

    return segments_dict


def get_entry(ref_path, text):
    if not ref_path:
        return text

    entry_dict = recursive_nesting_by_category(text)
    if isinstance(entry_dict, str):
        return entry_dict  # Final destination

    current = entry_dict.copy()

    for step in ref_path:
        if isinstance(current, str):
            return current  # Final destination

        find_correct = [
            k
            for k in current.keys()
            if k != "prefix" and str(REFERENCE_NUMBER_MAP[k]) == step
        ]
        if find_correct:
            current = current[find_correct[0]]
        else:
            break

    if isinstance(current, str):
        return current  # Final destination
    if isinstance(current, dict):
        # Current is still a nested dictionary
        return dict_to_text(current)


def convert_to_path(reference_numbers):
    path = []
    counter = 0
    for i, x in enumerate(reference_numbers):
        if counter > 0:
            counter -= 1
            continue

        if x <= "9" and counter == 0:
            path.append(f"{x}{reference_numbers[i + 1]}{reference_numbers[i + 2]}")
            counter = 2
        else:
            path.append(x)

    return path


def add_dictionary_to_big_data(dictionary_path, big_data):
    """
    Adds words and their definitions from dictionary files to the global `big_data` dictionary.

    Args:
    - dictionary_path (str): Path to the dictionary folder.
    - big_data (dict): The shared dictionary.
    """
    print(f"Adding from {dictionary_path}")
    term_bank_files = sorted(
        [
            f
            for f in os.listdir(dictionary_path)
            if re.match(r"term_bank_\d+\.json$", f)
        ],
        key=lambda x: int(re.search(r"\d+", x).group()),
    )

    for file in term_bank_files:
        # data = None
        # with open(f"旺文社国語辞典 第十一版/{file}", "r", encoding="utf-8") as f:
        #     data = json.load(f)

        # with open(f"旺文社国語辞典 第十一版/{file}", "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=2, ensure_ascii=False)

        process_term_bank_file(file, dictionary_path, big_data)


def process_term_bank_file(file, dictionary_path, big_data):
    """Processes a single term bank file."""
    print(f"Processing {file} in {dictionary_path}")

    if dictionary_path not in big_data:
        big_data[dictionary_path] = {}

    file_path = os.path.join(dictionary_path, file)
    words_to_remove = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for entry in data:
                word, reading, entry_type, definitions_in_data = (
                    entry[0],
                    entry[1],
                    entry[2],
                    entry[5],
                )
                # Skip entries with unwanted types
                if entry_type not in ["子", "句"]:
                    # Handle missing or convert reading to Hiragana
                    if not reading:
                        reading = get_hiragana_only(word)
                    else:
                        reading = get_hiragana_only(reading)

                    definition_list = []
                    for definition in definitions_in_data:
                        definition_text = get_text_only_from_dictionary(
                            word, reading, definition, dictionary_path
                        )
                        if definition_text:
                            definition_list.append(definition_text)

                else:
                    definition_list = []

                word = word.replace("＝", "")
                if not definition_list:  # No definitions for entry?
                    words_to_remove.append(word)
                else:
                    # Update call to `edit_big_data` with the new structure
                    edit_big_data(
                        big_data, dictionary_path, reading, word, definition_list
                    )

    except Exception as e:
        print(f"Error processing file {file}: {e}")
        raise e


def edit_big_data(big_data, dictionary_path, reading, word, definitions):
    """
    Updates big_data with the specified structure:

    big_data = {
        "dictionary_path": {
            "reading": {
                "word1": ["definitions_1"],
                "word2": ["definitions_2"],
            }
        }
    }
    """
    if re.search(r"^\d+$", word):
        print(f"Skipping all-number word {word}")
        return
    # Ensure dictionary_path and reading exist
    if reading not in big_data[dictionary_path]:
        big_data[dictionary_path][reading] = {}

    # Add definitions to the word under the reading
    if word not in big_data[dictionary_path][reading]:
        big_data[dictionary_path][reading][word] = []

    # Remove definitions containing "Weblio" and add the rest
    filtered_definitions = [x for x in definitions if "Weblio" not in x]

    big_data[dictionary_path][reading][word].extend(filtered_definitions)

    # Ensure unique definitions for the word
    big_data[dictionary_path][reading][word] = list(
        set(big_data[dictionary_path][reading][word])
    )
    # if reading == "かかりむすび":
    # print(word)
    if word not in word_to_readings_map:
        word_to_readings_map[word] = []

    word_to_readings_map[word].append(reading)
    word_to_readings_map[word] = list(set(word_to_readings_map[word]))


def replace_furigana_references(text):
    # hiragana_kanji_references = re.finditer(
    #         rf"([{HIRAGANA}]+?)(?:（| \()((?:(?:[{KANJI}]+)(?:[{HIRAGANA}]+))+)(?:（|\) )", text
    #     )
    # if hiragana_kanji_references:
    #     for r in hiragana_kanji_references:
    #         the_match = r.group()
    #         the_hiragana = r.group(1)
    #         the_kanji = r.group(2)

    text = text.replace("（", " (").replace("）", ") ")
    a_prefix = rf"({PREFIX})?"
    words_and_furigana = rf"((?:([{KANJI}]+)(?: \([{HIRAGANA}]+)\) ?)+)([{HIRAGANA}]+)?"
    a_suffix = rf"((?:{NUMBERS_AND_EMOJIS})+)?"
    ref_with_furigana = re.compile(
        rf"{a_prefix}⇒{words_and_furigana}{a_suffix}",
        flags=re.UNICODE,
    )

    match_object = ref_with_furigana.finditer(text)

    # links = []

    if match_object:
        for match in match_object:
            # Since we can't just "guess" the kanji's readings,
            # I'm only taking reading into account when it
            # describes the entire word.

            reading_match = re.search(
                rf"( \(([{HIRAGANA}]+)\) ?)(?:(?:[{NUMBER_CHARS}]|(\d️⃣))+|\n|$)",
                match.group(),
            )
            has_kanji = re.search(rf"[{KANJI}]", match.group())
            furigana = None

            if reading_match and has_kanji:
                matched = reading_match.group(1)
                furigana = "".join(
                    ["".join([y if y else "" for y in x]) for x in matched]
                )

            no_furigana_and_ref = re.findall(
                rf"[a-zA-Z]|[{KANJI}]|(?:{NUMBERS_AND_EMOJIS})+$|[^(⇒][{HIRAGANA}]+[^)]?$",
                match.group(),
                flags=re.U,
            )

            # number = match.groups()[3] if match.groups()[3] else ""

            if no_furigana_and_ref:
                no_furigana_and_ref = "".join(
                    [x.replace(" ", "") for x in no_furigana_and_ref]
                )

            # No furigana that describes the entire word
            # ↓
            # Replace with the no-furigana version

            # Has furigana that describes the entire word
            # ↓
            # Don't replace

            original = f"{match.group(2)}{match.group(4) if match.group(4) else ''}"
            if not furigana:
                text = text.replace(original, no_furigana_and_ref)

    return text


def normalize_references(text: str, dictionary_path: str) -> str:
    text = re.sub(rf" ?[{ARROWS}]", "⇒", text)
    text = text.replace("\\n", "\n")
    text = re.sub(r"<br ?/>", "\n", text)
    flag = False
    text_original = text[:]

    if dictionary_path.endswith("大辞泉"):
        # ［名］(スル)「アルバイト」の略。「夏休みにバイトする」
        text = re.sub(rf"⇒", " ⇒", text)
        has_ryaku = re.compile(
            rf"({PREFIX})「([^{OPENING_BRACKETS}]+?)」の略({SUFFIX})"
        )
        if has_ryaku.search(text):
            adding_text = has_ryaku.sub(r"⇒\2。 ", has_ryaku.search(text).group())
            if adding_text not in text:
                text += "\n" + adding_text

        # Handle this?
        # ［連語］⇒置 (お) く⑫
        # ⇒人返 (ひとがえ) し②

        """
        0-11  ⇒異化 (いか) ②
        0-1  
        2-10  異化 (いか) 
        2-4   異化
        10-11 ②
        """

        # flag = True
        text = replace_furigana_references(text)
        text = re.sub(r"⇒⇒+", "⇒", text)
        text = text.replace("\\n", "\n")
        # convert に同じ format to ⇒ format for linking purposes later.
        # Either in the beginning, between lines, or between periods.
        #                             Prefix   Word        Suffix
        definition_text = re.sub(
            rf"({PREFIX})「(.+?) \((.+?)\) 」に同じ({SUFFIX})", r"\1⇒\3 (\2) \4 ", text
        )
        definition_text = re.sub(
            rf"({PREFIX})「(.+?)」に同じ({SUFFIX})", r"\1⇒\2\3 ", text
        )

        # 。「言葉①」に同じ。
        # 。⇒言葉①
        # 。⇒言葉(1) (Later)

        # 。⇒内匠寮 (たくみりょう) ①
        # 。⇒IOA（Independent Olympic Athletes）
        # ⇒コマーシャル①
        # ...ラバー。→弾性ゴム\n② 植物から...
        # ⇒鉱工業生産指数①
        pattern_text = rf"({PREFIX})?⇒([^\n]+?)(?:（.+?）)?((?:{NUMBERS_AND_EMOJIS})*?)({SUFFIX}|$|・| |　)"
        pattern = re.compile(pattern_text)

        results = pattern.finditer(text)

        if results:
            # if len([x for x in results]) > 1:

            for result in results:
                _prefix, word, reference_number, suffix = result.groups()

                _prefix = _prefix if _prefix else ""
                reference_number = reference_number if reference_number else ""
                suffix = suffix if suffix else ""
                # Reference number
                reference_numbers = convert_to_path(reference_number)
                try:
                    references = "".join(
                        [convert_reference_numbers(x) for x in reference_numbers]
                    )
                except KeyError:
                    print("[ERROR]\t", text, reference_numbers)

                text = pattern.sub(f"{_prefix}⇒{word}{reference_number}{suffix}", text)

    if dictionary_path.endswith("三省堂国語辞典"):
        definition_text = re.sub(
            rf"({PREFIX})「(.+?) \((.+?)\) 」と同じ({SUFFIX})", r"\1⇒\3 (\2) \4 ", text
        )
        definition_text = re.sub(
            rf"({PREFIX})「(.+?)」と同じ({SUFFIX})", r"\1⇒\2\3 ", text
        )

        # ⇒「.+?」
        reference_pattern = rf"⇒「(.+?)((?:{NUMBERS_AND_EMOJIS})+)」"

        in_kagigakko = re.compile(reference_pattern)
        if in_kagigakko.search(text):
            text = in_kagigakko.sub(r"「⇒\1\2」", text)

        # ⇒脇⑦・挙げ句②。
        # ↓
        # ⇒脇⑦　⇒挙げ句②。
        reference_pattern = (
            rf"([^\n：・{NUMBER_CHARS}\d️⃣⇒ {OPENING_BRACKETS}{CLOSING_BRACKETS}]+)"
            rf"( \(.+?\) ?)?((?:[{NUMBER_CHARS}\d️⃣]| ?\(\d+\) ?)*)"
        )

        pattern_mulitple = re.compile(
            rf"⇒{reference_pattern}((?:(?:：|・){reference_pattern})+)($|\n| |　|。|[{CLOSING_BRACKETS}])"
        )

        results_multiple = pattern_mulitple.finditer(text)

        text_original = text[:]
        if results_multiple:
            for i, result in enumerate(results_multiple):
                first = i == 1  #                          Remove ⇒
                references = re.split("・", result.group()[1:])
                result_original = result.group()
                result_after_changes = ""
                for reference in references:
                    reference = (
                        reference.strip("\n").strip(" ").strip("　").replace("｠", "")
                    )
                    fixed_nubmers_reference = re.sub(
                        r" ?\((d+)\) ?", r"〚{\1}〛", reference
                    )
                    result_after_changes = re.sub(
                        rf" ?(?:⇒|・){re.escape(reference)}",
                        rf" ⇒{fixed_nubmers_reference} ",
                        result_original,
                    )
                text = text.replace(result_original, result_after_changes)

        text = replace_furigana_references(text)

        # ①朝。午前。            ☓
        # ②〘服〙←モーニングコート。 ◯
        # ③←モーニングサービス。　　 ◯
        # (!) Remeber,   All arrows are now "⇒"

        pattern = re.compile(
            rf"({NUMBERS_AND_EMOJIS}|^|。|\n|[{CLOSING_BRACKETS}{OPENING_BRACKETS}]| |　|記号.+?)⇒([{NUMBER_CHARS}]*)([^\d{OPENING_BRACKETS}]+?)([{NUMBER_CHARS}]|\d️)?(・|$|。|<br />|\n)"
        )
        results = pattern.finditer(text)
        for result in results:
            _prefix, _, word, reference_number, suffix = result.groups()
            _prefix = _prefix if _prefix else ""
            reference_number = reference_number if reference_number else ""
            suffix = suffix if suffix else ""
            text = pattern.sub(f"{_prefix}⇒{word}{reference_number}{suffix} ", text)

    if dictionary_path.endswith("大辞林"):
        # ［名］(スル)「アルバイト」の略。「夏休みにバイトする」
        text = text.replace(" ・", "・")
        has_ryaku = re.compile(
            rf"({PREFIX})「([^{OPENING_BRACKETS}]+?)」の略({SUFFIX})"
        )
        if has_ryaku.search(text):
            adding_text = has_ryaku.sub(r"⇒\2。 ", has_ryaku.search(text).group())
            if adding_text not in text:
                text += "\n" + adding_text

        reference_pattern = rf"([^\n・{NUMBER_CHARS}\d️⃣⇒ {OPENING_BRACKETS}{CLOSING_BRACKETS}]+)( \(.+?\) ?)?((?:[{NUMBER_CHARS}\d️⃣]| ?\(\d+\) ?)*)"

        pattern_mulitple = re.compile(
            rf"⇒{reference_pattern}((?:・{reference_pattern})+)($|\n| |　|。|[{CLOSING_BRACKETS}])"
        )

        results_multiple = pattern_mulitple.finditer(text)

        text_original = text[:]
        if results_multiple:
            for i, result in enumerate(results_multiple):
                first = i == 1  #                          Remove ⇒
                references = re.split("・", result.group()[1:])
                result_original = result.group()
                result_after_changes = ""
                for reference in references:
                    reference = (
                        reference.strip("\n").strip(" ").strip("　").replace("｠", "")
                    )
                    fixed_nubmers_reference = re.sub(
                        r" ?\((d+)\) ?", r"〚{\1}〛", reference
                    )
                    result_after_changes = re.sub(
                        rf" ?(?:⇒|・){re.escape(reference)}",
                        rf" ⇒{fixed_nubmers_reference} ",
                        result_original,
                    )
                text = text.replace(result_original, result_after_changes)

        text = replace_furigana_references(text)

    if dictionary_path.endswith("使い方の分かる 類語例解辞典"):
        ...

    if dictionary_path.endswith("旺文社国語辞典 第十一版"):
        # Change it out of our format. Not a reference
        # 「ｘ⇒ｘ⇒」
        text = text.replace("（", " (").replace("）", ") ")
        transformations = re.finditer(r"「(?:.+?⇒)+(?:.+?)」", text)
        for transformation in transformations:
            text = text.replace(
                transformation.group(), transformation.group().replace("⇒", "→")
            )

        text = re.sub(r" ?⇒", " ⇒", text)

        # ⇒けん（献）  -  Hiragana (kanji)
        hiragana_kanji_references = re.finditer(
            rf"([{HIRAGANA}]+?)(?:（| \()((?:(?:[{KANJI} ]+)(?:[{HIRAGANA}]+))+)(?:（|\) )",
            text,
        )
        if hiragana_kanji_references:
            for r in hiragana_kanji_references:
                the_match = r.group()
                the_hiragana = r.group(1).replace(" ", "")
                the_kanji = r.group(2).replace(" ", "")
                text = text.replace(
                    the_match, f"{the_kanji.replace(' ', '')} ({the_hiragana}) "
                )

        text = replace_furigana_references(text)

        text = re.sub(rf"⇒([{HIRAGANA}]+) \(([{HIRAGANA}]+)\)", "⇒\1\2", text)
        # これから起こる事柄を表す言い 方。<br />｟ ⇒過去・現在｠"

        # ⇒古人(1)：古人(2)
        # ↓
        # ⇒古人(1) ⇒古人(2)。

        # ⇒下がる ⇒おりる (下りる) (1)：おりる (降りる) (2)
        reference_pattern = rf"([^\n：・{NUMBER_CHARS}\d️⃣⇒ {OPENING_BRACKETS}{CLOSING_BRACKETS}]+)( \(.+?\) ?)?((?:[{NUMBER_CHARS}\d️⃣]| ?\(\d+\) ?)*)"

        pattern_mulitple = re.compile(
            rf"⇒{reference_pattern}((?:(?:：|・){reference_pattern})+)($|\n| |　|。|[{CLOSING_BRACKETS}])"
        )

        results_multiple = pattern_mulitple.finditer(text)

        text_original = text[:]
        if results_multiple:
            for i, result in enumerate(results_multiple):
                first = i == 1  #                          Remove ⇒
                references = re.split("：|・", result.group()[1:])
                result_original = result.group()
                result_after_changes = ""
                for reference in references:
                    reference = (
                        reference.strip("\n").strip(" ").strip("　").replace("｠", "")
                    )
                    fixed_nubmers_reference = re.sub(
                        r" ?\((d+)\) ?", r"〚{\1}〛", reference
                    )
                    result_after_changes = re.sub(
                        rf" ?(?:⇒|：|・){re.escape(reference)}",
                        f" ⇒{fixed_nubmers_reference} ",
                        result_original,
                    )
                text = text.replace(result_original, result_after_changes)

        # ⇒言語（げんご）- Gengo (Furigana)
        # Change full-width brackets to half-width for later function
        text = re.sub(rf"（([{HIRAGANA}]+?)）", rf" (\1) ", text)
        text = text = replace_furigana_references(text)

        if text.endswith("\n⇒「使い分け」"):
            text = text[: -len("\n⇒「使い分け」")]

    text = text.replace(" ⇒", "⇒")
    text = re.sub(rf"・(?:[{NUMBER_CHARS}]|\d️⃣)", "", text)

    # Search for reference pattern in the definition
    reference_matches = re.finditer(
        rf"⇒([^(]+?)( \([あ-ゔ]+\) )?((?:{NUMBERS_AND_EMOJIS})*)(?:。|$|\n|<br />| |　)",
        text,
    )

    # {prefix}{tag}⇒{word}{references}{suffix}
    # already_linked = []
    # If there's a reference in the definition
    if reference_matches:
        for reference_match in reference_matches:
            last_char = reference_match.group()[-1]
            suffix = last_char if last_char in ["。", "\n", "　", " ", ";"] else ""
            if suffix == ";" and reference_match.group().endswith("<br />"):
                suffix = "<br />"

            referenced_word, furigana, reference_number_path = reference_match.groups()
            furigana = furigana if furigana else ""

            reference_number_path = (
                reference_number_path if reference_number_path else ""
            )
            reference_numbers = convert_to_path(reference_number_path)

            try:
                reference_numbers = "".join(
                    [convert_reference_numbers(x) for x in reference_numbers]
                )
            except KeyError:
                print("[ERROR]\t", text, reference_numbers)

            text = text.replace(
                reference_match.group(),
                f" ⇒{referenced_word}{furigana}{reference_numbers} ",
            )
            text += suffix

    return text.replace("\n", "<br />")


def clean_definition(
    word: str, reading: str, definition_text: str, dictionary_path: str
) -> str:
    # 〔③が原義〕 !todo
    """
    Cleans and formats the definition text based on the specific dictionary.

    Args:
    - definition_text (str): The raw definition text to clean.
    - dictionary_path (str): The name or identifier of the dictionary.

    Returns:
    - str: The cleaned and formatted definition text.
    """
    # Remove the first line for specific dictionaries

    my_word = word == "1"

    if word.endswith("の解説"):
        return None
    # Normalize \n's
    definition_text = definition_text.replace("\\n", "\n")
    # Weird character
    definition_text = definition_text.replace(" ", " ")
    definition_text = definition_text.split("Linked")[0]
    # Unecessary parts
    definition_text = re.sub(
        r"(?:\[補説\]|［補説］|［用法］|\[用法\]|\[可能\]|［可能］)(?:.|\n)+",
        "",
        definition_text,
    ).strip()

    # I don't even know why this appears at times
    definition_text = definition_text.replace("_x000D_", "")
    definition_text = definition_text.replace("\r", "")
    definition_text = definition_text.replace("\1", "")
    definition_text = definition_text.replace("\2", "")

    if not word and not reading:
        return None

    # Normalize spaces after numbers:
    definition_text = re.sub(
        rf"((?:{NUMBERS_AND_EMOJIS})[ ]+)+",
        r"\1".replace(" ", "") + " ",
        definition_text,
    )

    definition_text = normalize_references(definition_text, dictionary_path)

    # if "⇒" in definition_text:

    # Using endswith because I don't care about their order in the priority (or what order you chose to give them
    # in the folder name). Just matters that it ends with the dictionary name.
    if my_word:
        print(1, definition_text)
    if dictionary_path.endswith("大辞泉"):
        splitted = definition_text.split("<br />")
        if len(splitted) > 1:
            definition_text = "<br />".join(splitted[1:])  # Remove first line

        if "[可能]" in definition_text:
            definition_text = definition_text.split("[可能]")[0]
        if "[派生]" in definition_text:
            definition_text = definition_text.split("[派生]")[0]
        # Remove remains of example sentences
        # ④: 納得する。合点がいく。・・・・・・・・・・・・・・・・・ (after parsing)
        definition_text = re.sub(r"・(?:・|／)+", "", definition_text)
        definition_text = re.sub(r"。。+", "。", definition_text)

        # ・・・・・・・・・・・・・・・・・・・・・・・・・・・・・・・・／・。 。
        # ［動ザ上一］「まん（慢）ずる」（サ変）の上一段化。
        # ［動ザ上一］「みそんずる」（サ変）の上一段化。「話題の展覧会を―・じる」
        # ［動ザ上一］「てん（転）ずる」（サ変）の上一段化。「攻勢に―・じる」

        # First fix 「てん（転）ずる」 → "「転ずる」"
        definition_text = re.sub(
            rf"「[{HIRAGANA}]+（([{KANJI}]+)）([{HIRAGANA}]+)」",
            r"「\1\2」",
            definition_text,
        )

        # Then fix ［動ザ上一］「転ずる」（サ変）の上一段化。「攻勢に―・じる」 →  "⇒転ずる"
        definition_text = re.sub(
            rf"(?:［.+?］)「(.+?)」の(?:..?段化|..語)({SUFFIX})",
            r"⇒\1\2 ",
            definition_text,
        )

        # Remove
        # ［連語］《形容詞、および形容詞型活用語の連体形活用語尾「かる」に推量の助動詞「めり」の付いた「かるめり」の音変化》
        # ［連語］《連語「かんめり」の撥音の無表記》
        definition_text = re.sub(r"［.+?］《.+?》", r"", definition_text)

        # ［動ラ下一］［文］かきみだ・る［ラ下二］
        # ［動ラ五（四）］
        # ［動サ下一］［文］かきよ・す［サ下二］
        # ［名］(スル)
        # ［形動］［文］［ナリ］
        definition_text = re.sub(
            rf"(?:［.+?］)+(?:[{HIRAGANA}・]+［.+?］)?(?:\(スル\))?",
            r"",
            definition_text,
        )

        # 「一つ汲んで下されと、下々にも―に詞 (ことば) 遣ひて」〈浮・禁短気・二〉
        definition_text = re.sub(
            rf"「[^」]+?」〈[^〉]+?〉",
            r"",
            definition_text,
        )
        # 《季 新年》「餅網も焦げて―となりにけり／友二」
        definition_text = re.sub(
            rf"《[^》]+?》「[^」]+?」",
            r"",
            definition_text,
        )

    if my_word:
        print(2, definition_text)

    if dictionary_path.endswith("旺文社国語辞典 第十一版"):
        definition_text = definition_text.replace("〔違い〕", "")
        # (形) 《カロ・カツ (ク) ・イ・イ・ケレ・○》

        definition_text = re.sub(r" ?\(.+?\) 《.+?》", "", definition_text)

        # Remove first line
        # あい‐しょう【哀傷】――シヤウ\n
        splitted = definition_text.split("<br />")
        if len(splitted) > 1:
            definition_text = "<br />".join(splitted[2:])  # Remove first line

        # Remove the first line in items like this.
        # あい【挨】\nアイ㊥\nおす\n筆順：\n
        # \n\n（字義）\n① おす。押しのける。「挨拶（あいさつ）（＝原義は押しのけて進む意。国 ...

        if "筆順：" in definition_text:
            return None
            # definition_text = definition_text.split("筆順：")[1]
        if "字義" in definition_text:
            return None
            # definition_text = definition_text.split("(字義)")[1]

        definition_text = re.sub(r"図版：\n?", "", definition_text)
        definition_text = definition_text.strip("<br />")

        # Remove
        # （名・他スル）\n.
        # （形）《カロ・カツ（ク）・イ・イ・ケレ・○》\n
        # But keep (…の略) ?

        definition_text = re.sub(r"（.+?(?!の略)）(《.+?》)?\n", "", definition_text)

        # Remove
        # 〔可能〕あが・れる（下一）<br />
        # 〔他〕あ・げる（下一 ）
        definition_text = re.sub(
            rf"〔.+?〕?[{HIRAGANA}・]+（.+?）({SUFFIX})", r"\1", definition_text
        )

        # Remove everything after 〘使い分け〙
        if "〘使い分け〙" in definition_text:
            definition_text = definition_text.split("〘使い分け〙")[0]

        # Remove everything after 〘ちがい〙
        if "〘ちがい〙" in definition_text:
            definition_text = definition_text.split("〘ちがい〙")[0]

    if dictionary_path.endswith("使い方の分かる 類語例解辞典"):
        ...
        # This is already handled in the scraping function.
        # definition_text = definition_text.split(r'📚使い方')[0]
        # definition_text = definition_text.split(r'🔄使い分け')[0]
        # definition_text = definition_text.split(r'🔗関連語')[0]

    if dictionary_path.endswith("三省堂国語辞典"):
        definition_text = re.sub(r"〔〕", "", definition_text)
        ...
        # This is already handled in the scraping function
        # definition_text = re.sub(r"^.+?｠<br />|「.+」(?:<br />)?", "", definition_text)

    if dictionary_path.endswith("事故・ことわざ・慣用句オンライン"):
        ...
        # This is already handled in the scraping function

        # Remove spans like this
        # しりてしらざれ【知りて知らざれ】
        # 【失敗は成功のもと】

    if dictionary_path.endswith("大辞林"):
        no_period_quote = re.search(r"[^。」]$", definition_text)
        final_word_reference = re.search(
            rf"⇒[{KANJI}{KANA}a-zA-Z・]+$", definition_text
        )
        if no_period_quote and not final_word_reference:
            return None
        definition_text = definition_text.split("補説欄")[0]

        # 〔③が原義〕 ......
        startswith_comment = re.sub(r"^〔.+?〕", "", definition_text)

    if dictionary_path.endswith("実用日本語表現辞典"):
        definition_text = re.sub(f"^{re.escape(word)}", "", definition_text)

        # This is already handled in the scraping function

    if dictionary_path.endswith("Weblio"):
        # ［動カ下一］［文］なつ・く［カ下二］《「なづける」とも》
        # ［動ア下一］［文］かま・ふ［ハ下二］
        # ［動カ五（四）］
        definition_text = re.sub(
            rf"({PREFIX})(?:［.+?］)+(?:[{HIRAGANA}・]+［.+?］)?(?:《.+?》)?({SUFFIX})",
            r"\1\2",
            definition_text,
        )
        # ［名］(スル)
        # ［形動］［文］［ナリ］
        definition_text = re.sub(
            rf"(?:［.+?］)+(?:[{HIRAGANA}・]+［.+?］)?(?:\(スル\))?",
            r"",
            definition_text,
        )

    # # Add line breaks before entry numbers
    # definition_text = re.sub(rf"({NUMBERS_AND_EMOJIS})", r"<br />\1", definition_text)
    # Clean up leading or trailing unwanted characters

    if definition_text:
        definition_text = definition_text.strip("\n").strip("<br />")
        # once

    # if "⇒" in definition_text:
    #     definition_text = re.sub(rf"({PREFIX})⇒([{NUMBER_CHARS}]*)(.+)($|。|<br />|\n)", r"\1\2\3\4", definition_text)

    # Normalize numbers back
    definition_text = re.sub(rf"([{NUMBER_CHARS}][^ ]) ", r"\1 ", definition_text)
    # if "遊里で客の相手となる遊女" in definition_text:

    # Normalize line breaks
    definition_text = definition_text.replace("\n", "<br />").replace("\\n", "<br />")

    # Contract multiple linebreaks into a single linebreak
    # For some fucking reason {2,} doesn't work so here we are.
    definition_text = re.sub(r"(<br />|\n|\\n)+", r"<br />", definition_text)

    # if "遊里で客の相手となる遊女" in definition_text:

    # Temp
    # definition_text = definition_text.replace("<br />", "\n")

    # if "遊里で客の相手となる遊女" in definition_text:
    if my_word:
        print(3, definition_text)
    definition_dict = recursive_nesting_by_category(definition_text)
    if isinstance(definition_dict, dict):
        definition_text = dict_to_text(definition_dict)
    else:
        definition_text = definition_dict

    definition_text = re.sub(r"。+", "。", definition_text)
    definition_text = re.sub(r" *。", "。", definition_text)

    definition_text = re.sub(r"(?: |　)+", " ", definition_text)

    definition_text = definition_text.strip("\n").strip()

    if "[可能]" in definition_text:
        definition_text = definition_text.split("[可能]")[1]

    if my_word:
        print(4, definition_text)
    return definition_text.replace("\n", "<br />")


def get_text_only_from_dictionary(
    word: str, reading: str, definition_data: list, dic_name: str
) -> str:
    """
    Extracts the main definition text from the raw data.

    Args:
    - definition_data (list): List of strings and possibly other data types containing the definition.
    - dic_name (str): Name of the dictionary being processed.

    Returns:
    - str: Cleaned and simplified definition text.
    """

    def get_non_recursive(information):
        """Iteratively extracts strings from the nested structure."""
        stack = [information]
        result = []

        while stack:
            current = stack.pop()
            if isinstance(current, str):
                # reference_number = re.search(
                #     rf"^({NUMBER_CHARS})$", current
                # )
                # if reference_number:
                #     current = (
                #         f'〚{REFERENCE_NUMBER_MAP[current]}〛'
                #     )
                result.append(current)

            elif isinstance(current, list):
                flag = True
                """
                使い方の分かる 類語例解辞典
                "content": [
                  {
                    "tag": "span",
                    "style": {
                      "fontWeight": "bold"
                    },
                    "content": "そう"
                  },
                  {
                    "tag": "span",
                    "style": {
                      "fontWeight": "normal"
                    },
                    "content": "【僧】僧／僧侶／坊主／坊さん／御坊／お寺さん／僧家／沙門／法師／出家／比丘"
                  }
                ]
                ---------------------------------
                実用日本語表現辞典
                "content": [
                  {
                    "tag": "span",
                    "style": {
                      "fontWeight": "bold"
                    },
                    "content": "ごじあい"
                  },
                  {
                    "tag": "span",
                    "style": {
                      "fontWeight": "normal"
                    },
                    "content": "【ご自愛】"
                  }
                ]
                """

                if len(current) == 2:
                    first, _ = current
                    # if dic_name.endswith("使い方の分かる 類語例解辞典"):
                    #     reading_data, ruigigo_data = first, second

                    #     if "content" in ruigigo_data and "content" in reading:
                    #         if isinstance(ruigigo_data["content"], str):
                    #             actually_is_ruigigo = re.search(r"(.+?／)+(.+)", ruigigo_data["content"])
                    #             if actually_is_ruigigo:
                    #                 # The actual 類義語 part.
                    #                 flag = False

                    # These two are essentially the same thing.
                    if dic_name.endswith("実用日本語表現辞典") or dic_name.endswith(
                        "使い方の分かる 類語例解辞典"
                    ):
                        if "content" in first:
                            if first["content"] == reading:
                                flag = False

                if flag:
                    stack.extend(reversed(current))  # Maintain original order

            elif isinstance(current, dict):
                flag = True
                content = current.get("content")
                if "data" in current:
                    if "name" in current["data"]:
                        current_name = current["data"]["name"]
                        # Some of these have a "G" suffix, some don't, etc.
                        unwanted_tags = re.compile(
                            "違い|派生|区別|百科|アクセント|表記|品詞|用例|対義語"
                            "注記|歴史仮名|区別|ルビ|見出|可能形|異字同訓"
                        )
                        if dic_name.endswith("大辞林"):
                            if (
                                current_name == "単位名"
                                and "content" in current["data"]
                            ):
                                if isinstance(current["data"]["content"], str):
                                    # (センチメートル)
                                    current["data"]["content"] = current["data"][
                                        "content"
                                    ][1:-1]
                            elif unwanted_tags.search(current_name):
                                flag = False

                        if dic_name.endswith("使い方の分かる 類語例解辞典"):
                            if current_name != "意味":
                                flag = False

                        if dic_name.endswith("三省堂国語辞典"):
                            """
                                {
                                  "tag": "span",
                                  "data": {
                                    "name": "参照語義番号"
                                  },
                                  "content": {
                                    "tag": "span",
                                    "data": {
                                      "name": "語義番号"
                                    },
                                    "content": "①"
                                  }
                                }
                            """
                            """
                                {
                                    "tag": "span",
                                    "data": {
                                        "name": "参照語義番号"
                                    },
                                    "content": {
                                        "tag": "span",
                                        "style": {
                                            "verticalAlign": "text-bottom",
                                            "marginRight": 0.25
                                        },
                                        "content": {
                                            "tag": "img",
                                            "height": 1.0,
                                            "width": 1.0,
                                            "sizeUnits": "em",
                                            "appearance": "auto",
                                            "title": "二",
                                            "collapsible": false,
                                            "collapsed": false,
                                            "background": false,
                                            "path": "sankoku8/二-bluefill.svg"
                                        }
                                    }
                                }   
                            """
                            """
                                "tag": "div",
                                "data": {
                                    "name": "大語義"
                                },
                                "content": [
                                    {
                                        "tag": "span",
                                        "style": {
                                            "verticalAlign": "text-bottom",
                                            "marginRight": 0.25
                                        },
                                        "content": {
                                            "tag": "img",
                                            "height": 1.0,
                                            "width": 1.0,
                                            "sizeUnits": "em",
                                            "appearance": "monochrome",
                                            "title": "二",
                                            "collapsible": false,
                                            "collapsed": false,
                                            "background": false,
                                            "path": "sankoku8/二-fill.svg"
                                        }
                                    }
                                ]
                            """
                            # print(current_name)
                            if unwanted_tags.search(current_name):
                                # Pretty sure 三省堂国語辞典 doesn't have this but 大辞林 does.
                                flag = False

                            elif "参照語義番号" in current_name:
                                if "content" in content:
                                    if isinstance(content["content"], str):
                                        reference_number = re.search(
                                            rf"^({NUMBER_CHARS})$", content["content"]
                                        )
                                        if reference_number:
                                            content["content"] = (
                                                f'〚{REFERENCE_NUMBER_MAP[content["content"]]}〛'
                                            )
                                        current["content"] = content

                        if dic_name.endswith("大辞泉"):
                            if unwanted_tags.search(current_name):
                                flag = False
                        # 実用日本語表現辞典 doesn't seem to have any names other than "definition",
                        # but I put this here just in case.
                        if dic_name.endswith("実用日本語表現辞典"):
                            if current_name != "definition":
                                flag = False

                if dic_name.endswith("事故・ことわざ・慣用句オンライン"):
                    if "tag" in current:
                        tag = current["tag"]
                        """
                           Span example:
                          {
                            "tag": "span",
                            "content": "しのしょうにん【死の商人】"
                          },
                          Tables are are just the 異形s summarized in table form.
                        """
                        if tag in ["span", "table"]:
                            flag = False

                if dic_name.endswith("大辞林"):
                    if "title" in current:
                        title = current["title"]
                        if title in KANSUUJI:
                            content = f"{KANSUUJI.index(title) + 1}️⃣"

                if dic_name.endswith("三省堂国語辞典"):
                    """
                        "content": {
                            "tag": "img",
                            "height": 1.0,
                            "width": 1.0,
                            "sizeUnits": "em",
                            "appearance": "monochrome",
                            "title": "二",
                            "collapsible": false,
                            "collapsed": false,
                            "background": false,
                            "path": "sankoku8/二-fill.svg"
                        }                        
                    """
                    if "title" in current:
                        title = current["title"]
                        if title in KANSUUJI:
                            content = f"{KANSUUJI.index(title) + 1}️⃣"
                if flag:
                    if content:
                        stack.append(content)
            else:
                print(
                    f"Unexpected type encountered in dictionary '{dic_name}': {type(current)}"
                )  # Logging unexpected types
        return "".join(result)

    my_text = get_non_recursive(definition_data)

    return clean_definition(word, reading, my_text, dic_name)


# def edit_big_data(big_data, dictionary_path, word, reading, definitions):
#     # Given a word, its reading, and its definition, it creates a new datapoint
#     # for said word/reading.

#     """
#     big_data = {
#         "dictionary_path": {
#             "word": {
#                 "reading1": ["definitions_1"],
#                 "reading2": ["definitions_2"],
#             }
#         }
#     }
#     """

#     if word not in big_data[dictionary_path]:
#         big_data[dictionary_path][word] = {}

#     if reading not in big_data[dictionary_path][word]:
#         big_data[dictionary_path][word][reading] = []

#     if definitions:
#         definitions = [x for x in definitions if "Weblio" not in x]
#         big_data[dictionary_path][word][reading].extend(definitions)
#         # Just in case there's dupelicates
#         big_data[dictionary_path][word][reading] = list(
#             set(big_data[dictionary_path][word][reading])
#         )


def load_big_data(big_data_dictionary, override=False):
    if not override:
        with open("big_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("You're about to override big_data, continue?\ny\\N")
        user_choice = input()
        if user_choice != "y":
            sys.exit()
        for dictionary_path in PRIORITY_ORDER:
            print(f"Loading {dictionary_path}")
            add_dictionary_to_big_data(dictionary_path, big_data_dictionary)

        # add_dictionary_to_big_data("旺文社国語辞典 第十一版", big_data_dictionary)
        # add_dictionary_to_big_data("使い方の分かる 類語例解辞典", big_data_dictionary)
        # add_dictionary_to_big_data("Weblio", big_data_dictionary)

        # Write the final big_data to a JSON file
        save_to_big_data(big_data_dictionary)
        return big_data_dictionary


def save_to_big_data(big_data_dictionary):
    with open(BIG_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(big_data_dictionary, f, ensure_ascii=False, indent=2)
    with open("word_to_readings_map.json", "w", encoding="utf-8") as f:
        json.dump(word_to_readings_map, f, ensure_ascii=False, indent=2)
    print("Saved to big data")


if __name__ == "__main__":
    big_data_dictionary = load_big_data(big_data_dictionary, override=True)
