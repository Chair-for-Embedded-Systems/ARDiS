import sys, os
import numpy as np
from tensorflow.keras.models import load_model
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pandas as pd
import joblib
import time
import re

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class MLPredictor():
    def __init__(self, objective='Energy', model_type='transformer'):
        self.__sequence_length = 5
        self.__target_variable = objective
        if 'Energy' in self.__target_variable:
            if model_type == 'transformer':
                self.__scaler_filename = config.ENERGY_SEQUENCE_SCALER_PATH
                self.__model_filename = config.ENERGY_TRANSFORMER_MODEL_PATH
            elif model_type == 'rnn':
                self.__scaler_filename = config.ENERGY_SEQUENCE_SCALER_PATH
                self.__model_filename = config.ENERGY_RNN_MODEL_PATH
            elif model_type == 'nn':
                self.__scaler_filename = config.ENERGY_INSTANT_SCALER_PATH
                self.__model_filename = config.ENERGY_NN_MODEL_PATH
            elif model_type == 'xgb':
                self.__scaler_filename = config.ENERGY_INSTANT_SCALER_PATH
                self.__model_filename = config.ENERGY_XGB_MODEL_PATH
            elif model_type == 'rf':
                self.__scaler_filename = config.ENERGY_INSTANT_SCALER_PATH
                self.__model_filename = config.ENERGY_RF_MODEL_PATH
        elif 'IPC' in self.__target_variable:
            if model_type == 'transformer':
                self.__scaler_filename = config.PERFORMANCE_SEQUENCE_SCALER_PATH
                self.__model_filename = config.PERFORMANCE_TRANSFORMER_MODEL_PATH
            elif model_type == 'rnn':
                self.__scaler_filename = config.PERFORMANCE_SEQUENCE_SCALER_PATH
                self.__model_filename = config.PERFORMANCE_RNN_MODEL_PATH
            elif model_type == 'nn':
                self.__scaler_filename = config.PERFORMANCE_INSTANT_SCALER_PATH
                self.__model_filename = config.PERFORMANCE_NN_MODEL_PATH
            elif model_type == 'xgb':
                self.__scaler_filename = config.PERFORMANCE_INSTANT_SCALER_PATH
                self.__model_filename = config.PERFORMANCE_XGB_MODEL_PATH
            elif model_type == 'rf':
                self.__scaler_filename = config.PERFORMANCE_INSTANT_SCALER_PATH
                self.__model_filename = config.PERFORMANCE_RF_MODEL_PATH

        # Load the saved model and scaler
        self.__scaler = joblib.load(self.__scaler_filename)
        self.__model = load_model(self.__model_filename)


    def preprocess_input(self, input_data):
        cluster_mapping = {'P': 0, 'E1': 1, 'E2': 2}
        input_data['AOI_Cluster'] = input_data['AOI_Cluster'].map(cluster_mapping)
        input_data['Other1_Cluster'] = input_data['Other1_Cluster'].map(cluster_mapping)
        input_data['Other2_Cluster'] = input_data['Other2_Cluster'].map(cluster_mapping)

        # Drop columns that were not used during training
        input_data = input_data.drop(columns=['Other1_Applications', 'Other2_Applications', 'Same_Cluster_Applications'])

        # Scale the features
        features_to_scale = input_data
        scaled_features = self.__scaler.transform(features_to_scale)

        # Reshape as a sequence for the model input
        X_sequence = np.array([scaled_features.flatten()] * self.__sequence_length)
        X_sequence = X_sequence.reshape(1, self.__sequence_length, -1)

        return X_sequence

    def run_inference_and_report(self, input_data):
        X_input_sequence = self.preprocess_input(input_data)
        
        start_time = time.time()
        prediction = self.__model.predict_on_batch(X_input_sequence)
        end_time = time.time()
        
        inference_time_ms = (end_time - start_time) * 1000
        print(f"Prediction: {prediction[0][0]}")
        print(f"Inference Time: {inference_time_ms:.3f} ms")
        
        return prediction[0][0], inference_time_ms

    def load_data_from_files(self, results_folder, frequency=3200):
        dataset = []
        log_path = os.path.join(results_folder, 'periodic_counters.log')
        if os.path.isfile(log_path):
            epochs = parse_log_file(log_path)
            dataset.extend(create_dataset(epochs, frequency, results_folder).to_dict(orient='records'))
        return pd.DataFrame(dataset)

    def run_inference_from_files(self, results_folder, frequency=3200):
        # Load and prepare data from log files
        data = self.load_data_from_files(results_folder, frequency)
        
        # Iterate over each row in the prepared dataset and make predictions
        predictions = []
        for _, row in data.iterrows():
            input_data = pd.DataFrame([row])  # Convert row to a DataFrame for processing
            print(input_data)
            prediction, inference_time_ms = self.run_inference_and_report(input_data)
            predictions.append({'Prediction': prediction, 'Inference Time (ms)': inference_time_ms})
        
        return pd.DataFrame(predictions)

