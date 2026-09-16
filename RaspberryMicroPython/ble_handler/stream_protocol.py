try:
    from micropython import const
except ImportError:  # pragma: no cover - normal Python execution
    def const(value):
        return value

try:
    import json as _json
except ImportError:  # pragma: no cover
    try:
        import ujson as _json
    except ImportError:  # pragma: no cover
        _json = None


BLE_STREAM_MSG_INIT = const(0x10)
BLE_STREAM_MSG_CHUNK = const(0x11)
BLE_STREAM_MSG_COMMIT = const(0x12)
BLE_STREAM_MSG_ABORT = const(0x13)

BLE_STREAM_MSG_GAME_CONFIG = const(0x20)
BLE_STREAM_MSG_GAME_SELECT = const(0x21)
BLE_STREAM_MSG_GAME_LOAD = const(0x22)

BLE_STREAM_FIELD_GAME_ID = const(1)
BLE_STREAM_FIELD_SEED = const(2)
BLE_STREAM_FIELD_NUM_STEPS = const(3)
BLE_STREAM_FIELD_HIT_ACTION = const(4)
BLE_STREAM_FIELD_MISS_ACTION = const(5)
BLE_STREAM_FIELD_GAME_NAME = const(6)


def _encode_varint(value):
    value = int(value)
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def _decode_varint(buffer, offset):
    value = 0
    shift = 0
    while offset < len(buffer):
        byte = buffer[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, offset
        shift += 7
        if shift > 64:
            raise ValueError("Varint is too large.")
    raise ValueError("Truncated varint field.")


def _encode_tag(field_number, wire_type):
    return _encode_varint((field_number << 3) | wire_type)


def _encode_field(field_number, wire_type, value):
    payload = bytearray()
    payload.extend(_encode_tag(field_number, wire_type))
    if wire_type == 0:
        payload.extend(_encode_varint(value))
        return bytes(payload)
    if wire_type == 2:
        value_bytes = bytes(value)
        payload.extend(_encode_varint(len(value_bytes)))
        payload.extend(value_bytes)
        return bytes(payload)
    raise ValueError(f"Unsupported wire type: {wire_type}")


def _normalize_action_payload(action_value):
    if action_value is None:
        return b"{}"
    if isinstance(action_value, bytes):
        return action_value
    if isinstance(action_value, bytearray):
        return bytes(action_value)
    if isinstance(action_value, str):
        return action_value.encode("utf-8")
    if isinstance(action_value, dict):
        if _json is None:
            raise ValueError("JSON encoder is not available for action payloads.")
        return _json.dumps(action_value, separators=(",", ":")).encode("utf-8")
    raise TypeError(f"Unsupported action payload type: {type(action_value)!r}")


def encode_game_config_message(game_id, seed, num_steps, hit_action=None, miss_action=None, game_name=""):
    payload = bytearray()
    payload.extend(_encode_field(BLE_STREAM_FIELD_GAME_ID, 0, int(game_id)))
    payload.extend(_encode_field(BLE_STREAM_FIELD_SEED, 0, int(seed)))
    payload.extend(_encode_field(BLE_STREAM_FIELD_NUM_STEPS, 0, int(num_steps)))
    if hit_action is not None:
        payload.extend(_encode_field(BLE_STREAM_FIELD_HIT_ACTION, 2, _normalize_action_payload(hit_action)))
    if miss_action is not None:
        payload.extend(_encode_field(BLE_STREAM_FIELD_MISS_ACTION, 2, _normalize_action_payload(miss_action)))
    if game_name:
        payload.extend(_encode_field(BLE_STREAM_FIELD_GAME_NAME, 2, str(game_name).encode("utf-8")))
    return bytes([BLE_STREAM_MSG_GAME_CONFIG]) + bytes(payload)


def decode_game_config_message(message):
    if not message:
        return {}

    result = {}
    offset = 0
    while offset < len(message):
        tag, offset = _decode_varint(message, offset)
        field_number = tag >> 3
        wire_type = tag & 0x07

        if wire_type == 0:
            value, offset = _decode_varint(message, offset)
            result[field_number] = value
        elif wire_type == 2:
            length, offset = _decode_varint(message, offset)
            if offset + length > len(message):
                raise ValueError("Length-delimited field exceeds message length.")
            value = message[offset:offset + length]
            offset += length
            result[field_number] = value
        else:
            raise ValueError(f"Unsupported protobuf wire type {wire_type} for field {field_number}.")

    decoded = {}
    for field_number, value in result.items():
        if field_number == BLE_STREAM_FIELD_GAME_ID:
            decoded["game_id"] = int(value)
        elif field_number == BLE_STREAM_FIELD_SEED:
            decoded["seed"] = int(value)
        elif field_number == BLE_STREAM_FIELD_NUM_STEPS:
            decoded["num_steps"] = int(value)
        elif field_number == BLE_STREAM_FIELD_HIT_ACTION:
            decoded["hit_action"] = _decode_action_bytes(value)
        elif field_number == BLE_STREAM_FIELD_MISS_ACTION:
            decoded["miss_action"] = _decode_action_bytes(value)
        elif field_number == BLE_STREAM_FIELD_GAME_NAME:
            decoded["game_name"] = value.decode("utf-8")
    return decoded


def _decode_action_bytes(value):
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value)
        if not value:
            return {}
        try:
            if _json is not None:
                decoded = _json.loads(value.decode("utf-8"))
                return decoded if isinstance(decoded, dict) else {"raw": decoded}
        except Exception:
            pass
        return {"raw": value.decode("utf-8", "ignore")}
    return value


def make_stream_chunk_message(chunk_type, payload=b""):
    return bytes([chunk_type]) + bytes(payload)
