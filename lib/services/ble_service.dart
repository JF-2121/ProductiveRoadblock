import 'dart:async';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:flutter/foundation.dart';

/// Commands (phone -> board) on the command characteristic: [category, sub-command, payload...].
/// Must match raspberry-micro-python/ble_handler/config.py (BLE_CMD_*), byte layouts in its README.
class BleCommand {
  BleCommand._();
  static const int gameControl = 0x01;
  static const int start = 0x00;
  static const int stop = 0x01; // quit the game, back to the start screen
  static const int reset = 0x02; // quit the run, back to the game's ready screen
  static const int resume = 0x03;
  static const int select = 0x04; // [game_id] or [game_id, variant]
  static const int load = 0x05; // reload the open game (back to its ready screen)
  static const int triggerHaptic = 0x06; // [effect_id 1-123]
  static const int runAutocal = 0x07; // haptic auto-calibration; answered by a calibration-report event
  static const int setBrightness = 0x08; // [level 0-255]
  static const int getTelemetry = 0x09; // answered with a battery report event
  static const int pause = 0x0A;

  static const int pocketGuitar = 0x02;
  static const int selectSong = 0x00; // [slot] - a song stored on the board (select screen only)
  static const int selectDifficulty = 0x01; // [difficulty 0-3]
  static const int selectMode = 0x02; // [0 play, 1 practice]
  static const int setDelayOffset = 0x03; // [offset ms i16 little-endian]
  static const int setOptions = 0x04; // [bits: 0 beat lines, 1 beat tick, 2 sustain hum]
  static const int getSelection = 0x05;
}

/// Game ids for [BleCommand.select], see raspberry-micro-python/pico_config.py.
class BleGameId {
  BleGameId._();
  static const int startScreen = 0x00;
  static const int pianoTiles = 0x01;
  static const int simonSays = 0x02;
  static const int pocketGuitar = 0x03;
}

/// Events (board -> phone) on the event characteristic: [event id, payload...].
/// Must match raspberry-micro-python/ble_handler/config.py (BLE_EVENT_ID_*).
class BleEvent {
  BleEvent._();
  static const int key = 0x01; // [type (0 press, 1 release), grid_key]
  static const int game = 0x02; // [subtype, value...]
  static const int gameState = 0x00; // subtype: [state]
  static const int gameScore = 0x01; // subtype: [score u16 little-endian]
  static const int gameSelected = 0x02; // subtype: [game_id, variant]
  static const int sound = 0x03; // [sound_id, duration_low, duration_high]
  static const int batteryReport = 0x04; // [vbat mV u16, free KB u16, game_id, state, brightness]
  static const int calibrationReport = 0x05; // answer to BleCommand.runAutocal
  static const int songStart = 0x06;
  static const int noteResult = 0x07;
  static const int overstrum = 0x08;
  static const int sustainEnd = 0x09;
  static const int songResult = 0x0A;
  static const int songSelection = 0x0B;
  static const int simonSays = 0x0C; // [subtype, payload...], see BleSimonSays
  static const int pianoTiles = 0x0D; // [subtype, payload...], see BlePianoTiles
  static const int error = 0xFF; // [error code, offending command or value]
}

/// Subtypes of [BleEvent.simonSays] (integers little-endian), see raspberry-micro-python/README.md.
class BleSimonSays {
  BleSimonSays._();
  static const int runStart = 0x00; // mode, steps (0 = open end), lives
  static const int watch = 0x01; // round, speed level, lives
  static const int cue = 0x02; // step, block 0-7, lit ms u16
  static const int turn = 0x03; // round, time per press ms u16
  static const int press = 0x04; // step, block, correct
  static const int roundClear = 0x05; // round
  static const int mistake = 0x06; // step, pressed block (0xFF = too slow), right block, lives left
  static const int result = 0x07; // mode, score, best, flags (bit 0 new best, bit 1 won)
}

/// Subtypes of [BleEvent.pianoTiles] (integers little-endian), see raspberry-micro-python/README.md.
class BlePianoTiles {
  BlePianoTiles._();
  static const int runStart = 0x00; // mode, goal u16, row time ms u16
  static const int tile = 0x01; // tile u16, lane, time ms u32 since the start
  static const int speed = 0x02; // level, row time ms u16
  static const int timeLeft = 0x03; // seconds
  static const int mistake = 0x04; // reason (1 wrong pad, 2 missed tile), tile u16, x, y
  static const int result = 0x05; // mode, score u32, tiles u16, stars, flags (bit 0 new best, bit 1 finished)
}

