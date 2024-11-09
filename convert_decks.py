"""
The main script.
"""

import json
import os
import re

import pandas as pd

from scraper import scrape_weblio, convert_word_to_hiragana, get_hiragana_only

from convert_to_big_data import (
    edit_big_data,
    clean_definition,
    NUMBER_CHARS,
    KANJI,
    HIRAGANA,
    KANA,
    OPENING_BRACKETS,
    CLOSING_BRACKETS,
    get_entry,
    PRIORITY_ORDER,
    load_big_data,
    RED, YELLOW, GRAY
    # recursive_nesting_by_category,
    # dict_to_text,
)

# from AnkiTools import anki_convert

big_data_dictionary = {"Weblio": {}}
not_in_weblio = []


# バグ　バグる
# グーグル ググる　ggrks
#
def get_versions_of_word(word, reading, word_to_readings_map):
    """
    Generates possible versions of the word by applying various transformations.

    Args:
    - word (str): The word to transform.

    Returns:
    - list: A list of possible word versions.
    """
    # original_word = word[:]  # Preserve the original word
    versions = [(word, reading)]

    # Deduplicate versions
    # Number and Katakana conversions
    def to_full_width(num):
        return chr(ord("０") + int(num))

    # to_full_width = lambda num: chr(ord("０") + int(num))
    digit_map = {
        "0": "〇",
        "1": "一",
        "2": "二",
        "3": "三",
        "4": "四",
        "5": "五",
        "6": "六",
        "7": "七",
        "8": "八",
        "9": "九",
    }
    tens_map = {
        "1": "十",
        "2": "二十",
        "3": "三十",
        "4": "四十",
        "5": "五十",
        "6": "六十",
        "7": "七十",
        "8": "八十",
        "9": "九十",
    }

    numbers = {
        "１００": "百",
        "100": "百",
        **{
            # 半角
            str(i): (
                digit_map[str(i)]
                if i < 10
                else (
                    tens_map[str(i // 10)]
                    + (digit_map[str(i % 10)] if i % 10 != 0 else "")
                )
            )
            for i in range(99, 0, -1)
        },
        **{
            # 全角
            "".join(to_full_width(d) for d in str(i)): (
                digit_map[str(i)]
                if i < 10
                else (
                    tens_map[str(i // 10)]
                    + (digit_map[str(i % 10)] if i % 10 != 0 else "")
                )
            )
            for i in range(99, 0, -1)
        },
    }

    word = re.sub(
        r"〈|～|\/.+|^.+・|\[.+?\]|.+,| |<.+?>|。|\n|\(.+?\)|【.+?】|〘.+?〙|［|］|（.+?）",
        "",
        word,
    )

    # Katakana to Hiragana Conversion
    versions.append((convert_word_to_hiragana(word), get_hiragana_only(reading)))
    versions.append((word.replace("ず", "づ"), reading.replace("づ", "ず")))
    versions.append((word.replace("づ", "ず"), reading.replace("づ", "ず")))

    versions.append((word.replace("じ", "ぢ"), reading.replace("じ", "ぢ")))
    versions.append((word.replace("ぢ", "じ"), reading.replace("ぢ", "じ")))

    # Number Replacement
    for num, kanji in numbers.items():
        if num in word:
            word = word.replace(num, kanji)
            versions.append((word, reading))

    # Handle words starting with "御"
    if word.startswith("御"):
        # I know this isn't the smartest check, but I'm not going to overengineer this.

        if "お" in reading:
            # We aren't changing the reading, so no need to reflect any changes
            versions.append(("お" + word[1:], reading[:]))

        if "ご" in reading:
            # We aren't changing the reading, so no need to reflect any changes
            versions.append(("ご" + word[1:], reading[:]))

    # Handle words starting with "お"
    if word.startswith("お"):
        versions.append((word[1:], reading[1:]))

    # Replace "いい" with "良い"
    if "いい" in word:
        ii_yoi_replaced_word = word.replace("いい", "良い")
        ii_yoi_replaced_reading = reading.replace("いい", "よい")

        # It might be listed as いい, or よい in the reading,
        # so account for both options.
        # If "いい" appears in the reading unrelated to 良い/いい, then it'll still get changed.
        # Again, I know this isn't the smartest thing to do, but I'm not going to overengineer this.
        # If you wish to contribute, and somehow make this take into account when いい in the reading
        # actually represents 良い in the word, you're welcome to make a PR. It'd be much appreciated.

        versions.append((ii_yoi_replaced_word, reading[:]))
        versions.append((ii_yoi_replaced_word, ii_yoi_replaced_reading))

    # Remove common suffixes
    # (!) We must reflect these changes in the reading too.
    suffixes = ["ような", "な", "だ", "と", "に", "した", "よう", "する", "さん"]
    for suffix in suffixes:
        if reading.endswith(suffix):
            # Sometimes decks have stupid hiragana.
            if word.endswith(suffix):
                no_suffix = word[: -len(suffix)]
            else:
                no_suffix = word[:]
            no_suffix_reading = reading[: -len(suffix)]

            if no_suffix:
                if no_suffix[-1] == "た":
                    normalized_no_suffix = no_suffix[:-1] + "る"
                    normalized_no_suffix = no_suffix_reading[:-1] + "る"

                    versions.append(
                        (normalized_no_suffix, no_suffix_reading)
                    )  # 生まれたよう→生まれる
                else:
                    versions.append((no_suffix, no_suffix_reading))
    versions.append((word, word))
    versions.append((word, ""))

    if word in word_to_readings_map:
        for possible_reading in word_to_readings_map[word]:
            versions.append((word, possible_reading))

    versions.append((reading, reading))
    # versions.append((word, ""))
    # versions.append((reading, reading))

    versions_final = []
    for version, version_reading in versions:
        if (version, version_reading) not in versions_final and version:
            versions_final.append((version, version_reading))

    return versions_final
    # return list(set([x for x in versions if x[0]]))  # Remove dupes and empty ones


def build_definition_html(data, text_mode_default=True):
    """
    Builds an HTML string for a word and its definitions, including a text mode toggle.
    This HTML will be used in the Anki card.

    Parameters:
        - data: dict containing dictionary information
        - text_mode_default: bool indicating whether text mode is initially enabled
    """

    if not data:
        return None

    guesses = []
    display = "none" if text_mode_default else "block"
    html = f"<div id='definitionsContainer' style='display:{display}; margin: 5px;'>"

    # Identify dictionaries marked as "guesses" and collect first non-guess definition for text mode
    first_non_guess_definition = ''
    for dictionary in data:
        for info in data[dictionary]:
            if info.get("tag") == "guess":
                guesses.append(dictionary)
            elif not first_non_guess_definition:
                # Capture the first non-guess definition if it exists
                first_non_guess_definition = "<br />As well as<br />".join(info["definitions"])

    # Fallback to the first guess definition if all are guesses
    if not first_non_guess_definition:
        first_non_guess_definition = "<br />As well as<br />".join(data[list(data.keys())[0]][0]["definitions"])

    if ":" in first_non_guess_definition:
        first_non_guess_definition = "".join(first_non_guess_definition.split(":")[1:])

    first_non_guess_definition = "<br /><br />" + first_non_guess_definition

    # Generate HTML for each dictionary entry
    for dictionary in data.keys():
        display = 'none' if dictionary in guesses else 'block'
        color = RED if dictionary in guesses else YELLOW
        html += (
            f"<div>"
            f"<button type='button' style='background-color: #{color}; border-radius: 5px; border-color: #{RED};' onclick=\"toggleDefinition('{dictionary}')\">{dictionary}</button>"
            f"<div id='{dictionary}' style='display:{display};'>"
        )

        for information in data[dictionary]:
            words = information["word"]
            reading = information["reading"]
            definitions = "<br />As well as<br />".join(information["definitions"])
            html += (
                f"<div>"
                f"<p><b>{words}</b> 【{reading}】:<br />{definitions}</p>"
                f"</div>"
            )
        html += "</div>"
        html += "</div>"

    # Wrap definitions in a container with an additional text mode toggle button
    if html:
        html += "</div>"
        display_opposite = "block" if text_mode_default else "none"
        mode_button_text = "Switch to Full Mode" if text_mode_default else "Switch to Single Mode"

        # Wrap all content and add the text mode content div with initial definition if needed
        html = (
            f"<div style='position: relative; border: 2px solid #{YELLOW}; border-radius: 10px; margin: 5px;'>"
            f"<button id='textModeToggle' type='button' style='position: absolute; top: 10px; right: 10px; background-color: #{YELLOW};' onclick='toggleTextMode()'>Switch to Full Mode</button>"
            f"{html}"
            f"<div id='textModeContent' style='display:{display_opposite}; margin: 10px;'>"
            f"{first_non_guess_definition}"
            f"</div>"
            "</div>"
        )

    else:
        html = None

    # Final wrap
    return html



def combine_dupes(data):
    combined_data = []
    definitions_map = {}

    for word, reading, definition_list in [
        (x["word"], x["reading"], x["definitions"]) for x in data
    ]:
        # Check if any definition in the current list matches an existing entry
        matched_key = None

        for def_key in definitions_map:
            if any(def_ in def_key for def_ in definition_list):
                matched_key = def_key
                break

        # If a match was found, append the word to the existing entry
        if matched_key:
            definitions_map[matched_key].append((word, reading))
        else:
            # Use the full list as the key in case of no matches
            definitions_map[tuple(definition_list)] = [(word, reading)]

    # Rebuild the combined list with merged words

    for definitions, words_and_readings in definitions_map.items():
        # for word_r
        words, readings = (
            [x[0] for x in words_and_readings],
            [x[1] for x in words_and_readings],
        )
        first_word = words[0]
        definitions = list(definitions)
        if len(words) == 1:
            combined_data.append(
                {
                    "word": first_word,
                    "readings": list(set(readings)),
                    "definitions": definitions,
                }
            )
        elif len(words) > 1:
            spelling_alternatives = [
                spelling
                for spelling, reading in words_and_readings[1:]
                if reading != spelling
            ]
            combined_data.append(
                {
                    "word": f"{first_word}"
                    f"{'(' + '・'.join(spelling_alternatives) + ')' if spelling_alternatives else ''}",
                    "readings": readings,
                    "definitions": definitions,
                }
            )

    return combined_data


def entries_with_reading(reading, big_data, dictionary):
    # Get entries with a specific reading, then sort
    entries = []

    # Iterate over all words in the specified dictionary
    if reading in big_data[dictionary]:
        for word in big_data[dictionary][reading]:
            # Check if the reading exists for the current word
            entries.append(
                {
                    "word": word,
                    "reading": reading,
                    "definitions": big_data[dictionary][reading][word],
                }
            )

        # Sort entries to prioritize exact matches (word == reading) first
        return combine_dupes(
            sorted(
                entries, key=lambda item: 0 if item["word"] != item["reading"] else 1
            )
        )

    return []


def get_definitions(
    word,
    reading,
    priority_order,
    big_data,
    word_to_readings_map,
    not_in_weblio,
    look_in_weblio,
    stop_at=-1
):
    """Finds a word's definitions using its possible versions and
    returns an HTML string with collapsible fields.
    """
    # print(word, reading)
    unique_versions = get_versions_of_word(word, reading, word_to_readings_map)

    # Ensure unique version readings
    # unique_versions = []
    # seen_readings = set()
    # for version, version_reading in versions:
    #     if version_reading not in seen_readings:
    #         unique_versions.append((version, version_reading))
    #         seen_readings.add(version_reading)

    return_data = {}
    found = False
    defs_found_counter = 0
    # Check local dictionaries in priority order
    for dictionary in [d for d in priority_order if d in big_data]:

        if stop_at > 0 and defs_found_counter >= stop_at:
            break

        try:
            mixed_versions = []
            hiragana_only_versions = []
            with_same_reading = None

            for version, version_reading in unique_versions:
                # Fetch entries that match the reading in the current dictionary
                hiragana_only = version == version_reading and re.search(
                    rf"^[{HIRAGANA}ー]+$", version_reading
                )
                if (
                    version_reading in big_data[dictionary]
                    and version in big_data[dictionary][version_reading]
                ):
                    with_same_reading = [
                        {
                            "word": version,
                            "readings": [version_reading],
                            "definitions": big_data[dictionary][version_reading][
                                version
                            ],
                            "tag": None
                        }
                    ]

                elif hiragana_only:
                    with_same_reading = entries_with_reading(
                        version_reading, big_data, dictionary
                    )
                    for x in with_same_reading:
                        x["tag"] = "guess"
                else:
                    continue

                if with_same_reading:
                    defs_found_counter += 1
                    break

            # Combine mixed versions first, then Hiragana-only versions
            already_seen = []

            # Process sorted entries
            if not with_same_reading:
                continue

            for information in with_same_reading:
                words = information["word"]
                reading = information["readings"][0]
                definitions = information["definitions"]
                tag = information["tag"]

                if definitions in already_seen:
                    continue
                else:
                    already_seen.append(already_seen)

                # Add definitions to return data
                if dictionary not in return_data:
                    return_data[dictionary] = []

                return_data[dictionary].append(
                    {"definitions": definitions, "word": words, "reading": reading, "tag": tag}
                )
                found = True

        except Exception as e:
            print(e)
            print(f"勘弁してくれ。{word}【{reading}】")
            raise e


    if look_in_weblio and not found:
        print(f"Looking for '{word}' in Weblio.")
        dictionary = "Weblio"
        if dictionary not in return_data:
            return_data[dictionary] = []

        for version, version_reading in unique_versions:
            if version not in not_in_weblio:
                if version[-1] == "。":
                    version = version[:-1]

                list_of_weblio_results, not_in_weblio = get_from_weblio(
                    version, big_data, not_in_weblio, desired_reading=version_reading
                )

                if list_of_weblio_results:
                    for (
                        la_palabra,
                        weblio_definition,
                        yomikata,
                    ) in list_of_weblio_results:
                        edit_big_data(
                            big_data,
                            dictionary,
                            yomikata,
                            la_palabra,
                            [weblio_definition],
                        )

                        return_data[dictionary].append(
                            {
                                "definitions": [weblio_definition],
                                "word": la_palabra,
                                "reading": yomikata,
                                "tag": None
                            }
                        )
                else:
                    # Try using the reading directly
                    list_of_weblio_results, not_in_weblio = get_from_weblio(
                        version_reading, big_data, not_in_weblio
                    )
                    if len(list_of_weblio_results) > 2:
                        list_of_weblio_results = list_of_weblio_results[:2]

                    if list_of_weblio_results:
                        for (
                            la_palabra,
                            weblio_definition,
                            yomikata,
                        ) in list_of_weblio_results:
                            edit_big_data(
                                big_data,
                                dictionary,
                                yomikata,
                                la_palabra,
                                [weblio_definition],
                            )
                            return_data[dictionary].append(
                                {
                                    "definitions": [weblio_definition],
                                    "word": la_palabra,
                                    "reading": yomikata,
                                    # ,
                                    "tag": None
                                }
                            )

    return return_data


def get_from_weblio(word, big_data, not_in_weblio, desired_reading=None):
    if word in not_in_weblio:
        return None, not_in_weblio

    list_of_weblio_results = scrape_weblio(word.strip(), desired_reading)
    if list_of_weblio_results:
        for la_palabra, weblio_definition, yomikata in list_of_weblio_results:
            if len(weblio_definition) > 600:
                continue  # Too long. Shitty parsing
            dictionary_path = "Weblio"

            weblio_definition = clean_definition(
                la_palabra, yomikata, weblio_definition, dictionary_path
            )
            edit_big_data(
                big_data, dictionary_path, word, yomikata, [weblio_definition]
            )
            edit_big_data(
                big_data, dictionary_path, la_palabra, yomikata, [weblio_definition]
            )
            with open("Weblio/term_bank_1.json", "w+", encoding="utf-8") as f:
                temp = []
                for word, readings in big_data["Weblio"].items():
                    for reading, definition_list in readings.items():
                        definition_text = "<br />".join(definition_list)
                        temp.append(
                            [
                                word if word else reading,
                                reading if yomikata else "",
                                "",
                                "",
                                "",
                                [definition_text],
                            ]
                        )
                json.dump(temp, f, ensure_ascii=False, indent=2)

                """
                "最中": {
                  "さいちゅう": [
                    "物事が行われていて、まだ終わらない段階。また、それがたけなわのとき。さなか。「試合の―に倒れる」"
                  ],
                  "さなか": [
                    "さいちゅう。まっさかり。「冬の―」"
                  ],
                  "もなか": [
                    "①米の粉をこね、薄くのばして焼いた皮にあんを入れた菓子。
                    <br /><br />②まんなか。
                    <br /><br />③まっさいちゅう。"
                  ]
                },
                """

        return list_of_weblio_results, not_in_weblio

    not_in_weblio.append(word)
    return None, not_in_weblio


def get_ref_numbers(referenced_word):
    """
    Fetches the reference numbers e.g. ① ❷
    from the given string
    """
    return re.search(rf"(?:(?:[{NUMBER_CHARS}])|(?:\d+️⃣))+$", referenced_word)


def fetch_entry_from_reference(reference_numbers: str, full_entry: str) -> str:
    """
    Takes the entire entry given to it,
    and returns the specific part of it that is required

    e.g.:

    ① Text
    ②
      ❶ text2
      ❷ text3

    fetch_entry_from_reference(that, "②❶") -> text2
    """

    if reference_numbers:
        reference_numbers_path = re.findall(r"〚(\d+)〛", reference_numbers)
        return get_entry(reference_numbers_path, full_entry)
    # print(type(full_entry))

    return full_entry


def link_up(
    word,
    reading,
    definition_original,
    dictionary_path,
    big_data,
    word_to_readings_map,
    not_in_weblio,
    look_in_weblio=False,
):
    # if dictionary_path == "旺文社国語辞典 第十一版":
    # return definition_original, dictionary_path
    """
    Take links to other entries in the target entry
    e.g. ⇒親 (link to 親)

    and add
    "Linked from 親's definition ...

    If there's a link number,
    e.g. ⇒親〚4〛
    We will take 親's number 4 definition using get_entry.
    """
    # Clean up formatting from the definition text
    super_original = definition_original[:]
    definition = definition_original[:]
    if definition == "":
        return None, dictionary_path

    definition = re.sub(rf"([{NUMBER_CHARS}])<br ?\/>", r"\1", definition)
    definition = re.sub(rf"([{NUMBER_CHARS}])\n", r"\1", definition)

    # Handle dictionary-specific reference standardization
    if not isinstance(dictionary_path, str):
        print("Dictionary path is not a string for some reason")
        print(f"{dictionary_path=}")
        dictionary_path = "大辞泉"

    definition = re.sub("「参考」", "", definition)

    # Search for reference pattern in the definition
    suffix = rf"(?:。|$|\n|<br ?\/>| |　|[{CLOSING_BRACKETS}{KANJI}{KANA}])"
    reference_matches = re.finditer(
        rf"⇒([^{OPENING_BRACKETS}{NUMBER_CHARS}。\n<〚]+)( \([あ-ゔ]+\) ?)?((?:〚\d〛)*){suffix}?",
        definition,
    )

    # ref_counter = len([x for x in reference_matches2])

    already_linked = list(set([word, reading]))

    # Process each reference found
    if reference_matches:
        for reference_match in reference_matches:
            referenced_word, furigana, reference_number_path = reference_match.groups()
            referenced_word = referenced_word.replace(" ", "")
            if referenced_word in already_linked:
                continue
            else:
                already_linked.append(referenced_word)

            # Skip unusually long matches
            if len(referenced_word) > 20:
                return definition, dictionary_path

            # Extract and clean furigana if present
            furigana = (
                re.search(rf"\(([{HIRAGANA}]+)\)", furigana).group(1)
                if furigana
                else ""
            )
            if furigana:
                readings = [furigana.replace(" ", "")]
            elif word_to_readings_map.get(referenced_word, []):
                readings = [
                    x.replace(" ", "")
                    for x in word_to_readings_map.get(referenced_word, [])
                ]
            elif re.search(rf"^[{HIRAGANA}]+$", referenced_word):
                readings = [referenced_word.replace(" ", "")]
            else:
                readings = []  # We don't know lol

            if readings:
                already_linked.extend(readings)
            # readings = [furigana] if furigana else word_to_readings_map.get(referenced_word, [])
            already_linked = list(set(already_linked))

            used_reading = None
            # Try to fetch the referenced word's definition
            ref_definition = ""
            ref_definitions = None
            for reading_found in readings:
                if reading_found in big_data[dictionary_path]:
                    if referenced_word in big_data[dictionary_path][reading_found]:
                        ref_definitions = big_data[dictionary_path][reading_found][
                            referenced_word
                        ]
                    elif word in big_data[dictionary_path][reading_found]:
                        # 案内（あんない・あない）みたいな？
                        ref_definitions = big_data[dictionary_path][reading_found][word]
                    elif len(big_data[dictionary_path][reading_found].keys()) == 1:
                        # There only is one definition
                        the_key = list(big_data[dictionary_path][reading_found].keys())[
                            0
                        ]
                        ref_definitions = big_data[dictionary_path][reading_found][
                            the_key
                        ]
                    if ref_definitions:
                        ref_definitions = [
                            fetch_entry_from_reference(
                                reference_number_path, ref_definition
                            )
                            for ref_definition in ref_definitions
                        ]
                        used_reading = reading_found
                        break

            # External lookup on Weblio if local lookup fails and `look_in_weblio` is True
            if (
                not ref_definitions
                and look_in_weblio
                and referenced_word not in not_in_weblio
            ):
                # Fetch Weblio results if available
                ref_definitions, not_in_weblio = get_from_weblio(
                    referenced_word, big_data, not_in_weblio, desired_reading=furigana
                )

                if ref_definitions:
                    # Add Weblio definitions to `big_data` and compile `ref_definition`
                    for la_palabra, ref_definition_text, yomikata in ref_definitions:
                        if ref_definition_text:
                            # Insert the fetched Weblio definition into `big_data`
                            edit_big_data(
                                big_data,
                                "Weblio",
                                la_palabra,
                                yomikata,
                                [fetch_entry_from_reference(ref_definition_text, "")],
                            )

            already_linked = []

            # If a referenced definition was successfully fetched
            if ref_definitions:
                # Process the reference definitions and append to the main definition text
                # print(ref_definition)

                # print(dictionary_path, referenced_word, ref_definition)
                more_than_one = len(ref_definitions) > 1

                for i, found_definition in enumerate(ref_definitions):
                    index = f"{i}. <br/>" if more_than_one else ""
                    #     word: str, reading: str, definition_text: str, dictionary_path: str
                    cleaned_found_definition = clean_definition(
                        referenced_word, used_reading, found_definition, dictionary_path
                    )
                    if cleaned_found_definition:
                        ref_definition += f"<br />{index}{cleaned_found_definition}"

                # Append linked information about the referenced definition
                if ref_definition:
                    if ref_definition in already_linked:
                        continue

                    already_linked.append(ref_definition)
                    definition += (
                        f"\n\n<hr>Linked {referenced_word}'s definition{reference_number_path}:"
                        f"\n{ref_definition}"
                    )

                    definition_original = definition

    # if len(already_linked) > 5:
    #     print(word, reading, already_linked)
    # Final cleanup and return
    definition_original = re.sub(r"(?:\n|<br />)+", "\n", definition_original)
    definition_original = "<br />".join(
        [x for x in definition_original.split("\n") if x != "└"]
    )

    if len(definition_original) > 3000:
        return super_original, dictionary_path

    return definition_original, dictionary_path


def process_deck(
    deck_file,
    vocab_field_name,
    reading_field_name,
    definitions_field_name,
    dictionary_priority_order,
    big_data,
    word_to_readings_map,
    not_in_weblio,
):
    """
    Processes an ANKI deck by adding monolingual definitions (XLSX version).

    Args:
    - deck_file (str): The file name of the ANKI deck (XLSX format).
    - vocab_field_name (str): Column name for words.
    - definitions_field_name (str): Column name for definitions.
    """
    deck_sorted = pd.read_excel(deck_file, index_col=None)

    deck_size = len(deck_sorted)
    progress_interval = deck_size // 10  # 10% progress intervals
    words = deck_sorted[vocab_field_name].unique()
    rows_to_drop = []
    for i, word in enumerate(words):
        # Identify duplicate rows and mark them for removal
        if (deck_sorted[vocab_field_name] == word).sum() > 1:
            indices = deck_sorted[deck_sorted[vocab_field_name] == word].index[1:]
            rows_to_drop.extend(indices)
        if word == vocab_field_name:
            rows_to_drop.append(i)

        # # Drop the marked rows from the sorted deck
    deck_cleaned = deck_sorted.drop(rows_to_drop)
    cleaned_definitions = []

    # Iterate through the cleaned deck for processing
    for i, row in deck_cleaned.iterrows():  # Change to deck_cleaned
        cleaned_word = row[vocab_field_name].split("/")[0]
        cleaned_reading = re.sub(
            r"(\(|（|＜).+?(\)|）|＞)", "", str(row[reading_field_name])
        )
        cleaned_reading = get_hiragana_only(cleaned_reading)
        monolingual_definition = row[definitions_field_name]

        if not isinstance(monolingual_definition, str):
            monolingual_definition = ""

        word_definitions = get_definitions(
            cleaned_word,
            cleaned_reading,
            dictionary_priority_order,
            big_data_dictionary,
            word_to_readings_map,
            not_in_weblio,
            look_in_weblio=False,
            stop_at=-1
        )
#!todo: if guessing reading, put a tag on it that says so
        already_seen = []
        for dictionary, dict_items in word_definitions.items():
            for j, information in enumerate(dict_items):
                word = information["word"].split("(")[0].strip()  # 可哀想 (可哀相)
                reading = information["reading"]  #   ↑ only this
                definitions = list(set(information["definitions"]))

                if definitions in already_seen:
                    word_definitions[dictionary][j] = {}
                    continue
                    # del word_definitions[dictionary][j]
                else:
                    already_seen.append(definitions)

                try:
                    for k, definition in enumerate(definitions):
                        if "⇒" in definition:
                            definition, _ = link_up(
                                word,
                                reading,
                                definition,
                                dictionary,
                                big_data_dictionary,
                                word_to_readings_map,
                                not_in_weblio,
                                look_in_weblio=False,
                            )

                            word_definitions[dictionary][j]["definitions"][k] = (
                                definition  # Update definition in place
                            )
                except Exception as e:
                    print(f"Couldn't link {word}【{reading}】")
                    raise e
                    print("oh no", definition, word, reading, "is die.")

        # if not word_definitions:
        # print(cleaned_word, cleaned_reading)

        # word_definitions[dictionary]
        for dictionary in word_definitions:
            word_definitions[dictionary] = [
                entry for entry in word_definitions[dictionary] if entry
            ]

        definition_html = build_definition_html(word_definitions)

        if definition_html:
            cleaned_definitions.append(
                "<" + definition_html.strip("<br />").strip("<br/>")
            )
        else:
            cleaned_definitions.append(None)
        # Show progress every 10%
        if i > 0 and i % progress_interval == 0:
            print(
                f"Progress: {i / len(deck_cleaned):.0%}"
            )  # Changed to len(deck_cleaned)

    # Update the definitions field in the DataFrame
    # only update where not None
    # cleaned_definitions = pd.Series(cleaned_definitions)

    deck_cleaned[definitions_field_name] = [
        new if new is not None else original
        for original, new in zip(
            deck_cleaned[definitions_field_name], cleaned_definitions
        )
    ]
    # deck_cleaned[definitions_field_name] = cleaned_definitions
    deck_cleaned = deck_cleaned.loc[:, ~deck_cleaned.columns.str.contains("^Unnamed")]

    output_file = f"[FIXED] {deck_file}"
    # print(deck_cleaned)

    deck_cleaned.to_excel(output_file, index=False)
    not_in_weblio = list(set(not_in_weblio))
    save_not_in_weblio(not_in_weblio)
    return deck_sorted


def save_not_in_weblio(not_in_weblio):
    with open("not_in_weblio.json", "w+", encoding="utf-8") as f:
        json.dump(not_in_weblio, f, ensure_ascii=False)


def load_not_in_weblio():
    not_in_weblio_data = []
    with open("not_in_weblio.json", "r", encoding="utf-8") as f:
        not_in_weblio_data = json.load(f)
    return not_in_weblio_data


def load_word_to_readings_map():
    load_word_to_readings_map = {}
    with open("word_to_readings_map.json", "r", encoding="utf-8") as f:
        load_word_to_readings_map = json.load(f)
    return load_word_to_readings_map


def change_to_monolingual(deck_name, big_data, not_in_weblio, word_to_readings_map, field_settings):
    """
    Converts an ANKI deck from bilingual to monolingual using dictionary files.

    Args:
    - deck_name (str): The name of the ANKI deck (without extension).
    """

    vocab_field_name=       field_settings["vocab"]                 # VocabKanji
    reading_field_name=     field_settings["reading"]  #    "Reading",    # VocabFurigana
    definitions_field_name= field_settings["definition"]  # "Meaning",  # VocabDef

    print(f"Converting {deck_name}...")
    # anki_convert(f"{deck_name}.apkg", out_file=f"{deck_name}.xlsx")
    # # Read the .txt file, automatically using the first row as header
    df = pd.read_csv(
        f"txt_exports/{deck_name}.txt", sep="\t", index_col=None
    )  # Change 'sep' if needed based on your file
    # Save to Excel

    df.to_excel(f"{deck_name}.xlsx", index=True)
    # Word  Reading Pitch   Meaning tags

    process_deck(
        deck_file=f"{deck_name}.xlsx",
        vocab_field_name=vocab_field_name,  # VocabKanji
        reading_field_name=reading_field_name,  # VocabFurigana
        definitions_field_name=definitions_field_name,  # VocabDef
        dictionary_priority_order=PRIORITY_ORDER,
        big_data=big_data,
        word_to_readings_map=word_to_readings_map,
        not_in_weblio=not_in_weblio,
    )

    # Convert to CSV and cleanup
    output_file = f"[FIXED] {deck_name}.xlsx"
    final_xlsx_file = pd.read_excel(output_file, index_col=None)
    final_xlsx_file.to_csv(f"[FIXED] {deck_name}.csv", index=False, sep="\t")

    os.remove(f"{deck_name}.xlsx")
    os.remove(output_file)    
    # Add script for toggle functions

    print(f"Conversion complete for {deck_name}!\n\n")


if __name__ == "__main__":
    big_data_dictionary = load_big_data(
        big_data_dictionary=big_data_dictionary, override=False
    )
    not_in_weblio = load_not_in_weblio()
    word_to_readings_map = load_word_to_readings_map()
    # save_to_big_data(big_data_dictionary)


    # vocab_field_name=       field_settings["vocab"]                 # VocabKanji
    # reading_field_name=     field_settings["reading"]  #    "Reading",    # VocabFurigana
    # definitions_field_name= field_settings["definition"]  # "Meaning",  # VocabDef


    field_settings = {
        "vocab": "VocabKanji",
        "reading": "VocabFurigana",
        "definition": "VocabDef"
    }

    deck_names = ["[JP-JP] N1", "[JP-JP] N2", "[JP-JP] N3", "[JP-JP] N4", "[JP-JP] N5", "物語"]
    for deck in deck_names:
        change_to_monolingual(deck, big_data_dictionary, not_in_weblio, word_to_readings_map, field_settings)
    
    field_settings = {
        "vocab": "Word",
        "reading": "Reading",
        "definition": "Meaning"
    }

    change_to_monolingual("N5-3", big_data_dictionary, not_in_weblio, word_to_readings_map, field_settings)

    script = """<script>
function toggleDefinition(id) {
    var elem = document.getElementById(id);
    elem.style.display = (elem.style.display === "none") ? "block" : "none";
}

function toggleTextMode() {
    var definitionsContainer = document.getElementById("definitionsContainer");
    var textModeContent = document.getElementById("textModeContent");
    var isTextMode = textModeContent.style.display === "block";
    var textModeButton = document.getElementById("textModeToggle");

    if (isTextMode) {
        // Switch to full mode
        definitionsContainer.style.display = "block";
        textModeContent.style.display = "none";
        textModeButton.innerText = "Switch to Single Mode";
    } else {
        // Switch to text mode
        definitionsContainer.style.display = "none";
        textModeButton.innerText = "Switch to Full Mode";

        // Try to get the first non-guess dictionary definition
        var firstDefinitionElem = document.querySelector("#definitionsContainer div:not([style*='color: #{yellow}']) p");

        // Fallback to the first definition if all are guesses (all red)
        if (!firstDefinitionElem) {
            firstDefinitionElem = document.querySelector("#definitionsContainer div p");
        }

        // Display the extracted definition in text mode
        if (firstDefinitionElem) {
            var firstDefinition = firstDefinitionElem.innerHTML;
            textModeContent.innerText = "\\\\n" + firstDefinition.split(":")[1].replaceAll("<br>", "\\\\n");
            textModeContent.style.display = "block";
        }
    }
}
</script>
    """.replace("{red}", f"{RED}").replace("{yellow}", f"{YELLOW}")
    print(f"Add this script to back card template:\n{script}")

    # word, reading = "依代", "よりしろ"

    # word_definitions = get_definitions(
    #     word,
    #     reading,
    #     PRIORITY_ORDER,
    #     big_data_dictionary,
    #     word_to_readings_map,
    #     not_in_weblio,
    #     look_in_weblio=False,
    #     stop_at=2
    # )
    # already_seen = []

    # for dictionary, dict_items in word_definitions.items():
    #     for j, information in enumerate(dict_items):
    #         word = information["word"].split("(")[0].strip()  # 可哀想 (可哀相)
    #         reading = information["reading"]  #   ↑ only this
    #         definitions = list(set(information["definitions"]))

    #         if definitions in already_seen:
    #             word_definitions[dictionary][j] = {}
    #             continue
    #             # del word_definitions[dictionary][j]
    #         else:
    #             already_seen.append(definitions)

    #         try:
    #             for k, definition in enumerate(definitions):
    #                 if "⇒" in definition:
    #                     definition, _ = link_up(
    #                         word,
    #                         reading,
    #                         definition,
    #                         dictionary,
    #                         big_data_dictionary,
    #                         word_to_readings_map,
    #                         not_in_weblio,
    #                         look_in_weblio=False,
    #                     )

    #                     word_definitions[dictionary][j]["definitions"][k] = (
    #                         definition  # Update definition in place
    #                     )
    #         except Exception as e:
    #             print(f"Couldn't link {word}【{reading}】")
    #             raise e
    #             print("oh no", definition, word, reading, "is die.")

    # # if not word_definitions:
    # # print(cleaned_word, cleaned_reading)

    # # word_definitions[dictionary]
    # for dictionary in word_definitions:
    #     word_definitions[dictionary] = [
    #         entry for entry in word_definitions[dictionary] if entry
    #     ]

    # definition_html = build_definition_html(word_definitions)

    # with open("a.html", "w", encoding="utf-8") as f:
    #     f.write(definition_html)
