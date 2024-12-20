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
    RED, YELLOW, GRAY,
    SUFFIX,
    PREFIX,
    recursive_nesting_by_category,
    dict_to_text,
)

# from AnkiTools import anki_convert

big_data_dictionary = {"Weblio": {}}
not_in_weblio = []


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
    versions.append((word.replace("づ", "ず"), reading.replace("づ", "ず")))
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
    suffixes = ["ような", "な", "だ", "と", "に", "した", "よう", "する", "さん"]
    for suffix in suffixes:
        if reading.endswith(suffix):

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
    versions.append((convert_word_to_hiragana(word), get_hiragana_only(reading)))



    if word in word_to_readings_map:
        for possible_reading in word_to_readings_map[word]:
            versions.append((word, possible_reading))

    find_numbers = re.compile(r"[0-9０-９]")
    for w, r in versions.copy():
        if extended:
            versions.append((r, r))
            if r and "が" in r:
                versions.append(("".join([x for x in w if x != "が"]), "".join([x for x in r if x != "が"])))

        if "々" in w:
            versions.append((re.sub("(.)々", r"\1\1", r), r))

        if find_numbers.search(w):
            for num, kanji in numbers.items():
                if num in word:
                    word = word.replace(num, kanji)
                    versions.append((word, reading))

    versions_final = []
    for version, version_reading in versions:
        if (version, version_reading) not in versions_final and version:
            versions_final.append((version, version_reading))

    return versions_final



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
                if isinstance(info["definitions"], list):
                    first_non_guess_definition = "<br />As well as<br />".join(info["definitions"])
                else:
                    first_non_guess_definition = info["definitions"]

    # Fallback to the first guess definition if all are guesses
    if not first_non_guess_definition:
        for dictionary in data:
            if data[dictionary]:
                if isinstance(data[dictionary][0]["definitions"], list):
                    first_non_guess_definition = "<br />As well as<br />".join(data[dictionary][0]["definitions"])
                else:
                    first_non_guess_definition = data[dictionary][0]["definitions"]
                break

    if not first_non_guess_definition:
        return

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

            if isinstance(information["definitions"], list):
                information["definitions"] = "<br />As well as<br />".join(information["definitions"])
            else:
                information["definitions"] = information["definitions"]

            definitions = information["definitions"]
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
                    }
                )

            # Sort entries to prioritize exact matches (word == reading) first
            return combine_dupes(
                sorted(
                    entries, key=lambda item: 0 if item["word"] != item["reading"] else 1
                )
            )

    return []

def clean_definition_weblio(text, dictionary):
        text = re.sub(r"(?:<br />|\n)+", "<br />", text)

        if dictionary == "デジタル大辞泉":
            if "[可能]" in text:
                text = text.split("[可能]")[0]
            if "[派生]" in text:
                text = text.split("[派生]")[0]
            # Remove remains of example sentences
            # ④: 納得する。合点がいく。・・・・・・・・・・・・・・・・・ (after parsing)
            text = re.sub(r"・(?:・|／)+", "", text)
            text = re.sub(r"。。+", "。", text)

            # ・・・・・・・・・・・・・・・・・・・・・・・・・・・・・・・・／・。 。
            # ［動ザ上一］「まん（慢）ずる」（サ変）の上一段化。
            # ［動ザ上一］「みそんずる」（サ変）の上一段化。「話題の展覧会を―・じる」
            # ［動ザ上一］「てん（転）ずる」（サ変）の上一段化。「攻勢に―・じる」

            # First fix 「てん（転）ずる」 → "「転ずる」"
            text = re.sub(
                rf"「[{HIRAGANA}]+（([{KANJI}]+)）([{HIRAGANA}]+)」",
                r"「\1\2」",
                text,
            )

            # Then fix ［動ザ上一］「転ずる」（サ変）の上一段化。「攻勢に―・じる」 →  "⇒転ずる"
            text = re.sub(
                rf"(?:［.+?］)「(.+?)」の(?:..?段化|..語)({SUFFIX})",
                r"⇒\1\2 ",
                text,
            )

            # Remove
            # ［連語］《形容詞、および形容詞型活用語の連体形活用語尾「かる」に推量の助動詞「めり」の付いた「かるめり」の音変化》
            # ［連語］《連語「かんめり」の撥音の無表記》
            text = re.sub(r"［.+?］《.+?》", r"", text)

            # ［動ラ下一］［文］かきみだ・る［ラ下二］
            # ［動ラ五（四）］
            # ［動サ下一］［文］かきよ・す［サ下二］
            # ［名］(スル)
            # ［形動］［文］［ナリ］

            text = re.sub(
                rf"(?:［.+?］)+(?:[{HIRAGANA}・]+［.+?］)?(?:\(スル\))?",
                r"",
                text,
            )

            # 「一つ汲んで下されと、下々にも―に詞 (ことば) 遣ひて」〈浮・禁短気・二〉
            text = re.sub(
                rf"「[^」]+?」〈[^〉]+?〉",
                r"",
                text,
            )

            # 《季 新年》「餅網も焦げて―となりにけり／友二」
            text = re.sub(
                rf"《[^》]+?》「[^」]+?」",
                r"",
                text,
            )
            # デジタル大辞泉|||押掛ける【おしかける】：<br />おしか・く<br />１
            text = re.sub(
                rf"<br />[{HIRAGANA}・]+<br />",
                r"<br />",
                text,
            )


        text = recursive_nesting_by_category(text, weblio=True)

        if isinstance(text, dict):
            text = dict_to_text(text)
        else:
            text = text

        text = re.sub(r"(?:<br />|\n)+", "<br />", text)
        
        return text.strip("<br />")


