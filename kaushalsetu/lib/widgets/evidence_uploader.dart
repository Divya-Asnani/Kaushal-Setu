import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/job.dart';

class EvidenceUploader extends StatefulWidget {
  final List<JobEvidence> evidenceList;
  final Function(List<JobEvidence>) onChanged;

  const EvidenceUploader({
    super.key,
    required this.evidenceList,
    required this.onChanged,
  });

  @override
  State<EvidenceUploader> createState() => _EvidenceUploaderState();
}

class _EvidenceUploaderState extends State<EvidenceUploader> {
  final ImagePicker _picker = ImagePicker();
  bool _isUploading = false;

  Future<void> _pickAndAddImage(String role) async {
    setState(() => _isUploading = true);
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1024,
        imageQuality: 85,
      );

      if (photo != null) {
        final bytes = await photo.readAsBytes();
        final timestamp = DateTime.now().millisecondsSinceEpoch;
        final cleanName = photo.name.replaceAll(' ', '_');
        final storagePath = 'evidence/${timestamp}_$cleanName';

        try {
          await Supabase.instance.client.storage
              .from('experience-media')
              .uploadBinary(storagePath, bytes);
        } catch (uploadErr) {
          debugPrint('Experience media upload note: $uploadErr');
        }

        final fullPath = 'experience-media/$storagePath';

        final updated = List<JobEvidence>.from(widget.evidenceList)
          ..add(JobEvidence(
            storagePath: fullPath,
            mediaType: 'image',
            mediaRole: role,
            isVerified: false,
          ));
        widget.onChanged(updated);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to pick image: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isUploading = false);
    }
  }

  void _removeEvidence(int index) {
    final updated = List<JobEvidence>.from(widget.evidenceList)..removeAt(index);
    widget.onChanged(updated);
  }

  void _showRolePickerModal() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: Text(
                    'Select Evidence Role',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.secondaryNavy,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                ListTile(
                  leading: const Icon(Icons.history_toggle_off, color: Colors.blue),
                  title: const Text('Before Repair'),
                  subtitle: const Text('Fault condition, damaged component, or error display'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _pickAndAddImage('before');
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.build_circle_outlined, color: Colors.purple),
                  title: const Text('During Repair'),
                  subtitle: const Text('Disassembly, micro-soldering, or component replacement'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _pickAndAddImage('during');
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.check_circle_outline, color: Colors.green),
                  title: const Text('After Repair (Default)'),
                  subtitle: const Text('Device powering on, tested rails, or completed installation'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _pickAndAddImage('after');
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.analytics_outlined, color: Colors.orange),
                  title: const Text('Diagnostic / Measurement'),
                  subtitle: const Text('Multimeter diode check, oscilloscope or thermal readings'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _pickAndAddImage('diagnostic');
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Repair Evidence & Photos',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: AppTheme.secondaryNavy,
              ),
            ),
            OutlinedButton.icon(
              onPressed: _isUploading ? null : _showRolePickerModal,
              icon: _isUploading
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.add_a_photo, size: 16),
              label: const Text('Add Evidence'),
            ),
          ],
        ),
        const SizedBox(height: 10),

        if (widget.evidenceList.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.borderSubtle, style: BorderStyle.solid),
            ),
            child: const Column(
              children: [
                Icon(Icons.photo_library_outlined, size: 36, color: Colors.grey),
                SizedBox(height: 8),
                Text(
                  'No evidence uploaded yet.',
                  style: TextStyle(color: Colors.grey, fontSize: 13),
                ),
                Text(
                  'Adding before/after photos helps customer verification.',
                  style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                ),
              ],
            ),
          )
        else
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: widget.evidenceList.asMap().entries.map((entry) {
              final idx = entry.key;
              final ev = entry.value;
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
                    Align(
                      alignment: Alignment.centerRight,
                      child: IconButton(
                        icon: const Icon(Icons.delete_outline, size: 18, color: Colors.red),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(),
                        onPressed: () => _removeEvidence(idx),
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
      ],
    );
  }
}
