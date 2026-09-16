/// Soundboard data format (mobile-app#3).
///
/// A board is a named grid of pads. Each pad has a label, a colour, and a
/// reference to a clip in the bundled [soundLibrary] (see sound_clip.dart).
/// [columns] controls the grid width, which is what makes pad size
/// customisable (mobile-app#4) — fewer columns means bigger pads.
///
/// Boards are persisted as JSON via SharedPreferences (see
/// state/soundboard_library.dart), so this file is also the on-disk schema.
library;

class SoundboardPad {
  const SoundboardPad({
    required this.label,
    required this.colorValue,
    required this.soundId,
  });

  final String label;
  final int colorValue;
  final String soundId;

  SoundboardPad copyWith({String? label, int? colorValue, String? soundId}) {
    return SoundboardPad(
      label: label ?? this.label,
      colorValue: colorValue ?? this.colorValue,
      soundId: soundId ?? this.soundId,
    );
  }

  factory SoundboardPad.fromJson(Map<String, dynamic> json) {
    return SoundboardPad(
      label: json['label'] as String,
      colorValue: json['colorValue'] as int,
      soundId: json['soundId'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
    'label': label,
    'colorValue': colorValue,
    'soundId': soundId,
  };
}

class Soundboard {
  const Soundboard({
    required this.id,
    required this.name,
    required this.pads,
    this.columns = 3,
  });

  final String id;
  final String name;
  final List<SoundboardPad> pads;
  final int columns;

  Soundboard copyWith({
    String? name,
    List<SoundboardPad>? pads,
    int? columns,
  }) {
    return Soundboard(
      id: id,
      name: name ?? this.name,
      pads: pads ?? this.pads,
      columns: columns ?? this.columns,
    );
  }

  factory Soundboard.fromJson(Map<String, dynamic> json) {
    return Soundboard(
      id: json['id'] as String,
      name: json['name'] as String,
      columns: json['columns'] as int? ?? 3,
      pads: (json['pads'] as List<dynamic>)
          .map((e) => SoundboardPad.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'columns': columns,
    'pads': pads.map((p) => p.toJson()).toList(),
  };
}

/// The single starter/prefixed board (mobile-app#5) shipped on first run,
/// built from the placeholder tones in the bundled sound library.
Soundboard buildDefaultSoundboard(String id) {
  return Soundboard(
    id: id,
    name: 'Default',
    columns: 3,
    pads: const [
      SoundboardPad(label: 'Click', colorValue: 0xFF3B82F6, soundId: 'click'),
      SoundboardPad(label: 'Pop', colorValue: 0xFFF97316, soundId: 'pop'),
      SoundboardPad(label: 'Zap', colorValue: 0xFFEAB308, soundId: 'zap'),
      SoundboardPad(label: 'Ding', colorValue: 0xFF22C55E, soundId: 'ding'),
      SoundboardPad(label: 'Buzz', colorValue: 0xFFA855F7, soundId: 'buzz'),
      SoundboardPad(label: 'Ping', colorValue: 0xFFEC4899, soundId: 'ping'),
    ],
  );
}

/// Preset swatches offered in the pad colour picker.
const List<int> soundboardPalette = [
  0xFF3B82F6, // blue
  0xFFF97316, // orange
  0xFFEAB308, // yellow
  0xFF22C55E, // green
  0xFFA855F7, // purple
  0xFFEC4899, // pink
  0xFF06B6D4, // cyan
  0xFFEF4444, // red
];
