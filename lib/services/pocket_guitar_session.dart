import 'dart:async';
import 'dart:math';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/board_games.dart';
import '../models/pocket_guitar_song.dart';
import 'ble_service.dart';
import 'sound_cache.dart';

enum PocketGuitarPhase { noBoard, loading, uploading, ready, countIn, playing, paused, result, error, closed }

class PocketGuitarResult {
  const PocketGuitarResult({
    required this.score,
    required this.stars,
    required this.accuracy,
    required this.bestStreak,
    required this.newBest,
    required this.flawless,
  });

  final int score;
  final int stars;
  final int accuracy;
  final int bestStreak;
  final bool newBest;
  final bool flawless;
}

/// Pocket Guitar with the board: the game runs on the board, the music plays on the phone.
///
/// Picks a random bundled song, sends its chart to the board and follows the board's events:
/// every song start event says which song position (ms) plays right now (negative during the
/// count-in), so the music starts on the board's clock. Pause, resume, quit and the result come
/// from the board as well, whether they were triggered on the board or in the app. Opened because
/// a song started on the board ([GameLaunch.board]) it sends no song and only follows the board.
/// Byte layouts: raspberry-micro-python/README.md (BLE protocol, Pocket Guitar events).
class PocketGuitarSession extends ChangeNotifier {
  PocketGuitarSession({BleService? ble, AudioPlayer? player, Random? random})
      : _ble = ble ?? BleService(),
        _player = player ?? AudioPlayer(),
        _random = random ?? Random();

  static const int appSongSlot = 0xFF;
  static const List<String> difficultyNames = ['Easy', 'Medium', 'Hard', 'Expert'];
  static const int modePlay = 0;
  static const int modePractice = 1;

  static const String _delayOffsetKey = 'pocket_guitar_delay_offset_ms';
  static const String _missSound = 'thump';
  static const int _gradeMiss = 4;
  static const double _missVolume = 0.4;
  static const Duration _missDuck = Duration(milliseconds: 250);

  /// On a resume the board starts a one-bar count-in inside the song; the music is scheduled this far
  /// ahead so the seek has finished when it has to play.
  static const int _resumeLeadMs = 250;

  final BleService _ble;
  final Random _random;
  final AudioPlayer _player;
  StreamSubscription<List<int>>? _events;
  StreamSubscription<BleConnectionState>? _connection;
  Timer? _startTimer;
  Timer? _duckTimer;
  int _playToken = 0;
  bool _disposed = false;

  /// Pocket Guitar is the game open on the board (the app closes it when the screen closes).
  bool _openOnBoard = false;

  GameLaunch launch = GameLaunch.app;

  List<PocketGuitarSong> _catalog = const [];

  /// The app song selected on the board, or null when a song stored on the board is selected.
  PocketGuitarSong? song;
  PocketGuitarPhase phase = PocketGuitarPhase.loading;
  String? message;
  double uploadProgress = 0;

  int difficulty = 0;
  int availableDifficulties = 0; // bit per difficulty
  int mode = modePlay;
  int bestStars = 0;
  int bestScore = 0;

  int score = 0;
  int multiplier = 1;
  PocketGuitarResult? result;

  /// Bluetooth + audio output delay, sent to the board (it shifts the board's judgement).
  int delayOffsetMs = 0;

  bool get isRunning =>
      phase == PocketGuitarPhase.countIn || phase == PocketGuitarPhase.playing || phase == PocketGuitarPhase.paused;

  bool get canChangeSong =>
      launch == GameLaunch.app &&
      (phase == PocketGuitarPhase.ready || phase == PocketGuitarPhase.result || phase == PocketGuitarPhase.error);

