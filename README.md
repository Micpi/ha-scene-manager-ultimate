# 🎬 Scene Manager Ultimate

**Scene Manager Ultimate** est une solution complète pour Home Assistant qui vous permet de créer, gérer et organiser vos scènes directement depuis votre tableau de bord Lovelace. Fini l'édition manuelle de fichiers YAML pour ajuster vos ambiances lumineuses !

![Version](https://img.shields.io/badge/version-1.0.10-blue)
![Maintenance](https://img.shields.io/badge/maintainer-Micpi-green)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

---

## ✨ Fonctionnalités

- **Création Intuitive** : Créez des scènes en un clic en capturant l'état actuel de vos entités (lumières, switchs, etc.).
- **Interface Tactile** : Une carte Lovelace dédiée (`scene-manager-card`) élégante, réactive et entièrement personnalisable.
- **Personnalisation Visuelle** : Choisissez l'icône et la couleur de chaque scène pour une identification rapide.
- **Organisation Avancée** :
  - **Drag & Drop** : Réorganisez vos scènes par simple glisser-déposer directement sur la carte (mode édition).
  - **Filtrage par Pièce** : Associez des scènes à des pièces spécifiques pour n'afficher que ce qui est pertinent.
- **Installation Simplifiée** : L'intégration gère automatiquement la copie des ressources JavaScript (`.js`) et vous notifie pour la configuration.
- **Nettoyage Automatique** : Désinstallation propre qui supprime les fichiers copiés et les données de stockage.

---

## 🚀 Installation

### Via HACS (Recommandé)

1. Ouvrez HACS dans Home Assistant.
2. Ajoutez ce dépôt en tant que **Dépôt Personnalisé** (Custom Repository).
3. Recherchez "Scene Manager Ultimate" et installez-le.
4. Redémarrez Home Assistant.

### Installation Manuelle

1. Téléchargez le code source.
2. Copiez le dossier `custom_components/scene_manager` dans votre dossier `config/custom_components/`.
3. Redémarrez Home Assistant.

---

## ⚙️ Configuration

### 1. Activer l'intégration

Une fois installé et Home Assistant redémarré :

1. Allez dans **Paramètres** > **Appareils et services**.
2. Cliquez sur **Ajouter une intégration**.
3. Cherchez **Scene Manager Ultimate** et validez.

> 💡 **Note** : Une notification persistante apparaîtra pour vous confirmer que la ressource JavaScript a été copiée dans `/local/` et vous guidera pour l'ajouter à vos ressources Lovelace si nécessaire.

### 2. Ajouter la carte au tableau de bord

Dans votre tableau de bord Lovelace :

1. Cliquez sur le menu (trois points) > **Modifier le tableau de bord**.
2. Cliquez sur **Ajouter une carte**.
3. Recherchez **Scene Manager Ultimate**.

#### Options de la carte (Éditeur Visuel)

| Option | Description |
| :--- | :--- |
| **Titre** | Le titre affiché en haut de la carte (ex: "Mes Ambiances"). |
| **Icône Titre** | L'icône affichée à côté du titre. |
| **Pièce Fixe** | (Optionnel) Si renseigné, la carte n'affichera que les scènes associées à cette pièce (ex: `salon`). |
| **Style Bouton** | Choisissez entre `Plein` (Filled), `Contour` (Outline) ou `Transparent` (Ghost). |
| **Forme Bouton** | `Arrondi`, `Carré` ou `Rond`. |
| **Dimensions** | Ajustez la largeur et la hauteur des boutons pour s'adapter à votre design. |

---

## 🛠 Services Techniques

Pour les utilisateurs avancés souhaitant scripter la création de scènes, l'intégration expose des services :

### `scene_manager.save_scene`

Crée ou met à jour une scène avec ses métadonnées personnalisées.

- **scene_id** (Requis) : Identifiant unique (ex: `soiree_film`).
- **entities** (Requis) : Liste des entités à inclure dans la capture.
- **icon** : Icône MDI (ex: `mdi:movie`).
- **color** : Couleur hexadécimale (ex: `#FF5722`).
- **room** : Pièce associée pour le filtrage.

### `scene_manager.delete_scene`

Supprime une scène et ses métadonnées du stockage.

- **entity_id** : L'entité scène à supprimer (ex: `scene.soiree_film`).

### `scene_manager.reorder_scenes`

Met à jour l'ordre d'affichage des scènes pour une pièce donnée.

---

## ❓ Dépannage

### Erreur : "Custom element doesn't exist: scene-manager-card"

- Cela signifie que le navigateur ne trouve pas le fichier JavaScript de la carte.
- Vérifiez dans **Paramètres** > **Tableaux de bord** > **Ressources** que vous avez bien une entrée :
  - **URL** : `/local/scene-manager-card.js`
  - **Type** : Module JavaScript
- Si l'erreur persiste, videz le cache de votre navigateur ou essayez en navigation privée.

---

## 📄 Licence

Ce projet est développé par **Micpi** et est distribué sous licence MIT.
