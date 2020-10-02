import string
import emoji


def text_to_emoji(text):
    emoji_text = []
    for letter in text:
        if letter in string.ascii_letters:
            emoji_text.append(emoji.emojize(
                f":regional_indicator_symbol_letter_{letter.lower()}:"))
        elif letter == " ":
            emoji_text.append(emoji.emojize(":blue_square:"))
    return " ".join(emoji_text)
