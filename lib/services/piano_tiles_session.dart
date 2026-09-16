import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/board_games.dart';
import '../models/piano_tiles_track.dart';
import 'ble_service.dart';
import 'sound_cache.dart';
import 'tap_follow_player.dart';

enum PianoTilesPhase { noBoard, loading, ready, playing, gameOver, result, paused, closed }

class PianoTilesResult {
  const PianoTilesResult({
    required this.mode,
    required this.score,
    required this.tiles,
    required this.stars,
    required this.newBest,
    required this.finished,
  });

  final int mode;

  /// Classic: time in ms (0 when not finished), Zen and Arcade: tiles.
  final int score;
  final int tiles;
  final int stars;
  final bool newBest;

  /// Classic: all tiles tapped, Zen: the time ran out (not ended by a mistake).
  final bool finished;
}

/// Piano Tiles with the board: the board deals the tiles and judges the taps, the app plays a song that follows
/// the tapped tiles ([TapFollowPlayer]) and shows the run.
///
/// Opened from the app it selects the mode on the board and lets the player pick the song; opened because the
/// game started on the board ([GameLaunch.board]) it plays the last picked song and only follows the board.
/// Byte layouts: raspberry-micro-python/README.md (Piano Tiles Events).
class PianoTilesSession extends ChangeNotifier {
  PianoTilesSession({
    BleService? ble,
    TapFollowPlayer? music,
    void Function(String soundId)? playSound,
    Future<List<PianoTilesTrack>> Function()? loadCatalog,
    Random? random,
  })  : _ble = ble ?? BleService(),
        _music = music ?? TapFollowPlayer(),
        _playSound = playSound ?? _playCached,
        _loadCatalog = loadCatalog ?? loadPianoTilesCatalog,
        _random = random ?? Random();

  static const List<String> modeNames = ['Classic', 'Zen', 'Arcade'];
  static const List<String> modeDescriptions = ['50 tiles against the clock', 'As many tiles as you can in 30 s', 'The tiles scroll and get faster'];
  static const int modeClassic = 0;
  static const int modeZen = 1;
  static const int modeArcade = 2;

  static const String _modeKey = 'piano_tiles_mode';
  static const String _songKey = 'piano_tiles_song';
  static const String _mistakeSound = 'buzz';

  static void _playCached(String soundId) => unawaited(SoundCache.instance.play(soundId));

  final BleService _ble;
  final TapFollowPlayer _music;
  final void Function(String soundId) _playSound;
  final Future<List<PianoTilesTrack>> Function() _loadCatalog;
  final Random _random;
  StreamSubscription<List<int>>? _events;
  StreamSubscription<BleConnectionState>? _connection;
  bool _disposed = false;
  bool _openOnBoard = false;

  GameLaunch launch = GameLaunch.app;
  PianoTilesPhase phase = PianoTilesPhase.loading;
  List<PianoTilesTrack> catalog = const [];
  PianoTilesTrack? song;
  int mode = modeClassic;

  /// Tiles tapped in this run, Classic's goal, time since the first tap, Zen's seconds left, Arcade's speed level.
  int tiles = 0;
  int goal = 50;
  int elapsedMs = 0;
  int? secondsLeft;
  int speedLevel = 0;
  PianoTilesResult? result;

  bool get isRunning => phase == PianoTilesPhase.playing || phase == PianoTilesPhase.paused;

  bool get canChange => launch == GameLaunch.app && !isRunning && phase != PianoTilesPhase.noBoard;

  Future<void> start(GameLaunch launch) async {
    this.launch = launch;
    final replay = launch == GameLaunch.board ? _ble.recentGameEvents : const <BleReceivedEvent>[];
    _events = _ble.eventStream.listen(_onEvent);
    _connection = _ble.connectionState.listen(_onConnection);
    if (launch == GameLaunch.board) {
      _openOnBoard = true;
      phase = PianoTilesPhase.ready;
      for (final event in replay) {
        _onEvent(event.data, replay: true);
      }
    }

    final prefs = await SharedPreferences.getInstance();
    catalog = await _loadCatalog();
    if (_disposed) return;
    final lastSong = prefs.getString(_songKey);
    final pick = catalog.where((s) => s.id == lastSong).firstOrNull ?? catalog.firstOrNull;
    if (launch == GameLaunch.app) {
      mode = (prefs.getInt(_modeKey) ?? modeClassic).clamp(modeClassic, modeArcade);
    }
    if (pick != null) await _loadSong(pick);
    if (_disposed) return;

    if (!_ble.isConnected) {
      _set(PianoTilesPhase.noBoard);
    } else if (launch == GameLaunch.app) {
      _set(PianoTilesPhase.ready);
      await _openOnBoardNow();
    } else if (phase == PianoTilesPhase.loading) {
      _set(PianoTilesPhase.ready);
    } else {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _events?.cancel();
    _connection?.cancel();
    _music.dispose();
    if (_openOnBoard) {
      unawaited(_ble.stopGame()); // leaving the game in the app closes it on the board
    }
    super.dispose();
  }

  // ==============================================================================================
  // Actions
  // ==============================================================================================

  Future<void> selectSong(PianoTilesTrack next) async {
    if (isRunning || next.id == song?.id) return;
    await _loadSong(next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_songKey, next.id);
  }

  Future<void> nextRandomSong() async {
    final choices = catalog.where((s) => s.id != song?.id).toList();
    if (choices.isEmpty) return;
    await selectSong(choices[_random.nextInt(choices.length)]);
  }

  Future<void> selectMode(int value) async {
    if (!canChange || value == mode) return;
    mode = value;
    result = null;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_modeKey, value);
    await _openOnBoardNow();
  }

