"""
ตัวช่วย export ไฟล์ — CSV (เปิดใน Excel ได้ ภาษาไทยไม่เพี้ยน ด้วย BOM)
ใช้ร่วมกันทุกหน้า report
"""
import csv

from django.http import HttpResponse


def csv_response(filename, header, rows):
    """
    คืน HttpResponse เป็นไฟล์ CSV ดาวน์โหลด
    - filename: ชื่อไฟล์ (ไม่ต้องมี .csv)
    - header: list หัวคอลัมน์
    - rows: iterable ของ list/tuple แต่ละแถว
    """
    resp = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    resp['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    resp.write('﻿')  # BOM เพื่อให้ Excel อ่านไทยถูก
    writer = csv.writer(resp)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return resp