# Map each core to its cluster type
core_to_cluster = {core: 'P' for core in config.intel_p_core_ids}
core_to_cluster.update({core: 'E1' for core in config.intel_e_core_ids_cluster_1})
core_to_cluster.update({core: 'E2' for core in config.intel_e_core_ids_cluster_2})

def parse_log_file(filepath):
    """Parses periodic_counters.log and returns a structured list of epochs."""
    epochs = []
    with open(filepath, 'r') as file:
        current_epoch = {}
        for line in file:
            if 'Current mapped cores' in line:
                # Start of a new epoch
                if current_epoch:
                    epochs.append(current_epoch)
                current_epoch = {'cores': {}}
            elif 'Core' in line:
                core_data = parse_core_line(line)
                core_id = core_data['core']
                current_epoch['cores'][core_id] = core_data
            elif 'SYSTEM' in line:
                current_epoch['system'] = parse_system_line(line)
        if current_epoch:
            epochs.append(current_epoch)
    return epochs


def parse_core_line(line):
    """Extracts core information from a log line."""
    core_info = {}
    core_id = int(re.search(r'Core (\d+):', line).group(1))
    app_name = re.search(r'app = (.*?) \|', line).group(1)
    core_info['core'] = core_id
    core_info['app'] = app_name
    core_info['cluster'] = core_to_cluster.get(core_id, 'Unknown')
    
    # Update regex to support multiple hyphens in metric names
    core_info.update({k: int(v) for k, v in re.findall(r'([\w-]+) = (\d+)', line)})
    
    #print(core_info)  # For debugging to confirm it works as expected
    return core_info

def parse_system_line(line):
    """Extracts system-wide information from a log line."""
    return {k: float(v) for k, v in re.findall(r'(\w+/energy-\w+/) = ([\d.]+)', line)}

