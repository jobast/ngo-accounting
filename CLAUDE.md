# CREATES GIE - Système Comptable

## Aperçu du Projet

Application de comptabilité pour **CREATES GIE** (Groupement d'Intérêt Économique), une ONG basée à Dakar, Sénégal. L'application gère la comptabilité de projets financés par des bailleurs de fonds internationaux, conforme aux normes **SYSCOHADA** (Système Comptable Ouest-Africain).

## Stack Technique

- **Backend** : Flask (Python)
- **Base de données** : SQLite (dev) / PostgreSQL (prod)
- **ORM** : Flask-SQLAlchemy
- **Auth** : Flask-Login
- **Frontend** : Bootstrap 5, Bootstrap Icons
- **PDF** : WeasyPrint
- **Excel** : openpyxl

## Structure du Projet

```
ngo-accounting/
├── app.py                 # Application principale (routes, modèles, logique)
├── instance/
│   └── creates.db         # Base de données SQLite
├── templates/
│   ├── base.html          # Template de base avec sidebar
│   ├── dashboard.html     # Tableau de bord
│   ├── auth/              # Login, mot de passe oublié
│   ├── admin/             # Utilisateurs, exercices, audit
│   ├── comptabilite/      # Écritures, plan comptable
│   ├── projets/           # Gestion des projets
│   └── rapports/          # Rapports bailleurs, réconciliation
└── uploads/               # Pièces justificatives (PDF, images)
```

## Modèles de Données Principaux

| Modèle | Description |
|--------|-------------|
| `Utilisateur` | Utilisateurs avec rôles (comptable, directeur, auditeur) |
| `ExerciceComptable` | Année fiscale (ouvert/clôturé) |
| `CompteComptable` | Plan comptable SYSCOHADA (classes 1-9) |
| `Journal` | Journaux comptables (AC, VE, BQ, CA, OD, SAL) |
| `PieceComptable` | En-tête d'écriture comptable |
| `LigneEcriture` | Lignes débit/crédit d'une écriture |
| `Projet` | Projets financés (LED, SOR4D, etc.) |
| `Bailleur` | Bailleurs de fonds (Nitidae, GIUB, etc.) |
| `LigneBudget` | Lignes budgétaires par projet |
| `PieceJustificative` | Documents scannés attachés aux écritures |
| `AuditLog` | Journal d'audit des actions |

## Rôles et Permissions

| Rôle | Permissions |
|------|-------------|
| **Comptable** | Saisir écritures, gérer projets, voir rapports |
| **Directeur** | Tout + valider écritures, clôturer exercice, gérer utilisateurs |
| **Auditeur** | Lecture seule, rapports, audit trail |

## Fonctionnalités Clés

### Comptabilité
- Saisie d'écritures avec validation équilibre (Débit = Crédit)
- Assistants de saisie par type d'opération (paiement, encaissement, salaires)
- Validation des écritures par le directeur (individuelle ou en lot)
- Plan comptable SYSCOHADA avec sous-comptes par bailleur/devise

### Gestion de Projets
- Suivi budgétaire par projet et ligne budgétaire
- Calcul du réalisé = somme des débits sur comptes de charge (classe 6)
- Imputation analytique multi-projets (ventilation des charges partagées)

### Rapports
- Rapport bailleur (budget vs réalisé par projet)
- Grand livre, Balance générale
- Réconciliation analytique ↔ comptabilité générale
- Export PDF et Excel

### Audit et Traçabilité
- Pièces justificatives (upload PDF/images)
- Journal d'audit complet (création, modification, validation)
- Clôture d'exercice irréversible

## Conventions Comptables SYSCOHADA

```
Classe 1 : Capitaux propres
Classe 2 : Immobilisations
Classe 3 : Stocks
Classe 4 : Tiers (fournisseurs 40x, clients 41x, personnel 42x)
Classe 5 : Trésorerie (banque 52x, caisse 57x)
Classe 6 : Charges (achats 60x, services 61-62x, personnel 66x)
Classe 7 : Produits (subventions 74x)
```

## Lancer l'Application

```bash
cd ngo-accounting
pip install -r requirements.txt
python app.py
```

Accès : http://127.0.0.1:5000

**Login par défaut** : `admin@creates.sn` / `admin123`

## Points d'Attention

1. **Validation serveur** : L'équilibre Débit=Crédit est vérifié côté serveur (pas seulement JS)
2. **Écritures validées** : Une fois validée, une écriture ne peut plus être modifiée
3. **Exercice clôturé** : Aucune écriture ne peut être ajoutée/modifiée
4. **Calcul réalisé** : Seuls les débits sur comptes classe 6 sont comptés
5. **Devise par défaut** : XOF (Franc CFA)

## Routes Principales

| Route | Description |
|-------|-------------|
| `/login` | Connexion |
| `/` | Dashboard |
| `/comptabilite/ecritures` | Liste des écritures (avec filtres) |
| `/comptabilite/ecritures/nouvelle` | Nouvelle écriture |
| `/comptabilite/ecritures/<id>` | Détail d'une écriture |
| `/projets` | Liste des projets |
| `/rapports/projet/<id>` | Rapport bailleur |
| `/admin/utilisateurs` | Gestion utilisateurs |
| `/admin/exercices` | Gestion exercices |
| `/admin/audit` | Journal d'audit |
