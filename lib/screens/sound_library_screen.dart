import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/sound_clip.dart';
import '../services/sound_cache.dart';

/// Flat browse-all-sounds view over the bundled library (mobile-app#6).
class SoundLibraryScreen extends StatefulWidget {
  const SoundLibraryScreen({super.key});

  @override
  State<SoundLibraryScreen> createState() => _SoundLibraryScreenState();
}

class _SoundLibraryScreenState extends State<SoundLibraryScreen> {
  String? _playingId;

  Future<void> _preview(SoundClip clip) async {
    HapticFeedback.selectionClick();
    setState(() => _playingId = clip.id);
    await SoundCache.instance.play(clip.id);
    if (mounted) setState(() => _playingId = null);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('All Sounds')),
      body: ListView.separated(
        padding: const EdgeInsets.all(20),
        itemCount: soundLibrary.length,
        separatorBuilder: (_, _) => const Divider(color: Colors.white12, height: 1),
        itemBuilder: (context, index) {
          final clip = soundLibrary[index];
          final isPlaying = _playingId == clip.id;
          return ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              isPlaying ? Icons.graphic_eq : Icons.music_note_outlined,
              color: isPlaying ? const Color(0xFF9C27B0) : Colors.white54,
            ),
            title: Text(
              clip.name,
              style: const TextStyle(color: Colors.white, fontSize: 16),
            ),
            trailing: IconButton(
              icon: const Icon(Icons.play_arrow, color: Colors.white70),
              onPressed: () => _preview(clip),
            ),
            onTap: () => _preview(clip),
          );
        },
      ),
    );
  }
}
