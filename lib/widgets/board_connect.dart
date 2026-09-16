import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/ble_service.dart';
import '../state/app_state.dart';

/// Scans for the board and connects to the first one found.
class BoardConnectButton extends ConsumerStatefulWidget {
  const BoardConnectButton({super.key});

  @override
  ConsumerState<BoardConnectButton> createState() => _BoardConnectButtonState();
}

class _BoardConnectButtonState extends ConsumerState<BoardConnectButton> {
  bool _isScanning = false;

  Future<void> _scanAndConnect() async {
    if (_isScanning) return;

    setState(() => _isScanning = true);
    HapticFeedback.mediumImpact();

    try {
      final devices = await ref.read(appProvider.notifier).scanDevices();

      if (!mounted) return;

      if (devices.isEmpty) {
        _showMessage('No devices found');
        return;
      }

      final success = await ref.read(appProvider.notifier).connectDevice(devices.first);

      if (!mounted) return;

      _showMessage(success ? 'Connected to ${devices.first.platformName}' : 'Connection failed');
    } catch (e) {
      if (mounted) {
        _showMessage('Error: ${e.toString()}');
      }
    } finally {
      if (mounted) {
        setState(() => _isScanning = false);
      }
    }
  }

  void _showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: _isScanning ? null : _scanAndConnect,
      icon: _isScanning
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
            )
          : const Icon(Icons.bluetooth_searching),
      label: Text(_isScanning ? 'SCANNING...' : 'SCAN & CONNECT'),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
      ),
    );
  }
}

/// What the board connection is doing, in the app's upper-case status style.
String boardStatusText(BleConnectionState state) => switch (state) {
      BleConnectionState.connected => 'BOARD CONNECTED',
      BleConnectionState.scanning => 'SCANNING...',
      BleConnectionState.connecting => 'CONNECTING...',
      BleConnectionState.bluetoothDisabled => 'BLUETOOTH IS DISABLED',
      _ => 'NO BOARD',
    };
