import msilib
db = msilib.OpenDatabase(r'D:\sb\MsiBuilder\test_build\test_ui.msi', msilib.MSIDBOPEN_READONLY)
view = db.OpenView("SELECT Property, Value FROM Property WHERE Property IN ('ProductName', 'Manufacturer', 'ProductLanguage', 'ProductVersion')")
view.Execute(None)
while True:
    rec = view.Fetch()
    if rec is None:
        break
    print(rec.GetString(1), '=', rec.GetString(2))
view.Close()
db.Close()
