import hmac
import secrets
from hashlib import pbkdf2_hmac


PIN_MIN_LENGTH = 4
PIN_MAX_LENGTH = 8
PIN_ITERATIONS = 210_000


def disabled_pin_protection():
    return {"enabled": False}


def pin_protection_is_disabled(protection):
    return (
        isinstance(protection, dict)
        and protection.get("enabled") is False
    )


def pin_protection_is_enabled(protection):
    return (
        isinstance(protection, dict)
        and protection.get("algorithm") == "pbkdf2_sha256"
    )


def validate_pin(pin):
    pin = str(pin)

    if not pin.isdigit():
        return False, "PIN 只能輸入數字。"

    if not PIN_MIN_LENGTH <= len(pin) <= PIN_MAX_LENGTH:
        return False, "PIN 必須是 4～8 位數字。"

    return True, ""


def create_pin_protection(pin):
    valid, message = validate_pin(pin)

    if not valid:
        raise ValueError(message)

    salt = secrets.token_bytes(16)
    digest = pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt,
        PIN_ITERATIONS
    )

    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": PIN_ITERATIONS,
        "length": len(pin),
        "salt": salt.hex(),
        "digest": digest.hex()
    }


def verify_pin(pin, protection):
    if not isinstance(protection, dict):
        return False

    try:
        if not pin_protection_is_enabled(protection):
            return False

        iterations = int(protection["iterations"])
        salt = bytes.fromhex(protection["salt"])
        expected_digest = bytes.fromhex(protection["digest"])
    except (KeyError, TypeError, ValueError):
        return False

    if iterations < 100_000 or not salt or not expected_digest:
        return False

    actual_digest = pbkdf2_hmac(
        "sha256",
        str(pin).encode("utf-8"),
        salt,
        iterations
    )
    return hmac.compare_digest(actual_digest, expected_digest)
