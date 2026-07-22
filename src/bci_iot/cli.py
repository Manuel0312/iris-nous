"""Command-line entry points for local development."""

from __future__ import annotations

import argparse
from pathlib import Path

from bci_iot import __version__
from bci_iot.config import load_app_config


def main(argv: list[str] | None = None) -> int:
    """CLI: version, train, calibrate, run pipeline, serve-help."""

    parser = argparse.ArgumentParser(prog="bci-iot", description="Voilà thesis CLI")
    parser.add_argument("--version", action="store_true", help="Show package version")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML config (default: configs/default.yaml)",
    )
    sub = parser.add_subparsers(dest="command")

    train_parser = sub.add_parser("train", help="Train the default sklearn intent classifier")
    train_parser.add_argument(
        "--out",
        type=str,
        default="models/baseline.joblib",
        help="Output path for the trained model",
    )
    train_parser.add_argument("--samples", type=int, default=300, help="Synthetic sample count")

    cal_parser = sub.add_parser("calibrate", help="Train a per-user model (software calibration)")
    cal_parser.add_argument("--user", required=True, help="Username / profile id")
    cal_parser.add_argument("--samples", type=int, default=300)
    cal_parser.add_argument("--out-dir", type=str, default="models/users")

    run_parser = sub.add_parser("run", help="Run the EEG→intent→action pipeline (simulator)")
    run_parser.add_argument("--windows", type=int, default=10, help="Number of EEG windows")
    run_parser.add_argument("--user", type=str, default=None, help="Optional profile username")
    run_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional model path (default: config or heuristic)",
    )
    run_parser.add_argument(
        "--context",
        type=str,
        default=None,
        help="Optional starting context: idle|music_mode|light_mode|call_mode",
    )
    run_parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Override acquisition.source: synthetic | brainflow_synthetic",
    )

    sub.add_parser("serve-help", help="Print how to open the config web app")

    exp_parser = sub.add_parser(
        "experiment",
        help="Run thesis experiment (surrogate MoABB-paradigm → report)",
    )
    exp_parser.add_argument(
        "--mode",
        choices=("surrogate", "moabb"),
        default="surrogate",
        help="surrogate = prior EEG offline (default); moabb = optional real stack",
    )
    exp_parser.add_argument("--subjects", type=int, default=8)
    exp_parser.add_argument("--windows-per-class", type=int, default=12)
    exp_parser.add_argument("--seed", type=int, default=42)
    exp_parser.add_argument(
        "--out-dir",
        type=str,
        default="results/experiments",
        help="Directory for JSON/Markdown reports",
    )

    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.command == "train":
        from bci_iot.ml import train_default_classifier

        out = Path(args.out)
        classifier, accuracy = train_default_classifier(
            n_samples=args.samples,
            model_path=out,
        )
        print(f"trained={classifier.is_fitted} accuracy_cv={accuracy:.3f} saved={out}")
        return 0

    if args.command == "calibrate":
        from bci_iot.ml.calibrate import calibrate_user_model

        path, accuracy = calibrate_user_model(
            args.user,
            models_dir=args.out_dir,
            n_samples=args.samples,
        )
        print(f"calibrated user={args.user} accuracy_cv={accuracy:.3f} saved={path}")
        return 0

    if args.command == "run":
        from bci_iot.pipeline.factory import build_pipeline
        from bci_iot.types import ActionContext

        config = load_app_config(args.config)
        if args.source:
            config = config.model_copy(
                update={
                    "acquisition": config.acquisition.model_copy(
                        update={"source": args.source}
                    )
                }
            )
        model_path = args.model
        if model_path is None and args.user:
            from bci_iot.accounts.names import safe_username

            candidate = Path("models/users") / f"{safe_username(args.user)}.joblib"
            if candidate.exists():
                model_path = str(candidate)

        runner = build_pipeline(
            config,
            username=args.user,
            max_windows_cap=args.windows,
            model_path=model_path,
        )
        if args.context:
            runner.router.set_context(ActionContext(args.context))

        results = runner.run(max_windows=args.windows)
        actions = sum(1 for r in results if r.action is not None)
        clean = sum(1 for r in results if r.is_clean)
        print(
            f"windows={len(results)} clean={clean} actions={actions} "
            f"dry_run={config.integrations.dry_run}"
        )
        for step in results:
            action_name = step.action.name if step.action else "-"
            print(
                f"  t={step.intent.timestamp_s:.2f}s "
                f"intent={step.intent.label.value} "
                f"conf={step.intent.confidence:.2f} "
                f"action={action_name} "
                f"clean={step.is_clean}"
            )
        return 0

    if args.command == "serve-help":
        print("Doppio click su: APRI IL SITO.bat")
        print("Oppure: uvicorn bci_iot.web.app:app --host 127.0.0.1 --port 8000")
        return 0

    if args.command == "experiment":
        if args.mode == "moabb":
            from bci_iot.experiments.moabb_loader import load_moabb_feature_bundle

            try:
                load_moabb_feature_bundle()
            except (ImportError, NotImplementedError) as exc:
                print(f"moabb mode non disponibile: {exc}")
                print("Usa: bci-iot experiment --mode surrogate")
                return 1
            return 0

        from bci_iot.experiments import run_surrogate_experiment

        report = run_surrogate_experiment(
            n_subjects=args.subjects,
            windows_per_class=args.windows_per_class,
            seed=args.seed,
            out_dir=args.out_dir,
        )
        print(f"mode={report.mode}")
        print(
            f"LOSO accuracy={report.loso['mean_accuracy']:.3f} "
            f"± {report.loso['std_accuracy']:.3f}"
        )
        print(
            f"5-fold accuracy={report.kfold['mean_accuracy']:.3f} "
            f"± {report.kfold['std_accuracy']:.3f}"
        )
        print(f"reports -> {args.out_dir}/latest.md")
        return 0

    config = load_app_config(args.config)
    print(f"bci-iot {__version__}")
    print(f"acquisition.source={config.acquisition.source}")
    print(f"sample_rate_hz={config.acquisition.sample_rate_hz}")
    print(f"integrations.dry_run={config.integrations.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
