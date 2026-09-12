import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:kaushalsetu/core/auth/auth_provider.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/services/problem_service.dart';
import 'package:kaushalsetu/screens/customer/problem_fingerprint_screen.dart';

class CreateProblemScreen extends StatefulWidget {
  final String? initialCategory;
  final String? initialTitle;
  final String? initialDescription;

  const CreateProblemScreen({
    super.key,
    this.initialCategory,
    this.initialTitle,
    this.initialDescription,
  });

  @override
  State<CreateProblemScreen> createState() => _CreateProblemScreenState();
}

class _CreateProblemScreenState extends State<CreateProblemScreen> {
  final _formKey = GlobalKey<FormState>();
  final _problemService = ProblemService();
  final ImagePicker _picker = ImagePicker();

  late TextEditingController _titleController;
  late TextEditingController _descController;
  final _addressController = TextEditingController(text: 'Flat 402, Sea View Apartments');
  late TextEditingController _localityController;
  late TextEditingController _cityController;
  final _stateController = TextEditingController(text: 'Maharashtra');
  final _postalCodeController = TextEditingController(text: '400050');

  final double _lat = 19.0760;
  final double _lon = 72.8777;

  bool _isSubmitting = false;
  XFile? _selectedImage;

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController(
      text: widget.initialTitle ?? 'Samsung Galaxy S23 Dead After Dropping',
    );
    _descController = TextEditingController(
      text: widget.initialDescription ??
          'Phone fell from table onto tiled floor. Screen has no cracks but device will not power on, zero charging current draw.',
    );

    final auth = Provider.of<AuthProvider>(context, listen: false);
    final userLocality = auth.userProfile?.locality;
    final userCity = auth.userProfile?.city;

    _localityController = TextEditingController(
      text: (userLocality != null && userLocality.trim().isNotEmpty) ? userLocality.trim() : '',
    );
    _cityController = TextEditingController(
      text: (userCity != null && userCity.trim().isNotEmpty) ? userCity.trim() : '',
    );
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descController.dispose();
    _addressController.dispose();
    _localityController.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _postalCodeController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    try {
      final photo = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1024,
        imageQuality: 85,
      );
      if (photo != null) {
        setState(() => _selectedImage = photo);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not pick image: $e')),
        );
      }
    }
  }

  Future<void> _submitProblem() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    try {
      List<String> mediaPaths = [];
      if (_selectedImage != null) {
        final bytes = await _selectedImage!.readAsBytes();
        final timestamp = DateTime.now().millisecondsSinceEpoch;
        final cleanName = _selectedImage!.name.replaceAll(' ', '_');
        final storagePath = 'problems/${timestamp}_$cleanName';
        try {
          await Supabase.instance.client.storage
              .from('problem-media')
              .uploadBinary(storagePath, bytes);
          mediaPaths.add('problem-media/$storagePath');
        } catch (storageErr) {
          debugPrint('Storage upload note: $storageErr');
          mediaPaths.add('problem-media/$storagePath');
        }
      }

      final problem = await _problemService.createProblem(
        title: _titleController.text.trim(),
        description: _descController.text.trim(),
        addressLine: _addressController.text.trim(),
        locality: _localityController.text.trim(),
        city: _cityController.text.trim(),
        state: _stateController.text.trim(),
        postalCode: _postalCodeController.text.trim(),
        latitude: _lat,
        longitude: _lon,
        mediaPaths: mediaPaths,
      );

      if (mounted) {
        // Direct transition to Fingerprint extraction screen (Golden Path)
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => ProblemFingerprintScreen(problem: problem),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to submit problem: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Report Repair Issue')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Describe the Issue',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.secondaryNavy,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Include device model and symptoms so AI can accurately extract repair requirements.',
                style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: 16),

              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Problem Title *',
                  hintText: 'e.g. Inverter tripping MCB, Phone dead after drop',
                ),
                validator: (v) => v == null || v.trim().isEmpty ? 'Please enter a title' : null,
              ),
              const SizedBox(height: 14),

              TextFormField(
                controller: _descController,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Detailed Symptoms & Context *',
                  hintText: 'Describe sounds, smell, impact history, or error indicators...',
                ),
                validator: (v) => v == null || v.trim().isEmpty ? 'Please enter a description' : null,
              ),
              const SizedBox(height: 20),

              // Photo upload selector
              const Text(
                'Optional Photo / Breakdown Media',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 8),
              InkWell(
                onTap: _pickImage,
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryAmber.withValues(alpha: 0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.camera_alt_outlined, color: AppTheme.primaryAmber),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _selectedImage != null ? _selectedImage!.name : 'Add Photo of Device / Fault',
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const Text(
                              'Supports JPG, PNG (Supabase Storage)',
                              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                            ),
                          ],
                        ),
                      ),
                      if (_selectedImage != null)
                        const Icon(Icons.check_circle, color: Colors.green, size: 20)
                      else
                        const Icon(Icons.arrow_forward_ios, size: 14, color: Colors.grey),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Location Section
              const Text(
                'Service Location',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 12),

              TextFormField(
                controller: _addressController,
                decoration: const InputDecoration(labelText: 'Address Line'),
              ),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _localityController,
                      decoration: const InputDecoration(labelText: 'Locality / Area'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: TextFormField(
                      controller: _cityController,
                      decoration: const InputDecoration(labelText: 'City'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _stateController,
                      decoration: const InputDecoration(labelText: 'State'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: TextFormField(
                      controller: _postalCodeController,
                      decoration: const InputDecoration(labelText: 'Postal Code'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 28),

              ElevatedButton(
                onPressed: _isSubmitting ? null : _submitProblem,
                child: _isSubmitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                      )
                    : const Text('Submit & Extract AI Fingerprint'),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}
