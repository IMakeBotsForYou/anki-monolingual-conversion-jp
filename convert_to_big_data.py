import pandas as pd
import json
import re
import os
from json.decoder import JSONDecodeError
big_data_dictionary = {}
from scraper import convert_word_to_hiragana
BIG_DATA_FILE = "big_data.json"
PRIORITY_ORDER = [
    "1. 大辞泉",   
    "7. 三省堂国語辞典",
    "5. 故事・ことわざ・慣用句オンライン",
    "2. 実用日本語表現辞典",
    "3. 大辞林",
    # "4. 使い方の分かる 類語例解辞典",
    # "6. 旺文社国語辞典 第十一版",
    # "8. Weblio",
]   
OPENING_BRACKETS = r"（「\[【〔\(『［〈《〔〘"
CLOSING_BRACKETS = r"）」\]】〕\)』］〉》〕〙"

KANJI = fr"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f"
HIRAGANA = fr"あ-ゔ"
NUMBER_CHARS = r"①-⑳❶-❿㉑-㉟⑴-⒇⒈-⒛➊-➓➀-➉🈩🈔🈪㊀-㊉㊤㊥㊦㋐-㋾１-９ⓐ-ⓩⒶ-Ⓩ🅐-🅩"
FIRST_NUMBER_CHARS = r"①❶⑴⒈➊➀🈩㊀㊤㋐１ⓐⒶ🅐"
LAST_NUMBER_CHARS = r"⑳❿⑳⒇⒛➓➉🈪㊉㊦㋾９ⓩⓏ🅩"
PREFIX = fr"[{NUMBER_CHARS}]|\d️⃣|^|。|<br\/>&nbsp;|\n|[{CLOSING_BRACKETS}{OPENING_BRACKETS}]| |　|記号.+?"
SUFFIX = fr"。|\n|<br\/>&nbsp;"
ARROWS = fr"⇔→←☞⇒⇐⇨"
NUMBER_CATEGORIES = {
    '①': r"[①-⑳㉑-㉟]+",
    '❶': r"[❶-❿]+",
    '⑴': r"[⑴-⒇]+",
    '⒈': r"[⒈-⒛]+",
    '➊': r"[➊-➓]+",
    '➀': r"[➀-➉]+",
    '🈩': r"[🈩🈔🈪]",
    '㊀': r"[㊀-㊉]+",
    '㊤': r"[㊤-㊦]+",
    '㋐': r"[㋐-㋾]+",
    '１': r"[０-９]+",
    'ⓐ': r"[ⓐ-ⓩ]+",
    'Ⓐ': r"[Ⓐ-Ⓩ]+",
    '🅐': r"[🅐-🅩]+",
    "KeyCapEmoji": r"(?:\d+️⃣)+"
}

