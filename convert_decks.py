import pandas as pd
from anki_export import ApkgReader
# from AnkiTools import anki_convert
import pyexcel_xlsxwx
from scraper import scrape_weblio, convert_word_to_hiragana, get_hiragana_only

from convert_to_big_data import *

big_data_dictionary = {"8. Weblio": {}}
not_in_weblio = []


import json
import os
import re



# バグ　バグる
# グーグル ググる　ggrks
# 
def get_versions_of_word(word, reading):
    """
    Generates possible versions of the word by applying various transformations.

    Args:
    - word (str): The word to transform.

    Returns:
    - list: A list of possible word versions.
    """

    original_word = word[:]  # Preserve the original word
    versions = [(word, reading)]
    # Deduplicate versions
    # Number and Katakana conversions
    numbers = {
        "１００": "百", "１０": "十", "１１": "十一", "１２": "十二",
        "１": "一", "２": "二", "３": "三", "４": "四", "５": "五",
        "６": "六", "７": "七", "８": "八", "９": "九",
        "100": "百", "10": "十", "11": "十一", "12": "十二",
        "1": "一", "2": "二", "3": "三", "4": "四", "5": "五",
        "6": "六", "7": "七", "8": "八", "9": "九"
    }

    word = re.sub(r"〈|～|\/.+|^.+・|\[.+?\]|.+,| |<.+?>|。|\n|\(.+?\)|【.+?】|〘.+?〙|［|］|（.+?）", "", word)

    # Katakana to Hiragana Conversion
    versions.append((convert_word_to_hiragana(word), reading))

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
        ii_yoi_replaced_reading = reading.replace("いい", "良い")

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

    suffixes = ["ような", "な", "だ", "と", "に", "した", "よう", "する", "さん", ""]
    for suffix in suffixes:
        if word.endswith(suffix):
            no_suffix = word[:-len(suffix)]
            no_suffix_reading = reading[:-len(suffix)]
            if no_suffix:
                if no_suffix[-1] == "た":
                    normalized_no_suffix = no_suffix[:-1] + "る"
                    normalized_no_suffix = no_suffix_reading[:-1] + "る"

                    versions.append((normalized_no_suffix, no_suffix_reading))  # 生まれたよう→生まれる
                else:
                    versions.append((no_suffix, no_suffix_reading))

    versions_final = []
    for word, reading in versions:
        if (word, reading) not in versions_final and word:
            versions_final.append((word, reading))

    return versions_final
    # return list(set([x for x in versions if x[0]]))  # Remove dupes and empty ones

def build_definition_html(word, data):
    """
            if definition_data:
            
                monolingual_definition, dictionary = link_up(cleaned_word, monolingual_definition, PRIORITY_ORDER, dictionary, big_data,
                                         not_in_weblio, look_in_weblio=True)
                linked_data.append((monolingual_definition, cleaned_word, dictionary))


        definition_html = build_definition_html(linked_data)
    """
    html = ""
    for dictionary in data.keys():
        html += f"<div>" \
                f"<button onclick=\"toggleDefinition('{dictionary}_{i}')\">{dictionary}</button>" \
                f"<div id='{dictionary}_{i}' style='display:none;'>" \

        for monolingual_definition, cleaned_word, version_reading, i in data[dictionary]:
            html += f"<div>" \
                    f"<p><b>{cleaned_word} ({version_reading}):</b> {monolingual_definition}</p>"  \
                    f"</div>" 

        html += f"</div><br/>"


    if html:
        html = "<div>" + "\n".join(html) + "</div>"
        html += """
        <script>
        function toggleDefinition(id) {
            var elem = document.getElementById(id);
            if (elem.style.display === "none") {
                elem.style.display = "block";
            } else {
                elem.style.display = "none";
            }
        }
        </script>
        """
    else:
        html = f"<p>No definitions found for {word}</p>"

    return html


