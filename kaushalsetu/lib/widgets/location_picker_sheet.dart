import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:kaushalsetu/core/auth/auth_provider.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';

Future<bool?> showChangeLocationSheet(BuildContext context, {VoidCallback? onLocationUpdated}) {
  final auth = context.read<AuthProvider>();
  final currentProfile = auth.userProfile;
  final localityController = TextEditingController(text: currentProfile?.locality ?? '');
  final cityController = TextEditingController(text: currentProfile?.city ?? 'Bengaluru');

  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) {
      bool isSubmitting = false;
      return StatefulBuilder(
        builder: (context, setModalState) {
          return Padding(
            padding: EdgeInsets.only(
              left: 20,
              right: 20,
              top: 20,
              bottom: MediaQuery.of(context).viewInsets.bottom + 20,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.location_on, color: AppTheme.primaryAmber, size: 24),
                        SizedBox(width: 8),
                        Text(
                          'Set Location',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            color: AppTheme.secondaryNavy,
                          ),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                const Text(
                  'Your location is saved to your account and used for accurate technician matching and on-site service.',
                  style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: localityController,
                  enabled: !isSubmitting,
                  decoration: const InputDecoration(
                    labelText: 'Locality / Area / Neighborhood *',
                    hintText: 'e.g. Pune, Kothrud or Indiranagar',
                    prefixIcon: Icon(Icons.home_work_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: cityController,
                  enabled: !isSubmitting,
                  decoration: const InputDecoration(
                    labelText: 'City *',
                    hintText: 'e.g. Pune or Bengaluru',
                    prefixIcon: Icon(Icons.location_city_outlined),
                  ),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          final loc = localityController.text.trim();
                          final city = cityController.text.trim();
                          if (loc.isEmpty) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Please enter your locality/area.'), backgroundColor: Colors.red),
                            );
                            return;
                          }

                          setModalState(() => isSubmitting = true);
                          final messenger = ScaffoldMessenger.of(context);
                          final success = await auth.updateProfile(
                            locality: loc,
                            city: city.isNotEmpty ? city : null,
                          );

                          if (ctx.mounted) Navigator.pop(ctx, success);

                          if (success) {
                            messenger.showSnackBar(
                              SnackBar(
                                content: Text('Location updated: $loc${city.isNotEmpty ? ", $city" : ""}'),
                                backgroundColor: Colors.green,
                              ),
                            );
                            onLocationUpdated?.call();
                          } else {
                            messenger.showSnackBar(
                              SnackBar(
                                content: Text(auth.errorMessage ?? 'Failed to update location.'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        },
                  child: isSubmitting
                      ? const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            ),
                            SizedBox(width: 10),
                            Text('Saving Location...'),
                          ],
                        )
                      : const Text('Save Location'),
                ),
              ],
            ),
          );
        },
      );
    },
  );
}
