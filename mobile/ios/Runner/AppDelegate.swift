import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate {
  private let callBridge = CallObserverBridge()
  private let callControl = CallControlBridge()

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)
    attachBridges()
    // Flutter 3+: engine may attach after first frame — retry once.
    DispatchQueue.main.async { [weak self] in
      self?.attachBridges()
    }
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  private func attachBridges() {
    guard let controller = window?.rootViewController as? FlutterViewController else { return }
    callBridge.attach(messenger: controller.binaryMessenger)
    callControl.attach(messenger: controller.binaryMessenger)
  }
}
