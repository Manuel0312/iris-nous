import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../config.dart';
import '../services/auth_store.dart';
import '../services/iris_api.dart';
import '../theme/iris_theme.dart';
import 'home_screen.dart';
import 'permissions_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.store});

  final AuthStore store;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _user = TextEditingController();
  final _pass = TextEditingController();
  final _code = TextEditingController();
  final _base = TextEditingController(text: IrisConfig.defaultBaseUrl);
  bool _busy = false;
  String? _error;

  late final IrisApi _api = IrisApi(widget.store);

  @override
  void initState() {
    super.initState();
    widget.store.baseUrl().then((u) {
      if (mounted) _base.text = u;
    });
  }

  @override
  void dispose() {
    _user.dispose();
    _pass.dispose();
    _code.dispose();
    _base.dispose();
    super.dispose();
  }

  Future<void> _scanQr() async {
    final code = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const _QrScanPage()),
    );
    if (code != null && mounted) {
      setState(() => _code.text = code);
    }
  }

  Future<void> _pair() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.store.setBaseUrl(_base.text);
      await _api.pair(
        username: _user.text,
        password: _pass.text,
        code: _code.text,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(builder: (_) => HomeScreen(store: widget.store)),
      );
    } on IrisApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Errore: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 600;
    final pad = wide ? 32.0 : 18.0;
    return IrisGlassScaffold(
      appBar: AppBar(title: const Text('Associa Iris')),
      child: ListView(
        padding: EdgeInsets.fromLTRB(pad, 12, pad, 28),
        children: [
          GlassPane(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Stesso account del sito. Codice o QR da Ecosistema → Associazione.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: IrisTheme.deep.withValues(alpha: 0.75),
                        height: 1.35,
                      ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _base,
                  decoration: const InputDecoration(labelText: 'URL Iris'),
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _user,
                  decoration: const InputDecoration(labelText: 'Username'),
                  autocorrect: false,
                  textInputAction: TextInputAction.next,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _pass,
                  decoration: const InputDecoration(labelText: 'Password'),
                  obscureText: true,
                  textInputAction: TextInputAction.next,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _code,
                  decoration: const InputDecoration(
                    labelText: 'Codice (6 cifre)',
                    counterText: '',
                  ),
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _scanQr,
                  icon: const Icon(Icons.qr_code_scanner),
                  label: const Text('Inquadra QR'),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 10),
                  Text(
                    _error!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                ],
                const SizedBox(height: 14),
                FilledButton(
                  onPressed: _busy ? null : _pair,
                  child: Text(_busy ? 'Associazione…' : 'Associa questo telefono'),
                ),
                TextButton(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => PermissionsScreen(store: widget.store),
                      ),
                    );
                  },
                  child: const Text('Permessi'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _QrScanPage extends StatefulWidget {
  const _QrScanPage();

  @override
  State<_QrScanPage> createState() => _QrScanPageState();
}

class _QrScanPageState extends State<_QrScanPage> {
  bool _done = false;

  @override
  Widget build(BuildContext context) {
    return IrisGlassScaffold(
      appBar: AppBar(title: const Text('Inquadra QR')),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: MobileScanner(
          onDetect: (capture) {
            if (_done) return;
            for (final barcode in capture.barcodes) {
              final raw = barcode.rawValue;
              if (raw == null) continue;
              final m = RegExp(r'IRISNOUS:(\d{6})', caseSensitive: false).firstMatch(raw)
                  ?? RegExp(r'(\d{6})').firstMatch(raw);
              if (m != null) {
                _done = true;
                Navigator.of(context).pop(m.group(1));
                return;
              }
            }
          },
        ),
      ),
    );
  }
}
