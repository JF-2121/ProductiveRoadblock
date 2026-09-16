import 'dart:async';
import 'dart:math';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';

import '../models/piano_tiles_track.dart';

/// Plays a Piano Tiles recording in step with the tapped tiles.
///
/// Tile k lets the music play from its start to the start of tile k + 1 ([PianoTilesTrack.tileMs]). Tap steadily
/// and the music flows; stop tapping and it fades out just after the allowed part (tiles start just before a
/// note, so it stops between notes); the next tap starts that tile's note again. The playback rate follows the
/// tapping tempo within [minRate]..[maxRate] (the pitch stays), with a small correction that keeps about half
/// a tile of music in hand. Far ahead of the music, it jumps to the tapped tile. Tile numbers past the end wrap
/// around, so Zen and Arcade loop the song.
class TapFollowPlayer {
  TapFollowPlayer({AudioPlayer? player, int Function()? nowMs, this.autoTick = true})
      : _player = player ?? AudioPlayer(),
        _nowMs = nowMs ?? _monotonicMs;

  static final Stopwatch _stopwatch = Stopwatch()..start();
  static int _monotonicMs() => _stopwatch.elapsedMilliseconds;

  static const double minRate = 0.7;
  static const double maxRate = 2.0;

  /// Tiles of music still allowed when the next tap comes, in a steady flow.
  static const double _targetSlack = 0.5;
  static const double _tempoSmoothing = 0.35;
  static const double _slackCorrection = 0.2;
  static const double _minRateChange = 0.03;

  /// The music jumps to a tapped tile this many tiles ahead of it.
  static const int _catchUpTiles = 6;
  static const int _maxGraceMs = 150;
  static const Duration _tickInterval = Duration(milliseconds: 30);
  static const int _syncIntervalMs = 500;
  static const int _resyncThresholdMs = 40;
  static const List<double> _fadeVolumes = [0.6, 0.3];
  static const Duration _fadeStep = Duration(milliseconds: 30);

  final AudioPlayer _player;
  final int Function() _nowMs;

  /// Runs [tick] on a timer while playing (tests call it themselves).
  final bool autoTick;

  PianoTilesTrack? _track;
  bool _playing = false;
  bool _fading = false;
  bool _disposed = false;
  int _allowedUntilMs = 0;
  double _rate = 1.0;
  double _tempo = 1.0;
  int? _lastTapAtMs;
  int _lastTapTileMs = 0;

  // Position estimate: _anchorPosMs at _anchorAtMs, moving with _rate while playing
  int _anchorPosMs = 0;
  int _anchorAtMs = 0;
  int _lastSyncAtMs = 0;

  /// Invalidates pending fades and starts.
  int _token = 0;
  Timer? _ticker;
  Timer? _fadeTimer;

  PianoTilesTrack? get track => _track;
  bool get isPlaying => _playing;
  double get rate => _rate;
  int get allowedUntilMs => _allowedUntilMs;

  int get positionMs =>
      _playing ? _anchorPosMs + ((_nowMs() - _anchorAtMs) * _rate).round() : _anchorPosMs;

  double get _avgTileMs {
    final track = _track!;
    return max(1, track.endMs - track.tileMs.first) / track.tileMs.length;
  }

  /// Loads a song (with its chart, see [PianoTilesTrack.loadChart]); the music waits for the first tile.
  Future<void> load(PianoTilesTrack track) async {
    stop();
    _track = track;
    _anchorPosMs = track.tileMs.isEmpty ? 0 : track.tileMs.first;
    try {
      await _player.setReleaseMode(ReleaseMode.stop);
      await _player.setSource(AssetSource(track.audioSourcePath));
    } catch (e) {
      debugPrint('[TapFollowPlayer] Could not load ${track.audioAsset}: $e');
    }
  }

  /// Tile [index] of the run was tapped.
  void tile(int index) {
    final track = _track;
    if (track == null || track.tileMs.isEmpty || _disposed) return;
    final tiles = track.tileMs;
    final k = index % tiles.length;
    final start = tiles[k];
    final end = k + 1 < tiles.length ? tiles[k + 1] : track.endMs;
    final now = _nowMs();

    // Tapping tempo: how fast the tapped tiles went compared to the recording
    final lastTap = _lastTapAtMs;
    if (lastTap != null) {
      final interval = now - lastTap;
      if (interval > 0 && interval < 3 * _lastTapTileMs) {
        final ratio = (_lastTapTileMs / interval).clamp(minRate, maxRate);
        _tempo += _tempoSmoothing * (ratio - _tempo);
      }
    }
    _lastTapAtMs = now;
    _lastTapTileMs = end - start;

    if (!_playing) {
      // The music waited for this tap: a bit slower, unless it's the first tap of a run
      _allowedUntilMs = end;
      _setRate(lastTap == null ? _tempo : _tempo * (1 - _slackCorrection * _targetSlack));
      _startFrom(start);
      return;
    }

    final position = positionMs;
    if (start > position + _catchUpTiles * _avgTileMs || start + _avgTileMs < position) {
      // Far ahead of the music, or behind it because the song started over: go to the tapped tile
      _cancelFade();
      _allowedUntilMs = end;
      _anchorPosMs = start;
      _anchorAtMs = now;
      unawaited(_guard(() => _player.seek(Duration(milliseconds: start))));
      return;
    }

    final slack = (_allowedUntilMs - position) / _avgTileMs;
    _allowedUntilMs = max(_allowedUntilMs, end);
    _cancelFade();
    final correction = (1 + _slackCorrection * (slack - _targetSlack)).clamp(0.8, 1.25);
    _setRate(_tempo * correction);
  }

