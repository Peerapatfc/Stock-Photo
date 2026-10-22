# Market research — Adobe Stock (วัดเมื่อ 22 ต.ค. 2026)

เอกสารนี้คือข้อมูล **ที่วัดจริงจากหน้าค้นหาสาธารณะของ Adobe Stock** (ไม่ใช่ภาพรวมทั่วไปแบบ `research_th.md`) ใช้ตัดสินใจว่าควรผลิตรูปหัวข้อไหนและเขียน metadata อย่างไร

## วิธีวัด

ค้นหาเฉพาะ "ภาพถ่าย" ต่อหนึ่งคำค้น แล้วอ่านจำนวนผลลัพธ์ 3 แบบ

| ตัวเลข | ตัวกรองใน URL | ความหมาย |
|---|---|---|
| `human` | `filters[gentech]=exclude` | ภาพที่ไม่ใช่ AI ทั้งหมด |
| `ai` | `filters[gentech]=only` | ภาพ AI ทั้งหมด (คู่แข่งตรงของเรา) |
| `human_undisc` | `filters[gentech]=exclude` + `filters[undiscovered]=only` | ภาพที่ไม่ใช่ AI และ Adobe จัดว่า "ยังไม่มีการค้นพบ" |

ตัวชี้วัดที่คำนวณ (ใช้ใน `src/market_insights.py`)

- `sell_through = 1 − human_undisc / human` ยิ่งสูง = ภาพหัวข้อนี้ถูกซื้อ/ถูกใช้มากกว่า (ตัวแทนความต้องการ)
- `ai_share = ai / (ai + human)` ยิ่งสูง = ยิ่งแออัดด้วยภาพ AI
- `opportunity = sell_through × (1 − ai_share)`

> ข้อจำกัดสำคัญ: Adobe ไม่เปิดเผยยอดดาวน์โหลดหรือยอดค้นหา `sell_through` เป็น **ตัวแทน** ที่อิงตัวกรอง "undiscovered" ซึ่ง Adobe ไม่นิยามไว้ชัดเจน คำค้นกำกวม (เช่น "press brake" ซึ่งติดภาพเบรกรถ) ให้ค่าไม่น่าเชื่อถือและไม่ถูกนำมาใช้ ใช้เป็นทิศทาง ไม่ใช่ตัวเลขทางบัญชี

## ผลการวัด

| Niche | คำค้น | human | ai | ai_share | human_undisc | sell_through | opportunity |
|---|---|---:|---:|---:|---:|---:|---:|
| Technical/Industrial | hydraulic press | 4,557 | 2,643 | 37% | 2,381 | 48% | **0.30** |
| Technical/Industrial | hydraulic cylinder | 8,023 | 3,845 | 32% | 4,713 | 41% | **0.28** |
| Retrofuturism | vintage synthesizer | 2,788 | 2,249 | 45% | 1,806 | 35% | 0.20 |
| Scientific Research | centrifuge laboratory | 6,054 | 5,320 | 47% | 3,575 | 41% | 0.22 |
| Authentic Cultural | thai silk fabric | 19,731 | 4,595 | 19% | 15,659 | 21% | 0.17 |
| Scientific Research | laboratory glassware | 148,073 | 177,172 | 54% | 109,174 | 26% | 0.12 |
| Abstract Color Texture | linen texture | 307,972 | 428,810 | 58% | 232,373 | 25% | 0.10 |
| Authentic Cultural | thai street food | 87,044 | 33,167 | 28% | 75,160 | 14% | 0.10 |
| Sustainable Sophistication | zero waste kitchen | 30,322 | 51,675 | 63% | 22,798 | 25% | 0.09 |
| Authentic Cultural | bamboo steamer | 25,399 | 35,355 | 58% | 20,062 | 21% | 0.09 |
| Scientific Research | scanning electron microscope | 1,614 | 3,165 | 66% | 1,245 | 23% | 0.08 |

## สิ่งที่อ่านได้

