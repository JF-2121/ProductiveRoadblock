import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/board_games.dart';
import '../state/app_state.dart';
import '../state/play_time.dart';
import '../widgets/game_ui.dart';
import '../widgets/simon_says_game.dart';
import '../widgets/tapping_game.dart';

/// Play on phone: the fallback when no board is connected. Taps count as play (idle time earns nothing, see
/// [PlayTimeTracker.phoneActivity]); DONE ends the run and turns it into Instagram time like a board game.
///
/// Deliberately laid out like the game screens: a slim header row and then the board.
class FreeplayScreen extends ConsumerStatefulWidget {
  const FreeplayScreen({super.key});

  @override
  ConsumerState<FreeplayScreen> createState() => _FreeplayScreenState();
}

class _FreeplayScreenState extends ConsumerState<FreeplayScreen> {
  late final PlayTimeTracker _tracker;
  final DateTime _openedAt = DateTime.now();
  bool _done = false;
  int _round = 0;

  @override
  void initState() {
    super.initState();
    _tracker = ref.read(playTimeProvider.notifier)..attachScreen(phoneGameScreenId);
  }

  @override
  void dispose() {
    // Crediting changes providers, which isn't allowed while the widget tree is being torn down
    final tracker = _tracker;
    scheduleMicrotask(tracker.endPhoneRun);
    tracker.detachScreen(phoneGameScreenId);
    super.dispose();
  }

  void _finish() {
    _tracker.endPhoneRun();
    setState(() => _done = true);
  }

  void _playAgain() {
    ref.read(appProvider.notifier).resetLock();
    setState(() {
      _done = false;
      _round++;
    });
  }

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(appProvider);

    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const GameHeader(title: 'PLAY ON PHONE'),
              const SizedBox(height: 8),
              if (_done) ...[
                const Spacer(),
                EarnedTimeCard(gameId: phoneGameScreenId, since: _openedAt),
                const SizedBox(height: 20),
                GameButton('PLAY AGAIN', Icons.replay, Colors.white24, () async => _playAgain()),
                const Spacer(),
              ] else ...[
                const Text(
                  'Every second you keep tapping earns Instagram time.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 11, letterSpacing: 1, color: Colors.white38),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: appState.challengeType == ChallengeType.simonSays
                      ? SimonSaysGame(
                          key: ValueKey<String>('phone-${appState.roadblockSessionId}-$_round'),
                          targetTapCount: appState.targetTapCount,
                          autoRestartOnWin: true,
                          onInteraction: _tracker.phoneActivity,
                        )
                      : TappingGame(
                          key: ValueKey<String>('phone-${appState.roadblockSessionId}-$_round'),
                          targetTapCount: appState.targetTapCount,
                          autoRestartOnWin: true,
                          onInteraction: _tracker.phoneActivity,
                        ),
                ),
                const SizedBox(height: 8),
                GameButton('DONE', Icons.check, Colors.green, () async => _finish()),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
