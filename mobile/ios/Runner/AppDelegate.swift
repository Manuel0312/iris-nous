import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate {
  private let callBridge = CallObserverBridge()

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)
    if let controller = window?.rootViewController as? FlutterViewController {
      callBridge.attach(messenger: controller.binaryMessenger)
    } else {
      // Flutter 3+: engine may attach after first frame — retry once.
      DispatchQueue.main.async { [weak self] in
        guard let self else { return }
        if let controller = self.window?.rootViewController as? FlutterViewController {
          self.callBridge.attach(messenger: controller.binaryMessenger)
        }
      }
    }
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
