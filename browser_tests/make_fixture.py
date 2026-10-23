"""Generate the documented workbook without using application calculation code."""
from pathlib import Path
from openpyxl import Workbook

path = Path(__file__).parent / "fixtures/two_sheets.xlsx"
path.parent.mkdir(exist_ok=True)
book = Workbook()
first = book.active
first.title = "First"
first.append(["Product", "Sales"])
for row in [("Apple", 4), ("Banana", 8), ("Apple", 12), ("Banana", 16)]:
    first.append(row)
second = book.create_sheet("Second")
second.append(["Product", "Sales"])
for row in [("Apple", 5), ("Banana", 15), ("Apple", 25), ("Banana", 25), ("Apple", 35), ("Banana", 45)]:
    second.append(row)
book.save(path)
