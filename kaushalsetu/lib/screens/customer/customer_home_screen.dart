import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:kaushalsetu/core/auth/auth_provider.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/problem.dart';
import 'package:kaushalsetu/models/service_request.dart';
import 'package:kaushalsetu/services/problem_service.dart';
import 'package:kaushalsetu/services/request_service.dart';
import 'package:kaushalsetu/widgets/status_badge.dart';
import 'package:kaushalsetu/screens/customer/create_problem_screen.dart';
import 'package:kaushalsetu/screens/customer/problem_fingerprint_screen.dart';
import 'package:kaushalsetu/screens/customer/customer_requests_screen.dart';
import 'package:kaushalsetu/screens/common/notifications_screen.dart';
import 'package:kaushalsetu/widgets/location_picker_sheet.dart';

class CustomerHomeScreen extends StatefulWidget {
  const CustomerHomeScreen({super.key});

  @override
  State<CustomerHomeScreen> createState() => _CustomerHomeScreenState();
}

class _CustomerHomeScreenState extends State<CustomerHomeScreen> {
  final ProblemService _problemService = ProblemService();
  final RequestService _requestService = RequestService();

  int _currentNavIndex = 0;
  bool _isLoading = true;
  List<CustomerProblem> _problems = [];
  List<ServiceRequestModel> _requests = [];

  // Carousel animation
  late PageController _pageController;
  int _currentBannerPage = 0;
  Timer? _bannerTimer;

  final List<Map<String, dynamic>> _promoBanners = [
    {
      'tag': 'AI OPPORTUNITY MATCHING',
      'title': 'Expert Electricians & Technicians',
      'subtitle': 'Verified ITI & board-level specialists at your doorstep in 15 mins',
      'color1': const Color(0xFF1E293B),
      'color2': const Color(0xFF0F172A),
      'icon': Icons.bolt_rounded,
      'badge': '₹0 DIAGNOSIS',
      'imageUrl': 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=800&auto=format&fit=crop&q=80',
    },
    {
      'tag': 'COMPONENT LEVEL',
      'title': 'Board Repair & Soldering',
      'subtitle': 'Micro-soldering, short circuit tracing with 30 days warranty',
      'color1': const Color(0xFFC2410C),
      'color2': const Color(0xFF9A3412),
      'icon': Icons.memory_rounded,
      'badge': 'TOP RATED ★ 4.9',
      'imageUrl': 'https://images.unsplash.com/photo-1597424214717-38cf565ba1d2?w=800&auto=format&fit=crop&q=80',
    },
    {
      'tag': 'POWER SYSTEMS',
      'title': 'Inverter & UPS Troubleshooting',
      'subtitle': 'MOSFET replacements, continuous overload alarms & battery testing',
      'color1': const Color(0xFF15803D),
      'color2': const Color(0xFF166534),
      'icon': Icons.battery_charging_full_rounded,
      'badge': 'EXPRESS ON-SITE',
      'imageUrl': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop&q=80',
    },
  ];

