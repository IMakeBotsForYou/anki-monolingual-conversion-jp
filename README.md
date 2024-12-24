# anki-monolingual-conversion-jp
A script to convert JP->X decks to JP-JP using yomitan dictionaries.


Take your favourite YOMITAN dictionaries and export them into folders.
How the dictionary folders should look.

![](https://github.com/IMakeBotsForYou/anki-monolingual-conversion-jp/blob/main/github_page_media/directory.png?raw=true)


You can limit the amount of dictionaries by changing `stop_at` in `get_definitions`.

Dictionaries which don't have an exact match for the card will search using solely the reading,
and then be marked with a red color. "red" or "marked" dictionaries are automatically collapsed.


![](https://github.com/IMakeBotsForYou/anki-monolingual-conversion-jp/blob/main/github_page_media/ouhei.png?raw=true)
![](https://github.com/IMakeBotsForYou/anki-monolingual-conversion-jp/blob/main/github_page_media/ouhei_expanded.png?raw=true)
![](https://github.com/IMakeBotsForYou/anki-monolingual-conversion-jp/blob/main/github_page_media/nigeooseru.png?raw=true)

