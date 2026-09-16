import 'dart:async';
import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/board_games.dart';
import '../services/ble_service.dart';
import 'session_manager.dart';

/// Counts the play time of one run. Time only counts while the run isn't paused and at most [idleLimit] past
/// the last activity, so a run left alone (Piano Tiles Classic waits forever for the next tap) or an app that
/// got suspended earns nothing.
class PlayClock {
  PlayClock({int Function()? nowMs}) : _nowMs = nowMs ?? _monotonicMs;

  static final Stopwatch _stopwatch = Stopwatch()..start();
  static int _monotonicMs() => _stopwatch.elapsedMilliseconds;

  final int Function() _nowMs;
  Duration idleLimit = const Duration(seconds: 5);

  bool _running = false;
  bool _paused = false;
  int _countedMs = 0;
  int _lastTickMs = 0;
  int _lastActivityMs = 0;

  bool get running => _running;
  bool get paused => _paused;

  Duration get played {
    _tick();
    return Duration(milliseconds: _countedMs);
  }

  void start(Duration idleLimit) {
    this.idleLimit = idleLimit;
    _running = true;
    _paused = false;
    _countedMs = 0;
    _lastTickMs = _lastActivityMs = _nowMs();
  }

  void activity() {
    if (!_running) return;
    _tick();
    _lastActivityMs = _nowMs();
  }

  void pause() {
    if (!_running || _paused) return;
    _tick();
    _paused = true;
  }

  void resume() {
    if (!_running || !_paused) return;
    _paused = false;
    _lastTickMs = _lastActivityMs = _nowMs();
  }

  /// Ends the run and returns its play time.
  Duration stop() {
    if (!_running) return Duration.zero;
    _tick();
    _running = false;
    _paused = false;
    return Duration(milliseconds: _countedMs);
  }

  void _tick() {
    final now = _nowMs();
    if (_running && !_paused) {
      final countUntil = min(now, _lastActivityMs + idleLimit.inMilliseconds);
      if (countUntil > _lastTickMs) _countedMs += countUntil - _lastTickMs;
    }
    _lastTickMs = now;
  }
}

/// A finished run and what it earned.
class RunCredit {
  const RunCredit({
    required this.gameId,
    required this.played,
    required this.multiplier,
    required this.earned,
    required this.endedAt,
  });

  /// [BleGameId] of the board game, [phoneGameScreenId] for the on-phone game.
  final int gameId;
  final Duration played;
  final double multiplier;
  final Duration earned;
  final DateTime endedAt;
}

class PlayTimeState {
  const PlayTimeState({
    this.boardGameId,
    this.boardGameState,
    this.runGameId,
    this.paused = false,
    this.played = Duration.zero,
    this.lastRun,
  });

  /// The game open on the board ([BleGameId], 0 = start screen), null while unknown or disconnected.
  final int? boardGameId;

  /// [BleGameState] of the open game.
  final int? boardGameState;

  /// Game of the run being counted ([BleGameId] or [phoneGameScreenId]), null when no run is counted.
  final int? runGameId;
  final bool paused;

  /// Play time of the running run so far (updated every second), or of the last run.
  final Duration played;
  final RunCredit? lastRun;

  bool get running => runGameId != null;

  PlayTimeState copyWith({
    int? boardGameId,
    int? boardGameState,
    bool clearBoard = false,
    int? runGameId,
    bool clearRun = false,
    bool? paused,
    Duration? played,
    RunCredit? lastRun,
  }) {
    return PlayTimeState(
      boardGameId: clearBoard ? null : boardGameId ?? this.boardGameId,
      boardGameState: clearBoard ? null : boardGameState ?? this.boardGameState,
      runGameId: clearRun ? null : runGameId ?? this.runGameId,
      paused: paused ?? this.paused,
      played: played ?? this.played,
      lastRun: lastRun ?? this.lastRun,
    );
  }
}

