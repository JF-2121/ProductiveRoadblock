import asyncio
import json

from bleak import BleakClient, BleakScanner

SERVICE_UUID = "6E400000-B5A3-F393-E0A9-E50E24DCCA9E"
EVENT_CHAR_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
COMMAND_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
STREAM_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

BLE_CMD_GAME_CONTROL = 0x01
BLE_GAME_CONTROL_START = 0x00
BLE_GAME_CONTROL_STOP = 0x01
BLE_GAME_CONTROL_RESET = 0x02
BLE_GAME_CONTROL_RESUME = 0x03
BLE_GAME_CONTROL_SELECT = 0x04
BLE_GAME_CONTROL_LOAD = 0x05

BLE_STREAM_MSG_INIT = 0x10
BLE_STREAM_MSG_CHUNK = 0x11
BLE_STREAM_MSG_COMMIT = 0x12
BLE_STREAM_MSG_ABORT = 0x13
BLE_STREAM_MSG_GAME_CONFIG = 0x20
BLE_STREAM_MSG_GAME_SELECT = 0x21
BLE_STREAM_MSG_GAME_LOAD = 0x22

BLE_STREAM_FIELD_GAME_ID = 0x01
BLE_STREAM_FIELD_SEED = 0x02
BLE_STREAM_FIELD_NUM_STEPS = 0x03
BLE_STREAM_FIELD_HIT_ACTION = 0x04
BLE_STREAM_FIELD_MISS_ACTION = 0x05
BLE_STREAM_FIELD_GAME_NAME = 0x06


def encode_varint(value: int) -> bytes:
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


def encode_tag(field_number: int, wire_type: int) -> bytes:
    return encode_varint((field_number << 3) | wire_type)


def encode_field(field_number: int, wire_type: int, value) -> bytes:
    payload = bytearray()
    payload.extend(encode_tag(field_number, wire_type))
    if wire_type == 0:
        payload.extend(encode_varint(int(value)))
        return bytes(payload)
    if wire_type == 2:
        if isinstance(value, str):
            value = value.encode("utf-8")
        value = bytes(value)
        payload.extend(encode_varint(len(value)))
        payload.extend(value)
        return bytes(payload)
    raise ValueError(f"Unsupported wire type: {wire_type}")


def make_game_config_message(game_id: int, seed: int, num_steps: int, hit_action: dict, miss_action: dict, name: str):
    payload = bytearray()
    payload.extend(encode_field(BLE_STREAM_FIELD_GAME_ID, 0, game_id))
    payload.extend(encode_field(BLE_STREAM_FIELD_SEED, 0, seed))
    payload.extend(encode_field(BLE_STREAM_FIELD_NUM_STEPS, 0, num_steps))
    payload.extend(encode_field(BLE_STREAM_FIELD_HIT_ACTION, 2, json.dumps(hit_action, separators=(",", ":")).encode("utf-8")))
    payload.extend(encode_field(BLE_STREAM_FIELD_MISS_ACTION, 2, json.dumps(miss_action, separators=(",", ":")).encode("utf-8")))
    payload.extend(encode_field(BLE_STREAM_FIELD_GAME_NAME, 2, name.encode("utf-8")))
    return bytes([BLE_STREAM_MSG_GAME_CONFIG]) + bytes(payload)


async def subscribe_to_events(client: BleakClient):
    def handler(sender, data):
        print(f"[EVENT] {sender}: {data.hex()}")

    await client.start_notify(EVENT_CHAR_UUID, handler)
    print("[INFO] Event notifications enabled.")


async def send_command(client: BleakClient, command_id: int, subcommand: int, payload: bytes = b""):
    packet = bytes([command_id, subcommand]) + payload
    print(f"[CMD] Sending: {packet.hex()}")
    await client.write_gatt_char(COMMAND_CHAR_UUID, packet, response=False)
    await asyncio.sleep(0.25)


async def send_stream_game_config(client: BleakClient):
    hit_action = {
        "score": 10,
        "haptic": {"effect_id": 1, "duration_ms": 40},
        "feedback_color": [0, 150, 255],
    }
    miss_action = {
        "score": 0,
        "haptic": {"effect_id": 47, "duration_ms": 250},
        "action": "fail",
        "feedback_color": [255, 0, 0],
    }

    config_message = make_game_config_message(
        game_id=0x01,
        seed=123456,
        num_steps=12,
        hit_action=hit_action,
        miss_action=miss_action,
        name="seeded_piano_tiles",
    )

    print(f"[STREAM] Full config message length: {len(config_message)}")
    chunk_size = 18

    await client.write_gatt_char(STREAM_CHAR_UUID, bytes([BLE_STREAM_MSG_INIT, 0x00, 0x00, 0x00, len(config_message)]), response=True)
    for offset in range(0, len(config_message), chunk_size):
        chunk = config_message[offset:offset + chunk_size]
        packet = bytes([BLE_STREAM_MSG_CHUNK]) + chunk
        print(f"[STREAM] Sending chunk {offset // chunk_size}: {packet.hex()}")
        await client.write_gatt_char(STREAM_CHAR_UUID, packet, response=True)
        await asyncio.sleep(0.05)

    await client.write_gatt_char(STREAM_CHAR_UUID, bytes([BLE_STREAM_MSG_COMMIT]), response=True)
    print("[STREAM] Commit sent. Pico should load and start the generated game configuration.")


async def main():
    print("[INFO] Scanning for Pico BLE service...")
    device = await BleakScanner.find_device_by_filter(
        lambda dev, adv: SERVICE_UUID.lower() in [s.lower() for s in adv.service_uuids],
        timeout=10.0,
    )
    if not device:
        print("[ERROR] Pico not found. Ensure the device is advertising and in range.")
        return

    print(f"[INFO] Found device: {device.name} [{device.address}]")
    async with BleakClient(device) as client:
        await client.connect()
        print(f"[INFO] Connected: {client.is_connected}")

        await subscribe_to_events(client)

        print("\n--- Basic command test ---")
        await send_command(client, BLE_CMD_GAME_CONTROL, BLE_GAME_CONTROL_START)
        await asyncio.sleep(0.5)
        await send_command(client, BLE_CMD_GAME_CONTROL, BLE_GAME_CONTROL_SELECT, bytes([0x02]))
        await asyncio.sleep(0.5)
        await send_command(client, BLE_CMD_GAME_CONTROL, BLE_GAME_CONTROL_STOP)
        await asyncio.sleep(0.5)

        print("\n--- Streamed game-config test ---")
        await send_stream_game_config(client)
        await asyncio.sleep(1.0)

        print("\n[INFO] Done.")


if __name__ == "__main__":
    asyncio.run(main())
