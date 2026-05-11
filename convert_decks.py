"""
The main script.
"""

import json
import os
import re

import pandas as pd

from scraper import (
    convert_word_to_hiragana,
    get_hiragana_only,
)

from math import exp
from bs4 import BeautifulSoup 

from convert_to_big_data import (
    NUMBER_CHARS,
    KANJI,
    HIRAGANA,
    KANA,
    OPENING_BRACKETS,
    CLOSING_BRACKETS,
    get_entry,
    PRIORITY_ORDER,
    load_big_data,
    RED, YELLOW, GRAY,
    SUFFIX,
    PREFIX,
    recursive_nesting_by_category,
    dict_to_text,
)

# from AnkiTools import anki_convert

big_data_dictionary = {}


# バグ　バグる
# グーグル ググる　ggrks
#
def get_versions_of_word(word, reading, word_to_readings_map, extended=False):
    """
    Generates possible versions of the word by applying various transformations.

    Args:
    - word (str): The word to transform.

    Returns:
    - list: A list of possible word versions.
    """
    # original_word = word[:]  # Preserve the original word
    versions = [(word, reading)]

    reading = get_hiragana_only(reading)

    versions.append((word, reading))

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


    # Katakana to Hiragana Conversion
    versions.append((word.replace("ず", "づ"), reading.replace("づ", "ず")))
    versions.append((word.replace("づ", "ず"), reading.replace("ず", "づ")))
    versions.append((word.replace("づく", "付く"), reading))
    versions.append((word.replace("づける", "付ける"), reading))

    versions.append((word.replace("じ", "ぢ"), reading.replace("じ", "ぢ")))
    versions.append((word.replace("ぢ", "じ"), reading.replace("ぢ", "じ")))

    versions.append((word.replace("がたい", "難い"), reading))
    versions.append((word.replace("やすい", "易い"), reading))

    # Number Replacement


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
    # ズバズバ言う
    if reading and word.endswith("言う"):
        versions.append((word[:-2], reading[:-2]))


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

    # キーボードー
    if reading and reading[-1] == "ー":
        versions.append((word[:-1], reading[:-1]))

    # Remove common suffixes
    # (!) We must reflect these changes in the reading too.
    potential_suffixes = ["ような", "な", "だ", "と", "に", "した", "よう", "になる", "にする", "する", "さん"]

    for suffix in [potential_suffix for potential_suffix in potential_suffixes if word.endswith(potential_suffix)]:

        if word.endswith(suffix):
            no_suffix = word[: -len(suffix)]
        else:
            no_suffix = word[:]

        no_suffix_reading = reading[: -len(suffix)]

        if no_suffix:
            if no_suffix[-1] == "た":
                normalized_no_suffix = no_suffix[:-1] + "る"
                normalized_no_suffix_reading = no_suffix_reading[:-1] + "る"
                versions.append(
                    (normalized_no_suffix, normalized_no_suffix_reading)
                )
            else:
                versions.append((no_suffix, no_suffix_reading))


    versions.append((word, word))
    versions.append((word, ""))

    if word != reading and not re.sub(rf"[{HIRAGANA}]+", "", word) == reading: # テンパる→てんぱる
        versions.append((convert_word_to_hiragana(word), get_hiragana_only(reading)))

    if word in word_to_readings_map and not reading:
        for possible_reading in word_to_readings_map[word]:
            versions.append((word, possible_reading))

    find_numbers = re.compile(r"[0-9０-９]")
    for w, r in versions.copy():
        if extended:
            versions.append((r, r))
            if r and "が" in r and "が" in w:
                versions.append((w.replace("が", ""), r.replace("が", "")))

        if "々" in w:
            versions.append((re.sub("(.)々", r"\1\1", r), r))

        if find_numbers.search(w):
            for num, kanji in numbers.items():
                if num in word:
                    word = word.replace(num, kanji)
                    versions.append((word, reading))

    versions_final = []

    for version in versions:

        if version and version not in versions_final:
            versions_final.append(version)

    return versions_final