  Future<void> start({GameLaunch launch = GameLaunch.app}) async {
    this.launch = launch;
    if (launch == GameLaunch.board) {
      // Follow the song the board already started: replay what happened since it opened Pocket Guitar
      final replay = _ble.recentGameEvents;
      _listen();
      _openOnBoard = true;
      phase = PocketGuitarPhase.ready;
      for (final event in replay) {
        _onEvent(event.data, age: event.age);
      }
      if (!_ble.isConnected) {
        _set(PocketGuitarPhase.noBoard);
        return;
      }
      notifyListeners();
      await _ble.sendCommand([BleCommand.pocketGuitar, BleCommand.getSelection]);
      return;
    }

    _catalog = await loadPocketGuitarCatalog();
    final prefs = await SharedPreferences.getInstance();
    delayOffsetMs = prefs.getInt(_delayOffsetKey) ?? 0;
    await _player.setReleaseMode(ReleaseMode.stop);
    if (_disposed) return;

    _listen();
    if (_ble.isConnected) {
      await _sendSong(_randomSong());
    } else {
      _set(PocketGuitarPhase.noBoard);
    }
  }

  void _listen() {
    _events = _ble.eventStream.listen(_onEvent);
    _connection = _ble.connectionState.listen((state) {
      if (state != BleConnectionState.connected) {
        _onBoardLost();
      } else if (phase == PocketGuitarPhase.noBoard) {
        if (launch == GameLaunch.board) {
          _set(PocketGuitarPhase.ready);
        } else {
          // After a reconnect the board may have restarted: send the song again
          unawaited(_sendSong(song ?? _randomSong()));
        }
      }
    });
  }

  @override
  void dispose() {
    _disposed = true;
    _events?.cancel();
    _connection?.cancel();
    _startTimer?.cancel();
    _duckTimer?.cancel();
    if (_openOnBoard) {
      unawaited(_ble.stopGame()); // leaving the game in the app closes it on the board (a song quits)
    }
    unawaited(_player.dispose());
    super.dispose();
  }

  // ==============================================================================================
  // Actions
  // ==============================================================================================

  /// Sends another random song (not the current one) to the board.
  Future<void> nextRandomSong() async {
    if (!canChangeSong) return;
    await _sendSong(_randomSong(exclude: song));
  }

  Future<void> selectDifficulty(int value) async {
    if (availableDifficulties & (1 << value) == 0) return;
    await _ble.sendCommand([BleCommand.pocketGuitar, BleCommand.selectDifficulty, value]);
  }

  /// Starts the selected song on the board in Play or Practice mode. Practice plays no music:
  /// the board waits at every note, the music can't.
  Future<void> startSong(int newMode) async {
    await _ble.sendCommand([BleCommand.pocketGuitar, BleCommand.selectMode, newMode]);
    await _ble.startGame();
  }

  Future<void> pause() => _ble.pauseGame();

  Future<void> resume() => _ble.resumeGame();

  /// Quits the running song, the board goes back to its select screen.
  Future<void> quitSong() => _ble.resetGame();

