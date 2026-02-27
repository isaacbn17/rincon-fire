# Remove all snow columnns in train and test sets

import pandas as pd
train_df = pd.read_csv("train_set_unbalanced.csv")
test_df = pd.read_csv("test_set_unbalanced.csv")

snow_cols = [col for col in train_df.columns if col.startswith("snow")]
train_df = train_df.drop(columns=snow_cols)
test_df = test_df.drop(columns=snow_cols)
# Save the modified datasets
train_df.to_csv("train_set_unbalanced_no_snow.csv", index=False)
test_df.to_csv("test_set_unbalanced_no_snow.csv", index=False)
