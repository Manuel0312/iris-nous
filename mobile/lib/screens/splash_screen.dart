import 'package:flutter/material.dart';

import '../services/auth_store.dart';
import '../theme/iris_theme.dart';
import 'site_shell_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key, required this.store});

  final AuthStore store;

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _go();
  }

  Future<void> _go() async {
    await Future<void>.delayed(const Duration(milliseconds: 450));
    if (!mounted) return;
    // First open = the real Iris website (same as discovering it on PC).
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => SiteShellScreen(store: widget.store, initialPath: '/app'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: Color(0xFFF5F5F7),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Iris Nous',
              style: TextStyle(
                fontSize: 34,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.6,
                color: IrisTheme.accent,
              ),
            ),
            SizedBox(height: 24),
            CircularProgressIndicator(color: IrisTheme.accent),
          ],
        ),
      ),
    );
  }
}