def parse_definition_html(html):
    soup = BeautifulSoup(html, "html.parser")

    result = {}

    buttons = soup.find_all(
        "button",
        onclick=re.compile(r"toggleDefinition")
    )

    for button in buttons:
        dictionary = button.get_text(strip=True)

        onclick = button.get("onclick", "")
        match = re.search(
            r"toggleDefinition\('(.+?)'\)",
            onclick
        )

        if not match:
            continue

        div_id = match.group(1)

        container = soup.find("div", id=div_id)

        if not container:
            continue

        entries = []

        # =========================
        # Special handling: Kenrowa
        # =========================
        if dictionary == "Kenrowa":

            text = container.get_text("\n").strip()

            text = "\n".join(
                line.strip()
                for line in text.splitlines()
                if line.strip()
            )

            match = re.search(
                r"^(.*?)\s*【(.*?)】\s*(.*)$",
                text,
                re.DOTALL
            )

            if match:
                reading = match.group(1).strip()
                word = match.group(2).strip()
                definitions = match.group(3).strip()

                entries.append({
                    "word": word,
                    "reading": reading,
                    "definitions": definitions
                })

            else:
                entries.append({
                    "word": "",
                    "reading": "",
                    "definitions": text
                })

            result[dictionary] = entries
            continue

        # ====================================
        # Standard structured dictionary parse
        # ====================================

        for entry_div in container.find_all("div", recursive=False):

            p = entry_div.find("p")

            if p:
                content = p.decode_contents()
            else:
                content = entry_div.decode_contents()

            text = BeautifulSoup(
                content,
                "html.parser"
            ).get_text("\n").strip()

            text = "\n".join(
                line.strip()
                for line in text.splitlines()
                if line.strip()
            )

            word = ""
            reading = ""
            definitions = ""

            # Standard:
            # 漢字【よみ】:
            standard_match = re.search(
                r"^(.*?)【(.*?)】[:：]?\s*(.*)$",
                text,
                re.DOTALL
            )

            if standard_match:
                word = standard_match.group(1).strip()
                reading = standard_match.group(2).strip()
                definitions = standard_match.group(3).strip()

            else:
                # Reverse:
                # よみ 【漢字】
                reverse_match = re.search(
                    r"^(.*?)\s*【(.*?)】\s*(.*)$",
                    text,
                    re.DOTALL
                )

                if reverse_match:
                    reading = reverse_match.group(1).strip()
                    word = reverse_match.group(2).strip()
                    definitions = reverse_match.group(3).strip()

                else:
                    # Completely unstructured entry
                    definitions = text

            definitions = definitions.replace(
                "THIS IS A GUESS ENTRY",
                ""
            ).strip()

            # Split multiple definitions
            split_definitions = re.split(
                r"(?:\n|<br\s*/?>)*As well as(?:\n|<br\s*/?>)*",
                definitions
            )

            split_definitions = [
                d.strip()
                for d in split_definitions
                if d.strip()
            ]

            if len(split_definitions) == 1:
                split_definitions = split_definitions[0]

            entry = {
                "word": word,
                "reading": reading,
                "definitions": split_definitions
            }

            if "THIS IS A GUESS ENTRY" in text:
                entry["tag"] = "guess"

            entries.append(entry)

        result[dictionary] = entries

    return result

