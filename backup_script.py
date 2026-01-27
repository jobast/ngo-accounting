#!/usr/bin/env python3
"""
CREATES - Script de sauvegarde automatique
==========================================

Ce script effectue des sauvegardes automatiques de la base de données.
Il peut être exécuté via cron pour des sauvegardes planifiées.

Usage:
    python backup_script.py [--type daily|weekly|manual] [--cleanup]

Exemples cron:
    # Sauvegarde quotidienne à 2h du matin
    0 2 * * * cd /path/to/ngo-accounting && python backup_script.py --type daily --cleanup

    # Sauvegarde hebdomadaire le dimanche à 3h du matin
    0 3 * * 0 cd /path/to/ngo-accounting && python backup_script.py --type weekly

Configuration:
    Les sauvegardes sont stockées dans le dossier 'backups/' avec la structure:
    - backups/daily/   : Sauvegardes quotidiennes (7 derniers jours)
    - backups/weekly/  : Sauvegardes hebdomadaires (4 dernières semaines)
    - backups/manual/  : Sauvegardes manuelles (conservation illimitée)
"""

import os
import sys
import shutil
import argparse
from datetime import datetime, date
import glob

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, 'instance', 'ngo_accounting.db')
BACKUP_FOLDER = os.path.join(SCRIPT_DIR, 'backups')
BACKUP_DAILY_FOLDER = os.path.join(BACKUP_FOLDER, 'daily')
BACKUP_WEEKLY_FOLDER = os.path.join(BACKUP_FOLDER, 'weekly')
BACKUP_MANUAL_FOLDER = os.path.join(BACKUP_FOLDER, 'manual')

# Retention
DAILY_RETENTION = 7    # Nombre de jours à conserver
WEEKLY_RETENTION = 4   # Nombre de semaines à conserver


def setup_folders():
    """Créer les dossiers de backup s'ils n'existent pas"""
    for folder in [BACKUP_FOLDER, BACKUP_DAILY_FOLDER, BACKUP_WEEKLY_FOLDER, BACKUP_MANUAL_FOLDER]:
        os.makedirs(folder, exist_ok=True)


def get_db_path():
    """Trouver le chemin de la base de données"""
    # Essayer différents emplacements possibles
    possible_paths = [
        DB_PATH,
        os.path.join(SCRIPT_DIR, 'ngo_accounting.db'),
        os.path.join(SCRIPT_DIR, 'instance', 'creates.db'),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def create_backup(backup_type='daily'):
    """Créer une sauvegarde de la base de données"""
    db_path = get_db_path()

    if not db_path:
        print(f"ERREUR: Base de données non trouvée")
        print(f"Chemins recherchés: {DB_PATH}")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if backup_type == 'daily':
        backup_dir = BACKUP_DAILY_FOLDER
        filename = f"backup_{date.today().isoformat()}.db"
    elif backup_type == 'weekly':
        backup_dir = BACKUP_WEEKLY_FOLDER
        week_num = date.today().isocalendar()[1]
        year = date.today().year
        filename = f"backup_{year}_week_{week_num:02d}.db"
    else:  # manual
        backup_dir = BACKUP_MANUAL_FOLDER
        filename = f"backup_{timestamp}.db"

    backup_path = os.path.join(backup_dir, filename)

    try:
        # Copier la base de données
        shutil.copy2(db_path, backup_path)
        size = os.path.getsize(backup_path)
        size_mb = size / 1024 / 1024

        print(f"OK: Sauvegarde créée: {filename}")
        print(f"    Taille: {size_mb:.2f} Mo")
        print(f"    Chemin: {backup_path}")

        return backup_path
    except Exception as e:
        print(f"ERREUR: {str(e)}")
        return None


def cleanup_old_backups():
    """Nettoyer les anciennes sauvegardes selon la politique de rétention"""
    cleaned = 0

    # Nettoyer les backups quotidiens (garder DAILY_RETENTION jours)
    daily_backups = sorted(
        glob.glob(os.path.join(BACKUP_DAILY_FOLDER, '*.db')),
        key=os.path.getmtime,
        reverse=True
    )
    for old_backup in daily_backups[DAILY_RETENTION:]:
        os.remove(old_backup)
        print(f"Supprimé (daily): {os.path.basename(old_backup)}")
        cleaned += 1

    # Nettoyer les backups hebdomadaires (garder WEEKLY_RETENTION semaines)
    weekly_backups = sorted(
        glob.glob(os.path.join(BACKUP_WEEKLY_FOLDER, '*.db')),
        key=os.path.getmtime,
        reverse=True
    )
    for old_backup in weekly_backups[WEEKLY_RETENTION:]:
        os.remove(old_backup)
        print(f"Supprimé (weekly): {os.path.basename(old_backup)}")
        cleaned += 1

    if cleaned > 0:
        print(f"Nettoyage: {cleaned} ancienne(s) sauvegarde(s) supprimée(s)")
    else:
        print("Nettoyage: Aucune ancienne sauvegarde à supprimer")

    return cleaned


def list_backups():
    """Lister toutes les sauvegardes disponibles"""
    backups = []

    for backup_type, folder in [('manual', BACKUP_MANUAL_FOLDER),
                                 ('daily', BACKUP_DAILY_FOLDER),
                                 ('weekly', BACKUP_WEEKLY_FOLDER)]:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                if filename.endswith('.db'):
                    filepath = os.path.join(folder, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        'filename': filename,
                        'type': backup_type,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_mtime)
                    })

    # Trier par date décroissante
    backups.sort(key=lambda x: x['created'], reverse=True)
    return backups


