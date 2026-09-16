import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:productive_roadblock/screens/game_menu_screen.dart';
import 'package:productive_roadblock/services/ble_service.dart';
import 'package:productive_roadblock/state/app_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// No board found, without touching Bluetooth.
class NoBoardApp extends AppNotifier {
  @override
  AppState build() => AppState(
        bleState: BleConnectionState.locked,
        targetTapCount: 5,
        roadblockSessionId: 0,
        challengeType: ChallengeType.pianoTiles,
      );
}

void main() {
  testWidgets('lock screen without a board: the board games are disabled, the phone game is offered', (tester) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    final opened = <String>[];
    await tester.pumpWidget(
      ProviderScope(
        overrides: [appProvider.overrideWith(NoBoardApp.new)],
        child: MaterialApp(
          home: const GameMenuScreen(locked: true),
          onGenerateRoute: (settings) {
            opened.add(settings.name!);
            return MaterialPageRoute<void>(builder: (_) => const SizedBox());
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('ROADBLOCK ACTIVE'), findsOneWidget);
    expect(find.text('LOCKED'), findsOneWidget);
    expect(find.text('NO BOARD'), findsOneWidget);
    expect(find.text('SCAN & CONNECT'), findsOneWidget);
    for (final game in ['Simon Says', 'Pocket Guitar', 'Piano Tiles']) {
      expect(find.text(game), findsOneWidget);
    }

    await tester.tap(find.text('Simon Says'));
    await tester.pumpAndSettle();
    expect(opened, isEmpty);

    await tester.scrollUntilVisible(find.text('Play on phone'), 200);
    await tester.tap(find.text('Play on phone'));
    await tester.pumpAndSettle();
    expect(opened, ['/freeplay']);
  });
}