/// Turns play into Instagram time and keeps the app in step with the board.
///
/// A board run starts when the open game's state becomes RUNNING and ends with OVER, WIN or READY, when
/// another game opens, or when the board disconnects. Its play time (without pauses, see [PlayClock]) is
/// credited once through [SessionManager.creditPlayTime]. Only events caused by playing count as activity:
/// pad and key presses on the board (Pocket Guitar's practice hits send nothing else), Simon Says run start,
/// cues and presses, Piano Tiles tiles, Pocket Guitar song starts, strums and notes that weren't missed.
/// The on-phone game reports its taps with [phoneActivity].
///
/// Game screens register with [attachScreen]. When the board opens or starts a game that has no screen,
/// [boardStartedGames] asks the app to show it.
class PlayTimeTracker extends Notifier<PlayTimeState> {
  PlayTimeTracker({BleService? ble, int Function()? nowMs})
      : _ble = ble ?? BleService(),
        _clock = PlayClock(nowMs: nowMs);

  static const Map<int, Duration> idleLimits = {
    BleGameId.pianoTiles: Duration(seconds: 3),
    BleGameId.simonSays: Duration(seconds: 6),
    BleGameId.pocketGuitar: Duration(seconds: 15),
    phoneGameScreenId: Duration(seconds: 2),
  };
  static const int _gradeMiss = 4;

  final BleService _ble;
  final PlayClock _clock;
  StreamSubscription<List<int>>? _events;
  StreamSubscription<BleConnectionState>? _connection;
  Timer? _ticker;
  final Map<int, int> _screens = {};
  final _boardStartedGames = StreamController<int>.broadcast();
  final _gameScreensClosed = StreamController<void>.broadcast();

  /// Game ids ([BleGameId]) the board opened or started while no screen for them was open.
  Stream<int> get boardStartedGames => _boardStartedGames.stream;

  /// Fires when the last open game screen closed.
  Stream<void> get gameScreensClosed => _gameScreensClosed.stream;

  bool get hasGameScreen => _screens.isNotEmpty;

  bool isScreenAttached(int id) => _screens.containsKey(id);

  @override
  PlayTimeState build() {
    _events?.cancel();
    _connection?.cancel();
    _events = _ble.eventStream.listen(_onEvent);
    _connection = _ble.connectionState.listen(_onConnection);
    ref.onDispose(() {
      _events?.cancel();
      _connection?.cancel();
      _ticker?.cancel();
    });
    if (_ble.isConnected) unawaited(_ble.requestTelemetry());
    return const PlayTimeState();
  }

  // ================================================================================================
  // Screens
  // ================================================================================================

  /// A game screen opened ([BleGameId] or [phoneGameScreenId]). Plain bookkeeping, safe in initState.
  void attachScreen(int id) => _screens[id] = (_screens[id] ?? 0) + 1;

  /// A game screen closed. Safe in dispose.
  void detachScreen(int id) {
    final count = (_screens[id] ?? 0) - 1;
    if (count > 0) {
      _screens[id] = count;
      return;
    }
    _screens.remove(id);
    if (_screens.isEmpty) _gameScreensClosed.add(null);
  }

  // ================================================================================================
  // On-phone game
  // ================================================================================================

  /// A tap in the on-phone game: starts a phone run or keeps it counting.
  void phoneActivity() {
    if (state.runGameId == phoneGameScreenId) {
      _clock.activity();
    } else {
      _startRun(phoneGameScreenId);
    }
  }

  /// Ends the on-phone run and credits it. Returns null when no phone run was counted.
  RunCredit? endPhoneRun() => state.runGameId == phoneGameScreenId ? _finishRun() : null;

  // ================================================================================================
  // Board
  // ================================================================================================

  void _onConnection(BleConnectionState connection) {
    if (connection == BleConnectionState.connected) {
      unawaited(_ble.requestTelemetry());
      return;
    }
    if (state.runGameId != null && state.runGameId != phoneGameScreenId) _finishRun();
    if (state.boardGameId != null) state = state.copyWith(clearBoard: true);
  }

