import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/board_games.dart';
import '../services/ble_service.dart';
import '../services/simon_says_session.dart';
import '../state/play_time.dart';
import '../widgets/game_ui.dart';

/// Simon Says: the game runs on the board, this screen plays the tones and shows the round, lives and result.
class SimonSaysScreen extends ConsumerStatefulWidget {
  const SimonSaysScreen({super.key, this.launch = GameLaunch.app});

  final GameLaunch launch;

  @override
  ConsumerState<SimonSaysScreen> createState() => _SimonSaysScreenState();
}

class _SimonSaysScreenState extends ConsumerState<SimonSaysScreen> {
  late final SimonSaysSession _session;
  late final PlayTimeTracker _tracker;
  final DateTime _openedAt = DateTime.now();

  static const Color _accent = Color(0xFFFF00C8);

  /// The board's block colours (game/simonSays/simon_says_control.py).
  static const List<Color> blockColors = [
    Color(0xFFFF0000),
    Color(0xFF00FF00),
    Color(0xFF003CFF),
    Color(0xFFFFC800),
    Color(0xFFFF00C8),
    Color(0xFF00DCFF),
    Color(0xFFFF5A00),
    Color(0xFFC8C8C8),
  ];

  @override
  void initState() {
    super.initState();
    _tracker = ref.read(playTimeProvider.notifier)..attachScreen(BleGameId.simonSays);
    _session = SimonSaysSession()..start(widget.launch);
  }

