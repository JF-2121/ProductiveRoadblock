import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/board_games.dart';
import '../services/ble_service.dart';
import '../services/pocket_guitar_session.dart';
import '../state/play_time.dart';
import '../widgets/game_ui.dart';

/// Pocket Guitar: the game runs on the board, this screen plays the music and shows the song,
/// difficulty, score and result. Only reachable while the board is connected. Opened because a
/// song started on the board ([GameLaunch.board]) it only follows that song.
class PocketGuitarScreen extends ConsumerStatefulWidget {
  const PocketGuitarScreen({super.key, this.launch = GameLaunch.app});

  final GameLaunch launch;

  @override
  ConsumerState<PocketGuitarScreen> createState() => _PocketGuitarScreenState();
}

class _PocketGuitarScreenState extends ConsumerState<PocketGuitarScreen> {
  late final PocketGuitarSession _session;
  late final PlayTimeTracker _tracker;
  final DateTime _openedAt = DateTime.now();

  static const Color _red = Color(0xFFFF3B30);
  static const Color _blue = Color(0xFF2F6BFF);
  static const List<Color> _difficultyColors = [
    Colors.greenAccent,
    Colors.amberAccent,
    Colors.orangeAccent,
    Colors.redAccent,
  ];

  @override
  void initState() {
    super.initState();
    _tracker = ref.read(playTimeProvider.notifier)..attachScreen(BleGameId.pocketGuitar);
    _session = PocketGuitarSession()..start(launch: widget.launch);
  }

  @override
  void dispose() {
    _session.dispose();
    _tracker.detachScreen(BleGameId.pocketGuitar);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: ListenableBuilder(
          listenable: _session,
          builder: (context, _) => Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const GameHeader(title: 'POCKET GUITAR'),
                const SizedBox(height: 12),
                Expanded(
                  child: _session.phase == PocketGuitarPhase.noBoard
                      ? const NoBoardHint(game: 'Pocket Guitar')
                      : SingleChildScrollView(child: _content()),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _content() {
    final s = _session;
    final fromApp = s.launch == GameLaunch.app;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _songCard(),
        const SizedBox(height: 20),
        _status(),
        const SizedBox(height: 20),
        _difficulties(),
        const SizedBox(height: 20),
        ..._controls(),
        const SizedBox(height: 20),
        EarnedTimeCard(gameId: BleGameId.pocketGuitar, since: _openedAt),
        if (fromApp) ...[
          const SizedBox(height: 8),
          _delayOffset(),
        ],
        const SizedBox(height: 12),
        Text(
          s.isRunning
              ? 'On the board: hold both strum keys for 2 s (no frets) to pause.'
              : fromApp
                  ? 'On the board: red strum = Play, blue strum = Practice (no music, the song waits for every note).'
                  : 'Started on the board. Songs stored on the board have no music in the app.',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, color: Colors.white38),
        ),
      ],
    );
  }

