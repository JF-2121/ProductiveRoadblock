import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/notification_service.dart';
import '../state/play_time.dart';
import '../state/session_manager.dart';
import '../widgets/game_ui.dart';

/// Debug screen for testing session and notification behavior
class DebugScreen extends ConsumerStatefulWidget {
  const DebugScreen({super.key});

  @override
  ConsumerState<DebugScreen> createState() => _DebugScreenState();
}

class _DebugScreenState extends ConsumerState<DebugScreen> {
  @override
  Widget build(BuildContext context) {
    final sessionState = ref.watch(sessionManagerProvider);
    final lastRun = ref.watch(playTimeProvider.select((p) => p.lastRun));
    final multiplier = sessionState.playTimeMultiplier;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Debug Controls'),
        backgroundColor: Colors.deepPurple,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Session Status Card
            _buildCard(
              title: 'Session Status',
              color: sessionState.isUnlocked ? Colors.green : Colors.red,
              children: [
                _buildInfoRow(
                  'Status',
                  sessionState.isUnlocked ? 'UNLOCKED' : 'LOCKED',
                  sessionState.isUnlocked ? Colors.green : Colors.red,
                ),
                if (sessionState.isUnlocked)
                  _buildInfoRow(
                    'Remaining Time',
                    _formatDuration(sessionState.remainingTime),
                    Colors.blue,
                  ),
              ],
            ),
            const SizedBox(height: 16),

            // Play time -> Instagram time
            _buildCard(
              title: 'Play Time Multiplier',
              color: Colors.teal,
              children: [
                _buildInfoRow(
                  'Instagram time per second played',
                  '${formatMultiplier(multiplier)}  (20 s → ${formatClock(Duration(milliseconds: (20000 * multiplier).round()))})',
                  Colors.teal,
                ),
                Slider(
                  value: multiplier.clamp(0.25, 5.0),
                  min: 0.25,
                  max: 5.0,
                  divisions: 19,
                  label: formatMultiplier(multiplier),
                  onChanged: (value) {
                    ref.read(sessionManagerProvider.notifier).setPlayTimeMultiplier(value);
                  },
                ),
                if (lastRun != null)
                  _buildInfoRow(
                    'Last run',
                    'played ${formatClock(lastRun.played)} ${formatMultiplier(lastRun.multiplier)} = +${formatClock(lastRun.earned)}',
                    Colors.white70,
                  ),
              ],
            ),
            const SizedBox(height: 16),

            // Notification Test
            _buildCard(
              title: 'Notification Test',
              color: Colors.orange,
              children: [
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: () async {
                    final messenger = ScaffoldMessenger.of(context);
                    try {
                      await NotificationService.instance
                          .showInstagramBlockedNotification();
                      messenger.showSnackBar(
                        const SnackBar(
                          content: Text('✅ Notification sent'),
                          backgroundColor: Colors.green,
                        ),
                      );
                    } catch (e) {
                      debugPrint('[DebugScreen] Notification error: $e');
                      messenger.showSnackBar(
                        SnackBar(
                          content: Text('❌ Error: $e'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  },
                  icon: const Icon(Icons.notifications_active),
                  label: const Text('Test Instagram Blocked Notification'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.orange,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.all(16),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Pocket Guitar (normally hidden on the home screen without a
            // live board connection - this reaches it anyway, for visual
            // inspection. It shows its "no board" state gracefully.)
            _buildCard(
              title: 'Pocket Guitar',
              color: Colors.redAccent,
              children: [
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pushNamed(context, '/pocket-guitar');
                  },
                  icon: const Icon(Icons.music_note),
                  label: const Text('OPEN (no board needed)'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.redAccent,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.all(16),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Session Controls
            _buildCard(
              title: 'Session Controls',
              color: Colors.indigo,
              children: [
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: sessionState.isUnlocked
                      ? null
                      : () {
                          ref.read(sessionManagerProvider.notifier).unlockSession();
                        },
                  icon: const Icon(Icons.lock_open),
                  label: const Text('Unlock Session (3 min)'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    padding: const EdgeInsets.all(16),
                  ),
                ),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: !sessionState.isUnlocked
                      ? null
                      : () {
                          ref.read(sessionManagerProvider.notifier).lockSession();
                        },
                  icon: const Icon(Icons.lock),
                  label: const Text('Lock Session'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    padding: const EdgeInsets.all(16),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCard({
    required String title,
    required Color color,
    required List<Widget> children,
  }) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: color,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
              ),
            ),
            child: Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: children,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Flexible(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: color.withValues(alpha: 0.3)),
            ),
            child: Text(
              value,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes;
    final seconds = duration.inSeconds % 60;
    return '${minutes}m ${seconds}s';
  }
}
