import 'package:flutter_test/flutter_test.dart';
import 'package:iris_nous_mobile/app.dart';
import 'package:iris_nous_mobile/services/auth_store.dart';

void main() {
  testWidgets('IrisNousApp builds', (tester) async {
    await tester.pumpWidget(IrisNousApp(store: AuthStore()));
    expect(find.textContaining('Iris'), findsWidgets);
  });
}
