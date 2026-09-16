import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/play_time.dart';
import '../state/session_manager.dart';

/// `mm:ss`, or `h:mm:ss` from one hour.
String formatClock(Duration duration) {
  final seconds = duration.inSeconds;
  final mmss = '${(seconds ~/ 60 % 60).toString().padLeft(2, '0')}:${(seconds % 60).toString().padLeft(2, '0')}';
  return seconds >= 3600 ? '${seconds ~/ 3600}:$mmss' : mmss;
}

/// `×1`, `×1.5`, `×0.25`.
String formatMultiplier(double multiplier) {
  final text = multiplier.toStringAsFixed(2).replaceFirst(RegExp(r'\.?0+$'), '');
  return '×$text';
}

/// Top row of a game screen: back to the menu, the game's name and, while a run is counted, its play time.
class GameHeader extends StatelessWidget {
  const GameHeader({super.key, required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton(
          icon: const Icon(Icons.arrow_back, size: 20),
          color: Colors.white.withValues(alpha: 0.5),
          tooltip: 'Back to the games',
          onPressed: () => Navigator.maybePop(context),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            title,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 13, letterSpacing: 3, fontWeight: FontWeight.w600, color: Colors.white70),
          ),
        ),
        const PlayTimeBadge(),
      ],
    );
  }
}

/// While a run is counted: its play time and the Instagram time it buys, e.g. `0:42 → +1:24`.
class PlayTimeBadge extends ConsumerWidget {
  const PlayTimeBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final play = ref.watch(playTimeProvider);
    if (!play.running) return const SizedBox.shrink();
    final multiplier = ref.watch(sessionManagerProvider.select((s) => s.playTimeMultiplier));
    final earned = Duration(milliseconds: (play.played.inMilliseconds * multiplier).round());
    final color = play.paused ? Colors.white38 : Colors.greenAccent;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(play.paused ? Icons.pause : Icons.timer_outlined, size: 14, color: color),
          const SizedBox(width: 6),
          Text(
            '${formatClock(play.played)} → +${formatClock(earned)}',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color, fontFeatures: const [FontFeature.tabularFigures()]),
          ),
        ],
      ),
    );
  }
}

/// The big line of a game screen: the phase or the score, with a smaller explanation below.
class BigStatus extends StatelessWidget {
  const BigStatus(this.big, this.small, {super.key, this.color = Colors.white});

  final String big;
  final String small;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          big,
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 40, fontWeight: FontWeight.w700, letterSpacing: 2, color: color),
        ),
        Text(small, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white54)),
      ],
    );
  }
}

class GameButton extends StatelessWidget {
  const GameButton(this.label, this.icon, this.color, this.onPressed, {super.key});

  final String label;
  final IconData icon;
  final Color color;
  final Future<void> Function()? onPressed;

  @override
  Widget build(BuildContext context) {
    final action = onPressed;
    return ElevatedButton.icon(
      onPressed: action == null
          ? null
          : () {
              HapticFeedback.mediumImpact();
              action();
            },
      icon: Icon(icon),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    );
  }
}

/// Mode selection of a game, e.g. Simple / Endless.
class ModeChips extends StatelessWidget {
  const ModeChips({
    super.key,
    required this.names,
    required this.selected,
    required this.onSelected,
    this.enabled = true,
    this.color = Colors.white,
  });

  final List<String> names;
  final int selected;
  final bool enabled;
  final Color color;
  final Future<void> Function(int mode) onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 8,
      children: [
        for (var mode = 0; mode < names.length; mode++)
          ChoiceChip(
            label: Text(names[mode]),
            selected: selected == mode,
            selectedColor: color.withValues(alpha: 0.35),
            onSelected: enabled
                ? (_) {
                    HapticFeedback.selectionClick();
                    onSelected(mode);
                  }
                : null,
          ),
      ],
    );
  }
}

/// After a run of [gameId] that ended after [since]: the play time, what it earned and the Instagram time now.
class EarnedTimeCard extends ConsumerWidget {
  const EarnedTimeCard({super.key, required this.gameId, required this.since});

  final int gameId;
  final DateTime since;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final play = ref.watch(playTimeProvider);
    final run = play.lastRun;
    if (play.running || run == null || run.gameId != gameId || run.endedAt.isBefore(since)) {
      return const SizedBox.shrink();
    }
    final session = ref.watch(sessionManagerProvider);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.greenAccent.withValues(alpha: 0.08),
        border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.35)),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        children: [
          Text(
            'PLAYED ${formatClock(run.played)}  ${formatMultiplier(run.multiplier)}  =  +${formatClock(run.earned)}',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13, letterSpacing: 1.5, fontWeight: FontWeight.w600, color: Colors.greenAccent),
          ),
          const SizedBox(height: 10),
          const Text('YOUR INSTAGRAM TIME', style: TextStyle(fontSize: 11, letterSpacing: 2, color: Colors.white54)),
          Text(
            session.isUnlocked ? formatClock(session.remainingTime) : '00:00',
            style: const TextStyle(
              fontSize: 44,
              fontWeight: FontWeight.w700,
              color: Colors.white,
              fontFeatures: [FontFeature.tabularFigures()],
            ),
          ),
          if (run.earned == Duration.zero)
            const Text('Play longer to earn Instagram time.', style: TextStyle(color: Colors.white38)),
        ],
      ),
    );
  }
}

/// Shown instead of a game while the board isn't connected.
class NoBoardHint extends StatelessWidget {
  const NoBoardHint({super.key, required this.game});

  final String game;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.bluetooth_disabled, size: 56, color: Colors.white38),
          const SizedBox(height: 16),
          const Text(
            'CONNECT THE BOARD',
            style: TextStyle(fontSize: 15, letterSpacing: 3, fontWeight: FontWeight.w600, color: Colors.white54),
          ),
          const SizedBox(height: 8),
          Text(
            '$game runs on the board.\nConnect it in the game menu.',
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.white38),
          ),
        ],
      ),
    );
  }
}
