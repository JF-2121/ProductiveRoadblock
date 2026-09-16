"""Bluetooth MIDI service for the Pico board.

The BLE MIDI specification uses a timestamp header before each MIDI message.
This module keeps the packet codec independent from aioble so it can also be
tested on a regular Python interpreter.

Packet layout: header byte (bit 7 set, bits 5-0 timestamp high), then for every
message a timestamp byte (bit 7 set, bits 6-0 timestamp low) and the MIDI message.
A message may leave out its status byte (running status), and then also its
timestamp byte. System real-time messages can appear between any two messages.
"""
import time


def _ticks_ms():
	return time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)


def _data_length(status):
	"""Number of data bytes after a status byte."""
	if status < 0xC0 or 0xE0 <= status < 0xF0:
		return 2  # note off/on, poly pressure, control change, pitch bend
	if status < 0xE0:
		return 1  # program change, channel pressure
	if status == 0xF2:
		return 2  # song position
	if status == 0xF1 or status == 0xF3:
		return 1  # time code quarter frame, song select
	return 0


def encode_midi_packet(message, timestamp=None):
	"""Return one BLE MIDI packet containing a single MIDI message."""
	message = bytes(message)
	if not message:
		raise ValueError("MIDI message must not be empty")
	if timestamp is None:
		timestamp = _ticks_ms()
	timestamp &= 0x1FFF
	return bytes((
		0x80 | ((timestamp >> 7) & 0x3F),
		0x80 | (timestamp & 0x7F),
	)) + message


def decode_midi_messages(packet):
	"""Return [(timestamp, message), ...] for all MIDI messages in a BLE MIDI packet.

	Handles several messages per packet, running status and system real-time messages.
	SysEx messages (also continued over several packets) are skipped.
	"""
	packet = bytes(packet)
	if len(packet) < 2 or packet[0] & 0xC0 != 0x80:
		raise ValueError("Invalid BLE MIDI packet")
	high = (packet[0] & 0x3F) << 7
	messages = []
	timestamp = 0
	status = 0
	# A packet that continues a SysEx starts with data bytes instead of a timestamp
	in_sysex = not packet[1] & 0x80
	i = 1
	count = len(packet)
	while i < count:
		byte = packet[i]
		if byte & 0x80:
			# Timestamp byte, then a status byte or data bytes with the running status
			timestamp = high | (byte & 0x7F)
			i += 1
			if i >= count:
				break
			byte = packet[i]
			if byte & 0x80:
				i += 1
				if byte >= 0xF8:
					messages.append((timestamp, bytes((byte,))))  # real-time, keeps the running status
				elif byte == 0xF0:
					in_sysex = True
					status = 0
				elif byte == 0xF7:
					in_sysex = False
				else:
					in_sysex = False
					status = byte
					if _data_length(status) == 0:
						messages.append((timestamp, bytes((status,))))
						status = 0
				continue
		if in_sysex or not status:
			i += 1  # SysEx data, or data bytes without a status: skipped
			continue
		end = i + _data_length(status)
		if end > count:
			break  # message cut off
		data = packet[i:end]
		for value in data:
			if value & 0x80:
				raise ValueError("Invalid BLE MIDI packet: status byte inside a message")
		messages.append((timestamp, bytes((status,)) + data))
		i = end
		if status >= 0xF0:
			status = 0  # system common messages have no running status
	return messages


def decode_midi_packet(packet):
	"""Return the timestamp and MIDI bytes of the first message in a BLE MIDI packet."""
	messages = decode_midi_messages(packet)
	if not messages:
		raise ValueError("Invalid BLE MIDI packet")
	return messages[0]
