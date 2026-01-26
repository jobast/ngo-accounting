"""
CREATES NGO Accounting System
Application de comptabilité pour ONG - Conforme SYSCOHADA
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import wraps
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'creates-ngo-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ngo_accounting.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Create upload folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'


# =============================================================================
# DECORATORS
# =============================================================================

def role_required(roles):
    """Décorateur pour restreindre l'accès par rôle"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Veuillez vous connecter.', 'warning')
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Vous n\'avez pas les permissions nécessaires.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_audit(table_name, record_id, action, old_values=None, new_values=None):
    """Enregistrer une action dans le journal d'audit"""
    audit = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        user=current_user.email if current_user.is_authenticated else 'system',
        ip_address=request.remote_addr if request else None
    )
    db.session.add(audit)


@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))

# =============================================================================
# MODELS
# =============================================================================

class Devise(db.Model):
    """Currencies / Devises"""
    __tablename__ = 'devises'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)  # XOF, USD, EUR
    nom = db.Column(db.String(50), nullable=False)
    symbole = db.Column(db.String(5))
    taux_base = db.Column(db.Numeric(15, 6), default=1)  # Taux vs XOF

    def __repr__(self):
        return f'<Devise {self.code}>'


class ExerciceComptable(db.Model):
    """Fiscal Year / Exercice comptable"""
    __tablename__ = 'exercices'

    id = db.Column(db.Integer, primary_key=True)
    annee = db.Column(db.Integer, unique=True, nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    cloture = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Exercice {self.annee}>'


class CompteComptable(db.Model):
    """Chart of Accounts / Plan comptable SYSCOHADA"""
    __tablename__ = 'comptes'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    intitule = db.Column(db.String(200), nullable=False)
    classe = db.Column(db.Integer, nullable=False)  # 1-7 SYSCOHADA
    type_compte = db.Column(db.String(20))  # actif, passif, charge, produit
    compte_parent_id = db.Column(db.Integer, db.ForeignKey('comptes.id'))
    actif = db.Column(db.Boolean, default=True)

    # Relations
    compte_parent = db.relationship('CompteComptable', remote_side=[id], backref='sous_comptes')

    def __repr__(self):
        return f'<Compte {self.numero} - {self.intitule}>'


class Bailleur(db.Model):
    """Donors / Bailleurs de fonds"""
    __tablename__ = 'bailleurs'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    nom = db.Column(db.String(200), nullable=False)
    pays = db.Column(db.String(100))
    contact = db.Column(db.String(200))
    email = db.Column(db.String(100))
    devise_id = db.Column(db.Integer, db.ForeignKey('devises.id'))
    actif = db.Column(db.Boolean, default=True)

    # Relations
    devise = db.relationship('Devise')
    projets = db.relationship('Projet', back_populates='bailleur')

    def __repr__(self):
        return f'<Bailleur {self.code} - {self.nom}>'


class Projet(db.Model):
    """Projects / Projets"""
    __tablename__ = 'projets'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    nom = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    bailleur_id = db.Column(db.Integer, db.ForeignKey('bailleurs.id'))
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
    budget_total = db.Column(db.Numeric(15, 2), default=0)
    devise_id = db.Column(db.Integer, db.ForeignKey('devises.id'))
    statut = db.Column(db.String(20), default='actif')  # actif, cloture, suspendu

    # Relations
    bailleur = db.relationship('Bailleur', back_populates='projets')
    devise = db.relationship('Devise')
    lignes_budget = db.relationship('LigneBudget', back_populates='projet', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Projet {self.code} - {self.nom}>'


class CategorieBudget(db.Model):
    """Budget Categories / Catégories budgétaires"""
    __tablename__ = 'categories_budget'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    ordre = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Categorie {self.code} - {self.nom}>'


class LigneBudget(db.Model):
    """Budget Lines / Lignes budgétaires"""
    __tablename__ = 'lignes_budget'

    id = db.Column(db.Integer, primary_key=True)
    projet_id = db.Column(db.Integer, db.ForeignKey('projets.id'), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories_budget.id'))
    code = db.Column(db.String(20), nullable=False)
    intitule = db.Column(db.String(200), nullable=False)
    annee = db.Column(db.Integer)  # Pour budget multi-années
    quantite = db.Column(db.Numeric(10, 2), default=1)
    unite = db.Column(db.String(50))
    cout_unitaire = db.Column(db.Numeric(15, 2), default=0)
    montant_prevu = db.Column(db.Numeric(15, 2), default=0)

    # Relations
    projet = db.relationship('Projet', back_populates='lignes_budget')
    categorie = db.relationship('CategorieBudget')

    def __repr__(self):
        return f'<LigneBudget {self.code} - {self.intitule}>'


class Journal(db.Model):
    """Accounting Journals / Journaux comptables"""
    __tablename__ = 'journaux'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    type_journal = db.Column(db.String(20))  # achat, vente, banque, caisse, od

    def __repr__(self):
        return f'<Journal {self.code} - {self.nom}>'


class PieceComptable(db.Model):
    """Accounting Entries / Pièces comptables"""
    __tablename__ = 'pieces'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    date_piece = db.Column(db.Date, nullable=False)
    journal_id = db.Column(db.Integer, db.ForeignKey('journaux.id'), nullable=False)
    exercice_id = db.Column(db.Integer, db.ForeignKey('exercices.id'), nullable=False)
    libelle = db.Column(db.String(200), nullable=False)
    reference = db.Column(db.String(100))  # Numéro facture, chèque, etc.
    devise_id = db.Column(db.Integer, db.ForeignKey('devises.id'))
    taux_change = db.Column(db.Numeric(15, 6), default=1)
    valide = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    journal = db.relationship('Journal')
    exercice = db.relationship('ExerciceComptable', backref='pieces')
    devise = db.relationship('Devise')
    lignes = db.relationship('LigneEcriture', back_populates='piece', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Piece {self.numero} - {self.libelle}>'

    @property
    def total_debit(self):
        return sum(l.debit or 0 for l in self.lignes)

    @property
    def total_credit(self):
        return sum(l.credit or 0 for l in self.lignes)

    @property
    def est_equilibree(self):
        return abs(self.total_debit - self.total_credit) < 0.01


class LigneEcriture(db.Model):
    """Journal Entry Lines / Lignes d'écriture"""
    __tablename__ = 'lignes_ecriture'

    id = db.Column(db.Integer, primary_key=True)
    piece_id = db.Column(db.Integer, db.ForeignKey('pieces.id'), nullable=False)
    compte_id = db.Column(db.Integer, db.ForeignKey('comptes.id'), nullable=False)
    projet_id = db.Column(db.Integer, db.ForeignKey('projets.id'))
    ligne_budget_id = db.Column(db.Integer, db.ForeignKey('lignes_budget.id'))
    libelle = db.Column(db.String(200))
    debit = db.Column(db.Numeric(15, 2), default=0)
    credit = db.Column(db.Numeric(15, 2), default=0)

    # Relations
    piece = db.relationship('PieceComptable', back_populates='lignes')
    compte = db.relationship('CompteComptable')
    projet = db.relationship('Projet')
    ligne_budget = db.relationship('LigneBudget')

    def __repr__(self):
        return f'<Ligne {self.compte.numero if self.compte else ""} D:{self.debit} C:{self.credit}>'


class ImputationAnalytique(db.Model):
    """Analytical Imputation / Ventilation analytique multi-projets

    Permet de répartir une charge sur plusieurs projets.
    Ex: Loyer 60% LED + 40% SOR4D
    """
    __tablename__ = 'imputations_analytiques'

    id = db.Column(db.Integer, primary_key=True)
    ligne_ecriture_id = db.Column(db.Integer, db.ForeignKey('lignes_ecriture.id'), nullable=False)
    projet_id = db.Column(db.Integer, db.ForeignKey('projets.id'), nullable=False)
    ligne_budget_id = db.Column(db.Integer, db.ForeignKey('lignes_budget.id'))
    pourcentage = db.Column(db.Numeric(5, 2))  # Ex: 60.00 pour 60%
    montant = db.Column(db.Numeric(15, 2))     # Montant calculé

    # Relations
    ligne_ecriture = db.relationship('LigneEcriture', backref='imputations_analytiques')
    projet = db.relationship('Projet')
    ligne_budget = db.relationship('LigneBudget')

    def __repr__(self):
        return f'<Imputation {self.projet.code if self.projet else ""} {self.pourcentage}%>'


class AuditLog(db.Model):
    """Journal d'audit - Traçabilité des modifications"""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer)
    action = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE
    old_values = db.Column(db.Text)    # JSON des anciennes valeurs
    new_values = db.Column(db.Text)    # JSON des nouvelles valeurs
    user = db.Column(db.String(100))
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.table_name} {self.action} {self.timestamp}>'


class PieceJustificative(db.Model):
    """Pièces justificatives / Supporting Documents

    Permet d'attacher des documents scannés aux écritures.
    """
    __tablename__ = 'pieces_justificatives'

    id = db.Column(db.Integer, primary_key=True)
    ligne_ecriture_id = db.Column(db.Integer, db.ForeignKey('lignes_ecriture.id'))
    piece_comptable_id = db.Column(db.Integer, db.ForeignKey('pieces.id'))
    type_piece = db.Column(db.String(50))  # facture, recu, contrat, bon_commande
    numero_piece = db.Column(db.String(50))
    fichier_path = db.Column(db.String(255))  # Chemin du fichier
    fichier_nom = db.Column(db.String(255))   # Nom original du fichier
    date_piece = db.Column(db.Date)
    description = db.Column(db.String(255))
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.String(100))

    # Relations
    ligne_ecriture = db.relationship('LigneEcriture', backref='pieces_justificatives')
    piece_comptable = db.relationship('PieceComptable', backref='pieces_justificatives')

    def __repr__(self):
        return f'<PieceJustificative {self.type_piece} {self.numero_piece}>'


class Utilisateur(UserMixin, db.Model):
    """Utilisateurs avec rôles et permissions"""
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100))
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='comptable')  # comptable, directeur, auditeur
    actif = db.Column(db.Boolean, default=True)
    derniere_connexion = db.Column(db.DateTime)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))

    # Permissions par rôle
    ROLES_PERMISSIONS = {
        'comptable': ['saisie_ecritures', 'voir_rapports', 'gerer_projets'],
        'directeur': ['saisie_ecritures', 'voir_rapports', 'gerer_projets',
                      'valider_ecritures', 'cloturer_exercice', 'gerer_utilisateurs'],
        'auditeur': ['voir_rapports', 'voir_audit_trail', 'export_donnees']
    }

    def has_permission(self, permission):
        """Vérifie si l'utilisateur a une permission donnée"""
        return permission in self.ROLES_PERMISSIONS.get(self.role, [])

    def __repr__(self):
        return f'<Utilisateur {self.email} ({self.role})>'