def build_definition_html(data, text_mode_default=True):
    if not data:
        return None

    guesses = []
    first_non_guess_definition = ''

    # Identify guesses and first non-guess definition
    for dictionary in data:
        for info in data[dictionary]:
            if info.get("tag") == "guess":
                guesses.append(dictionary)
            elif not first_non_guess_definition:
                definitions = info.get("definitions", "")
                first_non_guess_definition = (
                    "<br />As well as<br />".join(definitions)
                    if isinstance(definitions, list)
                    else definitions
                )

    # Fallback to guess definition if no non-guess found
    if not first_non_guess_definition:
        for dictionary in data:
            if data[dictionary]:
                definitions = data[dictionary][0].get("definitions", "")
                first_non_guess_definition = (
                    "<br />As well as<br />".join(definitions)
                    if isinstance(definitions, list)
                    else definitions
                ) + "<br />Warning: This is a guess entry"
                break

    if not first_non_guess_definition:
        return
                

    definitions_container = ""

    
    # Ensure Kenrowa appears first if present
    ordered_items = sorted(
        data.items(),
        key=lambda item: (item[0] != "Kenrowa", item[0])
    )


    for dictionary, entries in ordered_items:
        is_guess = dictionary in guesses
        display = "none" if is_guess else "block"
        color = RED if is_guess else YELLOW  # Red for guesses, yellow otherwise

        current_dict_definitions = ""
        for info in entries:
            if not info:
                continue
            words = info["word"]
            reading = info["reading"]
            definitions = info["definitions"]
            if isinstance(definitions, list):
                definitions = "<br />As well as<br />".join(definitions)
            
            # Remove redundant word/reading pairings
            definitions = re.sub(rf"{words}【{reading}】(:|：|とは、?)?", "", definitions)
            definitions = re.sub(rf"{reading}【{words}】(:|：|とは、?)?", "", definitions)

            guess_note = "<p>THIS IS A GUESS ENTRY</p>" if is_guess else ""
            current_dict_definitions += (
                f"<div>"
                f"<p><b>{words}</b>【{reading}】:<br />{definitions}</p>"
                f"{guess_note}"
                f"</div>"
            )

        definitions_container += (
            f"<button type='button' style='background-color: #{color}; color: #FFF; padding:10px; border-radius: 10px;' "
            f"onclick=\"toggleDefinition('{dictionary}')\">{dictionary}</button>"

            f"<div id='{dictionary}' style='display:{display};'>"
            f"{current_dict_definitions}</div><br />"
        )

    # Wrap content
    display_main = "none" if text_mode_default else "block"
    display_text_mode = "block" if text_mode_default else "none"
    mode_button_text = "Switch to Full Mode" if text_mode_default else "Switch to Single Mode"

    html = (

        f"<div class='overall-border'>"
        f"<button id='textModeToggle' type='button' "
        f"onclick='toggleTextMode()' style='background-color: #000; color: #FFF; position: relative; top: 4px; right: 4px; float: right; padding:10px; border-radius: 10px;'>{mode_button_text}</button>"

        f"<div id='definitionsContainer' style='display:{display_main};'>{definitions_container}</div>"
        f"<div id='textModeContent' style='display:{display_text_mode};'><br/><br/>{first_non_guess_definition}</div>"

        "</div>"
    )

    return html


def makes_no_fucking_sense(word, reading) -> bool:

    if word != reading and re.sub(rf"[^{HIRAGANA}]+", "", word) == reading:
        return True

    return False 

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
                    "all_spellings": [first_word]
                }
            )
        elif len(words) > 1:
            spelling_alternatives = [
                spelling
                for spelling, reading in words_and_readings[1:]
                if reading != spelling
            ]
            spelling_alternatives = [
                spelling for spelling in 
                spelling_alternatives
                if spelling
            ]
            combined_data.append(
                {
                    "word": f"{first_word}"
                    f"{'(' + '・'.join(spelling_alternatives) + ')' if spelling_alternatives else ''}",
                    "readings": readings,
                    "definitions": definitions,
                    "all_spellings": [first_word, *spelling_alternatives]
                }
            )

    return combined_data


def entries_with_reading(reading, big_data, dictionary, word_to_readings_map=None):
    # Get entries with a specific reading, then sort
    entries = []
    if word_to_readings_map:
        # Get all possible readings by extracting the second element from each result of get_versions_of_word
        # Filter out None values and remove duplicates by converting to a set
        possible_readings = set(
            filter(
                None, 
                [version[1] for version in get_versions_of_word(reading, reading, word_to_readings_map, extended=True)]
            )
        )
        # Convert the set to a sorted list based on the length of each reading, in descending order
        sorted_readings = sorted(possible_readings, key=len, reverse=True)
    else:
        # Put our only reading in the list so we can "iterate" over it
        possible_readings = [reading]

    # Iterate over all words in the specified dictionary
    for possible_reading in possible_readings:
        if possible_reading in big_data[dictionary]:
            for word in big_data[dictionary][possible_reading]:
                # Check if the reading exists for the current word
                entries.append(
                    {
                        "word": word,
                        "reading": possible_reading,
                        "definitions": big_data[dictionary][possible_reading][word],
                        "tag": None
                    }
                )

            # Sort entries to prioritize exact matches (word == reading) first
            return combine_dupes(
                sorted(
                    entries, key=lambda item: 0 if item["word"] != item["reading"] else 1
                )
            )

    return []