def get_definitions(word, reading, priority_order, big_data, not_in_weblio, look_in_weblio):
    """Finds a word's definitions using its possible versions and returns an HTML string with collapsible fields."""
    versions = get_versions_of_word(word, reading)
    # cleaned_word, monolingual_definition, versions, dictionary

    return_data =  {
       # dictionary: [
       #    "definition",
       #    "successful_version",
       #    "successful_version_reading"
       # ]
    }


    # big_data structure:
    """
    big_data = {
        "dictionary_path": {
            "word": {
                "reading1": ["definitions_1"],
                "reading2": ["definitions_2"],
            },
            ...
        },
        ...
    }
    """

    # Check local dictionaries in priority order
    found = False

    for dictionary in [d for d in priority_order if d in big_data]:
                                            # The version itself is in the data                           # The reading is also in the data
        for version, version_reading in [(v, r) for v, r in versions if v in big_data[dictionary] and r in big_data[dictionary][v].keys()]:
            # Retrieve the dictionary's entry for this word version
            dictionary_entry = big_data[dictionary][version]

            # If reading matches, add the definition to the HTML output
            for i, definition in enumerate(dictionary_entry[version_reading]):

                if dictionary not in return_data:
                    return_data[dictionary] = []

                return_data[dictionary].append((definition, version, version_reading, i))
                found = True

    if not found:
        print(f"Warning: Reading mismatch for word '{word}' in dictionary '{dictionary}'.")
        print(f"{big_data[dictionary][word]}")
        print("\n".join([f"Version: {version}, Reading: {version_reading}" for version, version_reading in versions]))
        # print(f"But, what was found was {list(dictionary_entry.keys())}")


    # Check Weblio if necessary
    if look_in_weblio:
        for version, version_reading in versions:
            if version not in not_in_weblio:
                if version[-1] == "。":
                    version = version[:-1]

                dictionary_path = "8. Weblio"
                list_of_weblio_results, not_in_weblio = get_from_weblio(version, big_data, not_in_weblio, desired_reading=version_reading)

                if list_of_weblio_results:
                    for la_palabra, weblio_definition, yomikata in list_of_weblio_results:
                        
                        edit_big_data(big_data, dictionary_path, la_palabra, yomikata, [weblio_definition])
                        # definition_text = f"<div>"
                        #                   f"<button onclick=\"toggleDefinition('{dictionary}_{version}_1')\">{dictionary}</button>"
                        #                   f"<div id='{dictionary}_{version}' style='display:none;'>"
                        #                   f"<p><b>{version} ({version_reading}):</b> {cleaned_def}</p>"
                        #                   f"</div>"
                        #                   f"</div>"
                                    
                        return_data.append((weblio_definition, version, version_reading, dictionary, 0))
                else:
                    # Try doing it with the reading
                    list_of_weblio_results, not_in_weblio = get_from_weblio(version_reading, big_data, not_in_weblio)
                    if list_of_weblio_results:
                        for la_palabra, weblio_definition, yomikata in list_of_weblio_results:

                            edit_big_data(big_data, dictionary_path, la_palabra, yomikata, [weblio_definition])
                            # definition_text = f"<div>"
                            #                   f"<button onclick=\"toggleDefinition('{dictionary}_{version}_1')\">{dictionary}</button>"
                            #                   f"<div id='{dictionary}_{version}' style='display:none;'>"
                            #                   f"<p><b>{version} ({version_reading}):</b> {cleaned_def}</p>"
                            #                   f"</div>"
                            #                   f"</div>"
                                        
                            return_data.append((weblio_definition, version, version_reading, dictionary, 0))

    # Final HTML output
    # if definitions_html:
    #     html_output = "<div>" + "\n".join(definitions_html) + "</div>"
    #     html_output += """
    #     <script>
    #     function toggleDefinition(id) {
    #         var elem = document.getElementById(id);
    #         if (elem.style.display === "none") {
    #             elem.style.display = "block";
    #         } else {
    #             elem.style.display = "none";
    #         }
    #     }
    #     </script>
    #     """
    # else:
    #     html_output = f"<p>No definitions found for {word}</p>"

    return return_data


