import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:productive_roadblock/services/ble_service.dart';

/// The board: events are sent synchronously, commands and streams are recorded.
class FakeBoard extends Fake implements BleService {
  final events = StreamController<List<int>>.broadcast(sync: true);
  final connection = StreamController<BleConnectionState>.broadcast(sync: true);
  final commands = <List<int>>[];
  final streams = <(int, List<int>)>[];

  /// What [recentGameEvents] returns.
  List<BleReceivedEvent> recent = [];
  bool connected = true;

  void send(List<int> event) => events.add(event);

  @override
  Stream<List<int>> get eventStream => events.stream;

  @override
  Stream<BleConnectionState> get connectionState => connection.stream;

  @override
  bool get isConnected => connected;

  @override
  List<BleReceivedEvent> get recentGameEvents => recent;

  @override
  Future<bool> sendStream(int messageType, List<int> payload, {void Function(double progress)? onProgress}) async {
    streams.add((messageType, payload));
    onProgress?.call(1);
    return true;
  }

  @override
  Future<bool> sendCommand(List<int> data) async {
    commands.add(data);
    return true;
  }

  @override
  Future<bool> startGame() => sendCommand([BleCommand.gameControl, BleCommand.start]);

  @override
  Future<bool> stopGame() => sendCommand([BleCommand.gameControl, BleCommand.stop]);

  @override
  Future<bool> pauseGame() => sendCommand([BleCommand.gameControl, BleCommand.pause]);

  @override
  Future<bool> resumeGame() => sendCommand([BleCommand.gameControl, BleCommand.resume]);

  @override
  Future<bool> resetGame() => sendCommand([BleCommand.gameControl, BleCommand.reset]);

  @override
  Future<bool> selectGame(int gameId, [int? variant]) =>
      sendCommand([BleCommand.gameControl, BleCommand.select, gameId, ?variant]);

  @override
  Future<bool> requestTelemetry() => sendCommand([BleCommand.gameControl, BleCommand.getTelemetry]);
}

/// Records the calls; [position] is what getCurrentPosition answers.
class FakePlayer extends Fake implements AudioPlayer {
  final calls = <String>[];
  Duration? position;

  @override
  Future<void> setReleaseMode(ReleaseMode releaseMode) async => calls.add('releaseMode');
  @override
  Future<void> setSource(Source source) async => calls.add('source ${(source as AssetSource).path}');
  @override
  Future<void> pause() async => calls.add('pause');
  @override
  Future<void> seek(Duration position) async => calls.add('seek ${position.inMilliseconds}');
  @override
  Future<void> resume() async => calls.add('resume');
  @override
  Future<void> stop() async => calls.add('stop');
  @override
  Future<void> setVolume(double volume) async => calls.add('volume $volume');
  @override
  Future<void> setPlaybackRate(double playbackRate) async => calls.add('rate ${playbackRate.toStringAsFixed(2)}');
  @override
  Future<Duration?> getCurrentPosition() async => position;
  @override
  Future<void> dispose() async => calls.add('dispose');
}

List<int> u16(int v) => [v & 0xFF, (v >> 8) & 0xFF];

List<int> u32(int v) => [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF];

List<int> gameSelected(int gameId, [int variant = 0xFF]) => [BleEvent.game, BleEvent.gameSelected, gameId, variant];

List<int> gameState(int state) => [BleEvent.game, BleEvent.gameState, state];

BleReceivedEvent received(List<int> data, [Duration age = Duration.zero]) =>
    BleReceivedEvent(data, DateTime.now().subtract(age));