# Maybe there's a smarter way to do this but lololol
REFERENCE_NUMBER_MAP = {
    # Circled Numbers
    '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5, '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
    '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15, '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20,
    
    # Parenthesized Numbers
    '⑴': 1, '⑵': 2, '⑶': 3, '⑷': 4, '⑸': 5, '⑹': 6, '⑺': 7, '⑻': 8, '⑼': 9, '⑽': 10,
    '⑾': 11, '⑿': 12, '⒀': 13, '⒁': 14, '⒂': 15, '⒃': 16, '⒄': 17, '⒅': 18, '⒆': 19, '⒇': 20,
    "1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣": 5, "6️⃣": 6, "7️⃣": 7, "8️⃣": 8, "9️⃣": 9,
    # Double Circled Numbers
    '❶': 1, '❷': 2, '❸': 3, '❹': 4, '❺': 5, '❻': 6, '❼': 7, '❽': 8, '❾': 9, '❿': 10,
    
    # Enclosed Alphanumeric Supplement
    '㉑': 21, '㉒': 22, '㉓': 23, '㉔': 24, '㉕': 25, '㉖': 26, '㉗': 27, '㉘': 28, '㉙': 29, '㉚': 30,
    '㉛': 31, '㉜': 32, '㉝': 33, '㉞': 34, '㉟': 35,
    
    # Enclosed CJK Ideographic Supplement
    '㊀': 1, '㊁': 2, '㊂': 3, '㊃': 4, '㊄': 5, '㊅': 6, '㊆': 7, '㊇': 8, '㊈': 9, '㊉': 10,
    
    # Enclosed CJK Ideographic Units
    '㊤': '上', '㊥': '中', '㊦': '下',
    
    # Enclosed Katakana
    '㋐': 'ア', '㋑': 'イ', '㋒': 'ウ', '㋓': 'エ', '㋔': 'オ', '㋕': 'カ', '㋖': 'キ', '㋗': 'ク', '㋘': 'ケ', '㋙': 'コ',
    '㋚': 'サ', '㋛': 'シ', '㋜': 'ス', '㋝': 'セ', '㋞': 'ソ', '㋟': 'タ', '㋠': 'チ', '㋡': 'ツ', '㋢': 'テ', '㋣': 'ト',
    '㋤': 'ナ', '㋥': 'ニ', '㋦': 'ヌ', '㋧': 'ネ', '㋨': 'ノ', '㋩': 'ハ', '㋪': 'ヒ', '㋫': 'フ', '㋬': 'ヘ', '㋭': 'ホ',
    '㋮': 'マ', '㋯': 'ミ', '㋰': 'ム', '㋱': 'メ', '㋲': 'モ', '㋳': 'ヤ', '㋴': 'ユ', '㋵': 'ヨ', '㋶': 'ラ', '㋷': 'リ',
    '㋸': 'ル', '㋹': 'レ', '㋺': 'ロ', '㋻': 'ワ', '㋼': 'ヰ', '㋽': 'ヱ', '㋾': 'ヲ',
    
    # Fullwidth Numbers
    '１': 1, '２': 2, '３': 3, '４': 4, '５': 5, '６': 6, '７': 7, '８': 8, '９': 9,
    # '１１': 11, '１２': 12, '１３': 13, '１４': 14, '１５': 15, '１６': 16, '１７': 17, '１８': 18, '１９': 19,
    # '２０': 20,
    # Enclosed Alphanumeric
    'ⓐ': 'a', 'ⓑ': 'b', 'ⓒ': 'c', 'ⓓ': 'd', 'ⓔ': 'e', 'ⓕ': 'f', 'ⓖ': 'g', 'ⓗ': 'h', 'ⓘ': 'i', 'ⓙ': 'j',
    'ⓚ': 'k', 'ⓛ': 'l', 'ⓜ': 'm', 'ⓝ': 'n', 'ⓞ': 'o', 'ⓟ': 'p', 'ⓠ': 'q', 'ⓡ': 'r', 'ⓢ': 's', 'ⓣ': 't',
    'ⓤ': 'u', 'ⓥ': 'v', 'ⓦ': 'w', 'ⓧ': 'x', 'ⓨ': 'y', 'ⓩ': 'z',
    
    # Enclosed Latin Letters
    'Ⓐ': 'A', 'Ⓑ': 'B', 'Ⓒ': 'C', 'Ⓓ': 'D', 'Ⓔ': 'E', 'Ⓕ': 'F', 'Ⓖ': 'G', 'Ⓗ': 'H', 'Ⓘ': 'I', 'Ⓙ': 'J',
    'Ⓚ': 'K', 'Ⓛ': 'L', 'Ⓜ': 'M', 'Ⓝ': 'N', 'Ⓞ': 'O', 'Ⓟ': 'P', 'Ⓠ': 'Q', 'Ⓡ': 'R', 'Ⓢ': 'S', 'Ⓣ': 'T',
    'Ⓤ': 'U', 'Ⓥ': 'V', 'Ⓦ': 'W', 'Ⓧ': 'X', 'Ⓨ': 'Y', 'Ⓩ': 'Z',
    
    # Fullwidth Latin Letters (uppercase)
    '🅐': 'A', '🅑': 'B', '🅒': 'C', '🅓': 'D', '🅔': 'E', '🅕': 'F', '🅖': 'G', '🅗': 'H', '🅘': 'I', '🅙': 'J',
    '🅚': 'K', '🅛': 'L', '🅜': 'M', '🅝': 'N', '🅞': 'O', '🅟': 'P', '🅠': 'Q', '🅡': 'R', '🅢': 'S', '🅣': 'T',
    '🅤': 'U', '🅥': 'V', '🅦': 'W', '🅧': 'X', '🅨': 'Y', '🅩': 'Z'
}

