import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'models/board_games.dart';
import 'screens/freeplay_screen.dart';
import 'screens/game_menu_screen.dart';
import 'screens/home_screen.dart';
import 'screens/piano_tiles_screen.dart';
import 'screens/pocket_guitar_screen.dart';
import 'screens/simon_says_screen.dart';
import 'screens/sound_library_screen.dart';
import 'screens/soundboard_editor_screen.dart';
import 'screens/soundboard_library_screen.dart';
import 'screens/soundboard_play_screen.dart';
import 'screens/debug_screen.dart';
import 'screens/screen_time_setup_screen.dart';
import 'screens/splash_screen.dart';
import 'screens/notification_test_screen.dart';
import 'state/app_state.dart';
import 'state/play_time.dart';
import 'state/session_manager.dart';
import 'services/ble_service.dart';
import 'services/notification_service.dart';
import 'services/sound_cache.dart';

/// DRV2605L library effect "Buzz 1 100%" - the board's own games already use
/// this as their mistake/game-over cue (see RaspberryMicroPython's
/// pianoTiles_control.py _FX_MISTAKE), so it reads as "attention, stop" on
/// hardware that's already felt elsewhere in the app.
const int _kSessionLockedHapticEffect = 47;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.instance.initialize();
  await NotificationService.instance.scheduleRoadblockReminder();
  unawaited(SoundCache.instance.preload());

  runApp(const ProviderScope(child: ProductiveRoadblockApp()));
}

class ProductiveRoadblockApp extends ConsumerStatefulWidget {
  const ProductiveRoadblockApp({super.key});

  @override
  ConsumerState<ProductiveRoadblockApp> createState() =>
      _ProductiveRoadblockAppState();
}

