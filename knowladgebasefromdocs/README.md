# knowladgebasefromdocs — Temur bilim bazasi (hujjatlar)

Bu papkaga bankning **normativ hujjatlarini** joylang — Temur AI epik va new
feature'lar bo'yicha savol/rekomendatsiya berganда shu hujjatlarga tayanadi
(muvofiqlikni tekshiradi va to'g'ri yo'lni ko'rsatadi).

## Nima joylash mumkin

- Bank strukturasi
- Loyihalarni boshqarish tartibi (Положение о порядке управления проектами)
- Proekt komiteti nizomi (Положение о проектном комитете)
- DPU / PMO departamenti nizomi
- Yangi mahsulotlar bo'yicha siyosat (Политика по новым продуктам)

## Qo'llab-quvvatlanadigan formatlar

PDF (matnли **va** skanер — OCR bilan o'qiladi), DOCX, XLSX, rasm (PNG/JPG),
TXT, MD, HTML. OCR tillari: rus, o'zbek (lotin + kirill), ingliz.

## Qanday ishlaydi

1. Faylni shu papkaga (yoki ichki papkalarga) tashlang.
2. Yangi ma'lumot yuklanganda indeks avtomatik qayta quriladi; yoki qo'lда:
   `python backend/scripts/build_rag.py`
   (yoki admin: `POST /api/temur/rebuild-rag`).
3. Matn bir marta OCR qilinadi va `storage/temp/docs_cache/`да keshlanadi —
   o'zgarmagan fayl qayta OCR qilinmaydi.

## Maxfiylik

Bu papkadagi hujjatlar **git'ga yuklanmaydi** (`.gitignore`da), faqat lokal
mashinada qoladi. Faqat shu `README.md` va `.gitkeep` kuzatiladi.
