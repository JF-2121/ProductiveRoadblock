import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/piano_tiles_song.dart';
import '../services/piano_tiles_highscore.dart';
import '../services/sound_cache.dart';
import 'square_tile_grid.dart';

/// Piano Tiles deliberately runs on just a handful of sounds — one per lane
/// for a hit, one shared sound for a miss — so the feedback stays instantly
/// readable instead of turning into a soundboard. The hit sounds are a
/// synthesized C major arpeggio (C4, E4, G4, C5), ascending left to right,
/// one per lane (see sound_clip.dart).
const List<String> _laneTapSounds = ['piano_c4', 'piano_e4', 'piano_g4', 'piano_c5'];
const String _wrongTapSound = 'buzz';

class PianoTilesGame extends StatefulWidget {
  const PianoTilesGame({
    super.key,
    this.targetTapCount,
    this.onGameWin,
    this.onInteraction,
    this.enabled = true,
    this.autoRestartOnWin = false,
    this.song,
  });

  final int? targetTapCount;
  final VoidCallback? onGameWin;

  /// Fired on every tap (right or wrong) so a wrapping widget can tell
  /// whether the player is actively engaged right now.
  final VoidCallback? onInteraction;
  final bool enabled;
  final bool autoRestartOnWin;

  /// When set, the tile pattern follows this song's lanes instead of being
  /// randomly generated (mobile-app#11). Falls back to random once the
  /// song's pattern is exhausted.
  final PianoTilesSong? song;

  @override
  State<PianoTilesGame> createState() => _PianoTilesGameState();
}

class _PianoTilesGameState extends State<PianoTilesGame> {
  static const int _columnCount = 4;
  // 8 rows = two stacked 4x4 boards (32 tiles), matching SimonSaysGame's
  // 2x4x4 layout.
  static const int _rowCount = 8;
  static const int _tileCount = _columnCount * _rowCount;

  final Random _random = Random();
  late final int _targetTaps;
  late List<int> _targetLanesByRow;
  int _songCursor = 0;

  Timer? _feedbackTimer;
  int? _lastCorrectTileIndex;
  int? _lastWrongTileIndex;
  int _currentTaps = 0;
  bool _isCompleted = false;

  @override
  void initState() {
    super.initState();
    _targetTaps = widget.targetTapCount ??
        widget.song?.pattern.length ??
        (_random.nextInt(6) + 5);
    _targetLanesByRow = _buildPattern();
  }

  @override
  void dispose() {
    _feedbackTimer?.cancel();
    super.dispose();
  }

  void _handleTap(int tileIndex) {
    if (!widget.enabled || _isCompleted) return;
    widget.onInteraction?.call();

    final row = tileIndex ~/ _columnCount;
    final lane = tileIndex % _columnCount;
    final isTarget = _targetLanesByRow[row] == lane;
    _feedbackTimer?.cancel();

    if (!isTarget) {
      HapticFeedback.heavyImpact();
      unawaited(SoundCache.instance.play(_wrongTapSound));
      PianoTilesHighscore.instance.recordMiss();
      setState(() {
        _lastWrongTileIndex = tileIndex;
        _lastCorrectTileIndex = null;
      });
      _feedbackTimer = Timer(const Duration(milliseconds: 150), () {
        if (!mounted) return;
        setState(() => _lastWrongTileIndex = null);
      });
      return;
    }

    HapticFeedback.lightImpact();
    unawaited(SoundCache.instance.play(_laneTapSounds[lane]));
    PianoTilesHighscore.instance.recordHit();
    final nextTaps = _currentTaps + 1;
    setState(() {
      _currentTaps = nextTaps;
      _lastCorrectTileIndex = tileIndex;
      _lastWrongTileIndex = null;
    });

    if (nextTaps >= _targetTaps) {
      _isCompleted = !widget.autoRestartOnWin;
      widget.onGameWin?.call();
      if (widget.autoRestartOnWin) {
        setState(() {
          _currentTaps = 0;
          _lastCorrectTileIndex = null;
          _lastWrongTileIndex = null;
          _targetLanesByRow = _buildPattern();
        });
      }
      return;
    }

    _feedbackTimer = Timer(const Duration(milliseconds: 120), () {
      if (!mounted || _isCompleted) return;
      setState(() {
        _lastCorrectTileIndex = null;
        _targetLanesByRow = _nextPattern(_targetLanesByRow);
      });
    });
  }

  List<int> _buildPattern() {
    return List<int>.generate(_rowCount, (_) => _nextLane());
  }

  List<int> _nextPattern(List<int> current) {
    final next = List<int>.from(current);
    next
      ..removeLast()
      ..insert(0, _nextLane());
    return next;
  }

  int _nextLane() {
    final song = widget.song;
    if (song != null && _songCursor < song.pattern.length) {
      final lane = song.pattern[_songCursor] % _columnCount;
      _songCursor++;
      return lane;
    }
    return _random.nextInt(_columnCount);
  }

  Color _tileColorFor(int index) {
    if (_lastWrongTileIndex == index) return Colors.redAccent;
    if (_lastCorrectTileIndex == index) return Colors.greenAccent;

    final row = index ~/ _columnCount;
    final lane = index % _columnCount;
    final isTarget = _targetLanesByRow[row] == lane;
    return isTarget ? Colors.black87 : Colors.white;
  }

  @override
  Widget build(BuildContext context) {
    // No score or round counter: progress is measured purely by the play
    // clock in the parent screen, which mirrors the Instagram time earned.
    return Column(
      children: [
        // A single seamless 4-wide x 8-tall grid (two stacked 4x4 boards),
        // sized/scrolled by [SquareTileGrid].
        Expanded(
          child: SquareTileGrid(
            itemCount: _tileCount,
            columns: _columnCount,
            itemBuilder: (context, index) {
              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => _handleTap(index),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 100),
                  decoration: BoxDecoration(
                    color: _tileColorFor(index),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.black26),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

typedef TappingGame = PianoTilesGame;