/// Game states in [BleEvent.gameState] events, see pico_config.py GAME_STATE_*.
class BleGameState {
  BleGameState._();
  static const int ready = 0x01;
  static const int running = 0x02;
  static const int paused = 0x03;
  static const int over = 0x04;
  static const int win = 0x05;
}

/// Stream characteristic messages: chunked transfers, every write is answered with an "ACK" indication.
class BleStream {
  BleStream._();
  static const int init = 0x10; // [message type, total size u32 big-endian]
  static const int chunk = 0x11; // [data...]
  static const int pocketGuitarSong = 0x23; // song file JSON (UTF-8)
}

/// A board event with the time it arrived, see [BleService.recentGameEvents].
class BleReceivedEvent {
  const BleReceivedEvent(this.data, this.receivedAt);
  final List<int> data;
  final DateTime receivedAt;

  Duration get age => DateTime.now().difference(receivedAt);
}

/// A physical key press/release reported by the Pico, from [BleService.keyEventStream].
class BleKeyEvent {
  const BleKeyEvent({required this.gridKey, required this.pressed});
  final int gridKey;
  final bool pressed;
}

class BleService {
  // MicroPython Pico BLE Protocol Constants.
  // Must match raspberry-micro-python/pico_config.py (BLE_DEVICE_NAME, BLE_*_UUID) and the GATT
  // service registered in raspberry-micro-python/ble_handler/ble_handler.py.
  static const String deviceName = 'PhoneMidiBoard';
  static const String serviceUuid = '6e400000-b5a3-f393-e0a9-e50e24dcca9e';
  static const String eventCharUuid = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'; // board -> phone, notify
  static const String commandCharUuid = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'; // phone -> board, write without response
  static const String streamCharUuid = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'; // phone -> board, write + indicate ACK

  /// Largest stream write the board accepts (BLE_STREAM_MAX_WRITE in pico_config.py).
  static const int _maxStreamWrite = 244;
  static const Duration _streamAckTimeout = Duration(seconds: 5);

  static final BleService _instance = BleService._internal();
  factory BleService() => _instance;
  BleService._internal();

  BluetoothDevice? _connectedDevice;
  BluetoothCharacteristic? _commandCharacteristic;
  BluetoothCharacteristic? _eventCharacteristic;
  BluetoothCharacteristic? _streamCharacteristic;

  final _connectionStateController =
      StreamController<BleConnectionState>.broadcast();
  Stream<BleConnectionState> get connectionState =>
      _connectionStateController.stream;
  final ValueNotifier<BleConnectionState> stateNotifier = ValueNotifier(
    BleConnectionState.scanning,
  );

  BleConnectionState _currentState = BleConnectionState.scanning;
  BleConnectionState get currentState => _currentState;

  Timer? _reconnectTimer;
  bool _isReconnecting = false;
  bool _reconnectInFlight = false;
  bool _startupCheckInProgress = false;
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;
  static const Duration _reconnectDelay = Duration(seconds: 3);
  static const Duration _startupGracePeriod = Duration(seconds: 5);

  String? _lastDeviceId;
  StreamSubscription<BluetoothAdapterState>? _adapterStateSubscription;
  StreamSubscription<BluetoothConnectionState>? _deviceConnectionSubscription;

  final _streamAckController = StreamController<void>.broadcast();

  final _keyEventController = StreamController<BleKeyEvent>.broadcast();
  Stream<BleKeyEvent> get keyEventStream => _keyEventController.stream;

  final _scoreController = StreamController<int>.broadcast();
  Stream<int> get scoreStream => _scoreController.stream;

  /// Every event notification from the board, raw ([event id, payload...]), for game-specific parsing.
  /// Synchronous, so listeners see an event in the same turn it lands in [recentGameEvents].
  final _eventController = StreamController<List<int>>.broadcast(sync: true);
  Stream<List<int>> get eventStream => _eventController.stream;

  static const int _maxRecentGameEvents = 64;
  final List<(int, BleReceivedEvent)> _recentGameEvents = [];
  (int, BleReceivedEvent)? _lastGameSelected;
  (int, BleReceivedEvent)? _lastGameState;
  int _eventSequence = 0;

