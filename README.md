# EPFL-ICUcockpit
The goal of this repository is to create a ML model based on the DOSE-I dataset, by EPFL students under the supervision of ICUcockpit members.

## Download the dataset

With Python 3.9 or a newer version, run this command on your terminal:

```bash
python3 scripts/download_data.py
```

This downloads all six dataset archives from the pinned [DOSE-I v2 Zenodo record](https://zenodo.org/records/22145442), checks their published MD5 checksums, and extracts them into:

```text
data/
├── raw/       # Original biosignal CSVs from data.zip
├── pEEG/      # Precomputed EEG features
├── metadata/  # Recording metadata and its README
├── static/    # Static subject data and its README
├── artifacts/ # EEG artifact annotations and summaries
└── plots/     # Recording overview plots
```

It is also possible to go on the Zenodo record and manually download the dataset, but be sure to keep the above format for consistency.

The download is approximately 808 MB compressed. Please read the dataset's [Data Use Agreement](https://zenodo.org/records/22145442/files/Data_Use_Agreement.txt?download=1) before use, and cite the dataset using the citation provided on its Zenodo page.

The script always saves the dataset in the repository's `data/` directory, regardless of the current working directory. The destination cannot be changed through a command-line option, keeping the folder structure consistent across users.

Rerunning skips completed folders whose recorded files still exist with the expected sizes. This checks completion, not whether extracted files have been edited. Interrupted archive downloads restart; already completed folders are retained.

ZIP files are removed after successful extraction. Add `--keep-archives` to retain them in the destination's `.downloads/` directory. Downloaded data is excluded from Git by `.gitignore`.