1. **อุตสาหกรรม/เครื่องจักรเฉพาะทาง คุ้มที่สุด** ภาพหัวข้อ "hydraulic press/cylinder" มีคู่แข่งน้อย (หลักพัน) แต่ภาพที่ถูกใช้แล้วสูงถึง 41–48% และ AI มีสัดส่วนน้อยกว่าหัวข้อทั่วไป ตรงกับสมมติฐานใน `research_th.md` ว่านี่คือ AI-resistant niche
2. **หัวข้อทั่วไปแออัดและขายยาก** linen texture (7 แสนรูป), laboratory glassware, zero waste kitchen มีภาพ AI มากกว่าภาพถ่ายจริง และภาพจริงกว่า 3 ใน 4 ยังไม่เคยถูกใช้
3. **อาหารไทยขายยากที่สุดในตัวอย่าง** thai street food มีภาพจริง 87k รูปและ 86% ยังไม่ถูกใช้ ขณะที่ thai silk fabric ที่เป็นของเฉพาะกว่าอยู่ในระดับดีกว่า (0.17) ควรเน้นวัตถุ/งานฝีมือเฉพาะ ไม่ใช่อาหารทั่วไป
4. **Retrofuturism ได้คะแนนดี (0.20) แต่ภาพของเราเสี่ยง** Adobe เคยปฏิเสธ retro cityscape ด้วยเหตุ IP และภาพ retro ผ่าน QC เมื่อผ่อน contrast เท่านั้น จึงต้องคุมน้ำหนักไว้ ไม่ปล่อยให้สูงเกินไป
5. **ภาพที่ติดอันดับต้นๆ ของ "hydraulic press" (ไม่ใช่ AI)** ส่วนมากมีคนทำงานหรือมือในภาพ ("engineer inspecting", "worker installing") ซึ่งเรางดไว้เพื่อลดความเสี่ยงเรื่องใบหน้า/model release ข้อนี้คือ trade-off ที่ต้องรู้ ไม่ได้ตัดสินแทน
6. **แนวทาง metadata ของ Adobe** (helpx: Tips for effective titles and keywords) title สั้น ควรไม่เกินประมาณ 70 ตัวอักษร เน้นสิ่งที่เห็นเด่นสุด และ keyword 10 คำแรกมีน้ำหนักสูงสุดในการจัดอันดับ ปัจจุบันเราสร้าง title ได้ถึง 200 ตัวอักษร จึงปรับลดแล้ว
7. **Adobe Creative Trends 2026** ("All the Feels", "Connectioneering", "Surreal Silliness", "Local Flavor") ตัวที่เกี่ยวกับเรามากที่สุดคือ *Local Flavor* (วัฒนธรรมเฉพาะถิ่นที่ดูจริง) และพื้นผิวสัมผัส (น้ำ ผ้า คริสตัล) ใน *All the Feels*

## ที่ยังไม่รู้ (อย่าตีความเกินจริง)

- ไม่มียอดค้นหาจริง จึงแยก "คนค้นหาน้อย" ออกจาก "ไม่มีใครผลิต" ไม่ได้ ภาพจำนวนน้อยอาจแปลว่าโอกาสหรือไม่มีความต้องการก็ได้
- ภาพ AI เพิ่งอัปโหลดใหม่เป็นส่วนมาก ภาพใหม่ย่อมมีโอกาสถูกซื้อน้อยกว่า จึงใช้เฉพาะภาพ **ไม่ใช่ AI** ในการคำนวณ `sell_through`
- บัญชีเรายังไม่มีรูปขายได้ (Insights: no sales) จึงยังไม่มีข้อมูลจริงของเราเองมาเทียบ ให้ตรวจ Insights หลังมีรูปผ่านการอนุมัติ

## ทำอย่างไรต่อ

- น้ำหนัก niche ปรับอัตโนมัติจาก `data/market_insights.json` (ดู `market_insights.py`) และอัปเดตด้วย scheduled task รายสัปดาห์
- เน้น subject เครื่องจักร/ชิ้นส่วนเฉพาะทาง และงานฝีมือเฉพาะถิ่น หลีกเลี่ยงอาหาร/พื้นผิวทั่วไป
- ตรวจ Insights ของ Adobe ทุกสัปดาห์เพื่อเทียบว่า niche ไหนมียอดจริง แล้วปรับ `weight` ใน `config/niches.yaml`