  final List<Map<String, dynamic>> _categories = [
    {
      'name': 'Electrician',
      'icon': Icons.bolt_rounded,
      'color': const Color(0xFFF97316),
      'title': 'General Electrical Breakdown',
      'desc': 'Tripping MCB, sparks, power socket breakdown',
      'imageUrl': 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=200&auto=format&fit=crop&q=80',
    },
    {
      'name': 'PCB Board',
      'icon': Icons.memory_rounded,
      'color': const Color(0xFF3B82F6),
      'title': 'PCB Board-Level Soldering',
      'desc': 'SMD component rework, phone or board dead after drop',
      'imageUrl': 'https://images.unsplash.com/photo-1597424214717-38cf565ba1d2?w=200&auto=format&fit=crop&q=80',
    },
    {
      'name': 'Inverter/UPS',
      'icon': Icons.battery_charging_full_rounded,
      'color': const Color(0xFF10B981),
      'title': 'Inverter Continuous Overload Alarm',
      'desc': 'Overload beep, backup power failure, battery charging issue',
      'imageUrl': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=200&auto=format&fit=crop&q=80',
    },
    {
      'name': 'TV & Screen',
      'icon': Icons.tv_rounded,
      'color': const Color(0xFF8B5CF6),
      'title': 'Smart TV Panel / Power Rail Fault',
      'desc': 'No display, sound working, LED backlight failure',
      'imageUrl': 'https://images.unsplash.com/photo-1461151304267-38535e780c79?w=200&auto=format&fit=crop&q=80',
    },
    {
      'name': 'Switchboard',
      'icon': Icons.power_rounded,
      'color': const Color(0xFFEC4899),
      'title': 'Switchboard Short Circuit',
      'desc': 'Burning smell from switches, burnt fuse box',
      'imageUrl': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=200&auto=format&fit=crop&q=80',
    },
    {
      'name': 'Motor & Fan',
      'icon': Icons.toys_rounded,
      'color': const Color(0xFF14B8A6),
      'title': 'Ceiling Fan / Motor Humming',
      'desc': 'Capacitor replacement, motor coil winding check',
      'imageUrl': 'https://images.unsplash.com/photo-1504917599217-d4dc5ebe6122?w=200&auto=format&fit=crop&q=80',
    },
    {
      'name': 'Wiring Trip',
      'icon': Icons.electrical_services_rounded,
      'color': const Color(0xFFEAB308),
      'title': 'Frequent ELCB / MCB Tripping',
      'desc': 'Earthing leakage test, short circuit detection',
      'imageUrl': 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=200&auto=format&fit=crop&q=80',
    },
    {
      'name': 'All Services',
      'icon': Icons.grid_view_rounded,
      'color': const Color(0xFF64748B),
      'title': 'Custom Repair Inspection',
      'desc': 'On-site technical evaluation by certified craftsman',
      'imageUrl': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=200&auto=format&fit=crop&q=80',
    },
  ];

