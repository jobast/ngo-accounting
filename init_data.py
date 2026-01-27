"""
Script d'initialisation avec les données CREATES
Projets LED et SOR4D basés sur vos budgets réels
"""

from app import app, db, Bailleur, Projet, CategorieBudget, LigneBudget, Devise
from datetime import date

def init_creates_data():
    """Initialiser les données CREATES"""
    with app.app_context():
        # Vérifier si déjà initialisé
        if Bailleur.query.first():
            print("Données déjà présentes")
            return

        # Récupérer les devises
        usd = Devise.query.filter_by(code='USD').first()
        chf = Devise.query.filter_by(code='CHF').first()
        xof = Devise.query.filter_by(code='XOF').first()

        # Récupérer les catégories
        cat_labor = CategorieBudget.query.filter_by(code='LABOR').first()
        cat_travel = CategorieBudget.query.filter_by(code='TRAVEL').first()
        cat_supplies = CategorieBudget.query.filter_by(code='SUPPLIES').first()
        cat_program = CategorieBudget.query.filter_by(code='PROGRAM').first()
        cat_admin = CategorieBudget.query.filter_by(code='ADMIN').first()
        cat_overhead = CategorieBudget.query.filter_by(code='OVERHEAD').first()
        cat_audit = CategorieBudget.query.filter_by(code='AUDIT').first()

        # =================================================================
        # BAILLEURS
        # =================================================================
        print("Création des bailleurs...")

        nitidae = Bailleur(
            code='NITIDAE',
            nom='Nitidae',
            pays='France',
            email='contact@nitidae.org',
            devise_id=usd.id if usd else None
        )
        db.session.add(nitidae)

        giub = Bailleur(
            code='GIUB',
            nom='Université de Berne (GIUB)',
            pays='Suisse',
            email='contact@giub.unibe.ch',
            devise_id=chf.id if chf else None
        )
        db.session.add(giub)

        db.session.flush()

        # =================================================================
        # PROJET LED
        # =================================================================
        print("Création du projet LED...")

        led = Projet(
            code='LED',
            nom='LED Bey Diiwaan - Local Economic Development',
            description='Projet de développement économique local en Casamance avec Nitidae',
            bailleur_id=nitidae.id,
            date_debut=date(2024, 1, 1),
            date_fin=date(2026, 12, 31),
            budget_total=540000000,  # ~900,000 USD en XOF
            devise_id=usd.id if usd else None,
            statut='actif'
        )
        db.session.add(led)
        db.session.flush()

        # Lignes budgétaires LED (basées sur votre fichier)
        lignes_led = [
            # LABOR
            {'cat': cat_labor, 'code': 'L1', 'intitule': 'Director - Science (CREATES)', 'qte': 4, 'unite': 'month', 'pu': 6500, 'annee': 2024},
            {'cat': cat_labor, 'code': 'L2', 'intitule': 'Director - Development (CREATES)', 'qte': 4, 'unite': 'month', 'pu': 6500, 'annee': 2024},
            {'cat': cat_labor, 'code': 'L3', 'intitule': 'Finance and Administration Manager', 'qte': 25.2, 'unite': 'month', 'pu': 1100, 'annee': None},
            {'cat': cat_labor, 'code': 'L4', 'intitule': 'Communication and M&E specialist', 'qte': 23.8, 'unite': 'month', 'pu': 1100, 'annee': None},
            {'cat': cat_labor, 'code': 'L5', 'intitule': 'DyTAES Coordinator (Bi, Mb, Fk)', 'qte': 34, 'unite': 'month', 'pu': 1000, 'annee': None},
            {'cat': cat_labor, 'code': 'L6', 'intitule': 'Market and value chain Officer', 'qte': 34, 'unite': 'month', 'pu': 1000, 'annee': None},
            {'cat': cat_labor, 'code': 'L7', 'intitule': 'Guard', 'qte': 34, 'unite': 'month', 'pu': 120, 'annee': None},

            # TRAVEL
            {'cat': cat_travel, 'code': 'T1', 'intitule': 'International Travel', 'qte': 5, 'unite': 'flight', 'pu': 700, 'annee': None},
            {'cat': cat_travel, 'code': 'T2', 'intitule': 'Local Travel', 'qte': 17600, 'unite': 'km', 'pu': 1, 'annee': None},

            # SUPPLIES
            {'cat': cat_supplies, 'code': 'S1', 'intitule': 'Laptops', 'qte': 4, 'unite': 'unit', 'pu': 800, 'annee': 2024},
            {'cat': cat_supplies, 'code': 'S2', 'intitule': 'Office equipment', 'qte': 1, 'unite': 'lump', 'pu': 2000, 'annee': 2024},
            {'cat': cat_supplies, 'code': 'S3', 'intitule': 'Vehicle maintenance', 'qte': 36, 'unite': 'month', 'pu': 200, 'annee': None},

            # PROGRAM
            {'cat': cat_program, 'code': 'P1', 'intitule': 'Baseline survey', 'qte': 1, 'unite': 'study', 'pu': 10000, 'annee': 2024},
            {'cat': cat_program, 'code': 'P2', 'intitule': 'Output 1.1: Capacity building', 'qte': 1, 'unite': 'lump', 'pu': 25000, 'annee': None},
            {'cat': cat_program, 'code': 'P3', 'intitule': 'Output 2.1: Agroecological practices', 'qte': 1, 'unite': 'lump', 'pu': 52000, 'annee': None},
            {'cat': cat_program, 'code': 'P4', 'intitule': 'Output 2.2: Seed production', 'qte': 1, 'unite': 'lump', 'pu': 47950, 'annee': None},
            {'cat': cat_program, 'code': 'P5', 'intitule': 'Output 2.3: Documentation and dissemination', 'qte': 1, 'unite': 'lump', 'pu': 13000, 'annee': None},
            {'cat': cat_program, 'code': 'P6', 'intitule': 'Output 3.1: Alternative food networks', 'qte': 1, 'unite': 'lump', 'pu': 19400, 'annee': None},
            {'cat': cat_program, 'code': 'P7', 'intitule': 'Output 3.2: Non-Timber Forest Product', 'qte': 1, 'unite': 'lump', 'pu': 26500, 'annee': None},
            {'cat': cat_program, 'code': 'P8', 'intitule': 'Video productions', 'qte': 2, 'unite': 'video', 'pu': 5000, 'annee': None},

            # ADMIN / OVERHEAD
            {'cat': cat_admin, 'code': 'A1', 'intitule': 'Office rent', 'qte': 36, 'unite': 'month', 'pu': 350, 'annee': None},
            {'cat': cat_admin, 'code': 'A2', 'intitule': 'Utilities', 'qte': 36, 'unite': 'month', 'pu': 200, 'annee': None},
            {'cat': cat_admin, 'code': 'A3', 'intitule': 'Miscellaneous costs (3%)', 'qte': 1, 'unite': 'lump', 'pu': 26002, 'annee': None},
            {'cat': cat_overhead, 'code': 'O1', 'intitule': 'Other Indirect Costs (10%)', 'qte': 1, 'unite': 'lump', 'pu': 81818, 'annee': None},

            # AUDIT
            {'cat': cat_audit, 'code': 'AU1', 'intitule': 'Audit annuel', 'qte': 3, 'unite': 'audit', 'pu': 5500, 'annee': None},
            {'cat': cat_audit, 'code': 'AU2', 'intitule': 'Evaluation finale', 'qte': 1, 'unite': 'evaluation', 'pu': 15000, 'annee': 2026},
        ]

        for l in lignes_led:
            ligne = LigneBudget(
                projet_id=led.id,
                categorie_id=l['cat'].id if l['cat'] else None,
                code=l['code'],
                intitule=l['intitule'],
                annee=l.get('annee'),
                quantite=l['qte'],
                unite=l['unite'],
                cout_unitaire=l['pu'],
                montant_prevu=l['qte'] * l['pu']
            )
            db.session.add(ligne)

        # =================================================================
        # PROJET SOR4D / TERAL
        # =================================================================
        print("Création du projet SOR4D...")

        sor4d = Projet(
            code='SOR4D',
            nom='SOR4D TERAL - Sustainable Food Systems',
            description='Projet TAG SOR4D avec GIUB - Systèmes alimentaires durables',
            bailleur_id=giub.id,
            date_debut=date(2025, 1, 1),
            date_fin=date(2025, 12, 31),
            budget_total=104992650,  # 149988.95 CHF en XOF (700 XOF/CHF)
            devise_id=chf.id if chf else None,
            statut='actif'
        )
        db.session.add(sor4d)
        db.session.flush()

        # Lignes budgétaires SOR4D (basées sur votre fichier)
        lignes_sor4d = [
            # LABOR / Salaries
            {'cat': cat_labor, 'code': 'S1', 'intitule': 'Production coordinator', 'qte': 12, 'unite': 'month', 'pu': 450},
            {'cat': cat_labor, 'code': 'S2', 'intitule': 'Value chain coordinator', 'qte': 12, 'unite': 'month', 'pu': 450},
            {'cat': cat_labor, 'code': 'S3', 'intitule': 'Communication officer', 'qte': 12, 'unite': 'month', 'pu': 450},
            {'cat': cat_labor, 'code': 'S4', 'intitule': 'Administration', 'qte': 12, 'unite': 'month', 'pu': 200},

            # SUPPLIES / Equipment
            {'cat': cat_supplies, 'code': 'E1', 'intitule': 'Pumps and solar panels', 'qte': 4, 'unite': 'unit', 'pu': 700},
            {'cat': cat_supplies, 'code': 'E2', 'intitule': 'Irrigation system', 'qte': 1, 'unite': 'lump', 'pu': 3400},
            {'cat': cat_supplies, 'code': 'E3', 'intitule': 'Backup well', 'qte': 1, 'unite': 'lump', 'pu': 4700},
            {'cat': cat_supplies, 'code': 'E4', 'intitule': 'Storage', 'qte': 2, 'unite': 'unit', 'pu': 1000},
            {'cat': cat_supplies, 'code': 'E5', 'intitule': 'Greenhouse', 'qte': 1, 'unite': 'unit', 'pu': 1200},
            {'cat': cat_supplies, 'code': 'E6', 'intitule': 'Drying area', 'qte': 1, 'unite': 'unit', 'pu': 1200},
            {'cat': cat_supplies, 'code': 'E7', 'intitule': 'Storage warehouse + shelter', 'qte': 1, 'unite': 'lump', 'pu': 8000},
            {'cat': cat_supplies, 'code': 'E8', 'intitule': 'Solar energy production', 'qte': 1, 'unite': 'lump', 'pu': 12300},
            {'cat': cat_supplies, 'code': 'E9', 'intitule': 'Lighthouse building', 'qte': 1, 'unite': 'lump', 'pu': 16000},
            {'cat': cat_supplies, 'code': 'E10', 'intitule': 'Cold room + fridge', 'qte': 1, 'unite': 'lump', 'pu': 4800},
            {'cat': cat_supplies, 'code': 'E11', 'intitule': 'Agricultural tools', 'qte': 1, 'unite': 'lump', 'pu': 4500},
            {'cat': cat_supplies, 'code': 'E12', 'intitule': 'Tricycle motorbike', 'qte': 1, 'unite': 'unit', 'pu': 2300},

            # PROGRAM / Activities
            {'cat': cat_program, 'code': 'A1', 'intitule': 'Agroecological production support', 'qte': 12, 'unite': 'month', 'pu': 480},
            {'cat': cat_program, 'code': 'A2', 'intitule': 'Inputs (seeds, fertilizer)', 'qte': 1, 'unite': 'lump', 'pu': 1450},
            {'cat': cat_program, 'code': 'A3', 'intitule': 'Apiculture', 'qte': 1, 'unite': 'lump', 'pu': 750},
            {'cat': cat_program, 'code': 'A4', 'intitule': 'Pisciculture', 'qte': 1, 'unite': 'lump', 'pu': 3800},
            {'cat': cat_program, 'code': 'A5', 'intitule': 'Poultry farming', 'qte': 1, 'unite': 'lump', 'pu': 2570},
            {'cat': cat_program, 'code': 'A6', 'intitule': 'Agroecological training', 'qte': 2, 'unite': 'training', 'pu': 1150},
            {'cat': cat_program, 'code': 'A7', 'intitule': 'Product transformation training', 'qte': 2, 'unite': 'training', 'pu': 1430},
            {'cat': cat_program, 'code': 'A8', 'intitule': 'Launching event', 'qte': 1, 'unite': 'event', 'pu': 2000},
            {'cat': cat_program, 'code': 'A9', 'intitule': 'Food fair organization', 'qte': 1, 'unite': 'event', 'pu': 1500},

            # Communication
            {'cat': cat_program, 'code': 'C1', 'intitule': 'Product merchandizing and design', 'qte': 1, 'unite': 'lump', 'pu': 2250},
            {'cat': cat_program, 'code': 'C2', 'intitule': 'Video pills', 'qte': 10, 'unite': 'video', 'pu': 300},
            {'cat': cat_program, 'code': 'C3', 'intitule': 'Layout and Printings', 'qte': 1, 'unite': 'lump', 'pu': 1750},
            {'cat': cat_program, 'code': 'C4', 'intitule': 'Podcast production', 'qte': 6, 'unite': 'podcast', 'pu': 300},
        ]

        for l in lignes_sor4d:
            ligne = LigneBudget(
                projet_id=sor4d.id,
                categorie_id=l['cat'].id if l['cat'] else None,
                code=l['code'],
                intitule=l['intitule'],
                annee=None,
                quantite=l['qte'],
                unite=l['unite'],
                cout_unitaire=l['pu'],
                montant_prevu=l['qte'] * l['pu']
            )
            db.session.add(ligne)

        db.session.commit()
        print("Données CREATES initialisées avec succès!")
        print(f"- Bailleurs: {Bailleur.query.count()}")
        print(f"- Projets: {Projet.query.count()}")
        print(f"- Lignes budget: {LigneBudget.query.count()}")


if __name__ == '__main__':
    init_creates_data()
