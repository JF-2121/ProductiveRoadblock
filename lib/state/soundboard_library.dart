import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/sound_clip.dart';
import '../models/soundboard.dart';

/// Owns the user's saved boards (mobile-app#3/#5/#8), persisted as JSON via
/// SharedPreferences under [_storageKey].
class SoundboardLibrary extends Notifier<List<Soundboard>> {
  static const String _storageKey = 'soundboards_v1';

  @override
  List<Soundboard> build() {
    unawaited(_restore());
    return const [];
  }

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_storageKey);

    if (raw == null) {
      // First run: ship one prefixed starter board (mobile-app#5).
      state = [buildDefaultSoundboard(_newId())];
      unawaited(_persist());
      return;
    }

    final decoded = jsonDecode(raw) as List<dynamic>;
    state = decoded
        .map((e) => Soundboard.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    final encoded = jsonEncode(state.map((b) => b.toJson()).toList());
    await prefs.setString(_storageKey, encoded);
  }

  String _newId() => DateTime.now().microsecondsSinceEpoch.toString();

  Soundboard createBoard() {
    final board = Soundboard(
      id: _newId(),
      name: 'New Board',
      pads: [
        SoundboardPad(
          label: 'Pad 1',
          colorValue: soundboardPalette.first,
          soundId: soundLibrary.first.id,
        ),
      ],
    );
    state = [...state, board];
    unawaited(_persist());
    return board;
  }

  void updateBoard(Soundboard updated) {
    state = [
      for (final board in state) if (board.id == updated.id) updated else board,
    ];
    unawaited(_persist());
  }

  void deleteBoard(String id) {
    state = state.where((board) => board.id != id).toList();
    unawaited(_persist());
  }
}

final soundboardLibraryProvider =
    NotifierProvider<SoundboardLibrary, List<Soundboard>>(SoundboardLibrary.new);
