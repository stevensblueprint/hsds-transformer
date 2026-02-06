import csv
import os 

def __get_nested_value(data, path):
    '''Retrieves nested dictionary values, i.e get_nested_value(data,user.name) will retrieve name key from user key in data dictionary, with nested values 
    separated by . symbol, otherwise will return highest dictionary key at specified path.'''
    keys = path.split('.')
    value = data
    for key in keys:
        value = value[key]
    if isinstance(value, list):
        return tuple(value)
    else:
        return (value,)

def reverseTransform(dictList, pathsTuple, csvPath):
    '''Searches over list of dictionaries, accepts list of tuples with path and csv field
    Will write each dictionary to row with the paths specified in the paths tuple and their corresponding mappings in csv file.'''
    with open(csvPath, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        fields = []
        for field in pathsTuple:
            fields.append(field[1])
        writer.writerow(fields)

        for dict in dictList: 
            dataFields = []
            for field in pathsTuple:
                try:
                    entry = __get_nested_value(dict, field[0])
                    if len(entry) == 1:
                        dataFields.append(entry[0])
                    else:
                        dataFields.append((",".join(map(str,entry))) if entry else "") 
                except KeyError:
                    dataFields.append("")

            writer.writerow(dataFields)



    
