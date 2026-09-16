import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/soundboard.dart';
import '../state/session_manager.dart';
import '../state/soundboard_library.dart';

/// Browse, create, and manage saved boards (mobile-app#6, #8).
class SoundboardLibraryScreen extends ConsumerWidget {
  const SoundboardLibraryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final boards = ref.watch(soundboardLibraryProvider);
    final sessionState = ref.watch(sessionManagerProvider);
    final remainingSeconds = sessionState.remainingTime.inSeconds;
    final minutes = (remainingSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (remainingSeconds % 60).toString().padLeft(2, '0');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Soundboards'),
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
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () => Navigator.pushNamed(context, '/sound-library'),
              icon: const Icon(Icons.library_music_outlined),
              label: const Text('Browse all sounds'),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: boards.isEmpty
                  ? const Center(
                      child: Text(
                        'No boards yet — tap + to create one.',
                        style: TextStyle(color: Colors.white54),
                      ),
                    )
                  : ListView.separated(
                      itemCount: boards.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 12),
                      itemBuilder: (context, index) =>
                          _BoardCard(board: boards[index]),
                    ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          HapticFeedback.mediumImpact();
          final board = ref.read(soundboardLibraryProvider.notifier).createBoard();
          if (context.mounted) {
            Navigator.pushNamed(context, '/soundboard-editor', arguments: board);
          }
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}

class _BoardCard extends ConsumerWidget {
  const _BoardCard({required this.board});

  final Soundboard board;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Material(
      color: Colors.white10,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () =>
            Navigator.pushNamed(context, '/soundboard-play', arguments: board),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      board.name,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        for (final pad in board.pads.take(6))
                          Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: Container(
                              width: 14,
                              height: 14,
                              decoration: BoxDecoration(
                                color: Color(pad.colorValue),
                                shape: BoxShape.circle,
                              ),
                            ),
                          ),
                        const SizedBox(width: 6),
                        Text(
                          '${board.pads.length} pads',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.white54,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.edit_outlined, color: Colors.white54),
                tooltip: 'Edit',
                onPressed: () => Navigator.pushNamed(
                  context,
                  '/soundboard-editor',
                  arguments: board,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.delete_outline, color: Colors.white38),
                tooltip: 'Delete',
                onPressed: () async {
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      backgroundColor: Colors.grey[900],
                      title: const Text('Delete board?'),
                      content: Text('"${board.name}" will be removed for good.'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context, false),
                          child: const Text('Cancel'),
                        ),
                        TextButton(
                          onPressed: () => Navigator.pop(context, true),
                          child: const Text(
                            'Delete',
                            style: TextStyle(color: Colors.redAccent),
                          ),
                        ),
                      ],
                    ),
                  );
                  if (confirmed == true) {
                    ref.read(soundboardLibraryProvider.notifier).deleteBoard(board.id);
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
