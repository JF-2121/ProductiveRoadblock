import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/soundboard.dart';
import '../services/sound_cache.dart';
import '../state/session_manager.dart';

/// Plays a specific [Soundboard]'s pads (mobile-app#4).
class SoundboardPlayScreen extends ConsumerStatefulWidget {
  const SoundboardPlayScreen({super.key});

  @override
  ConsumerState<SoundboardPlayScreen> createState() =>
      _SoundboardPlayScreenState();
}

class _SoundboardPlayScreenState extends ConsumerState<SoundboardPlayScreen> {
  int? _pressedIndex;

  void _playPad(SoundboardPad pad) {
    HapticFeedback.lightImpact();
    unawaited(SoundCache.instance.play(pad.soundId));
  }

  @override
  Widget build(BuildContext context) {
    final board = ModalRoute.of(context)!.settings.arguments! as Soundboard;
    final sessionState = ref.watch(sessionManagerProvider);
    final remainingSeconds = sessionState.remainingTime.inSeconds;
    final minutes = (remainingSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (remainingSeconds % 60).toString().padLeft(2, '0');

    return Scaffold(
      appBar: AppBar(
        title: Text(board.name),
        actions: [
          TextButton(
            onPressed: ref.read(sessionManagerProvider.notifier).lockSession,
            child: const Text('LOCK NOW'),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Unlocked time left: $minutes:$seconds',
              style: const TextStyle(
                fontSize: 16,
                letterSpacing: 0.5,
                color: Colors.white70,
              ),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: GridView.builder(
                physics: const NeverScrollableScrollPhysics(),
                itemCount: board.pads.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: board.columns,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.4,
                ),
                itemBuilder: (context, index) {
                  final pad = board.pads[index];
                  final isPressed = _pressedIndex == index;
                  final color = Color(pad.colorValue);

                  return GestureDetector(
                    onTapDown: (_) {
                      setState(() => _pressedIndex = index);
                      _playPad(pad);
                    },
                    onTapUp: (_) => setState(() => _pressedIndex = null),
                    onTapCancel: () => setState(() => _pressedIndex = null),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 80),
                      decoration: BoxDecoration(
                        color: isPressed
                            ? color.withValues(alpha: 0.55)
                            : color.withValues(alpha: 0.25),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: isPressed ? color : color.withValues(alpha: 0.5),
                          width: 1.5,
                        ),
                      ),
                      child: Center(
                        child: Text(
                          pad.label,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.5,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