def convert_reference_numbers(text):
    """Convert reference numbers in text to the format (number)."""
    
    # Function to replace each match with its mapped numeric value
    def replace_match(match):
        char = match.group(0)
        number = REFERENCE_NUMBER_MAP.get(char)
        return f"〚{number}〛" if number else char  # Return the number in parentheses or the char itself
    
    # Substitute each reference character with the desired format
    result = re.sub(r'|'.join(map(re.escape, REFERENCE_NUMBER_MAP.keys())), replace_match, text)
    return result


def dict_to_text(d, level=0):
    """Convert a nested dictionary to a formatted string with indentation based on nesting level."""
    result = ""
    
    for key, value in d.items():
        if value in ["", ":"]:
            continue
        # Add a newline, then tabs based on the current level
        prefix = "└" if level == 0 else "└" + "─" * level
        result += "\n" + prefix + key
        
        # If the value is a string, add it after the key
        if isinstance(value, str):
            value = re.sub(r"^:", "", value)
            result += " " + value
        # If the value is a nested dictionary, recursively convert it
        elif isinstance(value, dict):
            result += dict_to_text(value, level + 1)

    result = re.sub(fr"(?:<br/>&nbsp;){2,}", r"<br/>&nbsp;", result)
    result = re.sub(fr"\n{2,}", r"\n", result)

    return result

    
def find_first_category(text):
    """Identify the first number category that appears in the text."""
    first_category = None  
    earliest_index = len(text)+1  # Beyond bounds
    for category, pattern in NUMBER_CATEGORIES.items():

        match_object = re.search(pattern, text)
        if match_object:
            start_index = match_object.span()[0]
            if start_index < earliest_index:
                earliest_index = start_index
                first_category = category
    
    return first_category

def segment_by_category(text, category):
    """Segments text by the first number characters of a specified category."""
    pattern = NUMBER_CATEGORIES[category]
    segments = re.split(f"({pattern})", text)
    # Create dictionary with segments, using number chars as keys
    segments_dict = {}
    i = 0
    while i < len(segments) - 1:
        if re.match(pattern, segments[i]):
            key = segments[i]
            segments_dict[key] = segments[i + 1].strip()
            i += 2
        else:
            i += 1
    return segments_dict

def recursive_nesting_by_category(text):
    """Recursively separates the text into nested dictionaries by number character categories."""
    first_category = find_first_category(text)
    if not first_category:
        return text  # Base case: no number characters left

    # Segment by the first identifier
    segments_dict = segment_by_category(text, first_category)

    # Recursively process each segment
    for key, sub_text in segments_dict.items():
        segments_dict[key] = recursive_nesting_by_category(sub_text)
    
    return segments_dict


def get_entry(ref_path, text, big_data):
    entry_dict = recursive_nesting_by_category(text)

    current = entry_dict.copy()

    for step in ref_path:
        find_correct = [k for k in current.keys() if str(REFERENCE_NUMBER_MAP[k]) == step]
        if find_correct:
            current = current[find_correct[0]]
        else:
            raise KeyError(f"Could not find the equivalent to {step} in {current.keys()}")    

    if isinstance(current, str):
        return current  # Final destination
    elif isinstance(current, dict):
        # Current is still a nested dictionary
        text = convert_to_text(current)

        return convert_to_text(current)



def convert_to_path(reference_numbers):
    path = []
    counter = 0
    for i, x in enumerate(reference_numbers):
        
        if counter > 0:
            counter -= 1
            continue

        if x <= '9' and counter == 0:
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
        [f for f in os.listdir(dictionary_path) if re.match(r'term_bank_\d+\.json$', f)],
        key=lambda x: int(re.search(r'\d+', x).group())
    )

    for file in term_bank_files:
        # data = None
        # with open(f"6. 旺文社国語辞典 第十一版/{file}", "r", encoding="utf-8") as f:
        #     data = json.load(f)

        # with open(f"6. 旺文社国語辞典 第十一版/{file}", "w", encoding="utf-8") as f:
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
            # if dictionary_path.endswith("大辞林"):
            #     data = data[0]
            for i, entry in enumerate(data):
                word, reading, definitions_in_data = entry[0], entry[1], entry[5]
                
                # Words can have different readings, and different definitions.
                # 最中（さいちゅう・さなか）etc. 
                # If a word has multiple definitions for a single reading, run over all of them.
                # We are currently handling a single entry.

                if not reading:
                    reading = convert_word_to_hiragana(word)
                else:
                    reading = convert_word_to_hiragana(reading)

                definition_list = []

                for definition in definitions_in_data:
                    definition_text = get_text_only_from_dictionary(word, reading, definition, dictionary_path)
                    if definition_text:
                        definition_list.append(definition_text)
                
                # Create new entry/extend existing one

                if not definition_list:  # No definitions for entry?
                    
                    words_to_remove.append(word)
                    
                else:
                    edit_big_data(big_data, dictionary_path, word, reading, definition_list)


    except JSONDecodeError as e:
        print(f"Error decoding JSON in file {file_path}: {e}")
        return

    # Filter out words to remove
    data_after_edits = [item for item in data if item[0] not in words_to_remove]

    print(f"Size after removals: {len(data_after_edits)}")

    # with open(file_path, "w", encoding="utf-8") as f:
    #     json.dump(data_after_edits, f, ensure_ascii=False, indent=2)

