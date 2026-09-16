import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

/// Piano Tiles file structure & interface (mobile-app#11).
///
/// A song is just a named sequence of target lanes (0-3, one per row/beat).
/// PianoTilesGame plays a song when one is supplied instead of generating a
/// random pattern. Content — real curated songs — is tracked separately in
/// swhz-orga#3; this only defines the format and how to load it.
///
/// JSON shape:
/// ```json
/// { "name": "Example", "pattern": [0, 2, 1, 3, 0, 1, 2, 3] }
/// ```
class PianoTilesSong {
  const PianoTilesSong({required this.name, required this.pattern});

  final String name;
  final List<int> pattern;

  factory PianoTilesSong.fromJson(Map<String, dynamic> json) {
    return PianoTilesSong(
      name: json['name'] as String,
      pattern: (json['pattern'] as List<dynamic>)
          .map((e) => e as int)
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {'name': name, 'pattern': pattern};
}

/// Loads a [PianoTilesSong] from a bundled JSON asset, e.g. `assets/songs/demo_song.json`.
Future<PianoTilesSong> loadSongFromAsset(String assetPath) async {
  final raw = await rootBundle.loadString(assetPath);
  return PianoTilesSong.fromJson(jsonDecode(raw) as Map<String, dynamic>);
}