def build_definition_from_weblio(result):
    """
    Structure of results:
    {
      "デジタル大辞泉": [
        {
          "word": "曖昧",
          "reading": [
            "あいまい"
          ],
          "definition": "１ 態度や物事がはっきりしないこと。また、そのさま。あやふや。「—な答え」\n２ 怪しくて疑わしいこと。いかがわしいこと。また、そのさま。「—宿(やど)」",
          "synonyms": [
            "多義的",
            "紛らわしい"
          ]
        }
      ],
      "難読語辞典": [
        {
          "word": "曖昧",
          "reading": [
            "アイマイ"
          ],
          "definition": "はっきりしないこと",
          "synonyms": []
        }
      ],
      "百科事典": [
        {
          "word": "曖昧",
          "reading": [
            ""
          ],
          "definition": "曖昧（あいまい, 英語: ambiguity）または曖昧性（あいまいせい）は、狭義には、物事が二通り以上に決められ得ること、一意に決められないことを指す。",
          "synonyms": []
        }
      ]
    }
    """

    def get_text(entry):
        word, reading, definition, synonyms = list(entry.values())
        reading = f'【{reading}】' if reading else ''
        synonyms = f"Similar words: {'、'.join(synonyms)}" if synonyms else ''
        return fr"{word}{reading}: <br />{definition}<br />{synonyms}"

    new_results = {}

    for dictionary in result:
        already_seen = []
        new_results[dictionary] = []

        for item in result[dictionary]:
            word = item["word"]
            reading = item["reading"]
            if (word, reading) in already_seen:
                continue

            already_seen.append((word, reading))

            definition = get_text(item)
            definition = clean_definition_weblio(definition, dictionary)

            new_results[dictionary].append({
                "word": word,
                "reading": reading,
                "definition": definition    
            })

    return new_results


