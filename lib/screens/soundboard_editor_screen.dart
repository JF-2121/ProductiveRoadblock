import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/sound_clip.dart';
import '../models/soundboard.dart';
import '../services/sound_cache.dart';
import '../state/soundboard_library.dart';

/// Create/edit a board: name, pad labels, colours, and assigned sounds
/// (mobile-app#4, #7, #8).
class SoundboardEditorScreen extends ConsumerStatefulWidget {
  const SoundboardEditorScreen({super.key});

  @override
  ConsumerState<SoundboardEditorScreen> createState() =>
      _SoundboardEditorScreenState();
}

class _SoundboardEditorScreenState
    extends ConsumerState<SoundboardEditorScreen> {
  late Soundboard _board;
  late TextEditingController _nameController;
  late List<SoundboardPad> _pads;
  late List<TextEditingController> _labelControllers;
  late int _columns;
  bool _initialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_initialized) return;
    _initialized = true;

    _board = ModalRoute.of(context)!.settings.arguments! as Soundboard;
    _nameController = TextEditingController(text: _board.name);
    _pads = List<SoundboardPad>.from(_board.pads);
    _labelControllers = [
      for (final pad in _pads) TextEditingController(text: pad.label),
    ];
    _columns = _board.columns;
  }

  @override
  void dispose() {
    _nameController.dispose();
    for (final c in _labelControllers) {
      c.dispose();
    }
    super.dispose();
  }

  void _addPad() {
    setState(() {
      final label = 'Pad ${_pads.length + 1}';
      _pads.add(
        SoundboardPad(
          label: label,
          colorValue: soundboardPalette[_pads.length % soundboardPalette.length],
          soundId: soundLibrary.first.id,
        ),
      );
      _labelControllers.add(TextEditingController(text: label));
    });
  }

  void _removePad(int index) {
    setState(() {
      _pads.removeAt(index);
      _labelControllers.removeAt(index).dispose();
    });
  }

  Future<void> _pickColor(int index) async {
    final chosen = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: Colors.grey[900],
      builder: (context) => Padding(
        padding: const EdgeInsets.all(20),
        child: Wrap(
          spacing: 14,
          runSpacing: 14,
          children: [
            for (final color in soundboardPalette)
              GestureDetector(
                onTap: () => Navigator.pop(context, color),
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Color(color),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: _pads[index].colorValue == color
                          ? Colors.white
                          : Colors.transparent,
                      width: 3,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
    if (chosen != null) {
      setState(() => _pads[index] = _pads[index].copyWith(colorValue: chosen));
    }
  }

  Future<void> _pickSound(int index) async {
    final chosen = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.grey[900],
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            for (final clip in soundLibrary)
              ListTile(
                leading: Icon(
                  clip.id == _pads[index].soundId
                      ? Icons.check_circle
                      : Icons.music_note_outlined,
                  color: clip.id == _pads[index].soundId
                      ? const Color(0xFF9C27B0)
                      : Colors.white54,
                ),
                title: Text(clip.name, style: const TextStyle(color: Colors.white)),
                trailing: IconButton(
                  icon: const Icon(Icons.play_arrow, color: Colors.white54),
                  onPressed: () {
                    HapticFeedback.selectionClick();
                    unawaited(SoundCache.instance.play(clip.id));
                  },
                ),
                onTap: () => Navigator.pop(context, clip.id),
              ),
          ],
        ),
      ),
    );
    if (chosen != null) {
      setState(() => _pads[index] = _pads[index].copyWith(soundId: chosen));
    }
  }

  void _save() {
    final name = _nameController.text.trim();
    final updated = _board.copyWith(
      name: name.isEmpty ? _board.name : name,
      pads: _pads,
      columns: _columns,
    );
    ref.read(soundboardLibraryProvider.notifier).updateBoard(updated);
    Navigator.pop(context);
  }

  void _deleteBoard() {
    ref.read(soundboardLibraryProvider.notifier).deleteBoard(_board.id);
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Board'),
        actions: [
          IconButton(
            icon: const Icon(Icons.check),
            tooltip: 'Save',
            onPressed: _pads.isEmpty ? null : _save,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(
            controller: _nameController,
            style: const TextStyle(color: Colors.white, fontSize: 18),
            decoration: const InputDecoration(labelText: 'Board name'),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              const Text('Pad size', style: TextStyle(color: Colors.white70)),
              const SizedBox(width: 16),
              for (final option in [2, 3, 4])
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text('$option cols'),
                    selected: _columns == option,
                    onSelected: (_) => setState(() => _columns = option),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 24),
          for (var i = 0; i < _pads.length; i++)
            Card(
              color: Colors.white10,
              margin: const EdgeInsets.only(bottom: 10),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    GestureDetector(
                      onTap: () => _pickColor(i),
                      child: Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: Color(_pads[i].colorValue),
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _labelControllers[i],
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(labelText: 'Label'),
                        onChanged: (value) =>
                            _pads[i] = _pads[i].copyWith(label: value),
                      ),
                    ),
                    const SizedBox(width: 8),
                    TextButton.icon(
                      onPressed: () => _pickSound(i),
                      icon: const Icon(Icons.music_note_outlined, size: 18),
                      label: Text(findSoundClip(_pads[i].soundId)?.name ?? '—'),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.white38),
                      onPressed: () => _removePad(i),
                    ),
                  ],
                ),
              ),
            ),
          OutlinedButton.icon(
            onPressed: _addPad,
            icon: const Icon(Icons.add),
            label: const Text('Add pad'),
          ),
          const SizedBox(height: 32),
          TextButton.icon(
            onPressed: _deleteBoard,
            icon: const Icon(Icons.delete_forever, color: Colors.redAccent),
            label: const Text(
              'Delete board',
              style: TextStyle(color: Colors.redAccent),
            ),
          ),
        ],
      ),
    );
  }
}
