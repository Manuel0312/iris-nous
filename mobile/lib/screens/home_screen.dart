import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config.dart';
import '../services/auth_store.dart';
import '../services/call_observer.dart';
import '../services/iris_api.dart';
import '../theme/iris_theme.dart';
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
  late final CallObserverService _calls = CallObserverService(_api);
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
    _calls.onChanged = () {
      if (mounted) setState(() {});
    };
    _calls.start();
  }

  @override
  void dispose() {
    _beat?.cancel();
    _calls.stop();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final body = await _api.heartbeat();
      if (!mounted) return;
      setState(() {
        _status = body;
        _error = null;
        final u = body['username'] as String?;
        if (u != null && u.isNotEmpty) _username = u;
      });
    } on IrisApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401 || e.statusCode == 403) {
        await widget.store.clear();
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
          MaterialPageRoute<void>(builder: (_) => LoginScreen(store: widget.store)),
        );
        return;
      }
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

  Map<String, dynamic> _eco() {
    final raw = _status?['ecosystem'];
    if (raw is Map) return raw.cast<String, dynamic>();
    return {
      'cuffia': {
        'done': _status?['calibration_complete'] == true,
        'linked': _status?['headset_linked'] == true,
      },
      'telefono': {'done': _status?['phone_paired'] == true},
      'canali': {
        'done': _status?['spotify_linked'] == true,
        'spotify': _status?['spotify_linked'] == true,
      },
    };
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
    final eco = _eco();
    final cuffiaDone = (eco['cuffia'] as Map?)?['done'] == true;
    final telefonoDone = (eco['telefono'] as Map?)?['done'] == true;
    final canaliDone = (eco['canali'] as Map?)?['done'] == true;
    final accent = Theme.of(context).colorScheme.primary;

    final media = MediaQuery.of(context);
    final padH = media.size.width >= 720 ? 32.0 : 20.0;
    final wideEco = media.size.width >= 560;

    Widget ecoSteps() {
      final cuffia = _EcoStepCard(
        mark: '1',
        title: 'Cuffia',
        done: cuffiaDone,
        subtitle: cuffiaDone ? 'Pronta' : 'Da configurare',
        onTap: () => _openWeb(IrisConfig.webCuffia),
      );
      final telefono = _EcoStepCard(
        mark: '2',
        title: 'Telefono',
        done: telefonoDone,
        subtitle: telefonoDone ? 'Collegato' : 'Da collegare',
        onTap: () => _openWeb(IrisConfig.webTelefonoSetup),
      );
      final canali = _EcoStepCard(
        mark: '3',
        title: 'Canali',
        done: canaliDone,
        subtitle: canaliDone ? 'Spotify attivo (sito)' : 'Collega una volta sul sito',
        onTap: () => _openWeb(
          canaliDone ? IrisConfig.webEcosistema : IrisConfig.webSpotify,
        ),
      );
      if (!wideEco) {
        return Column(
          children: [
            cuffia,
            const SizedBox(height: 10),
            telefono,
            const SizedBox(height: 10),
            canali,
          ],
        );
      }
      return Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: cuffia),
              const SizedBox(width: 10),
              Expanded(child: telefono),
            ],
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.center,
            child: FractionallySizedBox(widthFactor: 0.5, child: canali),
          ),
        ],
      );
    }

    return IrisGlassScaffold(
      appBar: AppBar(
        title: const Text('Iris · Ecosistema'),
        actions: [
          IconButton(
            tooltip: 'Aggiorna',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: ListView(
        padding: EdgeInsets.fromLTRB(
          padH,
          8,
          padH,
          28 + media.padding.bottom,
        ),
        children: [
          Text(
            _username == null ? 'Associato a Iris' : 'Ciao, $_username',
            textAlign: wideEco ? TextAlign.left : TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            'Stesso ecosistema del sito: cuffia, telefono e canali.',
            textAlign: wideEco ? TextAlign.left : TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.black54,
                ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 10),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          const SizedBox(height: 18),
          Text('Ecosistema', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          ecoSteps(),
          const SizedBox(height: 8),
          TextButton.icon(
            onPressed: () => _openWeb(IrisConfig.webEcosistema),
            icon: Icon(Icons.open_in_browser, size: 18, color: accent),
            label: Text('Apri Ecosistema sul sito', style: TextStyle(color: accent)),
          ),
          const SizedBox(height: 16),
          Text('Stato live', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Chiamata',
            value: call ? 'In arrivo${caller.isNotEmpty ? ' · $caller' : ''}' : 'Nessuna',
            tone: call ? const Color(0xFFFFE8CC) : const Color(0xFFF0F0F2),
            accent: accent,
          ),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Musica (Spotify sito)',
            value: music
                ? 'In riproduzione${track.isNotEmpty ? ' · $track' : ''}'
                : (spotify
                    ? 'Collegato — apri Spotify e metti play (rileva via API)'
                    : 'Non collegato — una volta da Ecosistema sul sito'),
            tone: music ? const Color(0xFFE0F7FF) : const Color(0xFFF0F0F2),
            accent: accent,
          ),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Focus Iris',
            value: (focus?['title'] as String?) ?? '—',
            tone: const Color(0xFFE8F6FF),
            accent: accent,
          ),
          const SizedBox(height: 20),
          Text('Azioni', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
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
          if (_calls.lastSent != null)
            Text('Ultimo invio: ${_calls.lastSent}',
                style: TextStyle(color: accent, fontWeight: FontWeight.w600)),
          if (_calls.lastError != null)
            Text(_calls.lastError!,
                style: TextStyle(color: Theme.of(context).colorScheme.error)),
          const SizedBox(height: 6),
          Text(
            _calls.listening
                ? 'Rilevamento nativo attivo. Tieni l’APK aperta (o in background); sul PC apri In ascolto — si aggiorna da sola. '
                    'Rispondi/rifiuta restano sul telefono o con SÌ/NO su In ascolto.'
                : (!_calls.permitted
                    ? 'Concedi «Stato telefono» in Permessi, poi tocca Aggiorna. '
                        'Senza permesso lo squillo non arriva al PC.'
                    : 'Listener non attivo — tocca Aggiorna o riapri i Permessi.'),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54),
          ),
          TextButton(
            onPressed: _busy
                ? null
                : () async {
                    await _calls.start();
                    await _refresh();
                  },
            child: const Text('Riavvia rilevamento chiamate'),
          ),
          const SizedBox(height: 20),
          _LinkTile(
            icon: Icons.security,
            title: 'Permessi',
            subtitle: 'Spiegazione e richiesta graduale',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => PermissionsScreen(store: widget.store),
                ),
              );
            },
          ),
          _LinkTile(
            icon: Icons.hearing,
            title: 'In ascolto (sito)',
            subtitle: 'Contesto e risposte SÌ/NO',
            onTap: () => _openWeb(IrisConfig.webContesto),
          ),
          _LinkTile(
            icon: Icons.person_outline,
            title: 'I miei dati',
            subtitle: 'Anagrafica sul sito',
            onTap: () => _openWeb(IrisConfig.webAnagrafica),
          ),
          _LinkTile(
            icon: Icons.chat_bubble_outline,
            title: 'Le mie chat',
            subtitle: 'Apri sul sito',
            onTap: () => _openWeb(IrisConfig.webChat),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: _logout,
            child: Text(
              'Scollega questo telefono',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        ],
            ),
          ),
        ),
    );
  }
}

class _EcoStepCard extends StatelessWidget {
  const _EcoStepCard({
    required this.mark,
    required this.title,
    required this.subtitle,
    required this.done,
    required this.onTap,
  });

  final String mark;
  final String title;
  final String subtitle;
  final bool done;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;
    return GlassPane(
      padding: EdgeInsets.zero,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(22),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 14, 12, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: accent.withValues(alpha: 0.14),
                        border: Border.all(color: accent.withValues(alpha: 0.35)),
                      ),
                      child: Text(
                        mark,
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: accent,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    const Spacer(),
                    if (done) Icon(Icons.check_circle, size: 18, color: accent),
                  ],
                ),
                const SizedBox(height: 10),
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                const SizedBox(height: 2),
                Text(subtitle, style: const TextStyle(color: Colors.black54, fontSize: 12.5)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.title,
    required this.value,
    required this.tone,
    required this.accent,
  });

  final String title;
  final String value;
  final Color tone;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return GlassPane(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(fontWeight: FontWeight.w600, color: accent)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(height: 1.3)),
        ],
      ),
    );
  }
}

class _LinkTile extends StatelessWidget {
  const _LinkTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
      title: Text(title),
      subtitle: Text(subtitle),
      onTap: onTap,
    );
  }
}