def normalize_references(text: str, dictionary_path: str) -> str:
    text = re.sub(fr" ?[{ARROWS}]", "⇒", text)
    text = text.replace("\\n", "\n")
    text = text.replace("\\n", "\n")
    flag = False
    text_original = text[:]

    if dictionary_path.endswith("大辞泉"):

        #［名］(スル)「アルバイト」の略。「夏休みにバイトする」
        has_ryaku = re.compile(fr"({PREFIX})「([^{OPENING_BRACKETS}]+?)」の略({SUFFIX})")
        if has_ryaku.search(text):
            adding_text = has_ryaku.sub(r"⇒\2", has_ryaku.search(text).group())
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

        ref_with_furigana = re.compile(fr"([①-⑳❶-❿㉑-㉟⑴-⒇⒈-⒛➊-➓➀-➉🈩🈔🈪㊀-㊉㊤㊥㊦㋐-㋾１-９ⓐ-ⓩⒶ-Ⓩ🅐-🅩]|\d️⃣|^|。|<br\/>&nbsp;|\n|[）」\]】〕\)』］〉》〕〙（「\[【〔\(『［〈《〔〘]| |　|記号.+?)?⇒((?:([\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]+)(?: \([あ-ゔa-zA-Z]+\) ?)?|[あ-ゔa-zA-Z]+)+)((?:[①-⑳❶-❿㉑-㉟⑴-⒇⒈-⒛➊-➓➀-➉🈩🈔🈪㊀-㊉㊤㊥㊦㋐-㋾１-９ⓐ-ⓩⒶ-Ⓩ🅐-🅩]|\d️⃣)+)?", flags=re.UNICODE)
        match_object = ref_with_furigana.finditer(text)
        match_object_2 = ref_with_furigana.finditer(text)
        links = []
        if match_object:
            for match in match_object:

                # If I ever want to make it actually link stuff up and consider the reading, 
                # I'll do it. But for now, I'll make it ignore the reading.
                # reading = re.findall(fr" \(([{HIRAGANA}a-zA-Z]+)\) ", ref_with_furigana.group()).group()

                no_furigana_and_ref = re.findall(fr"[a-zA-Z]|[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]|(?:[①-⑳❶-❿㉑-㉟⑴-⒇⒈-⒛➊-➓➀-➉🈩🈔🈪㊀-㊉㊤㊥㊦㋐-㋾１-９ⓐ-ⓩⒶ-Ⓩ🅐-🅩]|\d️⃣)+$|[^(⇒][あ-ゔ]+[^)]", match.group(), flags=re.U)

                number = match.groups()[3] if match.groups()[3] else ""

                if no_furigana_and_ref:
                    no_furigana_and_ref = "".join([x.replace(" ", "") for x in no_furigana_and_ref])
                
                if no_furigana_and_ref and f"⇒{no_furigana_and_ref}" not in text:
                    parsed = "Parsed link: " if match.group() != no_furigana_and_ref else ""
                    link = f"{parsed}⇒{no_furigana_and_ref}"
                    if link not in links:
                        text = fr"{text}\n{link}"  
                        links.append(link)

                if no_furigana_and_ref and no_furigana_and_ref != f"{match.group(2)}{match.group(4) if match.group(4) else ''}":
                    text = text.replace(f"{match.groups()[1:]}", "[linked later]")
                # flag = True

        text = re.sub(r"⇒{2,}", "⇒", text)
        text = text.replace("\\n", "\n")
        # convert に同じ format to ⇒ format for linking purposes later.
        # Either in the beginning, between lines, or between periods.
        #                             Prefix   Word        Suffix
        definition_text = re.sub(fr"({PREFIX})「(.+?)」に同じ({SUFFIX})", r"\1⇒\2\3", text)

        # 。「言葉①」に同じ。
        # 。⇒言葉①
        # 。⇒言葉(1) (Later)


        # 。⇒内匠寮 (たくみりょう) ①
        # 。⇒IOA（Independent Olympic Athletes）
        # ⇒コマーシャル①
        # ...ラバー。→弾性ゴム\n② 植物から...
        # ⇒鉱工業生産指数①
        #                         To not include the number chars we want later. However, DO include digits, but not if follwoed by emoji data.
        #                       Prefix                         Word                                   SOMETHING IN BRACKETS                        Reference Num or whatever

        pattern_text = fr"([①-⑳❶-❿㉑-㉟⑴-⒇⒈-⒛➊-➓➀-➉🈩🈔🈪㊀-㊉㊤㊥㊦㋐-㋾１-９ⓐ-ⓩⒶ-Ⓩ🅐-🅩]|\d️⃣|^|。|<br\/>&nbsp;|\n|[）」\]】〕\)』］〉》〕〙（「\[【〔\(『［〈《〔〘]| |　|記号.+?)?⇒([^\n]+?)(?:（.+?）)?((?:[①-⑳❶-❿㉑-㉟⑴-⒇⒈-⒛➊-➓➀-➉🈩🈔🈪㊀-㊉㊤㊥㊦㋐-㋾１-９ⓐ-ⓩⒶ-Ⓩ🅐-🅩]|\d️⃣)*?)(。|\n|<br\/>&nbsp;|$|・| |　)"
        pattern = re.compile(pattern_text)
        

        results = pattern.finditer(text)

        if results:
            # if len([x for x in results]) > 1:
                
            for result in results:
                _prefix, word, reference_number, suffix = result.groups()
                reference_number = reference_number if reference_number else ""
                if re.search(fr"[{NUMBER_CHARS}]|\d️⃣", reference_number):
                    # Reference number
                    reference_numbers = convert_to_path(reference_number) 
                    try:
                        references = "".join([convert_reference_numbers(x) for x in reference_numbers])
                    except KeyError:
                        print("[ERROR]\t", text, reference_numbers)
                else:
                    # Just a suffix
                    references = reference_number

                text = pattern.sub(f"{_prefix}⇒{word}{references}{suffix}", text)

    if dictionary_path.endswith("三省堂国語辞典"):
        # ①朝。午前。
        # ②〘服〙←モーニングコート。 
        # ③←モーニングサービス。
        # (!) Remeber,   definition = re.sub(fr"[⇒⇨←☞]", "⇒", definition)





        pattern = re.compile(fr"([{NUMBER_CHARS}]|\d️⃣|^|。|<br\/>&nbsp;|\n|[{CLOSING_BRACKETS}{OPENING_BRACKETS}]| |　|記号.+?)⇒([{NUMBER_CHARS}]*)([^\d{OPENING_BRACKETS}]+?)([{NUMBER_CHARS}]|\d️)?(・|$|。|<br\/>&nbsp;|\n)")
        result = pattern.search(text)
        if result:
            _prefix, _, word, reference_number, suffix = result.groups()
            reference_number = reference_number if reference_number else ""
            if re.search(fr"[{NUMBER_CHARS}]|\d️⃣", reference_number):
                # Reference number
                reference_numbers = convert_to_path(reference_number) 
                try:
                    references = "".join([convert_reference_numbers(x) for x in reference_numbers])
                except KeyError:
                    print("[ERROR]\t", text, reference_numbers)
            else:
                references = reference_number

            text = pattern.sub(f"{_prefix}⇒{word}{references}{suffix}", text)

    if dictionary_path.endswith("大辞林"):
        ...


    text = re.sub(rf"・(?:{NUMBER_CHARS}]|\d️⃣|)", "", text)
    return text


