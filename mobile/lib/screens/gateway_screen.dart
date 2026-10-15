import 'package:flutter/material.dart';

import '../services/auth_store.dart';
import '../theme/iris_theme.dart';
import 'home_screen.dart';
import 'login_screen.dart';
import 'permissions_screen.dart';
import 'site_shell_screen.dart';

/// Entry hub: same journeys as PC/site, then native permissions.
class GatewayScreen extends StatelessWidget {
  const GatewayScreen({super.key, required this.store});

  final AuthStore store;

  void _openSite(BuildContext context, {String path = '/'}) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SiteShellScreen(store: store, initialPath: path),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return IrisGlassScaffold(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 36),
        children: [
          Text(
            'Iris Nous',
            style: TextStyle(
              fontSize: 36,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.8,
              color: IrisTheme.accent,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Stesso mondo del sito: account, Ecosistema, cuffia. '
            'L’app serve per le autorizzazioni del telefono.',
            style: TextStyle(
              color: IrisTheme.deep.withValues(alpha: 0.72),
              height: 1.4,
              fontSize: 15,
            ),
          ),
          const SizedBox(height: 22),
          _Card(
            title: 'Scopri Iris (sito completo)',
            body:
                'Come da PC o da Safari: registrati, anagrafica, Ecosistema, '
                'In ascolto. Grafica e animazioni 3D identiche.',
            cta: 'Apri Iris',
            onTap: () => _openSite(context),
          ),
          _Card(
            title: 'Ho già un account',
            body:
                'Hai creato l’account sul sito? Associa questo telefono con '
                'username, password e PIN da «Il tuo telefono».',
            cta: 'Associa dispositivo',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => LoginScreen(store: store),
                ),
              );
            },
          ),
          _Card(
            title: 'Autorizzazioni',
            body:
                'Dopo l’associazione: chiamate, notifiche, apertura WhatsApp '
                'al SÌ (senza leggere i messaggi).',
            cta: 'Permessi',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => PermissionsScreen(store: store),
                ),
              );
            },
          ),
          FutureBuilder<bool>(
            future: store.isPaired(),
            builder: (context, snap) {
              if (snap.data != true) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(top: 8),
                child: FilledButton(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => HomeScreen(store: store),
                      ),
                    );
                  },
                  child: const Text('Vai allo stato companion'),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({
    required this.title,
    required this.body,
    required this.cta,
    required this.onTap,
  });

  final String title;
  final String body;
  final String cta;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: GlassPane(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: IrisTheme.deep,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              body,
              style: TextStyle(
                color: IrisTheme.deep.withValues(alpha: 0.7),
                height: 1.35,
              ),
            ),
            const SizedBox(height: 14),
            FilledButton(onPressed: onTap, child: Text(cta)),
          ],
        ),
      ),
    );
  }
}
