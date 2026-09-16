import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/board_games.dart';
import '../models/piano_tiles_track.dart';
import '../services/ble_service.dart';
import '../services/piano_tiles_session.dart';
import '../state/play_time.dart';
import '../widgets/game_ui.dart';

/// Piano Tiles: the board deals the tiles, every tapped tile plays the song on. Pick a song and a mode here.
class PianoTilesScreen extends ConsumerStatefulWidget {
  const PianoTilesScreen({super.key, this.launch = GameLaunch.app});

  final GameLaunch launch;

  @override
  ConsumerState<PianoTilesScreen> createState() => _PianoTilesScreenState();
}

class _PianoTilesScreenState extends ConsumerState<PianoTilesScreen> {
  late final PianoTilesSession _session;
  late final PlayTimeTracker _tracker;
  final DateTime _openedAt = DateTime.now();

  static const Color _accent = Color(0xFF0096FF);

  @override
  void initState() {
    super.initState();
    _tracker = ref.read(playTimeProvider.notifier)..attachScreen(BleGameId.pianoTiles);
    _session = PianoTilesSession()..start(widget.launch);
  }

  @override
  void dispose() {
    _session.dispose();
    _tracker.detachScreen(BleGameId.pianoTiles);
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
                const GameHeader(title: 'PIANO TILES'),
                const SizedBox(height: 12),
                Expanded(
                  child: _session.phase == PianoTilesPhase.noBoard
                      ? const NoBoardHint(game: 'Piano Tiles')
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _songCard(),
        const SizedBox(height: 20),
        if (s.launch == GameLaunch.app) ...[
          ModeChips(
            names: PianoTilesSession.modeNames,
            selected: s.mode,
            enabled: s.canChange,
            color: _accent,
            onSelected: s.selectMode,
          ),
          const SizedBox(height: 4),
          Text(
            PianoTilesSession.modeDescriptions[s.mode],
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: Colors.white38),
          ),
        ] else
          Text(
            '${PianoTilesSession.modeNames[s.mode]} · started on the board',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, letterSpacing: 1, color: Colors.white54),
          ),
        const SizedBox(height: 24),
        _status(),
        const SizedBox(height: 24),
        ..._controls(),
        const SizedBox(height: 20),
        EarnedTimeCard(gameId: BleGameId.pianoTiles, since: _openedAt),
        const SizedBox(height: 12),
        Text(
          s.isRunning
              ? 'Keep tapping and the song keeps playing. Hold both mechanical keys for 2 s to go back.'
              : 'On the board: tap the pulsing start tile at the bottom to start.',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, color: Colors.white38),
        ),
      ],
    );
  }

  Widget _songCard() {
    final s = _session;
    final song = s.song;
    final canPick = s.canChange && s.catalog.length > 1;
    return Material(
      color: Colors.white.withValues(alpha: 0.06),
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: canPick ? _pickSong : null,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Icon(Icons.piano, size: 36, color: Colors.white70),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      song?.title ?? 'Loading songs…',
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white),
                    ),
                    const SizedBox(height: 2),
                    if (song != null)
                      Text('${song.composer} · ${song.performer}', style: const TextStyle(color: Colors.white54)),
                  ],
                ),
              ),
              if (s.launch == GameLaunch.app)
                IconButton(
                  tooltip: 'Another random song',
                  icon: const Icon(Icons.shuffle),
                  color: Colors.white70,
                  onPressed: canPick
                      ? () {
                          HapticFeedback.selectionClick();
                          s.nextRandomSong();
                        }
                      : null,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _pickSong() async {
    final s = _session;
    final picked = await showModalBottomSheet<PianoTilesTrack>(
      context: context,
      backgroundColor: const Color(0xFF1C1C1E),
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('PICK A SONG', style: TextStyle(letterSpacing: 3, fontWeight: FontWeight.w600, color: Colors.white70)),
            ),
            for (final song in s.catalog)
              ListTile(
                leading: Icon(song.id == s.song?.id ? Icons.check_circle : Icons.music_note, color: Colors.white70),
                title: Text(song.title, style: const TextStyle(color: Colors.white)),
                subtitle: Text('${song.composer} · ${song.performer}', style: const TextStyle(color: Colors.white54)),
                onTap: () => Navigator.pop(context, song),
              ),
          ],
        ),
      ),
    );
    if (picked != null && mounted) {
      HapticFeedback.selectionClick();
      await s.selectSong(picked);
    }
  }

  Widget _status() {
    final s = _session;
    switch (s.phase) {
      case PianoTilesPhase.loading:
        return const Center(child: CircularProgressIndicator());
      case PianoTilesPhase.ready:
        return const BigStatus('READY', 'Tap the start tile on the board');
      case PianoTilesPhase.playing:
        return switch (s.mode) {
          PianoTilesSession.modeClassic => BigStatus('${s.tiles} / ${s.goal}', _seconds(s.elapsedMs)),
          PianoTilesSession.modeZen => BigStatus('${s.tiles}', s.secondsLeft == null ? 'Tiles' : 'Tiles · ${s.secondsLeft} s left'),
          _ => BigStatus('${s.tiles}', 'Tiles · speed ${s.speedLevel + 1}'),
        };
      case PianoTilesPhase.paused:
        return BigStatus('PAUSED', '${s.tiles} tiles · resume here or press a pad on the board');
      case PianoTilesPhase.gameOver:
        return BigStatus('MISSED', '${s.tiles} tiles', color: Colors.redAccent);
      case PianoTilesPhase.result:
        return _result();
      case PianoTilesPhase.closed:
        return s.result != null ? _result() : const BigStatus('CLOSED', 'Piano Tiles was closed on the board');
      case PianoTilesPhase.noBoard:
        return const SizedBox.shrink();
    }
  }

  Widget _result() {
    final r = _session.result!;
    final classic = r.mode == PianoTilesSession.modeClassic;
    final big = classic ? (r.finished ? _seconds(r.score) : 'NOT FINISHED') : '${r.tiles}';
    final small = classic ? '${r.tiles} tiles' : 'tiles';
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
        Text(big, style: const TextStyle(fontSize: 40, fontWeight: FontWeight.w700, color: Colors.white)),
        Text(small, style: const TextStyle(color: Colors.white54)),
        if (r.newBest) ...[
          const SizedBox(height: 6),
          const Text('NEW BEST', style: TextStyle(color: Colors.greenAccent, letterSpacing: 2, fontWeight: FontWeight.w600)),
        ],
      ],
    );
  }

  static String _seconds(int ms) => '${(ms / 1000).toStringAsFixed(2)} s';

  List<Widget> _controls() {
    final s = _session;
    switch (s.phase) {
      case PianoTilesPhase.ready:
      case PianoTilesPhase.result:
      case PianoTilesPhase.closed:
      case PianoTilesPhase.gameOver:
        return [GameButton('NEW TILES', Icons.refresh, _accent, s.phase == PianoTilesPhase.gameOver ? null : s.newTiles)];
      case PianoTilesPhase.playing:
        return [GameButton('PAUSE', Icons.pause, Colors.white24, s.pause)];
      case PianoTilesPhase.paused:
        return [
          Row(
            children: [
              Expanded(child: GameButton('RESUME', Icons.play_arrow, _accent, s.resume)),
              const SizedBox(width: 12),
              Expanded(child: GameButton('QUIT RUN', Icons.stop, Colors.white24, s.quitRun)),
            ],
          ),
        ];
      case PianoTilesPhase.loading:
      case PianoTilesPhase.noBoard:
        return const [];
    }
  }
}