def clean_definition(word: str, reading: str, definition_text: str, dictionary_path: str) -> str:
    """
    Cleans and formats the definition text based on the specific dictionary.
    
    Args:
    - definition_text (str): The raw definition text to clean.
    - dictionary_path (str): The name or identifier of the dictionary.

    Returns:
    - str: The cleaned and formatted definition text.
    """
    # Remove the first line for specific dictionaries

    if word.endswith("の解説"):
        return None

    # Normalize \n's
    definition_text = definition_text.replace("\\n", "\n")
    # Weird character
    definition_text = definition_text.replace(" ", " ")

    # Unecessary parts
    definition_text = re.sub(r"(?:\[補説\]|［補説］|［用法］|\[用法\]|\[可能\]|［可能］)(?:.|\n)+", "", definition_text).strip()
    
    # I don't even know why this appears at times
    definition_text = definition_text.replace("_x000D_", "")
    
    # I don't even know why this appears at times
    definition_text = definition_text.replace("_x000D_", "")

    if not word and not reading:
        return None

    # Normalize spaces after numbers:
    definition_text = re.sub(fr"([{NUMBER_CHARS}])[ ]+", r"\1", definition_text)

    definition_text = normalize_references(definition_text, dictionary_path)

    # Using endswith because I don't care about their order in the priority (or what order you chose to give them
    # in the folder name). Just matters that it     ends with the dictionary name.
    if dictionary_path.endswith("大辞泉"):
        splitted = definition_text.split("\n")
        if len(splitted) > 1:
            definition_text = "<br/>&nbsp;".join(splitted[1:])  # Remove first line
        # Since we're adding all entries as seperate items in a list, we don't need to clean stuff like this;
        # It can easily be filtered out later.
        # No need to destroy data.

        if "[可能]" in definition_text:
            definition_text = definition_text.split("[可能]")[1]

        # Remove remains of example sentences
        # ④: 納得する。合点がいく。・・・・・・・・・・・・・・・・・ (after parsing)
        definition_text = re.sub(r"・{2,}", "", definition_text)


        # definition_text = re.sub(r"［(?:人名用漢字|常用漢字)］\s*［音］[ア-ン]+（漢）\s*[ア-ン]+（呉）\s*［訓］[{HIRAGANA}]+(?:{SUFFIX})", "", definition_text)

        # ［動ザ上一］「まん（慢）ずる」（サ変）の上一段化。
        # ［動ザ上一］「みそんずる」（サ変）の上一段化。「話題の展覧会を―・じる」
        # ［動ザ上一］「てん（転）ずる」（サ変）の上一段化。「攻勢に―・じる」

        # First fix 「てん（転）ずる」 → "「転ずる」"
        definition_text = re.sub(r"「[あ-ん]+（(.+?)）(.+?)」", r"「\1\2」", definition_text)

        # Then fix ［動ザ上一］「転ずる」（サ変）の上一段化。「攻勢に―・じる」 →  "⇒転ずる"
        definition_text = re.sub(fr"(?:［.+?］)「(.+?)」の(?:..?段化|..語)({SUFFIX})", r"⇒\1\2", definition_text)



        # Remove
        #［連語］《形容詞、および形容詞型活用語の連体形活用語尾「かる」に推量の助動詞「めり」の付いた「かるめり」の音変化》
        #［連語］《連語「かんめり」の撥音の無表記》
        definition_text = re.sub(r"［.+?］《.+?》", r"", definition_text)

        # Remove
        # 「憎げにおし立ちたることなどはあるまじ―◦めりと思すものから」〈源・若菜上〉$
        # 「うそぶかせ給ふこと、しげ―◦めりしかば」〈かげろふ・下〉$
        definition_text = re.sub(r"^〉.+?〈」.+?「", r"", definition_text[::-1])[::-1]


        # ［動ラ下一］［文］かきみだ・る［ラ下二］
        # ［動ラ五（四）］
        # ［動サ下一］［文］かきよ・す［サ下二］
        # ［名］(スル)
        definition_text = re.sub(fr"(?:［.+?］)+(?:[{HIRAGANA}・]+［.+?］)?(?:\(スル\))?", r"", definition_text)
    # if my_word:       
    if dictionary_path.endswith("旺文社国語辞典 第十一版"):
        # Remove first line
        # あい‐しょう【哀傷】――シヤウ\n
        splitted = definition_text.split("\n")
        if len(splitted) > 1:
            definition_text = "<br/>&nbsp;".join(splitted[1:])  # Remove first line

        # Remove the first line in items like this.
        # あい【挨】\nアイ㊥\nおす\n筆順：\n
        # \n\n（字義）\n① おす。押しのける。「挨拶（あいさつ）（＝原義は押しのけて進む意。国 ...

        if "筆順：\n" in definition_text:
            definition_text = definition_text.split("筆順：\n")[1]
        if "図版：" in definition_text:
            definition_text = definition_text.split("図版：")[1]

        # Remove 
        # （名・他スル）\n.
        # （形）《カロ・カツ（ク）・イ・イ・ケレ・○》\n
        # But keep (…の略).

        definition_text = re.sub(r"（.+?）(《.+?》)?\n", "", definition_text)

        # Remove 
        # 〔可能〕あが・れる（下一）<br/>&nbsp;
        # 〔他〕あ・げる（下一 ）
        definition_text = re.sub(r"〔.+?〕?[{HIRAGANA}・]+（.+?）({SUFFIX})", r"\1", definition_text)

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
        ...
        # This is already handled in the scraping function
        # definition_text = re.sub(r"^.+?｠<br/>&nbsp;|「.+」(?:<br/>&nbsp;)?", "", definition_text)
    
    if dictionary_path.endswith("事故・ことわざ・慣用句オンライン"):
        ...
        # This is already handled in the scraping function

        # Remove spans like this
        # しりてしらざれ【知りて知らざれ】
        # 【失敗は成功のもと】

    if dictionary_path.endswith("大辞林"):
        no_period_quote = re.search(r"[^。」]$", definition_text)
        final_word_reference = re.search(fr"⇒[{KANJI}{HIRAGANA}a-zA-Z]+$", definition_text)
        if no_period_quote and not final_word_reference:
            return None
        definition_text = definition_text.split("補説欄")[0]

        # This is already handled in the scraping function
    if dictionary_path.endswith("実用日本語表現辞典"):
        ...
        # This is already handled in the scraping function

    if dictionary_path.endswith("Weblio"):
        #［動カ下一］［文］なつ・く［カ下二］《「なづける」とも》
        #［動ア下一］［文］かま・ふ［ハ下二］
        #［動カ五（四）］
        definition_text = re.sub(fr"({PREFIX})(?:［.+?］)+(?:[{HIRAGANA}・]+［.+?］)?(?:《.+?》)?({SUFFIX})", r"\1\2", definition_text)

    # # Add line breaks before entry numbers
    # definition_text = re.sub(fr"([{NUMBER_CHARS}]|\d️⃣)", r"<br/>&nbsp;\1", definition_text)
    # Clean up leading or trailing unwanted characters

    if definition_text:
        definition_text = definition_text.strip("\n").strip("<br/>&nbsp;")
        # once

    # if "⇒" in definition_text:
    #     definition_text = re.sub(fr"({PREFIX})⇒([{NUMBER_CHARS}]*)(.+)($|。|<br/>&nbsp;|\n)", r"\1\2\3\4", definition_text)

    # Normalize numbers back
    definition_text = re.sub(fr"([{NUMBER_CHARS}][^ ]) ", r"\1 ", definition_text)

    # Normalize line breaks
    definition_text = definition_text.replace("\n", "<br/>&nbsp;").replace("\\n", "<br/>&nbsp;")

    # Contract multiple linebreaks into a single linebreak
    definition_text = re.sub(fr"(?:<br/>&nbsp;){2,}", r"<br/>&nbsp;", definition_text)
    # Temp
    definition_text = definition_text.replace("<br/>&nbsp;", "\n")

    definition_dict = recursive_nesting_by_category(definition_text)
    if isinstance(definition_dict, dict):
        definition_text = dict_to_text(definition_dict)
    else:
        definition_text = definition_dict

    definition_text = re.sub(r"。{2,}", "", definition_text)
    
    

    definition_text = definition_text.strip("\n").strip()
    return definition_text   


