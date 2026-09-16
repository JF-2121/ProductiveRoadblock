import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import '../services/ble_service.dart';

/// The two on-phone minigame variants (the fallback without a board) —
/// alternated randomly so the game doesn't get memorized/rote.
enum ChallengeType { pianoTiles, simonSays }

class AppState {
  final BleConnectionState bleState;
  final int targetTapCount;
  final int roadblockSessionId;
  final ChallengeType challengeType;

  AppState({
    required this.bleState,
    required this.targetTapCount,
    required this.roadblockSessionId,
    required this.challengeType,
  });

  AppState copyWith({
    BleConnectionState? bleState,
    int? targetTapCount,
    int? roadblockSessionId,
    ChallengeType? challengeType,
  }) {
    return AppState(
      bleState: bleState ?? this.bleState,
      targetTapCount: targetTapCount ?? this.targetTapCount,
      roadblockSessionId: roadblockSessionId ?? this.roadblockSessionId,
      challengeType: challengeType ?? this.challengeType,
    );
  }
}

class AppNotifier extends Notifier<AppState> {
  final BleService _bleService = BleService();
  final Random _random = Random();

  @override
  AppState build() {
    _bleService.initialize();
    _bleService.connectionState.listen(_handleBleStateChange);

    return AppState(
      bleState: BleConnectionState.scanning,
      targetTapCount: _nextTapTarget(),
      roadblockSessionId: 0,
      challengeType: _nextChallengeType(),
    );
  }

  void _handleBleStateChange(BleConnectionState newState) {
    state = state.copyWith(bleState: newState);
  }

  Future<List<BluetoothDevice>> scanDevices() async {
    try {
      return await _bleService.scanForDevices();
    } catch (e) {
      return [];
    }
  }

  Future<bool> connectDevice(BluetoothDevice device) async {
    try {
      return await _bleService.connectToDevice(device);
    } catch (e) {
      return false;
    }
  }

  Future<void> disconnectDevice() async {
    try {
      await _bleService.disconnect();
    } catch (e) {
      // Silent fail on disconnect
    }
  }

  /// Rolls a fresh tile pattern, minigame variant, and session id, forcing
  /// the challenge widget (keyed on roadblockSessionId) to restart.
  void resetLock() {
    state = state.copyWith(
      targetTapCount: _nextTapTarget(),
      roadblockSessionId: state.roadblockSessionId + 1,
      challengeType: _nextChallengeType(),
    );
  }

  int _nextTapTarget() => _random.nextInt(6) + 5;

  ChallengeType _nextChallengeType() =>
      ChallengeType.values[_random.nextInt(ChallengeType.values.length)];
}

final appProvider = NotifierProvider<AppNotifier, AppState>(() {
  return AppNotifier();
});
