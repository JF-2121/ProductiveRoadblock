import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/board_games.dart';
import '../services/ble_service.dart';
import '../services/notification_service.dart';
import '../state/app_state.dart';
import '../state/session_manager.dart';
import '../widgets/board_connect.dart';
import '../widgets/game_ui.dart';

/// Pick a game: Simon Says, Pocket Guitar or Piano Tiles on the board. Playing earns Instagram time (played time
/// × the multiplier from Debug Controls). Without a board, the on-phone game is offered instead.
///
/// [locked]: the lock screen (no way back, setup and dev tools in the menu); otherwise opened from Home.
class GameMenuScreen extends ConsumerWidget {
  const GameMenuScreen({super.key, this.locked = false});

  final bool locked;

  static const Color _simonColor = Color(0xFFFF00C8);
  static const Color _guitarColor = Color(0xFFFF3B30);
  static const Color _pianoColor = Color(0xFF0096FF);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bleState = ref.watch(appProvider.select((s) => s.bleState));
    final connected = bleState == BleConnectionState.connected;

    return PopScope(
      canPop: !locked,
      child: Scaffold(
        backgroundColor: Colors.black,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 4, 8),
            child: Column(
              children: [
                locked ? _lockedHeader(context, ref) : const GameHeader(title: 'PLAY GAMES'),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(4, 12, 12, 16),
                    children: [
                      const _InstagramTime(),
                      const SizedBox(height: 20),
                      _boardStatus(bleState),
                      const SizedBox(height: 20),
                      _GameCard(
                        title: 'Simon Says',
                        subtitle: 'Repeat the colour sequence · Simple or Endless',
                        icon: Icons.grid_view_rounded,
                        color: _simonColor,
                        enabled: connected,
                        onTap: () => _open(context, '/simon-says'),
                      ),
                      _GameCard(
                        title: 'Pocket Guitar',
                        subtitle: 'Guitar Hero on the board · pick a song and a difficulty',
                        icon: Icons.music_note,
                        color: _guitarColor,
                        enabled: connected,
                        onTap: () => _open(context, '/pocket-guitar'),
                      ),
                      _GameCard(
                        title: 'Piano Tiles',
                        subtitle: 'Your taps play the song · Classic, Zen or Arcade',
                        icon: Icons.piano,
                        color: _pianoColor,
                        enabled: connected,
                        onTap: () => _open(context, '/piano-tiles'),
                      ),
                      if (!connected)
                        _GameCard(
                          title: 'Play on phone',
                          subtitle: 'No board? Tap the tiles on the screen',
                          icon: Icons.phone_iphone,
                          color: Colors.white54,
                          enabled: true,
                          onTap: () => _open(context, '/freeplay'),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _open(BuildContext context, String route) {
    HapticFeedback.mediumImpact();
    Navigator.pushNamed(context, route, arguments: GameLaunch.app);
  }

  Widget _boardStatus(BleConnectionState state) {
    final connected = state == BleConnectionState.connected;
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              connected ? Icons.bluetooth_connected : Icons.bluetooth_disabled,
              size: 18,
              color: connected ? Colors.green : Colors.white54,
            ),
            const SizedBox(width: 8),
            Text(
              boardStatusText(state),
              style: const TextStyle(fontSize: 12, letterSpacing: 3, fontWeight: FontWeight.w600, color: Colors.white54),
            ),
          ],
        ),
        if (!connected && state != BleConnectionState.connecting && state != BleConnectionState.scanning) ...[
          const SizedBox(height: 12),
          const Center(child: BoardConnectButton()),
        ],
      ],
    );
  }

  Widget _lockedHeader(BuildContext context, WidgetRef ref) {
    return Row(
      children: [
        Icon(Icons.lock_outline, size: 16, color: Colors.white.withValues(alpha: 0.3)),
        const SizedBox(width: 6),
        const Text(
          'ROADBLOCK ACTIVE',
          style: TextStyle(fontSize: 11, letterSpacing: 2, fontWeight: FontWeight.w600, color: Colors.white54),
        ),
        const Spacer(),
        PopupMenuButton<String>(
          icon: Icon(Icons.menu, color: Colors.white.withValues(alpha: 0.5)),
          color: const Color(0xFF1C1C1E),
          onSelected: (value) async {
            switch (value) {
              case 'setup':
                Navigator.pushNamed(context, '/setup');
              case 'test':
                final messenger = ScaffoldMessenger.of(context);
                try {
                  await NotificationService.instance.showInstagramBlockedNotification();
                  messenger.showSnackBar(
                    const SnackBar(
                      content: Text('✅ Notification sent'),
                      duration: Duration(seconds: 2),
                      backgroundColor: Colors.green,
                    ),
                  );
                } catch (e) {
                  messenger.showSnackBar(
                    SnackBar(
                      content: Text('❌ Error: $e'),
                      duration: const Duration(seconds: 3),
                      backgroundColor: Colors.red,
                    ),
                  );
                }
              case 'dev':
                ref.read(sessionManagerProvider.notifier).unlockSession();
            }
          },
          itemBuilder: (context) => const [
            PopupMenuItem(
              value: 'setup',
              child: Row(
                children: [
                  Icon(Icons.help_outline, size: 18, color: Colors.white70),
                  SizedBox(width: 10),
                  Text('Setup', style: TextStyle(color: Colors.white70)),
                ],
              ),
            ),
            PopupMenuItem(
              value: 'test',
              child: Row(
                children: [
                  Icon(Icons.notifications_active, size: 18, color: Colors.orange),
                  SizedBox(width: 10),
                  Text('Test notification', style: TextStyle(color: Colors.orange)),
                ],
              ),
            ),
            PopupMenuItem(
              value: 'dev',
              child: Row(
                children: [
                  Icon(Icons.developer_mode, size: 18, color: Color(0xFF9C27B0)),
                  SizedBox(width: 10),
                  Text('Dev unlock', style: TextStyle(color: Color(0xFF9C27B0))),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Instagram time left (or locked) and the exchange rate for play time.
class _InstagramTime extends ConsumerWidget {
  const _InstagramTime();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionManagerProvider);
    final multiplier = session.playTimeMultiplier;
    final rate = multiplier == 1
        ? '1 s played = 1 s Instagram'
        : '${formatMultiplier(multiplier)}: 1 s played = ${formatMultiplier(multiplier).substring(1)} s Instagram';
    return Column(
      children: [
        const Text('INSTAGRAM TIME', style: TextStyle(fontSize: 11, letterSpacing: 2, color: Colors.white54)),
        Text(
          session.isUnlocked ? formatClock(session.remainingTime) : 'LOCKED',
          style: TextStyle(
            fontSize: 44,
            fontWeight: FontWeight.w700,
            color: session.isUnlocked ? Colors.white : Colors.white70,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
        Text(
          session.isUnlocked ? 'Play a game to add time · $rate' : 'Play a game to unlock · $rate',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, color: Colors.greenAccent),
        ),
      ],
    );
  }
}

class _GameCard extends StatelessWidget {
  const _GameCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.enabled,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Opacity(
        opacity: enabled ? 1 : 0.4,
        child: Material(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(16),
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: enabled ? onTap : null,
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  Icon(icon, size: 40, color: color),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white),
                        ),
                        const SizedBox(height: 2),
                        Text(subtitle, style: const TextStyle(color: Colors.white54)),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, color: enabled ? Colors.white54 : Colors.white24),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
