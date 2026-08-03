
import pandas as pd

def save_variable_to_csv(data,cols ,filepath, index=False):
    """Save the given variable to a CSV file using pandas.

    - If data is a pandas DataFrame, it is saved directly.
    - If data is a dict or list of dicts, it is converted to a DataFrame.
    - Otherwise the data is wrapped into a single-row DataFrame under column 'value'.
    """
    try:

        df = pd.DataFrame(data,columns=cols)
        df.to_csv(filepath, index=index, encoding='utf-8')

        print(f"Data saved to {filepath}")
    except Exception as ex:
        print(f"Error saving data to CSV: {ex}")
