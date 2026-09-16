import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/board_games.dart';
import '../models/sound_clip.dart';
import 'ble_service.dart';
import 'sound_cache.dart';

enum SimonSaysPhase { noBoard, ready, lives, watch, turn, mistake, result, paused, closed }

class SimonSaysResult {
  const SimonSaysResult({
    required this.mode,
    required this.score,
    required this.best,
    required this.newBest,
    required this.won,
  });

  final int mode;
  final int score;
  final int best;
  final bool newBest;
  final bool won;
}

/// Simon Says with the board: the board runs the game, the app shows it and plays the sounds.
///
/// Every step the board shows and every correct press plays the tone of its colour block, a mistake buzzes and
/// a won run gets a fanfare. Opened from the app it selects the game in the chosen mode on the board; opened
/// because the game started on the board ([GameLaunch.board]) it only follows the board's events.
/// Byte layouts: raspberry-micro-python/README.md (Simon Says Events).
class SimonSaysSession extends ChangeNotifier {
  SimonSaysSession({BleService? ble, void Function(String soundId)? playSound})
      : _ble = ble ?? BleService(),
        _playSound = playSound ?? _playCached;

  static const List<String> modeNames = ['Simple', 'Endless'];
  static const List<String> modeDescriptions = ['Repeat 8 steps', 'Open end, 3 lives'];
  static const int modeSimple = 0;
  static const int modeEndless = 1;
  static const int blockCount = 8;

  static const String _modeKey = 'simon_says_mode';
  static const String _mistakeSound = 'buzz';
  static const String _wonSound = 'fanfare';
  static const int _tooSlow = 0xFF;
  static const int _pressFlashMs = 180;

  static void _playCached(String soundId) => unawaited(SoundCache.instance.play(soundId));

  final BleService _ble;
  final void Function(String soundId) _playSound;
  StreamSubscription<List<int>>? _events;
  StreamSubscription<BleConnectionState>? _connection;
  Timer? _litTimer;
  bool _disposed = false;

  /// Simon Says is the game open on the board (the app closes it when the screen closes).
  bool _openOnBoard = false;

  GameLaunch launch = GameLaunch.app;
  SimonSaysPhase phase = SimonSaysPhase.ready;
  int mode = modeSimple;

  /// Steps of a Simple run (0 = open end), lives left in Endless, and the current round (= sequence length).
  int steps = 0;
  int lives = 0;
  int round = 0;

  /// The block lit right now (a shown step or a correct press), and the blocks of the last mistake.
  int? litBlock;
  int? pressedWrongBlock;
  int? rightBlock;
  SimonSaysResult? result;

  bool get isRunning => const {
        SimonSaysPhase.lives,
        SimonSaysPhase.watch,
        SimonSaysPhase.turn,
        SimonSaysPhase.mistake,
        SimonSaysPhase.paused,
      }.contains(phase);

  bool get canChangeMode => launch == GameLaunch.app && !isRunning && phase != SimonSaysPhase.noBoard;

  Future<void> start(GameLaunch launch) async {
    this.launch = launch;
    // Replay what happened since the board opened the game, then follow live (same synchronous block).
    final replay = launch == GameLaunch.board ? _ble.recentGameEvents : const <BleReceivedEvent>[];
    _events = _ble.eventStream.listen(_onEvent);
    _connection = _ble.connectionState.listen(_onConnection);
    if (launch == GameLaunch.board) {
      _openOnBoard = true;
      for (final event in replay) {
        _onEvent(event.data, replay: true);
      }
    }
    if (!_ble.isConnected) {
      _set(SimonSaysPhase.noBoard);
      return;
    }
    if (launch == GameLaunch.app) {
      final prefs = await SharedPreferences.getInstance();
      if (_disposed) return;
      mode = (prefs.getInt(_modeKey) ?? modeSimple).clamp(modeSimple, modeEndless);
      notifyListeners();
      await _openOnBoardNow();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _events?.cancel();
    _connection?.cancel();
    _litTimer?.cancel();
    if (_openOnBoard) {
      unawaited(_ble.stopGame()); // leaving the game in the app closes it on the board
    }
    super.dispose();
  }

  // ==============================================================================================
  // Actions
  // ==============================================================================================

  Future<void> selectMode(int value) async {
    if (!canChangeMode || value == mode) return;
    mode = value;
    result = null;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_modeKey, value);
    await _openOnBoardNow();
  }

  /// Starts a run (the board also starts one with any pad).
  Future<void> startRun() async {
    if (!_openOnBoard) await _openOnBoardNow();
    await _ble.startGame();
  }

  Future<void> pause() => _ble.pauseGame();

  Future<void> resume() => _ble.resumeGame();