  /// New tiles on the board; the run starts with the tap on the start tile.
  Future<void> newTiles() async {
    if (!_openOnBoard) await _openOnBoardNow();
    await _ble.startGame();
  }

  Future<void> pause() => _ble.pauseGame();

  Future<void> resume() => _ble.resumeGame();

  /// Quits the run, the board deals new tiles.
  Future<void> quitRun() => _ble.resetGame();

  Future<void> _openOnBoardNow() async {
    _openOnBoard = true;
    await _ble.selectGame(BleGameId.pianoTiles, mode);
  }

  Future<void> _loadSong(PianoTilesTrack next) async {
    final withChart = next.tileMs.isEmpty ? await next.loadChart() : next;
    if (_disposed) return;
    song = withChart;
    notifyListeners();
    await _music.load(withChart);
  }

  // ==============================================================================================
  // Board events
  // ==============================================================================================

  void _onConnection(BleConnectionState state) {
    if (_disposed) return;
    if (state != BleConnectionState.connected) {
      _music.stop();
      _set(PianoTilesPhase.noBoard);
    } else if (phase == PianoTilesPhase.noBoard) {
      _set(PianoTilesPhase.ready);
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
      case BleEvent.pianoTiles:
        if (data.length >= 2) _onPianoTiles(data, replay);
    }
  }

  void _onGameSelected(int gameId, int variant) {
    _openOnBoard = gameId == BleGameId.pianoTiles;
    _music.stop();
    if (!_openOnBoard) {
      _set(PianoTilesPhase.closed);
      return;
    }
    if (variant >= modeClassic && variant <= modeArcade) mode = variant;
    result = null;
    tiles = 0;
    _set(PianoTilesPhase.ready);
  }

  void _onGameState(int state) {
    if (!_openOnBoard) return; // another game's state
    switch (state) {
      case BleGameState.ready:
        _music.stop();
        result = null;
        tiles = 0;
        _set(PianoTilesPhase.ready);
      case BleGameState.paused:
        _music.hold();
        _set(PianoTilesPhase.paused);
      case BleGameState.running:
        // After a pause the board counts in, the next tile brings the music back
        if (phase == PianoTilesPhase.paused) _set(PianoTilesPhase.playing);
    }
  }

  void _onPianoTiles(List<int> data, bool replay) {
    switch (data[1]) {
      case BlePianoTiles.runStart: // mode, goal u16, row time ms u16
        if (data.length < 5) return;
        mode = data[2];
        goal = _u16(data, 3);
        tiles = 0;
        elapsedMs = 0;
        secondsLeft = mode == modeZen ? goal : null;
        speedLevel = 0;
        result = null;
        _music.stop();
        _set(PianoTilesPhase.playing);
      case BlePianoTiles.tile: // tile u16, lane, time ms u32
        if (data.length < 9) return;
        final tile = _u16(data, 2);
        tiles = tile + 1;
        elapsedMs = _u32(data, 5);
        if (!replay) _music.tile(tile);
        if (phase != PianoTilesPhase.playing) {
          _set(PianoTilesPhase.playing);
        } else {
          notifyListeners();
        }
      case BlePianoTiles.speed: // level, row time ms u16
        if (data.length < 3) return;
        speedLevel = data[2];
        notifyListeners();
      case BlePianoTiles.timeLeft: // seconds
        if (data.length < 3) return;
        secondsLeft = data[2];
        notifyListeners();
      case BlePianoTiles.mistake: // reason, tile u16, x, y
        _music.stop();
        if (!replay) _playSound(_mistakeSound);
        _set(PianoTilesPhase.gameOver);
      case BlePianoTiles.result: // mode, score u32, tiles u16, stars, flags (bit 0 new best, bit 1 finished)
        if (data.length < 11) return;
        result = PianoTilesResult(
          mode: data[2],
          score: _u32(data, 3),
          tiles: _u16(data, 7),
          stars: data[9],
          newBest: data[10] & 1 != 0,
          finished: data[10] & 2 != 0,
        );
        tiles = result!.tiles;
        // A finished run lets the last tapped tile ring out, the music stops by itself
        if (!result!.finished) _music.stop();
        _set(PianoTilesPhase.result);
    }
  }

  void _set(PianoTilesPhase next) {
    phase = next;
    if (!_disposed) notifyListeners();
  }

  static int _u16(List<int> d, int i) => d[i] | (d[i + 1] << 8);

  static int _u32(List<int> d, int i) => d[i] | (d[i + 1] << 8) | (d[i + 2] << 16) | (d[i + 3] << 24);
}
