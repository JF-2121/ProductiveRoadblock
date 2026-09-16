import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_test/flutter_test.dart';
import 'package:productive_roadblock/models/board_games.dart';
import 'package:productive_roadblock/models/piano_tiles_track.dart';
import 'package:productive_roadblock/services/ble_service.dart';
import 'package:productive_roadblock/services/piano_tiles_session.dart';
import 'package:productive_roadblock/services/tap_follow_player.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

/// 20 tiles of 500 ms, the last one ends at 10 s, 2 s fade-out.
PianoTilesTrack track(String id) => PianoTilesTrack(
      id: id,
      title: id,
      composer: 'Composer',
      performer: 'Performer',
      audioAsset: 'assets/piano_tiles/audio/$id.m4a',
      chartAsset: 'assets/piano_tiles/charts/$id.json',
      lengthMs: 12000,
    ).withChart([for (var i = 0; i < 20; i++) i * 500], 10000);

List<int> piano(int subtype, List<int> payload) => [BleEvent.pianoTiles, subtype, ...payload];

List<int> tileEvent(int index, int timeMs) => piano(BlePianoTiles.tile, [...u16(index), 2, ...u32(timeMs)]);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('bundled songs: every catalog entry has its audio and a playable chart', () async {
    final catalog = await loadPianoTilesCatalog();
    expect(catalog.map((s) => s.id), ['eine_kleine_nachtmusik', 'canon_in_d', 'rondo_alla_turca']);
    for (final entry in catalog) {
      final song = await entry.loadChart();
      expect((await rootBundle.load(song.audioAsset)).lengthInBytes, greaterThan(500000), reason: song.id);
      // Enough tiles for a Zen or Arcade run, rising, each a playable length, the last one before the fade-out
      expect(song.tileMs.length, greaterThan(150), reason: song.id);
      final bounds = [...song.tileMs, song.endMs];
      for (var i = 1; i < bounds.length; i++) {
        expect(bounds[i] - bounds[i - 1], inInclusiveRange(150, 600), reason: '${song.id} tile ${i - 1}');
      }
      expect(song.endMs, lessThan(song.lengthMs), reason: song.id);
    }
  });

  group('TapFollowPlayer', () {
    late FakePlayer player;
    late TapFollowPlayer music;
    var now = 0;

    Future<void> fadeOut() => Future<void>.delayed(const Duration(milliseconds: 120));

    setUp(() async {
      now = 0;
      player = FakePlayer();
      music = TapFollowPlayer(player: player, nowMs: () => now, autoTick: false);
      await music.load(track('song'));
      expect(player.calls, ['releaseMode', 'source piano_tiles/audio/song.m4a']);
      player.calls.clear();
    });

    test('a tap plays its tile, the music stops just after it', () async {
      music.tile(0);
      await pumpEventQueue();
      expect(player.calls, ['volume 1.0', 'seek 0', 'resume']);
      expect(music.allowedUntilMs, 500);

      now = 600;
      music.tick();
      expect(music.isPlaying, isTrue);
      now = 700; // past the tile + 150 ms grace
      music.tick();
      await fadeOut();
      expect(player.calls.sublist(3), ['volume 0.6', 'volume 0.3', 'pause']);
      expect(music.isPlaying, isFalse);

      // The next tap starts its tile again, a bit slower
      player.calls.clear();
      now = 900;
      music.tile(1);
      await pumpEventQueue();
      expect(player.calls, ['rate 0.81', 'volume 1.0', 'seek 500', 'resume']);
    });

    test('the music follows faster steady taps without stopping', () async {
      music.tile(0);
      await pumpEventQueue();
      for (var t = 30; t <= 12 * 330; t += 30) {
        now = t;
        if (t % 330 == 0) music.tile(t ~/ 330);
        music.tick();
      }
      expect(player.calls, isNot(contains('pause')));
      expect(music.rate, greaterThan(1.35));
      expect(music.rate, lessThan(1.7));
    });

    test('jumps to a tile far ahead and to the start when the song starts over', () async {
      music.tile(0);
      await pumpEventQueue();
      now = 100;
      music.tile(10);
      expect(player.calls.last, 'seek 5000');
      expect(music.allowedUntilMs, 5500);

      now = 200;
      music.tile(19);
      now = 300;
      music.tile(20); // wraps to tile 0
      expect(player.calls.last, 'seek 0');
      expect(music.allowedUntilMs, 500);
    });

    test('stop fades out and resets the speed', () async {
      music.tile(0);
      await pumpEventQueue();
      for (var t = 250; t <= 1500; t += 250) {
        now = t;
        music.tile(t ~/ 250);
      }
      expect(music.rate, greaterThan(1.2));
      music.stop();
      await fadeOut();
      expect(player.calls, containsAllInOrder(['volume 0.6', 'rate 1.00', 'volume 0.3', 'pause']));
      expect(music.rate, 1.0);
    });
  });

  group('PianoTilesSession', () {
    late FakeBoard board;
    late FakePlayer player;
    late List<String> sounds;
    late PianoTilesSession session;

    setUp(() {
      SharedPreferences.setMockInitialValues({'piano_tiles_song': 'second'});
      board = FakeBoard();
      player = FakePlayer();
      sounds = [];
      session = PianoTilesSession(
        ble: board,
        music: TapFollowPlayer(player: player, autoTick: false),
        playSound: sounds.add,
        loadCatalog: () async => [track('first'), track('second')],
      );
    });

    test('opened from the app: last song, selects the mode, taps play the music, a mistake buzzes', () async {
      await session.start(GameLaunch.app);
      expect(session.song!.id, 'second');
      expect(player.calls, contains('source piano_tiles/audio/second.m4a'));
      expect(board.commands, [
        [BleCommand.gameControl, BleCommand.select, BleGameId.pianoTiles, PianoTilesSession.modeClassic],
      ]);
      board.send(gameSelected(BleGameId.pianoTiles, 0));
      expect(session.phase, PianoTilesPhase.ready);

      board.send(gameState(BleGameState.running));
      board.send(piano(BlePianoTiles.runStart, [0, ...u16(50), ...u16(0)]));
      expect(session.phase, PianoTilesPhase.playing);
      expect(session.goal, 50);
      expect(session.canChange, isFalse);

      player.calls.clear();
      board.send(tileEvent(0, 0));
      await pumpEventQueue();
      expect(player.calls, ['volume 1.0', 'seek 0', 'resume']);
      board.send(tileEvent(1, 420));
      expect(session.tiles, 2);
      expect(session.elapsedMs, 420);

      board.send(piano(BlePianoTiles.mistake, [1, ...u16(2), 3, 7]));
      expect(sounds, ['buzz']);
      expect(session.phase, PianoTilesPhase.gameOver);
      expect(player.calls, containsAllInOrder(['volume 0.6', 'rate 1.00'])); // fades out, back to normal speed

      board.send(gameState(BleGameState.over));
      board.send(piano(BlePianoTiles.result, [0, ...u32(0), ...u16(2), 0, 0]));
      expect(session.phase, PianoTilesPhase.result);
      expect(session.result!.finished, isFalse);
      expect(session.result!.tiles, 2);
      expect(session.canChange, isTrue);

      await session.selectMode(PianoTilesSession.modeArcade);
      expect(board.commands.last, [BleCommand.gameControl, BleCommand.select, BleGameId.pianoTiles, 2]);
      await session.newTiles();
      expect(board.commands.last, [BleCommand.gameControl, BleCommand.start]);

      await session.selectSong(session.catalog.first);
      expect((await SharedPreferences.getInstance()).getString('piano_tiles_song'), 'first');
      expect(player.calls.last, 'source piano_tiles/audio/first.m4a');
    });

    test('opened for a run started on the board: catches up, then the taps play the music', () async {
      board.recent = [
        received(gameSelected(BleGameId.pianoTiles, PianoTilesSession.modeZen)),
        received(gameState(BleGameState.running)),
        received(piano(BlePianoTiles.runStart, [1, ...u16(30), ...u16(0)])),
        for (var i = 0; i < 5; i++) received(tileEvent(i, i * 300)),
        received(piano(BlePianoTiles.timeLeft, [29])),
      ];
      await session.start(GameLaunch.board);
      expect(board.commands, isEmpty);
      expect(session.mode, PianoTilesSession.modeZen);
      expect(session.phase, PianoTilesPhase.playing);
      expect(session.tiles, 5);
      expect(session.secondsLeft, 29);
      expect(session.canChange, isFalse);
      expect(player.calls, isNot(contains('resume')));

      board.send(tileEvent(5, 1500));
      await pumpEventQueue();
      expect(player.calls, containsAllInOrder(['seek 2500', 'resume']));

      board.send(gameState(BleGameState.paused));
      expect(session.phase, PianoTilesPhase.paused);

      session.dispose();
      expect(board.commands.last, [BleCommand.gameControl, BleCommand.stop]);
    });
  });
}