  /// The game events since the board last opened a game (key events left out), oldest first. That
  /// game selected event and the latest game state event are always included. A screen that opens
  /// after the board started a game replays these to catch up; read them and listen to
  /// [eventStream] in the same synchronous block, then no event is missed or seen twice.
  List<BleReceivedEvent> get recentGameEvents {
    final events = [
      ?_lastGameSelected,
      ?_lastGameState,
      ..._recentGameEvents,
    ];
    events.sort((a, b) => a.$1.compareTo(b.$1));
    final result = <BleReceivedEvent>[];
    int? previous;
    for (final (sequence, event) in events) {
      if (sequence != previous) result.add(event);
      previous = sequence;
    }
    return result;
  }

  bool get isConnected =>
      _currentState == BleConnectionState.connected && _commandCharacteristic != null;

  bool _disposed = false;

  Future<void> initialize() async {
    if (_disposed) return;

    if (await FlutterBluePlus.isSupported == false) {
      debugPrint("BLE not supported");
      _updateState(BleConnectionState.locked);
      return;
    }

    await _adapterStateSubscription?.cancel();
    _adapterStateSubscription = FlutterBluePlus.adapterState.listen((state) {
      if (_disposed) return;

      if (state != BluetoothAdapterState.on) {
        _cancelReconnection();
        _clearConnectedResources();
        _updateState(BleConnectionState.bluetoothDisabled);
        return;
      }

      if (_currentState == BleConnectionState.bluetoothDisabled) {
        _startStartupGraceCheck();
      }
    }, cancelOnError: false);

    _startStartupGraceCheck();
  }

  void _startStartupGraceCheck() {
    if (_startupCheckInProgress || _disposed) return;

    _startupCheckInProgress = true;
    unawaited(_runStartupGraceCheck());
  }

  Future<void> _runStartupGraceCheck() async {
    _updateState(BleConnectionState.scanning);

    try {
      final adapterState = await FlutterBluePlus.adapterState.first;
      if (adapterState != BluetoothAdapterState.on) {
        _updateState(BleConnectionState.bluetoothDisabled);
        return;
      }

      final devices = await scanForDevices(
        timeout: _startupGracePeriod,
        emitScanningState: false,
      );

      if (_disposed) return;

      if (devices.isEmpty) {
        _updateState(BleConnectionState.locked);
        return;
      }

      final connected = await connectToDevice(
        devices.first,
        failureState: BleConnectionState.locked,
      );

      if (!connected && !_disposed) {
        _updateState(BleConnectionState.locked);
      }
    } finally {
      _startupCheckInProgress = false;
    }
  }

  Future<List<BluetoothDevice>> scanForDevices({
    Duration timeout = const Duration(seconds: 4),
    bool emitScanningState = true,
  }) async {
    final devices = <BluetoothDevice>[];
    StreamSubscription<List<ScanResult>>? subscription;

    try {
      if (_disposed) return devices;

      if (await FlutterBluePlus.isSupported == false) {
        debugPrint("BLE not supported on this device");
        return devices;
      }

      final adapterState = await FlutterBluePlus.adapterState.first;
      if (adapterState != BluetoothAdapterState.on) {
        debugPrint("Bluetooth adapter is off");
        _updateState(BleConnectionState.bluetoothDisabled);
        return devices;
      }

      if (emitScanningState && _currentState != BleConnectionState.connected) {
        _updateState(BleConnectionState.scanning);
      }

      await FlutterBluePlus.startScan(timeout: timeout);

      subscription = FlutterBluePlus.scanResults.listen((results) {
        for (var result in results) {
          // Filter for PhoneMidiBoard device specifically
          if (!devices.contains(result.device) &&
              result.device.platformName == deviceName) {
            debugPrint("Found PhoneMidiBoard device: ${result.device.remoteId}");
            devices.add(result.device);
          }
        }
      }, cancelOnError: false);

      await Future.delayed(timeout);
    } catch (e) {
      debugPrint("BLE scan error: $e");
    } finally {
      await subscription?.cancel();
      try {
        await FlutterBluePlus.stopScan();
      } catch (e) {
        debugPrint("Stop scan cleanup error: $e");
      }
    }

    return devices;
  }