def similarity_score(str1, str2):
    """Calculate similarity between two strings by the number of matching characters."""
    # Convert strings to sets to get unique characters in each
    set1, set2 = set(str1), set(str2)
    # Find the intersection of the two sets (common characters)
    common_characters = set1.intersection(set2)
    if len(set1) == 0 and len(set2) == 0:
        return 1
        # Both are the same 

    similarity_score = len(common_characters) / max(len(set1), len(set2))
    return similarity_score


def get_definitions(
    word,
    reading,
    priority_order,
    big_data,
    word_to_readings_map,
    stop_at=-1
):
    """Finds a word's definitions using its possible versions and
    returns an HTML string with collapsible fields.
    """

    word = re.sub(
        r"〈|～|\/.+|^.+・|\[[^\]]+?\]|.+,| |<[^>]+?>|。|\n|\([^\)].+?\)|【[^】]+?】|〘[^〙]+?〙|［|］|（[^）]+?）|<",
        "",
        word,
    )
    reading = re.sub(
        r"〈|～|\/.+|^.+・|.+,| |。|\n|\([^\)]+?\)|【[^】]+?】|〘[^〙]+?〙|［|］|（[^）]+?）",
        "",
        reading,
    )

    unique_versions = get_versions_of_word(word, reading, word_to_readings_map)

    return_data = {}
    found = False
    defs_found_counter = 0
    # Check local dictionaries in priority order
    for dictionary in priority_order:

        if stop_at > 0 and defs_found_counter >= stop_at:
            break

        try:
            mixed_versions = []
            hiragana_only_versions = []
            with_same_reading = None

            for version, version_reading in unique_versions:
                # Fetch entries that match the reading in the current dictionary
                hiragana_only = version == version_reading and bool(re.fullmatch(rf"[{HIRAGANA}]+", version_reading))
                is_hiragana_only_but_not_word = hiragana_only and version != word


                if version_reading and makes_no_fucking_sense(version, version_reading):
                    print(f"{version}【{version_reading}】 make no fucking sense")
                    continue

                if (
                    version_reading in big_data[dictionary]
                    and version in big_data[dictionary][version_reading]
                ):
                    with_same_reading = [
                        {
                            "word": version,
                            "readings": [version_reading],
                            "definitions": big_data[dictionary][version_reading][version],
                            "tag": "guess" if is_hiragana_only_but_not_word else None
                        }
                    ]
                    # 1 version found
                    defs_found_counter += 1
                    break

                is_similar = False
                if version_reading in big_data[dictionary]:
                    for word_with_reading in big_data[dictionary][version_reading]:
                        if similarity_score(version, word_with_reading) > 0.65:
                            is_similar = True

                            break

                if hiragana_only or is_similar:
                    with_same_reading = entries_with_reading(
                        version_reading, big_data, dictionary, word_to_readings_map
                    )
                    if with_same_reading:
                        defs_found_counter += 1

                        def has_the_word(spellings, word):
                            return any([x for x in spellings if x == word])

                        actually_matches = [a for a in with_same_reading if has_the_word(a["all_spellings"], word) or has_the_word(a["all_spellings"], version)]
                        if len(actually_matches) > 0:
                            with_same_reading = actually_matches[:]
                        else:    
                            for x in with_same_reading:      
                                x["tag"] = "guess"
                        # Stop at 1 version found

                        break

                else:
                    continue

                                
            # Combine mixed versions first, then Hiragana-only versions
            already_seen = []

            # Process sorted entries
            if not with_same_reading:
                continue

            for information in with_same_reading:
                words = information["word"]
                reading_found = information["readings"][0] if reading not in information["readings"] else reading
                definitions = information["definitions"]
                tag = information.get("tag")
                if not tag and reading_found != reading:
                    tag = "guess"

                if definitions in already_seen:
                    continue
                else:
                    already_seen.append(already_seen)

                if dictionary not in return_data:
                    return_data[dictionary] = [] 

                if isinstance(definitions, str):
                    definition = [definitions]

                return_data[dictionary].append(
                    {"definitions": [d for d in definitions if d != "⇒"], "word": words, "reading": reading_found, "tag": tag}
                )
                found = True

        except Exception as e:
            print(e)
            print(f"エラー。{word}【{reading}】 - 【{reading_found}】")

    return return_data

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

    return full_entry


