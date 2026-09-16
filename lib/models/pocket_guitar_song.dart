import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

/// A Pocket Guitar song bundled with the app: the chart is sent to the board, the music plays here.
///
/// Listed in `assets/pocket_guitar/catalog.json`. The chart is a board song file
/// (raspberry-micro-python/game/pocketGuitar/songs format); the audio starts exactly at tick 0 of
/// the chart and has a constant tempo, so song position N ms on the board is N ms into the audio.
class PocketGuitarSong {
  const PocketGuitarSong({
    required this.id,
    required this.title,
    required this.artist,
    required this.bpm,
    required this.chartAsset,
    required this.audioAsset,
    required this.lengthMs,
  });

  final String id;
  final String title;
  final String artist;
  final double bpm;

  /// Asset path of the chart JSON, e.g. `assets/pocket_guitar/songs/hotel_california.json`.
  final String chartAsset;

  /// Asset path of the music, e.g. `assets/pocket_guitar/audio/hotel_california.m4a`.
  final String audioAsset;

  /// Song length on the board (end of the last note + one bar).
  final int lengthMs;

  factory PocketGuitarSong.fromJson(Map<String, dynamic> json) {
    return PocketGuitarSong(
      id: json['id'] as String,
      title: json['title'] as String,
      artist: json['artist'] as String,
      bpm: (json['bpm'] as num).toDouble(),
      chartAsset: json['chart'] as String,
      audioAsset: json['audio'] as String,
      lengthMs: json['length_ms'] as int,
    );
  }

  /// The chart as compact UTF-8 JSON, ready to send to the board.
  Future<List<int>> loadChartBytes() async {
    final raw = await rootBundle.loadString(chartAsset);
    return utf8.encode(jsonEncode(jsonDecode(raw)));
  }

  /// [audioAsset] relative to `assets/`, as audioplayers' AssetSource expects it.
  String get audioSourcePath => audioAsset.replaceFirst('assets/', '');
}

Future<List<PocketGuitarSong>> loadPocketGuitarCatalog() async {
  final raw = await rootBundle.loadString('assets/pocket_guitar/catalog.json');
  final songs = (jsonDecode(raw) as Map<String, dynamic>)['songs'] as List<dynamic>;
  return songs.map((s) => PocketGuitarSong.fromJson(s as Map<String, dynamic>)).toList();
}
