const XLSX = require('xlsx');

const wb = XLSX.utils.book_new();

const ws1 = XLSX.utils.aoa_to_sheet([["A"]]);
ws1['!sheet_color'] = "FF0000";
ws1['!color'] = { rgb: "FF0000" };
wb.SheetNames.push("Red Tab");
wb.Sheets["Red Tab"] = ws1;

// Another common SheetJS trick
const ws2 = XLSX.utils.aoa_to_sheet([["B"]]);
wb.SheetNames.push("Green Tab");
wb.Sheets["Green Tab"] = ws2;
if (!wb.Workbook) wb.Workbook = { Views: [{}] }
if (!wb.Workbook.Views) wb.Workbook.Views = [{}]
// The community edition of SheetJS (xlsx) often DROPS tab colors in writing.
// However, setting the workbook properties might work:
if (!wb.Workbook.Sheets) wb.Workbook.Sheets = [];
wb.Workbook.Sheets[1] = { Hidden: 0, tabColor: { rgb: "00FF00" } };

XLSX.writeFile(wb, "test_color.xlsx");
