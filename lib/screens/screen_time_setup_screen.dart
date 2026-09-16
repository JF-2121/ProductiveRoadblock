import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// iOS Shortcuts automation setup guide
class ScreenTimeSetupScreen extends StatefulWidget {
  const ScreenTimeSetupScreen({super.key});

  @override
  State<ScreenTimeSetupScreen> createState() => _ScreenTimeSetupScreenState();
}

class _ScreenTimeSetupScreenState extends State<ScreenTimeSetupScreen> {
  final PageController _pageController = PageController();
  int _currentStep = 0;

  static const Color primaryPurple = Color(0xFF9C27B0);
  static const Color backgroundColor = Colors.black;

  final List<SetupStep> _steps = [
    SetupStep(
      title: 'How It Works',
      icon: Icons.lightbulb_outline,
      instructions: [
        'You try to open Instagram',
        'Notification appears instantly',
        'Tap notification to open this app',
        'Complete quick challenge',
        'Return to Instagram unlocked',
      ],
    ),
    SetupStep(
      title: 'Open Shortcuts App',
      icon: Icons.apps,
      instructions: [
        'Find "Shortcuts" app on your iPhone',
        '(Orange icon with white squares)',
        '',
        'Tap to open it',
      ],
    ),
    SetupStep(
      title: 'Create Automation',
      icon: Icons.auto_awesome,
      instructions: [
        'Tap "Automation" tab (bottom)',
        'Tap "+" button (top right)',
        'Select "App"',
        'Choose "Instagram"',
        'Select "Is Opened"',
        'Tap "Next"',
      ],
    ),
    SetupStep(
      title: 'Add Notification',
      icon: Icons.notifications_active,
      instructions: [
        'Tap "Add Action"',
        'Search "Show Notification"',
        'Tap it to add',
        '',
        'Set notification text:',
        'Title: "Complete Challenge"',
        'Body: "Tap to unlock Instagram"',
      ],
    ),
    SetupStep(
      title: 'Add Open App',
      icon: Icons.open_in_new,
      instructions: [
        'Tap "Add Action" again',
        'Search "Open App"',
        'Tap it to add',
        'Select "Productive Roadblock"',
        '',
        'Now you have 2 actions',
      ],
    ),
    SetupStep(
      title: 'Enable Auto-Run',
      icon: Icons.flash_on,
      instructions: [
        'CRITICAL STEP:',
        '',
        'Find "Ask Before Running"',
        'Toggle it OFF (gray)',
        '',
        'This makes it automatic',
        'If ON, you must confirm each time',
        '',
        'Tap "Done"',
      ],
    ),
    SetupStep(
      title: 'All Set!',
      icon: Icons.check_circle,
      instructions: [
        'Automation is active',
        '',
        'Try opening Instagram now',
        'Notification will appear',
        'Tap it to open this app',
        'Complete challenge',
        'Instagram unlocked!',
      ],
    ),
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: backgroundColor,
      appBar: AppBar(
        title: const Text('Setup Guide'),
        backgroundColor: backgroundColor,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.pushReplacementNamed(context, '/blocking'),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Progress indicator
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(_steps.length, (index) {
                      return Container(
                        width: index == _currentStep ? 24 : 6,
                        height: 6,
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        decoration: BoxDecoration(
                          color: index == _currentStep
                              ? primaryPurple
                              : primaryPurple.withValues(alpha: 0.3),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      );
                    }),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Step ${_currentStep + 1} of ${_steps.length}',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.white.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),
            ),

            // Swipeable content
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (index) {
                  setState(() => _currentStep = index);
                  HapticFeedback.lightImpact();
                },
                itemCount: _steps.length,
                itemBuilder: (context, index) {
                  final step = _steps[index];
                  return SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Column(
                      children: [
                        const SizedBox(height: 20),
                        Container(
                          width: 90,
                          height: 90,
                          decoration: BoxDecoration(
                            color: primaryPurple.withValues(alpha: 0.2),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            step.icon,
                            size: 45,
                            color: primaryPurple,
                          ),
                        ),
                        const SizedBox(height: 24),
                        Text(
                          step.title,
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 32),
                        ...step.instructions.map((instruction) {
                          final isEmpty = instruction.trim().isEmpty;
                          final isBold = instruction.contains('CRITICAL') ||
                              instruction.contains('Set notification');
                          return Padding(
                            padding: EdgeInsets.only(
                              bottom: isEmpty ? 8 : 12,
                            ),
                            child: isEmpty
                                ? const SizedBox(height: 4)
                                : Text(
                                    instruction,
                                    style: TextStyle(
                                      fontSize: 15,
                                      color: Colors.white.withValues(alpha: 0.9),
                                      height: 1.6,
                                      fontWeight: isBold
                                          ? FontWeight.w600
                                          : FontWeight.normal,
                                    ),
                                    textAlign: TextAlign.center,
                                  ),
                          );
                        }),
                        const SizedBox(height: 40),
                      ],
                    ),
                  );
                },
              ),
            ),

            // Navigation
            Padding(
              padding: const EdgeInsets.all(24),
              child: Row(
                children: [
                  if (_currentStep > 0)
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          _pageController.previousPage(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeInOut,
                          );
                        },
                        icon: const Icon(Icons.arrow_back, size: 18),
                        label: const Text('Back'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          side: BorderSide(color: primaryPurple.withValues(alpha: 0.5)),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                  if (_currentStep > 0) const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: ElevatedButton.icon(
                      onPressed: () {
                        HapticFeedback.mediumImpact();
                        if (_currentStep < _steps.length - 1) {
                          _pageController.nextPage(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeInOut,
                          );
                        } else {
                          Navigator.pushReplacementNamed(context, '/blocking');
                        }
                      },
                      icon: Icon(
                        _currentStep < _steps.length - 1
                            ? Icons.arrow_forward
                            : Icons.check,
                        size: 18,
                      ),
                      label: Text(
                        _currentStep < _steps.length - 1 ? 'Next' : 'Done',
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: primaryPurple,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 0,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class SetupStep {
  final String title;
  final IconData icon;
  final List<String> instructions;

  SetupStep({
    required this.title,
    required this.icon,
    required this.instructions,
  });
}