  /// Quits the run, the board goes back to the game's ready screen.
  Future<void> quitRun() => _ble.resetGame();

  Future<void> _openOnBoardNow() async {
    _openOnBoard = true;
    await _ble.selectGame(BleGameId.simonSays, mode);
  }

  // ==============================================================================================
  // Board events
  // ==============================================================================================

  void _onConnection(BleConnectionState state) {
    if (_disposed) return;
    if (state != BleConnectionState.connected) {
      _litTimer?.cancel();
      litBlock = null;
      _set(SimonSaysPhase.noBoard);
    } else if (phase == SimonSaysPhase.noBoard) {
      _set(SimonSaysPhase.ready);
      if (launch == GameLaunch.app) unawaited(_openOnBoardNow());
    }
  }

  void _onEvent(List<int> data, {bool replay = false}) {
    if (_disposed || data.isEmpty) return;
    switch (data[0]) {
      case BleEvent.game:
        if (data.length < 3) return;
        if (data[1] == BleEvent.gameSelected) {
          _onGameSelected(data[2], data.length > 3 ? data[3] : 0xFF);
        } else if (data[1] == BleEvent.gameState) {
          _onGameState(data[2]);
        }
      case BleEvent.simonSays:
        if (data.length >= 2) _onSimonSays(data, replay);
    }
  }

  void _onGameSelected(int gameId, int variant) {
    _openOnBoard = gameId == BleGameId.simonSays;
    if (!_openOnBoard) {
      _litTimer?.cancel();
      litBlock = null;
      _set(SimonSaysPhase.closed);
      return;
    }
    if (variant == modeSimple || variant == modeEndless) mode = variant;
    result = null;
    _set(SimonSaysPhase.ready);
  }

  void _onGameState(int state) {
    if (!_openOnBoard) return; // another game's state
    switch (state) {
      case BleGameState.ready:
        result = null;
        _set(SimonSaysPhase.ready);
      case BleGameState.paused:
        _set(SimonSaysPhase.paused);
      case BleGameState.running:
        // A resume shows the round again, a new run sends its run start
        if (phase == SimonSaysPhase.paused || !isRunning) _set(SimonSaysPhase.watch);
    }
  }

  void _onSimonSays(List<int> data, bool replay) {
    switch (data[1]) {
      case BleSimonSays.runStart: // mode, steps, lives
        if (data.length < 5) return;
        mode = data[2];
        steps = data[3];
        lives = data[4];
        round = 1;
        result = null;
        pressedWrongBlock = rightBlock = null;
        _set(mode == modeEndless ? SimonSaysPhase.lives : SimonSaysPhase.watch);
      case BleSimonSays.watch: // round, speed level, lives
        if (data.length < 5) return;
        round = data[2];
        lives = data[4];
        pressedWrongBlock = rightBlock = null;
        _set(SimonSaysPhase.watch);
      case BleSimonSays.cue: // step, block, lit ms u16
        if (data.length < 6 || replay) return;
        final block = data[3] % blockCount;
        _playSound(simonToneId(block));
        _light(block, data[4] | (data[5] << 8));
      case BleSimonSays.turn: // round, time per press ms u16
        if (data.length < 3) return;
        round = data[2];
        _set(SimonSaysPhase.turn);
      case BleSimonSays.press: // step, block, correct
        if (data.length < 5 || replay || data[4] != 1) return;
        final block = data[3] % blockCount;
        _playSound(simonToneId(block));
        _light(block, _pressFlashMs);
      case BleSimonSays.mistake: // step, pressed block (0xFF too slow), right block, lives left
        if (data.length < 6) return;
        pressedWrongBlock = data[3] == _tooSlow ? null : data[3] % blockCount;
        rightBlock = data[4] % blockCount;
        lives = data[5];
        _litTimer?.cancel();
        litBlock = null;
        if (!replay) _playSound(_mistakeSound);
        _set(SimonSaysPhase.mistake);
      case BleSimonSays.result: // mode, score, best, flags (bit 0 new best, bit 1 won)
        if (data.length < 6) return;
        result = SimonSaysResult(
          mode: data[2],
          score: data[3],
          best: data[4],
          newBest: data[5] & 1 != 0,
          won: data[5] & 2 != 0,
        );
        _litTimer?.cancel();
        litBlock = null;
        if (!replay && result!.won) _playSound(_wonSound);
        _set(SimonSaysPhase.result);
    }
  }

  void _light(int block, int ms) {
    _litTimer?.cancel();
    litBlock = block;
    notifyListeners();
    _litTimer = Timer(Duration(milliseconds: ms), () {
      if (_disposed) return;
      litBlock = null;
      notifyListeners();
    });
  }

  void _set(SimonSaysPhase next) {
    phase = next;
    if (!_disposed) notifyListeners();
  }
}