  final List<Map<String, dynamic>> _popularServices = [
    {
      'title': 'Board Short Circuit Tracing',
      'price': '₹499',
      'time': '30 mins',
      'rating': '4.9 (1.2k)',
      'badge': 'Bestseller',
      'icon': Icons.biotech_rounded,
      'imageUrl': 'https://images.unsplash.com/photo-1597424214717-38cf565ba1d2?w=400&auto=format&fit=crop&q=80',
    },
    {
      'title': 'Inverter Overload Repair',
      'price': '₹399',
      'time': '45 mins',
      'rating': '4.8 (890)',
      'badge': 'Instant Match',
      'icon': Icons.battery_alert_rounded,
      'imageUrl': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=400&auto=format&fit=crop&q=80',
    },
    {
      'title': 'Distribution Board & MCB',
      'price': '₹299',
      'time': '20 mins',
      'rating': '4.9 (3.4k)',
      'badge': 'Safety Assured',
      'icon': Icons.shield_rounded,
      'imageUrl': 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=400&auto=format&fit=crop&q=80',
    },
    {
      'title': 'Motor Winding & Fan Repair',
      'price': '₹199',
      'time': '25 mins',
      'rating': '4.8 (2.1k)',
      'badge': 'Top Value',
      'icon': Icons.toys_rounded,
      'imageUrl': 'https://images.unsplash.com/photo-1504917599217-d4dc5ebe6122?w=400&auto=format&fit=crop&q=80',
    },
  ];

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _startBannerTimer();
    _loadData();
  }

  void _startBannerTimer() {
    _bannerTimer = Timer.periodic(const Duration(seconds: 4), (timer) {
      if (_pageController.hasClients) {
        _currentBannerPage = (_currentBannerPage + 1) % _promoBanners.length;
        _pageController.animateToPage(
          _currentBannerPage,
          duration: const Duration(milliseconds: 600),
          curve: Curves.easeInOutCubic,
        );
      }
    });
  }

  @override
  void dispose() {
    _bannerTimer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        _problemService.listProblems(),
        _requestService.listServiceRequests(),
      ]);
      _problems = results[0] as List<CustomerProblem>;
      _requests = results[1] as List<ServiceRequestModel>;
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  void _openBookingWithCategory(Map<String, dynamic> cat) async {
    final created = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CreateProblemScreen(
          initialCategory: cat['name'],
          initialTitle: cat['title'],
          initialDescription: cat['desc'],
        ),
      ),
    );
    if (created == true) _loadData();
  }

  void _showAccountSettingsSheet(BuildContext context) {
    final auth = context.read<AuthProvider>();
    final user = auth.userProfile;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetCtx) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              // User identity row
              Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: AppTheme.primaryAmber.withValues(alpha: 0.15),
                    child: Text(
                      (user?.fullName ?? 'U')[0].toUpperCase(),
                      style: const TextStyle(
                        color: AppTheme.primaryAmber,
                        fontWeight: FontWeight.bold,
                        fontSize: 20,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user?.fullName ?? 'User',
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.secondaryNavy,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          user?.email ?? '',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Color(0xFF64748B),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.blue.shade50,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: Colors.blue.shade200),
                          ),
                          child: Text(
                            auth.hasWorkerProfile ? 'Customer Mode (Technician Registered)' : 'Customer Mode',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: Colors.blue.shade800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Uber-style "Become a Technician" or "Switch to Technician Mode" Card
              if (auth.hasWorkerProfile)
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
                    ),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryAmber.withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.build_rounded, color: AppTheme.primaryAmber, size: 22),
                      ),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Switch to Technician Mode',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'View your jobs, requests & earnings',
                              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                            ),
                          ],
                        ),
                      ),
                      ElevatedButton(
                        onPressed: () {
                          Navigator.pop(sheetCtx);
                          auth.switchMode('worker');
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primaryAmber,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                        child: const Text('Switch'),
                      ),
                    ],
                  ),
                )
              else
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFFFFFBEB), Color(0xFFFEF3C7)],
                    ),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFFDE68A)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppTheme.primaryAmber.withValues(alpha: 0.25),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(Icons.handyman_rounded, color: AppTheme.primaryAmber, size: 20),
                          ),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Become a Technician',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    fontSize: 14,
                                    color: Color(0xFF78350F),
                                  ),
                                ),
                                Text(
                                  'Earn with KaushalSetu on repair jobs',
                                  style: TextStyle(fontSize: 11, color: Color(0xFF92400E)),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Join our verified network of electricians, PCB micro-soldering, and appliance technicians. Set your own rates.',
                        style: TextStyle(fontSize: 11.5, color: Color(0xFF78350F), height: 1.3),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                          label: const Text('Register as Technician'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryAmber,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                          ),
                          onPressed: () {
                            Navigator.pop(sheetCtx);
                            _showBecomeWorkerModal(context);
                          },
                        ),
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: 16),
              const Divider(),
              ListTile(
                leading: const Icon(Icons.notifications_none_rounded, color: AppTheme.secondaryNavy),
                title: const Text('Notifications', style: TextStyle(fontSize: 14)),
                trailing: const Icon(Icons.chevron_right, size: 20),
                onTap: () {
                  Navigator.pop(sheetCtx);
                  Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen()));
                },
              ),
              ListTile(
                leading: const Icon(Icons.location_on_outlined, color: AppTheme.secondaryNavy),
                title: const Text('Registered Location', style: TextStyle(fontSize: 14)),
                subtitle: Text(
                  auth.userProfile?.formattedLocation.isNotEmpty == true
                      ? auth.userProfile!.formattedLocation
                      : 'Not specified',
                  style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                ),
                trailing: TextButton(
                  onPressed: () {
                    Navigator.pop(sheetCtx);
                    showChangeLocationSheet(context);
                  },
                  child: const Text(
                    'Change',
                    style: TextStyle(
                      color: AppTheme.primaryAmber,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ),
                onTap: () {
                  Navigator.pop(sheetCtx);
                  showChangeLocationSheet(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.logout_rounded, color: Colors.red),
                title: const Text('Sign Out', style: TextStyle(color: Colors.red, fontSize: 14, fontWeight: FontWeight.w600)),
                onTap: () {
                  Navigator.pop(sheetCtx);
                  auth.logout();
                },
              ),
              const SizedBox(height: 10),
            ],
          ),
        );
      },
    );
  }

  void _showBecomeWorkerModal(BuildContext context) {
    String selectedCategory = 'electronics';
    int experienceYears = 3;
    final rateController = TextEditingController(text: '450');
    final authProfile = context.read<AuthProvider>().userProfile;
    final defaultLoc = authProfile?.formattedLocation.isNotEmpty == true
        ? authProfile!.formattedLocation
        : (authProfile?.locality ?? '');
    final localityController = TextEditingController(text: defaultLoc);
    final bioController = TextEditingController(text: 'Certified technician on KaushalSetu.');
    bool isSubmitting = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (modalCtx) {
        return StatefulBuilder(
          builder: (ctx, setModalState) {
            return Container(
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
              ),
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Center(
                      child: Container(
                        width: 40,
                        height: 4,
                        decoration: BoxDecoration(
                          color: Colors.grey.shade300,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryAmber.withValues(alpha: 0.15),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.bolt_rounded, color: AppTheme.primaryAmber, size: 24),
                        ),
                        const SizedBox(width: 10),
                        const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Technician Registration',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.secondaryNavy,
                              ),
                            ),
                            Text(
                              'Earn with KaushalSetu by taking repair jobs',
                              style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),

                    // Category dropdown
                    const Text('Primary Service Trade / Category:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                    const SizedBox(height: 6),
                    DropdownButtonFormField<String>(
                      initialValue: selectedCategory,
                      decoration: const InputDecoration(border: OutlineInputBorder()),
                      items: const [
                        DropdownMenuItem(value: 'electronics', child: Text('Electronics & PCB Soldering')),
                        DropdownMenuItem(value: 'electrical', child: Text('Electrician (Breakers & Wiring)')),
                        DropdownMenuItem(value: 'inverter', child: Text('Inverter & UPS Power Systems')),
                        DropdownMenuItem(value: 'appliance', child: Text('Home Appliance Repair')),
                        DropdownMenuItem(value: 'screen_display', child: Text('Smart TV & Screen Displays')),
                      ],
                      onChanged: (val) => setModalState(() => selectedCategory = val ?? 'electronics'),
                    ),
                    const SizedBox(height: 14),

                    // Experience & Rate Row
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Experience (Years):', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                              const SizedBox(height: 6),
                              DropdownButtonFormField<int>(
                                initialValue: experienceYears,
                                decoration: const InputDecoration(border: OutlineInputBorder()),
                                items: List.generate(20, (i) => i + 1).map((y) {
                                  return DropdownMenuItem(value: y, child: Text('$y yr${y > 1 ? "s" : ""}'));
                                }).toList(),
                                onChanged: (val) => setModalState(() => experienceYears = val ?? 3),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Rate (₹/hour):', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                              const SizedBox(height: 6),
                              TextField(
                                controller: rateController,
                                keyboardType: TextInputType.number,
                                decoration: const InputDecoration(
                                  prefixText: '₹ ',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // Locality
                    const Text('Service Locality / City:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: localityController,
                      decoration: const InputDecoration(
                        hintText: 'e.g. Koramangala, Bengaluru',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Submit button
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryAmber,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              setModalState(() => isSubmitting = true);
                              final auth = context.read<AuthProvider>();
                              final double rate = double.tryParse(rateController.text.trim()) ?? 450.0;
                              final locInput = localityController.text.trim();
                              String? loc;
                              String? cty;
                              if (locInput.isNotEmpty) {
                                if (locInput.contains(',')) {
                                  final parts = locInput.split(',');
                                  loc = parts[0].trim();
                                  cty = parts.sublist(1).join(',').trim();
                                } else {
                                  loc = locInput;
                                  cty = auth.userProfile?.city;
                                }
                              }
                              final success = await auth.becomeWorker(
                                serviceCategory: selectedCategory,
                                experienceYears: experienceYears,
                                hourlyRate: rate,
                                locality: loc,
                                city: cty,
                                bio: bioController.text.trim(),
                              );
                              setModalState(() => isSubmitting = false);
                              if (modalCtx.mounted) {
                                Navigator.pop(modalCtx);
                              }
                              if (ctx.mounted) {
                                ScaffoldMessenger.of(ctx).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      success
                                          ? '🎉 Technician profile activated! Switched to Technician Mode.'
                                          : (auth.errorMessage ?? 'Failed to activate technician profile.'),
                                    ),
                                    backgroundColor: success ? Colors.green : Colors.red,
                                  ),
                                );
                              }
                            },
                      child: isSubmitting
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Text(
                              'Activate Technician Profile',
                              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                            ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    // If viewing Bookings tab from bottom nav
    if (_currentNavIndex == 1) {
      return const CustomerRequestsScreen();
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(105),
        child: Container(
          color: Colors.white,
          padding: const EdgeInsets.only(top: 40, left: 16, right: 16, bottom: 8),
          child: Column(
            children: [
              // Urban Company Location Bar
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => showChangeLocationSheet(context),
                    child: Row(
                      children: [
                        const Icon(Icons.location_on, color: AppTheme.primaryAmber, size: 20),
                        const SizedBox(width: 6),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  'Location',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w800,
                                    fontSize: 14,
                                    color: AppTheme.secondaryNavy,
                                  ),
                                ),
                                const Icon(Icons.keyboard_arrow_down, size: 16),
                              ],
                            ),
                            Text(
                              (auth.userProfile?.formattedLocation.isNotEmpty == true)
                                  ? auth.userProfile!.formattedLocation
                                  : 'Tap to set location',
                              style: const TextStyle(color: Color(0xFF64748B), fontSize: 11),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.notifications_none_rounded, color: AppTheme.secondaryNavy),
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const NotificationsScreen()),
                          );
                        },
                      ),
                      GestureDetector(
                        onTap: () => _showAccountSettingsSheet(context),
                        child: CircleAvatar(
                          radius: 16,
                          backgroundColor: AppTheme.primaryAmber.withValues(alpha: 0.15),
                          child: Text(
                            (auth.userProfile?.fullName ?? 'U')[0].toUpperCase(),
                            style: const TextStyle(
                              color: AppTheme.primaryAmber,
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Search input field
              InkWell(
                onTap: () => _openBookingWithCategory(_categories[0]),
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  height: 38,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.search, size: 18, color: Color(0xFF94A3B8)),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          "Search 'Board repair', 'Inverter beep', 'Wiring trip'...",
                          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Icon(Icons.mic_none, size: 18, color: Color(0xFF94A3B8)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Urban Company Animated Promotional Carousel
              SizedBox(
                height: 175,
                child: PageView.builder(
                  controller: _pageController,
                  onPageChanged: (idx) => setState(() => _currentBannerPage = idx),
                  itemCount: _promoBanners.length,
                  itemBuilder: (context, idx) {
                    final b = _promoBanners[idx];
                    return AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(18),
                        boxShadow: [
                          BoxShadow(
                            color: (b['color1'] as Color).withValues(alpha: 0.25),
                            blurRadius: 12,
                            offset: const Offset(0, 5),
                          ),
                        ],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(18),
                        child: Stack(
                          children: [
                            // Background Photographic Image
                            Positioned.fill(
                              child: Image.network(
                                b['imageUrl'] as String,
                                fit: BoxFit.cover,
                                errorBuilder: (context, error, stackTrace) => Container(
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: [b['color1'] as Color, b['color2'] as Color],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            // Rich dark gradient overlay for text legibility
                            Positioned.fill(
                              child: Container(
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: [
                                      Colors.black.withValues(alpha: 0.88),
                                      Colors.black.withValues(alpha: 0.65),
                                      Colors.black.withValues(alpha: 0.35),
                                    ],
                                    begin: Alignment.centerLeft,
                                    end: Alignment.centerRight,
                                  ),
                                ),
                              ),
                            ),
                            // Faint watermark icon
                            Positioned(
                              right: 12,
                              bottom: 12,
                              child: Icon(
                                b['icon'] as IconData,
                                size: 90,
                                color: Colors.white.withValues(alpha: 0.12),
                              ),
                            ),
                            // Content
                            Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: AppTheme.primaryAmber,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      b['badge'] as String,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 10,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 0.5,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    b['title'] as String,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 17,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: -0.3,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    b['subtitle'] as String,
                                    style: const TextStyle(
                                      color: Colors.white70,
                                      fontSize: 11.5,
                                    ),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 10),
                                  ElevatedButton(
                                    onPressed: () => _openBookingWithCategory(_categories[idx]),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: AppTheme.primaryAmber,
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                      minimumSize: Size.zero,
                                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                    ),
                                    child: const Text('Book Repair Now', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),

              // Animated Carousel Dots
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(_promoBanners.length, (idx) {
                  final isSelected = _currentBannerPage == idx;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    margin: const EdgeInsets.symmetric(horizontal: 3, vertical: 8),
                    height: 6,
                    width: isSelected ? 18 : 6,
                    decoration: BoxDecoration(
                      color: isSelected ? AppTheme.primaryAmber : const Color(0xFFCBD5E1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  );
                }),
              ),
              const SizedBox(height: 10),

              // Urban Company Category Grid (8 Icons)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Repair & Electrical Services',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.secondaryNavy,
                      ),
                    ),
                    const SizedBox(height: 12),
                    GridView.builder(
                      physics: const NeverScrollableScrollPhysics(),
                      shrinkWrap: true,
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 4,
                        mainAxisSpacing: 12,
                        crossAxisSpacing: 8,
                        childAspectRatio: 0.85,
                      ),
                      itemCount: _categories.length,
                      itemBuilder: (context, idx) {
                        final cat = _categories[idx];
                        return InkWell(
                          onTap: () => _openBookingWithCategory(cat),
                          borderRadius: BorderRadius.circular(12),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                width: 52,
                                height: 52,
                                decoration: BoxDecoration(
                                  color: (cat['color'] as Color).withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: Icon(
                                  cat['icon'] as IconData,
                                  color: cat['color'] as Color,
                                  size: 26,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                cat['name'] as String,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: Color(0xFF334155),
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Urban Company Trust Strip (Guarantee)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildTrustFeature(Icons.verified_user_outlined, 'Verified Technicians', 'Background & skills tested'),
                    Container(height: 30, width: 1, color: const Color(0xFFE2E8F0)),
                    _buildTrustFeature(Icons.auto_graph_rounded, 'AI Match Precision', '4-factor case history'),
                    Container(height: 30, width: 1, color: const Color(0xFFE2E8F0)),
                    _buildTrustFeature(Icons.camera_alt_outlined, 'Photo Evidence', 'Before/after verified'),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Most Booked Technician Services (Urban Company Cards)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Most Booked Services',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.secondaryNavy,
                      ),
                    ),
                    TextButton(
                      onPressed: () => _openBookingWithCategory(_categories[0]),
                      child: const Text('See All'),
                    ),
                  ],
                ),
              ),
              SizedBox(
                height: 220,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  itemCount: _popularServices.length,
                  itemBuilder: (context, idx) {
                    final svc = _popularServices[idx];
                    return Container(
                      width: 195,
                      margin: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.04),
                            blurRadius: 8,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Top Image with Rating and Badge Overlay
                          SizedBox(
                            height: 105,
                            width: double.infinity,
                            child: Stack(
                              children: [
                                ClipRRect(
                                  borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
                                  child: Image.network(
                                    svc['imageUrl'] as String,
                                    height: 105,
                                    width: double.infinity,
                                    fit: BoxFit.cover,
                                    errorBuilder: (context, error, stackTrace) => Container(
                                      color: const Color(0xFFF1F5F9),
                                      child: Center(
                                        child: Icon(svc['icon'] as IconData, size: 36, color: AppTheme.primaryAmber),
                                      ),
                                    ),
                                  ),
                                ),
                                // Gradient shading on bottom of thumbnail
                                Positioned.fill(
                                  child: Container(
                                    decoration: BoxDecoration(
                                      borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
                                      gradient: LinearGradient(
                                        colors: [
                                          Colors.transparent,
                                          Colors.black.withValues(alpha: 0.4),
                                        ],
                                        begin: Alignment.topCenter,
                                        end: Alignment.bottomCenter,
                                      ),
                                    ),
                                  ),
                                ),
                                // Badge
                                Positioned(
                                  top: 8,
                                  left: 8,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.black.withValues(alpha: 0.75),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      svc['badge'] as String,
                                      style: const TextStyle(fontSize: 9, color: Colors.white, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ),
                                // Star Rating Pill
                                Positioned(
                                  bottom: 6,
                                  left: 8,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.white.withValues(alpha: 0.92),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Row(
                                      children: [
                                        const Icon(Icons.star, size: 11, color: Colors.amber),
                                        const SizedBox(width: 3),
                                        Text(
                                          svc['rating'] as String,
                                          style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          // Card Body
                          Padding(
                            padding: const EdgeInsets.all(10),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  svc['title'] as String,
                                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Color(0xFF1E293B)),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'Est: ${svc['time']}',
                                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                                ),
                                const SizedBox(height: 8),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      svc['price'] as String,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 13.5,
                                        color: AppTheme.primaryAmber,
                                      ),
                                    ),
                                    InkWell(
                                      onTap: () => _openBookingWithCategory(_categories[idx % _categories.length]),
                                      borderRadius: BorderRadius.circular(6),
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: AppTheme.primaryAmber.withValues(alpha: 0.12),
                                          borderRadius: BorderRadius.circular(6),
                                          border: Border.all(color: AppTheme.primaryAmber.withValues(alpha: 0.3)),
                                        ),
                                        child: const Text(
                                          'Book +',
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w800,
                                            color: AppTheme.primaryAmber,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 20),

              // Active Engagements / Live Status Section
              if (_requests.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Your Active Requests & Jobs',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.secondaryNavy,
                        ),
                      ),
                      TextButton(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const CustomerRequestsScreen()),
                          );
                        },
                        child: const Text('View All'),
                      ),
                    ],
                  ),
                ),
                ..._requests.take(2).map((req) {
                  return Card(
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: AppTheme.primaryAmber.withValues(alpha: 0.15),
                        child: const Icon(Icons.build_rounded, color: AppTheme.primaryAmber, size: 18),
                      ),
                      title: Text(
                        req.problemTitle ?? 'Repair Service',
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                      ),
                      subtitle: Text(
                        'Technician: ${req.workerName ?? "Specialist"}${req.locality != null && req.locality!.isNotEmpty ? " • ${req.locality}" : ""}',
                        style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                      ),
                      trailing: StatusBadge(status: req.status),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const CustomerRequestsScreen()),
                        );
                      },
                    ),
                  );
                }),
                const SizedBox(height: 16),
              ],

              // Previous Reported Problems
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Reported Problems',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppTheme.secondaryNavy),
                    ),
                    ElevatedButton.icon(
                      onPressed: () => _openBookingWithCategory(_categories[0]),
                      icon: const Icon(Icons.add, size: 14),
                      label: const Text('New Issue', style: TextStyle(fontSize: 11)),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        minimumSize: Size.zero,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),

              if (_isLoading)
                const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
              else if (_problems.isEmpty)
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: const Center(
                    child: Text('No repair issues reported yet. Tap any service above to begin.',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                  ),
                )
              else
                ..._problems.map((prob) {
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text(
                                  prob.title,
                                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                                ),
                              ),
                              StatusBadge(status: prob.status),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            prob.description,
                            style: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 10),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                '📍 ${prob.locality != null && prob.locality!.isNotEmpty ? prob.locality : "Location not specified"}',
                                style: const TextStyle(color: Colors.grey, fontSize: 11),
                              ),
                              ElevatedButton(
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => ProblemFingerprintScreen(problem: prob),
                                    ),
                                  );
                                },
                                style: ElevatedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                  minimumSize: Size.zero,
                                ),
                                child: const Text('View AI Matches', style: TextStyle(fontSize: 11)),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              const SizedBox(height: 30),
            ],
          ),
        ),
      ),
      // Urban Company Bottom Navigation Bar
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentNavIndex > 1 ? 0 : _currentNavIndex,
        onTap: (idx) {
          if (idx == 2) {
            _showAccountSettingsSheet(context);
          } else if (idx == 3) {
            auth.logout();
          } else {
            setState(() => _currentNavIndex = idx);
          }
        },
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppTheme.primaryAmber,
        unselectedItemColor: const Color(0xFF94A3B8),
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11),
        unselectedLabelStyle: const TextStyle(fontSize: 11),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_filled), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.receipt_long_rounded), label: 'Bookings'),
          BottomNavigationBarItem(icon: Icon(Icons.person_outline_rounded), label: 'Account'),
          BottomNavigationBarItem(icon: Icon(Icons.logout_rounded), label: 'Sign Out'),
        ],
      ),
    );
  }

  Widget _buildTrustFeature(IconData icon, String title, String sub) {
    return Column(
      children: [
        Icon(icon, color: AppTheme.primaryAmber, size: 20),
        const SizedBox(height: 4),
        Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: AppTheme.secondaryNavy)),
        Text(sub, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 9)),
      ],
    );
  }
}