  /// Board paused: fade out and keep the place.
  void hold() {
    _lastTapAtMs = null;
    if (_playing && !_fading) _fadeOutAndPause();
  }

  /// Mistake, quit or a new run: fade out, back to the first tile at normal speed.
  void stop() {
    _lastTapAtMs = null;
    _allowedUntilMs = 0;
    _tempo = 1.0;
    if (_playing && !_fading) _fadeOutAndPause();
    if (_rate != 1.0) {
      _rate = 1.0;
      unawaited(_guard(() => _player.setPlaybackRate(1.0)));
    }
  }

  void dispose() {
    _disposed = true;
    _token++;
    _ticker?.cancel();
    _fadeTimer?.cancel();
    unawaited(_guard(_player.dispose));
  }

  /// Checks whether the music has to stop, and keeps the position estimate in sync. Runs every 30 ms while
  /// playing (called directly in tests).
  @visibleForTesting
  void tick() {
    final track = _track;
    if (!_playing || _fading || track == null || _disposed) return;
    final now = _nowMs();
    final position = positionMs;
    final grace = min(_maxGraceMs, (0.35 * _avgTileMs).round());
    if (position >= _allowedUntilMs + grace || position >= track.lengthMs) {
      _fadeOutAndPause();
      return;
    }
    if (now - _lastSyncAtMs >= _syncIntervalMs) {
      _lastSyncAtMs = now;
      unawaited(_sync());
    }
  }

  void _startFrom(int ms) {
    final token = ++_token;
    _fadeTimer?.cancel();
    _playing = true;
    _fading = false;
    _anchorPosMs = ms;
    _anchorAtMs = _lastSyncAtMs = _nowMs();
    if (autoTick) _ticker ??= Timer.periodic(_tickInterval, (_) => tick());
    unawaited(_guard(() async {
      await _player.setVolume(1);
      await _player.seek(Duration(milliseconds: ms));
      if (token != _token || _disposed) return;
      // The music starts now, after the seek
      _anchorPosMs = ms;
      _anchorAtMs = _lastSyncAtMs = _nowMs();
      await _player.resume();
    }));
  }

  void _fadeOutAndPause() {
    _fading = true;
    final token = ++_token;
    var step = 0;
    void next() {
      if (token != _token || _disposed) return;
      if (step < _fadeVolumes.length) {
        unawaited(_guard(() => _player.setVolume(_fadeVolumes[step++])));
        _fadeTimer = Timer(_fadeStep, next);
        return;
      }
      _anchorPosMs = positionMs;
      _anchorAtMs = _nowMs();
      _playing = false;
      _fading = false;
      _ticker?.cancel();
      _ticker = null;
      unawaited(_guard(_player.pause));
    }

    next();
  }

  void _cancelFade() {
    if (!_fading) return;
    _token++;
    _fadeTimer?.cancel();
    _fading = false;
    unawaited(_guard(() => _player.setVolume(1)));
  }

  void _setRate(double value) {
    final next = value.clamp(minRate, maxRate);
    if ((next - _rate).abs() < _minRateChange) return;
    _anchorPosMs = positionMs;
    _anchorAtMs = _nowMs();
    _rate = next;
    unawaited(_guard(() => _player.setPlaybackRate(next)));
  }

  Future<void> _sync() async {
    final token = _token;
    final before = _nowMs();
    final actual = await _guard(_player.getCurrentPosition);
    if (actual == null || token != _token || !_playing || _fading || _disposed) return;
    final now = _nowMs();
    final measured = actual.inMilliseconds + ((now - before) * _rate / 2).round();
    if ((measured - positionMs).abs() > _resyncThresholdMs) {
      _anchorPosMs = measured;
      _anchorAtMs = now;
    }
  }

  Future<T?> _guard<T>(Future<T> Function() action) async {
    try {
      return await action();
    } catch (e) {
      debugPrint('[TapFollowPlayer] $e');
      return null;
    }
  }
}
