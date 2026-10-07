import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config.dart';
import '../services/auth_store.dart';
import '../services/iris_api.dart';
import 'login_screen.dart';
import 'permissions_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.store});

  final AuthStore store;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final IrisApi _api = IrisApi(widget.store);
  Timer? _beat;
  Map<String, dynamic>? _status;
  String? _error;
  String? _username;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    widget.store.username().then((u) {
      if (mounted) setState(() => _username = u);
    });
    _refresh();
    _beat = Timer.periodic(const Duration(seconds: 20), (_) => _refresh());
  }

  @override
  void dispose() {
    _beat?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final body = await _api.heartbeat();
      if (!mounted) return;
      setState(() {
        _status = body;
        _error = null;
      });
    } on IrisApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Errore rete: $e');
    }
  }

  Future<void> _demoCall(String event) async {
    setState(() => _busy = true);
    try {
      await _api.sendEvent(event, caller: 'Demo');
      await _refresh();
    } on IrisApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _musicNext() async {
    setState(() => _busy = true);
    try {
      final r = await _api.musicNext();
      if (!mounted) return;
      final detail = r['detail']?.toString();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            r['status'] == 'ok'
                ? 'Prossima canzone inviata a Spotify'
                : (detail ?? 'Spotify non disponibile'),
          ),
        ),
      );
      await _refresh();
    } on IrisApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openWeb(String path) async {
    final base = await widget.store.baseUrl();
    final uri = Uri.parse('$base$path');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _logout() async {
    await widget.store.clear();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => LoginScreen(store: widget.store)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ctx = (_status?['context'] as Map?)?.cast<String, dynamic>() ?? {};
    final focus = (ctx['focus'] as Map?)?.cast<String, dynamic>();
    final call = ctx['incoming_call'] == true;
    final music = ctx['music_playing'] == true;
    final caller = (ctx['caller_name'] as String?) ?? '';
    final track = (ctx['track_hint'] as String?) ?? '';
    final spotify = _status?['spotify_linked'] == true;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Stato'),
        actions: [
          IconButton(
            tooltip: 'Aggiorna',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            _username == null ? 'Associato a Iris' : 'Ciao, $_username',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          if (_error != null)
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          const SizedBox(height: 12),
          _StatusCard(
            title: 'Chiamata',
            value: call ? 'In arrivo${caller.isNotEmpty ? ' · $caller' : ''}' : 'Nessuna',
            tone: call ? Colors.orange.shade100 : Colors.grey.shade100,
          ),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Musica',
            value: music
                ? 'In riproduzione${track.isNotEmpty ? ' · $track' : ''}'
                : (spotify ? 'Spotify collegato (ferma)' : 'Spotify non collegato'),
            tone: music ? Colors.teal.shade50 : Colors.grey.shade100,
          ),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Focus Iris',
            value: (focus?['title'] as String?) ?? '—',
            tone: Colors.blueGrey.shade50,
          ),
          const SizedBox(height: 20),
          Text('Azioni', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: _busy ? null : () => _demoCall('call_incoming'),
                child: const Text('Simula squillo → Iris'),
              ),
              OutlinedButton(
                onPressed: _busy ? null : () => _demoCall('call_ended'),
                child: const Text('Fine chiamata → Iris'),
              ),
              FilledButton(
                onPressed: _busy ? null : _musicNext,
                child: const Text('Prossima canzone'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'I tasti «Simula» sono per test finché non c’è il rilevatore chiamate nativo. '
            'Rispondi / rifiuta restano sul telefono o su In ascolto (SÌ/NO cuffia) — non su questa app.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54),
          ),
          const SizedBox(height: 24),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.security),
            title: const Text('Permessi'),
            subtitle: const Text('Spiegazione e richiesta graduale'),
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => PermissionsScreen(store: widget.store),
                ),
              );
            },
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.open_in_browser),
            title: const Text('Apri In ascolto (Safari / Chrome)'),
            onTap: () => _openWeb(IrisConfig.webContesto),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.headphones),
            title: const Text('Apri La tua cuffia'),
            onTap: () => _openWeb(IrisConfig.webCuffia),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.phone_android),
            title: const Text('Apri Il tuo telefono (sito)'),
            onTap: () => _openWeb(IrisConfig.webTelefonoSetup),
          ),
          const SizedBox(height: 12),
          TextButton(onPressed: _logout, child: const Text('Scollega questo telefono')),
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.title,
    required this.value,
    required this.tone,
  });

  final String title;
  final String value;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tone,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(height: 1.3)),
        ],
      ),
    );
  }
}
