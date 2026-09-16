import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

/// A Piano Tiles song for the board: a recording that follows the player's taps (see TapFollowPlayer).
///
/// Listed in `assets/piano_tiles/catalog.json`. The board deals the tiles and reports every tapped tile; tile k
/// plays the music from [tileMs] k to [tileMs] k + 1 (the last tile ends at [endMs]). Tile times sit on the beat
/// grid of the recording, just before a note, so the music stops and starts cleanly between notes.
class PianoTilesTrack {
  const PianoTilesTrack({
    required this.id,
    required this.title,
    required this.composer,
    required this.performer,
    required this.audioAsset,
    required this.chartAsset,
    required this.lengthMs,
    this.tileMs = const [],
    this.endMs = 0,
  });

  final String id;
  final String title;
  final String composer;
  final String performer;

  /// Asset path of the music, e.g. `assets/piano_tiles/audio/canon_in_d.m4a`.
  final String audioAsset;

  /// Asset path of the tile chart, e.g. `assets/piano_tiles/charts/canon_in_d.json`.
  final String chartAsset;

  /// Length of the recording (the last tile plus a fade-out).
  final int lengthMs;

  /// Start of every tile in the recording (ms), empty until [loadChart].
  final List<int> tileMs;

  /// End of the last tile (ms).
  final int endMs;

  factory PianoTilesTrack.fromJson(Map<String, dynamic> json) {
    return PianoTilesTrack(
      id: json['id'] as String,
      title: json['title'] as String,
      composer: json['composer'] as String,
      performer: json['performer'] as String,
      audioAsset: json['audio'] as String,
      chartAsset: json['chart'] as String,
      lengthMs: json['length_ms'] as int,
    );
  }

  /// This song with its tile times from [chartAsset].
  Future<PianoTilesTrack> loadChart() async {
    final chart = jsonDecode(await rootBundle.loadString(chartAsset)) as Map<String, dynamic>;
    return withChart((chart['tile_ms'] as List<dynamic>).cast<int>(), chart['end_ms'] as int);
  }

  PianoTilesTrack withChart(List<int> tileMs, int endMs) {
    return PianoTilesTrack(
      id: id,
      title: title,
      composer: composer,
      performer: performer,
      audioAsset: audioAsset,
      chartAsset: chartAsset,
      lengthMs: lengthMs,
      tileMs: List.unmodifiable(tileMs),
      endMs: endMs,
    );
  }

  /// [audioAsset] relative to `assets/`, as audioplayers' AssetSource expects it.
  String get audioSourcePath => audioAsset.replaceFirst('assets/', '');
}

Future<List<PianoTilesTrack>> loadPianoTilesCatalog() async {
  final raw = await rootBundle.loadString('assets/piano_tiles/catalog.json');
  final songs = (jsonDecode(raw) as Map<String, dynamic>)['songs'] as List<dynamic>;
  return songs.map((s) => PianoTilesTrack.fromJson(s as Map<String, dynamic>)).toList();
}
