"""
Weblio.jp scraper
"""
import requests
from bs4 import BeautifulSoup as bs4
import json
import re
from time import sleep

katakana_to_hiragana = {
    chr(k): chr(k - 96) for k in range(12450, 12534) 
}


def get_hiragana_only(text):
    text = convert_word_to_hiragana(text)
    text = re.sub(r"\[(?:[あ-ゔー]+)(?:/|／|・|\n| |<br ?\\?>)([あ-ゔ]+)\]", r"\1", text)
    text = re.sub(r"[^あ-ゔー]", r"", text)
    return text


def convert_word_to_hiragana(word):
    # Katakana to Hiragana Conversion
    for k in [letter for letter in katakana_to_hiragana if letter in word]:
        word = word.replace(k, katakana_to_hiragana[k])
    return word


# Function to search for a word in Weblio's dictionary
def scrape_weblio(word, desired_reading=None):
    # Initialize dictionary to store the result
    desired_dictionaries = ["百科事典", "デジタル大辞泉", "実用日本語表現辞典", "難読語辞典",
                            "季語・季題辞典", " Wiktionary日本語版（日本語カテゴリ）", "新語時事用語辞典 ",
                            "ウィキペディア"]
    NetDict = {

    }

    url=u'https://www.weblio.jp/content/{word}'.format(word=word)
    get_requests=requests.get(url,timeout=5)
    content=get_requests.content
    soup=bs4(content,'html.parser').find('div',attrs={'id':'main'})

    # Removing specific unwanted phrases in one pass


    unwanted_patterns = [
        r"\n英語\n.+",
        r"\[続きの解説\].+",
        r"» ?類語の一覧を見る.+",
        r"\[可能\].+",
        r"\[派生\].+",
        r"\[用法\].+",
        r"\[補説\].+",
        r"\[下接語\].+",
        r"［[^］]+?］(?: ?\(.+?\))?",
        "「[^」]+?」の発音・読み方.+",
        "「[^」]+?」の類語、言い換え表現.+",
        "「[^」]+?」の熟語・言い回し.+",
        "「[^」]+?」の定義を英語で解説.+",
        "「[^」]+?」の類語.+",
        "「[^」]+?」に関連する用語・表現.+",
        "「[^」]+?」とは・「[^」]+?」の詳しい解説.+",
        "「[^」]+?」の語源・由来.+",
        "「[^」]+?」の類義語.+",
        "「[^」]+?」に似た言葉.+",
        r"\([^)]+? から転送\).+"
    ]
    try:
        for tr in soup.find_all('tr'):
            tr.decompose()  # Removes the <tr> tag and its contents

        # Convert unwanted patterns list into a single regex pattern
        pattern = "|".join(unwanted_patterns)


        # Iterate over each pbarT and its corresponding kijiWrp
        for pbar in soup.find_all('div', attrs={'class': 'pbarT'}):
            # Extract the dictionary name from the pbarT's title attribute
            dict_name_tag = pbar.find('a', attrs={'title': True})
            dict_name = dict_name_tag['title'] if dict_name_tag else "Unknown Dictionary"
            
            # Find the corresponding kijiWrp for this dictionary
            kiji_wrapper = pbar.find_next_sibling('div', class_='kijiWrp')

            if not kiji_wrapper:
                continue
            # Initialize a list for storing entries under each dictionary name
            dict_entries = []
            # Process each kiji entry within the current kijiWrp
            for entry in kiji_wrapper.find_all('div', attrs={'class': 'kiji'}):

                # Extract the main word from 'midashigo'
                word_tag = entry.find('h2', attrs={'class': 'midashigo'})
                main_word = word_tag['title'] if word_tag else ""

                # Extract reading and definitions
                definition_div = word_tag.find_next_sibling('div')
                if definition_div:
                    # Get reading from the first <p> in 'Sgkdj'
                    reading_tag = definition_div.find('p')
                    reading = reading_tag.text.replace("読み方：", "").strip() if reading_tag else ""
                    
                    if reading:
                        reading = re.sub(rf"\(.+?\)|（.+?）|出典.+", "", reading)
                        if "," in reading:
                            reading = reading.split(",")[0]
                        else:
                            reading = reading

                    if dict_name not in desired_dictionaries:
                        continue
                
                    # Collect all paragraphs in 'Sgkdj' as the definition text
                    definition_parts = [
                        p.text.strip() for p in definition_div.find_all(["p", "h3", "div", "li"])
                        if p != reading_tag  # Skip the reading paragraph
                    ]
                    definition_parts = [x.replace(" ", " ").replace(" ", " ")
                                        for x in 
                                        definition_parts]

                    # !todo: make it parse ウィキペディア correctly

                    cleaned_definition = re.sub(pattern, '', "\n".join(definition_parts), flags=re.S)
                    cleaned_definition = re.sub(r"\n+", "\n", cleaned_definition)

                    if dict_name == "百科事典":
                        cleaned_definition = re.sub(r"\[\d+\]", "", cleaned_definition)
                    elif dict_name == " Wiktionary日本語版（日本語カテゴリ）":
                        cleaned_definition = cleaned_definition.split("発音(?)")[0]
                    elif dict_name == "ウィキペディア":
                        cleaned_definition = re.sub(r"［.+?」も参照.+|概要.+", "", cleaned_definition)
                else:
                    reading = ""
                    cleaned_definition = ""

                # Extract synonyms from 'synonymsUnderDict'
                synonyms_tag = entry.find('div', attrs={'class': 'synonymsUnderDict'})
                synonyms = [
                    a.text.strip() for a in synonyms_tag.find_all('a')
                ] if synonyms_tag else []

                cleaned_definition = cleaned_definition.strip("\n")
                if cleaned_definition:
                    # Add the gathered information as an entry
                    dict_entries.append({
                        'word': main_word,
                        'reading': reading,
                        'definition': cleaned_definition,
                        'synonyms': synonyms
                    })
            
            # Add this dictionary's entries to NetDict
            if dict_entries:
                NetDict[dict_name] = dict_entries

    except Exception as e:
        return {}
        
    return NetDict


