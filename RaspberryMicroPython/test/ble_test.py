import asyncio
from bleak import BleakScanner, BleakClient

# Match the UUIDs configured on the Pico
SERVICE_UUID = "6E400000-B5A3-F393-E0A9-E50E24DCCA9E"
EVENT_CHAR_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
FAST_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
DATA_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# Test data stream to transfer over Channel 2
TEST_STREAM_DATA = (
    b'{"song": "Piano Tiles Test", "bpm": 120, "notes": [60, 62, 64, 65, 67, 69, 71]}'
)

async def test_event_channel(client: BleakClient):
    print("\n--- Testing Channel 0: Event Notifications ---")
    
    # Step 1: Subscribe to Event Characteristic notifications
    def event_notification_handler(sender, data):
        print(f"[EVENT CH] Notification from {sender}: {data.hex()}")

    await client.start_notify(EVENT_CHAR_UUID, event_notification_handler)
    while True:        
        await asyncio.sleep(0.1)

async def test_fast_channel(client: BleakClient):
    print("\n--- Testing Channel 1: Fast Event Commands ---")
    
    # 1. Send Audio Sound Trigger command (0x01, Sound ID: 5)
    sound_cmd = bytes([0x01, 0x05])
    print(f"[FAST CH] Sending Sound Trigger: {sound_cmd.hex()}")
    await client.write_gatt_char(FAST_CHAR_UUID, sound_cmd, response=False)
    await asyncio.sleep(0.5)

    # 2. Send Haptic Pulse command (0x02, Effect ID: 1)
    haptic_cmd = bytes([0x02, 0x01])
    print(f"[FAST CH] Sending Haptic Command: {haptic_cmd.hex()}")
    await client.write_gatt_char(FAST_CHAR_UUID, haptic_cmd, response=False)
    await asyncio.sleep(0.5)


async def test_stream_channel(client: BleakClient):
    print("\n--- Testing Channel 2: Chunked Data Stream ---")
    
    payload = TEST_STREAM_DATA
    total_length = len(payload)
    chunk_size = 20  # Payload chunk length (fits standard 23-byte MTU)

    # Step A: Send Transfer Header (Type 0x00 + 4-byte Big-Endian Length)
    header = bytes([0x00]) + total_length.to_bytes(4, byteorder="big")
    print(f"[STREAM CH] Sending Header: total_size={total_length} bytes")
    await client.write_gatt_char(DATA_CHAR_UUID, header, response=True)
    await asyncio.sleep(0.1)

    # Step B: Stream Data Chunks (Type 0x01 + 2-byte Sequence No. + Payload)
    seq_num = 0
    for offset in range(0, total_length, chunk_size):
        chunk_data = payload[offset : offset + chunk_size]
        packet = (
            bytes([0x01])
            + seq_num.to_bytes(2, byteorder="big")
            + chunk_data
        )
        print(f"[STREAM CH] Sending Chunk #{seq_num} ({len(chunk_data)} bytes)...")
        await client.write_gatt_char(DATA_CHAR_UUID, packet, response=True)
        seq_num += 1
        await asyncio.sleep(0.05)

    # Step C: Send End-of-Transfer Signal (Type 0x02)
    end_packet = bytes([0x02])
    print("[STREAM CH] Sending Transfer Complete signal...")
    await client.write_gatt_char(DATA_CHAR_UUID, end_packet, response=True)


async def main():
    print(f"Scanning for BLE Service: {SERVICE_UUID}...")
    device = await BleakScanner.find_device_by_filter(
        lambda dev, adv: SERVICE_UUID.lower() in [s.lower() for s in adv.service_uuids],
        timeout=10.0,
    )

    if not device:
        print("Device not found. Ensure the Pico is advertising!")
        return

    print(f"Found target peripheral: {device.name} [{device.address}]")

    async with BleakClient(device) as client:
        print(f"Connected successfully: {client.is_connected}")

        # Execute tests on both GATT channels sequentially
        asyncio.create_task(test_event_channel(client))
        await test_fast_channel(client)
        await test_stream_channel(client)


        print("\nAll channel tests finished.")

    
asyncio.run(main())