import 'package:flutter/material.dart';

import '../services/auth_store.dart';
import 'home_screen.dart';
import 'login_screen.dart';

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
    await Future<void>.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    final paired = await widget.store.isPaired();
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => paired
            ? HomeScreen(store: widget.store)
            : LoginScreen(store: widget.store),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Iris Nous',
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.w600, letterSpacing: 0.5),
            ),
            SizedBox(height: 12),
            Text('App companion', style: TextStyle(color: Colors.black54)),
            SizedBox(height: 28),
            CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
