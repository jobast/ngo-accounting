# CREATES GIE - Systeme Comptable

## Apercu du Projet

Application de comptabilite pour **CREATES GIE** (Groupement d'Interet Economique), une ONG basee a Dakar, Senegal. L'application gere la comptabilite de projets finances par des bailleurs de fonds internationaux, conforme aux normes **SYSCOHADA** (Systeme Comptable Ouest-Africain).

**Architecture multi-apps** : Cette app fait partie d'une plateforme a deux apps avec login unifie :
- **ngo-accounting** (port 5001) : Comptabilite SYSCOHADA *(cette app)*
- **creates-se** (port 5002) : Suivi & Evaluation

Les deux apps partagent la meme base de donnees et la meme session (cookie `creates_session`).

## Stack Technique

- **Backend** : Flask (Python)
- **Base de donnees** : SQLite (dev) / PostgreSQL (prod)
- **ORM** : Flask-SQLAlchemy
- **Auth** : Flask-Login (session partagee avec creates-se)
- **Frontend** : Bootstrap 5, Bootstrap Icons
- **PDF** : WeasyPrint
- **Excel** : openpyxl

## Structure du Projet

```
ngo-accounting/
├── app.py                 # Application principale (routes, modeles, logique)
├── instance/
│   └── ngo_accounting.db  # Base de donnees SQLite (partagee avec creates-se)
├── templates/
│   ├── base.html          # Template de base avec sidebar
│   ├── portail.html       # Portail multi-apps (apres login master)
│   ├── dashboard.html     # Tableau de bord
│   ├── auth/              # Login unifie (selecteur compta/S&E/master)
│   ├── admin/             # Utilisateurs, exercices, audit
│   ├── comptabilite/      # Ecritures, plan comptable
│   ├── projets/           # Gestion des projets
│   └── rapports/          # Rapports bailleurs, reconciliation
└── uploads/               # Pieces justificatives (PDF, images)
```

## Modeles de Donnees Principaux

| Modele | Description |
|--------|-------------|
| `Utilisateur` | Utilisateurs avec roles (comptable, directeur, auditeur) |
| `ExerciceComptable` | Annee fiscale (ouvert/cloture) |
| `CompteComptable` | Plan comptable SYSCOHADA (classes 1-9) |
| `Journal` | Journaux comptables (AC, VE, BQ, CA, OD, SAL) |
| `PieceComptable` | En-tete d'ecriture comptable |
| `LigneEcriture` | Lignes debit/credit d'une ecriture |
| `Projet` | Projets finances (LED, SOR4D, etc.) |
| `Bailleur` | Bailleurs de fonds (Nitidae, GIUB, etc.) |
| `LigneBudget` | Lignes budgetaires par projet |
| `PieceJustificative` | Documents scannes attaches aux ecritures |
| `AuditLog` | Journal d'audit des actions |

## Roles et Permissions

| Role | Permissions |
|------|-------------|
| **Comptable** | Saisir ecritures, gerer projets, voir rapports |
| **Directeur** | Tout + valider ecritures, cloturer exercice, gerer utilisateurs (role master) |
| **Auditeur** | Lecture seule, rapports, audit trail |

## Login Unifie

La page de login (`/login`) presente 3 options :
- **Comptabilite** : redirige vers le dashboard compta
- **Suivi & Evaluation** : redirige vers l'app S&E (port 5002)
- **Acces complet (Master)** : redirige vers le portail multi-apps

Session partagee via :
- `SESSION_COOKIE_NAME = 'creates_session'`
- `REMEMBER_COOKIE_NAME = 'creates_remember'`
- Meme `SECRET_KEY` dans les deux apps

## Fonctionnalites Cles

### Comptabilite
- Saisie d'ecritures avec validation equilibre (Debit = Credit)
- Assistants de saisie par type d'operation (paiement, encaissement, salaires)
- Validation des ecritures par le directeur (individuelle ou en lot)
- Plan comptable SYSCOHADA avec sous-comptes par bailleur/devise

### Gestion de Projets
- Suivi budgetaire par projet et ligne budgetaire
- Calcul du realise = somme des debits sur comptes de charge (classe 6)
- Imputation analytique multi-projets (ventilation des charges partagees)

### Rapports
- Rapport bailleur (budget vs realise par projet)
- Grand livre, Balance generale
- Reconciliation analytique ↔ comptabilite generale
- Export PDF et Excel

### Audit et Tracabilite
- Pieces justificatives (upload PDF/images)
- Journal d'audit complet (creation, modification, validation)
- Cloture d'exercice irreversible

## Conventions Comptables SYSCOHADA

```
Classe 1 : Capitaux propres
Classe 2 : Immobilisations
Classe 3 : Stocks
Classe 4 : Tiers (fournisseurs 40x, clients 41x, personnel 42x)
Classe 5 : Tresorerie (banque 52x, caisse 57x)
Classe 6 : Charges (achats 60x, services 61-62x, personnel 66x)
Classe 7 : Produits (subventions 74x)
```

## Lancer l'Application

```bash
cd ngo-accounting
pip install -r requirements.txt
python app.py
```

Acces : http://127.0.0.1:5001

**Login par defaut** : `admin@creates.sn` / `admin123`

## Variables d'Environnement

```
SECRET_KEY=<meme cle que creates-se>
PORT=5001
COMPTA_URL=http://localhost:5001
SE_URL=http://localhost:5002
DATABASE_URL=sqlite:///ngo_accounting.db
```

## Routes Principales

| Route | Description |
|-------|-------------|
| `/login` | Connexion unifiee (selecteur d'app) |
| `/portail` | Portail multi-apps |
| `/` | Dashboard compta |
| `/comptabilite/ecritures` | Liste des ecritures |
| `/comptabilite/ecritures/nouvelle` | Nouvelle ecriture |
| `/projets` | Liste des projets |
| `/rapports/projet/<id>` | Rapport bailleur |
| `/admin/utilisateurs` | Gestion utilisateurs |
| `/admin/exercices` | Gestion exercices |
| `/admin/audit` | Journal d'audit |
