# Tutoriel Dashboard Consultation Verso-Vet

## Vue d'ensemble

Le dashboard Consultation Verso-Vet permet de gérer les demandes de consultation vétérinaire soumises via le formulaire en ligne verso-vet.com.

### Accès
- **URL**: http://10.0.0.44:8092
- **Port**: 8092

---

## 1. Interface Principale

### Barre de Recherche
La barre de recherche en haut du dashboard permet de filtrer les consultations par:
- **Nom de l'animal** (ex: "Luna", "Milu")
- **Nom du propriétaire** (ex: "Martin", "Dupont")

**Utilisation**: Tapez un terme et appuyez sur Entrée pour filtrer.

### Filtres par Statut
Quatre boutons de statut permettent de filtrer les consultations:

1. **Pending** (Orange) - Demandes reçues mais non traitées
2. **Received** (Bleu) - Demandes accusées de réception
3. **Integrated** (Vert) - Demandes intégrées dans l'ERP
4. **Rejected** (Rouge) - Demandes rejetées

Cliquez sur un bouton pour afficher uniquement les consultations avec ce statut.

### Tableau des Consultations
Le tableau affiche les colonnes suivantes:

| Colonne | Description |
|---------|------------|
| **ID** | Numéro unique de la consultation |
| **Animal** | Nom de l'animal |
| **Propriétaire** | Nom du propriétaire |
| **Statut** | Statut actuel (Pending/Received/Integrated/Rejected) |
| **Soumis** | Date et heure de soumission |
| **Fichiers** | Nombre de documents joints |
| **Actions** | Boutons pour interagir avec la consultation |

---

## 2. Actions sur une Consultation

Pour chaque consultation, trois actions sont disponibles:

### 2.1 View (👁️ Voir les détails)
**Objective**: Afficher les informations complètes et les documents de la consultation.

**Étapes**:
1. Cliquez sur le bouton **View** de la ligne
2. Une modale s'ouvre avec:
   - Les données du formulaire (animal, propriétaire, motif, spécialité, etc.)
   - La liste des documents joints
   - Un lien de téléchargement pour chaque document

**Exemple**: Voir la photo du patient et le formulaire d'histoire médicale avant intégration.

### 2.2 Integrate (🔗 Intégrer dans l'ERP)
**Objective**: Intégrer la consultation et le patient dans l'ERP VetoPartner.

**Trois cas d'usage**:

#### Cas 1: Animal existant dans l'ERP
1. Cliquez sur **Integrate**
2. La modale d'intégration s'ouvre
3. **Section 1 - Dossiers existants**: Effectuez une recherche (ex: "Luna Martin")
4. Les résultats affichent les animaux correspondants
5. Cliquez sur **[Sélectionner]** à côté de l'animal existant
6. Cliquez sur **[Intégrer à l'ERP]** en bas
7. ✅ La consultation est liée à cet animal

#### Cas 2: Propriétaire existant + nouvel animal
1. Cliquez sur **Integrate**
2. La modale s'ouvre
3. **Section 1 - Dossiers existants**: Recherchez le propriétaire (ex: "Martin")
4. Vous verrez la liste des homonymes détectés
5. Cliquez sur **[Sélectionner]** à côté du propriétaire correct
6. **Section 3 - Animal**: Le formulaire animal s'affiche (pré-rempli)
7. Confirmez les données (nom, espèce, race)
8. Cliquez sur **[Confirmer l'animal ▶]**
9. Cliquez sur **[Intégrer à l'ERP]**
10. ✅ Un nouvel animal est créé pour le propriétaire existant

#### Cas 3: Nouveau propriétaire + nouvel animal
1. Cliquez sur **Integrate**
2. **Section 2 - Propriétaire**: Remplissez le formulaire avec les données du propriétaire
3. Cliquez sur **[Utiliser ce propriétaire ▶]**
4. **Section 3 - Animal**: Remplissez le formulaire animal (pré-rempli avec les données du formulaire)
5. Cliquez sur **[Confirmer l'animal ▶]**
6. Cliquez sur **[Intégrer à l'ERP]**
7. ✅ Un nouveau propriétaire ET un nouvel animal sont créés

**Notes**:
- Le bouton **[Intégrer à l'ERP]** n'est actif (cliquable) que lorsqu'un animal est prêt
- Les données du formulaire de consultation pré-remplissent les champs animal (nom, espèce, race)
- Les homonymes détectés permettent de vérifier qu'on ne crée pas de doublons

### 2.3 Delete (🗑️ Supprimer)
**Objective**: Supprimer la consultation de la base de données.

**Étapes**:
1. Cliquez sur le bouton **Delete**
2. La consultation est marquée comme "deleted" dans la base
3. L'email correspondant est supprimé de la boîte mailbox (IMAP)

**Attention**: Cette action est irréversible.

---

## 3. Flux de Travail Complet

### Étape 1: Réception de la Demande
1. Un propriétaire remplit le formulaire sur verso-vet.com
2. Un email avec pièces jointes est envoyé à consultations@verso-vet.com
3. Le système IMAP (monitoring automatique) récupère l'email
4. La consultation apparaît dans le dashboard avec le statut **Pending**

### Étape 2: Vérification (View)
1. Cliquez sur **View** pour voir les détails
2. Vérifiez les données du formulaire (animal, propriétaire, motif)
3. Consultez les documents joints (radios, analyses, photos, etc.)

### Étape 3: Recherche du Patient
1. Cliquez sur **Integrate**
2. **Section 1**: Recherchez si l'animal existe déjà dans l'ERP
   - Écrivez "Luna Martin" par exemple
   - Cliquez sur **[Rechercher]**
   - Les résultats affichent les matches

### Étape 4: Gestion du Propriétaire
**Si l'animal existe**: Pas besoin de cette étape, intégrez directement.

**Si l'animal n'existe pas**:
- **Propriétaire existant**: Cliquez sur le propriétaire dans la liste homonymes, puis confirmer l'animal
- **Propriétaire nouveau**: Remplissez le formulaire Propriétaire, cliquez "Utiliser ce propriétaire", puis l'animal

### Étape 5: Création de l'Animal (si nécessaire)
1. Remplissez le formulaire Animal (pré-rempli)
2. Vérifiez: nom, espèce, race
3. Cliquez sur **[Confirmer l'animal ▶]**

### Étape 6: Intégration dans l'ERP
1. Cliquez sur **[Intégrer à l'ERP]** (bouton en bas de modale)
2. Le système crée la consultation dans VetoPartner
3. Les documents sont uploadés automatiquement
4. Le statut passe à **Integrated** ✅

---

## 4. Gestion des Documents

### Affichage des Documents
- Dans la modale **View**, les documents sont listés avec leur nom et taille
- Cliquez sur le lien pour télécharger

### Suppression des Documents
- Les documents sont supprimés automatiquement après intégration dans l'ERP
- Si vous supprimez une consultation avant intégration, les documents locaux sont conservés

### Types de Documents Acceptés
- Images: JPG, PNG, GIF
- Documents: PDF, DOC, DOCX
- Autres: Taille max par fichier généralement 50MB

---

## 5. Statuts et Workflows

### Statuts disponibles

```
PENDING
  ↓ (après réception par le système)
RECEIVED
  ↓ (après intégration dans l'ERP)
INTEGRATED
  ↓ (optionnel, si rejet)
REJECTED
```

### Significations

| Statut | Couleur | Sens |
|--------|--------|------|
| **Pending** | Orange | Demande reçue mais non encore traitée par l'assistant |
| **Received** | Bleu | Demande reçue et en cours de traitement |
| **Integrated** | Vert | Demande intégrée dans l'ERP VetoPartner |
| **Rejected** | Rouge | Demande rejetée (données incomplètes, patient trouvé, etc.) |

---

## 6. Dépannage

### Problème: La consultation ne s'affiche pas après soumission
**Solution**:
1. Vérifiez que le système IMAP fonctionne (cron job configuré)
2. Vérifiez l'email reçu à consultations@verso-vet.com
3. Vérifiez que l'email contient un JSON valide en pièce jointe
4. Attendez quelques minutes (le monitoring IMAP s'exécute toutes les minutes)

### Problème: "Aucun résultat" lors de la recherche ERP
**Solution**:
1. Vérifiez l'orthographe du nom
2. La recherche se fait sur le nom EXACT (case-insensitive)
3. Utilisez seulement le nom (pas de prénoms complets)
4. Essayez une partie du nom (ex: "Mar" pour "Martin")

### Problème: Le document ne se télécharge pas
**Solution**:
1. Vérifiez que le document n'a pas d'accent ou caractères spéciaux
2. Vérifiez la taille du fichier
3. Essayez un autre navigateur
4. Attendez quelques secondes après le clic

### Problème: L'intégration échoue
**Solution**:
1. Vérifiez que l'ERP est accessible (http://10.0.0.44:8101)
2. Vérifiez que les données du formulaire sont complètes
3. Vérifiez que le propriétaire/animal n'existe pas déjà en double
4. Consultez les logs du serveur

---

## 7. Conseils Pratiques

1. **Avant d'intégrer**: Utilisez toujours **View** pour vérifier les données et documents
2. **Homonymes**: Ne passez pas à côté de la liste homonymes - elle prévient les doublons
3. **Noms exacts**: L'ERP utilise les noms exacts - attention aux espaces, majuscules
4. **Archivage**: Une fois intégrée, la consultation est archivée dans l'ERP - n'y revenez pas
5. **Fichiers**: Les documents sont supprimés après intégration - sauvegardez-les avant si besoin

---

## 8. Contactez le Support

Pour toute question ou problème technique:
- Email: drliot@verso-vet.com
- Système: Port 8092 sur 10.0.0.44
- Logs: Consulter les erreurs dans le journal du serveur

---

**Version**: 1.0  
**Date**: Mai 2026  
**Système**: Verso-Vet Consultation Management  