  Future<bool> connectToDevice(
    BluetoothDevice device, {
    BleConnectionState failureState = BleConnectionState.disconnected,
  }) async {
    if (_disposed) return false;

    _cancelReconnection();
    _updateState(BleConnectionState.connecting);
    _lastDeviceId = device.remoteId.toString();

    Future<bool> finalizeConnection() async {
      _connectedDevice = device;
      await _deviceConnectionSubscription?.cancel();
      _deviceConnectionSubscription = device.connectionState.listen((state) {
        if (state == BluetoothConnectionState.disconnected && !_disposed) {
          _handleDisconnection();
        }
      }, cancelOnError: true);
      await _discoverServices();
      _updateState(BleConnectionState.connected);
      _reconnectAttempts = 0;
      return true;
    }

    dynamic lastError;
    const int maxAttempts = 3;

    for (var attempt = 1; attempt <= maxAttempts && !_disposed; attempt++) {
      try {
        final currentState = await device.connectionState.first;
        if (currentState == BluetoothConnectionState.connected) {
          return await finalizeConnection();
        }

        await device.connect(
          license: License.nonprofit,
          timeout: const Duration(seconds: 15),
          autoConnect: false,
        );

        return await finalizeConnection();
      } catch (e) {
        lastError = e;
        debugPrint("Connection attempt $attempt/$maxAttempts failed: $e");

        _connectedDevice = null;
        _commandCharacteristic = null;
        _eventCharacteristic = null;
        _streamCharacteristic = null;

        try {
          await device.disconnect();
        } catch (disconnectError) {
          debugPrint(
            "Disconnect cleanup failed after connection error: $disconnectError",
          );
        }

        if (attempt < maxAttempts) {
          final delay = Duration(seconds: attempt * 2);
          await Future.delayed(delay);
        }
      }
    }

    debugPrint("Connection failed after $maxAttempts attempts: $lastError");
    _clearConnectedResources();
    _updateState(failureState);
    return false;
  }

  Future<void> _discoverServices() async {
    // Only ever touch the three named game characteristics below by exact UUID
    // match. The board also exposes a standard BLE MIDI service/characteristic
    // (see RaspberryMicroPython/pico_config.py BLE_MIDI_*) that a MIDI host can
    // subscribe to; if this app ever subscribed to it too, the board's mode
    // detection (BLEHandler._check_subscriptions) would latch it into MIDI mode
    // instead of game mode. Never add a generic "subscribe to every
    // characteristic" loop here.
    if (_connectedDevice == null || _disposed) return;

    try {
      final services = await _connectedDevice!.discoverServices();

      // Look for the board's service UUID
      BluetoothService? boardService;
      try {
        boardService = services.firstWhere(
          (s) => s.uuid.toString().toLowerCase() == serviceUuid,
        );
      } catch (e) {
        debugPrint("PhoneMidiBoard service not found, falling back to any service");
      }

      final servicesToCheck = boardService != null ? [boardService] : services;
      final device = _connectedDevice!;

      for (var service in servicesToCheck) {
        for (var characteristic in service.characteristics) {
          final charUuid = characteristic.uuid.toString().toLowerCase();

          if (charUuid == commandCharUuid) {
            _commandCharacteristic = characteristic;
            debugPrint("Found command characteristic: $charUuid");
          } else if (charUuid == eventCharUuid) {
            _eventCharacteristic = characteristic;
            debugPrint("Found event characteristic: $charUuid");
            try {
              // onValueReceived, not lastValueStream: that one also replays the cached value
              final subscription = characteristic.onValueReceived.listen(
                _handleIncomingData,
                onError: (error) => debugPrint("Event stream error: $error"),
                cancelOnError: false,
              );
              device.cancelWhenDisconnected(subscription);
              await characteristic.setNotifyValue(true);
            } catch (e) {
              debugPrint("BLE event notify setup failed: $e");
            }
          } else if (charUuid == streamCharUuid) {
            _streamCharacteristic = characteristic;
            debugPrint("Found stream characteristic: $charUuid");
            try {
              final subscription = characteristic.onValueReceived.listen(
                (_) => _streamAckController.add(null),
                onError: (error) => debugPrint("Stream ACK error: $error"),
                cancelOnError: false,
              );
              device.cancelWhenDisconnected(subscription);
              await characteristic.setNotifyValue(true);
            } catch (e) {
              debugPrint("BLE stream indicate setup failed: $e");
            }
          }
        }
      }

      if (_commandCharacteristic != null && _eventCharacteristic != null && _streamCharacteristic != null) {
        debugPrint("PhoneMidiBoard characteristics configured successfully (MTU ${device.mtuNow})");
      } else {
        debugPrint("Warning: Not all characteristics found (command: ${_commandCharacteristic != null}, "
            "event: ${_eventCharacteristic != null}, stream: ${_streamCharacteristic != null})");
      }
    } catch (e) {
      debugPrint("Service discovery error: $e");
    }
  }

