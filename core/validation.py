import ipaddress
import re
from urllib.parse import urlparse


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ValidationError(ValueError):
    pass


def require_json_object(request):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    return data


def bounded_integer(value, field_name, minimum, maximum, default=None):
    selected_value = default if value is None else value
    try:
        integer_value = int(selected_value)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{field_name} must be an integer.") from error
    if integer_value < minimum or integer_value > maximum:
        raise ValidationError(f"{field_name} must be between {minimum} and {maximum}.")
    return integer_value


def limited_string(value, field_name, minimum_length=1, maximum_length=4096):
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    normalized_value = value.strip()
    if len(normalized_value) < minimum_length or len(normalized_value) > maximum_length:
        raise ValidationError(
            f"{field_name} length must be between {minimum_length} and {maximum_length}."
        )
    if any(ord(character) < 32 and character not in "\r\n\t" for character in normalized_value):
        raise ValidationError(f"{field_name} contains invalid control characters.")
    return normalized_value


def identifier(value, field_name):
    normalized_value = limited_string(value, field_name, 1, 128)
    if not IDENTIFIER_PATTERN.fullmatch(normalized_value):
        raise ValidationError(f"{field_name} has an invalid format.")
    return normalized_value


def ip_address(value, field_name):
    normalized_value = limited_string(value, field_name, 2, 64)
    try:
        return str(ipaddress.ip_address(normalized_value))
    except ValueError as error:
        raise ValidationError(f"{field_name} must be a valid IP address.") from error


def http_url(value, field_name):
    normalized_value = limited_string(value, field_name, 8, 2048)
    parsed_value = urlparse(normalized_value)
    if parsed_value.scheme not in {"http", "https"} or not parsed_value.hostname:
        raise ValidationError(f"{field_name} must be a valid HTTP or HTTPS URL.")
    if parsed_value.username or parsed_value.password:
        raise ValidationError(f"{field_name} must not contain embedded credentials.")
    return normalized_value.rstrip("/")
