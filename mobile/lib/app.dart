import 'package:flutter/material.dart';

import 'screens/splash_screen.dart';
import 'services/auth_store.dart';
import 'theme/iris_theme.dart';

class IrisNousApp extends StatelessWidget {
  const IrisNousApp({super.key, required this.store});

  final AuthStore store;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Iris Nous',
      debugShowCheckedModeBanner: false,
      theme: IrisTheme.light(),
      home: SplashScreen(store: store),
    );
  }
}