def get_text_only_from_dictionary(word: str, reading: str, definition_data: list, dic_name: str) -> str:
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
                """
                Add in a seperator, so later we can filter out 
                unwanted text easily.
                Make sure the seperator definitely won't appear 
                in the definitions
                """
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
                    first, second = current
                    # if dic_name.endswith("使い方の分かる 類語例解辞典"):
                    #     reading_data, ruigigo_data = first, second

                    #     if "content" in ruigigo_data and "content" in reading:
                    #         if isinstance(ruigigo_data["content"], str):
                    #             actually_is_ruigigo = re.search(r"(.+?／)+(.+)", ruigigo_data["content"])
                    #             if actually_is_ruigigo:
                    #                 # The actual 類義語 part.
                    #                 flag = False

                    # These two are essentially the same thing.
                    if dic_name.endswith("実用日本語表現辞典") or dic_name.endswith("使い方の分かる 類語例解辞典"):
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
                        unwanted_tags = re.compile("表記|品詞|用例|注記|歴史仮名|区別|ルビ|見出|可能形|異字同訓")

                        if dic_name.endswith("大辞林"):
                            if current_name == "ref":
                                if isinstance(content, dict) and "content" in content:
                                    # We already fetched it. This is current[content][content]
                                    if isinstance(content, str):
                                         if re.search(fr"^[{NUMBER_CHARS}]$", content["content"]):
                                            # Convert references to items in the same entry to something
                                            # that wont be picked up by the regexes later
                                            content["content"] = f'({REFERENCE_NUMBER_MAP[content["content"]]})'
                            
                            elif current_name == "単位名" and "content" in current["data"]:
                                if isinstance(current["data"]["content"], str):
                                # (センチメートル)
                                    current["data"]["content"] = current["data"]["content"][1:-1]
                            elif unwanted_tags.search(current_name):
                                flag = False

                        if dic_name.endswith("使い方の分かる 類語例解辞典") and current_name != "意味":
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

                            if unwanted_tags.search(current_name):
                                # Pretty sure 三省堂国語辞典 doesn't have this but 大辞林 does.
                                flag = False

                            elif "参照語義番号" in current_name:
                                if "content" in content:
                                    if isinstance(content["content"], str):
                                        reference_number = re.search(fr"^({NUMBER_CHARS})$", content["content"])
                                        if reference_number:
                                            content["content"] = f'({REFERENCE_NUMBER_MAP[content["content"]]})'
                    
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

                if dic_name.endswith("三省堂国語辞典"):
                    ...

                if flag:
                    if content:
                        stack.append(content)
            else:
                print(f"Unexpected type encountered in dictionary '{dic_name}': {type(current)}")  # Logging unexpected types
        return "".join(result)

    my_text = get_non_recursive(definition_data)
    return clean_definition(word, reading, my_text, dic_name)

