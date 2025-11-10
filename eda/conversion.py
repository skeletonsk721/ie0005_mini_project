import pandas as pd

# 将分号分隔的csv转换成excel表

def convert_csv_to_excel(input_csv, output_excel):
    try:
        # Read the semicolon-separated CSV file
        df = pd.read_csv(input_csv, sep=';')
        
        # Write the DataFrame to an Excel file
        df.to_excel(output_excel, index=False)
        print(f"Conversion successful: {output_excel}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
input_csv = 'eda/cardio_train.csv'
output_excel = 'output_file.xlsx'
convert_csv_to_excel(input_csv, output_excel)