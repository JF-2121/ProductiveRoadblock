import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/sound_clip.dart';
import '../services/sound_cache.dart';
import 'square_tile_grid.dart';

/// Reserved for a wrong tap, so it never doubles as a tile tone.
const String _wrongTapSound = 'buzz';

/// Simon-Says style pattern-repeat challenge spread across two separate 4x4
/// boards (32 tiles total): the app flashes a growing sequence of tiles,
/// then the player repeats it back in order. Randomly alternated with
/// [PianoTilesGame] as one of the two "Roadblock" minigame variants.
class SimonSaysGame extends StatefulWidget {
  const SimonSaysGame({
    super.key,
    this.targetTapCount,
    this.onGameWin,
    this.onInteraction,
    this.enabled = true,
    this.autoRestartOnWin = false,
  });

  final int? targetTapCount;
  final VoidCallback? onGameWin;

  /// Fired on every tap (right or wrong) so a wrapping widget can tell
  /// whether the player is actively engaged right now.
  final VoidCallback? onInteraction;
  final bool enabled;
  final bool autoRestartOnWin;

  @override
  State<SimonSaysGame> createState() => _SimonSaysGameState();
}

class _SimonSaysGameState extends State<SimonSaysGame> {
  static const int _columnsPerBoard = 4;
  static const int _rowsPerBoard = 4;
  static const int _tilesPerBoard = _columnsPerBoard * _rowsPerBoard;
  static const int _tileCount = _tilesPerBoard * 2;

  final Random _random = Random();
  late final int _targetLength;
  late final List<String> _tileSounds;
  final List<int> _sequence = [];

  int _inputIndex = 0;
  int? _highlightedTile;
  int? _correctTile;
  int? _wrongTile;
  bool _accepting = false;
  bool _isCompleted = false;
  Timer? _playbackTimer;
  Timer? _feedbackTimer;
  Timer? _correctFeedbackTimer;

  @override
  void initState() {
    super.initState();
    _targetLength = widget.targetTapCount ?? (_random.nextInt(4) + 5);
    // Shuffle a tone across every tile position so playback/taps ring out
    // with a wide variety of sounds instead of one fixed click. The buzzer
    // is held back so it only ever means "wrong".
    final tones = soundLibrary
        .map((clip) => clip.id)
        .where((id) => id != _wrongTapSound)
        .toList();
    _tileSounds = List<String>.generate(
      _tileCount,
      (i) => tones[i % tones.length],
    )..shuffle(_random);
    _sequence.add(_random.nextInt(_tileCount));
    _startPlayback();
  }

  @override
  void dispose() {
    _playbackTimer?.cancel();
    _feedbackTimer?.cancel();
    _correctFeedbackTimer?.cancel();
    super.dispose();
  }

  void _startPlayback() {
    _accepting = false;
    _inputIndex = 0;
    var step = 0;

    void showNext() {
      if (!mounted) return;
      if (step >= _sequence.length) {
        setState(() {
          _highlightedTile = null;
          _accepting = true;
        });
        return;
      }
      final tile = _sequence[step];
      setState(() => _highlightedTile = tile);
      unawaited(SoundCache.instance.play(_tileSounds[tile]));
      _playbackTimer = Timer(const Duration(milliseconds: 420), () {
        if (!mounted) return;
        setState(() => _highlightedTile = null);
        step++;
        _playbackTimer = Timer(const Duration(milliseconds: 180), showNext);
      });
    }

    // Deferred so the very first call (from initState) never invokes
    // setState before the initial build completes.
    _playbackTimer?.cancel();
    _playbackTimer = Timer(Duration.zero, showNext);
  }

  void _handleTap(int tile) {
    if (!widget.enabled || !_accepting || _isCompleted) return;
    widget.onInteraction?.call();

    if (_sequence[_inputIndex] != tile) {
      HapticFeedback.heavyImpact();
      unawaited(SoundCache.instance.play(_wrongTapSound));
      _accepting = false;
      setState(() => _wrongTile = tile);
      _feedbackTimer = Timer(const Duration(milliseconds: 400), () {
        if (!mounted) return;
        setState(() => _wrongTile = null);
        _startPlayback();
      });
      return;
    }

    HapticFeedback.lightImpact();
    unawaited(SoundCache.instance.play(_tileSounds[tile]));
    // Same green flash as watching the pattern, so a correct press reads
    // exactly like the cue it's matching.
    setState(() => _correctTile = tile);
    _correctFeedbackTimer?.cancel();
    _correctFeedbackTimer = Timer(const Duration(milliseconds: 120), () {
      if (!mounted) return;
      setState(() => _correctTile = null);
    });
    final nextInputIndex = _inputIndex + 1;
    setState(() => _inputIndex = nextInputIndex);

    if (nextInputIndex >= _sequence.length) {
      if (_sequence.length >= _targetLength) {
        unawaited(SoundCache.instance.play('chime'));
        _accepting = false;
        _isCompleted = !widget.autoRestartOnWin;
        widget.onGameWin?.call();
        if (widget.autoRestartOnWin) {
          setState(() {
            _sequence
              ..clear()
              ..add(_random.nextInt(_tileCount));
          });
          _startPlayback();
        }
        return;
      }
      _accepting = false;
      setState(() => _sequence.add(_random.nextInt(_tileCount)));
      _feedbackTimer = Timer(const Duration(milliseconds: 500), _startPlayback);
    }
  }

  Color _tileColorFor(int tile) {
    if (_wrongTile == tile) return Colors.redAccent;
    if (_highlightedTile == tile || _correctTile == tile) return Colors.greenAccent;
    // Both 4x4 halves share one base color so the board reads as a single
    // uniform surface.
    return Colors.white;
  }

  @override
  Widget build(BuildContext context) {
    // No round counter: progress is measured purely by the play clock in
    // the parent screen, which mirrors the Instagram time earned. The
    // watch/turn cue stays because you can't play the game without it.
    return Column(
      children: [
        Text(
          _accepting ? 'Your turn' : 'Watch closely…',
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
            color: Colors.white70,
          ),
        ),
        const SizedBox(height: 8),
        // A single seamless 4-wide x 8-tall grid (two stacked 4x4 boards with
        // no gap or divider between them), sized/scrolled by [SquareTileGrid].
        Expanded(
          child: SquareTileGrid(
            itemCount: _tileCount,
            columns: _columnsPerBoard,
            itemBuilder: (context, tile) {
              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => _handleTap(tile),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 100),
                  decoration: BoxDecoration(
                    color: _tileColorFor(tile),
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