def edit_big_data(big_data, dictionary_path, word, reading, definitions):
    # Given a word, its reading, and its definition, it creates a new datapoint 
    # for said word/reading.

    """
    big_data = {
        "dictionary_path": {
            "word": {
                "reading1": ["definitions_1"],
                "reading2": ["definitions_2"],
            }
        }
    }
    """
    
    if word not in big_data[dictionary_path]:
        big_data[dictionary_path][word] = {}

    if reading not in big_data[dictionary_path][word]:
        big_data[dictionary_path][word][reading] = []
    
    if definitions:
        definitions = [x for x in definitions if "Weblio" not in x]
        big_data[dictionary_path][word][reading].extend(definitions)
        # Just in case there's dupelicates
        big_data[dictionary_path][word][reading] = list(set(big_data[dictionary_path][word][reading]))


def load_big_data(big_data_dictionary, override=False):
    if not override:
        with open("big_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("You're about to override big_data, continue?\ny\\N")
        user_choice = input()
        if user_choice != "y":
            exit()
        for dictionary_path in PRIORITY_ORDER:
            add_dictionary_to_big_data(dictionary_path, big_data_dictionary)

        # add_dictionary_to_big_data("6. 旺文社国語辞典 第十一版", big_data_dictionary)
        # add_dictionary_to_big_data("4. 使い方の分かる 類語例解辞典", big_data_dictionary)
        # add_dictionary_to_big_data("8. Weblio", big_data_dictionary)

        # Write the final big_data to a JSON file
        save_to_big_data(big_data_dictionary)
        return big_data_dictionary

def save_to_big_data(big_data_dictionary):
    with open(BIG_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(big_data_dictionary, f, ensure_ascii=False, indent=2)
    print("Saved to big data")

if __name__ == "__main__":

    big_data_dictionary = load_big_data(big_data_dictionary, override=True)
    