  Widget _songCard() {
    final s = _session;
    final song = s.song;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          const Icon(Icons.music_note, size: 36, color: Colors.white70),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(song?.title ?? 'Song from the board',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white)),
                const SizedBox(height: 2),
                Text(
                  song == null
                      ? 'Stored on the board · no music in the app'
                      : '${song.artist} · ${song.bpm.toStringAsFixed(0)} BPM · ${song.lengthMs ~/ 1000} s',
                  style: const TextStyle(color: Colors.white54),
                ),
              ],
            ),
          ),
          if (s.launch == GameLaunch.app)
            IconButton(
              tooltip: 'Another random song',
              icon: const Icon(Icons.shuffle),
              color: Colors.white70,
              onPressed: s.canChangeSong
                  ? () {
                      HapticFeedback.selectionClick();
                      s.nextRandomSong();
                    }
                  : null,
            ),
        ],
      ),
    );
  }

  Widget _status() {
    final s = _session;
    switch (s.phase) {
      case PocketGuitarPhase.loading:
        return const Center(child: CircularProgressIndicator());
      case PocketGuitarPhase.uploading:
        return Column(
          children: [
            const Text('Sending the song to the board…', style: TextStyle(color: Colors.white70)),
            const SizedBox(height: 10),
            LinearProgressIndicator(value: s.uploadProgress == 0 ? null : s.uploadProgress),
          ],
        );
      case PocketGuitarPhase.ready:
        return s.launch == GameLaunch.app
            ? const BigStatus('READY', 'Strum on the board or press Play')
            : const BigStatus('READY', 'Strum on the board to play');
      case PocketGuitarPhase.countIn:
        return const BigStatus('GET READY', 'Count-in…');
      case PocketGuitarPhase.playing:
        return BigStatus('${s.score}', s.mode == PocketGuitarSession.modePractice ? 'Practice' : 'Streak ×${s.multiplier}');
      case PocketGuitarPhase.paused:
        return BigStatus('PAUSED', 'Score ${s.score}');
      case PocketGuitarPhase.result:
      case PocketGuitarPhase.closed:
        return s.result != null ? _resultCard() : const BigStatus('CLOSED', 'Pocket Guitar was closed on the board');
      case PocketGuitarPhase.error:
        return Text(s.message ?? 'Something went wrong.',
            textAlign: TextAlign.center, style: const TextStyle(color: Colors.orangeAccent));
      case PocketGuitarPhase.noBoard:
        return const SizedBox.shrink();
    }
  }

  Widget _resultCard() {
    final r = _session.result!;
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(
            5,
            (i) => Icon(i < r.stars ? Icons.star : Icons.star_border, color: Colors.orangeAccent, size: 34),
          ),
        ),
        const SizedBox(height: 6),
        Text('${r.score}', style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w700, color: Colors.white)),
        Text('Accuracy ${r.accuracy}% · best streak ${r.bestStreak}', style: const TextStyle(color: Colors.white54)),
        if (r.newBest || r.flawless) ...[
          const SizedBox(height: 6),
          Text(
            [if (r.flawless) 'FLAWLESS', if (r.newBest) 'NEW BEST'].join(' · '),
            style: const TextStyle(color: Colors.greenAccent, letterSpacing: 2, fontWeight: FontWeight.w600),
          ),
        ],
      ],
    );
  }

  Widget _difficulties() {
    final s = _session;
    final editable = s.launch == GameLaunch.app && (s.phase == PocketGuitarPhase.ready || s.phase == PocketGuitarPhase.result);
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 8,
      children: [
        for (var d = 0; d < PocketGuitarSession.difficultyNames.length; d++)
          ChoiceChip(
            label: Text(PocketGuitarSession.difficultyNames[d]),
            selected: s.difficulty == d,
            selectedColor: _difficultyColors[d].withValues(alpha: 0.35),
            onSelected: editable && s.availableDifficulties & (1 << d) != 0
                ? (_) {
                    HapticFeedback.selectionClick();
                    s.selectDifficulty(d);
                  }
                : null,
          ),
      ],
    );
  }

  List<Widget> _controls() {
    final s = _session;
    switch (s.phase) {
      case PocketGuitarPhase.ready:
      case PocketGuitarPhase.result:
        if (s.launch == GameLaunch.board) return const [];
        return [
          Row(
            children: [
              Expanded(child: GameButton('PLAY', Icons.play_arrow, _red, () => s.startSong(PocketGuitarSession.modePlay))),
              const SizedBox(width: 12),
              Expanded(
                  child: GameButton('PRACTICE', Icons.school, _blue, () => s.startSong(PocketGuitarSession.modePractice))),
            ],
          ),
        ];
      case PocketGuitarPhase.countIn:
      case PocketGuitarPhase.playing:
        return [GameButton('PAUSE', Icons.pause, Colors.white24, s.pause)];
      case PocketGuitarPhase.paused:
        return [
          Row(
            children: [
              Expanded(child: GameButton('RESUME', Icons.play_arrow, _red, s.resume)),
              const SizedBox(width: 12),
              Expanded(child: GameButton('QUIT SONG', Icons.stop, Colors.white24, s.quitSong)),
            ],
          ),
        ];
      case PocketGuitarPhase.error:
        if (s.launch == GameLaunch.board) return const [];
        return [GameButton('TRY ANOTHER SONG', Icons.shuffle, Colors.white24, s.nextRandomSong)];
      default:
        return const [];
    }
  }

  Widget _delayOffset() {
    final s = _session;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text('Audio delay', style: TextStyle(color: Colors.white54)),
        IconButton(
          icon: const Icon(Icons.remove_circle_outline),
          color: Colors.white54,
          onPressed: s.isRunning ? null : () => s.changeDelayOffset(-10),
        ),
        SizedBox(
          width: 64,
          child: Text('${s.delayOffsetMs} ms', textAlign: TextAlign.center, style: const TextStyle(color: Colors.white)),
        ),
        IconButton(
          icon: const Icon(Icons.add_circle_outline),
          color: Colors.white54,
          onPressed: s.isRunning ? null : () => s.changeDelayOffset(10),
        ),
      ],
    );
  }
}
