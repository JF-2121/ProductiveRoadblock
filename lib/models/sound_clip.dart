/// A single playable sound in the bundled sound library.
///
/// These are placeholder synthesized tones (see assets/sounds/) standing in
/// for real recordings — swap the assets and this list stays the same shape.
class SoundClip {
  const SoundClip({required this.id, required this.name, required this.assetPath});

  final String id;
  final String name;
  final String assetPath;
}

const List<SoundClip> soundLibrary = [
  SoundClip(id: 'click', name: 'Click', assetPath: 'sounds/click.wav'),
  SoundClip(id: 'pop', name: 'Pop', assetPath: 'sounds/pop.wav'),
  SoundClip(id: 'zap', name: 'Zap', assetPath: 'sounds/zap.wav'),
  SoundClip(id: 'ding', name: 'Ding', assetPath: 'sounds/ding.wav'),
  SoundClip(id: 'buzz', name: 'Buzz', assetPath: 'sounds/buzz.wav'),
  SoundClip(id: 'ping', name: 'Ping', assetPath: 'sounds/ping.wav'),
  SoundClip(id: 'blip', name: 'Blip', assetPath: 'sounds/blip.wav'),
  SoundClip(id: 'chime', name: 'Chime', assetPath: 'sounds/chime.wav'),
  SoundClip(id: 'thump', name: 'Thump', assetPath: 'sounds/thump.wav'),
  SoundClip(id: 'chirp', name: 'Chirp', assetPath: 'sounds/chirp.wav'),
  SoundClip(id: 'swoosh', name: 'Swoosh', assetPath: 'sounds/swoosh.wav'),
  SoundClip(id: 'bloop', name: 'Bloop', assetPath: 'sounds/bloop.wav'),
  SoundClip(id: 'snap', name: 'Snap', assetPath: 'sounds/snap.wav'),
  SoundClip(id: 'warble', name: 'Warble', assetPath: 'sounds/warble.wav'),
  // Synthesized piano-like tones (additive synthesis, not a recording - no
  // sourcing/licensing question), one per Piano Tiles lane. A C major
  // arpeggio, ascending left to right: C4, E4, G4, C5.
  SoundClip(id: 'piano_c4', name: 'Piano C4', assetPath: 'sounds/piano_c4.wav'),
  SoundClip(id: 'piano_e4', name: 'Piano E4', assetPath: 'sounds/piano_e4.wav'),
  SoundClip(id: 'piano_g4', name: 'Piano G4', assetPath: 'sounds/piano_g4.wav'),
  SoundClip(id: 'piano_c5', name: 'Piano C5', assetPath: 'sounds/piano_c5.wav'),
];

/// Sounds of the board games, preloaded like [soundLibrary] but not offered on the soundboards: one tone per
/// Simon Says block (C major pentatonic, block 0 red = C5 ... block 7 white = E6) and a fanfare for a won run.
const List<SoundClip> gameSoundClips = [
  SoundClip(id: 'simon_0', name: 'Simon Says red', assetPath: 'simon_says/tone_0.wav'),
  SoundClip(id: 'simon_1', name: 'Simon Says green', assetPath: 'simon_says/tone_1.wav'),
  SoundClip(id: 'simon_2', name: 'Simon Says blue', assetPath: 'simon_says/tone_2.wav'),
  SoundClip(id: 'simon_3', name: 'Simon Says yellow', assetPath: 'simon_says/tone_3.wav'),
  SoundClip(id: 'simon_4', name: 'Simon Says magenta', assetPath: 'simon_says/tone_4.wav'),
  SoundClip(id: 'simon_5', name: 'Simon Says cyan', assetPath: 'simon_says/tone_5.wav'),
  SoundClip(id: 'simon_6', name: 'Simon Says orange', assetPath: 'simon_says/tone_6.wav'),
  SoundClip(id: 'simon_7', name: 'Simon Says white', assetPath: 'simon_says/tone_7.wav'),
  SoundClip(id: 'fanfare', name: 'Fanfare', assetPath: 'simon_says/fanfare.wav'),
];

/// Sound id of the tone of Simon Says block 0-7.
String simonToneId(int block) => 'simon_${block.clamp(0, 7)}';

SoundClip? findSoundClip(String id) {
  for (final clip in soundLibrary) {
    if (clip.id == id) return clip;
  }
  return null;
}
