import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';

class StatusBadge extends StatelessWidget {
  final String status;

  const StatusBadge({super.key, required this.status});

  Color _getBackgroundColor() {
    switch (status.toLowerCase()) {
      case 'pending':
        return AppTheme.statusPending.withValues(alpha: 0.15);
      case 'accepted':
      case 'confirmed':
        return AppTheme.statusAccepted.withValues(alpha: 0.15);
      case 'in_progress':
        return AppTheme.statusInProgress.withValues(alpha: 0.15);
      case 'completed':
      case 'verified':
        return AppTheme.statusCompleted.withValues(alpha: 0.15);
      case 'disputed':
      case 'rejected':
      case 'cancelled':
        return AppTheme.statusDisputed.withValues(alpha: 0.15);
      default:
        return Colors.grey.withValues(alpha: 0.15);
    }
  }

  Color _getTextColor() {
    switch (status.toLowerCase()) {
      case 'pending':
        return AppTheme.statusPending;
      case 'accepted':
      case 'confirmed':
        return AppTheme.statusAccepted;
      case 'in_progress':
        return AppTheme.statusInProgress;
      case 'completed':
      case 'verified':
        return AppTheme.statusCompleted;
      case 'disputed':
      case 'rejected':
      case 'cancelled':
        return AppTheme.statusDisputed;
      default:
        return Colors.black87;
    }
  }

  String _formatText() {
    return status.replaceAll('_', ' ').toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _getBackgroundColor(),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        _formatText(),
        style: TextStyle(
          color: _getTextColor(),
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}
