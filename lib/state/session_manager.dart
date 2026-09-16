import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/notification_service.dart';

/// How long the dev unlock lasts. A normal unlock lasts exactly as long as the play time that bought it.
const Duration kSessionDuration = Duration(minutes: 3);

/// Instagram time per second of play unless changed in Debug Controls: 20 s of play buy 20 s.
const double kDefaultPlayTimeMultiplier = 1.0;

class SessionState {
  const SessionState({
    required this.isUnlocked,
    required this.remainingTime,
    this.playTimeMultiplier = kDefaultPlayTimeMultiplier,
  });

  const SessionState.locked()
    : isUnlocked = false,
      remainingTime = Duration.zero,
      playTimeMultiplier = kDefaultPlayTimeMultiplier;

  final bool isUnlocked;

  /// Instagram time left while unlocked.
  final Duration remainingTime;

  /// Instagram time earned per second of play, e.g. 2.0: 20 s of play unlock 40 s.
  final double playTimeMultiplier;

  SessionState copyWith({
    bool? isUnlocked,
    Duration? remainingTime,
    double? playTimeMultiplier,
  }) {
    return SessionState(
      isUnlocked: isUnlocked ?? this.isUnlocked,
      remainingTime: remainingTime ?? this.remainingTime,
      playTimeMultiplier: playTimeMultiplier ?? this.playTimeMultiplier,
    );
  }
}

class SessionManager extends Notifier<SessionState> {
  static const String _unlockedUntilKey = 'unlocked_until_millis';
  static const String _multiplierKey = 'play_time_multiplier';
  Timer? sessionTimer;

  @override
  SessionState build() {
    ref.onDispose(() {
      sessionTimer?.cancel();
    });

    // The app is frequently killed and relaunched by the iOS Shortcuts
    // automation (every time Instagram is opened). Without restoring from
    // disk, a fresh process would start locked even with Instagram time left.
    unawaited(_restoreSession());

    return const SessionState.locked();
  }

  Future<void> _restoreSession() async {
    final prefs = await SharedPreferences.getInstance();

    final multiplier = prefs.getDouble(_multiplierKey);
    if (multiplier != null) {
      state = state.copyWith(playTimeMultiplier: multiplier);
    }

    final unlockedUntilMillis = prefs.getInt(_unlockedUntilKey);
    if (unlockedUntilMillis == null || state.isUnlocked) return;

    final remaining = DateTime.fromMillisecondsSinceEpoch(
      unlockedUntilMillis,
    ).difference(DateTime.now());

    if (remaining <= Duration.zero) {
      await prefs.remove(_unlockedUntilKey);
      return;
    }

    _startCountdown(remaining);
  }

  /// Dev unlock: a fixed window without playing.
  void unlockSession() {
    _startCountdown(kSessionDuration);
    unawaited(_persistUnlockedUntil(DateTime.now().add(kSessionDuration)));
  }

  /// Turns play time into Instagram time: played × [SessionState.playTimeMultiplier], in whole seconds.
  /// While locked this unlocks for exactly the earned time, while unlocked it is added to the time left.
  /// Returns the earned time.
  Duration creditPlayTime(Duration played) {
    final earnedSeconds = (played.inMilliseconds * state.playTimeMultiplier / 1000).round();
    if (earnedSeconds <= 0) return Duration.zero;
    final earned = Duration(seconds: earnedSeconds);

    final Duration total;
    if (state.isUnlocked && sessionTimer != null) {
      total = state.remainingTime + earned;
      state = state.copyWith(remainingTime: total);
    } else {
      total = earned;
      _startCountdown(total);
    }
    unawaited(_persistUnlockedUntil(DateTime.now().add(total)));
    return earned;
  }

  Future<void> setPlayTimeMultiplier(double multiplier) async {
    state = state.copyWith(playTimeMultiplier: multiplier);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_multiplierKey, multiplier);
  }

  void _startCountdown(Duration duration) {
    sessionTimer?.cancel();
    state = state.copyWith(isUnlocked: true, remainingTime: duration);

    sessionTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      final nextTime = state.remainingTime - const Duration(seconds: 1);
      if (nextTime <= Duration.zero) {
        lockSession();
        return;
      }
      state = state.copyWith(remainingTime: nextTime);
    });
  }

  void lockSession() {
    final wasUnlocked = state.isUnlocked;
    sessionTimer?.cancel();
    sessionTimer = null;
    state = state.copyWith(isUnlocked: false, remainingTime: Duration.zero);
    unawaited(_clearPersistedSession());

    if (wasUnlocked) {
      unawaited(
        NotificationService.instance.showNotification(
          "Time for Roadblock! Focus needed.",
        ),
      );
    }
  }

  Future<void> _persistUnlockedUntil(DateTime unlockedUntil) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_unlockedUntilKey, unlockedUntil.millisecondsSinceEpoch);
  }

  Future<void> _clearPersistedSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_unlockedUntilKey);
  }
}

final sessionManagerProvider = NotifierProvider<SessionManager, SessionState>(
  SessionManager.new,
);
