# Stock Photo Pipeline

Daily automated pipeline: generate AI stock photos → upscale → embed metadata → upload to Adobe Stock.

**Stack:** gpt-image-2 · Real-ESRGAN (Replicate) · exiftool · paramiko · GitHub Actions

---

## Architecture

```
run_daily.py
    └── pipeline.py
          ├── prompt_generator.py   — weighted niche rotation + GPT-4o prompt expansion
          ├── image_generator.py    — gpt-image-2 medium 1536×1024 (tenacity retry)
          ├── qc_checker.py         — resolution / filesize / color mode checks
          ├── upscaler.py           — Real-ESRGAN x2 via Replicate → 3072×2048
          ├── metadata_writer.py    — exiftool IPTC 2025.1 + Adobe Stock required fields
          ├── adobe_stock_uploader.py — paramiko SFTP → sftp.contributor.adobestock.com
          └── report.py             — daily summary + cost log
```

## Output Structure

```
output/YYYY-MM-DD/
├── generated/   # raw PNG 1536×1024
├── upscaled/    # 3072×2048 JPEG from Real-ESRGAN
├── ready/       # metadata-tagged, SFTP-uploaded
└── rejected/    # failed QC
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install exiftool

- **Ubuntu/GitHub Actions:** `sudo apt-get install -y libimage-exiftool-perl`
- **Windows (local):** download from [exiftool.org](https://exiftool.org), rename to `exiftool.exe`, add to PATH

### 3. Configure environment

```bash
cp .env.example .env
# edit .env with real credentials
```

```env
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
ADOBE_STOCK_SFTP_USER=...
ADOBE_STOCK_SFTP_PASS=...
```

### 4. Edit config

`config/settings.yaml`:
```yaml
daily_quota: 3
contributor_name: "Your Name"
```

### 5. Run locally

```bash
python run_daily.py
```

---

## GitHub Actions

Cron: **08:00 ICT daily** (`0 1 * * *`)

Required secrets (Settings → Secrets → Actions):

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` | OpenAI API key |
| `REPLICATE_API_TOKEN` | Replicate API token |
| `ADOBE_STOCK_SFTP_USER` | Adobe Stock contributor SFTP username |
| `ADOBE_STOCK_SFTP_PASS` | Adobe Stock contributor SFTP password |

Manual trigger: Actions → Daily Stock Photo Pipeline → Run workflow

---

## Adobe Stock SFTP Credentials

1. Apply at [contributor.stock.adobe.com](https://contributor.stock.adobe.com)
2. Wait for account approval (~1-3 days)
3. Go to **Upload** → scroll down → **"You can also import files using SFTP"** → **Learn More**
4. Generate password from contributor portal

> SFTP access unlocks after first images are approved. Use web UI upload initially.

---

## Niches (config/niches.yaml)

| Niche | Weight | Notes |
|-------|--------|-------|
| Authentic Cultural Scenes | 0.35 | Thai festivals, local food — no faces |
| Technical/Industrial Trades | 0.30 | Machinery, tools, equipment |
| Sustainable Sophistication | 0.20 | Eco-luxury, solar, clean materials |
| Retrofuturism | 0.15 | 80s/90s neon, holographic objects |

Cooldown: 3 days per niche — prevents "similar content" rejection

---

## Cost Estimate (3 images/day)

| Item | Cost/day | Cost/month |
|------|----------|------------|
| gpt-image-2 medium | $0.123 | $3.69 |
| Real-ESRGAN (Replicate) | $0.009 | $0.27 |
| GPT-4o metadata | ~$0.02 | $0.60 |
| **Total** | **~$0.15** | **~$4.56** |

Break-even: ~14 downloads/month at 33% Adobe Stock royalty

---

## Legal Compliance

- AI disclosure: `XMP-iptcExt:DigitalSourceType=trainedAlgorithmicMedia` (Adobe Stock required)
- People fictional: `XMP-plus:ModelStatus=NotAModel`
- AI system declared: `XMP-iptcExt:AISystemUsed=OpenAI gpt-image-2`
- Prompt logged: `XMP-iptcExt:AIPromptInformation`
- No real faces in prompts — all niche templates specify objects/scenes only
