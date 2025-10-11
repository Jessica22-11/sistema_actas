from django.core.management.base import BaseCommand
from django.conf import settings
import os
import zipfile
from datetime import datetime


class Command(BaseCommand):
    help = "Genera una copia de seguridad de la base de datos SQLite"

    def handle(self, *args, **options):
        db_path = settings.DATABASES["default"]["NAME"]
        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        # Nombre del archivo del respaldo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.zip")

        # Crear archivo ZIP con la base de datos
        with zipfile.ZipFile(backup_file, "w") as backup_zip:
            backup_zip.write(db_path, os.path.basename(db_path))

        self.stdout.write(self.style.SUCCESS(f"✅ Backup generado en: {backup_file}"))
