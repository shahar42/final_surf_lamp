# Surf Lamp Manufacturing System

Complete Arduino ID management and QR code generation system for Surf Lamp production.

## Features

✅ **Automatic ID Allocation** - Query database for next available Arduino ID
✅ **QR Code Generation** - Single, batch, and print-ready sheets
✅ **Web Dashboard** - Beautiful UI for manufacturing team
✅ **Database Integration** - Real-time sync with production database
✅ **Print-Ready Output** - Generate sheets with multiple QR codes for printing

## Quick Start

### 1. Install Dependencies

```bash
cd manufacturing
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file (or use parent directory's `.env`):

```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### 3. Run the Dashboard

```bash
python manufacturing_app.py
```

Visit: **http://localhost:5001**

## Usage

### Web Dashboard

The dashboard provides:

1. **Statistics Dashboard**
   - Next available Arduino ID
   - Total IDs used
   - Highest ID assigned

2. **Generate Single QR Code**
   - Enter Arduino ID
   - Generate and download QR code
   - Preview before downloading

3. **Generate Batch QR Codes**
   - Specify ID range (e.g., 1-100)
   - Generates individual files for each ID
   - Saves to `static/qr_codes/`

4. **Generate Print Sheet**
   - Create print-ready sheet with multiple QR codes
   - Customize columns (e.g., 3x3 grid)
   - Download for printing on card stock

### Python API

#### ID Manager

```python
from id_manager import IDManager

manager = IDManager()

# Get next available ID
next_id = manager.get_next_available_id()
print(f"Next ID: {next_id}")

# Check if ID is available
is_free = manager.is_id_available(42)
print(f"ID 42 available: {is_free}")

# Get statistics
stats = manager.get_id_statistics()
print(stats)
```

#### QR Generator

```python
from qr_generator import QRGenerator

generator = QRGenerator()

# Generate single QR code
path = generator.generate_qr_code(arduino_id=1)
print(f"Saved to: {path}")

# Generate batch
paths = generator.generate_batch(start_id=1, end_id=10)
print(f"Generated {len(paths)} QR codes")

# Generate print sheet
sheet_path = generator.generate_print_sheet([1, 2, 3, 4, 5, 6], cols=3)
print(f"Print sheet: {sheet_path}")
```

## QR Code Format

Generated QR codes link to:

```
https://final-surf-lamp-web.onrender.com/register?id=ARDUINO_ID
```

When users scan the QR code:
1. Registration page opens
2. Arduino ID field is pre-filled
3. User enters name, email, password
4. Submits → Lamp registered!

## File Structure

```
manufacturing/
├── id_manager.py          # Arduino ID allocation logic
├── qr_generator.py        # QR code generation
├── manufacturing_app.py   # Flask web application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── dashboard.html    # Web UI
└── static/
    └── qr_codes/        # Generated QR codes (auto-created)
```

## Production Workflow

### Manufacturing a New Lamp (MAC-derived IDs)

The Arduino ID is no longer chosen by the programmer. New firmware derives a
unique 24-bit ID from the ESP32's factory eFuse MAC at boot, so every lamp is
flashed with the **same** firmware image and no Config.h edit is needed.

1. **Flash Firmware** → universal image, no per-lamp edits
2. **Read the ID** → with the lamp still on USB:
   ```bash
   python read_lamp_id.py          # reads serial boot log + generates QR
   ```
   (or open a serial monitor and read the `Arduino ID: <N> (decimal)` line)
3. **Print QR Code** → the script saves it to `static/qr_codes/`
4. **Package Lamp** → include card with lamp; the card MUST stay paired with
   the physical lamp it was read from
5. **Ship to Customer** → customer scans QR to register

### Legacy: Sequential ID Allocation

The dashboard's "next available ID" allocator and batch QR generation apply
only to old-style firmware with hardcoded IDs (`const int ARDUINO_ID = N;`).
Do not use sequential allocation for lamps running MAC-derived firmware —
the ID must come from the device itself.

## API Endpoints

### GET `/`
Manufacturing dashboard (HTML)

### GET `/api/next-id`
```json
{"success": true, "next_id": 15}
```

### GET `/api/check-id/<id>`
```json
{"success": true, "arduino_id": 42, "available": true}
```

### POST `/api/generate-qr`
```json
Request: {"arduino_id": 15}
Response: {
  "success": true,
  "arduino_id": 15,
  "qr_code_path": "/static/qr_codes/arduino_15.png",
  "download_url": "/download-qr/15"
}
```

### POST `/api/generate-batch`
```json
Request: {"start_id": 1, "end_id": 10}
Response: {"success": true, "count": 10, "start_id": 1, "end_id": 10}
```

### POST `/api/generate-print-sheet`
```json
Request: {"start_id": 1, "end_id": 9, "cols": 3}
Response: {
  "success": true,
  "print_sheet_path": "/static/qr_codes/print_sheet_1-9.png",
  "count": 9
}
```

### GET `/download-qr/<id>`
Downloads QR code PNG file

### GET `/api/stats`
```json
{
  "success": true,
  "stats": {
    "total_ids_used": 14,
    "highest_id": 14,
    "next_available_id": 15,
    "gaps_exist": false
  }
}
```

## Customization

### Change Base URL

Edit `qr_generator.py`:

```python
generator = QRGenerator(base_url="https://your-custom-domain.com")
```

### Customize QR Code Size

```python
generator.generate_qr_code(arduino_id=1, size=400)  # Larger QR code
```

### Custom Print Sheet Layout

```python
generator.generate_print_sheet(
    arduino_ids=[1, 2, 3, 4, 5, 6],
    cols=2,           # 2 columns
    card_size=350     # Larger cards
)
```

## Troubleshooting

### "DATABASE_URL not set"
- Make sure `.env` file exists with `DATABASE_URL` variable
- Or set environment variable: `export DATABASE_URL=postgresql://...`

### QR codes not displaying
- Check `static/qr_codes/` directory exists
- Verify file permissions allow writing
- Check Flask static files configuration

### Font errors on QR labels
- Install DejaVu fonts: `sudo apt-get install fonts-dejavu`
- Or system will fall back to default font

## Security Notes

- 🔒 Dashboard has no authentication (run locally only)
- 🔒 Do not expose port 5001 to internet
- 🔒 Use for internal manufacturing team only
- 🔒 Production deployment should add authentication

## Future Enhancements

- [ ] Authentication for dashboard
- [ ] Manufacturing log table in database
- [ ] Export to CSV (ID, date, status)
- [ ] Barcode support in addition to QR codes
- [ ] Integration with inventory management
- [ ] Mobile app for scanning during production

## Support

For issues or questions, contact the development team.
