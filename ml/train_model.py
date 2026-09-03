"""
train_model.py

Trains a regression model that predicts how many people a food
donation can feed, based on: quantity, unit, category, food_type.

Pipeline:
  1. One-hot encode the categorical columns (unit, category, food_type)
  2. Leave quantity as a plain number
  3. Feed all of that into a RandomForestRegressor

Run with: python train_model.py
Requires: donations_dataset.csv (run generate_dataset.py first)
Produces: model.pkl (in this same folder)
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib

CATEGORICAL_COLUMNS = ['unit', 'category', 'food_type']
NUMERIC_COLUMNS = ['quantity']


def main():
    df = pd.read_csv('donations_dataset.csv')

    X = df[NUMERIC_COLUMNS + CATEGORICAL_COLUMNS]
    y = df['people_fed']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # handle_unknown='ignore' means a category/unit the model never saw during
    # training (e.g. a typo) won't crash prediction — it just gets zero weight.
    preprocessor = ColumnTransformer(transformers=[
        ('cat', OneHotEncoder(handle_unknown='ignore'), CATEGORICAL_COLUMNS),
    ], remainder='passthrough')  # passthrough keeps the numeric 'quantity' column as-is

    model = Pipeline(steps=[
        ('preprocess', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=150, max_depth=12, random_state=42)),
    ])

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    print(f'Mean Absolute Error: {mae:.2f} people')
    print(f'R^2 Score: {r2:.4f}')

    joblib.dump(model, 'model.pkl')
    print('Saved trained model to model.pkl')


if __name__ == '__main__':
    main()
