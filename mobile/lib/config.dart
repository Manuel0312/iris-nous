/// Configurazione Iris Nous companion (allineata al sito).
class IrisConfig {
  IrisConfig._();

  /// Backend pubblico (Render). Override in debug se serve locale.
  static const String defaultBaseUrl = 'https://iris-nous.onrender.com';

  static const String pairPath = '/api/companion/pair';
  static const String heartbeatPath = '/api/companion/heartbeat';
  static const String statusPath = '/api/companion/status';
  static const String eventPath = '/api/companion/event';
  static const String musicNextPath = '/api/companion/music/next';

  static const String webEcosistema = '/ecosistema';
  static const String webTelefonoSetup = '/telefono-setup';
  static const String webContesto = '/contesto';
  static const String webCuffia = '/cuffia';
  static const String webSpotify = '/auth/spotify/start';
  static const String webAnagrafica = '/anagrafica';
  static const String webChat = '/chatta';

  /// Brand accent (pari al sito 0.4.54+).
  static const int accentBlue = 0xFF00B7FF;
  static const int accentCyan = 0xFF6EF0FF;
}