def link_up(
    word,
    reading,
    definition_original,
    dictionary_path,
    big_data,
    word_to_readings_map
):
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
        return definition, dictionary_path

    definition = definition.split("<br /> Linked")[0]
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
        rf"⇒([^{OPENING_BRACKETS}{NUMBER_CHARS}。\n<〚]+)( ?\([ぁ-ゔ]+\) ?)?((?:〚\d〛)*)(?:{suffix}|<br />|$)?",
        definition,
    )

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

            elif re.fullmatch(rf"[{HIRAGANA}]+", referenced_word):
                readings = [referenced_word.replace(" ", "")]
            else:
                readings = []  # We don't know lol

            if readings:
                already_linked.extend(readings)

            already_linked = list(set(already_linked))

            used_reading = None
            # Try to fetch the referenced word's definition
            ref_definition = ""
            ref_definitions = None
            for reading_found in readings:
                if dictionary_path not in big_data:
                    dictionary_paths = []
                else:
                    dictionary_paths = [dictionary_path]                    

                for d_p in dictionary_paths:
                    if reading_found in big_data[d_p]:
                        if referenced_word in big_data[d_p][reading_found]:
                            ref_definitions = big_data[dictionary_path][reading_found][
                                referenced_word
                            ]

                        elif word in big_data[d_p][reading_found] and reading_found != reading:
                            # 案内（あんない・あない）みたいな？
                            ref_definitions = big_data[d_p][reading_found][word]

                        elif len(big_data[d_p][reading_found].keys()) == 1:
                            # There only is one definition
                            the_key = list(big_data[d_p][reading_found].keys())[
                                0
                            ]
                            ref_definitions = big_data[d_p][reading_found][
                                the_key
                            ]


                        ref_definitions = list(set(ref_definitions if ref_definitions else []))

                        if ref_definitions:
                            ref_definitions = [
                                fetch_entry_from_reference(
                                    reference_number_path, ref_definition
                                )
                                for ref_definition in ref_definitions
                            ]
                            # Filter "just links" out. Example:
                            # Linked 輸出【しゅしゅつ】
                            # ⇒ゆしゅつ (輸出)
                            ref_definitions = [
                                definition for definition in ref_definitions 
                                if not re.fullmatch(rf"(?:^|<br />|\n)⇒[a-zA-Z{KANJI}{KANA}]+(?: \(.+?\) ?)?(?:{SUFFIX}|$)", definition)
                            ]


                            if ref_definitions: 
                                used_reading = reading_found
                                break

            # If a referenced definition was successfully fetched
            if ref_definitions:

                # Original word?
                if referenced_word == word and used_reading == reading and used_reading:
                    continue

                # Process the reference definitions and append to the main definition text
                ref_definition = f"<br /> Linked {referenced_word}【{used_reading}】" + (reference_number_path if reference_number_path else '')

                found = False
                more_than_one = len(ref_definitions) > 1
                ref_definitions = list(set(ref_definitions if ref_definitions else []))
                for i, found_definition in enumerate(ref_definitions):

                    index = f"{i}. <br/>" if more_than_one else ""
                    found_definition = found_definition.split("<br /> Linked")[0]
                    definition_dict = recursive_nesting_by_category(found_definition)
                    if isinstance(definition_dict, dict):
                        cleaned_found_definition = dict_to_text(definition_dict)
                    else:
                        cleaned_found_definition = definition_dict

                    if cleaned_found_definition in already_linked:
                        continue

                    already_linked.append(cleaned_found_definition)

                    if cleaned_found_definition:
                        ref_definition += f"<br />{index}{cleaned_found_definition}"
                        found = True

                # Append linked information about the referenced definition
                if found:
                    definition_original += ref_definition


            # ほんまによくわからんがダブっちゃうんだよな。already_linkedで縛っても。
    # Append linked information about the referenced definition
    splits = [  
                x for x in re.sub(r"(?:\n|<br />)+", "<br />", definition_original)
                             .replace("<br/>", "<br />")
                             .replace("<br>", "<br />")
                             .split("<br /> Linked")
                if x != "└" 
             ]

    already_seen = []
    for part in splits:
        if part in already_seen:
            continue
        already_seen.append(part)

    definition_original = "<br />Linked".join(already_seen)

    if len(definition_original) > 3000:
        return super_original, dictionary_path

    return definition_original, dictionary_path