def similarity_score(str1, str2):
    """Calculate similarity between two strings by the number of matching characters."""
    # Convert strings to sets to get unique characters in each
    set1, set2 = set(str1), set(str2)
    # Find the intersection of the two sets (common characters)
    common_characters = set1.intersection(set2)

    similarity_score = len(common_characters) / min(len(set1), len(set2))
    return similarity_score


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
    word = re.sub(
        r"〈|～|\/.+|^.+・|\[.+?\]|.+,| |<.+?>|。|\n|\(.+?\)|【.+?】|〘.+?〙|［|］|（.+?）|<",
        "",
        word,
    )
    reading = re.sub(
        r"〈|～|\/.+|^.+・|\[.+?\]|.+,| |<.+?>|。|\n|\(.+?\)|【.+?】|〘.+?〙|［|］|（.+?）|<",
        "",
        reading,
    )
    unique_versions = get_versions_of_word(word, reading, word_to_readings_map)

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
                hiragana_only = version == version_reading #and re.fullmatch(


                if (
                    version_reading in big_data[dictionary]
                    and version in big_data[dictionary][version_reading]
                ):
                    with_same_reading = [
                        {
                            "word": version,
                            "readings": [version_reading],
                            "definitions": big_data[dictionary][version_reading][version],
                            "tag": None
                        }
                    ]
                    # Stop at 1 version found
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
                reading = information["readings"][0]
                definitions = information["definitions"]
                tag = information["tag"]

                if definitions in already_seen:
                    continue
                else:
                    already_seen.append(already_seen)


                if dictionary == "Weblio":
                    for definition in definitions:
                        dictionary, definition = definition.split("|||")
                        if dictionary not in return_data:
                            return_data[dictionary] = [] 

                        return_data[dictionary].append(
                            {"definitions": definition, "word": words, "reading": reading, "tag": tag}
                        )
                        found = True

                else:

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
        dictionary = "Weblio"
        if dictionary not in return_data:
            return_data[dictionary] = []

        already_tried = []
        list_of_weblio_results = None
        for version, version_reading in unique_versions:
            if version not in not_in_weblio:
                if version[-1] == "。":
                    version = version[:-1]

                if version in already_tried:
                    continue 

                list_of_weblio_results, not_in_weblio = get_from_weblio(
                    version, big_data, not_in_weblio, desired_reading=version_reading
                )
                already_tried.append(version)

            if not list_of_weblio_results and version_reading and version_reading not in not_in_weblio:

                if version_reading in already_tried:
                    continue 
                already_tried.append(version_reading)

                print(f"Trying reading 【{version_reading}】")

                list_of_weblio_results, not_in_weblio = get_from_weblio(
                    version_reading, big_data, not_in_weblio, desired_reading=version_reading
                )


            if list_of_weblio_results:
                for (
                    dictionary_name, entry_list
                ) in list_of_weblio_results.items():
                    for entry in entry_list:
                        la_palabra = entry["word"]
                        yomikata = entry["reading"]
                        weblio_definition = entry["definition"]

                        if dictionary_name not in return_data:
                            return_data[dictionary_name] = []

                        return_data[dictionary_name].append(
                            {
                                "definitions": weblio_definition,
                                "word": la_palabra,
                                "reading": yomikata,
                                "tag": None
                            }
                        )
                    

    return return_data


def get_from_weblio(word, big_data, not_in_weblio, desired_reading=None):
    if word in not_in_weblio:
        return None, not_in_weblio
    if not word:
        return None, not_in_weblio

    if "Weblio" not in big_data:
        big_data["Weblio"] = {}
    # Call `scrape_weblio`, which returns the result in the expected structure

    print(f"Looking for '{word}' in Weblio.")
    weblio_result = scrape_weblio(word.strip(), desired_reading)

    if weblio_result:
        # Use `build_definition_from_weblio` to format the definitions for each dictionary entry
        if desired_reading:
            # Filter the entries in `weblio_result` to only include those with the desired reading
            weblio_result = {
                key: [entry for entry in entries if desired_reading in entry["reading"]]
                for key, entries in weblio_result.items()
                if any(desired_reading in entry["reading"] for entry in entries)
            } 

        formatted_weblio_data = build_definition_from_weblio(weblio_result)
        
        # Add the formatted result to `big_data` under the "Weblio" dictionary

        for dictionary_name, data in formatted_weblio_data.items():
            for entry in data:

                if entry["reading"] not in big_data["Weblio"]:
                    big_data["Weblio"][entry["reading"]] = {}

                if entry["word"] not in big_data["Weblio"][entry["reading"]]:
                    big_data["Weblio"][entry["reading"]][entry["word"]] = []

                definition = f"{dictionary_name}|||{entry['definition']}"

                if definition not in big_data["Weblio"][entry["reading"]][entry["word"]]:
                    big_data["Weblio"][entry["reading"]][entry["word"]].append(
                        f"{dictionary_name}|||{entry['definition']}"
                    )
        

        save_data = []
        with open("Weblio/term_bank_1.json", "w+", encoding="utf-8") as f:

            for reading in big_data["Weblio"]:
                for word, definitions in big_data["Weblio"][reading].items():

                    save_data.append(
                        [
                        word,
                        reading,
                        '',
                        '',
                        '',
                        definitions
                        ]
                    )

            json.dump(save_data, f, ensure_ascii=False, indent=2)
            print("Saved finding")
        return formatted_weblio_data, not_in_weblio

    # If no results, add the word to `not_in_weblio`
    print(f"Not found in weblio add {word} to `not_in_weblio`")
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
        rf"⇒([^{OPENING_BRACKETS}{NUMBER_CHARS}。\n<〚]+)( \([あ-ゔ]+\) ?)?((?:〚\d〛)*)(?:{suffix})?",
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
                            if not re.fullmatch(rf"⇒[a-zA-Z{KANJI}{KANA}]+(?: \(.+?\) ?)?(?:{SUFFIX}|$)", definition)
                        ]

                        if ref_definitions: 
                            used_reading = reading_found
                            break

            # External lookup on Weblio if local lookup fails and `look_in_weblio` is True
            # if (
            #     not ref_definitions
            #     and look_in_weblio
            #     and referenced_word not in not_in_weblio
            # ):
            #     # Fetch Weblio results if available
            #     ref_definitions, not_in_weblio = get_from_weblio(
            #         referenced_word, big_data, not_in_weblio, desired_reading=furigana
            #     )



            definition_original = definition_original.split("<br />Linked")[0]
            # If a referenced definition was successfully fetched
            if ref_definitions:
                # Original word?
                if referenced_word == word and used_reading == reading:
                    continue

                # Process the reference definitions and append to the main definition text
                ref_definition = f"<br /> Linked {referenced_word}【{used_reading}】" + (reference_number_path if reference_number_path else '')
                
                found = False
                more_than_one = len(ref_definitions) > 1
                ref_definitions = list(set(ref_definitions if ref_definitions else []))
                for i, found_definition in enumerate(ref_definitions):

                    index = f"{i}. <br/>" if more_than_one else ""

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
    splits = definition_original.split("<br />Linked")

    already_seen = []
    for part in splits:
        if part in already_seen:
            continue
        already_seen.append(part)

    definition_original = "<br />Linked".join(already_seen)
    definition_original = re.sub(r"(?:\n|<br />)+", "<br />", definition_original)
    definition_original = "<br />".join(
        [x for x in definition_original.split("<br />") if x != "└"]
    )

    if len(definition_original) > 3000:
        return super_original, dictionary_path

    return definition_original, dictionary_path

