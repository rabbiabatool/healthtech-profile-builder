import re
import unicodedata

from rest_framework import serializers

PHONE_CHARACTERS = re.compile(r"\+?[0-9 ()\-]+")


def single_line_text(value):
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise serializers.ValidationError("Control characters are not allowed.")
    return value


def multi_line_text(value):
    if any(unicodedata.category(character) == "Cc" and character not in "\n\r\t" for character in value):
        raise serializers.ValidationError("Control characters are not allowed.")
    return value


def phone_number(value):
    value = value.strip()
    if not PHONE_CHARACTERS.fullmatch(value):
        raise serializers.ValidationError("Use digits, spaces, dashes, brackets and an optional leading +.")
    digits = sum(character.isdigit() for character in value)
    if not 7 <= digits <= 15:
        raise serializers.ValidationError("A phone number needs between 7 and 15 digits.")
    return value
