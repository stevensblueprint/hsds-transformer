import csv
from .reverse_transform import get_path_value


def reverseTransform(dictList, pathsTuple, csvPath):
    '''Searches over list of dictionaries, accepts list of tuples with path and csv field.
    Will write each dictionary to a row with the paths specified in the paths tuple and their
    corresponding mappings in the csv file.'''
    with open(csvPath, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        fields = [field[1] for field in pathsTuple]
        writer.writerow(fields)

        for element in dictList:
            dataFields = []
            for field in pathsTuple:
                try:
                    entry = get_path_value(element, field[0])
                    if len(entry) == 1:
                        dataFields.append(entry[0])
                    else:
                        dataFields.append((",".join(map(str, entry))) if entry else "")
                except (KeyError, ValueError):
                    dataFields.append("")

            writer.writerow(dataFields)
