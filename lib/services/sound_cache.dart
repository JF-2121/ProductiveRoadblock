import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';

import '../models/sound_clip.dart';

/// Preloads every bundled sound clip into its own low-latency player so a
/// tap plays instantly instead of paying asset-decode latency each time
/// (the "fast caching" half of mobile-app#13).
///
/// `AudioPlayer.play(AssetSource(...))` has to load and decode the asset on
/// every call, which is the ~150-300ms delay that made tile taps feel
/// laggy. Loading each clip once via [PlayerMode.lowLatency] +
/// `setSourceAsset`, then triggering playback with `seek(0) + resume()`,
/// skips that cost on every subsequent play.
class SoundCache {
  SoundCache._();
  static final SoundCache instance = SoundCache._();

  final Map<String, AudioPlayer> _players = {};
  bool _preloading = false;

  Future<void> preload() async {
    if (_preloading || _players.isNotEmpty) return;
    _preloading = true;

    await Future.wait(
      [...soundLibrary, ...gameSoundClips].map((clip) async {
        final player = AudioPlayer();
        await player.setPlayerMode(PlayerMode.lowLatency);
        await player.setReleaseMode(ReleaseMode.stop);
        try {
          await player.setSourceAsset(clip.assetPath);
          _players[clip.id] = player;
        } catch (e) {
          debugPrint('[SoundCache] Failed to preload ${clip.assetPath}: $e');
          unawaited(player.dispose());
        }
      }),
    );

    _preloading = false;
  }

  Future<void> play(String soundId) async {
    final player = _players[soundId];
    if (player == null) return;
    try {
      await player.seek(Duration.zero);
      await player.resume();
    } catch (e) {
      debugPrint('[SoundCache] Playback failed for $soundId: $e');
    }
  }

  Future<void> dispose() async {
    for (final player in _players.values) {
      unawaited(player.dispose());
    }
    _players.clear();
  }
}