class _ProductiveRoadblockAppState extends ConsumerState<ProductiveRoadblockApp>
    with WidgetsBindingObserver {
  final GlobalKey<NavigatorState> _navigatorKey = GlobalKey<NavigatorState>();
  late final _TopRouteObserver _routes = _TopRouteObserver(_onTopRouteChanged);
  AppLifecycleState? _lastLifecycleState;
  StreamSubscription<int>? _boardStartedGames;
  StreamSubscription<void>? _gameScreensClosed;

  /// The session locked or unlocked while a game screen was open; switch the root screen once it closes.
  bool _rootSwitchPending = false;

  /// A game the board started during the splash, opened once the splash is gone.
  int? _pendingBoardGame;

  static const Set<String> _gameRoutes = {'/simon-says', '/piano-tiles', '/pocket-guitar', '/freeplay'};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final tracker = ref.read(playTimeProvider.notifier);
    _boardStartedGames = tracker.boardStartedGames.listen(_openBoardGame);
    _gameScreensClosed = tracker.gameScreensClosed.listen((_) => _applyPendingRootSwitch());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _boardStartedGames?.cancel();
    _gameScreensClosed?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // iOS usually suspends this app rather than killing it (e.g. when the
    // Shortcuts automation reopens it), so `main()` never reruns and the
    // splash screen would otherwise only ever show once. Replay it on every
    // return from the background instead.
    final wasBackgrounded = _lastLifecycleState == AppLifecycleState.paused;
    _lastLifecycleState = state;

    if (state == AppLifecycleState.resumed && wasBackgrounded) {
      // Not during a game: closing its screen would quit the run on the board
      if (ref.read(playTimeProvider.notifier).hasGameScreen) return;
      _navigatorKey.currentState?.pushNamedAndRemoveUntil(
        '/splash',
        (route) => false,
      );
    }
  }

  /// The board opened or started a game that has no screen: show it, following the board.
  void _openBoardGame(int gameId) {
    final route = routeForBoardGame(gameId);
    final navigator = _navigatorKey.currentState;
    if (route == null || navigator == null) return;
    if (_routes.top == null || _routes.top == '/splash') {
      _pendingBoardGame = gameId;
      return;
    }
    // Already open, or opening (the board sends "game opened" and "running" back to back)
    if (_routes.top == route || ref.read(playTimeProvider.notifier).isScreenAttached(gameId)) return;
    navigator.popUntil((top) => top is PageRoute); // close sheets and dialogs first
    if (_gameRoutes.contains(_routes.top)) {
      navigator.pushReplacementNamed(route, arguments: GameLaunch.board);
    } else {
      navigator.pushNamed(route, arguments: GameLaunch.board);
    }
  }

  void _onTopRouteChanged(String? route) {
    final pending = _pendingBoardGame;
    if (pending == null || route == null || route == '/splash') return;
    _pendingBoardGame = null;
    WidgetsBinding.instance.addPostFrameCallback((_) => _openBoardGame(pending));
  }

  void _switchRoot(bool unlocked) {
    final navigator = _navigatorKey.currentState;
    if (navigator == null || _routes.top == '/splash') return; // the splash picks the root itself
    navigator.pushNamedAndRemoveUntil(unlocked ? '/home' : '/blocking', (route) => false);
  }

  void _applyPendingRootSwitch() {
    if (!_rootSwitchPending) return;
    _rootSwitchPending = false;
    _switchRoot(ref.read(sessionManagerProvider).isUnlocked);
  }

  static GameLaunch _launch(BuildContext context) =>
      ModalRoute.of(context)?.settings.arguments as GameLaunch? ?? GameLaunch.app;

  @override
  Widget build(BuildContext context) {
    ref.listen<SessionState>(sessionManagerProvider, (previous, next) {
      final previousUnlocked = previous?.isUnlocked ?? false;
      if (previousUnlocked == next.isUnlocked) {
        return;
      }

      if (!next.isUnlocked) {
        ref.read(appProvider.notifier).resetLock();
        // The app already shows the roadblock full-screen and fires a
        // notification (SessionManager.lockSession); give the board itself
        // physical feedback too, since it has haptics and the player's
        // attention might currently be on it, not the phone.
        if (BleService().isConnected) {
          unawaited(BleService().sendCommand(
            [BleCommand.gameControl, BleCommand.triggerHaptic, _kSessionLockedHapticEffect],
          ));
        }
      }
      // Keep a game (and the time it just earned) on screen; switch when it closes
      if (ref.read(playTimeProvider.notifier).hasGameScreen) {
        _rootSwitchPending = true;
        return;
      }
      _switchRoot(next.isUnlocked);
    });

    return MaterialApp(
      navigatorKey: _navigatorKey,
      navigatorObservers: [_routes],
      title: 'Productive Roadblock',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: Colors.black,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.black,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.w300,
          ),
          iconTheme: IconThemeData(color: Colors.white),
        ),
        colorScheme: const ColorScheme.dark(
          primary: Colors.white,
          surface: Colors.black,
        ),
        useMaterial3: true,
      ),
      initialRoute: '/splash',
      routes: {
        '/splash': (_) => const SplashScreen(),
        '/setup': (_) => const ScreenTimeSetupScreen(),
        '/blocking': (_) => const GameMenuScreen(locked: true),
        '/home': (_) => const HomeScreen(),
        '/games': (_) => const GameMenuScreen(),
        '/simon-says': (context) => SimonSaysScreen(launch: _launch(context)),
        '/piano-tiles': (context) => PianoTilesScreen(launch: _launch(context)),
        '/pocket-guitar': (context) => PocketGuitarScreen(launch: _launch(context)),
        '/freeplay': (_) => const FreeplayScreen(),
        '/soundboards': (_) => const SoundboardLibraryScreen(),
        '/soundboard-play': (_) => const SoundboardPlayScreen(),
        '/soundboard-editor': (_) => const SoundboardEditorScreen(),
        '/sound-library': (_) => const SoundLibraryScreen(),
        '/debug': (_) => const DebugScreen(),
        '/notification-test': (_) => const NotificationTestScreen(),
      },
    );
  }
}

/// Keeps track of the page on top of the navigator (dialogs, sheets and popup menus don't count).
class _TopRouteObserver extends NavigatorObserver {
  _TopRouteObserver(this.onChanged);

  final void Function(String? route) onChanged;
  Route<dynamic>? _top;

  /// Name of the top page, e.g. `/home`.
  String? get top => _top?.settings.name;

  void _set(Route<dynamic>? route) {
    _top = route;
    onChanged(top);
  }

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    if (route is PageRoute) _set(route);
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    if (oldRoute == _top) _set(newRoute);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    if (route == _top) _set(previousRoute);
  }

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) {
    if (route == _top) _set(previousRoute);
  }
}
