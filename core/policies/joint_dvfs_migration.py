from core.migration import *
import sys, os
import numpy as np
from tensorflow.keras.models import load_model
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class JointDVFSMigration():
    def __init__(self):
        self.__model = load_model(config.MODEL_PATH)
    
    def predictNextEnergy(self, input_data):

        y_pred = model.predict(X_test).flatten()
        