import 'package:flutter_test/flutter_test.dart';
import 'package:productive_roadblock/models/board_games.dart';
import 'package:productive_roadblock/services/ble_service.dart';
import 'package:productive_roadblock/services/simon_says_session.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

List<int> simon(int subtype, List<int> payload) => [BleEvent.simonSays, subtype, ...payload];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakeBoard board;
  late List<String> sounds;
  late SimonSaysSession session;

  setUp(() {
    SharedPreferences.setMockInitialValues({'simon_says_mode': SimonSaysSession.modeSimple});
    board = FakeBoard();
    sounds = [];
    session = SimonSaysSession(ble: board, playSound: sounds.add);
  });

  test('opened from the app: selects the saved mode, changes it and starts a run', () async {
    await session.start(GameLaunch.app);
    expect(board.commands, [
      [BleCommand.gameControl, BleCommand.select, BleGameId.simonSays, SimonSaysSession.modeSimple],
    ]);
    board.send(gameSelected(BleGameId.simonSays, 0));
    expect(session.phase, SimonSaysPhase.ready);
    expect(session.canChangeMode, isTrue);

    await session.selectMode(SimonSaysSession.modeEndless);
    expect(board.commands.last, [BleCommand.gameControl, BleCommand.select, BleGameId.simonSays, 1]);
    expect((await SharedPreferences.getInstance()).getInt('simon_says_mode'), 1);

    await session.startRun();
    expect(board.commands.last, [BleCommand.gameControl, BleCommand.start]);
  });

  test('plays a tone per block for shown steps and correct presses, buzz and fanfare', () async {
    await session.start(GameLaunch.app);
    board.send(gameState(BleGameState.running));
    board.send(simon(BleSimonSays.runStart, [0, 8, 0]));
    expect(session.phase, SimonSaysPhase.watch);
    expect(session.canChangeMode, isFalse);

    board.send(simon(BleSimonSays.watch, [1, 0, 0]));
    board.send(simon(BleSimonSays.cue, [0, 3, ...u16(520)]));
    expect(sounds, ['simon_3']);
    expect(session.litBlock, 3);

    board.send(simon(BleSimonSays.turn, [1, ...u16(5000)]));
    expect(session.phase, SimonSaysPhase.turn);
    board.send(simon(BleSimonSays.press, [0, 3, 1]));
    expect(sounds, ['simon_3', 'simon_3']);

    // A wrong press has no tone, the mistake buzzes and shows both blocks
    board.send(simon(BleSimonSays.press, [1, 5, 0]));
    board.send(simon(BleSimonSays.mistake, [1, 5, 2, 0]));
    expect(sounds, ['simon_3', 'simon_3', 'buzz']);
    expect(session.phase, SimonSaysPhase.mistake);
    expect(session.pressedWrongBlock, 5);
    expect(session.rightBlock, 2);

    board.send(gameState(BleGameState.win));
    board.send(simon(BleSimonSays.result, [0, 8, 8, 3]));
    expect(sounds.last, 'fanfare');
    expect(session.phase, SimonSaysPhase.result);
    expect(session.result!.won, isTrue);
    expect(session.result!.newBest, isTrue);
    expect(session.result!.score, 8);
  });

  test('opened for a game started on the board: catches up without sounds or commands', () async {
    board.recent = [
      received(gameSelected(BleGameId.simonSays, SimonSaysSession.modeEndless)),
      received(gameState(BleGameState.running)),
      received(simon(BleSimonSays.runStart, [1, 0, 3])),
      received(simon(BleSimonSays.watch, [2, 0, 2])),
      received(simon(BleSimonSays.cue, [0, 6, ...u16(520)])),
    ];
    await session.start(GameLaunch.board);
    expect(board.commands, isEmpty);
    expect(sounds, isEmpty);
    expect(session.mode, SimonSaysSession.modeEndless);
    expect(session.phase, SimonSaysPhase.watch);
    expect(session.round, 2);
    expect(session.lives, 2);
    expect(session.canChangeMode, isFalse);

    // Live events sound again
    board.send(simon(BleSimonSays.cue, [1, 7, ...u16(520)]));
    expect(sounds, ['simon_7']);

    // Closing the screen closes the game on the board
    session.dispose();
    expect(board.commands.last, [BleCommand.gameControl, BleCommand.stop]);
  });

  test('closed on the board: the result stays, closing the screen sends nothing', () async {
    await session.start(GameLaunch.app);
    board.send(simon(BleSimonSays.result, [0, 4, 6, 0]));
    board.send(gameSelected(BleGameId.startScreen));
    expect(session.phase, SimonSaysPhase.closed);
    expect(session.result!.score, 4);
    final sent = board.commands.length;
    session.dispose();
    expect(board.commands, hasLength(sent));
  });
}
