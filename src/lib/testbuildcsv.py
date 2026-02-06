from buildcsv import *

paths = [
    ("user.name", "Name"),
    ("user.age", "Age"),
    ("address.city", "City"), 
    ("admin", "Administrators"),
    ("privileged", "PrivilegedUsers")
]

data = [
    {"user": {"name": "Alice", "age": [30,35]}, "address": {"city": "NYC"}},
    {"user": {"name": "Bob", "age": 25}, "address": {"city": "LA"}},
    {"admin": ["John", "Bob", "Foo"], "privileged": ["Foo", "Bar"]},
    
]

def main():
    reverseTransform(data,paths,"test.csv")

main()