  /// Handles [data] as if the board had sent it.
  @visibleForTesting
  void debugReceive(List<int> data) => _handleIncomingData(data);

  void _handleIncomingData(List<int> data) {
    if (data.isEmpty) return;

    try {
      _remember(data);
      _eventController.add(data);
      switch (data[0]) {
        case BleEvent.key:
          if (data.length < 3) break;
          final pressed = data[1] == 0;
          final gridKey = data[2];
          _keyEventController.add(BleKeyEvent(gridKey: gridKey, pressed: pressed));
          break;

        case BleEvent.game:
          if (data.length >= 4 && data[1] == BleEvent.gameScore) {
            _scoreController.add(data[2] | (data[3] << 8));
          }
          break;

        case BleEvent.error:
          debugPrint("BLE: board error ${data.length > 1 ? data[1] : -1}, value ${data.length > 2 ? data[2] : -1}");
          break;
      }
    } catch (e) {
      debugPrint("Error handling incoming BLE data: $e");
    }
  }

  void _remember(List<int> data) {
    if (data[0] == BleEvent.key) return;
    final entry = (_eventSequence++, BleReceivedEvent(List.unmodifiable(data), DateTime.now()));
    if (data[0] == BleEvent.game && data.length >= 3) {
      if (data[1] == BleEvent.gameSelected) {
        _recentGameEvents.clear();
        _lastGameState = null;
        _lastGameSelected = entry;
        return;
      }
      if (data[1] == BleEvent.gameState) _lastGameState = entry;
    }
    _recentGameEvents.add(entry);
    if (_recentGameEvents.length > _maxRecentGameEvents) _recentGameEvents.removeAt(0);
  }

  /// Starts the open game (Pocket Guitar: the selected song).
  Future<bool> startGame() => sendCommand([BleCommand.gameControl, BleCommand.start]);

  /// Quits the game, the board goes back to its start screen.
  Future<bool> stopGame() => sendCommand([BleCommand.gameControl, BleCommand.stop]);

  /// Quits the current run, back to the game's ready screen.
  Future<bool> resetGame() => sendCommand([BleCommand.gameControl, BleCommand.reset]);

  Future<bool> pauseGame() => sendCommand([BleCommand.gameControl, BleCommand.pause]);

  Future<bool> resumeGame() => sendCommand([BleCommand.gameControl, BleCommand.resume]);

  /// Asks for a battery report ([BleEvent.batteryReport]), which also says which game is open and its state.
  Future<bool> requestTelemetry() => sendCommand([BleCommand.gameControl, BleCommand.getTelemetry]);

  /// Opens a game on the board ([BleGameId]), optionally with a variant (e.g. Pocket Guitar difficulty).
  Future<bool> selectGame(int gameId, [int? variant]) => sendCommand(
      [BleCommand.gameControl, BleCommand.select, gameId, ?variant]);

  /// Sends a command on the command characteristic (no answer; errors come back as error events).
  Future<bool> sendCommand(List<int> data) async {
    final characteristic = _commandCharacteristic;
    if (characteristic == null || _currentState != BleConnectionState.connected) {
      return false;
    }
    try {
      await characteristic.write(data, withoutResponse: true);
      return true;
    } catch (e) {
      debugPrint("Command send error: $e");
      return false;
    }
  }