  void _onEvent(List<int> data) {
    if (data.isEmpty) return;
    switch (data[0]) {
      case BleEvent.key: // [type (0 press), key]
        final run = state.runGameId;
        if (data.length >= 3 && data[1] == 0 && run != null && run != phoneGameScreenId) _clock.activity();
      case BleEvent.game:
        if (data.length < 3) return;
        if (data[1] == BleEvent.gameSelected) {
          _onGameSelected(data[2]);
        } else if (data[1] == BleEvent.gameState) {
          _onGameState(data[2]);
        }
      case BleEvent.batteryReport:
        if (data.length >= 7) _onTelemetry(data[5], data[6]);
      case BleEvent.simonSays:
        if (data.length >= 2 &&
            (data[1] == BleSimonSays.runStart || data[1] == BleSimonSays.cue || data[1] == BleSimonSays.press)) {
          _boardActivity(BleGameId.simonSays);
        }
      case BleEvent.pianoTiles:
        if (data.length >= 2 && data[1] == BlePianoTiles.tile) _boardActivity(BleGameId.pianoTiles);
      case BleEvent.songStart:
      case BleEvent.overstrum:
        _boardActivity(BleGameId.pocketGuitar);
      case BleEvent.noteResult:
        if (data.length >= 4 && data[3] != _gradeMiss) _boardActivity(BleGameId.pocketGuitar);
    }
  }

  void _onGameSelected(int gameId) {
    _finishBoardRun();
    state = state.copyWith(boardGameId: gameId, boardGameState: BleGameState.ready);
    if (isBoardGame(gameId) && !isScreenAttached(gameId)) _boardStartedGames.add(gameId);
  }

  void _onGameState(int gameState) {
    final gameId = state.boardGameId;
    state = state.copyWith(boardGameState: gameState);
    switch (gameState) {
      case BleGameState.running:
        if (gameId == null || !isBoardGame(gameId)) return;
        if (state.runGameId == gameId) {
          _clock.resume();
          state = state.copyWith(paused: false);
        } else {
          _startRun(gameId);
          if (!isScreenAttached(gameId)) _boardStartedGames.add(gameId);
        }
      case BleGameState.paused:
        if (state.runGameId == gameId) {
          _clock.pause();
          state = state.copyWith(paused: true, played: _clock.played);
        }
      case BleGameState.ready:
      case BleGameState.over:
      case BleGameState.win:
        _finishBoardRun();
    }
  }

  /// Battery report, asked for on connect: which game is open and whether a run is already going.
  void _onTelemetry(int gameId, int gameState) {
    if (gameId != state.boardGameId) {
      _finishBoardRun();
      state = state.copyWith(boardGameId: gameId);
    }
    if (gameState == BleGameState.running) {
      _onGameState(gameState);
    } else {
      state = state.copyWith(boardGameState: gameState);
    }
  }

  void _boardActivity(int gameId) {
    if (state.runGameId == gameId) _clock.activity();
  }

  void _finishBoardRun() {
    final run = state.runGameId;
    if (run != null && run != phoneGameScreenId) _finishRun();
  }

  // ================================================================================================
  // Runs
  // ================================================================================================

  void _startRun(int gameId) {
    if (state.runGameId != null) _finishRun();
    _clock.start(idleLimits[gameId] ?? const Duration(seconds: 5));
    state = state.copyWith(runGameId: gameId, paused: false, played: Duration.zero);
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (state.runGameId != null) state = state.copyWith(played: _clock.played);
    });
  }

  RunCredit _finishRun() {
    final gameId = state.runGameId!;
    _ticker?.cancel();
    _ticker = null;
    final played = _clock.stop();
    final session = ref.read(sessionManagerProvider.notifier);
    final multiplier = ref.read(sessionManagerProvider).playTimeMultiplier;
    final earned = session.creditPlayTime(played);
    final credit = RunCredit(
      gameId: gameId,
      played: played,
      multiplier: multiplier,
      earned: earned,
      endedAt: DateTime.now(),
    );
    state = state.copyWith(clearRun: true, paused: false, played: played, lastRun: credit);
    return credit;
  }
}

final playTimeProvider = NotifierProvider<PlayTimeTracker, PlayTimeState>(PlayTimeTracker.new);