  Future<void> changeDelayOffset(int deltaMs) async {
    delayOffsetMs = (delayOffsetMs + deltaMs).clamp(-300, 500);
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_delayOffsetKey, delayOffsetMs);
    await _sendDelayOffset();
  }

  // ==============================================================================================
  // Song upload
  // ==============================================================================================

  PocketGuitarSong _randomSong({PocketGuitarSong? exclude}) {
    final choices = _catalog.where((s) => s.id != exclude?.id).toList();
    final pool = choices.isEmpty ? _catalog : choices;
    return pool[_random.nextInt(pool.length)];
  }

  Future<void> _sendSong(PocketGuitarSong next) async {
    if (!_ble.isConnected) {
      _set(PocketGuitarPhase.noBoard);
      return;
    }
    await _stopMusic();
    _openOnBoard = true; // the song opens Pocket Guitar on the board
    song = next;
    result = null;
    score = 0;
    multiplier = 1;
    uploadProgress = 0;
    _set(PocketGuitarPhase.uploading);

    try {
      await _player.setSource(AssetSource(next.audioSourcePath));
    } catch (e) {
      debugPrint('[PocketGuitar] Could not load ${next.audioAsset}: $e');
    }
    final chart = await next.loadChartBytes();
    if (_disposed || song != next) return;

    final sent = await _ble.sendStream(BleStream.pocketGuitarSong, chart, onProgress: (progress) {
      uploadProgress = progress;
      if (!_disposed) notifyListeners();
    });
    if (_disposed || song != next) return;
    if (!sent) {
      _set(PocketGuitarPhase.error, 'Could not send the song to the board.');
      return;
    }
    // The board answers with a song selection event (see _onSongSelection) or an error event
    await _sendDelayOffset();
  }

  Future<void> _sendDelayOffset() async {
    final value = delayOffsetMs & 0xFFFF;
    await _ble.sendCommand([BleCommand.pocketGuitar, BleCommand.setDelayOffset, value & 0xFF, value >> 8]);
  }

  // ==============================================================================================
  // Board events
  // ==============================================================================================

  /// [age]: how long ago a replayed event arrived (a replayed song start plays the music that much later).
  void _onEvent(List<int> data, {Duration? age}) {
    if (_disposed || data.isEmpty) return;
    final replay = age != null;
    switch (data[0]) {
      case BleEvent.game:
        if (data.length >= 3 && data[1] == BleEvent.gameState) {
          _onGameState(data[2]);
        } else if (data.length >= 3 && data[1] == BleEvent.gameSelected) {
          _openOnBoard = data[2] == BleGameId.pocketGuitar;
          if (!_openOnBoard) {
            unawaited(_stopMusic());
            if (launch == GameLaunch.app) song = null;
            if (phase == PocketGuitarPhase.result) {
              _set(PocketGuitarPhase.closed); // the result stays on screen
            } else {
              _set(PocketGuitarPhase.error, 'Pocket Guitar was closed on the board.');
            }
          } else if (launch == GameLaunch.board &&
              (phase == PocketGuitarPhase.error || phase == PocketGuitarPhase.closed)) {
            result = null; // opened again on the board
            _set(PocketGuitarPhase.ready);
          }
        }
        break;
      case BleEvent.songSelection:
        if (data.length >= 11) _onSongSelection(data);
        break;
      case BleEvent.songStart:
        if (data.length >= 12) _onSongStart(data, age ?? Duration.zero);
        break;
      case BleEvent.noteResult:
        if (data.length >= 9) {
          multiplier = data[4];
          score = _u32(data, 5);
          if (phase == PocketGuitarPhase.countIn) phase = PocketGuitarPhase.playing; // Practice has no music timer
          if (data[3] == _gradeMiss && !replay) _onMistake();
          notifyListeners();
        }
        break;
      case BleEvent.overstrum:
        if (data.length >= 5) {
          score = _u32(data, 1);
          multiplier = 1;
          if (!replay) _onMistake();
          notifyListeners();
        }
        break;
      case BleEvent.songResult:
        if (data.length >= 10) {
          result = PocketGuitarResult(
            score: _u32(data, 1),
            stars: data[5],
            accuracy: data[6],
            bestStreak: data[7] | (data[8] << 8),
            newBest: data[9] & 1 != 0,
            flawless: data[9] & 2 != 0,
          );
          score = result!.score;
          _set(PocketGuitarPhase.result);
        }
        break;
      case BleEvent.error:
        if (data.length >= 3 && data[2] == BleStream.pocketGuitarSong && phase == PocketGuitarPhase.uploading) {
          _set(PocketGuitarPhase.error,
              'The board did not take the song. Quit the running song on the board, then try again.');
        }
        break;
    }
  }

  void _onGameState(int state) {
    if (!_openOnBoard) return; // another game's state
    switch (state) {
      case BleGameState.paused:
        _startTimer?.cancel();
        _playToken++;
        unawaited(_player.pause());
        _set(PocketGuitarPhase.paused);
        break;
      case BleGameState.over:
      case BleGameState.ready:
        // Quit (over) or back on the select screen: only matters while a song runs
        if (isRunning) {
          unawaited(_stopMusic());
          _set(PocketGuitarPhase.ready);
        }
        break;
    }
  }

  void _onSongSelection(List<int> data) {
    difficulty = data[3];
    availableDifficulties = data[4];
    mode = data[5];
    bestStars = data[6];
    bestScore = _u32(data, 7);
    if (data[1] != appSongSlot) {
      song = null; // a song stored on the board was picked on the pads
    }
    if (launch == GameLaunch.board) {
      // Following the board: its own songs are normal here, they just have no music in the app
      notifyListeners();
    } else if (phase == PocketGuitarPhase.uploading || phase == PocketGuitarPhase.error) {
      _set(song != null ? PocketGuitarPhase.ready : PocketGuitarPhase.error,
          song != null ? null : 'A song stored on the board is selected, it has no music in the app.');
    } else {
      notifyListeners();
    }
  }

  void _onSongStart(List<int> data, Duration age) {
    final sinceEvent = Stopwatch()..start();
    final ageMs = age.inMilliseconds;
    final slot = data[1];
    difficulty = data[2];
    mode = data[3];
    final startMs = _i32(data, 6);
    score = 0;
    multiplier = 1;
    result = null;
    _set(startMs < 0 ? PocketGuitarPhase.countIn : PocketGuitarPhase.playing);

    if (slot == appSongSlot && song != null && mode == modePlay) {
      unawaited(_playFrom(startMs, sinceEvent, ageMs));
    } else {
      unawaited(_stopMusic());
    }
  }

  void _onBoardLost() {
    unawaited(_stopMusic());
    _set(PocketGuitarPhase.noBoard);
  }

  // ==============================================================================================
  // Music
  // ==============================================================================================

  /// Plays the music so that song position [startMs] is heard at the time of the song start event, which
  /// arrived [ageMs] before [sinceEvent] started.
  Future<void> _playFrom(int startMs, Stopwatch sinceEvent, [int ageMs = 0]) async {
    final token = ++_playToken;
    _startTimer?.cancel();
    final leadMs = startMs < 0 ? -startMs : _resumeLeadMs;
    final positionMs = startMs + leadMs; // 0 for a new song, just after the pause point for a resume
    try {
      await _player.pause();
      await _player.setVolume(1);
      await _player.seek(Duration(milliseconds: positionMs));
    } catch (e) {
      debugPrint('[PocketGuitar] Seek failed: $e');
    }
    if (token != _playToken || _disposed) return;
    final waitMs = max(0, leadMs - ageMs - sinceEvent.elapsedMilliseconds);
    _startTimer = Timer(Duration(milliseconds: waitMs), () {
      if (token != _playToken || _disposed) return;
      unawaited(_player.resume());
      if (phase == PocketGuitarPhase.countIn) _set(PocketGuitarPhase.playing);
    });
  }

  Future<void> _stopMusic() async {
    _startTimer?.cancel();
    _duckTimer?.cancel();
    _playToken++;
    try {
      await _player.stop();
    } catch (e) {
      debugPrint('[PocketGuitar] Stop failed: $e');
    }
  }

  /// Miss or overstrum: a thump, and the music dips for a moment (like the guitar cutting out).
  void _onMistake() {
    unawaited(SoundCache.instance.play(_missSound));
    if (phase != PocketGuitarPhase.playing || mode != modePlay) return;
    _duckTimer?.cancel();
    unawaited(_player.setVolume(_missVolume));
    _duckTimer = Timer(_missDuck, () {
      if (!_disposed) unawaited(_player.setVolume(1));
    });
  }

  void _set(PocketGuitarPhase next, [String? text]) {
    phase = next;
    message = text;
    if (!_disposed) notifyListeners();
  }

  static int _u32(List<int> d, int i) => d[i] | (d[i + 1] << 8) | (d[i + 2] << 16) | (d[i + 3] << 24);

  static int _i32(List<int> d, int i) {
    final value = _u32(d, i);
    return value >= 0x80000000 ? value - 0x100000000 : value;
  }
}
