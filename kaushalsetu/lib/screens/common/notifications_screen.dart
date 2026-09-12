import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/app_notification.dart';
import 'package:kaushalsetu/services/notification_service.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final NotificationService _notificationService = NotificationService();

  bool _isLoading = true;
  List<AppNotification> _notifications = [];

  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() => _isLoading = true);
    try {
      final notifs = await _notificationService.listNotifications();
      _notifications = notifs;
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _markRead(String id) async {
    try {
      await _notificationService.markAsRead(id);
      _loadNotifications();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadNotifications),
        ],
      ),
      body: _isLoading
          ? const LoadingView(message: 'Loading notifications...')
          : _notifications.isEmpty
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text('No notifications yet.', style: TextStyle(color: Colors.grey)),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  itemCount: _notifications.length,
                  itemBuilder: (context, idx) {
                    final n = _notifications[idx];
                    return Card(
                      color: n.isRead ? Colors.white : const Color(0xFFF0FDF4),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: AppTheme.primaryAmber.withValues(alpha: 0.15),
                          child: const Icon(Icons.notifications_active_outlined, color: AppTheme.primaryAmber, size: 20),
                        ),
                        title: Text(
                          n.title,
                          style: TextStyle(
                            fontWeight: n.isRead ? FontWeight.w600 : FontWeight.w800,
                            fontSize: 14,
                          ),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 4),
                            Text(n.message, style: const TextStyle(fontSize: 12, color: Color(0xFF475569))),
                            const SizedBox(height: 4),
                            Text(
                              n.createdAt.toLocal().toString().substring(0, 16),
                              style: const TextStyle(fontSize: 10, color: Colors.grey),
                            ),
                          ],
                        ),
                        trailing: n.isRead
                            ? null
                            : IconButton(
                                icon: const Icon(Icons.done, size: 18, color: Colors.green),
                                tooltip: 'Mark as read',
                                onPressed: () => _markRead(n.id),
                              ),
                      ),
                    );
                  },
                ),
    );
  }
}
