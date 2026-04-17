import csv

def parse_input_csv(input_file: str) -> list:
    """
    Parses a reverse transformation CSV mapping file.

    Args:
        input_file: Path to a CSV formatted per mapping template.
            (See rest of docstring for more detail on CSV format.)

    Returns:
        List of tuples of the form:
        [(path, input_files_field), (path, input_files_field), ...]

        Does not include rows for which input_files_field column is blank.

    Raises:
        ValueError: If required CSV column headers are not present in first row.

    Note:
        - This function assumes a irrelevant second row ("filter" row) which is skipped. If that
        row contains mapping data, it will not be parsed nor present in output. Ensure a second CSV
        row is present which does not contain mapping data.
    """
    with open(input_file, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)

        #skip filter row
        next(reader)

        reqd_headers = {'path', 'input_files_field'}
        if not reqd_headers.issubset(reader.fieldnames):
            raise ValueError(f"CSV format incorrect. Required headers {reqd_headers}, "
                             f"but got {reader.fieldnames} in file {input_file}")

        output = []

        for row in reader:
            if not row['input_files_field']:
                continue
            output.append( (row['path'], row['input_files_field']) )

    return output
