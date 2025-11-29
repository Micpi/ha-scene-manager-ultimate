# 🏠 Scene Manager Ultimate

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)]()

**Scene Manager Ultimate** est une solution complète (Intégration + Carte) pour Home Assistant qui réinvente la gestion de l'éclairage.

Contrairement aux cartes classiques, cette intégration possède son propre "cerveau" (Backend) qui gère la synchronisation en temps réel entre tous les appareils et la persistance des données (couleurs, icônes, ordre) sans dépendre de scripts tiers.

![Preview](https://via.placeholder.com/800x400.png?text=Capture+d'écran+Scene+Manager)

## ✨ Pourquoi utiliser Scene Manager ?

* **📦 Tout-en-un :** Pas de scripts Python à copier manuellement. Installez l'intégration, et tout fonctionne.
* **⚡ Synchronisation Instantanée :** Modifiez une scène sur votre PC, la tablette murale se met à jour dans la seconde.
* **🧠 Détection Intelligente :** La carte scanne vos pièces (Areas) et détecte automatiquement les lumières associées.
* **🎨 Studio de Création :**
  * Interface visuelle pour régler les lumières (Sliders & Toggles).
  * **Drag & Drop** fluide pour organiser vos scènes.
  * Personnalisation des icônes et des couleurs.
* **💾 Persistance Robuste :** Vos configurations survivent aux redémarrages de Home Assistant.

---

## ⚙️ Installation

### Option 1 : Via HACS (Recommandé)

1. Assurez-vous d'avoir [HACS](https://hacs.xyz/) installé.
2. Allez dans **HACS > Intégrations**.
3. Cliquez sur le menu (3 points) > **Dépôts personnalisés**.
4. Ajoutez l'URL de ce dépôt.
5. Cherchez **"Scene Manager Ultimate"** et cliquez sur **Installer**.
6. **Redémarrez Home Assistant**.

### Option 2 : Installation Manuelle

1. Téléchargez ce dépôt.
2. Copiez le dossier `custom_components/scene_manager` dans votre dossier `/config/custom_components/`.
3. **Redémarrez Home Assistant**.

---

## 🔧 Configuration Initiale

Une fois installé et redémarré :

1. Allez dans **Paramètres > Appareils et services > Ajouter une intégration**.
2. Cherchez **"Scene Manager"**.
3. Validez (aucune configuration requise, cela active juste le moteur).

---

## 📱 Ajout de la Carte (Dashboard)

1. Allez sur votre tableau de bord.
2. Cliquez sur **Modifier** > **Ajouter une carte**.
3. Recherchez **"Scene Manager"**.
4. L'éditeur visuel s'ouvre :

| Option | Description |
| :--- | :--- |
| **Titre** | Nom affiché en haut de la carte. |
| **Pièce Fixe** | (Optionnel) ID de la zone pour créer un mode "Kiosque" bloqué sur une pièce. Laissez vide pour avoir le menu de navigation global. |
| **Style** | Choisissez l'apparence des boutons (Plein, Contour, Transparent, Rond, Carré...). |

### Code YAML (Exemple)

```yaml
type: custom:scene-manager-card
title: "Gestion Maison"
icon: "mdi:home-assistant"
button_style: "filled"
button_shape: "rounded"
scene_alignment: "left"
