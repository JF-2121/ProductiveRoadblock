import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import '../services/notification_service.dart';

/// Simple screen to test and debug iOS notifications
class NotificationTestScreen extends StatefulWidget {
  const NotificationTestScreen({super.key});

  @override
  State<NotificationTestScreen> createState() => _NotificationTestScreenState();
}

class _NotificationTestScreenState extends State<NotificationTestScreen> {
  String _status = 'Checking permissions...';
  bool? _permissionsGranted;

  @override
  void initState() {
    super.initState();
    _checkPermissions();
  }

  Future<void> _checkPermissions() async {
    final plugin = FlutterLocalNotificationsPlugin();
    final iosPlugin = plugin.resolvePlatformSpecificImplementation<
        IOSFlutterLocalNotificationsPlugin>();

    if (iosPlugin != null) {
      // Check current permission status
      setState(() {
        _status = 'Checking iOS notification permissions...';
      });

      // Request permissions
      final granted = await iosPlugin.requestPermissions(
        alert: true,
        badge: true,
        sound: true,
      );

      setState(() {
        _permissionsGranted = granted ?? false;
        _status = granted == true
            ? 'Permissions GRANTED ✓'
            : 'Permissions DENIED ✗\n\nGo to Settings → Productive Roadblock → Notifications → Allow';
      });
    } else {
      setState(() {
        _status = 'Not running on iOS';
      });
    }
  }

  Future<void> _sendTestNotification() async {
    setState(() {
      _status = 'Sending notification...';
    });

    try {
      await NotificationService.instance.showInstagramBlockedNotification();
      if (mounted) {
        setState(() {
          _status = 'Notification sent ✓';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _status = 'Failed to send notification:\n$e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Notification Test'),
        backgroundColor: Colors.black,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: _permissionsGranted == true
                      ? Colors.green.withValues(alpha: 0.2)
                      : Colors.orange.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _permissionsGranted == true
                        ? Colors.green
                        : Colors.orange,
                  ),
                ),
                child: Text(
                  _status,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 24),
              if (_permissionsGranted == false) ...[
                ElevatedButton(
                  onPressed: _checkPermissions,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.orange,
                    padding: const EdgeInsets.all(16),
                  ),
                  child: const Text('Request Permissions Again'),
                ),
                const SizedBox(height: 16),
                const Text(
                  'If permissions are denied:\n\n'
                  '1. Go to iPhone Settings\n'
                  '2. Scroll to "Productive Roadblock"\n'
                  '3. Tap "Notifications"\n'
                  '4. Enable "Allow Notifications"\n'
                  '5. Come back and tap "Request Permissions Again"',
                  style: TextStyle(color: Colors.white70, fontSize: 14),
                  textAlign: TextAlign.center,
                ),
              ],
              if (_permissionsGranted == true) ...[
                ElevatedButton(
                  onPressed: _sendTestNotification,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF9C27B0),
                    padding: const EdgeInsets.all(16),
                  ),
                  child: const Text(
                    'Send Test Notification',
                    style: TextStyle(fontSize: 16),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'You should see the notification banner immediately, '
                  'even while the app stays open.',
                  style: TextStyle(color: Colors.white70, fontSize: 14),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
