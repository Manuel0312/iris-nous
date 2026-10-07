import 'package:flutter/material.dart';

import 'screens/splash_screen.dart';
import 'services/auth_store.dart';

class IrisNousApp extends StatelessWidget {
  const IrisNousApp({super.key, required this.store});

  final AuthStore store;

  @override
  Widget build(BuildContext context) {
    final base = ColorScheme.fromSeed(
      seedColor: const Color(0xFF1F4B5F),
      brightness: Brightness.light,
    );
    return MaterialApp(
      title: 'Iris Nous',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: base,
        useMaterial3: true,
        appBarTheme: AppBarTheme(
          backgroundColor: base.surface,
          foregroundColor: base.onSurface,
          elevation: 0,
        ),
      ),
      home: SplashScreen(store: store),
    );
  }
}
