# Extension Icons

The PNG icons in this folder are **generated** — don't hand-edit them.

To regenerate (e.g. after a brand color change):

```bash
python scripts/generate_icons.py
```

Source: [`scripts/generate_icons.py`](../../scripts/generate_icons.py)

Requires Pillow (`pip install Pillow`). Outputs:

- `icon16.png` — toolbar
- `icon48.png` — extensions page
- `icon128.png` — Chrome Web Store listing
