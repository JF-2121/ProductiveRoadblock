import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/app_state.dart';
import '../state/session_manager.dart';
import '../services/ble_service.dart';
import '../widgets/board_connect.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  // Debug-only: lets you reach Play Games/Soundboards/Setup/Debug without a
  // real NeoTrellis board connected; the game menu then offers the on-phone game.
  bool _debugBypass = false;

  void _showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(appProvider);
    final sessionState = ref.watch(sessionManagerProvider);
    final remainingSeconds = sessionState.remainingTime.inSeconds;
    final minutes = (remainingSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (remainingSeconds % 60).toString().padLeft(2, '0');
    final isActuallyConnected = appState.bleState == BleConnectionState.connected;
    final unlocked = isActuallyConnected || _debugBypass;

    return Scaffold(
      // This screen is the menu / root, so it deliberately has no back
      // arrow: backing out of debug mode or another screen should land
      // here, never re-lock the app. Locking is only ever explicit, via
      // ACTIVATE LOCK below.
      appBar: AppBar(
        title: const Text('Productive Roadblock'),
        automaticallyImplyLeading: false,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isActuallyConnected
                  ? Icons.bluetooth_connected
                  : unlocked
                  ? Icons.bug_report
                  : Icons.bluetooth_disabled,
              size: 64,
              color: isActuallyConnected
                  ? Colors.green
                  : unlocked
                  ? Colors.deepPurpleAccent
                  : Colors.white54,
            ),
            const SizedBox(height: 24),
            Text(
              isActuallyConnected
                  ? 'DEVICE CONNECTED'
                  : appState.bleState == BleConnectionState.scanning
                  ? 'SCANNING...'
                  : appState.bleState == BleConnectionState.bluetoothDisabled
                  ? 'BLUETOOTH IS DISABLED'
                  : appState.bleState == BleConnectionState.connecting
                  ? 'CONNECTING...'
                  : 'NO DEVICE',
              style: const TextStyle(
                fontSize: 16,
                letterSpacing: 4,
                fontWeight: FontWeight.w600,
                color: Colors.white54,
              ),
            ),
            if (_debugBypass && !isActuallyConnected) ...[
              const SizedBox(height: 8),
              const Text(
                'DEBUG BYPASS ACTIVE',
                style: TextStyle(
                  fontSize: 12,
                  letterSpacing: 2,
                  fontWeight: FontWeight.w600,
                  color: Colors.deepPurpleAccent,
                ),
              ),
            ],
            const SizedBox(height: 12),
            Text(
              'SESSION: $minutes:$seconds',
              style: const TextStyle(
                fontSize: 14,
                letterSpacing: 1.5,
                color: Colors.white70,
              ),
            ),
            const SizedBox(height: 48),
            if (!isActuallyConnected && !unlocked) ...[
              const BoardConnectButton(),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: () {
                  HapticFeedback.mediumImpact();
                  setState(() => _debugBypass = true);
                },
                icon: const Icon(Icons.bug_report, size: 18),
                label: const Text('DEBUG: SKIP BLUETOOTH'),
                style: TextButton.styleFrom(
                  foregroundColor: Colors.deepPurpleAccent,
                ),
              ),
            ],
            if (unlocked) ...[
              ElevatedButton.icon(
                onPressed: () async {
                  HapticFeedback.mediumImpact();
                  if (isActuallyConnected) {
                    await ref.read(appProvider.notifier).disconnectDevice();
                  }
                  setState(() => _debugBypass = false);
                  if (mounted) {
                    _showMessage(
                      isActuallyConnected ? 'Disconnected' : 'Debug bypass off',
                    );
                  }
                },
                icon: const Icon(Icons.bluetooth_disabled),
                label: Text(isActuallyConnected ? 'DISCONNECT' : 'EXIT DEBUG BYPASS'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                  backgroundColor: Colors.redAccent,
                ),
              ),
              const SizedBox(height: 16),
              // Simon Says, Pocket Guitar and Piano Tiles on the board (the on-phone game without a board);
              // playing adds Instagram time to this session
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/games');
                },
                icon: const Icon(Icons.sports_esports),
                label: const Text('PLAY GAMES'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                  backgroundColor: Colors.redAccent,
                ),
              ),
              // Pocket Guitar runs on the board, so it needs a real connection (not the debug bypass)
              if (isActuallyConnected) ...[
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pushNamed(context, '/pocket-guitar');
                  },
                  icon: const Icon(Icons.music_note),
                  label: const Text('POCKET GUITAR'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 32,
                      vertical: 16,
                    ),
                    backgroundColor: Colors.redAccent,
                  ),
                ),
              ],
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/soundboards');
                },
                icon: const Icon(Icons.graphic_eq),
                label: const Text('OPEN SOUNDBOARD'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () {
                  HapticFeedback.lightImpact();
                  ref.read(sessionManagerProvider.notifier).lockSession();
                  _showMessage('Lock activated');
                },
                icon: const Icon(Icons.lock),
                label: const Text('ACTIVATE LOCK'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/setup');
                },
                icon: const Icon(Icons.help_outline),
                label: const Text('SCREEN TIME SETUP'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                  backgroundColor: Colors.blue,
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/debug');
                },
                icon: const Icon(Icons.bug_report),
                label: const Text('DEBUG CONTROLS'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                  backgroundColor: Colors.deepPurple,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
