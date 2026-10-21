"""Pobiera surowe dane z Odoo do katalogu cache/ (uruchom raz, potem run.py korzysta z cache)."""
import sys

import odoo_extract

if __name__ == "__main__":
    data = odoo_extract.load_all(refresh="--refresh" in sys.argv)
    for k, v in data.items():
        print(k, len(v))
