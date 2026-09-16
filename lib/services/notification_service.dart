import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  NotificationService._();

  static final NotificationService instance = NotificationService._();
  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  static const int _roadblockNotificationId = 1001;
  static const int _instantNotificationId = 1002;
  static const String _roadblockChannelId = 'roadblock_reminders';

  Future<void> initialize() async {
    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );

    // presentAlert/Badge/Sound default to true, and the AppDelegate sets
    // itself as the UNUserNotificationCenter delegate, so these show even
    // while the app is in the foreground.
    final darwinSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
      onDidReceiveLocalNotification: (id, title, body, payload) async {
        debugPrint('[NotificationService] Received local notification: $title');
      },
    );

    const linuxSettings = LinuxInitializationSettings(
      defaultActionName: 'Open notification',
    );

    final settings = InitializationSettings(
      android: androidSettings,
      iOS: darwinSettings,
      macOS: darwinSettings,
      linux: linuxSettings,
    );

    // Handle notification tap to open app
    await _plugin.initialize(
      settings,
      onDidReceiveNotificationResponse: (details) async {
        debugPrint('[NotificationService] Notification tapped: ${details.payload}');
      },
    );

    // Request permissions explicitly for iOS
    final iosPlugin = _plugin.resolvePlatformSpecificImplementation<
        IOSFlutterLocalNotificationsPlugin>();

    if (iosPlugin != null) {
      final granted = await iosPlugin.requestPermissions(
        alert: true,
        badge: true,
        sound: true,
      );
      debugPrint('[NotificationService] iOS permissions granted: $granted');
    }
  }

  Future<void> scheduleRoadblockReminder() async {
    const androidDetails = AndroidNotificationDetails(
      _roadblockChannelId,
      'Roadblock Reminders',
      channelDescription: 'Reminder notifications for Productive Roadblock',
      importance: Importance.high,
      priority: Priority.high,
    );
    const details = NotificationDetails(
      android: androidDetails,
      iOS: DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      ),
      macOS: DarwinNotificationDetails(),
    );

    try {
      await _plugin.periodicallyShow(
        _roadblockNotificationId,
        'Time for Roadblock',
        'Take a focus checkpoint before opening Instagram.',
        RepeatInterval.daily,
        details,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    } on UnimplementedError {
      debugPrint(
        '[NotificationService] periodicallyShow unsupported on this platform',
      );
    }
  }

  /// Show immediate notification to unlock Instagram.
  Future<void> showInstagramBlockedNotification() async {
    const androidDetails = AndroidNotificationDetails(
      _roadblockChannelId,
      'Instagram Blocked',
      channelDescription: 'Instagram is blocked - play a game to unlock',
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      enableVibration: true,
    );
    
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      badgeNumber: 1,
    );
    
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
      macOS: DarwinNotificationDetails(),
    );

    try {
      await _plugin.show(
        _instantNotificationId,
        '🚫 Instagram Blocked',
        'Play a game on the board to earn Instagram time',
        details,
        payload: 'instagram_blocked',
      );
    } catch (e) {
      debugPrint('[NotificationService] Error showing notification: $e');
      rethrow;
    }
  }

  Future<void> showNotification(String message) async {
    const androidDetails = AndroidNotificationDetails(
      _roadblockChannelId,
      'Roadblock Reminders',
      channelDescription: 'Reminder notifications for Productive Roadblock',
      importance: Importance.high,
      priority: Priority.high,
    );
    
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );
    
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
      macOS: DarwinNotificationDetails(),
    );

    await _plugin.show(
      _instantNotificationId,
      'Productive Roadblock',
      message,
      details,
    );
  }

  Future<void> cancelAll() async {
    await _plugin.cancelAll();
  }
}
