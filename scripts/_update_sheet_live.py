import sys
sys.path.insert(0, "/opt/data/web-blog-astro/scripts")
from sheet_helper import service

SID = "1JWgph214tsk9HFAeRyG5uhGicxU18RBGQ7O7nVN6CkY"
svc = service()

# Artikel "Berapa Lama Sayuran Bisa Disimpan di Kulkas?" ada di data index 9 -> sheet row 10
row = 10
updates = {
    f"Content Plan Living!G{row}": "LIVE",
    f"Content Plan Living!H{row}": "2026-08-14",
    f"Content Plan Living!M{row}": "cover-berapa-lama-sayuran-bisa-disimpan-di-kulkas.jpg",
    f"Content Plan Living!P{row}": "Yes",
}
for rng, val in updates.items():
    res = svc.spreadsheets().values().update(
        spreadsheetId=SID,
        range=rng,
        valueInputOption="RAW",
        body={"values": [[val]]},
    ).execute()
    print(rng, "->", val, "updated cells:", res.get("updatedCells"))
