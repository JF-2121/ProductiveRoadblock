import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:productive_roadblock/models/board_games.dart';
import 'package:productive_roadblock/services/ble_service.dart';
import 'package:productive_roadblock/state/play_time.dart';
import 'package:productive_roadblock/state/session_manager.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('PlayClock', () {
    var now = 0;
    late PlayClock clock;

    setUp(() {
      now = 0;
      clock = PlayClock(nowMs: () => now)..start(const Duration(seconds: 3));
    });

    test('counts running time while there is activity', () {
      for (var t = 1000; t <= 10000; t += 1000) {
        now = t;
        clock.activity();
      }
      expect(clock.stop(), const Duration(seconds: 10));
    });

    test('pauses and idle time earn nothing', () {
      now = 2000;
      clock.pause();
      now = 30000;
      clock.resume();
      now = 31000;
      clock.activity();
      // no activity for 20 s: only the idle limit (3 s) counts
      now = 51000;
      expect(clock.stop(), const Duration(seconds: 2 + 1 + 3));
    });
  });

  group('PlayTimeTracker', () {
    late FakeBoard board;
    late ProviderContainer container;
    var now = 0;

    PlayTimeTracker tracker() => container.read(playTimeProvider.notifier);
    PlayTimeState play() => container.read(playTimeProvider);
    SessionState session() => container.read(sessionManagerProvider);

    List<int> cue() => [BleEvent.simonSays, BleSimonSays.cue, 0, 3, ...u16(520)];

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      now = 0;
      board = FakeBoard();
      container = ProviderContainer(overrides: [
        playTimeProvider.overrideWith(() => PlayTimeTracker(ble: board, nowMs: () => now)),
      ]);
      container.read(sessionManagerProvider);
      tracker();
      await pumpEventQueue();
    });

    tearDown(() => container.dispose());

    test('a board run earns played time × multiplier and unlocks', () async {
      await container.read(sessionManagerProvider.notifier).setPlayTimeMultiplier(2);
      board.send(gameSelected(BleGameId.simonSays, 0));
      board.send(gameState(BleGameState.running));
      expect(play().running, isTrue);
      for (var t = 1000; t <= 20000; t += 1000) {
        now = t;
        board.send(cue());
      }
      board.send(gameState(BleGameState.win));

      expect(play().running, isFalse);
      final run = play().lastRun!;
      expect(run.gameId, BleGameId.simonSays);
      expect(run.played, const Duration(seconds: 20));
      expect(run.multiplier, 2);
      expect(run.earned, const Duration(seconds: 40));
      expect(session().isUnlocked, isTrue);
      expect(session().remainingTime, const Duration(seconds: 40));

      // While unlocked, the next run adds to the time left
      board.send(gameState(BleGameState.running));
      now = 25000;
      board.send(cue());
      board.send(gameState(BleGameState.over));
      expect(play().lastRun!.earned, const Duration(seconds: 10));
      expect(session().remainingTime, const Duration(seconds: 50));
    });

    test('pauses do not count, and a stalled run stops counting', () {
      board.send(gameSelected(BleGameId.pianoTiles, 0));
      board.send(gameState(BleGameState.running));
      List<int> tile(int index) => [BleEvent.pianoTiles, BlePianoTiles.tile, ...u16(index), 0, ...u32(now)];
      for (var t = 0; t <= 5000; t += 500) {
        now = t;
        board.send(tile(t ~/ 500));
      }
      board.send(gameState(BleGameState.paused));
      now = 60000;
      board.send(gameState(BleGameState.running));
      // Zen's time ticks are no activity: 20 s without a tile only count 3 s
      for (var t = 61000; t <= 80000; t += 1000) {
        now = t;
        board.send([BleEvent.pianoTiles, BlePianoTiles.timeLeft, 10]);
      }
      board.send(gameState(BleGameState.win));
      expect(play().lastRun!.played, const Duration(seconds: 5 + 3));
    });

    test('pad and key presses keep a run counting (Pocket Guitar practice hits send no note events)', () {
      board.send(gameSelected(BleGameId.pocketGuitar, 0));
      board.send(gameState(BleGameState.running));
      for (var t = 2000; t <= 40000; t += 2000) {
        now = t;
        board.send([BleEvent.key, 0, 33]); // strum press
        board.send([BleEvent.key, 1, 33]);
      }
      now = 100000;
      board.send(gameState(BleGameState.over));
      expect(play().lastRun!.played, const Duration(seconds: 40 + 15));
    });

    test('asks the app to show a game the board opened or started without a screen', () async {
      final requested = <int>[];
      final subscription = tracker().boardStartedGames.listen(requested.add);

      tracker().attachScreen(BleGameId.pianoTiles);
      board.send(gameSelected(BleGameId.pianoTiles, 1)); // opened by the app's own screen
      board.send(gameSelected(BleGameId.simonSays, 0)); // opened on the board
      board.send(gameSelected(BleGameId.startScreen));
      await pumpEventQueue();
      expect(requested, [BleGameId.simonSays]);

      // On connect the app asks what runs on the board: a running Pocket Guitar song
      board.connection.add(BleConnectionState.connected);
      expect(board.commands.last, [BleCommand.gameControl, BleCommand.getTelemetry]);
      board.send([BleEvent.batteryReport, ...u16(3900), ...u16(120), BleGameId.pocketGuitar, BleGameState.running, 255]);
      await pumpEventQueue();
      expect(requested, [BleGameId.simonSays, BleGameId.pocketGuitar]);
      expect(play().runGameId, BleGameId.pocketGuitar);

      // A disconnect ends the run
      now = 4000;
      board.send([BleEvent.overstrum, ...u32(0)]);
      board.connection.add(BleConnectionState.locked);
      expect(play().running, isFalse);
      expect(play().lastRun!.played, const Duration(seconds: 4));
      expect(play().boardGameId, isNull);
      await subscription.cancel();
    });

    test('the phone game counts taps and ends with endPhoneRun', () async {
      final closed = <void>[];
      final subscription = tracker().gameScreensClosed.listen(closed.add);
      tracker().attachScreen(phoneGameScreenId);
      for (var t = 0; t <= 9000; t += 1000) {
        now = t;
        tracker().phoneActivity();
      }
      now = 30000;
      final run = tracker().endPhoneRun()!;
      expect(run.played, const Duration(seconds: 11)); // last tap at 9 s + 2 s idle limit
      expect(session().remainingTime, const Duration(seconds: 11));
      expect(tracker().endPhoneRun(), isNull);

      expect(tracker().hasGameScreen, isTrue);
      tracker().detachScreen(phoneGameScreenId);
      expect(tracker().hasGameScreen, isFalse);
      await pumpEventQueue();
      expect(closed, hasLength(1));
      await subscription.cancel();
    });
  });

  test('BleService keeps the game events since the board opened a game', () {
    final ble = BleService();
    ble.debugReceive(gameSelected(BleGameId.pianoTiles, 0));
    for (var i = 0; i < 80; i++) {
      ble.debugReceive([BleEvent.key, 0, 5]);
    }
    ble.debugReceive(gameState(BleGameState.running));
    for (var i = 0; i < 70; i++) {
      ble.debugReceive([BleEvent.pianoTiles, BlePianoTiles.tile, ...u16(i), 0, ...u32(i * 250)]);
    }
    final events = ble.recentGameEvents.map((e) => e.data).toList();
    // The game selected and latest state event stay, then the newest 64 events; key events are left out
    expect(events.first, gameSelected(BleGameId.pianoTiles, 0));
    expect(events[1], gameState(BleGameState.running));
    expect(events, hasLength(2 + 64));
    expect(events.last.sublist(2, 4), u16(69));

    ble.debugReceive(gameSelected(BleGameId.simonSays, 1));
    expect(ble.recentGameEvents.map((e) => e.data).toList(), [gameSelected(BleGameId.simonSays, 1)]);
  });
}