class Alerte(db.Model):
    """Alertes système pour le suivi budgétaire"""
    __tablename__ = 'alertes'

    id = db.Column(db.Integer, primary_key=True)
    type_alerte = db.Column(db.String(50), nullable=False)  # budget_80, ecritures_non_validees, solde_negatif
    niveau = db.Column(db.String(20), default='warning')  # info, warning, danger
    message = db.Column(db.String(500), nullable=False)
    projet_id = db.Column(db.Integer, db.ForeignKey('projets.id'))
    compte_id = db.Column(db.Integer, db.ForeignKey('comptes.id'))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_lecture = db.Column(db.DateTime)
    lu_par = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)

    # Relations
    projet = db.relationship('Projet')
    compte = db.relationship('CompteComptable')

    def __repr__(self):
        return f'<Alerte {self.type_alerte} {self.niveau}>'


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generer_alertes():
    """Génère les alertes système automatiques"""
    alertes = []

    # Alerte: Projets > 80% budget consommé
    projets = Projet.query.filter_by(statut='actif').all()
    for projet in projets:
        total_prevu = sum(float(l.montant_prevu or 0) for l in projet.lignes_budget)
        if total_prevu > 0:
            total_realise = 0
            for ligne in projet.lignes_budget:
                realise = db.session.query(
                    db.func.sum(LigneEcriture.debit)
                ).join(CompteComptable).filter(
                    (LigneEcriture.ligne_budget_id == ligne.id) &
                    (CompteComptable.classe == 6)
                ).scalar() or 0
                total_realise += float(realise)

            taux = (total_realise / total_prevu) * 100
            if taux > 80:
                alertes.append({
                    'type': 'budget_80',
                    'niveau': 'danger' if taux > 100 else 'warning',
                    'message': f"Projet {projet.code}: {taux:.0f}% du budget consommé",
                    'projet': projet
                })

    # Alerte: Écritures non validées > 7 jours
    date_limite = datetime.utcnow() - timedelta(days=7)
    ecritures_non_validees = PieceComptable.query.filter(
        PieceComptable.valide == False,
        PieceComptable.date_creation < date_limite
    ).count()
    if ecritures_non_validees > 0:
        alertes.append({
            'type': 'ecritures_non_validees',
            'niveau': 'warning',
            'message': f"{ecritures_non_validees} écriture(s) non validée(s) depuis plus de 7 jours",
            'projet': None
        })

    # Alerte: Solde bancaire négatif (comptes classe 5)
    comptes_banque = db.session.query(
        CompteComptable.numero,
        CompteComptable.intitule,
        db.func.sum(LigneEcriture.debit).label('total_debit'),
        db.func.sum(LigneEcriture.credit).label('total_credit')
    ).join(
        LigneEcriture, LigneEcriture.compte_id == CompteComptable.id
    ).filter(
        CompteComptable.classe == 5
    ).group_by(CompteComptable.id).all()

    for compte in comptes_banque:
        solde = float(compte.total_debit or 0) - float(compte.total_credit or 0)
        if solde < 0:
            alertes.append({
                'type': 'solde_negatif',
                'niveau': 'danger',
                'message': f"Compte {compte.numero} ({compte.intitule}): solde négatif de {solde:,.0f} FCFA",
                'projet': None
            })

    return alertes


def calculer_stats_dashboard():
    """Calcule les statistiques pour le dashboard"""
    projets = Projet.query.filter_by(statut='actif').all()

    stats = {
        'nb_projets': len(projets),
        'nb_bailleurs': Bailleur.query.filter_by(actif=True).count(),
        'budget_total': sum(float(p.budget_total or 0) for p in projets),
        'total_realise': 0,
        'ecritures_mois': 0,
        'projets_data': []
    }

    # Calculer réalisé total
    for projet in projets:
        projet_realise = 0
        projet_prevu = sum(float(l.montant_prevu or 0) for l in projet.lignes_budget)
        for ligne in projet.lignes_budget:
            realise = db.session.query(
                db.func.sum(LigneEcriture.debit)
            ).join(CompteComptable).filter(
                (LigneEcriture.ligne_budget_id == ligne.id) &
                (CompteComptable.classe == 6)
            ).scalar() or 0
            projet_realise += float(realise)

        stats['total_realise'] += projet_realise
        if projet_prevu > 0:
            stats['projets_data'].append({
                'code': projet.code,
                'nom': projet.nom,
                'prevu': projet_prevu,
                'realise': projet_realise,
                'taux': (projet_realise / projet_prevu) * 100
            })

    # Écritures ce mois
    debut_mois = date.today().replace(day=1)
    stats['ecritures_mois'] = PieceComptable.query.filter(
        PieceComptable.date_piece >= debut_mois
    ).count()

    # Taux d'exécution global
    if stats['budget_total'] > 0:
        stats['taux_execution'] = (stats['total_realise'] / stats['budget_total']) * 100
    else:
        stats['taux_execution'] = 0

    return stats


# =============================================================================
# ROUTES - AUTHENTICATION
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = Utilisateur.query.filter_by(email=email).first()

        if user and user.actif and check_password_hash(user.password_hash, password):
            login_user(user, remember=request.form.get('remember'))
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()

            log_audit('utilisateurs', user.id, 'LOGIN')
            db.session.commit()

            next_page = request.args.get('next')
            flash(f'Bienvenue, {user.prenom or user.nom}!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    log_audit('utilisateurs', current_user.id, 'LOGOUT')
    db.session.commit()
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))


@app.route('/admin/utilisateurs')
@login_required
@role_required(['directeur'])
def liste_utilisateurs():
    """Gestion des utilisateurs (Directeur uniquement)"""
    utilisateurs = Utilisateur.query.all()
    return render_template('admin/utilisateurs.html', utilisateurs=utilisateurs)


