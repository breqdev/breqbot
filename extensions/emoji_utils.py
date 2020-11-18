import string
import emoji


digit_names = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine"
}


def text_to_emoji(text, join=True, strict=False):
    emoji_text = []
    for letter in text:
        if letter in string.ascii_letters:
            emoji_text.append(emoji.emojize(
                f":regional_indicator_symbol_letter_{letter.lower()}:"))
        elif letter in string.digits:
            emoji_text.append(emoji.emojize(
                f":keycap_digit_{digit_names[int(letter)]}:"))
        elif letter == " ":
            emoji_text.append(emoji.emojize(":blue_square:"))
        elif letter == "?":
            emoji_text.append(emoji.emojize(":question_mark:"))
        elif letter == "!":
            emoji_text.append(emoji.emojize(":exclamation_mark:"))
        elif not strict:
            emoji_text.append(letter)
    if join:
        return "\u200b".join(emoji_text)
    else:
        return emoji_text
