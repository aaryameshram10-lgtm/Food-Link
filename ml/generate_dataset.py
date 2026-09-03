"""
generate_dataset.py

Creates a synthetic training dataset for the "Estimated People Fed"
model, since FoodLink doesn't have historical donation records yet.

The target value isn't random — it's built from a realistic
"people fed per unit" table for each (category, unit) combination,
plus a small food_type effect and random noise (to simulate the
natural variation real donations would have). This gives the model
a genuine pattern to learn instead of pure noise.

Run with: python generate_dataset.py
Produces: donations_dataset.csv (in this same folder)
"""

import csv
import random

random.seed(42)

CATEGORIES = ['Cooked Meal', 'Bakery', 'Produce', 'Packaged Food', 'Dairy', 'Other']
UNITS = ['kg', 'liters', 'pieces', 'boxes', 'plates']
FOOD_TYPES = ['veg', 'nonveg']

# Average number of people ONE unit of that (category, unit) pair can feed.
# e.g. 1 kg of a Cooked Meal feeds ~2.5 people.
FACTOR_TABLE = {
    ('Cooked Meal', 'kg'): 2.5, ('Cooked Meal', 'liters'): 2.2, ('Cooked Meal', 'pieces'): 0.5,
    ('Cooked Meal', 'boxes'): 8.0, ('Cooked Meal', 'plates'): 1.0,

    ('Bakery', 'kg'): 3.0, ('Bakery', 'liters'): 2.0, ('Bakery', 'pieces'): 0.4,
    ('Bakery', 'boxes'): 10.0, ('Bakery', 'plates'): 1.2,

    ('Produce', 'kg'): 2.0, ('Produce', 'liters'): 2.0, ('Produce', 'pieces'): 0.3,
    ('Produce', 'boxes'): 7.0, ('Produce', 'plates'): 1.0,

    ('Packaged Food', 'kg'): 3.5, ('Packaged Food', 'liters'): 3.0, ('Packaged Food', 'pieces'): 1.0,
    ('Packaged Food', 'boxes'): 12.0, ('Packaged Food', 'plates'): 1.5,

    ('Dairy', 'kg'): 4.0, ('Dairy', 'liters'): 4.0, ('Dairy', 'pieces'): 0.5,
    ('Dairy', 'boxes'): 9.0, ('Dairy', 'plates'): 1.3,

    ('Other', 'kg'): 2.5, ('Other', 'liters'): 2.5, ('Other', 'pieces'): 0.5,
    ('Other', 'boxes'): 8.0, ('Other', 'plates'): 1.0,
}

QUANTITY_RANGES = {
    'kg': (1, 50),
    'liters': (1, 50),
    'pieces': (5, 300),
    'boxes': (1, 30),
    'plates': (5, 150),
}


def make_row():
    category = random.choice(CATEGORIES)
    unit = random.choice(UNITS)
    food_type = random.choice(FOOD_TYPES)

    lo, hi = QUANTITY_RANGES[unit]
    quantity = round(random.uniform(lo, hi), 1)

    factor = FACTOR_TABLE[(category, unit)]
    food_type_multiplier = 0.92 if food_type == 'nonveg' else 1.0
    noise = random.gauss(1.0, 0.12)  # +/- ~12% natural variation

    people_fed = quantity * factor * food_type_multiplier * noise
    people_fed = max(1, round(people_fed))

    return [quantity, unit, category, food_type, people_fed]


def main(n_rows=4000):
    with open('donations_dataset.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['quantity', 'unit', 'category', 'food_type', 'people_fed'])
        for _ in range(n_rows):
            writer.writerow(make_row())
    print(f'Wrote {n_rows} rows to donations_dataset.csv')


if __name__ == '__main__':
    main()