def kotobank_clean_word(word, dictionary_name):
    _OPENING_BRACKETS = r"<（「\[〔\(『［〈《〔〘｟"
    _CLOSING_BRACKETS = r">）」\]〕\)』］〉》〕〙｠"

    till_first_space = ["ブリタニカ国際大百科事典 小項目事典", 
                        "日本大百科全書(ニッポニカ)",
                        "日本大百科全書(ニッポニカ)"]

    in_brackets = ["精選版 日本国語大辞典",
                   "日本の美術館・博物館INDEX",
                   "デジタル大辞泉"]

    if dictionary_name in in_brackets:
        word = re.sub(r"[あ-ゔー・‐〔〕()‥]+【([^】]+?)】", r"\1", word)
# の【野】 と なれ山((やま))となれ
    if dictionary_name in till_first_space:
        word = word.split(" ")[0]
    
    word = re.sub(rf"[{_OPENING_BRACKETS}].+?[{_OPENING_BRACKETS}]", "", word)
    word = re.sub(r"[‐・◦▽×= ]", "", word)
    word = word.split("／")[0]
    if dictionary_name not in till_first_space and dictionary_name not in in_brackets:
        None

    return word

def kotobank_clean_definition(word, definition, dictionary_name):
    remove_first_brackets = ["精選版 日本国語大辞典",
                             "日本大百科全書(ニッポニカ)",
                             "ブリタニカ国際大百科事典 小項目事典"]

    remove_final_sections =       ["精選版 日本国語大辞典",
                             "日本大百科全書(ニッポニカ)",
                             "ブリタニカ国際大百科事典 小項目事典",
                             "デジタル大辞泉"]

    if dictionary_name in remove_first_brackets:
        definition = re.sub(r"〘.+?〙", "", definition)

    if dictionary_name in remove_final_sections:
        definition = re.sub(r"\[(?:初出の実例|類語)\].+", "", definition)

    return definition


def scrape_kotobank(word, desired_reading=None):

    url=u'https://kotobank.jp/search?q={word}&t=all'.format(word=word)
    get_requests=requests.get(url,timeout=5)
    content=get_requests.content
    soup=bs4(content,'html.parser').find('div',attrs={'id':'mainArea'})

    results = {}
    # if word == "野となれ山となれ":
    for dl in soup.find_all('dl'):
        # Extract the word
        word_tag = dl.find("h4").find("a") if dl.find("h4") else None
        word_found = word_tag.text.strip() if word_tag else "N/A"
        link = word_tag['href'] if word_tag and 'href' in word_tag.attrs else None

        # Extract the dictionary name
        dictionary_tag = dl.find("dd", class_="dictionary_name")
        dictionary_name = dictionary_tag.text.strip() if dictionary_tag else "N/A"

        # Extract the definition
        description_tag = dl.find("dd", class_="description")
        definition = description_tag.text.strip() if description_tag else "N/A"

        word_found = kotobank_clean_word(word_found, dictionary_name)

        if word_found != word:
            continue  # Not the word we're looking for

        # Check if the definition ends with "..."
        # This means the definition isn't the full text

        if definition.endswith('…') and link:
            try:
                # Fetch the content of the link
                response = requests.get(f"https://kotobank.jp{link}")
                if response.status_code == 200:
                    linked_soup = bs4(response.text, 'html.parser')
                    # Extract the full definition from the linked page (example selector, may vary)
                    full_definition = linked_soup.find("section", class_="description")
                    definition = full_definition.text.strip() if full_definition else definition

            except Exception as e:
                print(f"Failed to fetch the full definition from {link}: {e}")

        definition = kotobank_clean_definition(word_found, definition, dictionary_name)

        if not definition:
            continue

        if dictionary_name not in results:
            results[dictionary_name] = []

        results[dictionary_name].append(definition)

    return results

# # Main code: Get input word and perform the Weblio search
# word = input("Enter the word to search: ")
# data = scrape_kotobank(word)
# print(json.dumps(data, indent=2, ensure_ascii=False))