  @override
  void dispose() {
    _session.dispose();
    _tracker.detachScreen(BleGameId.simonSays);
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
                const GameHeader(title: 'SIMON SAYS'),
                const SizedBox(height: 12),
                Expanded(
                  child: _session.phase == SimonSaysPhase.noBoard
                      ? const NoBoardHint(game: 'Simon Says')
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
        if (s.launch == GameLaunch.app) ...[
          ModeChips(
            names: SimonSaysSession.modeNames,
            selected: s.mode,
            enabled: s.canChangeMode,
            color: _accent,
            onSelected: s.selectMode,
          ),
          const SizedBox(height: 4),
          Text(
            SimonSaysSession.modeDescriptions[s.mode],
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: Colors.white38),
          ),
        ] else
          Text(
            '${SimonSaysSession.modeNames[s.mode]} · started on the board',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, letterSpacing: 1, color: Colors.white54),
          ),
        const SizedBox(height: 20),
        _status(),
        const SizedBox(height: 20),
        Center(child: _blocks()),
        const SizedBox(height: 24),
        ..._controls(),
        const SizedBox(height: 20),
        EarnedTimeCard(gameId: BleGameId.simonSays, since: _openedAt),
        const SizedBox(height: 12),
        Text(
          s.isRunning
              ? 'On the board: hold both mechanical keys for 2 s to go back.'
              : 'On the board: press any pad to start. Every colour has its own tone.',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, color: Colors.white38),
        ),
      ],
    );
  }

  Widget _status() {
    final s = _session;
    final lives = s.mode == SimonSaysSession.modeEndless ? _lives(s.lives) : null;
    switch (s.phase) {
      case SimonSaysPhase.ready:
        return const BigStatus('READY', 'Press START or any pad on the board');
      case SimonSaysPhase.lives:
        return Column(children: [const BigStatus('GET READY', 'Lives'), ?lives]);
      case SimonSaysPhase.watch:
        return Column(children: [
          BigStatus('WATCH', s.steps > 0 ? 'Round ${s.round} of ${s.steps}' : 'Round ${s.round}'),
          ?lives,
        ]);
      case SimonSaysPhase.turn:
        return Column(children: [
          BigStatus('YOUR TURN', s.steps > 0 ? 'Round ${s.round} of ${s.steps}' : 'Round ${s.round}', color: Colors.greenAccent),
          ?lives,
        ]);
      case SimonSaysPhase.mistake:
        return Column(children: [
          BigStatus(
            s.pressedWrongBlock == null ? 'TOO SLOW' : 'WRONG',
            s.mode == SimonSaysSession.modeEndless && s.lives > 0 ? 'The round starts again' : 'Run over',
            color: Colors.redAccent,
          ),
          ?lives,
        ]);
      case SimonSaysPhase.paused:
        return const BigStatus('PAUSED', 'Resume here or press a pad on the board');
      case SimonSaysPhase.result:
        return _result();
      case SimonSaysPhase.closed:
        return s.result != null ? _result() : const BigStatus('CLOSED', 'Simon Says was closed on the board');
      case SimonSaysPhase.noBoard:
        return const SizedBox.shrink();
    }
  }

  Widget _result() {
    final r = _session.result!;
    return Column(
      children: [
        Text(
          r.won ? 'YOU WON' : 'SCORE',
          style: TextStyle(letterSpacing: 3, fontWeight: FontWeight.w600, color: r.won ? Colors.greenAccent : Colors.white54),
        ),
        Text('${r.score}', style: const TextStyle(fontSize: 48, fontWeight: FontWeight.w700, color: Colors.white)),
        Text('Longest sequence · best ${r.best}', style: const TextStyle(color: Colors.white54)),
        if (r.newBest) ...[
          const SizedBox(height: 6),
          const Text('NEW BEST', style: TextStyle(color: Colors.greenAccent, letterSpacing: 2, fontWeight: FontWeight.w600)),
        ],
      ],
    );
  }

  Widget _lives(int lives) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(
          3,
          (i) => Icon(i < lives ? Icons.favorite : Icons.favorite_border, color: Colors.redAccent, size: 26),
        ),
      ),
    );
  }

  /// The 8 colour blocks as on the board (2 wide, 4 tall), lit when the board shows or you press them.
  Widget _blocks() {
    final s = _session;
    final dim = switch (s.phase) {
      SimonSaysPhase.turn => 0.35,
      SimonSaysPhase.watch || SimonSaysPhase.lives => 0.18,
      _ => 0.25,
    };
    return SizedBox(
      width: 180,
      child: GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        children: [
          for (var block = 0; block < SimonSaysSession.blockCount; block++)
            _block(block, dim),
        ],
      ),
    );
  }

  Widget _block(int block, double dim) {
    final s = _session;
    final color = blockColors[block];
    final mistake = s.phase == SimonSaysPhase.mistake;
    final lit = s.litBlock == block || (mistake && s.rightBlock == block);
    final wrong = mistake && s.pressedWrongBlock == block;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 80),
      decoration: BoxDecoration(
        color: color.withValues(alpha: lit ? 1 : dim),
        borderRadius: BorderRadius.circular(12),
        border: wrong ? Border.all(color: Colors.redAccent, width: 4) : null,
        boxShadow: lit ? [BoxShadow(color: color.withValues(alpha: 0.7), blurRadius: 18, spreadRadius: 1)] : null,
      ),
    );
  }

  List<Widget> _controls() {
    final s = _session;
    switch (s.phase) {
      case SimonSaysPhase.ready:
      case SimonSaysPhase.result:
      case SimonSaysPhase.closed:
        return [GameButton(s.phase == SimonSaysPhase.ready ? 'START' : 'PLAY AGAIN', Icons.play_arrow, _accent, s.startRun)];
      case SimonSaysPhase.lives:
      case SimonSaysPhase.watch:
      case SimonSaysPhase.turn:
      case SimonSaysPhase.mistake:
        return [GameButton('PAUSE', Icons.pause, Colors.white24, s.pause)];
      case SimonSaysPhase.paused:
        return [
          Row(
            children: [
              Expanded(child: GameButton('RESUME', Icons.play_arrow, _accent, s.resume)),
              const SizedBox(width: 12),
              Expanded(child: GameButton('QUIT RUN', Icons.stop, Colors.white24, s.quitRun)),
            ],
          ),
        ];
      case SimonSaysPhase.noBoard:
        return const [];
    }
  }
}
