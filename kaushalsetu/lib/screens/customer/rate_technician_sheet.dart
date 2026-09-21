import 'package:flutter/material.dart';
import 'package:kaushalsetu/models/job.dart';
import 'package:kaushalsetu/services/verification_service.dart';

void showRateTechnicianSheet({
  required BuildContext context,
  required JobModel job,
  required VoidCallback onSubmitted,
}) {
  double rating = 5.0;
  final commentController = TextEditingController();

  showModalBottomSheet(
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
                        Icon(Icons.star_rounded, color: Colors.amber, size: 26),
                        SizedBox(width: 8),
                        Text(
                          'Rate your technician',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
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
                Text(
                  'Technician: ${job.workerName ?? "Technician"}',
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: Color(0xFF334155)),
                ),
                Text(
                  'Job: ${job.problemTitle ?? "Repair"}',
                  style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                ),
                const SizedBox(height: 16),
                const Center(
                  child: Text(
                    'How was your experience?',
                    style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [1, 2, 3, 4, 5].map((star) {
                    return IconButton(
                      icon: Icon(
                        star <= rating ? Icons.star_rounded : Icons.star_outline_rounded,
                        color: Colors.amber,
                        size: 38,
                      ),
                      onPressed: isSubmitting ? null : () => setModalState(() => rating = star.toDouble()),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: commentController,
                  maxLines: 3,
                  enabled: !isSubmitting,
                  decoration: const InputDecoration(
                    labelText: 'Optional comment',
                    hintText: 'Share feedback about diagnosis quality, timeliness...',
                  ),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          setModalState(() => isSubmitting = true);
                          final messenger = ScaffoldMessenger.of(context);
                          try {
                            final verifService = VerificationService();
                            await verifService.submitFeedback(
                              jobId: job.id,
                              rating: rating,
                              feedbackText: commentController.text.trim().isNotEmpty
                                  ? commentController.text.trim()
                                  : null,
                            );
                            if (ctx.mounted) Navigator.pop(ctx);
                            messenger.showSnackBar(
                              const SnackBar(
                                content: Text('Thank you. Your review has been submitted.'),
                                backgroundColor: Colors.green,
                              ),
                            );
                            onSubmitted();
                          } catch (e) {
                            setModalState(() => isSubmitting = false);
                            if (ctx.mounted) {
                              messenger.showSnackBar(
                                SnackBar(
                                  content: Text(e.toString().contains('already reviewed')
                                      ? 'You have already reviewed this job.'
                                      : 'Failed to submit review: $e'),
                                  backgroundColor: Colors.red,
                                ),
                              );
                            }
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
                            Text('Submitting review...'),
                          ],
                        )
                      : const Text('Submit Review'),
                ),
              ],
            ),
          );
        },
      );
    },
  );
}
