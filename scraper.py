"""
Weblio.jp scraper
"""

from re import sub
from time import sleep
import requests
from bs4 import BeautifulSoup


def remove_unwanted_text(content, word):
    # Pattern for removing unwanted sections
    content = sub(
        r"(?:［常用漢字］　)?(［.］([ア-ヺ]+　?)*)?(?:（.）(?:（[ア-ヺ]+）)?)?(?:（.）(?:（[ア-ヺ]+）)?)?　(［.］([あ-ゔ]+　?)*)",
        "",
        content,
    )

    # Removing specific unwanted phrases in one pass
    unwanted_patterns = [
        "» 類語の一覧を見る",
        "[続きの解説]",
        f"({word} から転送)",
        "[可能]",
        f"「{word}」の発音・読み方",
        f"「{word}」の類語、言い換え表現",
        f"「{word}」の熟語・言い回し",
        f"「{word}」の定義を英語で解説",
        f"「{word}」の類語",
        f"「{word}」に関連する用語・表現",
        f"「{word}」とは・「{word}」の詳しい解説",
        f"「{word}」の語源・由来",
        f"「{word}」の類義語",
        f"「{word}」に似た言葉",
        "出典:",
        "[用法]",
        "[補説]",
        "[下接語] ",
    ]

    for pattern in unwanted_patterns:
        content = content.split(pattern)[0]

    content = sub(rf"^「{word}」とは、", "", content).replace(" ", " ")

    return content


def get_hiragana_only(text):
    text = convert_word_to_hiragana(text)
    text = sub(r"\[(?:[あ-ゔー]+)(?:/|／|・|\n| |<br ?\\?>)([あ-ゔ]+)\]", r"\1", text)
    text = sub(r"[^あ-ゔー]", r"", text)
    return text


def convert_word_to_hiragana(word):
    # Katakana to Hiragana Conversion
    katakana_to_hiragana = {
        chr(k): chr(k - 96) for k in range(12450, 12534)
    }  # Katakana to Hiragana
    for k in katakana_to_hiragana:
        word = word.replace(k, katakana_to_hiragana[k])
    return word


# def log(function):
#     def inner(*args, **kwargs):
#         result = function(*args, **kwargs)
#         if not result[1]:
#             with open("log.txt", "a", encoding="utf-8") as f:
#                 f.write(f"{result[0]}\n")  # Use f-string for correct formatting
#         return result  # Return the results

#     return inner


def scrape_weblio(word, desired_reading=None):
    # Clean the word, removing text within parentheses
    word = sub(r"(?:<|く|｠|〔違い〕|\[派生\]).+", "", word)  # bad barsing. fix later
    word = sub(r"（.+?）", "", word)  # bad barsing. fix later

    if not word:
        return []

    if word[0] == "っ":
        word = word[1:]
    if "／" in word:  # bad barsing. fix later
        word = word.split("／")[-1]
    url = f"https://www.weblio.jp/content/{word}"

    if not word:
        return None

    # Send a request to the URL
    response = requests.get(url, timeout=3)
    sleep(1)
    if response.status_code != 200:
        print(f"Failed to retrieve data for {word}")
        return None

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # Find all <h2> with the class "midashigo"
    h2_midashigos = soup.find_all("h2", {"class": "midashigo"})
    if not h2_midashigos:
        print(f"No <h2> with class 'midashigo' found for {word}")
        return None

    for h2_midashigo in h2_midashigos:
        if h2_midashigo.text.endswith("例文・使い方・用例・文例"):
            continue

        la_palabra = h2_midashigo.title if h2_midashigo.title else word

        # Get the next <div> after each <h2>
        div_after_h2 = h2_midashigo.find_next("div")
        if not div_after_h2:
            print(f"No <div> found after <h2> for {h2_midashigo.text}")
            continue

        # Remove all <a>, <p>, <h3>, and <div> tags by replacing them with their text content
        for tag in div_after_h2.find_all(["a", "p", "h3", "div"]):
            tag.replace_with(tag.get_text())

        gather_text = []
        yomikata = None

        # Find the position of <br class="AM">
        br_am = div_after_h2.find("br", {"class": "AM"})
        element_to_loop_over = br_am if br_am else div_after_h2
        looper = (
            element_to_loop_over.next_siblings
            if element_to_loop_over.name == "br"
            else div_after_h2.contents
        )

        for sibling in looper:
            if isinstance(sibling, str):
                text = sibling.strip()
                text, yomikata_temp = check(text, word)
                if yomikata_temp and not yomikata:
                    yomikata = yomikata_temp
                gather_text.append(text)
            elif sibling.name == "synonymsUnderDictWrp":
                continue
            elif sibling.name.endswith("publish-date"):
                continue
            elif sibling.name:
                text = sibling.get_text(strip=True)
                text, yomikata_temp = check(text, word)
                if yomikata_temp and not yomikata:
                    yomikata = yomikata_temp
                gather_text.append(text)

        if desired_reading and desired_reading != yomikata:
            continue
        final_content = "".join(filter(None, gather_text)).strip()

        # Remove unwanted sections
        if (
            "日本語例文用例辞書はプログラムで機械的に例文を生成しているため、不適切な項目が含まれていることもあります。ご了承くださいませ"
            in final_content
        ):
            continue

        final_content = remove_unwanted_text(final_content, word)
        final_content = sub(rf"^「{word}」とは、", "", final_content)
        final_content = final_content.replace(" ", " ")
        # 発音・読み方
        if yomikata != "null" and len(final_content) < 400:
            yomikata = get_hiragana_only(
                convert_word_to_hiragana(yomikata if yomikata else word)
            )
            results.append((la_palabra, final_content, yomikata))
        else:
            href = f'<a href="{url}" title="{la_palabra} Definition from Weblio"</a>'
            results.append((la_palabra, href, yomikata))

    return results


def check(text, word):
    """
    Checks an HTML element to see if we should add it
    parameters:
      - text: str
      - word: str
    """
    word = sub("［.+?］", "", word)
    skip_phrases = {
        "別表記",
        f"「{word}」の意味・「{word}」とは",
        "の意味を調べる",
        "とは / 意味",
    }
    if any(phrase in text for phrase in skip_phrases):
        return "", None

    if "読み方" in text:
        return "", text.replace("読み方：", "")

    text = sub(r"^\s?「?.+?」?とは?(?:（.+?）)?は、", "", text)
    return text, None


# print(scrape_weblio("図らずも"))
# print(scrape_weblio("気が向かない"))
