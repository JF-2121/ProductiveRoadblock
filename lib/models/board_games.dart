import '../services/ble_service.dart';

/// How a game screen was opened: from the app's game menu (the app selects the mode or song and opens the game
/// on the board), or because the game was opened or started on the board (the screen only follows it).
enum GameLaunch { app, board }

/// Screen id of the on-phone game for [PlayTimeTracker.attachScreen]; board games use their [BleGameId].
const int phoneGameScreenId = -1;

/// Route of the app screen that follows a board game ([BleGameId]), or null for the start screen.
String? routeForBoardGame(int gameId) => switch (gameId) {
      BleGameId.simonSays => '/simon-says',
      BleGameId.pianoTiles => '/piano-tiles',
      BleGameId.pocketGuitar => '/pocket-guitar',
      _ => null,
    };

bool isBoardGame(int gameId) => routeForBoardGame(gameId) != null;
