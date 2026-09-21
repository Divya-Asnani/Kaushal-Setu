import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/job.dart';
import 'package:kaushalsetu/services/job_service.dart';
import 'package:kaushalsetu/services/verification_service.dart';
import 'package:kaushalsetu/widgets/status_badge.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/widgets/error_view.dart';

class CustomerJobDetailsScreen extends StatefulWidget {
  final String jobId;

  const CustomerJobDetailsScreen({super.key, required this.jobId});

  @override
  State<CustomerJobDetailsScreen> createState() => _CustomerJobDetailsScreenState();
}

class _CustomerJobDetailsScreenState extends State<CustomerJobDetailsScreen> {
  final JobService _jobService = JobService();
  final VerificationService _verifService = VerificationService();

  bool _isLoading = true;
  String? _errorMessage;
  JobModel? _job;

  @override
  void initState() {
    super.initState();
    _loadJob();
  }

  Future<void> _loadJob() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final job = await _jobService.getJob(widget.jobId);
      _job = job;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _handleConfirmRepair() {
    final commentsController = TextEditingController(text: 'Confirmed repair working properly.');
    double rating = 5.0;
    final feedbackController = TextEditingController();

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
                  const Row(
                    children: [
                      Icon(Icons.verified, color: Colors.green, size: 24),
                      SizedBox(width: 8),
                      Text(
                        'Verify Repair & Rate Work',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Verifying this job confirms the fault was resolved and makes the technician’s experience reusable on KaushalSetu.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: commentsController,
                    decoration: const InputDecoration(labelText: 'Verification Note'),
                  ),
                  const SizedBox(height: 16),
                  const Text('Rate Technician Performance:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [1, 2, 3, 4, 5].map((star) {
                      return IconButton(
                        icon: Icon(
                          star <= rating ? Icons.star : Icons.star_border,
                          color: Colors.amber,
                          size: 32,
                        ),
                        onPressed: () => setModalState(() => rating = star.toDouble()),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: feedbackController,
                    maxLines: 2,
                    decoration: const InputDecoration(
                      labelText: 'Feedback Comments',
                      hintText: 'Share how satisfied you are with the repair...',
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: isSubmitting
                        ? null
                        : () async {
                            setModalState(() => isSubmitting = true);
                            try {
                              final messenger = ScaffoldMessenger.of(context);
                              // 1. Verify Job
                              if (!_job!.isVerified) {
                                await _verifService.verifyJob(
                                  widget.jobId,
                                  comments: commentsController.text.trim(),
                                );
                              }
                              // 2. Submit Feedback if not already submitted
                              if (!_job!.hasFeedback) {
                                await _verifService.submitFeedback(
                                  jobId: widget.jobId,
                                  rating: rating,
                                  feedbackText: feedbackController.text.trim().isNotEmpty
                                      ? feedbackController.text.trim()
                                      : null,
                                );
                              }
                              if (ctx.mounted) Navigator.pop(ctx);
                              _loadJob();
                              if (mounted) {
                                messenger.showSnackBar(
                                  const SnackBar(
                                    content: Text('Thank you! Job verified and review submitted.'),
                                    backgroundColor: Colors.green,
                                  ),
                                );
                              }
                            } catch (e) {
                              setModalState(() => isSubmitting = false);
                              if (ctx.mounted) {
                                ScaffoldMessenger.of(ctx).showSnackBar(
                                  SnackBar(content: Text('Verification error: $e'), backgroundColor: Colors.red),
                                );
                              }
                            }
                          },
                    child: isSubmitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('Confirm Verification & Submit Rating'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _handleDispute() {
    final disputeController = TextEditingController();

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
                  const Row(
                    children: [
                      Icon(Icons.warning_amber_rounded, color: Colors.red, size: 24),
                      SizedBox(width: 8),
                      Text(
                        'Raise Repair Dispute',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'If the device or appliance still malfunctions after the repair, explain what is not working.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: disputeController,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Describe Unresolved Symptoms *',
                      hintText: 'e.g. Device powers off after 10 minutes, still tripping MCB...',
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                    onPressed: isSubmitting
                        ? null
                        : () async {
                            if (disputeController.text.trim().isEmpty) {
                              ScaffoldMessenger.of(ctx).showSnackBar(
                                const SnackBar(content: Text('Please explain the issue.')),
                              );
                              return;
                            }
                            setModalState(() => isSubmitting = true);
                            final messenger = ScaffoldMessenger.of(context);
                            try {
                              await _verifService.disputeJob(
                                widget.jobId,
                                comments: disputeController.text.trim(),
                              );
                              if (ctx.mounted) Navigator.pop(ctx);
                              _loadJob();
                              if (mounted) {
                                messenger.showSnackBar(
                                  const SnackBar(
                                    content: Text('Dispute submitted. Technician notified.'),
                                    backgroundColor: Colors.red,
                                  ),
                                );
                              }
                            } catch (e) {
                              setModalState(() => isSubmitting = false);
                              if (ctx.mounted) {
                                ScaffoldMessenger.of(ctx).showSnackBar(
                                  SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
                                );
                              }
                            }
                          },
                    child: isSubmitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('Submit Dispute'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Job Details')),
        body: const LoadingView(message: 'Loading job information & evidence...'),
      );
    }

    if (_errorMessage != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Job Details')),
        body: ErrorView(
          title: 'Could not load job',
          message: _errorMessage!,
          onRetry: _loadJob,
        ),
      );
    }

    final job = _job!;

    return Scaffold(
      appBar: AppBar(
        title: Text(job.problemTitle ?? 'Job Engagement'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadJob),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status Header
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Status',
                        style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                      ),
                      const SizedBox(height: 4),
                      StatusBadge(status: job.status),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Text(
                        'Assigned Technician',
                        style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        job.workerName ?? 'Technician',
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Technician Completion Diagnosis & Actions Review
            if (job.diagnosis != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.assignment_turned_in, color: AppTheme.primaryAmber, size: 20),
                          SizedBox(width: 8),
                          Text(
                            'Technician Diagnosis',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        job.diagnosis!,
                        style: const TextStyle(fontSize: 13, color: Color(0xFF334155), height: 1.4),
                      ),
                      if (job.actions.isNotEmpty) ...[
                        const Divider(height: 24),
                        const Text(
                          'Actions Performed:',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                        ),
                        const SizedBox(height: 8),
                        ...job.actions.map((act) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${act.stepNumber}. ', style: const TextStyle(fontWeight: FontWeight.bold)),
                                Expanded(
                                  child: Text(
                                    '${act.actionType.toUpperCase()}: ${act.actionDescription}',
                                    style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }),
                      ],
                      if (job.outcomes.isNotEmpty) ...[
                        const Divider(height: 24),
                        const Text(
                          'Outcome Assessment:',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                        ),
                        const SizedBox(height: 6),
                        ...job.outcomes.map((out) {
                          return Text(
                            '• ${out.outcomeDescription} (${out.successStatus})',
                            style: const TextStyle(fontSize: 12, color: Color(0xFF059669), fontWeight: FontWeight.w600),
                          );
                        }),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Evidence Photos Section (Section 24)
            if (job.evidence.isNotEmpty) ...[
              const Text(
                'Submitted Repair Evidence Photos',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: job.evidence.map((ev) {
                  return Container(
                    width: 140,
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.borderSubtle),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          height: 80,
                          width: double.infinity,
                          decoration: BoxDecoration(
                            color: const Color(0xFFE2E8F0),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Center(
                            child: Icon(Icons.image, size: 36, color: Color(0xFF64748B)),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryAmber.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            ev.mediaRole.toUpperCase(),
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.primaryAmber,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          ev.storagePath.split('/').last,
                          style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 20),
            ],

            // Customer Action Buttons: Verification vs Dispute (Section 24)
            if (job.isCompleted) ...[
              if (job.isVerified && job.hasFeedback) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFBBF7D0)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.check_circle_rounded, color: Colors.green, size: 28),
                      SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Repair Verified & Reviewed ✓',
                              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFF166534)),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Your feedback was submitted and reflected on the technician profile.',
                              style: TextStyle(fontSize: 12, color: Color(0xFF15803D)),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
              ] else ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFBBF7D0)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        'Customer Action Required',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFF166534)),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Please verify if the appliance/device is functioning properly and rate your technician.',
                        style: TextStyle(fontSize: 12, color: Color(0xFF15803D)),
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: _handleConfirmRepair,
                              icon: const Icon(Icons.check, size: 16),
                              label: Text(job.hasFeedback ? 'Confirm Repair' : 'Verify & Rate Work'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF16A34A),
                                foregroundColor: Colors.white,
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _handleDispute,
                              icon: const Icon(Icons.close, size: 16, color: Colors.red),
                              label: const Text('Dispute', style: TextStyle(color: Colors.red)),
                              style: OutlinedButton.styleFrom(
                                side: const BorderSide(color: Colors.red),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
              ],
            ],

            // Job Status History / Timeline (Section 11)
            const Text(
              'Engagement Timeline',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
            ),
            const SizedBox(height: 10),
            ...job.timeline.map((event) {
              return Padding(
                padding: const EdgeInsets.only(left: 8, bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      margin: const EdgeInsets.only(top: 2),
                      width: 12,
                      height: 12,
                      decoration: const BoxDecoration(
                        color: AppTheme.primaryAmber,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            event.toStatus.replaceAll('_', ' ').toUpperCase(),
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                          ),
                          if (event.notes != null)
                            Text(
                              event.notes!,
                              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                            ),
                          Text(
                            'By: ${event.changedByName ?? "System"} • ${event.createdAt.toLocal().toString().substring(0, 16)}',
                            style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}
