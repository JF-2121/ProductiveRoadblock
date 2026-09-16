import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Tracks the longest run of correct Piano Tiles taps without a miss, across
/// both the roadblock challenge and Freeplay (one shared highscore). A miss
/// resets the current streak to zero; the best streak persists forever via
/// SharedPreferences.
///
/// Piano Tiles itself never shows a score or round counter during play (by
/// design - see tapping_game.dart), so this only surfaces outside the game
/// grid: the current streak while playing, and the best streak on the menu.
class PianoTilesHighscore {
  PianoTilesHighscore._();
  static final PianoTilesHighscore instance = PianoTilesHighscore._();

  static const String _bestStreakKey = 'piano_tiles_best_streak';

  /// Longest streak ever recorded. Starts at 0 until [load] resolves.
  final ValueNotifier<int> best = ValueNotifier<int>(0);

  /// Current unbroken streak, live during play.
  final ValueNotifier<int> current = ValueNotifier<int>(0);

  bool _loaded = false;

  Future<void> load() async {
    if (_loaded) return;
    _loaded = true;
    final prefs = await SharedPreferences.getInstance();
    best.value = prefs.getInt(_bestStreakKey) ?? 0;
  }

  /// Call on every correct tap.
  void recordHit() {
    current.value++;
    if (current.value > best.value) {
      best.value = current.value;
      unawaited(_persistBest(current.value));
    }
  }

  /// Call on every wrong tap - breaks the current streak.
  void recordMiss() {
    current.value = 0;
  }

  Future<void> _persistBest(int value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_bestStreakKey, value);
  }
}
