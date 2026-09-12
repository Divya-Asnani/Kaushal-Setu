import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/worker_profile.dart';
import 'package:kaushalsetu/services/worker_service.dart';

class WorkerProfileSkillsScreen extends StatefulWidget {
  final WorkerProfile profile;

  const WorkerProfileSkillsScreen({super.key, required this.profile});

  @override
  State<WorkerProfileSkillsScreen> createState() => _WorkerProfileSkillsScreenState();
}

class _WorkerProfileSkillsScreenState extends State<WorkerProfileSkillsScreen> {
  final WorkerService _workerService = WorkerService();
  late WorkerProfile _currentProfile;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _currentProfile = widget.profile;
  }

  Future<void> _refreshProfile() async {
    setState(() => _isLoading = true);
    try {
      final updated = await _workerService.getMyProfile();
      setState(() => _currentProfile = updated);
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  void _showAddSkillDialog() async {
    List<Map<String, dynamic>> allSkills = [];
    try {
      allSkills = await _workerService.listAllSkills();
    } catch (_) {}

    if (!mounted) return;

    String? selectedSkillId = allSkills.isNotEmpty ? allSkills.first['id'] as String : null;
    String selectedProficiency = 'intermediate';

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              title: const Text('Add Technical Skill'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Select Canonical Skill:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    initialValue: selectedSkillId,
                    isExpanded: true,
                    items: allSkills.map((s) {
                      return DropdownMenuItem<String>(
                        value: s['id'] as String,
                        child: Text('${s['name']} (${s['category']})', style: const TextStyle(fontSize: 13)),
                      );
                    }).toList(),
                    onChanged: (val) => setDialogState(() => selectedSkillId = val),
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 16),
                  const Text('Proficiency Level:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    initialValue: selectedProficiency,
                    items: const [
                      DropdownMenuItem(value: 'beginner', child: Text('Beginner')),
                      DropdownMenuItem(value: 'intermediate', child: Text('Intermediate')),
                      DropdownMenuItem(value: 'advanced', child: Text('Advanced')),
                      DropdownMenuItem(value: 'expert', child: Text('Expert')),
                    ],
                    onChanged: (val) => setDialogState(() => selectedProficiency = val ?? 'intermediate'),
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                  ),
                ],
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
                ElevatedButton(
                  onPressed: selectedSkillId == null
                      ? null
                      : () async {
                          Navigator.pop(ctx);
                          final existingSkills = _currentProfile.skills.map((s) => <String, dynamic>{
                            'skill_id': s.skillId,
                            'proficiency_level': s.proficiencyLevel,
                          }).toList();
                          existingSkills.add(<String, dynamic>{
                            'skill_id': selectedSkillId!,
                            'proficiency_level': selectedProficiency,
                          });
                          await _workerService.updateSkills(existingSkills);
                          _refreshProfile();
                        },
                  child: const Text('Add Skill'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showAddCertificateDialog() {
    final titleController = TextEditingController();
    final orgController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('Add Professional Certificate'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'Certificate Title',
                  hintText: 'e.g. ITI Wireman License',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: orgController,
                decoration: const InputDecoration(
                  labelText: 'Issuing Organization',
                  hintText: 'e.g. National Skill Development Corp',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () async {
                if (titleController.text.trim().isEmpty) return;
                Navigator.pop(ctx);
                await _workerService.addCertificate(
                  title: titleController.text.trim(),
                  issuingOrganization: orgController.text.trim().isNotEmpty
                      ? orgController.text.trim()
                      : 'Government Recognized Institute',
                );
                _refreshProfile();
              },
              child: const Text('Save Certificate'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final profile = _currentProfile;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Professional Profile & Skills'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshProfile,
          )
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Bio Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            profile.fullName,
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.secondaryNavy),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            profile.headline ?? 'Repair Specialist',
                            style: const TextStyle(color: AppTheme.primaryAmber, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            profile.bio ?? 'Professional technician on KaushalSetu.',
                            style: const TextStyle(fontSize: 13, color: Color(0xFF475569), height: 1.4),
                          ),
                          const Divider(height: 24),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text('Experience: ${profile.experienceYears} Years'),
                              Text('Service Radius: ${profile.serviceRadiusKm.toStringAsFixed(0)} km'),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Skills Section
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Technical Skills & Proficiencies',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
                      ),
                      TextButton.icon(
                        onPressed: _showAddSkillDialog,
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('Add Skill', style: TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  if (profile.skills.isEmpty)
                    const Text('No skills listed yet. Click "+ Add Skill" to add verified capabilities.', style: TextStyle(color: Colors.grey))
                  else
                    ...profile.skills.map((skill) {
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: const Icon(Icons.bolt, color: AppTheme.primaryAmber),
                          title: Text(skill.skillName, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                          subtitle: Text('${skill.category} • ${skill.proficiencyLevel.toUpperCase()}'),
                          trailing: skill.verified
                              ? const Icon(Icons.verified, color: Colors.green, size: 20)
                              : null,
                        ),
                      );
                    }),
                  const SizedBox(height: 20),

                  // Certificates Section
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Verified Certifications',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
                      ),
                      TextButton.icon(
                        onPressed: _showAddCertificateDialog,
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('Add Certificate', style: TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  if (profile.certificates.isEmpty)
                    const Text('No certifications recorded. Click "+ Add Certificate" to register credentials.', style: TextStyle(color: Colors.grey))
                  else
                    ...profile.certificates.map((cert) {
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: const Icon(Icons.card_membership_rounded, color: AppTheme.accentIndigo),
                          title: Text(cert.title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                          subtitle: Text(cert.issuingOrganization),
                          trailing: cert.isVerified
                              ? const Icon(Icons.verified, color: Colors.blue, size: 20)
                              : null,
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
