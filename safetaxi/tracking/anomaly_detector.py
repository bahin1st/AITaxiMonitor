import numpy as np
import pandas as pd  
import joblib
from django.conf import settings

# Load pre-trained model
#anomaly_model_path = settings.BASE_DIR / "models/anomaly_multi_model_new.pkl"
rating_model_path = settings.BASE_DIR / "models/trip_rating_model1.pkl"
ensemble_model = settings.BASE_DIR / "models/anomaly_multi_model_ensemble.pkl"


# rf_model = joblib.load(anomaly_model_path)
rating_model = joblib.load(rating_model_path)
ensemble_model = joblib.load(ensemble_model)
FEATURES = ["speed", "acceleration", "heading", "yaw_rate",
            "steering_angle", "jerk", "traffic_condition", "road_condition","road_type", "time_of_day"]

def detect_anomalies(data):
    """Detect anomalies based on real-time taxi data."""
    try:
        # Convert dictionary to pandas DataFrame
        feature_df = pd.DataFrame([{feature: data[feature] for feature in FEATURES}])

        # Make predictions using the ensemble model
        predictions = np.array(ensemble_model.predict(feature_df))

        if predictions.ndim == 0:
            predictions = np.array([predictions])
        if predictions.ndim == 1:
            predictions = predictions.reshape(1, -1)

        anomaly_types = ['sudden_brake', 'sudden_acceleration', 'sudden_stop',
                         'sudden_turn', 'tight_turn']

        detected_anomalies = [
            anomaly_types[i] for i, pred in enumerate(predictions[0]) if pred == 1
        ]

        if detected_anomalies:
            return True, ", ".join(detected_anomalies)
        else:
            return False, None

    except Exception as e:
        print(f"Error in anomaly detection: {e}")
        return False, None

def rate_trip_model(data):
    try:
        result = rating_model.predict(data)[0]
        
    except Exception as e:
        print(f"Error in trip rating: {e}")
        result = None
    return float(result)
        
    