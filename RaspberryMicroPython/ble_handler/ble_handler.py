import uasyncio as asyncio
from queue import Queue, QueueFull
import aioble
import bluetooth
import globals
import pico_config as config
from ble_handler.config import *
from ble_handler.ble_commands import *
from ble_handler.ble_midi import decode_midi_messages, encode_midi_packet
from game import game_manager


class BLEHandler:
    # Restrict dynamic dictionary allocation to save RAM on Pico[cite: 1]
    __slots__ = (
        "service",
        "midi_service",
        "event_char",
        "event_queue",
        "command_char",
        "stream_char",
        "midi_char",
        "_ble",
        "_connected",
        "_conn",
        "_dropped_events",
        "_stream_buffer",
        "_stream_total_size",
        "_stream_message_type",
    )

    def __init__(self):
        self._ble = None
        self._connected = False
        self._conn = None
        self.event_queue = Queue(maxsize=config.BLE_EVENT_CHANNEL_MAX_QUEUE_SIZE)  # Queue for event data
        self._dropped_events = 0
        self._stream_buffer = bytearray()
        self._stream_total_size = 0
        self._stream_message_type = 0
        globals.midiboard_mode = None

        # Instantiate GATT structure
        self.service = aioble.Service(config.BLE_SERVICE_UUID)
        self.event_char = aioble.Characteristic(
            self.service, config.BLE_EVENT_UUID, notify=True
        )
        self.command_char = aioble.Characteristic(
            self.service, config.BLE_COMMAND_UUID, write_no_response=True
        )
        # Buffered: a plain characteristic keeps only the first 20 bytes of a write
        self.stream_char = aioble.BufferedCharacteristic(
            self.service, config.BLE_DATA_STREAM_UUID, write=True, indicate=True,
            max_len=config.BLE_STREAM_MAX_WRITE,
        )
        self.midi_service = aioble.Service(config.BLE_MIDI_SERVICE_UUID)
        # MIDI I/O characteristic as the BLE MIDI spec asks: read (answers an empty value), write
        # without response and notify. Buffered, so packets up to MTU - 3 bytes fit, and captured,
        # so packets that arrive back to back are all processed.
        self.midi_char = aioble.BufferedCharacteristic(
            self.midi_service,
            config.BLE_MIDI_CHAR_UUID,
            read=True,
            write=True,
            write_no_response=True,
            notify=True,
            max_len=config.BLE_STREAM_MAX_WRITE,
            capture=True,
        )

    async def start(self):
        """Clean hardware startup sequence to clear CYW43 locks[cite: 1, 2]."""
        ble_inst = bluetooth.BLE()
        if ble_inst.active():
            ble_inst.active(False)
        await asyncio.sleep_ms(100)
        ble_inst.active(True)
        self._ble = ble_inst
        aioble.config(mtu=config.BLE_MTU)

        aioble.register_services(self.service, self.midi_service)
        # Launch concurrent internal tasks
        asyncio.create_task(self._advertising_loop())
        asyncio.create_task(self._event_channel_loop())
        asyncio.create_task(self._command_channel_loop())
        asyncio.create_task(self._stream_channel_loop())
        asyncio.create_task(self._midi_channel_loop())

    async def _advertising_loop(self):
        """Handles advertising and client connections."""
        while True:
            print(f"[BLE] Advertising as '{config.BLE_DEVICE_NAME}'...")
            try:
                self._conn = await aioble.advertise(
                    100_000,
                    name=config.BLE_DEVICE_NAME,
                    services=[config.BLE_MIDI_SERVICE_UUID]
                )
                self._connected = True
                print(f"[BLE] Connected to: {self._conn.device}")
                # A MIDI host usually only subscribes to the MIDI notifications and may never write,
                # so until a write chooses the session mode, the subscriptions are checked as well.
                while globals.midiboard_mode is None and self._conn.is_connected():
                    self._check_subscriptions()
                    await asyncio.sleep_ms(config.BLE_SESSION_POLL_MS)
                await self._conn.disconnected()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[BLE Error] Advertising loop fault: {e}")
            finally:
                self._end_session()

    def _end_session(self):
        """After a disconnect: no session mode any more, and after a MIDI session the games come back."""
        was_midi = globals.midiboard_mode == config.BOARD_MODE_MIDI
        self._connected = False
        self._conn = None
        globals.midiboard_mode = None
        self._reset_stream()
        self._clear_subscriptions()
        if was_midi:
            print("[BLE] MIDI device disconnected: back to the start screen")
            try:
                game_manager.open_start_screen()
            except Exception as exc:
                print(f"[BLE Error] Could not open the start screen: {exc}")

    async def _command_channel_loop(self):
        """Processes low-latency commands."""
        while True:
            conn = await self.command_char.written()
            data = self.command_char.read()
            if data:
                if self._select_session(config.BOARD_MODE_GAME):
                    self._on_command(data)

    async def _midi_channel_loop(self):
        """Processes incoming BLE MIDI packets; the first one also selects the MIDI session."""
        while True:
            conn, data = await self.midi_char.written()
            self._on_midi_packet(conn, data)

    def _on_midi_packet(self, conn, data):
        self.midi_char.write(b"")  # a read answers an empty value, as the BLE MIDI spec asks
        try:
            messages = decode_midi_messages(data)
        except ValueError as exc:
            print(f"[BLE MIDI Error] Invalid packet: {exc}")
            return
        if self._select_session(config.BOARD_MODE_MIDI):
            for timestamp, message in messages:
                self.on_midi_message(message, timestamp, conn)

    async def _stream_channel_loop(self):
        """Processes stream data with acknowledgment."""
        while True:
            conn = await self.stream_char.written()
            data = self.stream_char.read()
            if data:
                if self._select_session(config.BOARD_MODE_GAME):
                    try:
                        self.on_stream(data)
                    except Exception as e:
                        # A bad transfer must not end this loop, or the stream channel is dead until reboot
                        print(f"[BLE Error] Stream message rejected: {e}")
                        self._reset_stream()
                        self._send_ble_error(BLE_ERROR_CODE_INVALID_STREAM, data[0])
                await self.stream_char.indicate(conn, b"ACK")

    async def _event_channel_loop(self):
        """Send the queued events to the connected client, one notification each."""
        while True:
            event = await self.event_queue.get()
            if self._connected and self._conn:
                try:
                    if config.BLE_EVENT_DEBUG_LOG:
                        print(f"[BLE] Sending event notification: {event.hex()}")
                    self.event_char.notify(self._conn, event)
                    await asyncio.sleep_ms(config.BLE_EVENT_CHANNEL_NOTIFICATION_INTERVAL_MS)  # Small delay to avoid overwhelming the client
                except Exception as e:
                    print(f"[BLE Error] Event notification failed: {e}")

    def send_event(self, event_id: int, event_data: bytes):
        """Queue an event for the connected client. Without a client, or when the queue is full, the event is dropped."""
        if not isinstance(event_data, bytes):
            raise ValueError("Event data must be of type 'bytes'.")
        if not self._connected or globals.midiboard_mode != config.BOARD_MODE_GAME:
            return
        try:
            self.event_queue.put_nowait(bytes([event_id]) + event_data)
        except QueueFull:
            self._dropped_events += 1
            if self._dropped_events == 1 or self._dropped_events % 50 == 0:
                print(f"[BLE Warning] Event queue is full, {self._dropped_events} events dropped so far.")

    def _select_session(self, mode):
        """The first game or MIDI traffic of a connection chooses its mode; the other kind is ignored
        until disconnect. In MIDI mode no game runs: the board shows the MIDI pads."""
        selected_mode = globals.midiboard_mode
        if selected_mode is None:
            globals.midiboard_mode = mode
            print("[BLE] Session mode: %s" % ("MIDI" if mode == config.BOARD_MODE_MIDI else "game"))
            if mode == config.BOARD_MODE_MIDI:
                try:
                    game_manager.open_midi_screen()
                except Exception as exc:
                    print(f"[BLE Error] Could not open MIDI mode: {exc}")
            return True
        if selected_mode != mode:
            print("[BLE] Ignoring %s traffic during %s session" % (
                "MIDI" if mode == config.BOARD_MODE_MIDI else "game",
                "MIDI" if selected_mode == config.BOARD_MODE_MIDI else "game",
            ))
            return False
        return True

    def _check_subscriptions(self):
        """Choose the session mode by subscription: MIDI notifications = MIDI host, game events or
        stream indications = game app."""
        if self._subscribed(self.midi_char):
            self._select_session(config.BOARD_MODE_MIDI)
        elif self._subscribed(self.event_char) or self._subscribed(self.stream_char):
            self._select_session(config.BOARD_MODE_GAME)

    def _subscribed(self, characteristic):
        # MicroPython with BTstack (Pico W) keeps each subscription (CCCD) in its attribute table at the
        # value handle + 1 and stores the client's writes there, but sends no IRQ for them. On other
        # Bluetooth stacks this read fails and only writes choose the mode.
        if self._ble is None:
            return False
        try:
            cccd = self._ble.gatts_read(characteristic._value_handle + 1)
        except (OSError, TypeError, ValueError):
            return False
        return bool(cccd) and (cccd[0] & 0x03) != 0

    def _clear_subscriptions(self):
        # The stored subscriptions outlive the connection: clear them, or the next client looks subscribed
        if self._ble is None:
            return
        for characteristic in (self.event_char, self.stream_char, self.midi_char):
            try:
                self._ble.gatts_write(characteristic._value_handle + 1, b"\x00\x00")
            except (OSError, TypeError, ValueError):
                pass

    def on_midi_message(self, message, timestamp, conn):
        """Handle incoming MIDI: the MIDI screen lights the pads of the notes the host plays."""
        print("[BLE MIDI] Received %s at %d ms" % (bytes(message).hex(), timestamp))
        game = globals.game
        if game is not None and game.config.game_id == config.GAME_ID_MIDI:
            game.midi_in(message)

    def send_midi(self, message, timestamp=None):
        if self._connected and self._conn and globals.midiboard_mode == config.BOARD_MODE_MIDI:
            try:
                self.midi_char.notify(self._conn, encode_midi_packet(message, timestamp))
            except (OSError, ValueError) as exc:
                # Called from the key interrupt: a full Bluetooth buffer must not break the key handling
                print(f"[BLE MIDI Error] Message not sent: {exc}")

    def _on_command(self, data: bytes):
        """Processes incoming C&C channel commands from the connected BLE client."""
        if not data:
            return
        cmd_id = data[0]
        print(f"[BLE Event] Received command 0x{cmd_id:02X} (length {len(data)})")
        try:
            if cmd_id == BLE_CMD_GAME_CONTROL or cmd_id == BLE_CMD_POCKET_GUITAR:
                if len(data) < 2:
                    self._send_ble_error(BLE_ERROR_CODE_INVALID_PAYLOAD, cmd_id)
                    raise ValueError("Command requires a subcommand byte.")
                print(f"[BLE Event] Command 0x{cmd_id:02X} / 0x{data[1]:02X}")
                if cmd_id == BLE_CMD_GAME_CONTROL:
                    game_interaction(data[1], data[2:])
                else:
                    pocket_guitar_interaction(data[1], data[2:])
                return

            self._send_ble_error(BLE_ERROR_CODE_WRONG_COMMAND, cmd_id)
            raise ValueError(f"Unsupported command ID: 0x{cmd_id:02X}")

        except Exception as e:
            print(f"[BLE Error] Failed to process command 0x{cmd_id:02X}: {e}")

    def _handle_stream_message(self, message_type: int, payload: bytes):
        """Decodes and dispatches a complete stream payload."""
        try:
            if message_type == BLE_STREAM_MSG_GAME_CONFIG or message_type == BLE_STREAM_MSG_GAME_LOAD:
                handle_stream_message(message_type, payload)
                return
            if message_type == BLE_STREAM_MSG_GAME_SELECT or message_type == BLE_STREAM_MSG_POCKET_GUITAR_SONG:
                handle_stream_message(message_type, payload)
                return
            print(f"[BLE Event] Unsupported stream message type 0x{message_type:02X}: {payload.hex()}")
        except Exception as exc:
            print(f"[BLE Error] Failed to process stream payload 0x{message_type:02X}: {exc}")
            self._send_ble_error(BLE_ERROR_CODE_GENERIC, message_type)

    def on_stream(self, data: bytes):
        """Processes chunked or single-shot stream payloads."""
        if not data:
            return

        message_type = data[0]
        payload = data[1:]
        if message_type != BLE_STREAM_MSG_CHUNK:  # a song is ~100 chunks, don't print them
            print(f"[BLE Event] Received stream message type 0x{message_type:02X}: {payload.hex()}")

        if message_type == BLE_STREAM_MSG_INIT:
            # [message type, total size u32 big-endian], or only [total size u32] when the
            # assembled data starts with its message type byte
            if len(payload) >= 5:
                self._stream_message_type = payload[0]
                size = payload[1:5]
            elif len(payload) == 4:
                self._stream_message_type = 0
                size = payload
            else:
                raise ValueError("Stream INIT payload requires the total size.")
            self._stream_total_size = int.from_bytes(size, "big")
            self._stream_buffer = bytearray()
            return

        if message_type == BLE_STREAM_MSG_CHUNK:
            if self._stream_total_size <= 0:
                raise ValueError("Chunk received before stream INIT.")
            self._stream_buffer.extend(payload)
            if len(self._stream_buffer) >= self._stream_total_size:
                self._finish_stream()
            return

        if message_type == BLE_STREAM_MSG_COMMIT:
            if self._stream_buffer:
                self._finish_stream()
            # Nothing buffered: the transfer was already handled when its last chunk arrived
            return

        if message_type == BLE_STREAM_MSG_ABORT:
            self._reset_stream()
            return

        self._handle_stream_message(message_type, payload)

    def _finish_stream(self):
        data = bytes(self._stream_buffer)
        if self._stream_total_size > 0:
            data = data[:self._stream_total_size]
        message_type = self._stream_message_type
        self._reset_stream()
        if not message_type:
            if not data:
                raise ValueError("Empty stream transfer.")
            message_type = data[0]
            data = data[1:]
        self._handle_stream_message(message_type, data)

    def _reset_stream(self):
        self._stream_buffer = bytearray()
        self._stream_total_size = 0
        self._stream_message_type = 0

    def _send_ble_error(self, error_code: int, payload: int | bytes = b""):
        if isinstance(payload, int):
            payload_bytes = bytes([payload & 0xFF])
        else:
            payload_bytes = bytes(payload) if payload else b""
        self.send_event(BLE_EVENT_ID_ERROR, bytes([error_code]) + payload_bytes)


    @property
    def is_connected(self) -> bool:
        return self._connected