import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/job.dart';
import 'package:kaushalsetu/services/job_service.dart';
import 'package:kaushalsetu/widgets/evidence_uploader.dart';

class WorkerJobCompletionScreen extends StatefulWidget {
  final JobModel job;

  const WorkerJobCompletionScreen({super.key, required this.job});

  @override
  State<WorkerJobCompletionScreen> createState() => _WorkerJobCompletionScreenState();
}

class _WorkerJobCompletionScreenState extends State<WorkerJobCompletionScreen> {
  final _formKey = GlobalKey<FormState>();
  final JobService _jobService = JobService();

  final _diagnosisController = TextEditingController(
    text: 'Identified short circuit on primary power rail caused by fractured decoupling capacitor next to PMIC.',
  );

  final List<JobAction> _actions = [
    JobAction(
      stepNumber: 1,
      actionType: 'diagnostic',
      actionDescription: 'Thermal camera inspection identified localized heating under motherboard shielding.',
      toolsUsed: ['Thermal Camera', 'Digital Multimeter'],
    ),
    JobAction(
      stepNumber: 2,
      actionType: 'repair',
      actionDescription: 'Lifted shield at 320C, desoldered shorted capacitor, cleaned pads, soldered replacement 10uF SMD capacitor.',
      toolsUsed: ['Micro-soldering Station', 'Hot Air Rework'],
    ),
  ];

  final List<JobOutcome> _outcomes = [
    JobOutcome(
      outcomeType: 'repair_result',
      outcomeDescription: 'Device boots normally into operating system, charging current confirmed at 2.4A.',
      successStatus: 'successful',
      lessonsLearned: 'Mechanical drops often produce hairline fractures on high-capacitance decoupling capacitors.',
    ),
  ];

  List<JobEvidence> _evidence = [
    JobEvidence(
      storagePath: 'experience-media/before_fault.jpg',
      mediaType: 'image',
      mediaRole: 'before',
      isVerified: false,
    ),
    JobEvidence(
      storagePath: 'experience-media/after_tested.jpg',
      mediaType: 'image',
      mediaRole: 'after',
      isVerified: false,
    ),
  ];

  bool _isSubmitting = false;

  @override
  void dispose() {
    _diagnosisController.dispose();
    super.dispose();
  }

  void _addAction() {
    setState(() {
      _actions.add(
        JobAction(
          stepNumber: _actions.length + 1,
          actionType: 'repair',
          actionDescription: '',
        ),
      );
    });
  }

  void _submitCompletion() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);
    try {
      await _jobService.submitCompletion(
        jobId: widget.job.id,
        diagnosis: _diagnosisController.text.trim(),
        actions: _actions,
        outcomes: _outcomes,
        evidence: _evidence,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Completion submitted! Experience recorded and customer notified for verification.'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to submit completion: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Submit Job Completion')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                widget.job.problemTitle ?? 'Repair Completion',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 4),
              const Text(
                'Provide thorough technical diagnosis, actions, outcomes, and photos to support customer verification.',
                style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: 20),

              // Diagnosis Input
              const Text(
                '1. Technical Diagnosis *',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _diagnosisController,
                maxLines: 3,
                decoration: const InputDecoration(
                  hintText: 'Describe root cause of malfunction identified during inspection...',
                ),
                validator: (v) => v == null || v.trim().isEmpty ? 'Please provide a diagnosis' : null,
              ),
              const SizedBox(height: 24),

              // Actions Performed (Section 23 Dynamic List)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    '2. Actions Performed',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
                  ),
                  TextButton.icon(
                    onPressed: _addAction,
                    icon: const Icon(Icons.add, size: 16),
                    label: const Text('Add Step'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ..._actions.asMap().entries.map((entry) {
                final idx = entry.key;
                final act = entry.value;
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Step ${act.stepNumber} (${act.actionType.toUpperCase()})',
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                          if (_actions.length > 1)
                            IconButton(
                              icon: const Icon(Icons.remove_circle_outline, size: 18, color: Colors.red),
                              onPressed: () => setState(() => _actions.removeAt(idx)),
                            ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      TextFormField(
                        initialValue: act.actionDescription,
                        decoration: const InputDecoration(labelText: 'Action Description'),
                        onChanged: (val) {
                          _actions[idx] = JobAction(
                            stepNumber: act.stepNumber,
                            actionType: act.actionType,
                            actionDescription: val,
                            toolsUsed: act.toolsUsed,
                          );
                        },
                      ),
                    ],
                  ),
                );
              }),
              const SizedBox(height: 20),

              // Outcomes Section
              const Text(
                '3. Repair Outcome',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.borderSubtle),
                ),
                child: Column(
                  children: [
                    TextFormField(
                      initialValue: _outcomes[0].outcomeDescription,
                      decoration: const InputDecoration(labelText: 'Outcome Description'),
                      onChanged: (val) {
                        _outcomes[0] = JobOutcome(
                          outcomeType: _outcomes[0].outcomeType,
                          outcomeDescription: val,
                          successStatus: _outcomes[0].successStatus,
                          lessonsLearned: _outcomes[0].lessonsLearned,
                        );
                      },
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      initialValue: _outcomes[0].lessonsLearned,
                      decoration: const InputDecoration(labelText: 'Key Lesson Learned / Technical Insight'),
                      onChanged: (val) {
                        _outcomes[0] = JobOutcome(
                          outcomeType: _outcomes[0].outcomeType,
                          outcomeDescription: _outcomes[0].outcomeDescription,
                          successStatus: _outcomes[0].successStatus,
                          lessonsLearned: val,
                        );
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Evidence Photos Uploader (Section 13)
              EvidenceUploader(
                evidenceList: _evidence,
                onChanged: (updated) => setState(() => _evidence = updated),
              ),
              const SizedBox(height: 32),

              // Submit Button
              ElevatedButton(
                onPressed: _isSubmitting ? null : _submitCompletion,
                child: _isSubmitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                      )
                    : const Text('Submit Completion & Await Customer Verification'),
              ),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }
}