# !todo: make alternative versions count as guesses (make "same reading" produce versions)

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
    deck = pd.read_excel(deck_file, index_col=None)
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

        cleaned_reading = re.sub(r"\[(.+?),.+?\]", r"[\1]", str(row[reading_field_name]) if row[reading_field_name] else "")
        cleaned_reading = re.sub(
            r"(?:\(|（|＜).+?(?:\)|）|＞)", "", cleaned_reading
        )

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
            big_data_dictionary,
            word_to_readings_map,
            not_in_weblio,
            look_in_weblio=True,
            stop_at=-1
        )
        already_seen = []
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
                definitions = [defi for defi in definitions if not re.fullmatch(rf"⇒[a-zA-Z{KANJI}{KANA}]+(?: \(.+?\) ?)?(?:{SUFFIX})", defi)][:3]

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

        for dictionary in word_definitions:
            word_definitions[dictionary] = [
                entry for entry in word_definitions[dictionary] if entry
            ]

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
            length_debuf = get_total_length(item[1])//100
            priority_index = get_index(item[0]) 
            priority_debuf = len(dictionary_priority_order) if any([d["tag"] for d in item[1]]) else 0
            return length_debuf+priority_index+priority_debuf


        original = word_definitions.copy()
        word_definitions = dict(sorted(word_definitions.items(), 
                key=lambda item: get_new_index(item)))

        definition_html = build_definition_html(word_definitions)

        if definition_html:
            cleaned_definitions.append(
                "<" + definition_html.strip("<br />").strip("<br/>")
            )
        else:
            print("Didn't find", cleaned_word)
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

    deck_cleaned[vocab_field_name] = [
        the_word if str(the_word).strip() or the_word in ["None", "null", "nan"] else its_reading
        for the_word, its_reading in zip(
            deck_cleaned[vocab_field_name], deck_cleaned[reading_field_name]
        )
    ]

    # deck_cleaned[definitions_field_name] = cleaned_definitions
    deck_cleaned = deck_cleaned.loc[:, ~deck_cleaned.columns.str.contains("^Unnamed")]

    output_file = f"[FIXED] {deck_file}"
    # print(deck_cleaned)

    deck_cleaned.to_excel(output_file, index=False)
    not_in_weblio = list(set(not_in_weblio))
    save_not_in_weblio(not_in_weblio)
    return deck


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
    # print(1)
    # print(df.columns)
    df.to_excel(f"{deck_name}.xlsx", index=False)
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


    # field_settings = {
    #     "vocab": "VocabKanji",
    #     "reading": "VocabFurigana",
    #     "definition": "VocabDef"
    # }

    # deck_names = ["[JP-JP] N1", "[JP-JP] N2", "[JP-JP] N3", "[JP-JP] N4", "[JP-JP] N5", "物語"]

    # for deck in deck_names:
    #     change_to_monolingual(deck, big_data_dictionary, not_in_weblio, word_to_readings_map, field_settings)
    
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
        textModeContent.style.display = "block";
    }
}
</script>
    """.replace("{red}", f"{RED}").replace("{yellow}", f"{YELLOW}")