def get_from_weblio(word, big_data, not_in_weblio, desired_reading=None):
    if word in not_in_weblio:
        # print("Word is in NOT IN WEBLIO")
        return None, not_in_weblio
    # print(f"Looking for {word} on weblio")

    list_of_weblio_results = scrape_weblio(word.strip(), desired_reading)
    if list_of_weblio_results:   
        for la_palabra, weblio_definition, yomikata in list_of_weblio_results:
            if len(weblio_definition) > 600:
                continue  # Too long. Shitty parsing
            dictionary_path = "8. Weblio"

            weblio_definition = clean_definition(la_palabra, yomikata, weblio_definition, dictionary_path)
            edit_big_data(big_data, dictionary_path, word, yomikata, [weblio_definition])
            edit_big_data(big_data, dictionary_path, la_palabra, yomikata, [weblio_definition])
            with open("8. Weblio/term_bank_1.json", "w+", encoding="utf-8") as f:
                temp = []
                for word, readings in big_data["8. Weblio"].items():
                    for reading, definition_list in readings.items():
                        definition_text = "<br/>&nbsp;".join(definition_list)
                        temp.append([word if word else reading, reading if yomikata else '', '', '', '', [definition_text]])
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
                    "①米の粉をこね、薄くのばして焼いた皮にあんを入れた菓子。<br/>&nbsp;<br/>&nbsp;②まんなか。<br/>&nbsp;<br/>&nbsp;③まっさいちゅう。"
                  ]
                },
                """

        return list_of_weblio_results, not_in_weblio
    else:
        # print("Didn't find anything.")
        not_in_weblio.append(word)
        return None, not_in_weblio




def get_ref_numbers(referenced_word):
    return re.search(fr"(?:(?:[{NUMBER_CHARS}])|(?:\d+️⃣))+$", referenced_word)


def fetch_entry_from_reference(reference, reference_numbers, full_entry, big_data):
    if reference_numbers:
        reference_numbers_path = re.findall(r"〚(\d+)〛", reference_numbers)
        return get_entry(reference_numbers_path, full_entry, big_data)
    else:
        return full_entry


def link_up(word, reading, definition_original, priority_order, dictionary_path, big_data, not_in_weblio, look_in_weblio=True):
    # Clean up formatting from the definition text
    definition = definition_original[:]
    if definition == "":
        None, dictionary_path
    definition = re.sub(fr"([{NUMBER_CHARS}])<br\/>&nbsp;", r"\1", definition)
    definition = re.sub(fr"([{NUMBER_CHARS}])\n", r"\1", definition)

    # Handle dictionary-specific reference standardization
    if not isinstance(dictionary_path, str):
        dictionary_path = "大辞泉"

    definition = re.sub("「参考」", "", definition)

    # Search for reference pattern in the definition
    reference_matches = re.finditer(fr"⇒+([{NUMBER_CHARS}]*)(.+?)((?:〚\d〛)*)(?:。|$|\n|<br\/>&nbsp;)", definition)

    # {prefix}{tag}⇒{word}{references}{suffix}

    # If there's a reference in the definition
    if reference_matches:
        for reference_match in reference_matches:
            ref_number, referenced_word, original_entry_number = reference_match.groups()[2], reference_match.groups()[1], reference_match.groups()[0]
            referenced_word = re.sub(r"（.+?）|・.+", "", referenced_word)
            # Maybe bad parsing?

            if len(referenced_word) > 15:
                return definition, dictionary_path

            print(f"Attempting link-up for {dictionary_path}/{referenced_word}")
            # Try to fetch the referenced word definition
            ref_definition = None
            if referenced_word in big_data[dictionary_path]:
                print(f"Fetching referenced definition for {referenced_word} from {dictionary_path}")
                # Use helper function to get specific entry if a reference number is given
                ref_definitions = big_data[dictionary_path][referenced_word]

                ref_definition = ""
                for reading in ref_definitions:
                    ref_definition += f"{referenced_word}【{reading}】\n"
                    for meaning in ref_definitions[reading]:
                        ref_definition += f"{meaning}\n"
                # print(ref_definition) 

                ref_definitions = fetch_entry_from_reference(referenced_word, ref_number, 
                                                            ref_definition, 
                                                            big_data)


                # print(ref_definitions)
                # ref_definitions = "\n".join([fr"{referenced_word}【{reading}】\n{'\n'.join(ref_definitions[reading])}" for reading in ref_definitions.keys()])
                # # {'かいとう': ['└① 冷凍したものを解かしてもどすこと。\n└② コンピューターで、圧縮されたデータを一定のアルゴリズムを用いて変換し、もとに戻すこと。展開。⇒圧縮']}
                # print(ref_definition)

            
            elif referenced_word in big_data["8. Weblio"]:
                print("Fetching from local Weblio data")
                if reading in big_data["8. Weblio"][referenced_word]:
                    ref_definition = "<br/>&nbsp;".join(big_data["8. Weblio"][referenced_word][reading])
                else:
                    print(F"Warning: Reading {reading} not found for Weblio Entry {referenced_word}")

            elif look_in_weblio and referenced_word not in not_in_weblio:
                print(f"Attempting Weblio lookup")            
                list_of_weblio_results, not_in_weblio = get_from_weblio(referenced_word, big_data, not_in_weblio)
                if list_of_weblio_results:
                    for la_palabra, ref_definition, yomikata in list_of_weblio_results:
                        if ref_definition:
                            edit_big_data(big_data, "8. Weblio", la_palabra, yomikata, [ref_definition])
                    ref_definition = "<br/>&nbsp;".join([f"{chr(ord('Ⓐ')+i)} {entry[0]}" for i, entry in enumerate(list_of_weblio_results)])
                    # save_to_big_data(big_data)
            # If a referenced definition was successfully fetched
             

            if ref_definition:
                
                definition = definition + f"\n\n<hr>Linked {referenced_word}'s definition:\n{ref_definition}" 
                index = -1 
                if word in big_data[dictionary_path]:
                    for word_reading in big_data[dictionary_path][word]:
                        for i, definition_text in enumerate(big_data[dictionary_path][word][word_reading]):
                            if definition_text == definition_original:
                                index = i
                                break
                    if index != -1 and reading in big_data[dictionary_path][word]: 
                        big_data[dictionary_path][word][reading][i] = definition
                    # edit_big_data(big_data, dictionary_path, referenced_word, reading, definition)
                    # save_to_big_data(big_data)
                return definition, dictionary_path

    # Return the original definition if no reference processing was needed
    return definition_original, dictionary_path


def process_deck(deck_file, sort_column, vocab_field_name, reading_field_name, definitions_field_name, dictionary_priority_order, big_data,
                 not_in_weblio):
    """
    Processes an ANKI deck by adding monolingual definitions (XLSX version).

    Args:
    - deck_file (str): The file name of the ANKI deck (XLSX format).
    - vocab_field_name (str): Column name for words.
    - definitions_field_name (str): Column name for definitions.
    """

    deck_sorted = pd.read_excel(deck_file)
    deck_size = len(deck_sorted)
    progress_interval = deck_size // 10  # 10% progress intervals


    # deck_sorted = deck.sort_values(by=sort_column)
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

    # Iterate through the cleaned deck for processing
    for i, row in deck_sorted.iterrows():
        word = row[vocab_field_name]
        monolingual_definition = row[definitions_field_name]
        reading = get_hiragana_only(row[reading_field_name])
        cleaned_word = word[:]
        # dictionary = row["dictionary"]
        if not isinstance(monolingual_definition, str):
            monolingual_definition = ""


        definition_data = get_definitions(word, reading, dictionary_priority_order,
                                             big_data, not_in_weblio, look_in_weblio=True)
        
        linked_data = []
        
        if definition_data:
            for dictionary in data.keys():
                linked_data[dictionary] = []
                for monolingual_definition, cleaned_word, reading, i in definition_data:
                    monolingual_definition, dictionary = link_up(cleaned_word, reading, monolingual_definition, PRIORITY_ORDER, dictionary, big_data,
                                             not_in_weblio, look_in_weblio=True)
                    linked_data[dictionary].append((monolingual_definition, cleaned_word, reading, i))


        definition_html = build_definition_html(word, linked_data)

        # deck_cleaned.loc[i, definitions_field_name] = definition_html


        # deck_cleaned.loc[i, "dictionary"] = dictionary if dictionary else "None"
        # if not monolingual_definition:
            # evil_counter += 1
            # print(f"No definition found for '{word}' (Tried versions: {versions}). So far: {evil_counter}")

        # row[sort_column] = int(row[sort_column])
        # Show progress every 10%
        if i > 0 and i % progress_interval == 0:
            print(f"Progress: {i / deck_size:.0%}")

    output_file = f"[FIXED] {deck_file}"
    deck_cleaned.to_excel(output_file, index=False)
    not_in_weblio = list(set(not_in_weblio))
    save_not_in_weblio(not_in_weblio)
    return deck_sorted


def save_not_in_weblio(not_in_weblio):
    with open("not_in_weblio.json", "w+", encoding="utf-8") as f:
        json.dump(not_in_weblio, f, ensure_ascii=False)


def load_not_in_weblio(not_in_weblio):
    with open("not_in_weblio.json", "r", encoding="utf-8") as f:
        not_in_weblio = json.load(f)
    return not_in_weblio


def change_to_monolingual(deck_name, big_data, not_in_weblio):
    """
    Converts an ANKI deck from bilingual to monolingual using dictionary files.

    Args:
    - deck_name (str): The name of the ANKI deck (without extension).
    """

    print(f"Converting {deck_name}...")

     # Read the .txt file, automatically using the first row as header
    df = pd.read_csv(f"txt_exports/{deck_name}.txt", sep='\t')  # Change 'sep' if needed based on your file

    # Save to Excel
    df.to_excel(f"{deck_name}.xlsx", index=False)

    process_deck(deck_file=f'{deck_name}.xlsx',
                 sort_column="1",
                 vocab_field_name='VocabKanji',
                 reading_field_name='VocabFurigana',
                 definitions_field_name='VocabDef',
                 dictionary_priority_order=PRIORITY_ORDER,
                 big_data=big_data,
                 not_in_weblio=not_in_weblio)

    # Convert to CSV and cleanup
    output_file = f"[FIXED] {deck_name}.xlsx"
    final_xlsx_file = pd.read_excel(output_file)
    final_xlsx_file.to_csv(f"[FIXED] {deck_name}.csv", index=False, sep='\t')

    os.remove(f'{deck_name}.xlsx')
    os.remove(output_file)

    print(f"Conversion complete for {deck_name}!\n\n")


if __name__ == '__main__':
    big_data_dictionary = load_big_data(big_data_dictionary=big_data_dictionary, override=False)
    not_in_weblio = load_not_in_weblio(not_in_weblio)
    # save_to_big_data(big_data_dictionary)

    # deck_names = ["[JP-JP] N3", "[JP-JP] N4", "[JP-JP] N5", "[JP-JP] N1", "[JP-JP] N2"]
    # for deck in deck_names:
    # change_to_monolingual("[JP-JP] N1", big_data_dictionary, not_in_weblio)
    # save_to_big_data(big_data_dictionary)


    # def get_definitions(word, reading, priority_order, big_data, not_in_weblio, look_in_weblio):
    # link_up(word, reading, definition_original, priority_order, dictionary_path, big_data, not_in_weblio, look_in_weblio=True)
    word, reading = "総理大臣", "そうりだいじん"
    filter_service = get_definitions(word, reading, PRIORITY_ORDER, big_data_dictionary, not_in_weblio, look_in_weblio=False)

    print(f"Found definitions in the next dictionaries:", ", ".join(filter_service.keys()))
    for dictionary in PRIORITY_ORDER:
        if dictionary in filter_service:
            for definition, version, version_reading, i in filter_service[dictionary]:
                if "⇒" in definition:
                    definition, _ = link_up(word, reading, definition, PRIORITY_ORDER, dictionary, big_data_dictionary, not_in_weblio, look_in_weblio=False)
                print(f"{i}: {dictionary}")
                print(f"{version}【{version_reading}】")
                print(definition)

    """
    return_data =  [
        # "definitions",
        # "successful_versions",
        # "successful_version_readings"
        # "dictionaries",
        # i
    ]
    """