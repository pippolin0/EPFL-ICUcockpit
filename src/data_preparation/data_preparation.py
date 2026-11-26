"""Functions preparing the dataset to be used for the ML pipeline"""
from pathlib import Path
import pandas as pd

def merge_data(
    raw: pd.DataFrame, 
    pEEG: pd.DataFrame, 
    static: pd.DataFrame, 
    patient_id: int,
    resolution: str = '1s') -> pd.DataFrame:
    """Merge all separated datasets into one containing all the features measured at the 
    same frequency. 
    Note that this function only supports downsampling, i.e. resolution >= 1s, since 
    this fits our study use.
    Ensures the 8 duplicated features from raw data to pEEG are kept from raw data and excluded from pEEG datasets, 
    as discussed in feature analysis.

    Args:
        raw (pd.DataFrame): the raw data containing most of the features measured at a resolution of 4ms
        pEEG (pd.DataFrame): processed EEG data containing several pre-computed features at a resolution of 1s
        static (pd.DataFrame): data containing interesting features about the patients, no resolution
        patient_id (int): study ID of the patient recording (e.g. 3 for '10-003.csv')
        resolution (str): the resolution at which all features are merged, default is '1s'
    """
    # --- Downsampling rules: raw ---

    # taken all raw features into account, not in dictionary if removed during feature analysis
    agg_mean_raw_cols = [
    'Intellivue/ECG_II', 'Intellivue/EEG_1', 'Intellivue/EEG_2', 'Intellivue/PLETH', 'Intellivue/RESP', 
    'Intellivue/ECG_HR', 'Intellivue/RR', 'Intellivue/PLETH_SAT_O2', 'Intellivue/PLETH_HR', 'Intellivue/PLETH_PERF_REL', 
    'Intellivue/NIBP_SYS', 'Intellivue/NIBP_DIA', 'Intellivue/NIBP_MEAN']
    agg_last_raw_cols = ['SOC', 'MOAAS', 'Endoscopy', 'EVENT', 'Misc']
    agg_sum_raw_cols = ['Propofol']
    agg_dict_raw = (
        {col: 'mean' for col in agg_mean_raw_cols if col in raw.columns} |
        {col: 'last' for col in agg_last_raw_cols if col in raw.columns} |
        {col: 'sum' for col in agg_sum_raw_cols if col in raw.columns}
    )

    # --- Downsampling rules: pEEG ---

    # ensures the 8 duplicated columns from raw data are excluded - keep as much independence from feature analysis as possible
    agg_mean_pEEG_cols = [
        'abs_subdelta', 'abs_delta1', 'abs_delta2', 'abs_theta',
        'abs_alpha', 'abs_beta1', 'abs_beta2', 'abs_gamma',
        'rel_subdelta', 'rel_delta1', 'rel_delta2', 'rel_theta',
        'rel_alpha', 'rel_beta1', 'rel_beta2', 'rel_gamma',
        'sync_subdelta', 'sync_delta1', 'sync_delta2', 'sync_theta',
        'sync_alpha', 'sync_beta1', 'sync_beta2', 'sync_gamma',
        'MF', 'SEF95', 'WSMF30', 'WSMF49',
        'PE31', 'PE32', 'PE61',
        'SFS', 'CFS', 'PFS',
        'WSMF_Klimpel', 'MF_Jordan', 'SEF95_Jordan',
        'WSMF30_16', 'WSMF49_16', 'WSMF_Klimpel_16',
    ]
    agg_dict_pEEG = {col: 'mean' for col in agg_mean_pEEG_cols if col in pEEG.columns}

    downsampled_raw = raw.resample(rule=resolution).agg(agg_dict_raw)
    downsampled_pEEG = pEEG[list(agg_dict_pEEG.keys())] if resolution == '1s' else pEEG.resample(rule=resolution).agg(agg_dict_pEEG)

    # --- Merging ---
    full_timed_data = downsampled_raw.merge(
        downsampled_pEEG, 
        left_index=True,
        right_index=True, 
        how='left'
    )
    # insert patient ID up front and merge static features for this recording
    full_timed_data.insert(0, 'ID', patient_id)
    full_data = full_timed_data.reset_index(names='Time').merge(static, on='ID', how='left')
    return full_data


def merge_all_recordings(
    raw_dir: str | Path,
    peeg_dir: str | Path,
    static_path: str | Path,
    resolution: str = '1s') -> pd.DataFrame:
    """Load, downsample, and merge raw, pEEG, and static data across all patient recordings.

    Args:
        raw_dir (str | Path): directory containing '10-XXX.csv' raw files
        peeg_dir (str | Path): directory containing '10-XXX_pEEG.csv' pEEG files
        static_path (str | Path): path to 'DOSE-I_static_data.csv'
        resolution (str): target downsampling resolution (>= '1s'), default is '1s'
    """
    raw_dir = Path(raw_dir)
    peeg_dir = Path(peeg_dir)
    static = pd.read_csv(static_path)

    patient_dfs = []
    for raw_path in sorted(raw_dir.glob('10-*.csv')):
        patient_id = int(raw_path.stem.split('-')[1])
        peeg_path = peeg_dir / f'{raw_path.stem}_pEEG.csv'

        raw = pd.read_csv(raw_path, index_col=0, parse_dates=True, low_memory=False)
        pEEG = pd.read_csv(peeg_path, index_col=0, parse_dates=True, na_values=['?'])

        df_patient = merge_data(raw, pEEG, static, patient_id=patient_id, resolution=resolution)
        patient_dfs.append(df_patient)

    return pd.concat(patient_dfs, ignore_index=True)

def add_medication_features(data: pd.DataFrame):
    """Create new propofol and consciousness related features: 
    - time since last bolus received 
    - amount of last bolus received 
    - cumulative amount of propofol received
    - time since last LoC 
    - last MOAA/S score 
    - time since last MOAA/S measure 

    Args:
        data (pd.DataFrame): raw data containing needed features ('SOC', 'MOAAS', 'Propofol')
    """
    ...

def create_labels(data: pd.DataFrame):
    """Create the labels (y) needed for ML validation:
    - Time to next RoC
    - Event happened indicator

    Args:
        data (pd.DataFrame): dataset containing 'SOC' feature to create these labels
    """
    ...
