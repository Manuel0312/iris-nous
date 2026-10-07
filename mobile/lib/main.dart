import 'package:flutter/material.dart';

import 'app.dart';
import 'services/auth_store.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(IrisNousApp(store: AuthStore()));
}