@app.route('/admin/utilisateurs/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['directeur'])
def nouveau_utilisateur():
    """Créer un nouvel utilisateur"""
    if request.method == 'POST':
        email = request.form.get('email')

        if Utilisateur.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
        else:
            utilisateur = Utilisateur(
                email=email,
                nom=request.form.get('nom'),
                prenom=request.form.get('prenom'),
                password_hash=generate_password_hash(request.form.get('password')),
                role=request.form.get('role', 'comptable'),
                created_by=current_user.email
            )
            db.session.add(utilisateur)
            log_audit('utilisateurs', None, 'CREATE', new_values={'email': email, 'role': utilisateur.role})
            db.session.commit()
            flash('Utilisateur créé avec succès.', 'success')
            return redirect(url_for('liste_utilisateurs'))

    return render_template('admin/utilisateur_form.html')


@app.route('/admin/utilisateurs/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['directeur'])
def modifier_utilisateur(id):
    """Modifier un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)

    if request.method == 'POST':
        old_values = {'email': utilisateur.email, 'role': utilisateur.role, 'actif': utilisateur.actif}

        utilisateur.nom = request.form.get('nom')
        utilisateur.prenom = request.form.get('prenom')
        utilisateur.role = request.form.get('role')
        utilisateur.actif = request.form.get('actif') == 'on'

        if request.form.get('password'):
            utilisateur.password_hash = generate_password_hash(request.form.get('password'))

        new_values = {'email': utilisateur.email, 'role': utilisateur.role, 'actif': utilisateur.actif}
        log_audit('utilisateurs', id, 'UPDATE', old_values=old_values, new_values=new_values)
        db.session.commit()

        flash('Utilisateur modifié avec succès.', 'success')
        return redirect(url_for('liste_utilisateurs'))

    return render_template('admin/utilisateur_form.html', utilisateur=utilisateur)


@app.route('/admin/audit')
@login_required
@role_required(['directeur', 'auditeur'])
def audit_trail():
    """Consulter le journal d'audit"""
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
    return render_template('admin/audit_trail.html', logs=logs)


# =============================================================================
# ROUTES - DASHBOARD
# =============================================================================

@app.route('/')
@login_required
def dashboard():
    """Tableau de bord principal"""
    projets = Projet.query.filter_by(statut='actif').all()
    bailleurs = Bailleur.query.filter_by(actif=True).all()

    # Statistiques améliorées
    stats = calculer_stats_dashboard()

    # Alertes
    alertes = generer_alertes()

    return render_template('dashboard.html',
                          projets=projets,
                          bailleurs=bailleurs,
                          stats=stats,
                          alertes=alertes)


# =============================================================================
# ROUTES - BAILLEURS
# =============================================================================

@app.route('/bailleurs')
@login_required
def liste_bailleurs():
    """Liste des bailleurs"""
    bailleurs = Bailleur.query.all()
    return render_template('bailleurs/liste.html', bailleurs=bailleurs)


@app.route('/bailleurs/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['comptable', 'directeur'])
def nouveau_bailleur():
    """Créer un nouveau bailleur"""
    devises = Devise.query.all()

    if request.method == 'POST':
        bailleur = Bailleur(
            code=request.form['code'],
            nom=request.form['nom'],
            pays=request.form.get('pays'),
            contact=request.form.get('contact'),
            email=request.form.get('email'),
            devise_id=request.form.get('devise_id') or None
        )
        db.session.add(bailleur)
        db.session.commit()
        flash('Bailleur créé avec succès', 'success')
        return redirect(url_for('liste_bailleurs'))

    return render_template('bailleurs/form.html', devises=devises)


@app.route('/bailleurs/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['comptable', 'directeur'])
def modifier_bailleur(id):
    """Modifier un bailleur"""
    bailleur = Bailleur.query.get_or_404(id)
    devises = Devise.query.all()

    if request.method == 'POST':
        bailleur.code = request.form['code']
        bailleur.nom = request.form['nom']
        bailleur.pays = request.form.get('pays')
        bailleur.contact = request.form.get('contact')
        bailleur.email = request.form.get('email')
        bailleur.devise_id = request.form.get('devise_id') or None
        db.session.commit()
        flash('Bailleur modifié avec succès', 'success')
        return redirect(url_for('liste_bailleurs'))

    return render_template('bailleurs/form.html', bailleur=bailleur, devises=devises)


# =============================================================================
# ROUTES - PROJETS
# =============================================================================

@app.route('/projets')
@login_required
def liste_projets():
    """Liste des projets"""
    projets = Projet.query.all()
    return render_template('projets/liste.html', projets=projets)


@app.route('/projets/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['comptable', 'directeur'])
def nouveau_projet():
    """Créer un nouveau projet"""
    bailleurs = Bailleur.query.filter_by(actif=True).all()
    devises = Devise.query.all()

    if request.method == 'POST':
        projet = Projet(
            code=request.form['code'],
            nom=request.form['nom'],
            description=request.form.get('description'),
            bailleur_id=request.form.get('bailleur_id') or None,
            date_debut=datetime.strptime(request.form['date_debut'], '%Y-%m-%d').date() if request.form.get('date_debut') else None,
            date_fin=datetime.strptime(request.form['date_fin'], '%Y-%m-%d').date() if request.form.get('date_fin') else None,
            budget_total=request.form.get('budget_total') or 0,
            devise_id=request.form.get('devise_id') or None
        )
        db.session.add(projet)
        db.session.commit()
        flash('Projet créé avec succès', 'success')
        return redirect(url_for('liste_projets'))

    return render_template('projets/form.html', bailleurs=bailleurs, devises=devises)


@app.route('/projets/<int:id>')
@login_required
def detail_projet(id):
    """Détail d'un projet avec budget"""
    projet = Projet.query.get_or_404(id)
    categories = CategorieBudget.query.order_by(CategorieBudget.ordre).all()

    # Calcul des réalisés par ligne budgétaire
    # SYSCOHADA: Pour les charges (classe 6), seuls les débits comptent comme dépenses réalisées
    realisations = {}
    for ligne in projet.lignes_budget:
        realise = db.session.query(
            db.func.sum(LigneEcriture.debit)
        ).join(CompteComptable).filter(
            (LigneEcriture.ligne_budget_id == ligne.id) &
            (CompteComptable.classe == 6)
        ).scalar() or 0
        realisations[ligne.id] = float(realise)

    return render_template('projets/detail.html',
                         projet=projet,
                         categories=categories,
                         realisations=realisations)


@app.route('/projets/<int:id>/budget/ajouter', methods=['GET', 'POST'])
@login_required
@role_required(['comptable', 'directeur'])
def ajouter_ligne_budget(id):
    """Ajouter une ligne budgétaire"""
    projet = Projet.query.get_or_404(id)
    categories = CategorieBudget.query.order_by(CategorieBudget.ordre).all()

    if request.method == 'POST':
        montant = float(request.form.get('quantite', 1)) * float(request.form.get('cout_unitaire', 0))
        ligne = LigneBudget(
            projet_id=projet.id,
            categorie_id=request.form.get('categorie_id') or None,
            code=request.form['code'],
            intitule=request.form['intitule'],
            annee=request.form.get('annee') or None,
            quantite=request.form.get('quantite') or 1,
            unite=request.form.get('unite'),
            cout_unitaire=request.form.get('cout_unitaire') or 0,
            montant_prevu=montant
        )
        db.session.add(ligne)
        db.session.commit()
        flash('Ligne budgétaire ajoutée', 'success')
        return redirect(url_for('detail_projet', id=id))

    return render_template('projets/ligne_budget_form.html', projet=projet, categories=categories)


# =============================================================================
# ROUTES - COMPTABILITE
# =============================================================================

@app.route('/comptabilite/comptes')
@login_required
def plan_comptable():
    """Plan comptable"""
    comptes = CompteComptable.query.order_by(CompteComptable.numero).all()
    return render_template('comptabilite/plan_comptable.html', comptes=comptes)


@app.route('/comptabilite/ecritures')
@login_required
def liste_ecritures():
    """Liste des écritures comptables avec filtres"""
    # Base query
    query = PieceComptable.query

    # Filtre par exercice
    exercice_id = request.args.get('exercice_id', type=int)
    if exercice_id:
        query = query.filter(PieceComptable.exercice_id == exercice_id)

    # Filtre par journal
    journal_id = request.args.get('journal_id', type=int)
    if journal_id:
        query = query.filter(PieceComptable.journal_id == journal_id)

    # Filtre par statut de validation
    valide = request.args.get('valide')
    if valide == '1':
        query = query.filter(PieceComptable.valide == True)
    elif valide == '0':
        query = query.filter(PieceComptable.valide == False)

    # Recherche textuelle
    q = request.args.get('q', '').strip()
    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                PieceComptable.numero.ilike(search),
                PieceComptable.libelle.ilike(search),
                PieceComptable.reference.ilike(search)
            )
        )

    # Ordonner et limiter
    pieces = query.order_by(PieceComptable.date_piece.desc()).limit(200).all()

    # Données pour les filtres
    exercices = ExerciceComptable.query.order_by(ExerciceComptable.annee.desc()).all()
    journaux = Journal.query.order_by(Journal.code).all()

    return render_template('comptabilite/ecritures.html',
                           pieces=pieces,
                           exercices=exercices,
                           journaux=journaux)


@app.route('/comptabilite/ecritures/nouvelle', methods=['GET', 'POST'])
@login_required
@role_required(['comptable', 'directeur'])
def nouvelle_ecriture():
    """Saisir une nouvelle écriture"""
    journaux = Journal.query.all()
    exercices = ExerciceComptable.query.filter_by(cloture=False).all()
    comptes = CompteComptable.query.filter_by(actif=True).order_by(CompteComptable.numero).all()
    projets = Projet.query.filter_by(statut='actif').all()
    devises = Devise.query.all()

    if request.method == 'POST':
        # Générer numéro de pièce
        dernier = PieceComptable.query.order_by(PieceComptable.id.desc()).first()
        numero = f"PC{datetime.now().year}{(dernier.id + 1 if dernier else 1):05d}"

        piece = PieceComptable(
            numero=numero,
            date_piece=datetime.strptime(request.form['date_piece'], '%Y-%m-%d').date(),
            journal_id=request.form['journal_id'],
            exercice_id=request.form['exercice_id'],
            libelle=request.form['libelle'],
            reference=request.form.get('reference'),
            devise_id=request.form.get('devise_id') or None,
            taux_change=request.form.get('taux_change') or 1
        )
        db.session.add(piece)
        db.session.flush()

        # Ajouter les lignes
        comptes_ids = request.form.getlist('compte_id[]')
        projets_ids = request.form.getlist('projet_id[]')
        libelles = request.form.getlist('ligne_libelle[]')
        debits = request.form.getlist('debit[]')
        credits = request.form.getlist('credit[]')
        ventilations = request.form.getlist('ventilation[]')

        for i in range(len(comptes_ids)):
            if comptes_ids[i]:
                # Déterminer le montant de la ligne
                montant_ligne = float(debits[i]) if debits[i] else float(credits[i]) if credits[i] else 0

                ligne = LigneEcriture(
                    piece_id=piece.id,
                    compte_id=comptes_ids[i],
                    projet_id=projets_ids[i] if i < len(projets_ids) and projets_ids[i] else None,
                    libelle=libelles[i] if i < len(libelles) else '',
                    debit=float(debits[i]) if debits[i] else 0,
                    credit=float(credits[i]) if credits[i] else 0
                )
                db.session.add(ligne)
                db.session.flush()  # Pour obtenir l'ID de la ligne

                # Traiter la ventilation multi-projets si présente
                if i < len(ventilations) and ventilations[i]:
                    try:
                        ventilation_data = json.loads(ventilations[i])
                        if ventilation_data:
                            for v in ventilation_data:
                                imputation = ImputationAnalytique(
                                    ligne_ecriture_id=ligne.id,
                                    projet_id=int(v['projet_id']),
                                    pourcentage=Decimal(str(v['pourcentage'])),
                                    montant=Decimal(str(montant_ligne * v['pourcentage'] / 100))
                                )
                                db.session.add(imputation)
                    except (json.JSONDecodeError, KeyError):
                        pass  # Ignorer les données de ventilation invalides

        # VALIDATION SYSCOHADA : Vérifier équilibre Débit = Crédit
        if not piece.est_equilibree:
            db.session.rollback()
            flash("Écriture déséquilibrée - Total Débit ≠ Total Crédit. L'écriture n'a pas été enregistrée.", "danger")
            return redirect(url_for('nouvelle_ecriture'))

        db.session.commit()
        flash(f'Écriture {numero} créée avec succès', 'success')
        return redirect(url_for('liste_ecritures'))

    return render_template('comptabilite/ecriture_form.html',
                         journaux=journaux,
                         exercices=exercices,
                         comptes=comptes,
                         projets=projets,
                         devises=devises,
                         today=date.today().strftime('%Y-%m-%d'))


@app.route('/comptabilite/ecritures/<int:id>')
@login_required
def detail_ecriture(id):
    """Détail d'une écriture comptable"""
    piece = PieceComptable.query.get_or_404(id)
    return render_template('comptabilite/ecriture_detail.html', piece=piece)


@app.route('/comptabilite/ecritures/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['comptable', 'directeur'])
def modifier_ecriture(id):
    """Modifier une écriture comptable non validée"""
    piece = PieceComptable.query.get_or_404(id)

    if piece.valide:
        flash('Impossible de modifier une écriture validée.', 'danger')
        return redirect(url_for('detail_ecriture', id=id))

    # Check if exercise is closed
    if piece.exercice.cloture:
        flash('Impossible de modifier une écriture sur un exercice clôturé.', 'danger')
        return redirect(url_for('detail_ecriture', id=id))

    journaux = Journal.query.all()
    exercices = ExerciceComptable.query.filter_by(cloture=False).all()
    comptes = CompteComptable.query.filter_by(actif=True).order_by(CompteComptable.numero).all()
    projets = Projet.query.filter_by(statut='actif').all()
    devises = Devise.query.all()
    lignes_budget = LigneBudget.query.all()

    if request.method == 'POST':
        # Store old values for audit
        old_values = {
            'date_piece': str(piece.date_piece),
            'libelle': piece.libelle,
            'reference': piece.reference
        }

        # Update piece
        piece.date_piece = datetime.strptime(request.form['date_piece'], '%Y-%m-%d').date()
        piece.journal_id = request.form['journal_id']
        piece.exercice_id = request.form['exercice_id']
        piece.libelle = request.form['libelle']
        piece.reference = request.form.get('reference')
        piece.devise_id = request.form.get('devise_id') or None
        piece.taux_change = request.form.get('taux_change') or 1

        # Delete existing lines
        for ligne in piece.lignes:
            db.session.delete(ligne)

        # Add new lines
        comptes_ids = request.form.getlist('compte_id[]')
        projets_ids = request.form.getlist('projet_id[]')
        libelles = request.form.getlist('ligne_libelle[]')
        debits = request.form.getlist('debit[]')
        credits = request.form.getlist('credit[]')
        lignes_budget_ids = request.form.getlist('ligne_budget_id[]')

        for i in range(len(comptes_ids)):
            if comptes_ids[i]:
                ligne = LigneEcriture(
                    piece_id=piece.id,
                    compte_id=comptes_ids[i],
                    projet_id=projets_ids[i] if projets_ids[i] else None,
                    libelle=libelles[i] if i < len(libelles) else '',
                    debit=Decimal(debits[i] or 0),
                    credit=Decimal(credits[i] or 0),
                    ligne_budget_id=lignes_budget_ids[i] if i < len(lignes_budget_ids) and lignes_budget_ids[i] else None
                )
                db.session.add(ligne)

        # Validate balance
        db.session.flush()
        if not piece.est_equilibree:
            db.session.rollback()
            flash("Écriture déséquilibrée - Total Débit ≠ Total Crédit.", "danger")
            return redirect(url_for('modifier_ecriture', id=id))

        # Audit log
        new_values = {
            'date_piece': str(piece.date_piece),
            'libelle': piece.libelle,
            'reference': piece.reference
        }
        log_audit('pieces', id, 'UPDATE', old_values=old_values, new_values=new_values)

        db.session.commit()
        flash(f'Écriture {piece.numero} modifiée avec succès.', 'success')
        return redirect(url_for('detail_ecriture', id=id))

    return render_template('comptabilite/ecriture_edit.html',
                           piece=piece,
                           journaux=journaux,
                           exercices=exercices,
                           comptes=comptes,
                           projets=projets,
                           devises=devises,
                           lignes_budget=lignes_budget)


@app.route('/comptabilite/ecritures/<int:id>/valider', methods=['POST'])
@login_required
@role_required(['directeur'])
def valider_ecriture(id):
    """Valider une écriture comptable (Directeur uniquement)"""
    piece = PieceComptable.query.get_or_404(id)

    if piece.valide:
        flash('Cette écriture est déjà validée.', 'warning')
        return redirect(url_for('detail_ecriture', id=id))

    if not piece.est_equilibree:
        flash('Impossible de valider une écriture déséquilibrée.', 'danger')
        return redirect(url_for('detail_ecriture', id=id))

    piece.valide = True
    log_audit('pieces', id, 'VALIDATE', new_values={'valide': True})
    db.session.commit()

    flash(f'Écriture {piece.numero} validée avec succès.', 'success')
    return redirect(url_for('detail_ecriture', id=id))


@app.route('/comptabilite/ecritures/<int:id>/invalider', methods=['POST'])
@login_required
@role_required(['directeur'])
def invalider_ecriture(id):
    """Invalider une écriture comptable (Directeur uniquement)"""
    piece = PieceComptable.query.get_or_404(id)

    if not piece.valide:
        flash('Cette écriture n\'est pas validée.', 'warning')
        return redirect(url_for('detail_ecriture', id=id))

    # Vérifier que l'exercice n'est pas clôturé
    if piece.exercice.cloture:
        flash('Impossible de modifier une écriture d\'un exercice clôturé.', 'danger')
        return redirect(url_for('detail_ecriture', id=id))

    piece.valide = False
    log_audit('pieces', id, 'INVALIDATE', new_values={'valide': False})
    db.session.commit()

    flash(f'Écriture {piece.numero} invalidée.', 'warning')
    return redirect(url_for('detail_ecriture', id=id))


@app.route('/comptabilite/ecritures/valider-lot', methods=['POST'])
@login_required
@role_required(['directeur'])
def valider_lot_ecritures():
    """Valider plusieurs écritures en lot"""
    ids = request.form.getlist('piece_ids')
    count = 0

    for piece_id in ids:
        piece = PieceComptable.query.get(piece_id)
        if piece and not piece.valide and piece.est_equilibree:
            piece.valide = True
            log_audit('pieces', piece.id, 'VALIDATE', new_values={'valide': True})
            count += 1

    db.session.commit()
    flash(f'{count} écriture(s) validée(s) avec succès.', 'success')
    return redirect(url_for('liste_ecritures'))


# =============================================================================
# ROUTES - PIECES JUSTIFICATIVES
# =============================================================================

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/comptabilite/ecritures/<int:id>/pieces-justificatives')
@login_required
def liste_pieces_justificatives(id):
    """Liste des pièces justificatives d'une écriture"""
    piece = PieceComptable.query.get_or_404(id)
    return render_template('comptabilite/pieces_justificatives.html', piece=piece)


@app.route('/comptabilite/ecritures/<int:id>/upload', methods=['POST'])
@login_required
@role_required(['comptable', 'directeur'])
def upload_piece_justificative(id):
    """Upload d'une pièce justificative"""
    piece = PieceComptable.query.get_or_404(id)

    if 'fichier' not in request.files:
        flash('Aucun fichier sélectionné.', 'danger')
        return redirect(url_for('detail_ecriture', id=id))

    fichier = request.files['fichier']

    if fichier.filename == '':
        flash('Aucun fichier sélectionné.', 'danger')
        return redirect(url_for('detail_ecriture', id=id))

    if fichier and allowed_file(fichier.filename):
        # Créer un nom de fichier sécurisé
        filename = secure_filename(fichier.filename)
        # Ajouter un timestamp pour éviter les doublons
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{piece.numero}_{timestamp}_{filename}"

        # Créer le dossier par année/mois si nécessaire
        year_month = piece.date_piece.strftime('%Y/%m')
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], year_month)
        os.makedirs(upload_path, exist_ok=True)

        # Sauvegarder le fichier
        filepath = os.path.join(upload_path, filename)
        fichier.save(filepath)

        # Créer l'enregistrement en base
        pj = PieceJustificative(
            piece_comptable_id=piece.id,
            type_piece=request.form.get('type_piece', 'autre'),
            numero_piece=request.form.get('numero_piece'),
            fichier_path=os.path.join(year_month, filename),
            fichier_nom=fichier.filename,
            date_piece=datetime.strptime(request.form.get('date_piece'), '%Y-%m-%d').date() if request.form.get('date_piece') else None,
            description=request.form.get('description'),
            uploaded_by=current_user.email
        )
        db.session.add(pj)
        log_audit('pieces_justificatives', None, 'CREATE', new_values={'fichier': filename, 'piece_id': piece.id})
        db.session.commit()

        flash('Pièce justificative ajoutée avec succès.', 'success')
    else:
        flash('Type de fichier non autorisé. Formats acceptés: PDF, PNG, JPG, GIF', 'danger')

    return redirect(url_for('detail_ecriture', id=id))


@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Servir les fichiers uploadés"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


@app.route('/pieces-justificatives/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required(['comptable', 'directeur'])
def supprimer_piece_justificative(id):
    """Supprimer une pièce justificative"""
    pj = PieceJustificative.query.get_or_404(id)
    piece_id = pj.piece_comptable_id

    # Supprimer le fichier physique
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], pj.fichier_path)
    if os.path.exists(filepath):
        os.remove(filepath)

    log_audit('pieces_justificatives', id, 'DELETE', old_values={'fichier': pj.fichier_nom})
    db.session.delete(pj)
    db.session.commit()

    flash('Pièce justificative supprimée.', 'success')
    return redirect(url_for('detail_ecriture', id=piece_id))


# =============================================================================
# ROUTES - CLOTURE EXERCICE
# =============================================================================

@app.route('/admin/exercices')
@login_required
@role_required(['directeur'])
def liste_exercices():
    """Liste des exercices comptables"""
    exercices = ExerciceComptable.query.order_by(ExerciceComptable.annee.desc()).all()
    return render_template('admin/exercices.html', exercices=exercices)


@app.route('/admin/exercices/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['directeur'])
def nouvel_exercice():
    """Créer un nouvel exercice comptable"""
    if request.method == 'POST':
        annee = int(request.form.get('annee'))

        if ExerciceComptable.query.filter_by(annee=annee).first():
            flash(f'L\'exercice {annee} existe déjà.', 'danger')
        else:
            exercice = ExerciceComptable(
                annee=annee,
                date_debut=date(annee, 1, 1),
                date_fin=date(annee, 12, 31),
                cloture=False
            )
            db.session.add(exercice)
            log_audit('exercices', None, 'CREATE', new_values={'annee': annee})
            db.session.commit()
            flash(f'Exercice {annee} créé avec succès.', 'success')
            return redirect(url_for('liste_exercices'))

    return render_template('admin/exercice_form.html')


@app.route('/admin/exercices/<int:id>/cloturer', methods=['GET', 'POST'])
@login_required
@role_required(['directeur'])
def cloturer_exercice(id):
    """Clôturer un exercice comptable"""
    exercice = ExerciceComptable.query.get_or_404(id)

    if exercice.cloture:
        flash('Cet exercice est déjà clôturé.', 'warning')
        return redirect(url_for('liste_exercices'))

    # Vérifications avant clôture
    ecritures_non_validees = PieceComptable.query.filter_by(
        exercice_id=id,
        valide=False
    ).count()

    if request.method == 'POST':
        if ecritures_non_validees > 0 and not request.form.get('force'):
            flash(f'Il reste {ecritures_non_validees} écriture(s) non validée(s).', 'danger')
            return redirect(url_for('cloturer_exercice', id=id))

        # Effectuer la clôture
        exercice.cloture = True

        # Calculer le résultat de l'exercice
        # Produits (classe 7) - Charges (classe 6)
        produits = db.session.query(
            db.func.sum(LigneEcriture.credit) - db.func.sum(LigneEcriture.debit)
        ).join(CompteComptable).join(PieceComptable).filter(
            CompteComptable.classe == 7,
            PieceComptable.exercice_id == id
        ).scalar() or 0

        charges = db.session.query(
            db.func.sum(LigneEcriture.debit) - db.func.sum(LigneEcriture.credit)
        ).join(CompteComptable).join(PieceComptable).filter(
            CompteComptable.classe == 6,
            PieceComptable.exercice_id == id
        ).scalar() or 0

        resultat = float(produits) - float(charges)

        log_audit('exercices', id, 'CLOTURE', new_values={
            'cloture': True,
            'resultat': resultat,
            'ecritures_non_validees_ignorees': ecritures_non_validees if request.form.get('force') else 0
        })
        db.session.commit()

        flash(f'Exercice {exercice.annee} clôturé. Résultat: {resultat:,.0f} FCFA', 'success')
        return redirect(url_for('liste_exercices'))

    # Statistiques pour la page de confirmation
    stats = {
        'nb_ecritures': PieceComptable.query.filter_by(exercice_id=id).count(),
        'nb_non_validees': ecritures_non_validees,
        'total_debit': db.session.query(
            db.func.sum(LigneEcriture.debit)
        ).join(PieceComptable).filter(
            PieceComptable.exercice_id == id
        ).scalar() or 0,
        'total_credit': db.session.query(
            db.func.sum(LigneEcriture.credit)
        ).join(PieceComptable).filter(
            PieceComptable.exercice_id == id
        ).scalar() or 0
    }

    return render_template('admin/cloture_exercice.html', exercice=exercice, stats=stats)


# =============================================================================
# ROUTES - MOT DE PASSE OUBLIE
# =============================================================================

import secrets

# Stockage temporaire des tokens (en production, utiliser Redis ou la BD)
password_reset_tokens = {}


@app.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
def mot_de_passe_oublie():
    """Demande de réinitialisation de mot de passe"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = Utilisateur.query.filter_by(email=email).first()

        if user and user.actif:
            # Générer un token
            token = secrets.token_urlsafe(32)
            password_reset_tokens[token] = {
                'user_id': user.id,
                'expires': datetime.utcnow() + timedelta(hours=1)
            }

            # En production, envoyer un email avec le lien
            reset_url = url_for('reinitialiser_mot_de_passe', token=token, _external=True)

            # Pour le développement, afficher le lien
            flash(f'Un lien de réinitialisation a été généré. En production, il serait envoyé par email.', 'info')
            flash(f'Lien (dev): {reset_url}', 'warning')

            log_audit('utilisateurs', user.id, 'PASSWORD_RESET_REQUEST')
            db.session.commit()
        else:
            # Ne pas révéler si l'email existe ou non (sécurité)
            flash('Si cette adresse email est associée à un compte, un lien de réinitialisation a été envoyé.', 'info')

        return redirect(url_for('login'))

    return render_template('auth/mot_de_passe_oublie.html')


@app.route('/reinitialiser-mot-de-passe/<token>', methods=['GET', 'POST'])
def reinitialiser_mot_de_passe(token):
    """Réinitialisation du mot de passe avec token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    # Vérifier le token
    token_data = password_reset_tokens.get(token)
    if not token_data or token_data['expires'] < datetime.utcnow():
        flash('Ce lien de réinitialisation est invalide ou a expiré.', 'danger')
        return redirect(url_for('mot_de_passe_oublie'))

    user = Utilisateur.query.get(token_data['user_id'])
    if not user:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
        elif password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
        else:
            user.password_hash = generate_password_hash(password)
            log_audit('utilisateurs', user.id, 'PASSWORD_RESET_COMPLETE')
            db.session.commit()

            # Supprimer le token utilisé
            del password_reset_tokens[token]

            flash('Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))

    return render_template('auth/reinitialiser_mot_de_passe.html', token=token, email=user.email)


@app.route('/changer-mot-de-passe', methods=['GET', 'POST'])
@login_required
def changer_mot_de_passe():
    """Changer son propre mot de passe"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not check_password_hash(current_user.password_hash, current_password):
            flash('Mot de passe actuel incorrect.', 'danger')
        elif len(new_password) < 6:
            flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'danger')
        elif new_password != confirm_password:
            flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
        else:
            current_user.password_hash = generate_password_hash(new_password)
            log_audit('utilisateurs', current_user.id, 'PASSWORD_CHANGE')
            db.session.commit()
            flash('Votre mot de passe a été changé avec succès.', 'success')
            return redirect(url_for('dashboard'))

    return render_template('auth/changer_mot_de_passe.html')


# =============================================================================
# ROUTES - RAPPORTS
# =============================================================================

@app.route('/rapports')
@login_required
def rapports():
    """Page des rapports"""
    projets = Projet.query.all()
    exercices = ExerciceComptable.query.order_by(ExerciceComptable.annee.desc()).all()
    return render_template('rapports/index.html', projets=projets, exercices=exercices)


@app.route('/rapports/balance')
@login_required
def balance_generale():
    """Balance générale"""
    exercice_id = request.args.get('exercice_id')

    # Requête pour calculer les soldes par compte
    query = db.session.query(
        CompteComptable.numero,
        CompteComptable.intitule,
        db.func.sum(LigneEcriture.debit).label('total_debit'),
        db.func.sum(LigneEcriture.credit).label('total_credit')
    ).join(
        LigneEcriture, LigneEcriture.compte_id == CompteComptable.id
    ).join(
        PieceComptable, PieceComptable.id == LigneEcriture.piece_id
    )

    if exercice_id:
        query = query.filter(PieceComptable.exercice_id == exercice_id)

    query = query.group_by(CompteComptable.id).order_by(CompteComptable.numero)

    balance = []
    for row in query.all():
        debit = float(row.total_debit or 0)
        credit = float(row.total_credit or 0)
        solde_debit = debit - credit if debit > credit else 0
        solde_credit = credit - debit if credit > debit else 0
        balance.append({
            'numero': row.numero,
            'intitule': row.intitule,
            'debit': debit,
            'credit': credit,
            'solde_debit': solde_debit,
            'solde_credit': solde_credit
        })

    exercices = ExerciceComptable.query.order_by(ExerciceComptable.annee.desc()).all()
    return render_template('rapports/balance.html', balance=balance, exercices=exercices, exercice_id=exercice_id)


@app.route('/rapports/projet/<int:id>')
@login_required
def rapport_projet(id):
    """Rapport bailleur - Budget vs Réalisé"""
    projet = Projet.query.get_or_404(id)
    categories = CategorieBudget.query.order_by(CategorieBudget.ordre).all()

    # Organiser les données par catégorie
    rapport = []
    total_prevu = 0
    total_realise = 0

    for cat in categories:
        lignes_cat = [l for l in projet.lignes_budget if l.categorie_id == cat.id]
        if not lignes_cat:
            continue

        cat_data = {
            'categorie': cat,
            'lignes': [],
            'total_prevu': 0,
            'total_realise': 0
        }

        for ligne in lignes_cat:
            # SYSCOHADA: Pour les charges (classe 6), seuls les débits comptent comme dépenses réalisées
            realise = db.session.query(
                db.func.sum(LigneEcriture.debit)
            ).join(CompteComptable).filter(
                (LigneEcriture.ligne_budget_id == ligne.id) &
                (CompteComptable.classe == 6)
            ).scalar() or 0
            realise = float(realise)
            prevu = float(ligne.montant_prevu or 0)

            cat_data['lignes'].append({
                'ligne': ligne,
                'prevu': prevu,
                'realise': realise,
                'ecart': prevu - realise,
                'taux': (realise / prevu * 100) if prevu > 0 else 0
            })
            cat_data['total_prevu'] += prevu
            cat_data['total_realise'] += realise

        total_prevu += cat_data['total_prevu']
        total_realise += cat_data['total_realise']
        rapport.append(cat_data)

    return render_template('rapports/projet.html',
                         projet=projet,
                         rapport=rapport,
                         total_prevu=total_prevu,
                         total_realise=total_realise)


@app.route('/rapports/projet/<int:id>/pdf')
@login_required
def export_projet_pdf(id):
    """Export PDF du rapport bailleur"""
    try:
        from weasyprint import HTML
    except ImportError:
        flash("WeasyPrint n'est pas installé. Utilisez: pip install weasyprint", "danger")
        return redirect(url_for('rapport_projet', id=id))

    projet = Projet.query.get_or_404(id)
    categories = CategorieBudget.query.order_by(CategorieBudget.ordre).all()

    # Mêmes calculs que rapport_projet
    rapport = []
    total_prevu = 0
    total_realise = 0

    for cat in categories:
        lignes_cat = [l for l in projet.lignes_budget if l.categorie_id == cat.id]
        if not lignes_cat:
            continue

        cat_data = {
            'categorie': cat,
            'lignes': [],
            'total_prevu': 0,
            'total_realise': 0
        }

        for ligne in lignes_cat:
            realise = db.session.query(
                db.func.sum(LigneEcriture.debit)
            ).join(CompteComptable).filter(
                (LigneEcriture.ligne_budget_id == ligne.id) &
                (CompteComptable.classe == 6)
            ).scalar() or 0
            realise = float(realise)
            prevu = float(ligne.montant_prevu or 0)

            cat_data['lignes'].append({
                'ligne': ligne,
                'prevu': prevu,
                'realise': realise,
                'ecart': prevu - realise,
                'taux': (realise / prevu * 100) if prevu > 0 else 0
            })
            cat_data['total_prevu'] += prevu
            cat_data['total_realise'] += realise

        total_prevu += cat_data['total_prevu']
        total_realise += cat_data['total_realise']
        rapport.append(cat_data)

    html = render_template('rapports/projet_pdf.html',
                          projet=projet,
                          rapport=rapport,
                          total_prevu=total_prevu,
                          total_realise=total_realise,
                          date_generation=datetime.now())

    pdf = HTML(string=html, base_url=request.host_url).write_pdf()

    return Response(pdf,
                   mimetype='application/pdf',
                   headers={'Content-Disposition': f'attachment; filename=rapport_{projet.code}_{date.today()}.pdf'})


@app.route('/rapports/projet/<int:id>/excel')
@login_required
def export_projet_excel(id):
    """Export Excel du rapport bailleur"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from io import BytesIO
    except ImportError:
        flash("openpyxl n'est pas installé. Utilisez: pip install openpyxl", "danger")
        return redirect(url_for('rapport_projet', id=id))

    projet = Projet.query.get_or_404(id)
    categories = CategorieBudget.query.order_by(CategorieBudget.ordre).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Rapport Budget"

    # Styles
    header_font = Font(bold=True, size=12)
    title_font = Font(bold=True, size=14)
    cat_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # En-tête
    ws.merge_cells('A1:F1')
    ws['A1'] = f"RAPPORT BAILLEUR - {projet.code}"
    ws['A1'].font = title_font

    ws['A2'] = f"Projet: {projet.nom}"
    ws['A3'] = f"Bailleur: {projet.bailleur.nom if projet.bailleur else 'N/A'}"
    ws['A4'] = f"Date: {date.today().strftime('%d/%m/%Y')}"

    # En-têtes tableau
    row = 6
    headers = ['Code', 'Description', 'Budget prévu', 'Réalisé', 'Écart', 'Taux (%)']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.border = thin_border

    row = 7
    total_prevu = 0
    total_realise = 0

    for cat in categories:
        lignes_cat = [l for l in projet.lignes_budget if l.categorie_id == cat.id]
        if not lignes_cat:
            continue

        # Ligne catégorie
        ws.cell(row=row, column=1, value=cat.nom).font = Font(bold=True)
        ws.cell(row=row, column=1).fill = cat_fill
        for col in range(1, 7):
            ws.cell(row=row, column=col).fill = cat_fill
            ws.cell(row=row, column=col).border = thin_border
        row += 1

        cat_prevu = 0
        cat_realise = 0

        for ligne in lignes_cat:
            realise = db.session.query(
                db.func.sum(LigneEcriture.debit)
            ).join(CompteComptable).filter(
                (LigneEcriture.ligne_budget_id == ligne.id) &
                (CompteComptable.classe == 6)
            ).scalar() or 0
            realise = float(realise)
            prevu = float(ligne.montant_prevu or 0)
            taux = (realise / prevu * 100) if prevu > 0 else 0

            ws.cell(row=row, column=1, value=ligne.code).border = thin_border
            ws.cell(row=row, column=2, value=ligne.intitule).border = thin_border
            ws.cell(row=row, column=3, value=prevu).border = thin_border
            ws.cell(row=row, column=3).number_format = '#,##0'
            ws.cell(row=row, column=4, value=realise).border = thin_border
            ws.cell(row=row, column=4).number_format = '#,##0'
            ws.cell(row=row, column=5, value=prevu - realise).border = thin_border
            ws.cell(row=row, column=5).number_format = '#,##0'
            ws.cell(row=row, column=6, value=taux).border = thin_border
            ws.cell(row=row, column=6).number_format = '0.0%'

            cat_prevu += prevu
            cat_realise += realise
            row += 1

        total_prevu += cat_prevu
        total_realise += cat_realise

    # Total général
    row += 1
    ws.cell(row=row, column=1, value="TOTAL GÉNÉRAL").font = Font(bold=True)
    ws.cell(row=row, column=3, value=total_prevu).font = Font(bold=True)
    ws.cell(row=row, column=3).number_format = '#,##0'
    ws.cell(row=row, column=4, value=total_realise).font = Font(bold=True)
    ws.cell(row=row, column=4).number_format = '#,##0'
    ws.cell(row=row, column=5, value=total_prevu - total_realise).font = Font(bold=True)
    ws.cell(row=row, column=5).number_format = '#,##0'
    if total_prevu > 0:
        ws.cell(row=row, column=6, value=total_realise / total_prevu).font = Font(bold=True)
        ws.cell(row=row, column=6).number_format = '0.0%'

    # Ajuster largeur colonnes
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 12

    # Sauvegarder
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(output.read(),
                   mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                   headers={'Content-Disposition': f'attachment; filename=rapport_{projet.code}_{date.today()}.xlsx'})


@app.route('/rapports/reconciliation')
@login_required
def reconciliation_analytique():
    """Réconciliation Analytique ↔ Comptabilité Générale"""
    exercice_id = request.args.get('exercice_id')
    exercices = ExerciceComptable.query.order_by(ExerciceComptable.annee.desc()).all()

    if not exercice_id and exercices:
        exercice_id = exercices[0].id

    # Total charges classe 6 (comptabilité générale)
    total_compta_generale = db.session.query(
        db.func.sum(LigneEcriture.debit)
    ).join(CompteComptable).join(PieceComptable).filter(
        CompteComptable.classe == 6
    )
    if exercice_id:
        total_compta_generale = total_compta_generale.filter(
            PieceComptable.exercice_id == exercice_id
        )
    total_compta_generale = float(total_compta_generale.scalar() or 0)

    # Total par projet (analytique)
    projets_data = []
    total_analytique = 0

    for projet in Projet.query.all():
        projet_total = 0
        for ligne in projet.lignes_budget:
            realise = db.session.query(
                db.func.sum(LigneEcriture.debit)
            ).join(CompteComptable).filter(
                (LigneEcriture.ligne_budget_id == ligne.id) &
                (CompteComptable.classe == 6)
            ).scalar() or 0
            projet_total += float(realise)

        if projet_total > 0:
            projets_data.append({
                'projet': projet,
                'total': projet_total
            })
            total_analytique += projet_total

    # Écart de réconciliation
    ecart = total_compta_generale - total_analytique

    # Charges non imputées (sans ligne_budget_id)
    charges_non_imputees = db.session.query(
        db.func.sum(LigneEcriture.debit)
    ).join(CompteComptable).filter(
        CompteComptable.classe == 6,
        LigneEcriture.ligne_budget_id == None
    ).scalar() or 0

    return render_template('rapports/reconciliation.html',
                          exercices=exercices,
                          exercice_id=exercice_id,
                          total_compta_generale=total_compta_generale,
                          total_analytique=total_analytique,
                          projets_data=projets_data,
                          ecart=ecart,
                          charges_non_imputees=float(charges_non_imputees))


@app.route('/rapports/etats-financiers')
@login_required
def etats_financiers():
    """États financiers SYSCOHADA"""
    exercice_id = request.args.get('exercice_id')
    exercices = ExerciceComptable.query.order_by(ExerciceComptable.annee.desc()).all()

    if not exercice_id and exercices:
        exercice_id = exercices[0].id

    # Calculer Actif (classes 2-5)
    actif = calculer_soldes_classe([2, 3, 4, 5], exercice_id, 'actif')

    # Calculer Passif (classes 1, 4)
    passif = calculer_soldes_classe([1, 4], exercice_id, 'passif')

    # Calculer Charges (classe 6)
    charges = calculer_soldes_classe([6], exercice_id)

    # Calculer Produits (classe 7)
    produits = calculer_soldes_classe([7], exercice_id)

    resultat = sum(p['solde'] for p in produits) - sum(c['solde'] for c in charges)

    return render_template('rapports/etats_financiers.html',
                         actif=actif,
                         passif=passif,
                         charges=charges,
                         produits=produits,
                         resultat=resultat,
                         exercices=exercices,
                         exercice_id=exercice_id)


def calculer_soldes_classe(classes, exercice_id=None, type_solde=None):
    """Calculer les soldes pour une classe de comptes"""
    query = db.session.query(
        CompteComptable.numero,
        CompteComptable.intitule,
        db.func.sum(LigneEcriture.debit).label('total_debit'),
        db.func.sum(LigneEcriture.credit).label('total_credit')
    ).join(
        LigneEcriture, LigneEcriture.compte_id == CompteComptable.id
    ).join(
        PieceComptable, PieceComptable.id == LigneEcriture.piece_id
    ).filter(
        CompteComptable.classe.in_(classes)
    )

    if exercice_id:
        query = query.filter(PieceComptable.exercice_id == exercice_id)

    query = query.group_by(CompteComptable.id).order_by(CompteComptable.numero)

    resultats = []
    for row in query.all():
        debit = float(row.total_debit or 0)
        credit = float(row.total_credit or 0)

        if type_solde == 'actif':
            solde = debit - credit
        elif type_solde == 'passif':
            solde = credit - debit
        else:
            solde = debit - credit

        if abs(solde) > 0.01:
            resultats.append({
                'numero': row.numero,
                'intitule': row.intitule,
                'solde': solde
            })

    return resultats


# =============================================================================
# INITIALISATION BASE DE DONNEES
# =============================================================================

def init_db():
    """Initialiser la base de données avec les données de base"""
    db.create_all()

    # Vérifier si déjà initialisé
    if Devise.query.first():
        return

    # Devises
    devises = [
        Devise(code='XOF', nom='Franc CFA', symbole='FCFA', taux_base=1),
        Devise(code='USD', nom='Dollar US', symbole='$', taux_base=600),
        Devise(code='EUR', nom='Euro', symbole='€', taux_base=655),
        Devise(code='CHF', nom='Franc Suisse', symbole='CHF', taux_base=700),
    ]
    db.session.add_all(devises)

    # Exercice comptable
    exercice = ExerciceComptable(
        annee=2025,
        date_debut=date(2025, 1, 1),
        date_fin=date(2025, 12, 31)
    )
    db.session.add(exercice)

    # Plan comptable SYSCOHADA pour ONG - Conforme aux normes
    comptes = [
        # Classe 1 - Capitaux propres (compte 19 supprimé - non standard SYSCOHADA)
        CompteComptable(numero='10', intitule='Capital', classe=1, type_compte='passif'),
        CompteComptable(numero='101', intitule='Capital social', classe=1, type_compte='passif'),
        CompteComptable(numero='11', intitule='Réserves', classe=1, type_compte='passif'),
        CompteComptable(numero='12', intitule='Report à nouveau', classe=1, type_compte='passif'),
        CompteComptable(numero='13', intitule='Résultat de l\'exercice', classe=1, type_compte='passif'),
        CompteComptable(numero='14', intitule='Subventions d\'investissement', classe=1, type_compte='passif'),
        CompteComptable(numero='15', intitule='Provisions réglementées', classe=1, type_compte='passif'),
        CompteComptable(numero='16', intitule='Emprunts et dettes', classe=1, type_compte='passif'),
        CompteComptable(numero='17', intitule='Dettes de crédit-bail', classe=1, type_compte='passif'),
        CompteComptable(numero='18', intitule='Dettes liées à des participations', classe=1, type_compte='passif'),

        # Classe 2 - Immobilisations
        CompteComptable(numero='21', intitule='Immobilisations incorporelles', classe=2, type_compte='actif'),
        CompteComptable(numero='211', intitule='Frais de développement', classe=2, type_compte='actif'),
        CompteComptable(numero='212', intitule='Brevets, licences', classe=2, type_compte='actif'),
        CompteComptable(numero='22', intitule='Terrains', classe=2, type_compte='actif'),
        CompteComptable(numero='23', intitule='Bâtiments', classe=2, type_compte='actif'),
        CompteComptable(numero='24', intitule='Matériel et outillage', classe=2, type_compte='actif'),
        CompteComptable(numero='241', intitule='Matériel industriel', classe=2, type_compte='actif'),
        CompteComptable(numero='244', intitule='Matériel informatique', classe=2, type_compte='actif'),
        CompteComptable(numero='245', intitule='Matériel de transport', classe=2, type_compte='actif'),
        CompteComptable(numero='246', intitule='Mobilier de bureau', classe=2, type_compte='actif'),
        CompteComptable(numero='28', intitule='Amortissements', classe=2, type_compte='actif'),
        CompteComptable(numero='281', intitule='Amort. immobilisations incorporelles', classe=2, type_compte='actif'),
        CompteComptable(numero='284', intitule='Amort. matériel', classe=2, type_compte='actif'),

        # Classe 3 - Stocks
        CompteComptable(numero='31', intitule='Stocks de matières premières', classe=3, type_compte='actif'),
        CompteComptable(numero='32', intitule='Stocks fournitures', classe=3, type_compte='actif'),
        CompteComptable(numero='38', intitule='Stocks en cours de route', classe=3, type_compte='actif'),
        CompteComptable(numero='39', intitule='Dépréciations des stocks', classe=3, type_compte='actif'),

        # Classe 4 - Tiers
        CompteComptable(numero='40', intitule='Fournisseurs', classe=4, type_compte='passif'),
        CompteComptable(numero='401', intitule='Fournisseurs locaux', classe=4, type_compte='passif'),
        CompteComptable(numero='402', intitule='Fournisseurs étrangers', classe=4, type_compte='passif'),
        CompteComptable(numero='41', intitule='Clients et bailleurs', classe=4, type_compte='actif'),
        CompteComptable(numero='411', intitule='Bailleurs de fonds', classe=4, type_compte='actif'),
        # Sous-comptes par bailleur
        CompteComptable(numero='4111', intitule='Bailleur - Nitidae', classe=4, type_compte='actif'),
        CompteComptable(numero='4112', intitule='Bailleur - GIUB', classe=4, type_compte='actif'),
        CompteComptable(numero='4113', intitule='Bailleur - AFD', classe=4, type_compte='actif'),
        CompteComptable(numero='4114', intitule='Bailleur - Union Européenne', classe=4, type_compte='actif'),
        CompteComptable(numero='4119', intitule='Autres bailleurs', classe=4, type_compte='actif'),
        CompteComptable(numero='42', intitule='Personnel', classe=4, type_compte='passif'),
        CompteComptable(numero='421', intitule='Personnel - Rémunérations dues', classe=4, type_compte='passif'),
        CompteComptable(numero='422', intitule='Personnel - Avances et acomptes', classe=4, type_compte='actif'),
        CompteComptable(numero='43', intitule='Organismes sociaux', classe=4, type_compte='passif'),
        CompteComptable(numero='431', intitule='Sécurité sociale (CSS)', classe=4, type_compte='passif'),
        CompteComptable(numero='432', intitule='Caisse de retraite (IPRES)', classe=4, type_compte='passif'),
        CompteComptable(numero='433', intitule='Mutuelles santé (IPM)', classe=4, type_compte='passif'),
        CompteComptable(numero='44', intitule='État et collectivités', classe=4, type_compte='passif'),
        CompteComptable(numero='441', intitule='État - Impôt sur les bénéfices', classe=4, type_compte='passif'),
        CompteComptable(numero='442', intitule='État - TVA collectée', classe=4, type_compte='passif'),
        CompteComptable(numero='443', intitule='État - TVA déductible', classe=4, type_compte='actif'),
        CompteComptable(numero='444', intitule='État - Retenues à la source (BRS)', classe=4, type_compte='passif'),
        CompteComptable(numero='445', intitule='État - IRVM/IRCM', classe=4, type_compte='passif'),
        CompteComptable(numero='446', intitule='État - Patente et CFCE', classe=4, type_compte='passif'),
        CompteComptable(numero='47', intitule='Comptes transitoires', classe=4, type_compte='actif'),
        CompteComptable(numero='471', intitule='Débiteurs divers', classe=4, type_compte='actif'),
        CompteComptable(numero='472', intitule='Créditeurs divers', classe=4, type_compte='passif'),
        CompteComptable(numero='48', intitule='Charges/Produits constatés d\'avance', classe=4, type_compte='passif'),

        # Classe 5 - Trésorerie
        CompteComptable(numero='52', intitule='Banques', classe=5, type_compte='actif'),
        CompteComptable(numero='521', intitule='Banque compte principal', classe=5, type_compte='actif'),
        # Sous-comptes par devise
        CompteComptable(numero='5211', intitule='Banque XOF', classe=5, type_compte='actif'),
        CompteComptable(numero='5212', intitule='Banque USD', classe=5, type_compte='actif'),
        CompteComptable(numero='5213', intitule='Banque CHF', classe=5, type_compte='actif'),
        CompteComptable(numero='5214', intitule='Banque EUR', classe=5, type_compte='actif'),
        CompteComptable(numero='522', intitule='Banque compte projet', classe=5, type_compte='actif'),
        CompteComptable(numero='53', intitule='Établissements financiers', classe=5, type_compte='actif'),
        CompteComptable(numero='57', intitule='Caisse', classe=5, type_compte='actif'),
        CompteComptable(numero='571', intitule='Caisse siège', classe=5, type_compte='actif'),
        CompteComptable(numero='572', intitule='Caisse terrain', classe=5, type_compte='actif'),
        CompteComptable(numero='58', intitule='Virements internes', classe=5, type_compte='actif'),

        # Classe 6 - Charges
        CompteComptable(numero='60', intitule='Achats', classe=6, type_compte='charge'),
        CompteComptable(numero='601', intitule='Achats fournitures bureau', classe=6, type_compte='charge'),
        CompteComptable(numero='602', intitule='Achats fournitures terrain', classe=6, type_compte='charge'),
        CompteComptable(numero='603', intitule='Achats consommables', classe=6, type_compte='charge'),
        CompteComptable(numero='604', intitule='Achats matières premières', classe=6, type_compte='charge'),
        CompteComptable(numero='605', intitule='Achats équipements', classe=6, type_compte='charge'),
        CompteComptable(numero='61', intitule='Transports', classe=6, type_compte='charge'),
        CompteComptable(numero='611', intitule='Transport personnel', classe=6, type_compte='charge'),
        CompteComptable(numero='612', intitule='Transport matériel', classe=6, type_compte='charge'),
        CompteComptable(numero='613', intitule='Transport aérien', classe=6, type_compte='charge'),
        CompteComptable(numero='62', intitule='Services extérieurs', classe=6, type_compte='charge'),
        CompteComptable(numero='621', intitule='Locations immobilières', classe=6, type_compte='charge'),
        CompteComptable(numero='622', intitule='Locations matériel/véhicules', classe=6, type_compte='charge'),
        CompteComptable(numero='623', intitule='Entretien et réparations', classe=6, type_compte='charge'),
        CompteComptable(numero='624', intitule='Honoraires et consultants', classe=6, type_compte='charge'),
        CompteComptable(numero='625', intitule='Déplacements et missions', classe=6, type_compte='charge'),
        CompteComptable(numero='6251', intitule='Frais de déplacement local', classe=6, type_compte='charge'),
        CompteComptable(numero='6252', intitule='Frais de mission international', classe=6, type_compte='charge'),
        CompteComptable(numero='6253', intitule='Hébergement', classe=6, type_compte='charge'),
        CompteComptable(numero='6254', intitule='Per diem', classe=6, type_compte='charge'),
        CompteComptable(numero='626', intitule='Télécommunications', classe=6, type_compte='charge'),
        CompteComptable(numero='6261', intitule='Téléphone et internet', classe=6, type_compte='charge'),
        CompteComptable(numero='6262', intitule='Courrier et affranchissement', classe=6, type_compte='charge'),
        CompteComptable(numero='627', intitule='Services bancaires', classe=6, type_compte='charge'),
        CompteComptable(numero='628', intitule='Assurances', classe=6, type_compte='charge'),
        CompteComptable(numero='63', intitule='Autres services', classe=6, type_compte='charge'),
        CompteComptable(numero='631', intitule='Formation', classe=6, type_compte='charge'),
        CompteComptable(numero='632', intitule='Ateliers et réunions', classe=6, type_compte='charge'),
        CompteComptable(numero='633', intitule='Communication et publication', classe=6, type_compte='charge'),
        CompteComptable(numero='634', intitule='Études et recherches', classe=6, type_compte='charge'),
        CompteComptable(numero='635', intitule='Sous-traitance', classe=6, type_compte='charge'),
        # Classe 64 - Impôts et taxes (détaillé pour le Sénégal)
        CompteComptable(numero='64', intitule='Impôts et taxes', classe=6, type_compte='charge'),
        CompteComptable(numero='641', intitule='Patente', classe=6, type_compte='charge'),
        CompteComptable(numero='642', intitule='CFCE (Contribution Foncière)', classe=6, type_compte='charge'),
        CompteComptable(numero='643', intitule='Taxes sur véhicules', classe=6, type_compte='charge'),
        CompteComptable(numero='644', intitule='TVA non récupérable', classe=6, type_compte='charge'),
        CompteComptable(numero='645', intitule='Droits d\'enregistrement', classe=6, type_compte='charge'),
        CompteComptable(numero='646', intitule='Droits de douane', classe=6, type_compte='charge'),
        CompteComptable(numero='647', intitule='Autres impôts et taxes', classe=6, type_compte='charge'),
        CompteComptable(numero='65', intitule='Autres charges', classe=6, type_compte='charge'),
        CompteComptable(numero='651', intitule='Pertes sur créances', classe=6, type_compte='charge'),
        CompteComptable(numero='652', intitule='Pénalités et amendes', classe=6, type_compte='charge'),
        CompteComptable(numero='66', intitule='Charges de personnel', classe=6, type_compte='charge'),
        CompteComptable(numero='661', intitule='Salaires bruts', classe=6, type_compte='charge'),
        CompteComptable(numero='6611', intitule='Salaires personnel permanent', classe=6, type_compte='charge'),
        CompteComptable(numero='6612', intitule='Salaires personnel projet', classe=6, type_compte='charge'),
        CompteComptable(numero='662', intitule='Indemnités et primes', classe=6, type_compte='charge'),
        CompteComptable(numero='6621', intitule='Indemnité de logement', classe=6, type_compte='charge'),
        CompteComptable(numero='6622', intitule='Indemnité de transport', classe=6, type_compte='charge'),
        CompteComptable(numero='6623', intitule='Prime de rendement', classe=6, type_compte='charge'),
        CompteComptable(numero='663', intitule='Charges sociales patronales', classe=6, type_compte='charge'),
        CompteComptable(numero='6631', intitule='Cotisations CSS (employeur)', classe=6, type_compte='charge'),
        CompteComptable(numero='6632', intitule='Cotisations IPRES (employeur)', classe=6, type_compte='charge'),
        CompteComptable(numero='6633', intitule='Cotisations IPM (employeur)', classe=6, type_compte='charge'),
        CompteComptable(numero='664', intitule='Charges sociales salariales', classe=6, type_compte='charge'),
        CompteComptable(numero='67', intitule='Charges financières', classe=6, type_compte='charge'),
        CompteComptable(numero='671', intitule='Intérêts des emprunts', classe=6, type_compte='charge'),
        CompteComptable(numero='672', intitule='Pertes de change', classe=6, type_compte='charge'),
        CompteComptable(numero='68', intitule='Dotations amortissements et provisions', classe=6, type_compte='charge'),
        CompteComptable(numero='681', intitule='Dotations aux amortissements', classe=6, type_compte='charge'),
        CompteComptable(numero='682', intitule='Dotations aux provisions', classe=6, type_compte='charge'),
        CompteComptable(numero='69', intitule='Charges exceptionnelles', classe=6, type_compte='charge'),

        # Classe 7 - Produits
        CompteComptable(numero='70', intitule='Ventes et prestations', classe=7, type_compte='produit'),
        CompteComptable(numero='701', intitule='Ventes de services', classe=7, type_compte='produit'),
        CompteComptable(numero='702', intitule='Prestations de conseil', classe=7, type_compte='produit'),
        CompteComptable(numero='74', intitule='Subventions d\'exploitation', classe=7, type_compte='produit'),
        CompteComptable(numero='741', intitule='Subventions projets', classe=7, type_compte='produit'),
        # Sous-comptes par projet
        CompteComptable(numero='7411', intitule='Subvention projet LED', classe=7, type_compte='produit'),
        CompteComptable(numero='7412', intitule='Subvention projet SOR4D', classe=7, type_compte='produit'),
        CompteComptable(numero='7413', intitule='Subvention projet AMSANA', classe=7, type_compte='produit'),
        CompteComptable(numero='7419', intitule='Subventions autres projets', classe=7, type_compte='produit'),
        CompteComptable(numero='742', intitule='Subventions fonctionnement', classe=7, type_compte='produit'),
        CompteComptable(numero='75', intitule='Autres produits', classe=7, type_compte='produit'),
        CompteComptable(numero='751', intitule='Produits accessoires', classe=7, type_compte='produit'),
        CompteComptable(numero='76', intitule='Produits financiers', classe=7, type_compte='produit'),
        CompteComptable(numero='761', intitule='Intérêts bancaires', classe=7, type_compte='produit'),
        CompteComptable(numero='762', intitule='Gains de change', classe=7, type_compte='produit'),
        CompteComptable(numero='77', intitule='Produits exceptionnels', classe=7, type_compte='produit'),
        CompteComptable(numero='78', intitule='Reprises amortissements et provisions', classe=7, type_compte='produit'),
        CompteComptable(numero='79', intitule='Transferts de charges', classe=7, type_compte='produit'),
    ]
    db.session.add_all(comptes)

    # Journaux comptables
    journaux = [
        Journal(code='AC', nom='Journal des Achats', type_journal='achat'),
        Journal(code='BQ', nom='Journal de Banque', type_journal='banque'),
        Journal(code='CA', nom='Journal de Caisse', type_journal='caisse'),
        Journal(code='OD', nom='Opérations Diverses', type_journal='od'),
        Journal(code='SAL', nom='Journal des Salaires', type_journal='od'),
    ]
    db.session.add_all(journaux)

    # Catégories budgétaires (basées sur vos budgets)
    categories = [
        CategorieBudget(code='LABOR', nom='Personnel / Salaires', ordre=1),
        CategorieBudget(code='TRAVEL', nom='Voyages et Déplacements', ordre=2),
        CategorieBudget(code='SUPPLIES', nom='Fournitures et Équipements', ordre=3),
        CategorieBudget(code='PROGRAM', nom='Coûts Programmes / Activités', ordre=4),
        CategorieBudget(code='ADMIN', nom='Frais Administratifs', ordre=5),
        CategorieBudget(code='OVERHEAD', nom='Frais Généraux / Indirect', ordre=6),
        CategorieBudget(code='AUDIT', nom='Audit et Évaluation', ordre=7),
    ]
    db.session.add_all(categories)

    # Créer un utilisateur administrateur par défaut
    admin = Utilisateur(
        email='admin@creates.sn',
        nom='Administrateur',
        prenom='CREATES',
        password_hash=generate_password_hash('admin123'),  # Mot de passe à changer!
        role='directeur',
        actif=True,
        created_by='system'
    )
    db.session.add(admin)

    db.session.commit()
    print("Base de données initialisée avec succès!")
    print("Utilisateur admin créé: admin@creates.sn / admin123 (à changer!)")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=5000)