def create_dataset(epochs, frequency, log_path):
    """Creates a DataFrame from parsed epochs with AOI-based structure."""
    path_date_time = log_path.split("_")[0] + "_" + log_path.split("_")[1]
    path_date_time = path_date_time.replace("-", "")
    data_rows = []
    for epoch in epochs:
        #print(epoch)  # For debugging, to see the structure of each epoch
        if "system" in epoch:
            for aoicore, aoidata in epoch['cores'].items():
                aoi_cluster = aoidata['cluster']
                #print(aoidata)
                # Determine the other two clusters based on the AOI cluster
                if aoi_cluster == 'P':
                    other1_cluster, other2_cluster = 'E1', 'E2'
                elif aoi_cluster == 'E1':
                    other1_cluster, other2_cluster = 'P', 'E2'
                elif aoi_cluster == 'E2':
                    other1_cluster, other2_cluster = 'P', 'E1'
                else:
                    continue  # Skip if the cluster is not recognized

                # Separate applications based on the determined clusters
                same_cluster_apps = {c: d for c, d in epoch['cores'].items() if d['cluster'] == aoi_cluster and c != aoicore}
                other1_apps = {c: d for c, d in epoch['cores'].items() if d['cluster'] == other1_cluster}
                other2_apps = {c: d for c, d in epoch['cores'].items() if d['cluster'] == other2_cluster}
                # Proceed with data aggregation and row construction as before
                row = {
                    #'Experiment_ID': path_date_time,
                    #'AOI_Application': aoidata['app'],
                    'AOI_Core': aoicore,
                    'AOI_Cluster': aoi_cluster,
                    'AOI_IPC': aoidata['instructions'] / aoidata['cycles'] if aoidata['cycles'] else 0,
                    'AOI_Instructions': aoidata.get('instructions', 0),
                    'AOI_LLC_Loads': aoidata.get('LLC-loads', 0),
                    'AOI_LLC_Misses': aoidata.get('LLC-load-misses', 0),
                    'AOI_Stores': aoidata.get('LLC-stores', 0),
                    'AOI_Store_Misses': aoidata.get('LLC-store-misses', 0),
                    'AOI_Cycles': aoidata.get('cycles', 0),
                    'AOI_Branch_Misses': aoidata.get('branch-misses', 0),
                    'AOI_Branches': aoidata.get('branches', 0),
                    'Frequency': aoidata.get('frequency',0),
                    #'Energy': epoch['system']['power/energy-psys/'],
                }

                # Add same cluster characteristics
                row.update({
                    'Same_Cluster_Applications': ', '.join([data['app'] for data in same_cluster_apps.values()]),
                    'Same_Cluster_Instructions': sum(data.get('instructions', 0) for data in same_cluster_apps.values()),
                    'Same_Cluster_LLC_Loads': sum(data.get('LLC-loads', 0) for data in same_cluster_apps.values()),
                    'Same_Cluster_LLC_Misses': sum(data.get('LLC-load-misses', 0) for data in same_cluster_apps.values()),
                    'Same_Cluster_Stores': sum(data.get('LLC-stores', 0) for data in same_cluster_apps.values()),
                    'Same_Cluster_Store_Misses': sum(data.get('LLC-store-misses', 0) for data in same_cluster_apps.values()),
                    'Same_Cluster_Cycles': sum(data.get('cycles', 0) for data in same_cluster_apps.values()),
                    'Same_Cluster_Branch_Misses': sum(data.get('branch-misses', 0) for data in same_cluster_apps.values()),
                    'Same_Cluster_Branches': sum(data.get('branches', 0) for data in same_cluster_apps.values())
                })

                # Add characteristics for Other1 and Other2 clusters
                row.update({
                    'Other1_Applications': ', '.join([data['app'] for data in other1_apps.values()]),
                    'Other1_Cluster': other1_cluster,
                    'Other1_Instructions': sum(data.get('instructions', 0) for data in other1_apps.values()),
                    'Other1_LLC_Loads': sum(data.get('LLC-loads', 0) for data in other1_apps.values()),
                    'Other1_LLC_Misses': sum(data.get('LLC-load-misses', 0) for data in other1_apps.values()),
                    'Other1_Stores': sum(data.get('LLC-stores', 0) for data in other1_apps.values()),
                    'Other1_Store_Misses': sum(data.get('LLC-store-misses', 0) for data in other1_apps.values()),
                    'Other1_Cycles': sum(data.get('cycles', 0) for data in other1_apps.values()),
                    'Other1_Branch_Misses': sum(data.get('branch-misses', 0) for data in other1_apps.values()),
                    'Other1_Branches': sum(data.get('branches', 0) for data in other1_apps.values())
                })

                row.update({
                    'Other2_Applications': ', '.join([data['app'] for data in other2_apps.values()]),
                    'Other2_Cluster': other2_cluster,
                    'Other2_Instructions': sum(data.get('instructions', 0) for data in other2_apps.values()),
                    'Other2_LLC_Loads': sum(data.get('LLC-loads', 0) for data in other2_apps.values()),
                    'Other2_LLC_Misses': sum(data.get('LLC-load-misses', 0) for data in other2_apps.values()),
                    'Other2_Stores': sum(data.get('LLC-stores', 0) for data in other2_apps.values()),
                    'Other2_Store_Misses': sum(data.get('LLC-store-misses', 0) for data in other2_apps.values()),
                    'Other2_Cycles': sum(data.get('cycles', 0) for data in other2_apps.values()),
                    'Other2_Branch_Misses': sum(data.get('branch-misses', 0) for data in other2_apps.values()),
                    'Other2_Branches': sum(data.get('branches', 0) for data in other2_apps.values())
                })

                data_rows.append(row)

    return pd.DataFrame(data_rows)



if __name__ == '__main__':
    predictor = MLPredictor(objective='Energy', model_type='transformer')
    results_folder = config.TRAINING_RESULTS_FOLDER + "/dynamic_map_dynamic_freq/2024-11-06_19-55-39_tr_exp_9apps_mig_45"
    predictor.run_inference_from_files(results_folder)