def process_deck(
    deck,
    vocab_field_name,
    reading_field_name,
    definitions_field_name,
    dictionary_priority_order,
    big_data,
    word_to_readings_map,
):
    """
    Processes an ANKI deck by adding monolingual definitions (XLSX version).

    Args:
    - deck_file (str): The file name of the ANKI deck (XLSX format).
    - vocab_field_name (str): Column name for words.
    - definitions_field_name (str): Column name for definitions.
    """
    # deck = pd.read_excel(deck_file, index_col=None)
    deck_size = len(deck)
    progress_interval = deck_size // 10  # 10% progress intervals
    words = deck[vocab_field_name].unique()
    rows_to_drop = []
    for i, word in enumerate(words):
        # Identify duplicate rows and mark them for removal
        if (deck[vocab_field_name] == word).sum() > 1:
            indices = deck[deck[vocab_field_name] == word].index[1:]
            rows_to_drop.extend(indices)
        if word == vocab_field_name:
            rows_to_drop.append(i)

        # # Drop the marked rows from the sorted deck
    deck_cleaned = deck.drop(rows_to_drop)
    cleaned_definitions = []

    # Iterate through the cleaned deck for processing
    for i, row in deck_cleaned.iterrows():  # Change to deck_cleaned
        cleaned_word = re.sub(
            r"\[.+?\]", "", str(row[vocab_field_name])
        )
        cleaned_word = str(row[vocab_field_name]).split("/")[0].split("・")[0]

        cleaned_reading = re.sub(r"\[(.+?),.+?\]", r"\1", str(row[reading_field_name]) if str(row[reading_field_name]) else "")
        cleaned_reading = re.sub(r"\[.+?<br>([^<]+?)(?:<br>.+?)?\]", r"[\1]", cleaned_reading)

        cleaned_reading = re.sub(
            r"(?:\(|（|＜|<)[^\)）＞>]+?(?:\)|）|＞|>)", "", cleaned_reading
        ).strip(">").strip("<")

        cleaned_reading = get_hiragana_only(cleaned_reading)

        if not cleaned_word or cleaned_word == 'nan':
            cleaned_word = cleaned_reading
            
        monolingual_definition = row[definitions_field_name]


        if not isinstance(monolingual_definition, str):
            monolingual_definition = ""

        word_definitions = get_definitions(
            cleaned_word,
            cleaned_reading,
            dictionary_priority_order,
            big_data,
            word_to_readings_map,
            stop_at=-1
        )

        already_seen = []
        similarity_debuf = {}
        for dictionary, dict_items in word_definitions.items():
            for j, information in enumerate(dict_items):
                word = information["word"].split("(")[0].strip()  # 可哀想 (可哀相)
                reading = information["reading"]  #   ↑ only this
                definitions = list(set(information["definitions"]))

                if definitions in already_seen:
                    word_definitions[dictionary][j] = {}
                    continue
                else:
                    already_seen.append(definitions)

                # Definition is simply a link + limit to 3
                # definitions = [defi for defi in definitions if not re.fullmatch(rf"⇒[a-zA-Z{KANJI}{KANA}]+(?: ?\(.+?\) ?)?(?:{SUFFIX}|$)", defi)][:3]
                definitions = definitions[:3]
                
                for k, definition in enumerate(definitions):
                    try:
                        if "⇒" in definition:
                            definition, _ = link_up(
                                word,
                                reading,
                                definition,
                                dictionary,
                                big_data_dictionary,
                                word_to_readings_map,
                            )

                            word_definitions[dictionary][j]["definitions"][k] = (
                                definition  # Update definition in place
                            )
                    except Exception as e:
                        print(f"Couldn't link {word}【{reading}】")
                        print("oh no", definition, word, reading, "is die.", dictionary)
                        raise e


        for dictionary in word_definitions:
            word_definitions[dictionary] = [
                entry for entry in word_definitions[dictionary] if entry
            ]

            if not word_definitions[dictionary]:
                similarity_debuf[dictionary] = 0
                continue

            # All have at least 1
            reading = word_definitions[dictionary][0]["reading"]
            word = word_definitions[dictionary][0]["word"]

            similarity_debuf[dictionary] = exp(1 - similarity_score(reading, cleaned_reading))
            similarity_debuf[dictionary] += exp(1 - similarity_score(word, cleaned_word))


        def get_total_length(entry):
            length = 0
            for word in entry:
                # print(word)
                length += len("".join(word["definitions"]))
            return length

        def get_index(dictionary):
            if dictionary not in dictionary_priority_order:
                return 0
            return dictionary_priority_order.index(dictionary)

        def get_new_index(item):

            definitions = item[1]
            dictionary_name = item[0]

            length_debuf = get_total_length(definitions)//100
            priority_index = get_index(dictionary_name) 
            priority_debuf = len(dictionary_priority_order) if any([d["tag"] for d in definitions]) else 0
            return length_debuf+priority_index+priority_debuf+similarity_debuf[dictionary_name]



        original = word_definitions.copy()
        word_definitions = dict(sorted(word_definitions.items(), 
                key=lambda item: get_new_index(item)))

        definition_html = build_definition_html(word_definitions)

        if definition_html:
            cleaned_definitions.append(
                definition_html
            )
            # print(cleaned_word, definition_html)
        else:
            print("Didn't find", cleaned_word)
            # print(cleaned_word)
            cleaned_definitions.append(None)
        # Show progress every 10%
        if i > 0 and i % progress_interval == 0:
            print(
                f"Progress: {i / len(deck_cleaned):.0%}"
            )  # Changed to len(deck_cleaned)

    # Update the definitions field in the DataFrame
    # only update where not None
    # cleaned_definitions = pd.Series(cleaned_definitions)

    # new + "<hr><div style='color: gray'>" + original + "</div>" 

    deck_cleaned.loc[:, definitions_field_name] = [
        new
        if new is not None 
        else original
        for original, new in zip(
            deck_cleaned[definitions_field_name], cleaned_definitions
        )
    ]

    deck_cleaned.loc[:, vocab_field_name] = [
        the_word if str(the_word).strip() or the_word in ["None", "null", "nan"] else its_reading
        for the_word, its_reading in zip(
            deck_cleaned[vocab_field_name], deck_cleaned[reading_field_name]
        )
    ]

    return deck_cleaned