def print_status():
    """Afficher le statut des sauvegardes"""
    print("\n" + "=" * 60)
    print("CREATES - Statut des sauvegardes")
    print("=" * 60)

    db_path = get_db_path()
    if db_path:
        db_size = os.path.getsize(db_path) / 1024 / 1024
        print(f"\nBase de données: {db_path}")
        print(f"Taille: {db_size:.2f} Mo")
    else:
        print("\nBase de données: NON TROUVÉE")

    backups = list_backups()

    print(f"\nSauvegardes disponibles: {len(backups)}")
    print("-" * 60)

    if backups:
        for b in backups[:10]:  # Afficher les 10 plus récentes
            size_mb = b['size'] / 1024 / 1024
            print(f"  [{b['type']:7}] {b['filename']:40} {size_mb:6.2f} Mo  {b['created'].strftime('%d/%m/%Y %H:%M')}")

        if len(backups) > 10:
            print(f"  ... et {len(backups) - 10} autres")
    else:
        print("  Aucune sauvegarde")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='CREATES - Script de sauvegarde automatique',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python backup_script.py --type daily --cleanup    Sauvegarde quotidienne + nettoyage
  python backup_script.py --type weekly             Sauvegarde hebdomadaire
  python backup_script.py --status                  Afficher le statut
  python backup_script.py --list                    Lister les sauvegardes
        """
    )

    parser.add_argument('--type', choices=['daily', 'weekly', 'manual'],
                        default='daily', help='Type de sauvegarde (défaut: daily)')
    parser.add_argument('--cleanup', action='store_true',
                        help='Nettoyer les anciennes sauvegardes')
    parser.add_argument('--status', action='store_true',
                        help='Afficher le statut des sauvegardes')
    parser.add_argument('--list', action='store_true',
                        help='Lister toutes les sauvegardes')

    args = parser.parse_args()

    # Créer les dossiers
    setup_folders()

    # Afficher le statut ou la liste
    if args.status or args.list:
        print_status()
        return 0

    # Créer la sauvegarde
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Début de la sauvegarde ({args.type})")

    backup_path = create_backup(args.type)

    if not backup_path:
        return 1

    # Nettoyage si demandé
    if args.cleanup:
        print("\nNettoyage des anciennes sauvegardes...")
        cleanup_old_backups()

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sauvegarde terminée\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
