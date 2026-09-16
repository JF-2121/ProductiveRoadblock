import 'dart:convert';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:productive_roadblock/models/board_games.dart';
import 'package:productive_roadblock/services/ble_service.dart';
import 'package:productive_roadblock/services/pocket_guitar_session.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

List<int> _i32(int v) => [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF];

/// SONG_START: slot, difficulty, mode, bpm*10 u16, start position ms i32, delay offset ms i16
List<int> songStart(int startMs, {int slot = 0xFF, int mode = 0}) =>
    [BleEvent.songStart, slot, 0, mode, 0xC7, 0x04, ..._i32(startMs), 0, 0];

/// SONG_SELECTION: slot, song count, difficulty, available, mode, best stars, best score u32
List<int> selection({int slot = 0xFF}) => [BleEvent.songSelection, slot, 2, 1, 0x0F, 0, 0, 0, 0, 0, 0];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakeBoard board;
  late FakePlayer player;
  late PocketGuitarSession session;

  setUp(() async {
    SharedPreferences.setMockInitialValues({'pocket_guitar_delay_offset_ms': 40});
    board = FakeBoard();
    player = FakePlayer();
    session = PocketGuitarSession(ble: board, player: player, random: Random(1));
    await session.start();
  });

  test('sends a bundled song to the board and is ready on its selection event', () async {
    expect(board.streams, hasLength(1));
    final (type, payload) = board.streams.single;
    expect(type, BleStream.pocketGuitarSong);
    final chart = jsonDecode(utf8.decode(payload)) as Map<String, dynamic>;
    expect(chart['id'], session.song!.id);
    // Every bundled song has at least Easy; some auto-generated charts (see catalog.json's
    // "chart_generated" note) are Easy-only, so the other difficulties aren't guaranteed.
    expect((chart['charts'] as Map).keys, contains('easy'));
    expect(player.calls, contains('source pocket_guitar/audio/${session.song!.id}.m4a'));
    // delay offset 40 ms, i16 little-endian
    expect(board.commands, contains(equals([BleCommand.pocketGuitar, BleCommand.setDelayOffset, 40, 0])));
    expect(session.phase, PocketGuitarPhase.uploading);

    board.events.add(selection());
    expect(session.phase, PocketGuitarPhase.ready);
    expect(session.availableDifficulties, 0x0F);
    expect(session.difficulty, 1);
  });

  // Real time with short count-ins (the session loads assets with real I/O, so no fake clock)
  Future<void> wait(int ms) => Future<void>.delayed(Duration(milliseconds: ms));

  test('music starts when the count-in ends, pause and resume follow the board', () async {
    board.events.add(selection());
    player.calls.clear();

    board.events.add(songStart(-500));
    await pumpEventQueue();
    expect(session.phase, PocketGuitarPhase.countIn);
    expect(player.calls, ['pause', 'volume 1.0', 'seek 0']);

    await wait(350);
    expect(player.calls, isNot(contains('resume')));
    await wait(300);
    expect(player.calls.last, 'resume');
    expect(session.phase, PocketGuitarPhase.playing);

    board.events.add([BleEvent.game, BleEvent.gameState, BleGameState.paused]);
    await pumpEventQueue();
    expect(session.phase, PocketGuitarPhase.paused);
    expect(player.calls.last, 'pause');

    // Resume: the board counts in inside the song, the music is scheduled 250 ms ahead
    player.calls.clear();
    board.events.add(songStart(10000));
    await pumpEventQueue();
    expect(player.calls, ['pause', 'volume 1.0', 'seek 10250']);
    await wait(150);
    expect(player.calls, isNot(contains('resume')));
    await wait(250);
    expect(player.calls.last, 'resume');

    // A miss dips the music for a moment
    board.events.add([BleEvent.noteResult, 3, 0, 4, 1, ..._i32(500)]);
    await pumpEventQueue();
    expect(session.score, 500);
    expect(player.calls.last, 'volume 0.4');
    await wait(400);
    expect(player.calls.last, 'volume 1.0');

    // Result: score u32, stars, accuracy, best streak u16, flags (new best)
    board.events.add([BleEvent.songResult, ..._i32(12345), 4, 87, 31, 0, 1]);
    expect(session.phase, PocketGuitarPhase.result);
    expect(session.result!.stars, 4);
    expect(session.result!.accuracy, 87);
    expect(session.result!.bestStreak, 31);
    expect(session.result!.newBest, isTrue);
    expect(session.result!.flawless, isFalse);
  });

  test('practice plays no music and quitting stops the music', () async {
    board.events.add(selection());
    player.calls.clear();
    board.events.add(songStart(-200, mode: PocketGuitarSession.modePractice));
    await wait(400);
    expect(player.calls, isNot(contains('resume')));

    board.events.add(songStart(-200));
    await wait(400);
    expect(player.calls.last, 'resume');
    board.events.add([BleEvent.game, BleEvent.gameState, BleGameState.over]);
    await pumpEventQueue();
    expect(player.calls.last, 'stop');
    expect(session.phase, PocketGuitarPhase.ready);
  });

  test('a rejected upload shows an error, a board song has no music', () {
    board.events.add([BleEvent.error, 0x05, BleStream.pocketGuitarSong]);
    expect(session.phase, PocketGuitarPhase.error);

    board.events.add(selection(slot: 1));
    expect(session.song, isNull);
    board.events.add(songStart(-1962, slot: 1));
    expect(player.calls, isNot(contains('resume')));
  });

  test('opened for a song started on the board: follows it without sending a song', () async {
    final boardBoard = FakeBoard()
      ..recent = [
        received(gameSelected(BleGameId.pocketGuitar, 1), const Duration(milliseconds: 400)),
        received(selection(slot: 0), const Duration(milliseconds: 380)),
        received(gameState(BleGameState.running), const Duration(milliseconds: 360)),
        received(songStart(-2000, slot: 0), const Duration(milliseconds: 350)),
      ];
    final boardPlayer = FakePlayer();
    final follower = PocketGuitarSession(ble: boardBoard, player: boardPlayer, random: Random(1));
    await follower.start(launch: GameLaunch.board);

    expect(boardBoard.streams, isEmpty);
    expect(boardBoard.commands, [
      [BleCommand.pocketGuitar, BleCommand.getSelection],
    ]);
    expect(follower.song, isNull);
    expect(follower.phase, PocketGuitarPhase.countIn);
    expect(follower.canChangeSong, isFalse);

    boardBoard.send([BleEvent.noteResult, 0, 0, 1, 2, ..._i32(250)]);
    expect(follower.phase, PocketGuitarPhase.playing);
    expect(follower.score, 250);

    // Result, then the board goes back to its start screen: the result stays
    boardBoard.send([BleEvent.songResult, ..._i32(900), 3, 70, 12, 0, 0]);
    boardBoard.send(gameSelected(BleGameId.startScreen, 0xFF));
    expect(follower.phase, PocketGuitarPhase.closed);
    expect(follower.result!.score, 900);
    expect(boardPlayer.calls, isNot(contains('resume')));

    // Pocket Guitar isn't open any more: closing the screen sends nothing
    follower.dispose();
    expect(boardBoard.commands.last, [BleCommand.pocketGuitar, BleCommand.getSelection]);
  });

  test('closing the screen closes Pocket Guitar on the board', () {
    session.dispose();
    expect(board.commands.last, [BleCommand.gameControl, BleCommand.stop]);
  });
}
