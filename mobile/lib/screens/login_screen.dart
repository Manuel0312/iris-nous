import 'package:flutter/material.dart';

import '../config.dart';
import '../services/auth_store.dart';
import '../services/iris_api.dart';
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
    return Scaffold(
      appBar: AppBar(title: const Text('Accedi · Associa')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Stesso account del sito Iris. Il codice a 6 cifre lo trovi in Ecosistema → Telefono '
            '(oppure Il tuo telefono).',
            style: TextStyle(height: 1.35),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _base,
            decoration: const InputDecoration(
              labelText: 'URL Iris',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.url,
            autocorrect: false,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _user,
            decoration: const InputDecoration(
              labelText: 'Username',
              border: OutlineInputBorder(),
            ),
            autocorrect: false,
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _pass,
            decoration: const InputDecoration(
              labelText: 'Password',
              border: OutlineInputBorder(),
            ),
            obscureText: true,
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _code,
            decoration: const InputDecoration(
              labelText: 'Codice associazione (6 cifre)',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
            maxLength: 6,
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _busy ? null : _pair,
            child: Text(_busy ? 'Associazione…' : 'Associa questo telefono'),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => PermissionsScreen(store: widget.store),
                ),
              );
            },
            child: const Text('Vedi e gestisci i permessi'),
          ),
          const SizedBox(height: 16),
          Text(
            'L’app configura e rileva eventi. Non risponde né rifiuta le chiamate cellulari al posto del telefono.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54),
          ),
        ],
      ),
    );
  }
}