  /// Sends a large payload on the stream characteristic: INIT with the message type and size, then
  /// chunks as large as the MTU allows, each after the board's ACK for the previous write.
  Future<bool> sendStream(
    int messageType,
    List<int> payload, {
    void Function(double progress)? onProgress,
  }) async {
    final characteristic = _streamCharacteristic;
    final device = _connectedDevice;
    if (characteristic == null || device == null || _currentState != BleConnectionState.connected) {
      return false;
    }
    final chunkSize = (device.mtuNow - 3 - 1).clamp(19, _maxStreamWrite - 1);
    final size = payload.length;

    Future<void> writeAndWaitForAck(List<int> packet) async {
      // Listen before writing: the ACK can arrive before write() returns
      final ack = _streamAckController.stream.first.timeout(_streamAckTimeout);
      try {
        await characteristic.write(packet, withoutResponse: false);
      } catch (_) {
        ack.ignore();
        rethrow;
      }
      await ack;
    }

    try {
      await writeAndWaitForAck([
        BleStream.init,
        messageType,
        (size >> 24) & 0xFF,
        (size >> 16) & 0xFF,
        (size >> 8) & 0xFF,
        size & 0xFF,
      ]);
      for (var offset = 0; offset < size; offset += chunkSize) {
        final end = offset + chunkSize < size ? offset + chunkSize : size;
        await writeAndWaitForAck([BleStream.chunk, ...payload.sublist(offset, end)]);
        onProgress?.call(end / size);
      }
      return true;
    } catch (e) {
      debugPrint("Stream send error (message 0x${messageType.toRadixString(16)}, chunk $chunkSize): $e");
      return false;
    }
  }

  void _handleDisconnection() {
    if (_disposed) return;

    _clearConnectedResources();
    _updateState(BleConnectionState.locked);

    if (!_isReconnecting &&
        _lastDeviceId != null &&
        _reconnectAttempts < _maxReconnectAttempts) {
      _startReconnection();
    }
  }

  void _startReconnection() {
    if (_disposed) return;

    _isReconnecting = true;
    _reconnectTimer?.cancel();

    _reconnectTimer = Timer.periodic(_reconnectDelay, (timer) async {
      if (_disposed || _reconnectAttempts >= _maxReconnectAttempts) {
        timer.cancel();
        _isReconnecting = false;
        _reconnectInFlight = false;
        return;
      }

      if (_reconnectInFlight) return;

      _reconnectInFlight = true;

      _reconnectAttempts++;
      debugPrint(
        "Reconnect attempt $_reconnectAttempts/$_maxReconnectAttempts",
      );

      try {
        final devices = await scanForDevices(
          timeout: const Duration(seconds: 2),
          emitScanningState: false,
        );
        if (devices.isEmpty) return;

        BluetoothDevice? targetDevice;
        try {
          targetDevice = devices.firstWhere(
            (d) => d.remoteId.toString() == _lastDeviceId,
          );
        } catch (_) {
          if (devices.isNotEmpty) {
            targetDevice = devices.first;
          }
        }

        if (targetDevice != null && !_disposed) {
          final success = await connectToDevice(
            targetDevice,
            failureState: BleConnectionState.locked,
          );
          if (success) {
            timer.cancel();
            _isReconnecting = false;
          }
        }
      } catch (e) {
        debugPrint("Reconnection error: $e");
      } finally {
        _reconnectInFlight = false;
      }
    });
  }

  Future<void> disconnect() async {
    _cancelReconnection();
    _reconnectAttempts = 0;
    _lastDeviceId = null;

    if (_connectedDevice != null) {
      await _connectedDevice!.disconnect();
    }

    _clearConnectedResources();

    _updateState(BleConnectionState.disconnected);
  }

  void _updateState(BleConnectionState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      stateNotifier.value = newState;
      if (!_connectionStateController.isClosed) {
        _connectionStateController.add(newState);
      }
    }
  }

  void _clearConnectedResources() {
    _connectedDevice = null;
    _commandCharacteristic = null;
    _eventCharacteristic = null;
    _streamCharacteristic = null;
    unawaited(_deviceConnectionSubscription?.cancel());
    _deviceConnectionSubscription = null;
  }

  void _cancelReconnection() {
    _reconnectTimer?.cancel();
    _isReconnecting = false;
    _reconnectInFlight = false;
  }

  void dispose() {
    _disposed = true;
    _cancelReconnection();
    unawaited(_adapterStateSubscription?.cancel());
    _adapterStateSubscription = null;
    unawaited(_deviceConnectionSubscription?.cancel());
    _deviceConnectionSubscription = null;
    disconnect();
    _connectionStateController.close();
    _streamAckController.close();
    _keyEventController.close();
    _scoreController.close();
    _eventController.close();
    stateNotifier.dispose();
  }
}

enum BleConnectionState {
  scanning,
  connecting,
  connected,
  locked,
  disconnected,
  bluetoothDisabled,
}
