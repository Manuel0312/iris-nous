# PhysioNet EEG corpus (vendored windows)

- File: `physionet_mmidb_s001r01_windows.npz`
- Dataset: [EEG Motor Movement/Imagery Dataset](https://physionet.org/content/eegmmidb/1.0.0/) (eegmmidb 1.0.0)
- Subject/run: S001 R01 (eyes-open baseline)
- Content: twelve 1-second windows, 8 channels (C3, C4, Cz, Fc3, Fc4, Cp3, Cp4, Fz), 160 Hz
- License: ODC-BY-1.0 (PhysioNet)

Rebuild from the full EDF with `scripts/_build_eeg_corpus_npz.py` (not shipped in production).
