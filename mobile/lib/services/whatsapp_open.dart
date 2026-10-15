import 'package:url_launcher/url_launcher.dart';

/// Opens WhatsApp in the foreground. Does not read message content.
Future<bool> openWhatsApp({String url = 'whatsapp://'}) async {
  final candidates = <Uri>[
    Uri.parse(url.isNotEmpty ? url : 'whatsapp://'),
    Uri.parse('whatsapp://'),
    Uri.parse('https://wa.me/'),
  ];
  for (final uri in candidates) {
    try {
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (ok) return true;
    } catch (_) {
      /* try next */
    }
  }
  return false;
}