def load_word_to_readings_map():
    load_word_to_readings_map = {}
    with open("word_to_readings_map.json", "r", encoding="utf-8") as f:
        load_word_to_readings_map = json.load(f)
    return load_word_to_readings_map


def get_definitions_for_one_word(word, reading):

    word_definitions = get_definitions(
        word,
        reading,
        PRIORITY_ORDER,
        big_data_dictionary,
        word_to_readings_map,
        stop_at=-1
    )

    already_seen = []
    similarity_debuf = {}
    for dictionary, dict_items in word_definitions.items():
        for j, information in enumerate(dict_items):
            word = information["word"].split("(")[0].strip()  # 可哀想 (可哀相)
            reading = information["reading"]  #   ↑ only this
            definitions = list(set(information["definitions"]))

            if definitions in already_seen:
                word_definitions[dictionary][j] = {}
                continue
            else:
                already_seen.append(definitions)

            # Definition is simply a link + limit to 3
            # definitions = [defi for defi in definitions if not re.fullmatch(rf"⇒[a-zA-Z{KANJI}{KANA}]+(?: \(.+?\) ?)?(?:{SUFFIX})", defi)][:3]
            definitions = definitions[:3]

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
                        )

                        word_definitions[dictionary][j]["definitions"][k] = (
                            definition  # Update definition in place
                        )
            except Exception as e:
                print(f"Couldn't link {word}【{reading}】")
                # raise e
                print("oh no", definition, word, reading, "is die.")

    # for dictionary in word_definitions:
    #     word_definitions[dictionary] = [
    #         entry for entry in word_definitions[dictionary] if entry
    #     ]

    #     similarity_debuf[dictionary] = exp(1 - similarity_score(reading, cleaned_reading))
    #     similarity_debuf[dictionary] += exp(1 - similarity_score(word, cleaned_word))


    def get_total_length(entry):
        length = 0
        for word in entry:
            # print(json.dumps(word, indent=2, ensure_ascii=False))
            if "definitions" not in word:
                length += 0
            else:
                length += len("".join(word["definitions"]))
        return length

    def get_index(dictionary):
        if dictionary not in PRIORITY_ORDER:
            return 0
        return PRIORITY_ORDER.index(dictionary)

    def get_new_index(item):

        definitions = item[1]
        dictionary_name = item[0]
        if not definitions[0]:
            return 1000
        length_debuf = get_total_length(definitions)//100
        priority_index = get_index(dictionary_name) 

        priority_debuf = len(PRIORITY_ORDER) if any([d["tag"] for d in definitions]) else 0
        return length_debuf+priority_index+priority_debuf#+similarity_debuf[dictionary_name]




    word_definitions = dict(sorted(word_definitions.items(), 
            key=lambda item: get_new_index(item)))

      
    definition_html = build_definition_html(word_definitions)
    if definition_html is None:
        print(f"Couldn't find definition for {word}【{reading}】")
        return ""
    return definition_html
    # print(json.dumps(word_definitions, indent=2, ensure_ascii=False))


def change_to_monolingual(deck_name, big_data, word_to_readings_map, field_settings):
    """
    Converts an ANKI deck from bilingual to monolingual using dictionary files.

    Args:
    - deck_name (str): The name of the ANKI deck (without extension).
    """

    vocab_field_name=       field_settings["vocab"]                 # VocabKanji
    reading_field_name=     field_settings["reading"]  #    "Reading",    # VocabFurigana
    definitions_field_name= field_settings["definition"]  # "Meaning",  # VocabDef

    print(f"Converting {deck_name}...")
    # # Read the .txt file, automatically using the first row as header

    df = pd.read_csv(
        f"{deck_name}", sep=",", header=0
    )  # Change 'sep' if needed based on your file

    # df.to_excel(f"{deck_name}.xlsx", index=False)
    # Word  Reading Pitch   Meaning tags

    df = process_deck(
        deck=df,
        vocab_field_name=vocab_field_name,  # VocabKanji
        reading_field_name=reading_field_name,  # VocabFurigana
        definitions_field_name=definitions_field_name,  # VocabDef
        dictionary_priority_order=PRIORITY_ORDER,
        big_data=big_data,
        word_to_readings_map=word_to_readings_map,
    )

    # Convert to CSV and cleanup
    # output_file = f"[FIXED] {deck_name}.xlsx"
    # final_xlsx_file = pd.read_excel(output_file, index_col=None)
    df.to_csv(f"[FIXED] {deck_name}.csv", index=False, sep="\t")
    # os.remove(f"{deck_name}.xlsx")
    # os.remove(output_file)    
    # Add script for toggle functions

    print(f"Conversion complete for {deck_name}!\n\n")


if __name__ == "__main__":
    big_data_dictionary = load_big_data(
        big_data_dictionary=big_data_dictionary, override=False
    )

    word_to_readings_map = load_word_to_readings_map()


    # UNCOMMENT THIS TO GET A DEFINITION FOR A SINGLE WORD

    while True:
        # cleaned_word = "枯れ木も山の賑わい"
        # cleaned_reading = "かれきもやまのにぎわい"
        cleaned_word = input("Enter word (w/ kanji): ")
        cleaned_reading = input("Enter word reading (hiragana only): ")
        get_definitions_for_one_word(cleaned_word, cleaned_reading)
    

    # field_settings = {
    #     "vocab": input("Vocab field name > "),
    #     "reading": input("Reading field name > "),
    #     "definition": input("Meaning field name (will be overridden) > ")
    # }
    # for filename in os.listdir("text_files"):
    #     if filename.endswith(".txt"):
    #         file_path = os.path.join("text_files", filename)

    #         with open(file_path, "r", encoding="utf-8") as file:
    #             content = file.read()
    #             change_to_monolingual(file_path, big_data_dictionary, word_to_readings_map, field_settings)
